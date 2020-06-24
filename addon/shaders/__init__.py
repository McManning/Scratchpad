
from .fallback import FallbackShader
from .glsl import GLSLShader
from .ogsfx import OGSFXShader
from .base import (
    BaseShader,
    ShaderProperties
)

# Supported shaders the user can pick from
SUPPORTED_SHADERS = [
    ('Builtin', FallbackShader),
    ('GLSL', GLSLShader),
    ('Maya OGSFX', OGSFXShader)
]
