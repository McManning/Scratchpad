#version 410 core

// Lighting information provided by micro.py
uniform vec4 _MainLightDirection;
uniform vec4 _MainLightColor; // (R, G, B, Intensity)

layout (location = 0) out vec4 FragColor;

in GS_OUT {
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
    vec3 ambient = vec3(0.5, 0.5, 0.5);

    vec3 diffuse = lambert(_MainLightColor.rgb, _MainLightDirection.xyz, IN.normalWS);
    FragColor = vec4(diffuse + ambient, 1);
}
