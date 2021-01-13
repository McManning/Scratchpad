/**
 * Simple wireframing geometry shader to display tessellation results
 */
#version 450 core

layout (triangles) in;
layout (line_strip, max_vertices = 4) out;
// layout (triangle_strip, max_vertices = 4) out;

in TES_OUT {
    vec4 position;
    vec3 normal;
} IN[];

out GS_OUT {
    vec4 position;
    vec3 normal;
} OUT;

vec3 getNormal() {
    vec3 a = vec3(gl_in[0].gl_Position) - vec3(gl_in[1].gl_Position);
    vec3 b = vec3(gl_in[2].gl_Position) - vec3(gl_in[1].gl_Position);
    return normalize(cross(a, b));
}

void main() {
    for (int i = 0; i < 4; i++) {
        gl_Position = gl_in[i % 3].gl_Position;

        OUT.position = gl_Position;
        OUT.normal = IN[i % 3].normal;
        EmitVertex();
    }

    EndPrimitive();
}
