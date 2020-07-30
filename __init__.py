
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

import os
import sys

# This is done to allow absolute imports from the root of this package.
# TODO: Better solution. This lets us keep the same imports as we would 
# while running through unittest.
path = os.path.dirname(os.path.realpath(__file__))
if path not in sys.path:
    sys.path.append(path)

if 'bpy' in locals():
    import importlib
    importlib.reload(libs)
    libs.registry.Registry.clear()
    importlib.reload(shaders)
    importlib.reload(core)
else:
    import bpy 
    from . import libs
    from . import shaders
    from . import core

import bpy

from libs.registry import Registry

def register():
    Registry.register()

def unregister():
    Registry.unregister()
