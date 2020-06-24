
import bpy
from bgl import *
# from mathutils import Vector, Matrix, Quaternion

from .lights import (
    SceneLighting,
    MainLight,
    SpotLight,
    PointLight
)

from .renderables import (
    Mesh,
    Material
)

from .shaders.fallback import FallbackShader
from .shaders import SUPPORTED_SHADERS 

from .properties import (
    register_dynamic_property_group, 
    unregister_dynamic_property_group,
    BaseDynamicMaterialSettings, 
    BaseDynamicRendererSettings
)

class FooRenderEngine(bpy.types.RenderEngine):
    bl_idname = "foo_renderer"
    bl_label = "Foo Renderer"
    bl_use_preview = True

    def __init__(self):
        """Called when a new render engine instance is created. 

        Note that multiple instances can exist @ once, e.g. a viewport and final render
        """
        self.meshes = dict()
        self.lighting = SceneLighting()
        self.lighting.main_light = MainLight()

        self.default_shader = FallbackShader()
        self.user_shader = None

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
        # TODO: Implement? Should be the same as view_draw.
        # Not sure what the use case for this is - since this is a 
        # realtime viewport renderer. Material preview windows maybe?

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
        self.update_shaders(context)

        region = context.region
        view3d = context.space_data
        scene = depsgraph.scene

        self.updated_meshes = dict()
        self.updated_additional_lights = dict()
        self.updated_geometries = []
        
        # Check for any updated mesh geometry to rebuild GPU buffers
        # Note that (de)selecting components still counts as updating geometry. 
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
            # else:
            #     print('Unhandled scene object type', obj.type)
                
        self.meshes = self.updated_meshes
        self.lighting.ambient_color = context.scene.foo.ambient_color
        self.lighting.additional_lights = self.updated_additional_lights
    
    def update_mesh(self, obj, depsgraph):
        rebuild_geometry = obj.name in self.updated_geometries
        if obj.name not in self.meshes:
            mesh = Mesh()
            rebuild_geometry = True
        else:
            mesh = self.meshes[obj.name]

        mesh.update(obj)

        # Copy updated vertex data to the GPU, if modified since last render
        if rebuild_geometry:
            mesh.rebuild(obj.evaluated_get(depsgraph))
        
        self.updated_meshes[obj.name] = mesh
        
    def update_light(self, obj):
        """Track an updated light in the scene
        
        Parameters:
            obj (bpy.types.Object)
        """
        light_type = obj.data.type 

        if light_type == 'SUN':
            self.update_main_light(obj)
        elif light_type == 'POINT':
            self.update_point_light(obj)
        elif light_type == 'SPOT':
            self.update_spot_light(obj)
        # TODO: AREA
        
    def update_main_light(self, obj):
        """Track an updated directional light in the scene
        
        Parameters:
            obj (bpy.types.Object)
        """
        self.lighting.main_light.update(obj)

    def update_point_light(self, obj):
        """Track an updated point light in the scene
        
        Parameters:
            obj (bpy.types.Object)
        """
        if obj.name not in self.lighting.additional_lights:
            light = PointLight()
        else:
            light = self.lighting.additional_lights[obj.name]
        
        light.update(obj)
        self.updated_additional_lights[obj.name] = light
    
    def update_spot_light(self, obj):
        """Track an updated spot light in the scene
        
        Parameters:
            obj (bpy.types.Object)
        """
        if obj.name not in self.lighting.additional_lights:
            light = SpotLight()
        else:
            light = self.lighting.additional_lights[obj.name]
        
        light.update(obj)
        self.updated_additional_lights[obj.name] = light
    
    def update_shaders(self, context):
        """Send updated user data to shaders and check if we should hot reload sources"""
        settings = context.scene.foo

        # Check if the selected shader has changed from what's  
        # currently loaded and if so, instantiate a new one
        for shader in SUPPORTED_SHADERS:
            name = shader[0]
            shader_impl = shader[1]
            if settings.loader == name and not isinstance(self.user_shader, shader_impl):
                self.user_shader = shader_impl()
                settings.last_shader_error = ''

                print('Swap dynamic properties')
                # On shader change, update the dynamic renderer properties to match
                unregister_dynamic_property_group('FooRendererDynamicProperties')
                props = self.user_shader.get_renderer_properties()
                if props:
                    register_dynamic_property_group(
                        'FooRendererDynamicProperties', 
                        BaseDynamicRendererSettings,
                        props.definitions
                    )

        # Check for readable source files and changes
        try:
            # Push current dynamic properties from the UI to the shader
            if hasattr(context.scene, 'foo_dynamic'):
                props = context.scene.foo_dynamic
                self.user_shader.update_renderer_properties(props)
                
            needs_recompile = self.user_shader.needs_recompile()
        except Exception as e:
            settings.last_shader_error = str(e)
            self.shader = self.default_shader
            return

        # print('--- Force reload', settings.force_reload)
        # print('--- Live reload', settings.live_reload)
        # print('--- needs recompile', needs_recompile)
        
        # Trigger a recompile if we're forcing it or the files on disk
        # have been modified since the last render
        if settings.force_reload or (settings.live_reload and needs_recompile):
            settings.force_reload = False
            try:
                self.user_shader.recompile()
                settings.last_shader_error = ''
                self.shader = self.user_shader
                
                # Load new dynamic material properties into context
                unregister_dynamic_property_group('FooMaterialDynamicProperties')
                props = self.user_shader.get_material_properties()
                if props:
                    register_dynamic_property_group(
                        'FooMaterialDynamicProperties', 
                        BaseDynamicMaterialSettings,
                        props.definitions
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

        self.shader.set_lighting(self.lighting)

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


classes = (
    FooRenderEngine,
)
