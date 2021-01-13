
#version 450 core

// Matrices available to you by micro.py
uniform mat4 ViewMatrix;
uniform mat4 ProjectionMatrix;
uniform mat4 CameraMatrix; // Inverted ViewMatrix

uniform mat4 ModelMatrix;
uniform mat4 ModelViewMatrix;
uniform mat4 ModelViewProjectionMatrix;

// Lighting information provided by micro.py
uniform vec4 _MainLightDirection;
uniform vec4 _MainLightColor; // (R, G, B, Intensity)

// Other useful information
uniform int _Frame;

in vec3 Position;
in vec3 Normal;

out VS_OUT {
    vec4 position;
    vec3 normal;
} OUT;

void main()
{
    // vec3 offset = vec3(1, 1, 1.0 + sin(_Frame * 0.1) * 0.5);

    // Only model space is passed forward
    gl_Position = ModelMatrix * vec4(Position, 1.0);

    OUT.position = gl_Position;
    OUT.normal = Normal;
}
