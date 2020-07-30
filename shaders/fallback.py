
from .base import (
    BaseShader,
    compile_program
)

VS_FALLBACK = '''
#version 330 core

uniform mat4 ModelViewProjectionMatrix;

in vec3 Position;

out VS_OUT {
    vec3 position;
} OUT;

void main()
{
    gl_Position = ModelViewProjectionMatrix * vec4(Position, 1.0);
    OUT.position = Position.xyz;
}
'''

FS_FALLBACK = '''
#version 330 core

out vec4 fragColor;

in VS_OUT { 
    vec3 position;
} IN;

void main()
{
    vec3 p = floor((IN.position.xyz + 0.00001) * 2.0);
    float m = mod(p.x + p.y + p.z, 2.0);
    fragColor = vec4(m, 0, m, 1);
}

'''

class FallbackShader(BaseShader):
    """Built-in default shader as a "safe" fallback in case of failures"""
    def compile(self):
        self.program = compile_program(VS_FALLBACK, FS_FALLBACK)
