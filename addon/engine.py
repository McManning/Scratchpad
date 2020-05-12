
import bpy
from bgl import *
# from mathutils import Vector, Matrix, Quaternion

from .lights import (
    MainLight,
    SpotLight,
    PointLight
)

from .renderables import (
    Mesh,
    Material
)

from .shaders.base import (
    Shader,
    LightData
)

from .shaders.fallback import FallbackShader
from .shaders.glsl import GLSLShader
from .shaders.ogsfx import OGSFXShader

from .properties import register_dynamic_property_group

class FooRenderEngine(bpy.types.RenderEngine):
    bl_idname = "foo_renderer"
    bl_label = "Foo Renderer"
    bl_use_preview = True

    def __init__(self):
        """Called when a new render engine instance is created. 

        Note that multiple instances can exist @ once, e.g. a viewport and final render
        """
        self.meshes = dict()
        self.lights = LightData()
        self.lights.main_light = MainLight()

        self.default_shader = FallbackShader()
        self.user_shader = GLSLShader()

        # Set the initial shader to the default until we load a user shader
        self.shader = self.default_shader

        try:
            self.default_shader.recompile()
        except Exception as e:
            # show_message('Failed to compile fallback shader. Check console', 'Compile Error', 'ERROR')
            print('--Failed to compile default shader--')
            print(e)
    
    # When the render engine instance is destroy, this is called. Clean up any
    # render engine data here, for example stopping running render threads.
    def __del__(self):
        pass

    def render(self, depsgraph):
        """Handle final render (F12) and material preview window renders"""
        pass
        # TODO: Implement. Should be the same as view_draw.

        # scene = depsgraph.scene
        # scale = scene.render.resolution_percentage / 100.0
        # self.size_x = int(scene.render.resolution_x * scale)
        # self.size_y = int(scene.render.resolution_y * scale)

        # # Fill the render result with a flat color. The framebuffer is
        # # defined as a list of pixels, each pixel itself being a list of
        # # R,G,B,A values.
        # if self.is_preview:
        #     color = [0.1, 0.2, 0.1, 1.0]
        # else:
        #     color = [0.2, 0.1, 0.1, 1.0]

        # pixel_count = self.size_x * self.size_y
        # rect = [color] * pixel_count

        # # Here we write the pixel values to the RenderResult
        # result = self.begin_result(0, 0, self.size_x, self.size_y)
        # layer = result.layers[0].passes["Combined"]
        # layer.rect = rect
        # self.end_result(result)

    def view_update(self, context, depsgraph):
        """Called when a scene or 3D viewport changes"""
        self.check_shaders(context)

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
                print('Unhandled scene object type', obj.type)
                
        self.meshes = self.updated_meshes
        self.lights.additional_lights = self.updated_additional_lights
    
    def update_mesh(self, obj, depsgraph):
        rebuild_geometry = obj.name in self.updated_geometries
        if obj.name not in self.meshes:
            mesh = Mesh()
            rebuild_geometry = True
            # print('Add mesh', mesh)
        else:
            mesh = self.meshes[obj.name]
            # print('Update mesh', mesh)

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
        self.lights.main_light.update(obj)

    def update_point_light(self, obj):
        if obj.name not in self.lights.additional_lights:
            light = PointLight()
            print('Add point light', light)
        else:
            light = self.lights.additional_lights[obj.name]
            print('Update point light', light)
        
        light.update(obj)
        self.updated_additional_lights[obj.name] = light
    
    def update_spot_light(self, obj):
        if obj.name not in self.lights.additional_lights:
            light = SpotLight()
            print('Add spot light', light)
        else:
            light = self.lights.additional_lights[obj.name]
            print('Update spot light', light)
        
        light.update(obj)
        self.updated_additional_lights[obj.name] = light
    
    def check_shaders(self, context):
        """Check if we should reload the shader sources"""
        settings = context.scene.foo
        
        if hasattr(context.scene, 'foo_shader_properties'):
            shader_properties = context.scene.foo_shader_properties
            self.user_shader.update_shader_properties(shader_properties)
            
        # Check for readable source files and changes
        try:
            self.user_shader.update_settings(settings)
            needs_recompile = self.user_shader.needs_recompile()
        except Exception as e:
            settings.last_shader_error = str(e)
            self.shader = self.default_shader
            return

        print('--- Force reload', settings.force_reload)
        print('--- Live reload', settings.live_reload)
        print('--- needs recompile', needs_recompile)
        
        # Trigger a recompile if we're forcing it or the files on disk
        # have been modified since the last render
        if settings.force_reload or (settings.live_reload and needs_recompile):
            settings.force_reload = False
            try:
                self.user_shader.recompile()
                settings.last_shader_error = ''
                self.shader = self.user_shader
                    
                # Load a new shader properties into context
                properties = self.user_shader.properties
                register_dynamic_property_group(
                    'foo_shader_properties', 
                    properties.definitions
                )
                
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
        
        # self.check_shader_reload(context)
        
        # viewport = [region.x, region.y, region.width, region.height]
        
        # view_matrix = region3d.view_matrix # transposed GL_MODELVIEW_MATRIX
        # view_matrix_inv = view_matrix.inverted()
        # cam_pos = view_matrix_inv * Vector((0.0, 0.0, 0.0))
        # cam_dir = (view_matrix_inv * Vector((0.0, 0.0, -1.0))) - cam_pos        
        
        self.bind_display_space_shader(scene)
        self.shader.bind()

        # TODO: Move this.
        self.shader.set_int("_Frame", scene.frame_current)
        
        self.shader.set_camera_matrices(
            region3d.view_matrix,
            region3d.window_matrix
        )

        self.shader.set_lights(self.lights)

        glEnable(GL_DEPTH_TEST)
        
        # glEnable(GL_BLEND)
        # glBlendFunc(GL_ONE, GL_ONE_MINUS_SRC_ALPHA)

        clear_color = scene.foo.clear_color
        glClearColor(clear_color[0], clear_color[1], clear_color[2], 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        for mesh in self.meshes.values():
            self.shader.set_object_matrices(mesh.model_matrix)
            mesh.draw(self.shader)

        self.shader.unbind()
        self.unbind_display_space_shader()

        # glDisable(GL_BLEND)

    def refresh_all_buffers(self):
        """Force *all* GPU buffers to reload.
        
        This can trigger when shaders are recompiled
        """
        for mesh in self.meshes.values():
            mesh.dirty()


classes = (
    FooRenderEngine,
)

# # RenderEngines also need to tell UI Panels that they are compatible with.
# # We recommend to enable all panels marked as BLENDER_RENDER, and then
# # exclude any panels that are replaced by custom panels registered by the
# # render engine, or that are not supported.
# def get_panels():
#     exclude_panels = {
#         'VIEWLAYER_PT_filter',
#         'VIEWLAYER_PT_layer_passes',
    
#         # From cycles:
#         # https://github.com/sobotka/blender/blob/f6f4ab3ebfe4772dcc0a47a2f54121017d5181d1/intern/cycles/blender/addon/ui.py#L1341
#         'DATA_PT_light',
#         'DATA_PT_preview',
#         'DATA_PT_spot',
#     }

#     panels = []
#     for panel in bpy.types.Panel.__subclasses__():
#         if hasattr(panel, 'COMPAT_ENGINES') and 'BLENDER_RENDER' in panel.COMPAT_ENGINES:
#             if panel.__name__ not in exclude_panels:
#                 panels.append(panel)

#     return panels

# def register():
#     bpy.utils.register_class(FooRenderEngine)

#     for panel in get_panels():
#         panel.COMPAT_ENGINES.add(FooRenderEngine.bl_idname)

# def unregister():
#     bpy.utils.unregister_class(FooRenderEngine)

#     for panel in get_panels():
#         if FooRenderEngine.bl_idname in panel.COMPAT_ENGINES:
#             panel.COMPAT_ENGINES.remove(FooRenderEngine.bl_idname)
