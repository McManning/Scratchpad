
import bpy

class FooReloadSourcesOperator(bpy.types.Operator):
    """Operator to force reload of shader source files"""
    bl_idname = 'foo.reload_sources'
    bl_label = 'Reload Shader Sources'
    # bl_options = {'INTERNAL'}

    def invoke(self, context, event):
        context.scene.foo.force_reload = True
        
        return {'FINISHED'}

# CLASSLIST = (
#     FooReloadSourcesOperator
# )

# def register():
#     bpy.utils.register_class(FooReloadSourcesOperator)
#     # for cls in CLASSLIST:
#     #     bpy.utils.register_class(cls)

# def unregister():
#     bpy.utils.unregister_class(FooReloadSourcesOperator)
#     # for cls in CLASSLIST:
#     #     bpy.utils.unregister_class(cls)

classes = (
    FooReloadSourcesOperator,
)
