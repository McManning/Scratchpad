
if 'bpy' in locals():
    import importlib
    importlib.reload(render_pass)
    importlib.reload(additional_lights_shadow_caster_pass)
    importlib.reload(draw_objects_pass)
    importlib.reload(main_light_shadow_caster_pass)
else:
    from .render_pass import *
    from .additional_lights_shadow_caster_pass import * 
    from .draw_objects_pass import * 
    from .main_light_shadow_caster_pass import * 

import bpy
