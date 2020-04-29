
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

class FooRendererSettings(PropertyGroup):
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
    
    geom_filename: StringProperty(
        name='Geometry',
        description='GLSL geometry shader source file',
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

classes = (
    FooRendererSettings,
    FooLightSettings,
)

# def register():
#     for cls in classes:
#         bpy.utils.register_class(cls)

# def unregister():
#     for cls in classes:
#         bpy.utils.unregister_class(cls)
