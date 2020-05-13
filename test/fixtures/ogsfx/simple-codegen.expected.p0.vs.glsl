#version 420 core
#define DEBUG 1
uniform mat4 gMVP;
in vec3 position;
in vec3 normal;
in vec4 channel0;
out V2P {
    vec4 position;
    vec4 normal;
} OUT;

    void main() {
        OUT.position = gMVP * vec4(position, 1.0);
    }
