#version 330 core

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
uniform vec4 _AmbientColor;

// Other useful information
uniform int _Frame;

in vec3 Position;
in vec3 Normal;

out VS_OUT {
    vec3 positionWS;
    vec3 normalWS;
} OUT;

void main()
{
    gl_Position = ModelViewProjectionMatrix * vec4(Position, 1.0);

    gl_Position.z = gl_Position.z - 0.000001 * gl_Position.w;

    vec3 positionWS = (ModelMatrix * vec4(Position, 1.0)).xyz;
    vec3 normalWS = (ModelMatrix * vec4(Normal, 0)).xyz;

    OUT.positionWS = positionWS;
    OUT.normalWS = normalWS;
}
