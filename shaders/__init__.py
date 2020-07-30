
if 'bpy' in locals():
    import importlib
    importlib.reload(base)
    importlib.reload(fallback)
    importlib.reload(glsl)
    importlib.reload(ogsfx)
else:
    from . import base
    from . import fallback 
    from . import glsl 
    from . import ogsfx

import bpy

# Supported shaders the user can pick from
SUPPORTED_SHADERS = [
    ('Builtin', fallback.FallbackShader),
    ('GLSL', glsl.shader.GLSLShader),
    # ('Maya OGSFX', ogsfx.OGSFXShader)
]
