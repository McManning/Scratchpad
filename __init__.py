
bl_info = {
    'name': 'Scratchpad',
    'description': 'Simple realtime viewport render engine',
    'author': 'Chase McManning',
    'version': (0, 1, 0),
    'blender': (2, 82, 0),
    'doc_url': 'https://github.com/McManning/Scratchpad/wiki',
    'tracker_url': 'https://github.com/McManning/Scratchpad/issues',
    'category': 'Render'
}

if 'bpy' in locals():
    import importlib
    importlib.reload(lib)
    lib.registry.Registry.clear()
    importlib.reload(shaders)
    importlib.reload(core)
else:
    import bpy 
    from . import lib
    from . import shaders
    from . import core

import bpy

def register():
    lib.registry.Registry.register()

def unregister():
    lib.registry.Registry.unregister()

    # TODO: Move to Registry?
    # Unregister dynamic-generated property groups 
    if hasattr(bpy, 'scratchpad_dynamic_property_groups'):
        for key, instance in bpy.scratchpad_dynamic_property_groups.items():
            try:
                bpy.utils.unregister_class(instance)
            except: 
                pass
            
        bpy.scratchpad_dynamic_property_groups = {}
