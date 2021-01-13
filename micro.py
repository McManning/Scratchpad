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

bl_info = {
    'name': 'Foo',
    'description': 'Micro GLSL Render Engine',
    'author': 'Chase McManning',
    'version': (0, 1, 0),
    'blender': (2, 82, 0),
    'doc_url': 'https://github.com/McManning/Scratchpad/wiki',
    'tracker_url': 'https://github.com/McManning/Scratchpad/issues',
    'category': 'Render'
}

import os
import threading
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

# Constants not exported from bgl for some reason despite
# being documented in https://docs.blender.org/api/current/bgl.html
GL_TESS_EVALUATION_SHADER = 36487
GL_TESS_CONTROL_SHADER = 36488
GL_PATCHES = 14

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

#endregion Fallback Shaders

#region Render Engine

class CompileError(Exception):
    pass

class LinkError(Exception):
    pass

class BaseShader:
    """Encapsulate shader compilation and configuration

    Attributes:
        program (int): Shader program ID or None if not loaded
        last_error (str): Last shader compilation error
        sources (dict): Dictionary mapping GL stage constant to shader source string
        needs_recompile (bool): Should the render thread try to recompile shader sources
    """

    # Supported GLSL stages
    STAGES = [
        GL_VERTEX_SHADER,
        GL_TESS_EVALUATION_SHADER,
        GL_TESS_CONTROL_SHADER,
        GL_GEOMETRY_SHADER,
        GL_FRAGMENT_SHADER
    ]

    def __init__(self):
        self.program = None
        self.last_error = ''
        self.sources = dict.fromkeys(self.STAGES, None)
        self.needs_recompile = True

    def update_settings(self, settings):
        """Update current settings and check if a recompile is necessary.

        This method is called from the main thread. Do not perform any actual
        shader compilation here - instead flag it for a recompile on the
        render thread by setting `self.needs_recompile` to true.

        Args:
            settings (FooRendererSettings): Current settings to read
        """
        pass

    def recompile(self):
        """Recompile shaders from sources, setting `self.last_error` if anything goes wrong.

        This *MUST* be called from within the render thread to safely
        compile shaders within the RenderEngine's GL context.
        """

        try:
            self.program = self.compile_program()
            self.last_error = ''
        except Exception as err:
            self.last_error = str(err)
            self.program = None

    @property
    def has_tessellation(self) -> bool:
        """Does this shader perform tessellation"""
        return self.sources[GL_TESS_CONTROL_SHADER] is not None and self.sources[GL_TESS_EVALUATION_SHADER] is not None

    def compile_stage(self, stage: int):
        """Compile a specific shader stage from `self.sources`

        Args:
            stage (int): GL stage (e.g. `GL_VERTEX_SHADER`)

        Returns:
            int|None: Compiled Shader ID or None if the stage does not have a source

        Raises:
            CompileError: If GL fails to compile the stage
        """
        if not self.sources[stage]: # Skip stage
            return None

        shader = glCreateShader(stage)
        glShaderSource(shader, self.sources[stage])
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

        if stage == GL_VERTEX_SHADER:
            stage_name = 'Vertex'
        elif stage == GL_FRAGMENT_SHADER:
            stage_name = 'Fragment'
        elif stage == GL_TESS_CONTROL_SHADER:
            stage_name = 'Tessellation Control'
        elif stage == GL_TESS_EVALUATION_SHADER:
            stage_name = 'Tessellation Evaluation'
        elif stage == GL_GEOMETRY_SHADER:
            stage_name = 'Geometry'

        # Reconstruct byte data into a string
        err = ''.join(chr(infoLog[i]) for i in range(length[0]))
        raise CompileError(stage_name + ' Shader Error:\n' + err)

    def compile_program(self):
        """Create a GL shader program from current `self.sources`

        Returns:
            int: GL program ID

        Raises:
            CompileError: If one or more stages fail to compile
            LinkError: If the program fails to link stages
        """
        vs = self.compile_stage(GL_VERTEX_SHADER)
        fs = self.compile_stage(GL_FRAGMENT_SHADER)
        tcs = self.compile_stage(GL_TESS_CONTROL_SHADER)
        tes = self.compile_stage(GL_TESS_EVALUATION_SHADER)
        gs = self.compile_stage(GL_GEOMETRY_SHADER)

        program = glCreateProgram()
        glAttachShader(program, vs)
        glAttachShader(program, fs)
        if tcs: glAttachShader(program, tcs)
        if tes: glAttachShader(program, tes)
        if gs: glAttachShader(program, gs)

        glLinkProgram(program)

        # Cleanup shaders
        glDeleteShader(vs)
        glDeleteShader(fs)
        if tcs: glDeleteShader(tcs)
        if tes: glDeleteShader(tes)
        if gs: glDeleteShader(gs)

        # Check for link errors
        link_ok = Buffer(GL_INT, 1)
        glGetProgramiv(program, GL_LINK_STATUS, link_ok)

        # If not okay, read the error from GL logs and report
        if link_ok[0] != True:
            bufferSize = 1024
            length = Buffer(GL_INT, 1)
            infoLog = Buffer(GL_BYTE, [bufferSize])
            glGetProgramInfoLog(program, bufferSize, length, infoLog)

            err = ''.join(chr(infoLog[i]) for i in range(length[0]))
            raise LinkError(err)

        return program

    def bind(self) -> bool:
        """Bind the shader for use and check if a recompile is necessary.

        Returns:
            bool: False if the shader could not be bound (e.g. due to a failed recompile)
        """
        if self.needs_recompile:
            self.recompile()
            self.needs_recompile = False

        if not self.program:
            return False

        glUseProgram(self.program)
        return True

    def unbind(self):
        """Perform cleanup necessary for this shader"""
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

    def set_float(self, uniform: str, value: float):
        location = glGetUniformLocation(self.program, uniform)
        if location < 0: return

        glUniform1f(location, value)

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


class FallbackShader(BaseShader):
    """Safe fallback shader in case the user shader fails to compile"""

    def __init__(self):
        super().__init__()
        self.sources[GL_VERTEX_SHADER] = VS_FALLBACK
        self.sources[GL_FRAGMENT_SHADER] = FS_FALLBACK

class UserShader(BaseShader):
    """Shader compiled from the user's GLSL source files"""
    def __init__(self):
        super().__init__()

        self.prev_mtimes = []
        self.monitored_files = []
        self.stage_filenames = dict()

    def update_settings(self, settings):
        """Update current settings and check if a recompile is necessary

        Raises:
            FileNotFoundError: If the vertex or fragment shader are missing

        Args:
            settings (FooRendererSettings): Current settings to read
        """
        if not os.path.isfile(settings.vert_filename):
            raise FileNotFoundError('Missing required vertex shader')

        if not os.path.isfile(settings.frag_filename):
            raise FileNotFoundError('Missing required fragment shader')

        self.stage_filenames = {
            GL_VERTEX_SHADER:           settings.vert_filename,
            GL_TESS_CONTROL_SHADER:     settings.tesc_filename,
            GL_TESS_EVALUATION_SHADER:  settings.tese_filename,
            GL_GEOMETRY_SHADER:         settings.geom_filename,
            GL_FRAGMENT_SHADER:         settings.frag_filename
        }

        self.monitored_files = [f for f in self.stage_filenames.values() if f]

        # Determine if we need to recompile this shader in the render thread.
        # This is based on whether the source files have changed and we're live reloading
        # OR the user has chosen to force reload shaders for whatever reason
        has_source_changes = self.mtimes_changed()
        if settings.force_reload or (settings.live_reload and has_source_changes):
            settings.force_reload = False

            self.load_source_files()
            self.needs_recompile = True

    def load_source_files(self):
        """Read source files into their respective stage buffers for recompilation"""
        self.stage = [f for f in self.stage_filenames]

        for stage in self.STAGES:
            if self.stage_filenames[stage]:
                with open(self.stage_filenames[stage]) as f:
                    self.sources[stage] = f.read()
            else:
                self.sources[stage] = None

        # Update our mtimes to match the last time we read from source files
        self.prev_mtimes = self.mtimes()

    def mtimes(self):
        """Aggregate file modication times from sources"""
        return [os.stat(file).st_mtime for file in self.monitored_files]

    def mtimes_changed(self) -> bool:
        """Check if the file update time has changed in any of the source files"""
        return self.prev_mtimes != self.mtimes()


class Mesh:
    """Minimal representation needed to render a mesh"""
    def __init__(self, name):
        self.name = name
        self.lock = threading.Lock()
        self.VAO = None
        self.VBO = None
        self.EBO = None

        self.is_dirty = False
        self.indices_size = 0

    def rebuild(self, eval_obj):
        """Copy evaluated mesh data into buffers for updating the VBOs on the render thread"""

        with self.lock:
            # We use the evaluated mesh after all modifies are applied.
            # This is a temporary mesh that we can't safely hold a reference
            # to within the render thread - so we copy from it here and now.
            mesh = eval_obj.to_mesh()

            # Refresh triangles on the mesh
            # TODO: Is this necessary with the eval mesh?
            mesh.calc_loop_triangles()

            # Fast copy vertex data / triangle indices from the mesh into buffers
            # Reference: https://blog.michelanders.nl/2016/02/copying-vertices-to-numpy-arrays-in_4.html
            self._vertices = [0]*len(mesh.vertices) * 3
            mesh.vertices.foreach_get('co', self._vertices)
            self.vertices = Buffer(GL_FLOAT, len(self._vertices), self._vertices)

            self._normals = [0]*len(mesh.vertices) * 3
            mesh.vertices.foreach_get('normal', self._normals)
            self.normals = Buffer(GL_FLOAT, len(self._normals), self._normals)

            self._indices = [0]*len(mesh.loop_triangles) * 3
            mesh.loop_triangles.foreach_get('vertices', self._indices)
            self.indices = Buffer(GL_INT, len(self._indices), self._indices)

            eval_obj.to_mesh_clear()

            # Let the render thread know it can copy new buffer data to the GPU
            self.is_dirty = True

    def rebuild_vbos(self, shader: BaseShader):
        """Upload new vertex buffer data to the GPU

        This method needs to be called within the render thread
        to safely access the RenderEngine's current GL context

        Args:
            shader (BaseShader): Shader to set attribute positions in
        """

        # Make sure our VAO/VBOs are ready
        if not self.VAO:
            VAO = Buffer(GL_INT, 1)
            glGenVertexArrays(1, VAO)
            self.VAO = VAO[0]

        if not self.VBO:
            VBO = Buffer(GL_INT, 2)
            glGenBuffers(2, VBO)
            self.VBO = VBO

        if not self.EBO:
            EBO = Buffer(GL_INT, 1)
            glGenBuffers(1, EBO)
            self.EBO = EBO[0]

        # Bind the VAO so we can upload new buffers
        glBindVertexArray(self.VAO)

        # TODO: Use glBufferSubData to avoid recreating the store with glBufferData.
        # This would require tracking previous buffer size as well to determine if
        # we need to rebuild a new one during resizes.

        # Copy verts
        glBindBuffer(GL_ARRAY_BUFFER, self.VBO[0])
        glBufferData(GL_ARRAY_BUFFER, len(self.vertices) * 4, self.vertices, GL_DYNAMIC_DRAW) # GL_STATIC_DRAW - for inactive mesh
        shader.set_vertex_attribute('Position', 0)

        # Copy normals
        glBindBuffer(GL_ARRAY_BUFFER, self.VBO[1])
        glBufferData(GL_ARRAY_BUFFER, len(self.normals) * 4, self.normals, GL_DYNAMIC_DRAW)
        shader.set_vertex_attribute('Normal', 0)

        # TODO: set_vertex_attribute calls don't really make sense here - because we're
        # not rebuilding a mesh on a shader reload - so those attributes are never bound
        # on the new program?

        # TODO: Tangent, Binormal, Color, Texcoord0-7
        # TODO: Probably don't do per-mesh VAO. See: https://stackoverflow.com/a/18487155

        # Copy indices
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.EBO)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, len(self.indices) * 4, self.indices, GL_DYNAMIC_DRAW)

        # Cleanup, just so bad code elsewhere doesn't also write to this VAO
        glBindVertexArray(0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        self.indices_size = len(self.indices)

    def update(self, obj):
        """Update transformation info for this mesh"""
        self.model_matrix = obj.matrix_world

    def draw(self, shader: BaseShader):
        if self.is_dirty:
            with self.lock:
                self.rebuild_vbos(shader)
                self.is_dirty = False

        # print('draw VAO={} valid={}, VBO[0]={} valid={}, VBO[1]={} valid={}, EBO={} valid={}'.format(
        #     self.VAO,
        #     glIsBuffer(self.VAO),
        #     self.VBO[0],
        #     glIsBuffer(self.VBO[0]),
        #     self.VBO[1],
        #     glIsBuffer(self.VBO[1]),
        #     self.EBO,
        #     glIsBuffer(self.EBO),
        # ))

        glBindVertexArray(self.VAO)

        # If the shader includes a tessellation stage, we need to draw in patch mode
        if shader.has_tessellation:
            # glPatchParameteri(GL_PATCH_VERTICES, 3)
            # Not supported in bgi - but defaults to 3.
            glDrawElements(GL_PATCHES, self.indices_size, GL_UNSIGNED_INT, 0)
        else:
            glDrawElements(GL_TRIANGLES, self.indices_size, GL_UNSIGNED_INT, 0)

        glBindVertexArray(0)

class FooRenderEngine(bpy.types.RenderEngine):
    bl_idname = "foo_renderer"
    bl_label = "Foo Renderer"
    bl_use_preview = False

    # Enable an OpenGL context for the engine (2.91+ only)
    bl_use_gpu_context = True

    # Apply Blender's compositing on render results.
    # This enables the "Color Management" section of the scene settings
    bl_use_postprocess = True

    def __init__(self):
        """Called when a new render engine instance is created.

        Note that multiple instances can exist @ once, e.g. a viewport and final render
        """
        self.meshes = dict()

        self.light_direction = (0, 0, 1, 0)
        self.light_color = (1, 1, 1, 1)

        self.fallback_shader = FallbackShader()
        self.user_shader = UserShader()

    def __del__(self):
        """Clean up render engine data, e.g. stopping running render threads"""
        pass

    def render(self, depsgraph):
        """Handle final render (F12) and material preview window renders"""
        # If you want to support material preview windows you will
        # also need to set `bl_use_preview = True`
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
            mesh = Mesh(obj.name)
            rebuild_geometry = True
        else:
            mesh = self.meshes[obj.name]

        mesh.update(obj)

        # If modified - prep the mesh to be copied to the GPU next draw
        if rebuild_geometry:
            mesh.rebuild(obj.evaluated_get(depsgraph))

        self.updated_meshes[obj.name] = mesh

    def update_light(self, obj):
        """Update main (sun) light data for the next render"""
        light_type = obj.data.type

        direction = obj.matrix_world.to_quaternion() @ Vector((0, 0, 1))
        color = obj.data.color
        intensity = obj.data.foo.intensity

        self.light_direction = (direction[0], direction[1], direction[2], 0)
        self.light_color = (color[0], color[1], color[2], intensity)

    def check_shaders(self, context):
        """Check if we should reload the shader sources"""
        settings = context.scene.foo

        # Check for source file changes or other setting changes
        try:
            self.user_shader.update_settings(settings)
            settings.last_shader_error = self.user_shader.last_error
        except Exception as e:
            settings.last_shader_error = str(e)

    def view_draw(self, context, depsgraph):
        """Called whenever Blender redraws the 3D viewport.

        In 2.91+ this is also where you can safely interact
        with the GL context for this RenderEngine.
        """
        scene = depsgraph.scene
        region = context.region
        region3d = context.region_data
        settings = scene.foo

        glEnable(GL_BLEND)
        glBlendFunc(GL_ONE, GL_ONE_MINUS_SRC_ALPHA)

        self.bind_display_space_shader(scene)

        # Try to use the user shader. If we can't, use the fallback.
        shader = self.user_shader
        if not shader.bind():
            shader = self.fallback_shader
            shader.bind()

        # Set up MVP matrices
        shader.set_mat4("ViewMatrix", region3d.view_matrix.transposed())
        shader.set_mat4("ProjectionMatrix", region3d.window_matrix.transposed())
        shader.set_mat4("CameraMatrix", region3d.view_matrix.inverted().transposed())

        # Upload current lighting information
        shader.set_vec4("_MainLightDirection", self.light_direction)
        shader.set_vec4("_MainLightColor", self.light_color)
        shader.set_vec4("_AmbientColor", settings.ambient_color)

        # Upload other useful information
        shader.set_int("_Frame", context.scene.frame_current)

        glEnable(GL_DEPTH_TEST)

        # Clear background with the user's clear color
        clear_color = scene.foo.clear_color
        glClearColor(clear_color[0], clear_color[1], clear_color[2], 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        for mesh in self.meshes.values():
            mv = region3d.view_matrix @ mesh.model_matrix
            mvp = region3d.window_matrix @ mv

            # Set per-mesh uniforms
            shader.set_mat4("ModelMatrix", mesh.model_matrix.transposed())
            shader.set_mat4("ModelViewMatrix", mv.transposed())
            shader.set_mat4("ModelViewProjectionMatrix", mvp.transposed())

            # Draw the mesh itself
            mesh.draw(shader)

        shader.unbind()
        self.unbind_display_space_shader()

        glDisable(GL_BLEND)

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
        subtype='FILE_PATH'
        # update=force_shader_reload
    )

    frag_filename: StringProperty(
        name='Fragment Shader',
        description='Source file path',
        default='',
        subtype='FILE_PATH'
        # update=force_shader_reload
    )

    tesc_filename: StringProperty(
        name='Tess Control Shader',
        description='Source file path',
        default='',
        subtype='FILE_PATH'
        # update=force_shader_reload
    )

    tese_filename: StringProperty(
        name='Tess Evaluation Shader',
        description='Source file path',
        default='',
        subtype='FILE_PATH'
        # update=force_shader_reload
    )

    geom_filename: StringProperty(
        name='Geometry Shader',
        description='Source file path',
        default='',
        subtype='FILE_PATH'
        # update=force_shader_reload
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

    ambient_color: FloatVectorProperty(
        name='Ambient Color',
        subtype='COLOR',
        default=(0.008, 0.008, 0.008, 1),
        size=4,
        min=0.0, max=1.0,
        description='Ambient color of the scene'
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
        col.prop(settings, 'ambient_color')

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
    bl_label = 'Foo Light Settings'
    bl_context = 'data'

    @classmethod
    def poll(cls, context):
        return context.light and BasePanel.poll(context)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        light = context.light

        settings = context.light.foo

        col = layout.column(align=True)

        # Only a primary sun light is supported
        if light.type != 'SUN':
            col.label(text='Only Sun lights are supported by Foo')
            return

        col.prop(light, 'color')

        col.separator()
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
        'VIEWLAYER_PT_layer_passes',
        'RENDER_PT_freestyle',
        'RENDER_PT_simplify',
        'DATA_PT_vertex_colors',
        'DATA_PT_preview',
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
