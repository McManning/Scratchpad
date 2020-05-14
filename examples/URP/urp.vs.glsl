
#include "common.glsl"

in vec3 Position;
in vec3 Normal;

out VS_OUT {
    vec3 positionWS;
    vec3 normalWS;
} OUT;

void main()
{
    // gl_Position = ProjectionMatrix * ViewMatrix * ModelMatrix * vec4(position, 1.0);
    gl_Position = ModelViewProjectionMatrix * vec4(Position, 1.0);
    
    vec3 cameraPositionWS = CameraMatrix[3].xyz;
    vec3 positionWS = (ModelMatrix * vec4(Position, 1.0)).xyz;
    vec3 normalWS = (ModelMatrix * vec4(Normal, 0)).xyz;
    
    OUT.positionWS = positionWS;
    OUT.normalWS = normalWS;
}
