
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

from .shaders import SUPPORTED_SHADERS

def force_shader_reload(self, context):
    """Callback when any of the shader filenames change in FooRenderSettings"""
    context.scene.foo.force_reload = True

# Generate a Blender enum list for available shader loaders
LOADERS = [(s[0], s[0], s[1].__doc__, '', i) for i, s in enumerate(SUPPORTED_SHADERS)]

class FooRendererSettings(PropertyGroup):
    loader: EnumProperty(
        name='Shader Format',
        items=LOADERS,
        description='Shader file format to load from',
        default=LOADERS[0][0]
        # update = do thing
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
        min=0.0, 
        max=1.0
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

class BaseDynamicRendererSettings(PropertyGroup):
    """Base class for groups registered with register_dynamic_property_group()"""
    @classmethod
    def register(cls):
        bpy.types.Scene.foo_dynamic = PointerProperty(
            name='Foo Dynamic Renderer Settings',
            description='',
            type=cls
        )
    
    @classmethod
    def unregister(cls):
        del bpy.types.Scene.foo_dynamic

class BaseDynamicMaterialSettings(PropertyGroup):
    """Base class for groups registered with register_dynamic_property_group()"""
    @classmethod
    def register(cls):
        bpy.types.Material.foo_dynamic = PointerProperty(
            name='Foo Dynamic Material Settings',
            description='',
            type=cls
        )
    
    @classmethod
    def unregister(cls):
        del bpy.types.Material.foo_dynamic

def register_dynamic_property_group(class_name: str, base: PropertyGroup, properties: list):
    """Create a named PropertyGroup from a configuration list at runtime

    Parameters:
        class_name (str):       Class name to generate (used for unregister_dynamic...)
        base (PropertyGroup):   Base property group class to inherit the new class
        properties (list):      List in the shape [(key, title, description, type, default_value, min*, max*)]
    """
    # Map a key to a *Property() class instance
    attr = {}
    images = []

    print('Register dynamic', class_name, base, properties)

    for prop in properties:
        field_type, key, title, description, default_value, min_value, max_value = prop

        if field_type == 'float':
            attr[key] = FloatProperty(
                name=title,
                description=description,
                default=default_value or 0,
                min=min_value,
                max=max_value
            )
        elif field_type == 'color':
            attr[key] = FloatVectorProperty(  
                name=title,
                description=description,
                subtype='COLOR',
                default=default_value or (1, 1, 1),
                min=0.0, max=1.0,
            )
        elif field_type == 'boolean':
            attr[key] = BoolProperty(
                name=title,
                description=description,
                default=default_value
            )
        elif field_type == 'vec2':
            attr[key] = FloatVectorProperty(
                size=2,
                name=title,
                description=description,
                default=default_value or (0, 0),
                min=min_value,
                max=max_value
            )
        elif field_type == 'vec3':
            attr[key] = FloatVectorProperty(
                size=3,
                name=title,
                description=description,
                default=default_value or (0, 0, 0),
                min=min_value,
                max=max_value
            )
        elif field_type == 'vec4':
            attr[key] = FloatVectorProperty(
                size=4,
                name=title,
                description=description,
                default=default_value or (0, 0, 0, 0),
                min=min_value,
                max=max_value
            )
        elif field_type == 'source_file':
            attr[key] = StringProperty(
                name=title,
                description=description,
                default=default_value or '',
                subtype='FILE_PATH',
                update=force_shader_reload
            )
        elif field_type == 'image':
            # Typically, accessing bpy.types.* would be unsafe
            # while loading addons during boot. But since this 
            # is a dynamically registered instance, it's assumed
            # this ends up being registered after initial load.
            attr[key] = PointerProperty(
                name=title,
                description=description,
                type=bpy.types.Image
            )

            # TODO: COULD add a view toggle boolean here as well
            # if the image (or texture) input field becomes too large.

            # Add extra metadata to track this image input
            images.append(key)

        # And so on as needed.

    if not hasattr(bpy, 'foo_dynamic_property_groups'):
        bpy.foo_dynamic_property_groups = {}

    # Unregister the previous instance if reloading
    if class_name in bpy.foo_dynamic_property_groups:
        # delattr(bpy.types.Scene, class_name)
        bpy.utils.unregister_class(bpy.foo_dynamic_property_groups[class_name])

    # Instantiate a new BaseDynamicMaterialSettings instance container.
    # We add everything as property annotations for Blender 2.8+
    clazz = type(class_name, (base,), { '__annotations__': attr })
    clazz.images = images 

    print('Register dynamic', clazz)
    bpy.utils.register_class(clazz)

    # Apply to scope - no longer applicable, class has its own @register method
    # setattr(bpy.types.Scene, name, PointerProperty(type=clazz))

    # track for unregister_dynamic_property_group
    bpy.foo_dynamic_property_groups[class_name] = clazz

def unregister_dynamic_property_group(class_name: str):     
    """"Remove a PropertyGroup previously created by register_dynamic_property_group
    
    Parameters:
        class_name (str): Class name to unregister
    """
    if hasattr(bpy, 'foo_dynamic_property_groups') and class_name in bpy.foo_dynamic_property_groups:
        clazz = bpy.foo_dynamic_property_groups[class_name]
        print('Unregister dynamic', clazz)

        try:
            bpy.utils.unregister_class(clazz)
        except: 
            pass
        
        del bpy.foo_dynamic_property_groups[class_name]
    else:
        print('Cannot find dynamic to unregister:', class_name)

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
