# Shader Variables

Built-in global variables for GLSL shaders

## Inputs

||Name|Description
|---|---|---
|vec3|Position|Vertex local space position
|vec3|Normal|

Not implemented but planned:

||Name|Description
|---|---|---
|vec3|Tangent|
|vec4|Binormal|
|vec4|Color|Vertex color
|vec4|Texcoord0-7|UV coordinates

## Transformations

||Name|Description
|---|---|---
|mat4|ModelMatrix|
|mat4|ViewMatrix|
|mat4|ProjectionMatrix|
|mat4|ModelViewMatrix|
|mat4|ModelViewProjectionMatrix|
|mat4|CameraMatrix|View inverse matrix

## Lighting

### Main Light

||Name|Description
|---|---|---
|vec4|_MainLightDirection|Equivalent to `_MainLightPosition` in Unity URP
|vec4|_MainLightColor|`.w` stores the intensity value
|vec3|_AmbientColor|

### Additional Lights

Packed data for additional spot and point lights in the scene.

Packed similar to Unity's URP, except the set of lights is global to the scene rather than per object.

||Name|Description
|---|---|---
|int|_AdditionalLightsCount|Number of lights in the vec4 buffers
|vec4[]|_AdditionalLightsPosition|
|vec4[]|_AdditionalLightsColor|
|vec4[]|_AdditionalLightsSpotDir|
|vec4[]|_AdditionalLightsAttenuation|
