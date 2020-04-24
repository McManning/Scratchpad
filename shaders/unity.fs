
#version 330 core
layout (location = 0) out vec4 FragColor;

uniform mat4 ModelMatrix; // World
uniform mat4 ViewMatrix; // View
uniform mat4 ProjectionMatrix; // Projection
uniform mat4 ModelViewMatrix; // World
uniform mat4 MVP; // WorldViewProjection
uniform mat4 CameraMatrix; // ViewInverse

uniform vec4 _MainLightDirection;
uniform vec4 _MainLightColor;
uniform vec3 _AmbientColor;

uniform int _AdditionalLightsCount;
uniform vec4[16] _AdditionalLightsPosition; // (Light.matrix_world.to_translation(), 1|0)
uniform vec4[16] _AdditionalLightsColor; // (Light.color, intensity)
uniform vec4[16] _AdditionalLightsSpotDir; // (Light.matrix_world.to_quaternion() @ Vector((0, 1, 0)), 0)
uniform vec4[16] _AdditionalLightsAttenuation; // (magic, 2.8, 0, 1)

struct Light {
    vec3 position;
    vec3 direction;
    vec3 color;
    float distanceAttenuation;
};

float rsqrt(float a)
{
    return pow(a, -0.5);
}

/**
 * Unity Vanilla attenuation - smooth decrease to light range
 */
float DistanceAttenuation(float distanceSqr, vec2 distanceAttenuation)
{
    float lightAtten = 1.0 / distanceSqr;

    float factor = distanceSqr * distanceAttenuation.x;
    float smoothFactor = clamp(1.0 - factor * factor, 0.0, 1.0);
    smoothFactor = smoothFactor * smoothFactor;

    // float smoothFactor = clamp(distanceSqr * distanceAttenuation.x + distanceAttenuation.y, 0.0, 1.0);

    return lightAtten * smoothFactor;
}

float AngleAttenuation(vec3 spotDirection, vec3 lightDirection, vec2 spotAttenuation)
{
    float SdotL = dot(spotDirection, lightDirection);
    float atten = clamp(SdotL * spotAttenuation.x + spotAttenuation.y, 0.0, 1.0);
    return atten * atten;
}

Light GetMainLight() 
{
    Light light;
    light.direction = _MainLightDirection.xyz;

    // Directional light, so infinite. However, Unity uses .w of the position here (intensity field),
    // but also with lightmapping so... maybe incorrect. I'm not good at lighting.
    light.distanceAttenuation = 1.0;
    light.color = _MainLightColor.rgb;
    
    return light;
}

vec3 LightingLambert(vec3 lightColor, vec3 lightDir, vec3 normal)
{
    float NdotL = clamp(dot(normal, lightDir), 0.0, 1.0);
    return lightColor * NdotL;
}

int GetAdditionalLightsCount()
{
    return _AdditionalLightsCount;
}

Light GetAdditionalLight(int i, vec3 positionWS) 
{
    vec4 lightPositionWS = _AdditionalLightsPosition[i];
    vec4 distanceAndSpotAttenuation = _AdditionalLightsAttenuation[i]; 
    vec4 spotDirection = _AdditionalLightsSpotDir[i];

    /*
        Seems to be:
        color.multiply by intensity (linear or not)
        mcc is max color component (I guess whichever of the 3 is highest?)

        mcc_rcp = 1 / mcp 
        return (r * mcc_rcp, g * mcc_rcp, b * mcc_rcp)
        where rgb are from the results of multiplying the color
    */

    // Via: https://github.com/zhanmengao/Main/blob/dd0975a921154b1f943ddafbc335cab1f155cab5/%E5%A4%96%E9%83%A8%E5%BA%93%E6%BA%90%E7%A0%81/UnityCsEdit/UnityCsEdit/UnityCsReference-master/Runtime/Export/GI/Lightmapping.cs#L93
    vec3 color = pow(_AdditionalLightsColor[i].rgb, vec3(2.2)) * _AdditionalLightsColor[i].w;
    // float mcc_rcp = 1.0 / max(color.r, max(color.g, color.b));
    // color = color * mcc_rcp; 
    
    // TODO: Color is all wrong. It's too intense in the wrong places.
    // Might be linear/srgb color space issues, might be some math
    // from Unity that's precomputed that I'm missing, idk.
    // The color that Unity pushes for a (.54, .85, .55) -> (5.7, 16, 6)
    // for 22 intensity. So (c^2.2) * 22  for gamma correction

    // Directional lights store direction in lightPosition.xyz and have .w set to 0.0.
    // This way the following code will work for both directional and punctual lights.
    vec3 lightVector = lightPositionWS.xyz - positionWS * lightPositionWS.w;
    float distanceSqr = max(dot(lightVector, lightVector), 0.0000610352); // Nonzero distance
    
    vec3 lightDirection = lightVector * rsqrt(distanceSqr);
    float attenuation = DistanceAttenuation(distanceSqr, distanceAndSpotAttenuation.xy);
    attenuation *= AngleAttenuation(spotDirection.xyz, lightDirection, distanceAndSpotAttenuation.zw);

    Light light;
    light.direction = lightDirection;
    light.distanceAttenuation = attenuation;
    light.color = color;
    
    return light;
}

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

    vec3 finalColor = diffuseColor + _AmbientColor.rgb;

    FragColor = vec4(finalColor, 1);
} 
