
import uuid
from collections import OrderedDict
import bpy
# from mathutils import Vector, Matrix, Quaternion

from .driver import (
    Graphics,
    CommandBuffer,
)

from .lights import (
    MainLight,
    SpotLight,
    PointLight
)

from .render_data import (
    RenderData
)

from .renderables import (
    ScratchpadMaterial,
    ScratchpadMesh
)

from .properties import (
    register_dynamic_property_group, 
    unregister_dynamic_property_group,
    BaseDynamicMaterialProperties
)

from .passes import (
    MainLightShadowCasterPass,
    AdditionalLightsShadowCasterPass,
    DrawObjectsPass
)

from shaders.fallback import FallbackShader
from shaders import SUPPORTED_SHADERS 

from libs.debug import debug
from libs.registry import autoregister

def sort_by_draw_order(arr):
    """Sort a list of ScratchpadMaterial instances by Scratchpad draw priority
    
    Parameters:
        arr ({ ScratchpadMaterial, list(Renderable) }): Dictionary mapping a material     
                                                        to Renderables that use it
    
    Returns:
        list(ScratchpadMaterial)
    """
    return OrderedDict(sorted(arr.items(), key=lambda m: m[0].material.scratchpad.priority))

def generate_unique_key() -> str:
    return 'scratchpad_dynamic_' + uuid.uuid4().hex

@autoregister
class ScratchpadRenderEngine(bpy.types.RenderEngine):
    bl_idname = "scratchpad_renderer"
    bl_label = "Scratchpad"
    bl_use_preview = True

    # Statically available instance for use in render passes/etc 
    fallback_shader = FallbackShader()

    # Panels that we don't register this engine with
    exclude_panels = {
        'VIEWLAYER_PT_filter',
        'VIEWLAYER_PT_layer_passes',
        'RENDER_PT_freestyle',
        'RENDER_PT_simplify',
        'DATA_PT_vertex_colors', # TODO: Support.
        'DATA_PT_preview', # TODO: Reimplement once preview viewports can be supported
        
    }

    def __init__(self):
        """Called when a new render engine instance is created. 

        Note that multiple instances can exist @ once, e.g. a viewport and final render
        """
        self.meshes = dict()
        self.materials = dict() # Material -> ScratchpadMaterial cache

        self.render_data = RenderData()

        self.passes = [
            MainLightShadowCasterPass(),
            AdditionalLightsShadowCasterPass(),
            DrawObjectsPass()
        ]

        self.setup_passes()

    # When the render engine instance is destroy, this is called. Clean up any
    # render engine data here, for example stopping running render threads.
    def __del__(self):
        self.cleanup_passes()
        pass

    def setup_passes(self):
        """Execute setup() on all registered render passes"""
        for p in self.passes:
            p.setup()

    def cleanup_passes(self):
        """Execute cleanup() on all registered render passes"""
        for p in self.passes:
            p.cleanup()

    def configure_passes(self):
        """Execute configure() on all registered render passes"""
        # TODO: Configure with what? Registered dynamic properties per-pass?
        pass
        # for p in self.passes:
        #     p.configure(???)

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
        # region = context.region
        # view3d = context.space_data
        scene = depsgraph.scene

        # self.updated_meshes = dict()
        self.updated_renderables = dict()
        self.updated_materials = dict() # bpy.types.Material -> ScratchpadMaterial
        self.updated_additional_lights = dict()
        self.updated_geometries = []

        # Check for any updated mesh geometry to rebuild GPU buffers
        # Note that (de)selecting components still counts as updating geometry. 
        for update in depsgraph.updates:
            name = update.id.name
            if type(update.id) == bpy.types.Object:
                if update.is_updated_geometry: # and name in self.meshes:
                    self.updated_geometries.append(name)
        
        # Aggregate everything visible in the scene that we care about
        # and update meshes, lighting, materials, etc.
        for obj in scene.objects:
            if not obj.visible_get():
                continue
            
            if obj.type == 'MESH':
                self.update_mesh(obj, depsgraph)
            elif obj.type == 'LIGHT':
                self.update_light(obj)
            else:
                debug('Unhandled scene object type', obj.type)
        
        # Replace old aggregates of tracked scene data
        self.render_data.renderables = sort_by_draw_order(self.updated_renderables)
        self.render_data.lights.additional_lights = self.updated_additional_lights

        # Drop any materials no longer used
        self.materials = self.updated_materials

    def update_mesh(self, obj, depsgraph):
        """Track a mesh still used in the scene and updated geometry on the GPU if needed
        
        Parameters:
            obj (bpy.types.Object):             Object containing mesh data to read
            depsgraph (bpy.types.Depsgraph):    Dependency graph to use for generating a final mesh
        """
        rebuild_geometry = obj.name in self.updated_geometries
        
        # TODO: This isn't pruning deleted meshes from the list. 
        if obj.data not in self.meshes:
            mesh = ScratchpadMesh()
            self.meshes[obj.data] = mesh
            rebuild_geometry = True
        else:
            mesh = self.meshes[obj.data]

        mesh.update(obj)

        # Propagate an update to every attached material as well
        for mat in obj.data.materials:
            self.update_material(mat, mesh)

        # Copy updated vertex data to the GPU, if modified since last render
        if rebuild_geometry:
            mesh.rebuild(obj.evaluated_get(depsgraph))

    def update_material(self, mat, obj):
        """Track a material still used by an object in the scene

        Parameters:
            mat (bpy.types.Material)  
            obj (Renderable):           Renderable that uses the material
        """
        # Make sure there's a ScratchpadMaterial
        if mat not in self.materials:
            sm = ScratchpadMaterial()
            sm.material = mat
        else:
            sm = self.materials[mat]

        # Aggregate Renderables under the ScratchpadMaterial
        # In a perfect world, we'd iterate polygons and aggregate what specific
        # polygons are using what materials. But that's too slow to be practical.
        if sm not in self.updated_renderables:
            self.updated_renderables[sm] = [obj] 
        else:
            self.updated_renderables[sm].append(obj)

        # On first update this frame - check shaders.
        if mat not in self.updated_materials:
            self.update_material_shader(sm)
            self.updated_materials[mat] = sm

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
        self.render_data.lighting.main_light.update(obj)

    def update_point_light(self, obj):
        """Track an updated point light in the scene
        
        Parameters:
            obj (bpy.types.Object)
        """
        additional_lights = self.render_data.lights.additional_lights
        if obj.name not in additional_lights:
            light = PointLight()
        else:
            light = additional_lights[obj.name]
        
        light.update(obj)
        self.updated_additional_lights[obj.name] = light
    
    def update_spot_light(self, obj):
        """Track an updated spot light in the scene
        
        Parameters:
            obj (bpy.types.Object)
        """
        additional_lights = self.render_data.lights.additional_lights
        if obj.name not in additional_lights:
            light = SpotLight()
        else:
            light = additional_lights[obj.name]
        
        light.update(obj)
        self.updated_additional_lights[obj.name] = light
    
    def update_material_shader(self, mat):
        """ Send updated user data to the shader attached to     
            the material and check if we should hot reload sources

        Parameters:
            mat (ScratchpadMaterial): Parent material of the shader
        """
        # scene_settings = context.scene.scratchpad # TODO: Unused. Needed anymore?
        settings = mat.material.scratchpad
        active_shader = mat.shader
        
        # Instantiate unique class keys for this material instance, if not already
        shader_group_key = settings.dynamic_shader_property_group_key
        if not shader_group_key:
            shader_group_key = generate_unique_key()
            settings.dynamic_shader_property_group_key = shader_group_key
        
        material_group_key = settings.dynamic_material_property_group_key
        if not material_group_key:
            material_group_key = generate_unique_key()
            settings.dynamic_material_property_group_key = material_group_key
    
        # Check if the selected shader has changed from what's  
        # currently loaded and if so, instantiate a new one
        for shader in SUPPORTED_SHADERS:
            name = shader[0]
            shader_impl = shader[1]

            # If the loader changed, instantiate a new Shader and assign to the material
            if settings.loader == name and (active_shader is None or not isinstance(active_shader, shader_impl)):
                active_shader = shader_impl()

                settings.last_shader_error = ''

                debug('Swap dynamic properties to', active_shader)

                unregister_dynamic_property_group(shader_group_key)
                props = active_shader.get_properties()
                if props and not props.is_empty:
                    register_dynamic_property_group(
                        shader_group_key, 
                        BaseDynamicMaterialProperties,
                        props.definitions,
                        shader_group_key
                    )

        try:
            active_shader.last_error = None

            # Push dynamic properties from the UI to the shader
            props = getattr(mat.material, shader_group_key, None)
            if props: active_shader.update_properties(props)

            needs_recompile = active_shader.needs_recompile()

            debug('--- Active shader', active_shader)
            debug('--- Force reload', settings.force_reload)
            debug('--- Live reload', settings.live_reload)
            debug('--- needs recompile', needs_recompile)
            
            # Trigger a recompile if we're forcing it or the files on disk
            # have been modified since the last render
            if settings.force_reload or (settings.live_reload and needs_recompile):
                settings.force_reload = False
                
                active_shader.compile()
                settings.last_shader_error = ''
                
                # Load new dynamic material properties into context
                unregister_dynamic_property_group(material_group_key)
                props = active_shader.get_material_properties()
                if props and not props.is_empty:
                    register_dynamic_property_group(
                        material_group_key, 
                        BaseDynamicMaterialProperties,
                        props.definitions,
                        material_group_key
                    )

            # This needs to happen after compilation, in case we switch back 
            # to a shader format that we're already storing data for 
            props = getattr(mat.material, material_group_key, None)
            if props: active_shader.update_material_properties(props)
                
        except Exception as e:
            print('SHADER ERROR', type(e))
            print(e)
            settings.last_shader_error = str(e)
            active_shader.last_error = str(e)

        mat.shader = active_shader
        
    @staticmethod
    def check_fallback_shader():
        """Make sure the fallback shader is compiled and ready to use"""
        try:
            if not ScratchpadRenderEngine.fallback_shader.is_compiled:
                ScratchpadRenderEngine.fallback_shader.compile()
        except Exception as e:
            # show_message('Failed to compile fallback shader. Check console', 'Compile Error', 'ERROR')
            print('--Failed to compile fallback shader--')
            print(e)

    def view_draw(self, context, depsgraph):
        """Called whenever Blender redraws the 3D viewport
        
        Parameters:
            context (bpy.context)
            depsgraph (bpy.types.Depsgraph)
        """
        scene = depsgraph.scene
        region3d = context.region_data

        # Begin frame rendering
        ScratchpadRenderEngine.check_fallback_shader()
        self.bind_display_space_shader(scene)

        # Camera Loop 
        self.render_data.camera.view_matrix = region3d.view_matrix
        self.render_data.camera.projection_matrix = region3d.window_matrix

        Graphics.enable_features(depth_test = True)
        Graphics.clear_render_target(
            clear_depth = True, 
            clear_color = True, 
            background_color = scene.world.color
        )

        # Run draw passes
        for p in self.passes:
            p.execute(self.render_data)
        
        # End frame rendering
        self.unbind_display_space_shader()
