#version 420 core
#define DEBUG 1
uniform mat4 gMVP;
in V2P {
    vec4 position;
    vec4 normal;
} IN;
out vec4 color;

    void main() {
        color = vec4(1, 0, 0, 1);
    }
