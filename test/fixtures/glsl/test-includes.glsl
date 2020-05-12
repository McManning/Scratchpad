
#include <include.glslv>

#include "include-with-guard.glsl"

float foobar() {
    return 1.2;
}

#include "include-with-guard.glsl"

// main
void main() {
    gl_Position = vec4(0, 0, 0, 1);
}
