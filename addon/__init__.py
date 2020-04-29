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

# support reloading sub-modules
# This comes from Blender's bl_ui startup addon
if 'bpy' in locals():
    from importlib import reload
    _modules_loaded[:] = [reload(val) for val in _modules_loaded]
    del reload

_modules = [
    'properties',
    'operators',
    'panels',
    'engine',

    'lights',
    'renderables',

    # TODO: Hot reloading of subfolder modules somehow? 
    'shaders',
]

import bpy

__import__(name=__name__, fromlist=_modules)
_namespace = globals()
_modules_loaded = [_namespace[name] for name in _modules]
del _namespace

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
