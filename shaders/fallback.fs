#version 330 core

uniform mat4 CameraMatrix;

layout (location = 0) out vec4 FragColor;

in VS_OUT { 
    vec3 positionWS;
    vec3 normalWS;
} IN;

void main()
{
    vec3 cameraPositionWS = CameraMatrix[3].xyz;

    vec3 eye = cameraPositionWS - IN.positionWS;
    float ndl = clamp(dot(IN.normalWS, normalize(eye)), 0.0, 1.0);

    vec4 inner = vec4(0.5, 0.1, 0.1, 1);
    vec4 outer = vec4(0.2, 0, 0, 1);

    FragColor = mix(outer, inner, ndl);
}
