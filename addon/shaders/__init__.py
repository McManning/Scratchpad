
from .fallback import FallbackShader
from .glsl import GLSLShader
from .ogsfx import OGSFXShader
from .base import (
    Shader,
    LightData,
    VertexData,
    ShaderProperties
)

# Supported shaders the user can pick from
shaders = [
    ('Builtin', FallbackShader),
    ('GLSL', GLSLShader),
    ('Maya OGSFX', OGSFXShader)
]
