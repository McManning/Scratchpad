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

layout (location = 0) out vec4 FragColor;

in VS_OUT {
    vec3 positionWS;
    vec3 normalWS;
} IN;

vec3 lambert(vec3 lightColor, vec3 lightDir, vec3 normal)
{
    float NdotL = clamp(dot(normal, lightDir), 0.0, 1.0);
    return lightColor * NdotL;
}

void main()
{
    vec3 diffuse = lambert(_MainLightColor.rgb, _MainLightDirection.xyz, IN.normalWS);
    FragColor = vec4(diffuse + _AmbientColor.rgb, 1);
}
