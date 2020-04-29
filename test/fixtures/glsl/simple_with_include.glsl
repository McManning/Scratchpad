#version 110 core

uniform mat4 ModelViewProjectionMatrix;

in vec3 Position;

#include "func1.glsl"
// Line 8

void main()
{
    gl_Position = ModelViewProjectionMatrix * vec4(Position, 1.0);
}
