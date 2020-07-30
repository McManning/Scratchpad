
if 'bpy' in locals():
    import importlib
    importlib.reload(lexer)
    importlib.reload(parser)
    importlib.reload(shader)
else:
    from . import lexer
    from . import parser
    from . import shader

import bpy
