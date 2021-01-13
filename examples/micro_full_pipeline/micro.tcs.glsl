/**
 * Basic Phong Tessellation example
 *
 * References:
 * http://onrendering.blogspot.com/2011/12/tessellation-on-gpu-curved-pn-triangles.html
 */
#version 450 core

// NOTE: There is no way to change
layout (vertices = 3) out;

in VS_OUT {
    vec4 position;
    vec3 normal;
} IN[];

out TCS_OUT {
    vec4 position;
    vec3 normal;

    // Phong patch terms
    float termIJ;
    float termJK;
    float termIK;
} OUT[];

#define Pi gl_in[0].gl_Position.xyz
#define Pj gl_in[1].gl_Position.xyz
#define Pk gl_in[2].gl_Position.xyz

float PIi(int i, vec3 q)
{
    vec3 q_minus_p = q - gl_in[i].gl_Position.xyz;
    return q[gl_InvocationID] - dot(q_minus_p, IN[i].normal) * IN[i].normal[gl_InvocationID];
}

void main(void) {
    if (gl_InvocationID == 0) {
        gl_TessLevelInner[0] = 5.0;
        gl_TessLevelOuter[0] = 5.0;
        gl_TessLevelOuter[1] = 5.0;
        gl_TessLevelOuter[2] = 5.0;
    }

    gl_out[gl_InvocationID].gl_Position = gl_in[gl_InvocationID].gl_Position;

    OUT[gl_InvocationID].position = IN[gl_InvocationID].position;
    OUT[gl_InvocationID].normal = IN[gl_InvocationID].normal;

    // Compute Phong patch terms
    OUT[gl_InvocationID].termIJ = PIi(0, Pj) + PIi(1, Pi);
    OUT[gl_InvocationID].termJK = PIi(1, Pk) + PIi(2, Pj);
    OUT[gl_InvocationID].termIK = PIi(2, Pi) + PIi(0, Pk);
}
