
// Transformation matrices
uniform mat4 ModelMatrix;
uniform mat4 ViewMatrix;
uniform mat4 ModelViewMatrix;
uniform mat4 ProjectionMatrix;
uniform mat4 ModelViewProjectionMatrix;
uniform mat4 CameraMatrix;

// Lighting
uniform vec4 _MainLightDirection;
uniform vec4 _MainLightColor;
uniform vec3 _AmbientColor;

// Scene information
uniform float _Time; // Not yet supported
uniform int _Frame;
