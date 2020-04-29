#version 110 core

uniform mat4 ModelViewProjectionMatrix;

in vec3 Position;

void main()
{
    gl_Position = ModelViewProjectionMatrix * vec4(Position, 1.0);
}
