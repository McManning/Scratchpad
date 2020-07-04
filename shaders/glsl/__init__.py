
if 'bpy' in locals():
    import importlib
    importlib.reload(preprocessor)
    importlib.reload(shader)
else:
    from . import preprocessor
    from . import shader

import bpy
