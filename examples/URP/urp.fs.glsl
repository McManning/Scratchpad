
#include "common.glsl"
#include "lights.glsl"

layout (location = 0) out vec4 FragColor;

in VS_OUT {
    vec3 positionWS;
    vec3 normalWS;
} IN;

void main()
{
    Light mainLight = GetMainLight();
    
    vec3 attenuatedLightColor = mainLight.color * mainLight.distanceAttenuation;
    vec3 diffuseColor = LightingLambert(attenuatedLightColor, mainLight.direction, IN.normalWS);
    // vec3 specularColor = LightingSpecular(attenuatedLightColor, mainLight.direction, normalWS, viewDirectionWS, specularGloss, shininess);

    int pixelLightCount = GetAdditionalLightsCount();
    for (int i = 0; i < pixelLightCount; ++i)
    {
        Light light = GetAdditionalLight(i, IN.positionWS);
        vec3 attenuatedLightColor = light.color * light.distanceAttenuation;
        diffuseColor += LightingLambert(attenuatedLightColor, light.direction, IN.normalWS);
        // specularColor += LightingSpecular(attenuatedLightColor, light.direction, normalWS, viewDirectionWS, specularGloss, shininess);
    }

    // vec3 diffuse = vec3(0.5, 0.5, 0.5);

    // TODO: Hook up LightweightFragmentBlinnPhong

    vec3 finalColor = diffuseColor + _AmbientColor.rgb;

    FragColor = vec4(finalColor, 1);
} 
