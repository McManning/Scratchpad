/**
 * Basic Phong Tessellation example
 *
 * References:
 * http://onrendering.blogspot.com/2011/12/tessellation-on-gpu-curved-pn-triangles.html
 */
#version 450 core

layout (triangles, fractional_odd_spacing, cw) in;

uniform mat4 ModelViewProjectionMatrix;
uniform mat4 ViewMatrix;
uniform mat4 ProjectionMatrix;
uniform mat4 ModelMatrix;

in TCS_OUT {
    vec4 position;
    vec3 normal;

    // Phong patch terms
    float termIJ;
    float termJK;
    float termIK;
} IN[];

out TES_OUT {
    vec4 position;
    vec3 normal;
} OUT;

#define Pi gl_in[0].gl_Position.xyz
#define Pj gl_in[1].gl_Position.xyz
#define Pk gl_in[2].gl_Position.xyz

void main(void) {
    vec3 tc1 = gl_TessCoord;
    vec3 tc2 = gl_TessCoord * gl_TessCoord;

    // interpolated position
    vec3 pos = tc1[0] * Pi + tc1[1] * Pj + tc1[2] * Pk;

    vec3 termIJ = vec3(IN[0].termIJ, IN[1].termIJ, IN[2].termIJ);
    vec3 termJK = vec3(IN[0].termJK, IN[1].termJK, IN[2].termJK);
    vec3 termIK = vec3(IN[0].termIK, IN[1].termIK, IN[2].termIK);

    // Phong position from terms
    vec3 phongPos   = tc2[0] * Pi
                    + tc2[1] * Pj
                    + tc2[2] * Pk
                    + tc1[0] * tc1[1] * termIJ
                    + tc1[1] * tc1[2] * termJK
                    + tc1[2] * tc1[0] * termIK;

    float alpha = 0.5;

    // Final blended position in
    vec3 finalPos = (1.0 - alpha) * pos + alpha * phongPos;
    gl_Position = ProjectionMatrix * ViewMatrix * vec4(finalPos, 1.0);

    // Interpolate outputs
    OUT.position = gl_Position;

    // TODO: Fix interp
    OUT.normal =    gl_TessCoord.x * IN[0].normal +
                    gl_TessCoord.y * IN[1].normal +
                    gl_TessCoord.z * IN[2].normal;

}
