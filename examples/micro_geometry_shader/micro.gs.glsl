/**
 * Simple example geometry shader to explode faces on animation frames
 *
 * @author https://learnopengl.com/Advanced-OpenGL/Geometry-Shader
 */
#version 410 core

layout (triangles) in;
layout (triangle_strip, max_vertices = 3) out;

in TCS_OUT {
    vec3 positionWS;
    vec3 normalWS;
} IN[];

out GS_OUT {
    vec3 positionWS;
    vec3 normalWS;
} OUT;

vec3 getNormal() {
    vec3 a = vec3(gl_in[0].gl_Position) - vec3(gl_in[1].gl_Position);
    vec3 b = vec3(gl_in[2].gl_Position) - vec3(gl_in[1].gl_Position);
    return normalize(cross(a, b));
}

vec4 explode(vec4 position, vec3 normal) {
    float magnitude = 0.2;
    float frame = 1.0; // If there was a frame/time uniform, we'd use that instead.

    vec3 direction = normal * ((sin(frame * 0.1) + 1.0) / 2.0) * magnitude;
    return position + vec4(direction, 0.0);
}

void main() {
    vec3 normal = getNormal();

    gl_Position = explode(gl_in[0].gl_Position, normal);
    OUT.positionWS = IN[0].positionWS;
    OUT.normalWS = IN[0].normalWS;
    EmitVertex();

    gl_Position = explode(gl_in[1].gl_Position, normal);
    OUT.positionWS = IN[1].positionWS;
    OUT.normalWS = IN[1].normalWS;
    EmitVertex();

    gl_Position = explode(gl_in[2].gl_Position, normal);
    OUT.positionWS = IN[2].positionWS;
    OUT.normalWS = IN[2].normalWS;
    EmitVertex();

    EndPrimitive();
}
