
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

DEFAULT_SHADER_PATH = 'D:\\Blender\\GLSLRenderEngine\\shaders\\'

# Fallback shaders if custom shader compilation fails
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

    vec4 inner = vec4(0.5, 0.1, 0.1, 1);
    vec4 outer = vec4(0.2, 0, 0, 1);

    FragColor = mix(outer, inner, ndl);
}
'''

# Skip geometry shader for fallback
GS_FALLBACK = None


def show_message(message = "", title = "Message Box", icon = 'INFO'):
    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)

class CompileError(Exception):
    pass
    
class LinkError(Exception):
    pass

def compile_shader(src: str, type_flag):
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
    
    # Reconstruct byte data into a string
    err = ''.join(chr(infoLog[i]) for i in range(length[0]))
    raise CompileError(err)
    
class Shader:
    """Encapsulate shader compilation and configuration"""
    def __init__(self):
        self.program = None
        self.is_fallback = False
        self.prev_mtimes = []

    def compile_from_sources(self, vert: str, frag: str, geom: str = None):
        print('Compiling shader from', vert, frag, geom)
        
        self.is_fallback = False
        self.vert = vert 
        self.frag = frag 
        self.geom = geom
        self.recompile()

    def compile_from_fallback(self):
        if self.is_fallback: return # Already compiled

        self.is_fallback = True
        self.prev_mtimes = []
        self.compile_from_strings(VS_FALLBACK, FS_FALLBACK, GS_FALLBACK)

    def mtimes(self):
        """Aggregate file modication times from sources"""
        if self.is_fallback: return []
    
        mtimes = [
            os.stat(self.vert).st_mtime,
            os.stat(self.frag).st_mtime
        ]

        if self.geom:
            mtimes.append(os.stat(self.geom).st_mtime)
        
        return mtimes

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
                
        self.compile_from_strings(vs, fs, gs)
        self.prev_mtimes = self.mtimes()

    def compile_from_strings(self, vs: str, fs: str, gs: str = None):
        vertShader = compile_shader(vs, GL_VERTEX_SHADER)
        fragShader = compile_shader(fs, GL_FRAGMENT_SHADER)
        
        geomShader = None
        if gs: geomShader = compile_shader(gs, GL_GEOMETRY_SHADER)

        program = glCreateProgram()
        glAttachShader(program, vertShader)
        glAttachShader(program, fragShader)
        if gs: glAttachShader(program, geomShader)
            
        glLinkProgram(program)

        # Cleanup shaders
        glDeleteShader(vertShader)
        glDeleteShader(fragShader)
        if gs: glDeleteShader(geomShader)

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
        print('Refresh buffers', self)
        
        
        # mesh = self.obj.data
        mesh = eval_obj.to_mesh()

        # Refresh triangles on the mesh
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
        self.obj = obj
        self.model_matrix = obj.matrix_world

    def dirty(self):
        """Dirty the mesh - causing all GPU buffers to reload"""
        self.is_dirty = True

    def draw(self, shader: Shader):
        if self.is_dirty:
            self.rebuild_vbos(shader)
            self.is_dirty = False

        # Texture stuff go here.
        
        glBindVertexArray(self.VAO)
        glDrawElements(GL_TRIANGLES, self.indices_size, GL_UNSIGNED_INT, 0)
        glBindVertexArray(0)


class MainLight:
    """Primary directional light"""
    def __init__(self):
        # self.position = (0, 0, 0, 1)
        self.direction = (0, 0, 1, 0)
        self.color = (1, 1, 1, 1)

    def update(self, obj):
        settings = obj.data.foo
        
        # Object data
        direction = obj.matrix_world.to_quaternion() @ Vector((0, 0, 1))
        color = obj.data.color

        self.direction = (direction[0], direction[1], direction[2], 0)
        self.color = (color[0], color[1], color[2], settings.intensity)


class SpotLight:
    def __init__(self):
        self.position = (0, 0, 0, 1)
        self.direction = (0, 1, 0, 0)
        self.color = (1, 1, 1, 1)
        self.attenuation = (0, 1, 0, 1)

    def update(self, obj):
        settings = obj.data.foo
        
        # Object data
        position = obj.matrix_world.to_translation()
        direction = obj.matrix_world.to_quaternion() @ Vector((0, 0, 1))
        color = obj.data.color

        # Convert spot size and blend (factor) to inner/outer angles
        spot_angle = obj.data.spot_size
        inner_spot_angle = obj.data.spot_size * (1.0 - obj.data.spot_blend)

        # Vec4s that match Unity's URP for forward lights
        self.position = (position[0], position[1], position[2], 1.0)
        self.direction = (direction[0], direction[1], direction[2], 0)
        self.color = (color[0], color[1], color[2], settings.intensity)
        
        # Range and attenuation settings
        light_range_sqr = settings.distance * settings.distance # TODO: Should be scale or something, so it matches the gizmo 
        fade_start_distance_sqr = 0.8 * 0.8 * light_range_sqr
        fade_range_sqr = fade_start_distance_sqr - light_range_sqr

        self.attenuation = (1.0 / light_range_sqr, -light_range_sqr / fade_range_sqr, 0, 1)

        light_range_sqr = settings.distance * settings.distance # TODO: Should be scale or something, so it matches the gizmo 
        fade_start_distance_sqr = 0.8 * 0.8 * light_range_sqr
        fade_range_sqr = fade_start_distance_sqr - light_range_sqr

        cos_outer_angle = cos(spot_angle * 0.5)
        cos_inner_angle = cos(inner_spot_angle * 0.5)
        smooth_angle_range = max(0.001, cos_inner_angle - cos_outer_angle)
        inv_angle_range = 1.0 / smooth_angle_range
        add = -cos_outer_angle * inv_angle_range

        self.attenuation = (1.0 / light_range_sqr, -light_range_sqr / fade_range_sqr, inv_angle_range, add)


class PointLight:
    def __init__(self):
        self.position = (0, 0, 0, 1)
        self.direction = (0, 1, 0, 0)
        self.color = (1, 1, 1, 1)
        self.attenuation = (0, 1, 0, 1)

    def update(self, obj):
        settings = obj.data.foo
        
        # Object data
        position = obj.matrix_world.to_translation()
        direction = obj.matrix_world.to_quaternion() @ Vector((0, 0, 1))
        color = obj.data.color
        
        # Vec4s that match Unity's URP for forward lights
        self.position = (position[0], position[1], position[2], 1.0)
        self.direction = (direction[0], direction[1], direction[2], 0)
        self.color = (color[0], color[1], color[2], settings.intensity)
        
        # Range and attenuation settings
        light_range_sqr = settings.distance * settings.distance
        fade_start_distance_sqr = 0.8 * 0.8 * light_range_sqr
        fade_range_sqr = fade_start_distance_sqr - light_range_sqr

        self.attenuation = (1.0 / light_range_sqr, -light_range_sqr / fade_range_sqr, 0, 1)


class Material:
    def bind(self):
        pass

    
class CustomRenderEngine(bpy.types.RenderEngine):
    bl_idname = "foo_renderer"
    bl_label = "Foo Renderer"
    bl_use_preview = True

    def __init__(self):
        """Called when a new render engine instance is created. 

        Note that multiple instances can exist @ once, e.g. a viewport and final render
        """
        self.scene_data = None
        self.draw_data = None
        
        self.meshes = dict()
        self.main_light = MainLight()
        self.additional_lights = dict()

        self.shader = Shader()

        self.reload_counter = 0

        try:
            self.shader.compile_from_fallback()
        except Exception as e:
            show_message('Failed to compile fallback shader. Check console', 'Compile Error', 'ERROR')
            print('--Failed to compile fallback shader--')
            print(e)
    
    # When the render engine instance is destroy, this is called. Clean up any
    # render engine data here, for example stopping running render threads.
    def __del__(self):
        pass

    def render(self, depsgraph):
        """Handle final render (F12) and material preview window renders"""
        if not self.shader: return

        scene = depsgraph.scene
        scale = scene.render.resolution_percentage / 100.0
        self.size_x = int(scene.render.resolution_x * scale)
        self.size_y = int(scene.render.resolution_y * scale)

        # Fill the render result with a flat color. The framebuffer is
        # defined as a list of pixels, each pixel itself being a list of
        # R,G,B,A values.
        if self.is_preview:
            color = [0.1, 0.2, 0.1, 1.0]
        else:
            color = [0.2, 0.1, 0.1, 1.0]

        pixel_count = self.size_x * self.size_y
        rect = [color] * pixel_count

        # Here we write the pixel values to the RenderResult
        result = self.begin_result(0, 0, self.size_x, self.size_y)
        layer = result.layers[0].passes["Combined"]
        layer.rect = rect
        self.end_result(result)

    def view_update(self, context, depsgraph):
        """Called when a scene or 3D viewport changes"""
        if not self.shader: return 

        region = context.region
        view3d = context.space_data
        scene = depsgraph.scene

        self.updated_meshes = dict()
        self.updated_additional_lights = dict()
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
            elif obj.type == 'LIGHT':
                self.update_light(obj)
            else:
                print(obj.type)
                
        self.meshes = self.updated_meshes
        self.additional_lights = self.updated_additional_lights
    
    def update_mesh(self, obj, depsgraph):
        rebuild_geometry = obj.name in self.updated_geometries
        if obj.name not in self.meshes:
            mesh = Mesh()
            rebuild_geometry = True
            print('Add mesh', mesh)
        else:
            mesh = self.meshes[obj.name]
            print('Update mesh', mesh)

        mesh.update(obj)

        # Copy updated vertex data to the GPU, IFF changed
        if rebuild_geometry:
            mesh.rebuild(obj.evaluated_get(depsgraph), self.shader)
        
        self.updated_meshes[obj.name] = mesh
        
    def update_light(self, obj):
        light_type = obj.data.type 

        if light_type == 'SUN':
            self.update_main_light(obj)
        elif light_type == 'POINT':
            self.update_point_light(obj)
        elif light_type == 'SPOT':
            self.update_spot_light(obj)
        # AREA not supported

    def update_main_light(self, obj):
        self.main_light.update(obj)

    def update_point_light(self, obj):
        if obj.name not in self.additional_lights:
            light = PointLight()
            print('Add point light', light)
        else:
            light = self.additional_lights[obj.name]
            print('Update point light', light)
        
        light.update(obj)
        self.updated_additional_lights[obj.name] = light
    
    def update_spot_light(self, obj):
        if obj.name not in self.additional_lights:
            light = SpotLight()
            print('Add spot light', light)
        else:
            light = self.additional_lights[obj.name]
            print('Update spot light', light)
        
        light.update(obj)
        self.updated_additional_lights[obj.name] = light
    
    def check_shader_reload(self, context):
        """Check if we should reload the shader sources"""
        settings = context.scene.foo

        # Workaround since I can't write back to settings during this phase
        force_reload = self.reload_counter != settings.reload_counter
        
        # Trigger a recompile if we're forcing it or the files on disk
        # have been modified since the last render
        if force_reload or (settings.live_reload and self.shader.mtimes_changed()):
            try:
                self.shader.compile_from_sources(
                    settings.vert_filename,
                    settings.frag_filename,
                    settings.geom_filename
                )
                
                # Unflag reload IFF it successfully compiled
                self.reload_counter = settings.reload_counter
                self.last_shader_error = None
            except Exception as e:
                show_message('Failed to compile shader. Check console', 'Compile Error', 'ERROR')
                print('COMPILE ERROR', type(e))
                print(e)
                self.last_shader_error = e
                self.shader.compile_from_fallback()

    def upload_lighting(self):
        """Copy lighting information into shader uniforms
        
        This is inspired by Unity's LWRP where there is a main directional light
        and a number of secondary lights packed into an array buffer. 

        This particular implementation doesn't account for anything advanced
        like shadows, light cookies, etc. 
        """
        limit = 16

        positions = [0] * (limit * 4)
        directions = [0] * (limit * 4)
        colors = [0] * (limit * 4)
        attenuations = [0] * (limit * 4)

        # Feed lights into buffers
        i = 0
        for light in self.additional_lights.values():
            # print('Light', i)
            v = light.position
            # print('    Position', v)
            positions[i * 4] = v[0]
            positions[i * 4 + 1] = v[1]
            positions[i * 4 + 2] = v[2]
            positions[i * 4 + 3] = v[3]
            
            v = light.direction
            # print('    Direction', v)
            directions[i * 4] = v[0]
            directions[i * 4 + 1] = v[1]
            directions[i * 4 + 2] = v[2]
            directions[i * 4 + 3] = v[3]

            v = light.color
            # print('    Color', v)
            colors[i * 4] = v[0]
            colors[i * 4 + 1] = v[1]
            colors[i * 4 + 2] = v[2]
            colors[i * 4 + 3] = v[3]

            v = light.attenuation
            # print('    Attenuation', v)
            attenuations[i * 4] = v[0]
            attenuations[i * 4 + 1] = v[1]
            attenuations[i * 4 + 2] = v[2]
            attenuations[i * 4 + 3] = v[3]

            i += 1
        
        if self.main_light:
            self.shader.set_vec4("_MainLightDirection", self.main_light.direction)
            self.shader.set_vec4("_MainLightColor", self.main_light.color)

        self.shader.set_int("_AdditionalLightsCount", i)
        self.shader.set_vec4_array("_AdditionalLightsPosition", positions)
        self.shader.set_vec4_array("_AdditionalLightsColor", colors)
        self.shader.set_vec4_array("_AdditionalLightsSpotDir", directions)
        self.shader.set_vec4_array("_AdditionalLightsAttenuation", attenuations)

    def view_draw(self, context, depsgraph):
        """Called whenever Blender redraws the 3D viewport"""
        if not self.shader: return 
        
        scene = depsgraph.scene
        region = context.region
        region3d = context.region_data
        settings = scene.foo
        
        # self.check_shader_reload(context)
        
        self.bind_display_space_shader(scene)
        self.shader.bind()
        
        # viewport = [region.x, region.y, region.width, region.height]
        
        # view_matrix = region3d.view_matrix # transposed GL_MODELVIEW_MATRIX
        # view_matrix_inv = view_matrix.inverted()
        # cam_pos = view_matrix_inv * Vector((0.0, 0.0, 0.0))
        # cam_dir = (view_matrix_inv * Vector((0.0, 0.0, -1.0))) - cam_pos        
        
        # Set up MVP matrices
        self.shader.set_mat4("ViewMatrix", region3d.view_matrix.transposed())
        self.shader.set_mat4("ProjectionMatrix", region3d.window_matrix.transposed())
        self.shader.set_mat4("CameraMatrix", region3d.view_matrix.inverted().transposed())

        # Upload current light information
        self.upload_lighting()
        self.shader.set_vec3("_AmbientColor", settings.ambient_color)

        glEnable(GL_DEPTH_TEST)
        
        # glEnable(GL_BLEND)
        # glBlendFunc(GL_ONE, GL_ONE_MINUS_SRC_ALPHA)

        r, g, b = scene.foo.clear_color
        glClearColor(r, g, b, 1.0)
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
        """Force *all* GPU buffers to reload.
        
        This can trigger when shaders are recompiled
        """
        for mesh in self.meshes.values():
            mesh.dirty()

def force_shader_reload(self, context):
    """Callback when any of the shader filenames change in FooRenderSettings"""
    context.scene.foo.reload_counter += 1

class FooRendererSettings(PropertyGroup):
    vert_filename: StringProperty(
        name='Vertex Shader',
        description='Source file path',
        default='D:\\Blender\\default.vert',
        subtype='FILE_PATH',
        update=force_shader_reload
    )
    
    frag_filename: StringProperty(
        name='Fragment Shader',
        description='Source file path',
        default='D:\\Blender\\default.frag',
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
    
    tesc_filename: StringProperty(
        name='Tess Control Shader',
        description='Source file path',
        default='',
        subtype='FILE_PATH',
        update=force_shader_reload
    )
    
    # tesc, tese, comp, etc etc. 
    
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
        description='color picker'
    )
    
    ambient_color: FloatVectorProperty(
        name='Ambient Color',
        subtype='COLOR',
        default=(0.15, 0.15, 0.15),
        min=0.0, max=1.0,
        description='color picker'
    )
    
    reload_counter: IntProperty(
        name='Reload Counter'
    )
    
    @classmethod
    def register(cls):
        bpy.types.Scene.foo = PointerProperty(
            name="Foo Render Settings",
            description="something about it",
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
            name="Foo Light Settings",
            description="something about it",
            type=cls
        )
    
    @classmethod
    def unregister(cls):
        del bpy.types.Light.foo
    
    
class BaseFooRendererPanel(Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'
    COMPAT_ENGINES = {CustomRenderEngine.bl_idname}

    @classmethod
    def poll(cls, context):
        return context.engine in cls.COMPAT_ENGINES

class ReloadSourcesOperator(bpy.types.Operator):
    bl_idname = 'foo.reload_sources'
    bl_label = 'Reload Shader Sources'
    # bl_options = {'INTERNAL'}

    def invoke(self, context, event):
        print('call invoke')
        context.scene.foo.reload_counter += 1
        
        return {'FINISHED'}


class FOO_RENDER_PT_settings(BaseFooRendererPanel):
    """Parent panel for renderer settings"""
    bl_label = 'Foo Renderer Settings'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        settings = context.scene.foo
        # No controls at top level.
        
class FOO_RENDER_PT_settings_viewport(BaseFooRendererPanel):
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
    

class FOO_RENDER_PT_settings_sources(BaseFooRendererPanel):
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
        col.prop(settings, 'geom_filename')
        # col.prop(settings, "tesc_filename", text="Tess Control Shader")
        
        layout.separator()
         
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(settings, "live_reload", text="Live Reload")
        row.operator("foo.reload_sources", text = "Reload")
        
        col = layout.column(align=True)
        col.alignment = 'RIGHT'
        col.label(text="Last reloaded N minutes ago")
        
        # Alert message on compile error
        
        col = layout.column(align=True)
        col.alert = True
        col.label(text='Compilation error: message goes here', icon='ERROR')
        # TODO: Blender doesn't have text wrapping for this to be nice
        
        
class FOO_LIGHT_PT_light(BaseFooRendererPanel):
    bl_label = 'Light'
    bl_context = 'data'
    
    @classmethod
    def poll(cls, context):
        return context.light and BaseFooRendererPanel.poll(context)

    def draw(self, context):
        layout = self.layout
        light = context.light
        
        settings = context.light.foo
        
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
        
        if light.type == 'SPOT':
            col.prop(light, 'spot_size')
            col.prop(light, 'spot_blend')
            

            
# RenderEngines also need to tell UI Panels that they are compatible with.
# We recommend to enable all panels marked as BLENDER_RENDER, and then
# exclude any panels that are replaced by custom panels registered by the
# render engine, or that are not supported.
def get_panels():
    exclude_panels = {
        'VIEWLAYER_PT_filter',
        'VIEWLAYER_PT_layer_passes',
    
        # From cycles:
        # https://github.com/sobotka/blender/blob/f6f4ab3ebfe4772dcc0a47a2f54121017d5181d1/intern/cycles/blender/addon/ui.py#L1341
        'DATA_PT_light',
        'DATA_PT_preview',
        'DATA_PT_spot',
    }

    panels = []
    for panel in bpy.types.Panel.__subclasses__():
        if hasattr(panel, 'COMPAT_ENGINES') and 'BLENDER_RENDER' in panel.COMPAT_ENGINES:
            if panel.__name__ not in exclude_panels:
                panels.append(panel)

    return panels


# Classes to (un)register as part of this addon
CLASSLIST = (
    CustomRenderEngine,
    
    # Operators
    ReloadSourcesOperator,
    
    # Settings
    FooRendererSettings,
    FooLightSettings,
    
    # Panels
    FOO_RENDER_PT_settings,
    FOO_RENDER_PT_settings_viewport,
    FOO_RENDER_PT_settings_sources,
    FOO_LIGHT_PT_light
)

def register():
    for cls in CLASSLIST:
        bpy.utils.register_class(cls)

    for panel in get_panels():
        panel.COMPAT_ENGINES.add(CustomRenderEngine.bl_idname)


def unregister():
    for cls in CLASSLIST:
        bpy.utils.unregister_class(cls)

    for panel in get_panels():
        if 'FOO' in panel.COMPAT_ENGINES:
            panel.COMPAT_ENGINES.remove(CustomRenderEngine.bl_idname)


if __name__ == "__main__":
    register()
