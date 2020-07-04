
import uuid
from collections import OrderedDict
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
    ScratchpadMesh
)

from .shaders.fallback import FallbackShader
from .shaders import SUPPORTED_SHADERS 

from .properties import (
    register_dynamic_property_group, 
    unregister_dynamic_property_group,
    BaseDynamicMaterialProperties
)

def sort_by_draw_order(arr):
    """Sort a list of Material instances by Scratchpad draw priority
    
    Parameters:
        arr ({ bpy.types.Material, list(Renderable) }): Dictionary mapping a material     
                                                        to Renderables that use it
    
    Returns:
        list(bpy.types.Material)
    """
    return OrderedDict(sorted(arr.items(), key=lambda m: m[0].scratchpad.priority))

def generate_unique_key() -> str:
    return 'scratchpad_dynamic_' + uuid.uuid4().hex

class ScratchpadRenderEngine(bpy.types.RenderEngine):
    bl_idname = "scratchpad_renderer"
    bl_label = "Scratchpad"
    bl_use_preview = True

    # Mesh instances shared between render engines
    # Maps a bpy.types.Mesh to a ScratchpadMesh.
    # TODO: Unfortunately, I'm getting access violation crashes when toggling between 
    # different modes (layout, editing, sculpting). Hard to trace. I'm *guessing* that
    # GL isn't shared between them, because I'm also getting weird issues with every
    # other VAO not working?
    # meshes = dict()

    def __init__(self):
        """Called when a new render engine instance is created. 

        Note that multiple instances can exist @ once, e.g. a viewport and final render
        """
        self.meshes = dict()
        self.renderables = dict() # Material -> Renderable impl 
        self.shaders = dict() # Material -> BaseShader impl
        
        self.lighting = SceneLighting()
        self.lighting.main_light = MainLight()

        self.fallback_shader = FallbackShader()

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
        # region = context.region
        # view3d = context.space_data
        scene = depsgraph.scene

        # self.updated_meshes = dict()
        self.updated_renderables = dict()
        self.updated_shaders = dict()
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
                print('Unhandled scene object type', obj.type)
        
        # Replace old aggregates of tracked scene data
        # self.meshes = self.updated_meshes
        self.shaders = self.updated_shaders
        self.renderables = sort_by_draw_order(self.updated_renderables)

        # self.lighting.ambient_color = context.scene.scratchpad.ambient_color TODO:MIGRATE
        self.lighting.additional_lights = self.updated_additional_lights

        self.prune_missing_meshes()

    def update_mesh(self, obj, depsgraph):
        """Track a mesh still used in the scene and updated geometry on the GPU if needed
        
        Parameters:
            obj (bpy.types.Object):             Object containing mesh data to read
            depsgraph (bpy.types.Depsgraph):    Dependency graph to use for generating a final mesh
        """
        rebuild_geometry = obj.name in self.updated_geometries
        
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

    def prune_missing_meshes(self):
        """Remove any meshes no longer present in the file"""
        pass

    def update_material(self, mat, obj):
        """Track a material still used by an object in the scene

        Parameters:
            mat (bpy.types.Material)  
            obj (Renderable):           Renderable that uses the material
        """
        # Aggregate Renderables under the Material
        # In a perfect world, we'd iterate polygons and aggregate what specific
        # polygons are using what materials. But that's too slow to be practical.
        if mat not in self.updated_renderables:
            # TODO: Set instead? Would it be slower?
            self.updated_renderables[mat] = [obj] 
        else:
            self.updated_renderables[mat].append(obj)

        # On first update of this Material also check for a Shader update
        if mat not in self.updated_shaders:
            self.update_material_shader(mat)

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
    
    def update_material_shader(self, mat):
        """ Send updated user data to the shader attached to     
            the material and check if we should hot reload sources

        Parameters:
            mat (bpy.types.Material): Parent material of the shader
        """
        # scene_settings = context.scene.scratchpad # TODO: Unused. Needed anymore?
        settings = mat.scratchpad
        active_shader = self.shaders.get(mat, None)

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

                print('Swap dynamic properties to', active_shader)

                unregister_dynamic_property_group(shader_group_key)
                props = active_shader.get_renderer_properties()
                if props:
                    register_dynamic_property_group(
                        shader_group_key, 
                        BaseDynamicMaterialProperties,
                        props.definitions,
                        shader_group_key
                    )

        try:
            active_shader.error = None

            # Push dynamic properties from the UI to the shader
            props = getattr(mat, shader_group_key, None)
            if props: active_shader.update_renderer_properties(props)

            needs_recompile = active_shader.needs_recompile()

            print('--- Active shader', active_shader)
            print('--- Force reload', settings.force_reload)
            print('--- Live reload', settings.live_reload)
            print('--- needs recompile', needs_recompile)
            
            # Trigger a recompile if we're forcing it or the files on disk
            # have been modified since the last render
            if settings.force_reload or (settings.live_reload and needs_recompile):
                settings.force_reload = False
                
                active_shader.compile()
                settings.last_shader_error = ''
                
                # Load new dynamic material properties into context
                unregister_dynamic_property_group(material_group_key)
                props = active_shader.get_material_properties()
                if props:
                    register_dynamic_property_group(
                        material_group_key, 
                        BaseDynamicMaterialProperties,
                        props.definitions,
                        material_group_key
                    )

            # This needs to happen after compilation, in case we switch back 
            # to a shader format that we're already storing data for 
            props = getattr(mat, material_group_key, None)
            if props: active_shader.update_material_properties(props)
                
        except Exception as e:
            print('SHADER ERROR', type(e))
            print(e)
            settings.last_shader_error = str(e)
            active_shader.error = str(e)

        self.updated_shaders[mat] = active_shader

    # def update_shaders(self, context):
    #     """Send updated user data to active shaders and check for reloads
        
    #     Parameters:
    #         context (bpy.context) - Current context to update from
    #     """
        
    #     for mat in self.shaders:
    #         self.update_material_shader(context, mat)

    def check_fallback_shader(self):
        """Make sure the fallback shader is compiled and ready to use"""
        try:
            if not self.fallback_shader.is_compiled:
                self.fallback_shader.compile()
        except Exception as e:
            # show_message('Failed to compile fallback shader. Check console', 'Compile Error', 'ERROR')
            print('--Failed to compile fallback shader--')
            print(e)

    def draw_pass(self, context, mat):
        """Draw Renderables with the given Material

        Parameters:
            context (bpy.context):      Current draw context
            mat (bpy.types.Material):   Material to draw with
        """
        region3d = context.region_data
        shader = self.shaders[mat]
        renderables = self.renderables[mat]

        if shader.error:
            shader = self.fallback_shader

        shader.bind()
        shader.set_camera_matrices(
            region3d.view_matrix,
            region3d.window_matrix
        )
        
        shader.set_lighting(self.lighting)

        # Render everything in the scene with this material
        for r in renderables:
            shader.set_object_matrices(r.model_matrix)
            r.draw(shader)

        shader.unbind()

    def view_draw(self, context, depsgraph):
        """Called whenever Blender redraws the 3D viewport
        
        Parameters:
            context (bpy.context)
            depsgraph (bpy.types.Depsgraph)
        """
        scene = depsgraph.scene
        # region = context.region
        # region3d = context.region_data
        # settings = scene.scratchpad
        
        # self.check_shader_reload(context)
        
        # viewport = [region.x, region.y, region.width, region.height]
        
        # view_matrix = region3d.view_matrix # transposed GL_MODELVIEW_MATRIX
        # view_matrix_inv = view_matrix.inverted()
        # cam_pos = view_matrix_inv * Vector((0.0, 0.0, 0.0))
        # cam_dir = (view_matrix_inv * Vector((0.0, 0.0, -1.0))) - cam_pos        
        
        self.bind_display_space_shader(scene)
        self.check_fallback_shader()

        glEnable(GL_DEPTH_TEST)
        
        # glEnable(GL_BLEND)
        # glBlendFunc(GL_ONE, GL_ONE_MINUS_SRC_ALPHA)

        clear_color = scene.scratchpad.clear_color
        glClearColor(clear_color[0], clear_color[1], clear_color[2], 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # TODO: Other draw passes (shadow, depth, whatever) would happen here in some form. 
        for mat in self.renderables:
            self.draw_pass(context, mat)
        
        # for mesh in self.meshes.values():
        #     self.shader.set_object_matrices(mesh.model_matrix)
        #     mesh.draw(self.shader)

        self.unbind_display_space_shader()
        # glDisable(GL_BLEND)


classes = (
    ScratchpadRenderEngine,
)
