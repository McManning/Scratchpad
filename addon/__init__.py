
bl_info = {
    'name': 'Scratchpad',
    'description': 'Simple realtime viewport render engine',
    'author': 'Chase McManning',
    'version': (0, 1, 0),
    'blender': (2, 83, 0),
    'doc_url': 'https://github.com/McManning/Scratchpad/wiki',
    'tracker_url': 'https://github.com/McManning/Scratchpad/issues',
    'category': 'Render'
}

# TODO: Reloading isn't working for anything in renderables.

_modules = [
    'properties',
    'operators',
    'panels',
    'engine',

    'lights',
    'renderables',
    'mesh_data',
    'vao',
    
    # TODO: Hot reloading of subfolder modules somehow? 
    'shaders',
]

# support reloading sub-modules
# TODO: This works - but maybe something more explicit and direct would be better?
# e.g. https://github.com/blender/blender-addons/blob/master/magic_uv/__init__.py 
_namespace = globals()
if 'bpy' in locals():
    from importlib import reload
    _modules_loaded = [reload(_namespace[val]) for val in _modules]
else:
    import bpy
    __import__(name=__name__, fromlist=_modules)
    _modules_loaded = [_namespace[name] for name in _modules]

import bpy

def register():
    from bpy.utils import register_class
    for mod in _modules_loaded:
        if 'classes' in dir(mod):
            for instance in mod.classes:
                register_class(instance)

def unregister():
    from bpy.utils import unregister_class
    for mod in reversed(_modules_loaded):
        if 'classes' in dir(mod):
            for instance in reversed(mod.classes):
                if instance.is_registered:
                    unregister_class(instance)

    # Unregister dynamic-generated property groups 
    if hasattr(bpy, 'scratchpad_dynamic_property_groups'):
        for key, instance in bpy.scratchpad_dynamic_property_groups.items():
            try:
                bpy.utils.unregister_class(instance)
            except: 
                pass
            
        bpy.scratchpad_dynamic_property_groups = {}
