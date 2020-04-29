
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

from .shader import Shader

class FooRenderEngine(bpy.types.RenderEngine):
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

        self.default_shader = Shader()
        self.user_shader = Shader()

        # Set the initial shader to the default until we load a user shader
        self.shader = self.default_shader

        try:
            self.default_shader.compile_from_fallback()
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
        if not self.shader: return

        # TODO: Implement

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
        self.additional_lights = self.updated_additional_lights
    
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
    
    def check_shaders(self, context):
        """Check if we should reload the shader sources"""
        settings = context.scene.foo

        self.user_shader.set_sources(
            settings.vert_filename,
            settings.frag_filename,
            settings.geom_filename
        )
        
        # Check for readable source files and changes
        try:
            has_user_shader_changes = self.user_shader.mtimes_changed()
        except Exception as e:
            settings.last_shader_error = str(e)
            self.shader = self.default_shader
            return

        print('--- Force reload', settings.force_reload)
        print('--- Live reload', settings.live_reload)
        print('--- has changes', has_user_shader_changes)
        
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
