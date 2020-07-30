
import uuid
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

from shaders import SUPPORTED_SHADERS
from libs.debug import debug
from libs.registry import autoregister, Registry

def force_shader_reload(self, context):
    """Callback when any of the shader filenames change"""
    context.scene.scratchpad.force_reload = True

# Generate a Blender enum list for available shader loaders
LOADERS = [(s[0], s[0], s[1].__doc__, '', i) for i, s in enumerate(SUPPORTED_SHADERS)]

@autoregister
class ScratchpadProperties(PropertyGroup):
    # TODO: Scene/render properties

    @classmethod
    def register(cls):
        bpy.types.Scene.scratchpad = PointerProperty(
            name="Scratchpad Scene Settings",
            type=cls
        )
        
    @classmethod
    def unregister(cls):
        del bpy.types.Scene.scratchpad

@autoregister
class ScratchpadMaterialProperties(PropertyGroup):
    dynamic_shader_property_group_key: StringProperty(
        default=''
    )

    dynamic_material_property_group_key: StringProperty(
        default=''
    )

    priority: IntProperty(
        name='Priority',
        default=1000,
        description='Render order priority. Lowest are drawn first',
    )

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
        bpy.types.Material.scratchpad = PointerProperty(
            name="Scratchpad Settings",
            type=cls
        )
        
    @classmethod
    def unregister(cls):
        del bpy.types.Material.scratchpad

@autoregister
class ScratchpadLightProperties(PropertyGroup):
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
        bpy.types.Light.scratchpad = PointerProperty(
            name='Scratchpad Light Settings',
            description='',
            type=cls
        )
    
    @classmethod
    def unregister(cls):
        del bpy.types.Light.scratchpad

class BaseDynamicMaterialProperties(PropertyGroup):
    """Base class for groups registered with register_dynamic_property_group()"""
    @classmethod
    def register(cls):
        setattr(bpy.types.Material, cls.property_key, PointerProperty(
            name='Scratchpad Dynamic Material Properties',
            description='',
            type=cls
        ))
    
    @classmethod
    def unregister(cls):
        # del bpy.types.Material[cls.property_key]
        delattr(bpy.types.Material, cls.property_key)


def register_dynamic_property_group(class_name: str, base: PropertyGroup, properties: list, property_key: str):
    """Create a named PropertyGroup from a configuration list at runtime

    Parameters:
        class_name (str):       Class name to generate (used for unregister_dynamic...)
        base (PropertyGroup):   Base property group class to inherit the new class
        properties (list):      List in the shape [(key, title, description, type, default_value, min*, max*)]
    """
    # Map a key to a *Property() class instance
    attr = {}
    images = []

    debug('Register dynamic', class_name, base, properties)

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

    # Unregister the previous instance if reloading
    Registry.unregister_dynamic(class_name)

    # Instantiate a new BaseDynamicMaterialProperties instance container.
    # We add everything as property annotations for Blender 2.8+
    instance = type(class_name, (base,), { '__annotations__': attr })
    instance.images = images 
    instance.property_key = property_key

    debug('Register dynamic', instance)
    Registry.register_dynamic(class_name, instance)

def unregister_dynamic_property_group(class_name: str):     
    """"Remove a PropertyGroup previously created by register_dynamic_property_group
    
    Parameters:
        class_name (str): Class name to unregister
    """
    Registry.unregister_dynamic(class_name)
    