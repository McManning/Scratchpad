
from .fallback import FallbackShader
from .glsl import GLSLShader
from .base import (
    Shader,
    ShaderData,
    LightData,
    VertexData
)

shaders = (
    FallbackShader,
    GLSLShader,
    # ('OGSFX', OGSFXShader),
    # ('Unity ShaderLab', UnityShaderLabShader),
)
