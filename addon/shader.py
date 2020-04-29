
import os
import numpy as np
from bgl import *
# from mathutils import Vector, Matrix, Quaternion

# Fallback shaders if custom shader compilation fails
VS_FALLBACK = '''
#version 330 core

uniform mat4 ModelViewProjectionMatrix;
uniform mat4 ModelMatrix;

in vec3 Position;
in vec3 Normal;

out VS_OUT {
    vec3 positionWS;
    vec3 normalWS;
} OUT;

void main()
{
    gl_Position = ModelViewProjectionMatrix * vec4(Position, 1.0);
    
    vec3 positionWS = (ModelMatrix * vec4(Position, 1.0)).xyz;
    vec3 normalWS = (ModelMatrix * vec4(Normal, 0)).xyz;
    
    OUT.positionWS = positionWS;
    OUT.normalWS = normalWS;
}
'''

FS_FALLBACK = '''
#version 330 core

uniform mat4 CameraMatrix;

layout (location = 0) out vec4 FragColor;

in VS_OUT { 
    vec3 positionWS;
    vec3 normalWS;
} IN;

void main()
{
    vec3 cameraPositionWS = CameraMatrix[3].xyz;

    vec3 eye = cameraPositionWS - IN.positionWS;
    float ndl = clamp(dot(IN.normalWS, normalize(eye)), 0.0, 1.0);
    
    vec3 inner = vec3(0.61, 0.54, 0.52);
    vec3 outer = vec3(0.27, 0.19, 0.18);
    vec3 highlight = vec3(0.98, 0.95, 0.92);
    
    FragColor = vec4(mix(outer, mix(inner, highlight, ndl * 0.25), ndl * 0.75), 1);
}
'''

# Skip geometry shader for fallback
GS_FALLBACK = None


class CompileError(Exception):
    pass


class LinkError(Exception):
    pass


def compile_shader(src: str, type_flag):
    shader = glCreateShader(type_flag)
    glShaderSource(shader, src)
    glCompileShader(shader)

    #Check for compile errors
    shader_ok = Buffer(GL_INT, 1)
    glGetShaderiv(shader, GL_COMPILE_STATUS, shader_ok)

    if shader_ok[0] == True:
        return shader

    # If not okay, read the error from GL logs
    bufferSize = 1024
    length = Buffer(GL_INT, 1)
    infoLog = Buffer(GL_BYTE, [bufferSize])
    glGetShaderInfoLog(shader, bufferSize, length, infoLog)

    if type_flag == GL_VERTEX_SHADER:
        stype = 'Vertex'
    elif type_flag == GL_FRAGMENT_SHADER:
        stype = 'Fragment'
    elif type_flag == GL_GEOMETRY_SHADER:
        stype = 'Geometry'
    
    # Reconstruct byte data into a string
    err = ''.join(chr(infoLog[i]) for i in range(length[0]))
    raise CompileError(stype + ' Shader Error:\n' + err)


class Shader:
    """Encapsulate shader compilation and configuration"""
    def __init__(self):
        self.program = None
        self.prev_mtimes = []

    def set_sources(self, vert: str, frag: str, geom: str = None):
        self.vert = vert 
        self.frag = frag 
        self.geom = geom
        # We keep prev_mtimes - in case this was called with the same files

    def compile_from_fallback(self):
        self.prev_mtimes = []
        self.compile_from_strings(VS_FALLBACK, FS_FALLBACK, GS_FALLBACK)

    def mtimes(self):
        """Aggregate file modication times from sources"""
        if not os.path.isfile(self.vert):
            raise FileNotFoundError('Missing required vertex shader')
            
        if not os.path.isfile(self.frag):
            raise FileNotFoundError('Missing required fragment shader')
            
        mtimes = [
            os.stat(self.vert).st_mtime,
            os.stat(self.frag).st_mtime
        ]

        if self.geom:
            mtimes.append(os.stat(self.geom).st_mtime)
        
        return mtimes

    def mtimes_changed(self) -> bool:
        """Check if the file update time has changed in any of the source files"""
        return self.prev_mtimes != self.mtimes()

    def recompile(self):
        with open(self.vert) as f:
            vs = f.read()
        
        with open(self.frag) as f:
            fs = f.read()
        
        gs = None
        if (self.geom):
            with open(self.geom) as f:
                gs = f.read()
                
        self.compile_from_strings(vs, fs, gs)
        self.prev_mtimes = self.mtimes()

    def compile_from_strings(self, vs: str, fs: str, gs: str = None):
        vertShader = compile_shader(vs, GL_VERTEX_SHADER)
        fragShader = compile_shader(fs, GL_FRAGMENT_SHADER)
        
        geomShader = None
        if gs: geomShader = compile_shader(gs, GL_GEOMETRY_SHADER)

        program = glCreateProgram()
        glAttachShader(program, vertShader)
        glAttachShader(program, fragShader)
        if gs: glAttachShader(program, geomShader)
            
        glLinkProgram(program)

        # Cleanup shaders
        glDeleteShader(vertShader)
        glDeleteShader(fragShader)
        if gs: glDeleteShader(geomShader)

        #Check for link errors
        link_ok = Buffer(GL_INT, 1)
        glGetProgramiv(program, GL_LINK_STATUS, link_ok)

        # If not okay, read the error from GL logs and report
        if link_ok[0] != True:
            self.program = None
            
            bufferSize = 1024
            length = Buffer(GL_INT, 1)
            infoLog = Buffer(GL_BYTE, [bufferSize])
            glGetProgramInfoLog(program, bufferSize, length, infoLog)
            
            err = ''.join(chr(infoLog[i]) for i in range(length[0]))
            raise LinkError(err)
            
        self.program = program
    
    def bind(self):
        glUseProgram(self.program)
        
    def unbind(self):
        pass
        
    def set_mat4(self, uniform: str, mat):
        location = glGetUniformLocation(self.program, uniform)
        if location < 0: return # Skip uniforms that were optimized out for being unused

        mat_buffer = np.reshape(mat, (16, )).tolist()
        mat_buffer = Buffer(GL_FLOAT, 16, mat_buffer)
        glUniformMatrix4fv(location, 1, GL_FALSE, mat_buffer)

    def set_vec3_array(self, uniform: str, arr):
        location = glGetUniformLocation(self.program, uniform)
        if location < 0: return

        buffer = Buffer(GL_FLOAT, len(arr), arr)
        glUniform3fv(location, len(arr), buffer)
        
    def set_vec4_array(self, uniform: str, arr):
        location = glGetUniformLocation(self.program, uniform)
        if location < 0: return

        buffer = Buffer(GL_FLOAT, len(arr), arr)
        glUniform4fv(location, len(arr), buffer)
    
    def set_int(self, uniform: str, value: int):
        location = glGetUniformLocation(self.program, uniform)
        if location < 0: return

        glUniform1i(location, value)

    def set_vec3(self, uniform: str, value):
        location = glGetUniformLocation(self.program, uniform)
        if location < 0: return

        glUniform3f(location, value[0], value[1], value[2])
        
    def set_vec4(self, uniform: str, value):
        location = glGetUniformLocation(self.program, uniform)
        if location < 0: return

        glUniform4f(location, value[0], value[1], value[2], value[3])
        
    def set_vertex_attribute(self, name: str, stride: int):
        """Enable a vertex attrib array and set the pointer for GL_ARRAY_BUFFER reads"""
        location = glGetAttribLocation(self.program, name)
        glEnableVertexAttribArray(location)
        glVertexAttribPointer(location, 3, GL_FLOAT, GL_FALSE, stride, 0)
