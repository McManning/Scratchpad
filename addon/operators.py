
import bpy

class FooReloadSourcesOperator(bpy.types.Operator):
    """Force reload of shader source files"""
    bl_idname = 'foo.reload_sources'
    bl_label = 'Reload Shader Sources'
    # bl_options = {'INTERNAL'}

    def invoke(self, context, event):
        context.scene.foo.force_reload = True
        
        return {'FINISHED'}

classes = (
    FooReloadSourcesOperator,
)
