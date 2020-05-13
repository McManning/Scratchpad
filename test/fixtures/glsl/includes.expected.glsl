#line 2 1
vec3 Foo() {
    return vec3(1, 0, 0);
}
#line 5 2
float IncludeGuardFunc()
{
    return 1.0;
}
#line 6 0
float foobar() {
    return 1.2;
}




void main() {
    gl_Position = vec4(0, 0, 0, 1);
}
