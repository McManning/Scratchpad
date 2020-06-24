# License stuff
#
#

bl_info = {
    'name': 'Foo Render Engine',
    'author': 'Chase McManning',
    'blender': (2, 80, 0),
    'description': '...',
    'doc_url': 'https://path/to/docs',
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
            for cls in mod.classes:
                register_class(cls)

def unregister():
    from bpy.utils import unregister_class
    for mod in reversed(_modules_loaded):
        if 'classes' in dir(mod):
            for cls in reversed(mod.classes):
                if cls.is_registered:
                    unregister_class(cls)

    # Unregister dynamic-generated property groups 
    if hasattr(bpy, 'foo_dynamic_property_groups'):
        for key, value in bpy.foo_dynamic_property_groups.items():
            # TODO: Scope. Currently assumes they all exist on Scene.
            # TODO: SHOULD we delattr? Reloading the plugin should just
            # replace, not destroy what was there. What about a scene reload?
            # Does that break everything stored here? 
            # Each PropertyGroup *does* delete the property on unregister currently.
            # delattr(bpy.types.Material, key) 
            bpy.utils.unregister_class(value)
    
    bpy.foo_dynamic_property_groups = {}
