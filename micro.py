"""Foo - The Micro GLSL Render Engine

Simple standalone version of the render engine contained within a single script.
Useful for a basis of your own render engine, or just for simple use cases and experimental shaders.

Features:
- Full GLSL pipeline (Vertex, Fragment, Geometry, Tessellation)
- Live viewport shading as you work
- Hot reload of shader source files on change
- Single directional light information as uniforms `_MainLightDirection` and `_MainLightColor`
- Per-vertex inputs `Position` and `Normal`
"""
import os
import bpy
import numpy as np
import gpu
from bgl import *
from mathutils import Vector, Matrix, Quaternion
from math import cos

from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)

from bpy.types import (
    PropertyGroup,
    Panel
)

#region Fallback Shaders

VS_FALLBACK = '''
#version 330 core

uniform mat4 ModelViewProjectionMatrix;
uniform mat4 ModelMatrix;

in vec3 Position;
in vec3 Normal;

out VS_OUT {
    vec3 positionWS;
    vec3 normalWS;
} OUT;

void main()
{
    gl_Position = ModelViewProjectionMatrix * vec4(Position, 1.0);
    
    vec3 positionWS = (ModelMatrix * vec4(Position, 1.0)).xyz;
    vec3 normalWS = (ModelMatrix * vec4(Normal, 0)).xyz;
    
    OUT.positionWS = positionWS;
    OUT.normalWS = normalWS;
}
'''

FS_FALLBACK = '''
#version 330 core

uniform mat4 CameraMatrix;

layout (location = 0) out vec4 FragColor;

in VS_OUT { 
    vec3 positionWS;
    vec3 normalWS;
} IN;

void main()
{
    vec3 cameraPositionWS = CameraMatrix[3].xyz;

    vec3 eye = cameraPositionWS - IN.positionWS;
    float ndl = clamp(dot(IN.normalWS, normalize(eye)), 0.0, 1.0);
    
    vec3 inner = vec3(0.61, 0.54, 0.52);
    vec3 outer = vec3(0.27, 0.19, 0.18);
    vec3 highlight = vec3(0.98, 0.95, 0.92);
    
    FragColor = vec4(mix(outer, mix(inner, highlight, ndl * 0.25), ndl * 0.75), 1);
}
'''

# Skip geometry shader for fallback
GS_FALLBACK = None

#endregion Fallback Shaders

#region Render Engine

class CompileError(Exception):
    pass

class LinkError(Exception):
    pass

def compile_glsl(src: str, stage_flag: int) -> int:
    shader = glCreateShader(type_flag)
    glShaderSource(shader, src)
    glCompileShader(shader)

    #Check for compile errors
    shader_ok = Buffer(GL_INT, 1)
    glGetShaderiv(shader, GL_COMPILE_STATUS, shader_ok)

    if shader_ok[0] == True:
        return shader

    # If not okay, read the error from GL logs
    bufferSize = 1024
    length = Buffer(GL_INT, 1)
    infoLog = Buffer(GL_BYTE, [bufferSize])
    glGetShaderInfoLog(shader, bufferSize, length, infoLog)

    if stage_flag == GL_VERTEX_SHADER:
        stage = 'Vertex'
    elif stage_flag == GL_FRAGMENT_SHADER:
        stage = 'Fragment'
    elif stage_flag == GL_TESS_CONTROL_SHADER:
        stage = 'Tessellation Control'
    elif stage_flag == GL_TESS_EVALUATION_SHADER:
        stage = 'Tessellation Evaluation'
    elif stage_flag == GL_GEOMETRY_SHADER:
        stage = 'Geometry'
    
    # Reconstruct byte data into a string
    err = ''.join(chr(infoLog[i]) for i in range(length[0]))
    raise CompileError(stage + ' Shader Error:\n' + err)

class Shader:
    """Encapsulate shader compilation and configuration"""
    def __init__(self):
        self.program = None
        self.prev_mtimes = []
        self.monitored_files = []
        self.stages = {}

    def update_settings(self, settings):
        if not os.path.isfile(settings.vert_filename):
            raise FileNotFoundError('Missing required vertex shader')
            
        if not os.path.isfile(settings.frag_filename):
            raise FileNotFoundError('Missing required fragment shader')
        
        self.stages = { 
            'vs': settings.vert_filename,
            'fs': settings.frag_filename,
            'tcs': settings.tesc_filename, 
            'tes': settings.tese_filename,
            'gs': settings.geom_filename
        }
        
        self.monitored_files = [f for f in self.stages.values() if f]
        # We keep prev_mtimes - in case this was called with the same files

    def compile_from_fallback(self):
        self.prev_mtimes = []
        self.compile_from_strings(VS_FALLBACK, FS_FALLBACK)

    def mtimes(self):
        """Aggregate file modication times from sources"""
        return [os.stat(file).st_mtime for file in self.monitored_files]

    def mtimes_changed(self) -> bool:
        """Check if the file update time has changed in any of the source files"""
        return self.prev_mtimes != self.mtimes()

    def recompile(self):
        with open(self.vert) as f:
            vs = f.read()
        
        with open(self.frag) as f:
            fs = f.read()
        
        gs = None
        if (self.geom):
            with open(self.geom) as f:
                gs = f.read()
                
        self.compile_from_strings(vs, fs, tcs, tes, gs)
        self.prev_mtimes = self.mtimes()

    def compile_from_strings(self, vs: str, fs: str, tcs: str = None, tes: str = None, gs: str = None):
        vs_compiled = compile_glsl(vs, GL_VERTEX_SHADER)
        fs_compiled = compile_glsl(fs, GL_FRAGMENT_SHADER)
        tcs_compiled = compile_glsl(gs, GL_TESS_CONTROL_SHADER) if tcs else None
        tes_compiled = compile_glsl(gs, GL_TESS_EVALUATION_SHADER) if tes else None
        gs_compiled = compile_glsl(gs, GL_GEOMETRY_SHADER) if gs else None

        program = glCreateProgram()
        glAttachShader(program, vs_compiled)
        glAttachShader(program, fs_compiled)
        if tcs: glAttachShader(program, tcs_compiled)
        if tes: glAttachShader(program, tes_compiled)
        if gs: glAttachShader(program, gs_compiled)
            
        glLinkProgram(program)

        # Cleanup shaders
        glDeleteShader(vs_compiled)
        glDeleteShader(fs_compiled)
        if tcs: glDeleteShader(tcs_compiled)
        if tes: glDeleteShader(tes_compiled)
        if gs: glDeleteShader(gs_compiled)

        #Check for link errors
        link_ok = Buffer(GL_INT, 1)
        glGetProgramiv(program, GL_LINK_STATUS, link_ok)

        # If not okay, read the error from GL logs and report
        if link_ok[0] != True:
            self.program = None
            
            bufferSize = 1024
            length = Buffer(GL_INT, 1)
            infoLog = Buffer(GL_BYTE, [bufferSize])
            glGetProgramInfoLog(program, bufferSize, length, infoLog)
            
            err = ''.join(chr(infoLog[i]) for i in range(length[0]))
            raise LinkError(err)
            
        self.program = program
    
    def bind(self):
        glUseProgram(self.program)
        
    def unbind(self):
        pass
        
    def set_mat4(self, uniform: str, mat):
        location = glGetUniformLocation(self.program, uniform)
        if location < 0: return # Skip uniforms that were optimized out for being unused

        mat_buffer = np.reshape(mat, (16, )).tolist()
        mat_buffer = Buffer(GL_FLOAT, 16, mat_buffer)
        glUniformMatrix4fv(location, 1, GL_FALSE, mat_buffer)

    def set_vec3_array(self, uniform: str, arr):
        location = glGetUniformLocation(self.program, uniform)
        if location < 0: return

        buffer = Buffer(GL_FLOAT, len(arr), arr)
        glUniform3fv(location, len(arr), buffer)
        
    def set_vec4_array(self, uniform: str, arr):
        location = glGetUniformLocation(self.program, uniform)
        if location < 0: return

        buffer = Buffer(GL_FLOAT, len(arr), arr)
        glUniform4fv(location, len(arr), buffer)
    
    def set_int(self, uniform: str, value: int):
        location = glGetUniformLocation(self.program, uniform)
        if location < 0: return

        glUniform1i(location, value)

    def set_vec3(self, uniform: str, value):
        location = glGetUniformLocation(self.program, uniform)
        if location < 0: return

        glUniform3f(location, value[0], value[1], value[2])
        
    def set_vec4(self, uniform: str, value):
        location = glGetUniformLocation(self.program, uniform)
        if location < 0: return

        glUniform4f(location, value[0], value[1], value[2], value[3])
        
    def set_vertex_attribute(self, name: str, stride: int):
        """Enable a vertex attrib array and set the pointer for GL_ARRAY_BUFFER reads"""
        location = glGetAttribLocation(self.program, name)
        glEnableVertexAttribArray(location)
        glVertexAttribPointer(location, 3, GL_FLOAT, GL_FALSE, stride, 0)

class Mesh:
    """Minimal representation needed to render a mesh"""
    def __init__(self):
        # Once on setup, create a VAO to store VBO/EBO and settings
        VAO = Buffer(GL_INT, 1)
        glGenVertexArrays(1, VAO)
        self.VAO = VAO[0]

        VBO = Buffer(GL_INT, 2)
        glGenBuffers(2, VBO)
        self.VBO = VBO

        EBO = Buffer(GL_INT, 1)
        glGenBuffers(1, EBO)
        self.EBO = EBO[0]
        
        self.is_dirty = True
        self.indices_size = 0

        # ..and in cleanup:
        # might need to be buffer refs
        # glDeleteVertexArrays(1, VAO)
        # glDeleteBuffers(1, VBO)
        # glDeleteBuffers(1, EBO)

    def rebuild(self, eval_obj, shader: Shader):
        """Copy evaluated mesh data into buffers for updating the VBOs"""
        # mesh = self.obj.data
        mesh = eval_obj.to_mesh()

        # Refresh triangles on the mesh
        # TODO: Is this necessary with the eval mesh?
        mesh.calc_loop_triangles()
        
        # Fast copy vertex data / triangle indices from the mesh into buffers
        # Reference: https://blog.michelanders.nl/2016/02/copying-vertices-to-numpy-arrays-in_4.html
        vertices = [0]*len(mesh.vertices) * 3
        mesh.vertices.foreach_get('co', vertices)
        self.vertices = Buffer(GL_FLOAT, len(vertices), vertices)
        
        normals = [0]*len(mesh.vertices) * 3
        mesh.vertices.foreach_get('normal', normals)
        self.normals = Buffer(GL_FLOAT, len(normals), normals)
        
        indices = [0]*len(mesh.loop_triangles) * 3
        mesh.loop_triangles.foreach_get('vertices', indices)
        self.indices = Buffer(GL_INT, len(indices), indices)
        
        eval_obj.to_mesh_clear()

        # let the render loop set the new buffer data into the VAO,
        # otherwise we may run into access violation issues. 
        self.is_dirty = True


    def rebuild_vbos(self, shader: Shader):
        """Upload new vertex buffer data to the GPU
        
        This method needs to be called within the render thread.
        """
        # Bind the VAO so we can upload new buffers
        glBindVertexArray(self.VAO)

        # Copy verts
        glBindBuffer(GL_ARRAY_BUFFER, self.VBO[0])
        glBufferData(GL_ARRAY_BUFFER, len(self.vertices) * 4, self.vertices, GL_STATIC_DRAW) # GL_STATIC_DRAW - for inactive mesh
        shader.set_vertex_attribute('Position', 0)

        # Copy normals
        glBindBuffer(GL_ARRAY_BUFFER, self.VBO[1])
        glBufferData(GL_ARRAY_BUFFER, len(self.normals) * 4, self.normals, GL_STATIC_DRAW)
        shader.set_vertex_attribute('Normal', 0)

        # TODO: Tangent, Binormal, Color, Texcoord0-7
        # TODO: Probably don't do per-mesh VAO. See: https://stackoverflow.com/a/18487155

        # Copy indices
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.EBO)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, len(self.indices) * 4, self.indices, GL_STATIC_DRAW)

        # Cleanup, just so bad code elsewhere doesn't also write to this VAO
        glBindVertexArray(0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        self.indices_size = len(self.indices)

    def update(self, obj):
        """Update transformation info for this mesh"""
        self.model_matrix = obj.matrix_world

    def dirty(self):
        """Dirty the mesh - causing all GPU buffers to reload"""
        self.is_dirty = True

    def draw(self, shader: Shader):
        if self.is_dirty:
            self.rebuild_vbos(shader)
            self.is_dirty = False

        glBindVertexArray(self.VAO)
        glDrawElements(GL_TRIANGLES, self.indices_size, GL_UNSIGNED_INT, 0)
        glBindVertexArray(0)

class FooRenderEngine(bpy.types.RenderEngine):
    bl_idname = "foo_renderer"
    bl_label = "Foo Renderer"
    bl_use_preview = True

    def __init__(self):
        """Called when a new render engine instance is created. 

        Note that multiple instances can exist @ once, e.g. a viewport and final render
        """
        self.meshes = dict()
        
        self.light_direction = (0, 0, 1, 0)
        self.light_color = (1, 1, 1, 1)

        self.default_shader = Shader()
        self.user_shader = Shader()

        # Set the initial shader to the default until we load a user shader
        self.shader = self.default_shader

        try:
            self.default_shader.compile_from_fallback()
        except Exception as e:
            print('--Failed to compile default shader--')
            print(e)
    
    def __del__(self):
        """Clean up render engine data, e.g. stopping running render threads"""
        pass

    def render(self, depsgraph):
        """Handle final render (F12) and material preview window renders"""
        pass

    def view_update(self, context, depsgraph):
        """Called when a scene or 3D viewport changes"""
        self.check_shaders(context)

        region = context.region
        view3d = context.space_data
        scene = depsgraph.scene

        self.updated_meshes = dict()
        self.updated_geometries = []
        
        # Check for any updated mesh geometry to rebuild GPU buffers
        for update in depsgraph.updates:
            name = update.id.name
            if type(update.id) == bpy.types.Object:
                if update.is_updated_geometry and name in self.meshes:
                    self.updated_geometries.append(name)
        
        # Aggregate everything visible in the scene that we care about
        for obj in scene.objects:
            if not obj.visible_get():
                continue
            
            if obj.type == 'MESH':
                self.update_mesh(obj, depsgraph)
            elif obj.type == 'LIGHT' and obj.data.type == 'SUN':
                self.update_light(obj)
                
        self.meshes = self.updated_meshes
    
    def update_mesh(self, obj, depsgraph):
        """Update mesh data for next render"""
        # Get/create the mesh instance and determine if we need 
        # to reupload geometry to the GPU for this mesh
        rebuild_geometry = obj.name in self.updated_geometries
        if obj.name not in self.meshes:
            mesh = Mesh()
            rebuild_geometry = True
        else:
            mesh = self.meshes[obj.name]

        mesh.update(obj)

        # Copy updated vertex data to the GPU when modified
        if rebuild_geometry:
            mesh.rebuild(obj.evaluated_get(depsgraph), self.shader)
        
        self.updated_meshes[obj.name] = mesh
        
    def update_light(self, obj):
        """Update main (sun) light data for the next render"""
        light_type = obj.data.type 
        
        direction = obj.matrix_world.to_quaternion() @ Vector((0, 0, 1))
        color = obj.data.color

        self.light_direction = (direction[0], direction[1], direction[2], 0)
        self.light_color = (color[0], color[1], color[2], settings.intensity)

    def check_shaders(self, context):
        """Check if we should reload the shader sources"""
        settings = context.scene.foo

        # Check for readable source files and changes
        try:
            self.user_shader.update_settings(settings)
            has_user_shader_changes = self.user_shader.mtimes_changed()
        except Exception as e:
            settings.last_shader_error = str(e)
            self.shader = self.default_shader
            return

        # Trigger a recompile if we're forcing it or the files on disk
        # have been modified since the last render
        if settings.force_reload or (settings.live_reload and has_user_shader_changes):
            settings.force_reload = False
            try:
                self.user_shader.recompile()
                settings.last_shader_error = ''
                self.shader = self.user_shader
            except Exception as e:
                print('COMPILE ERROR', type(e))
                print(e)
                settings.last_shader_error = str(e)
                self.shader = self.default_shader

    def view_draw(self, context, depsgraph):
        """Called whenever Blender redraws the 3D viewport"""
        if not self.shader: return 
        
        scene = depsgraph.scene
        region = context.region
        region3d = context.region_data
        settings = scene.foo
        
        self.bind_display_space_shader(scene)
        self.shader.bind()
        
        # Set up MVP matrices
        self.shader.set_mat4("ViewMatrix", region3d.view_matrix.transposed())
        self.shader.set_mat4("ProjectionMatrix", region3d.window_matrix.transposed())
        self.shader.set_mat4("CameraMatrix", region3d.view_matrix.inverted().transposed())

        # Upload current lighting information
        self.shader.set_vec4("_MainLightDirection", self.light_direction)
        self.shader.set_vec4("_MainLightColor", self.light_color)

        glEnable(GL_DEPTH_TEST)
        
        clear_color = scene.foo.clear_color
        glClearColor(clear_color[0], clear_color[1], clear_color[2], 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        for mesh in self.meshes.values():
            mv = region3d.view_matrix @ mesh.model_matrix
            mvp = region3d.window_matrix @ mv

            # Set per-mesh uniforms
            self.shader.set_mat4("ModelMatrix", mesh.model_matrix.transposed())
            self.shader.set_mat4("ModelViewMatrix", mv.transposed())
            self.shader.set_mat4("ModelViewProjectionMatrix", mvp.transposed())
            
            # Draw the mesh itself
            mesh.draw(self.shader)

        self.shader.unbind()
        self.unbind_display_space_shader()

        glDisable(GL_BLEND)

    def refresh_all_buffers(self):
        """Force *all* GPU buffers to reload"""
        for mesh in self.meshes.values():
            mesh.dirty()

#endregion Render Engine

#region Settings

def force_shader_reload(self, context):
    """Callback when any of the shader filenames change in FooRenderSettings"""
    context.scene.foo.force_reload = True

class FooRendererSettings(PropertyGroup):
    """Collection of user configurable settings for the renderer"""

    # Shader source files 
    vert_filename: StringProperty(
        name='Vertex Shader',
        description='Source file path',
        default='',
        subtype='FILE_PATH',
        update=force_shader_reload
    )
    
    frag_filename: StringProperty(
        name='Fragment Shader',
        description='Source file path',
        default='',
        subtype='FILE_PATH',
        update=force_shader_reload
    )
    
    tesc_filename: StringProperty(
        name='Tess Control Shader',
        description='Source file path',
        default='',
        subtype='FILE_PATH',
        update=force_shader_reload
    )
    
    tese_filename: StringProperty(
        name='Tess Evaluation Shader',
        description='Source file path',
        default='',
        subtype='FILE_PATH',
        update=force_shader_reload
    )
    
    geom_filename: StringProperty(
        name='Geometry Shader',
        description='Source file path',
        default='',
        subtype='FILE_PATH',
        update=force_shader_reload
    )
    
    live_reload: BoolProperty(
        name='Live Reload',
        description='Reload source files on change',
        default=True
    )
    
    clear_color: FloatVectorProperty(  
        name='Clear Color',
        subtype='COLOR',
        default=(0.15, 0.15, 0.15),
        min=0.0, max=1.0,
        description='Background color of the scene'
    )
    
    force_reload: BoolProperty(
        name='Force Reload'
    )

    last_shader_error: StringProperty(
        name='Last Shader Error'
    )
    
    @classmethod
    def register(cls):
        bpy.types.Scene.foo = PointerProperty(
            name='Foo Render Settings',
            description='',
            type=cls
        )
        
    @classmethod
    def unregister(cls):
        del bpy.types.Scene.foo

class FooLightSettings(PropertyGroup):
    color: FloatVectorProperty(  
        name='Color',
        subtype='COLOR',
        default=(0.15, 0.15, 0.15),
        min=0.0, max=1.0,
        description='color picker'
    )
    
    distance: FloatProperty(
        name='Range',
        default=1.0,
        description='How far light is emitted from the center of the object',
        min=0.000001
    )
    
    intensity: FloatProperty(
        name='Intensity',
        default=1.0,
        description='Brightness of the light',
        min=0.0
    )
    
    @classmethod
    def register(cls):
        bpy.types.Light.foo = PointerProperty(
            name='Foo Light Settings',
            description='',
            type=cls
        )
    
    @classmethod
    def unregister(cls):
        del bpy.types.Light.foo
    
#endregion Settings

#region Operators

class FooReloadSourcesOperator(bpy.types.Operator):
    """Operator to force reload of shader source files"""
    bl_idname = 'foo.reload_sources'
    bl_label = 'Reload Shader Sources'

    def invoke(self, context, event):
        context.scene.foo.force_reload = True
        
        return {'FINISHED'}

#endregion Operators

#region Panels

class BasePanel(Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'
    COMPAT_ENGINES = {FooRenderEngine.bl_idname}

    @classmethod
    def poll(cls, context):
        return context.engine in cls.COMPAT_ENGINES

class FOO_RENDER_PT_settings(BasePanel):
    """Parent panel for renderer settings"""
    bl_label = 'Foo Renderer Settings'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        settings = context.scene.foo
        # No controls at top level.

class FOO_RENDER_PT_settings_viewport(BasePanel):
    """Global viewport configurations"""
    bl_label = 'Viewport'
    bl_parent_id = 'FOO_RENDER_PT_settings'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        settings = context.scene.foo

        col = layout.column(align=True)
        col.prop(settings, 'clear_color')

class FOO_RENDER_PT_settings_sources(BasePanel):
    """Shader source file references and reload settings"""
    bl_label = 'Source Files'
    bl_parent_id = 'FOO_RENDER_PT_settings'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        settings = context.scene.foo

        col = layout.column(align=True)
        col.prop(settings, 'vert_filename')
        col.prop(settings, 'frag_filename')
        col.prop(settings, 'tesc_filename')
        col.prop(settings, 'tese_filename')
        col.prop(settings, 'geom_filename')
        
        layout.separator()
         
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(settings, "live_reload", text="Live Reload")
        row.operator("foo.reload_sources", text = "Reload")
        
        # Alert message on compile error
        col = layout.column(align=True)
        col.alert = True

        if settings.last_shader_error:
            col.label(text='Compilation error(s):', icon='ERROR')
            lines = settings.last_shader_error.split('\n')
            for line in lines:
                col.label(text=line)
 
class FOO_LIGHT_PT_light(BasePanel):
    """Custom per-light settings editor for this render engine"""
    bl_label = 'Light'
    bl_context = 'data'
    
    @classmethod
    def poll(cls, context):
        return context.light and BasePanel.poll(context)

    def draw(self, context):
        layout = self.layout
        light = context.light
        
        settings = context.light.foo
        
        # Only a primary sun light is supported
        if light.type != 'SUN':
            return 

        if self.bl_space_type == 'PROPERTIES':
            layout.row().prop(light, 'type', expand=True)
            layout.use_property_split = True
        else:
            layout.use_property_split = True
            layout.row().prop(light, 'type')
        
        col = layout.column()
        col.prop(light, 'color')
        
        col.separator()
        col.prop(settings, 'distance')
        col.prop(settings, 'intensity')

#endregion Panels

#region Plugin Registration

# Classes to (un)register as part of this addon
CLASSLIST = (
    FooRenderEngine,
    
    # Operators
    FooReloadSourcesOperator,
    
    # Settings
    FooRendererSettings,
    FooLightSettings,
    
    # Renderer panels
    FOO_RENDER_PT_settings,
    FOO_RENDER_PT_settings_viewport,
    FOO_RENDER_PT_settings_sources,

    # Light panels
    FOO_LIGHT_PT_light
)

# RenderEngines also need to tell UI Panels that they are compatible with.
# We recommend to enable all panels marked as BLENDER_RENDER, and then
# exclude any panels that are replaced by custom panels registered by the
# render engine, or that are not supported.
def get_panels():
    exclude_panels = {
        'VIEWLAYER_PT_filter',
        'VIEWLAYER_PT_layer_passes'
    }

    panels = []
    for panel in bpy.types.Panel.__subclasses__():
        if hasattr(panel, 'COMPAT_ENGINES') and 'BLENDER_RENDER' in panel.COMPAT_ENGINES:
            if panel.__name__ not in exclude_panels:
                panels.append(panel)

    return panels

def register():
    """Register panels, operators, and the render engine itself"""
    for cls in CLASSLIST:
        bpy.utils.register_class(cls)

    for panel in get_panels():
        panel.COMPAT_ENGINES.add(FooRenderEngine.bl_idname)

def unregister():
    """Unload everything previously registered"""
    for cls in CLASSLIST:
        bpy.utils.unregister_class(cls)

    for panel in get_panels():
        if FooRenderEngine.bl_idname in panel.COMPAT_ENGINES:
            panel.COMPAT_ENGINES.remove(FooRenderEngine.bl_idname)

if __name__ == "__main__":
    register()

#endregion Plugin Registration
