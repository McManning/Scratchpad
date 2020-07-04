
import bpy
from bpy.types import Operator

from ..lib.registry import autoregister

@autoregister
class SCRATCHPAD_OT_reload_sources(Operator):
    """Force reload of shader source files"""
    bl_idname = 'scratchpad.reload_sources'
    bl_label = 'Reload Shader Sources'

    def invoke(self, context, event):
        # TODO: Refactor to trigger a reload for ALL materials
        # TODO:MIGRATE
        context.scene.scratchpad.force_reload = True
        
        return {'FINISHED'}
