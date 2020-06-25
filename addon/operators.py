
import bpy
from bpy.types import Operator

class SCRATCHPAD_OT_reload_sources(Operator):
    """Force reload of shader source files"""
    bl_idname = 'scratchpad.reload_sources'
    bl_label = 'Reload Shader Sources'

    def invoke(self, context, event):
        context.scene.scratchpad.force_reload = True
        
        return {'FINISHED'}

classes = (
    SCRATCHPAD_OT_reload_sources,
)
