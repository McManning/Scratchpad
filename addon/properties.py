
import bpy
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

from bpy.types import PropertyGroup

def force_shader_reload(self, context):
    """Callback when any of the shader filenames change in FooRenderSettings"""
    context.scene.foo.force_reload = True

LOADERS = [
    # Identifier, name, description, icon, number
    ('glsl', 'GLSL', 'Shader loaded from simple GLSL files without extra features', '', 0),
    ('ogsfx', 'Maya OGSFX', 'Shader using OGSFX format to declare custom UI editors, techniques, and passes', '', 1),
]

class FooRendererSettings(PropertyGroup):
    loader: EnumProperty(
        name='Shader Format',
        items=LOADERS,
        description='Shader file format to load from',
        default='glsl',
        # update = do thing
    )

    # Renderer settings specific to OGSFXShader
    ogsfx_filename: StringProperty(
        name='Filename',
        description='.ogsfx file to load',
        default='',
        subtype='FILE_PATH',
        update=force_shader_reload
    )

    # Renderer settings specific to GLSLShader
    vert_filename: StringProperty(
        name='Vertex',
        description='GLSL vertex shader source file',
        default='',
        subtype='FILE_PATH',
        update=force_shader_reload
    )
    
    frag_filename: StringProperty(
        name='Fragment',
        description='GLSL fragment shader source file',
        default='',
        subtype='FILE_PATH',
        update=force_shader_reload
    )
    
    tesc_filename: StringProperty(
        name='Tessellation Control',
        description='GLSL tessellation control shader source file',
        default='',
        subtype='FILE_PATH',
        update=force_shader_reload
    )
    
    tese_filename: StringProperty(
        name='Tessellation Evaluation',
        description='GLSL tessellation evaluation shader source file',
        default='',
        subtype='FILE_PATH',
        update=force_shader_reload
    )
    
    geom_filename: StringProperty(
        name='Geometry',
        description='GLSL geometry shader source file',
        default='',
        subtype='FILE_PATH',
        update=force_shader_reload
    )
    
    # Common properties
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
    
    force_reload: BoolProperty(
        name='Force Reload'
    )

    last_shader_error: StringProperty(
        name='Last Shader Error'
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
            name='Foo Light Settings',
            description='',
            type=cls
        )
    
    @classmethod
    def unregister(cls):
        del bpy.types.Light.foo

def register_dynamic_property_group(name: str, properties: list):
    """Create a named PropertyGroup from a configuration list at runtime

    :param properties: List in the shape [(name, description, type, default_value, min*, max*)]
    """
    # Map a key to a *Property() class instance
    attributes = {}

    for prop in properties:
        prop_name = prop[0]
        description = prop[1]
        prop_type = prop[2]
        default_value = prop[3] # mixed type
        prop_min = prop[4] if len(prop) > 4 else -99999 # TODO: float min
        prop_max = prop[5] if len(prop) > 5 else 99999 # TODO: Float max

        if prop_type == 'float':
            attributes[prop_name] = FloatProperty(
                name=prop_name,
                description=description,
                default=default_value,
                min=prop_min,
                max=prop_max
            )
        elif prop_type == 'color':
            attributes[prop_name] = FloatVectorProperty(  
                name=prop_name,
                description=description,
                subtype='COLOR',
                default=default_value, # (0.15, 0.15, 0.15)
                min=0.0, max=1.0,
            )
        elif prop_type == 'boolean':
            attributes[prop_name] = BoolProperty(
                name=prop_name,
                description=description,
                default=default_value
            )
        elif prop_type == 'vec2':
            attributes[prop_name] = FloatVectorProperty(
                size=2,
                name=prop_name,
                description=description,
                default=default_value,
                min=prop_min,
                max=prop_max
            )
        elif prop_type == 'vec3':
            attributes[prop_name] = FloatVectorProperty(
                size=3,
                name=prop_name,
                description=description,
                default=default_value,
                min=prop_min,
                max=prop_max
            )
        elif prop_type == 'vec4':
            attributes[prop_name] = FloatVectorProperty(
                size=4,
                name=prop_name,
                description=description,
                default=default_value,
                min=prop_min,
                max=prop_max
            )

        # And so on as needed.

    if not hasattr(bpy, 'foo_dynamic_property_groups'):
        bpy.foo_dynamic_property_groups = {}

    # Unregister the previous instance if reloading
    if name in bpy.foo_dynamic_property_groups:
        delattr(bpy.types.Scene, name)
        bpy.utils.unregister_class(bpy.foo_dynamic_property_groups[name])

    # Instantiate a new PropertyGroup instance container.
    # We add everything as property annotations for Blender 2.8+
    clazz = type(name, (PropertyGroup,), { '__annotations__': attributes })
    bpy.utils.register_class(clazz)

    # Apply to scope
    # TODO: Allow scoping to something else. It's assumed this is just for
    # shader settings at the moment, so we just scope onto Scene
    setattr(bpy.types.Scene, name, PointerProperty(type=clazz))
    bpy.foo_dynamic_property_groups[name] = clazz


# def unregister_dynamic_property_groups():
#     if hasattr(bpy, 'dynamic_property_groups'):
#         for key, value in bpy.dynamic_property_groups.items():
#             delattr(bpy.types.Scene, key) # TODO: Scope
#             bpy.utils.unregister_class(value)
    
#     bpy.dynamic_property_groups = {}

classes = (
    FooRendererSettings,
    FooLightSettings,
)
