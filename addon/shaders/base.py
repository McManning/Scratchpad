
import os
import json
import numpy as np
from bgl import *

class CompileError(Exception):
    pass

class LinkError(Exception):
    pass

class ShaderProperties:
    """ Collection of user-editable properties that can be changed 
        on a per-shader instance basis. For example, editable uniforms
        within an OGSFX file
    """
    def __init__(self):
        self.clear()

    def add(
        self, 
        field_type: str, 
        key: str, 
        title: str,
        description: str  = '', 
        default_value = None,
        min_value: float = float('-inf'), 
        max_value: float = float('inf')
    ):
        """Add a new dynamic property

        Parameters:
            field_type (enum):       One of the accepted property types
            key (str):              Lookup key for reading the value back
            title (str):            Human readable title
            description (str):      Hover description block for Blender
            default_value (mixed):  Initial value, if not set
            min_value (float):      Minimum value for field_type `float`
            max_value (float):      Maximum value for field_type `float`
        """
        self.definitions.append(
            (field_type, key, title, description, default_value, min_value, max_value)
        )
        self.values[key] = default_value
    
    def clear(self):
        self.definitions = []
        self.values = {}

    def from_property_group(self, settings):
        """Load current values from a PropertyGroup"""
        for key in self.values.keys():
            self.values[key] = getattr(settings, key)

        # TODO: Should this also perform UPLOAD for the shader (textures, etc)
        # I would assume so, right? 

def compile_glsl(src: str, stage_flag: int) -> int:
    shader = glCreateShader(stage_flag)
    glShaderSource(shader, src)
    glCompileShader(shader)

    # Check for compile errors
    shader_ok = Buffer(GL_INT, 1)
    glGetShaderiv(shader, GL_COMPILE_STATUS, shader_ok)

    if shader_ok[0] == True:
        return shader

    # If not okay, read the error from GL logs
    bufferSize = 1024
    length = Buffer(GL_INT, 1)
    infoLog = Buffer(GL_BYTE, [bufferSize])
    glGetShaderInfoLog(shader, bufferSize, length, infoLog)

    if stage_flag == GL_VERTEX_SHADER:
        stage = 'Vertex'
    elif stage_flag == GL_FRAGMENT_SHADER:
        stage = 'Fragment'
    elif stage_flag == GL_TESS_CONTROL_SHADER:
        stage = 'Tessellation Control'
    elif stage_flag == GL_TESS_EVALUATION_SHADER:
        stage = 'Tessellation Evaluation'
    elif stage_flag == GL_GEOMETRY_SHADER:
        stage = 'Geometry'
    
    # Reconstruct byte data into a string
    err = ''.join(chr(infoLog[i]) for i in range(length[0]))
    raise CompileError(stage + ' Shader Error:\n' + err)


class BaseShader:
    """Base encapsulation of shader compilation and configuration.
    
    Different shader abstraction formats inherit from this base, 
    but ultimately they all end up as GLSL one way or another
    """
    def __init__(self):
        self.program = None
        self.prev_mtimes = []
        self.monitored_files = []

    def needs_recompile(self) -> bool:
        """Does this shader need to be recompiled from updated settings"""
        return self.mtimes_changed()

    def update_mtimes(self):
        self.prev_mtimes = self.mtimes()

    def mtimes(self):
        """Aggregate file modication times from monitored files"""
        return [os.stat(file).st_mtime for file in self.monitored_files]

    def mtimes_changed(self) -> bool:
        """Check if the file update time has changed in any of the source files"""
        return self.prev_mtimes != self.mtimes()

    def compile_from_strings(self, vs: str, fs: str, tcs: str = None, tes: str = None, gs: str = None):
        vs_compiled = compile_glsl(vs, GL_VERTEX_SHADER)
        fs_compiled = compile_glsl(fs, GL_FRAGMENT_SHADER)
        tcs_compiled = compile_glsl(gs, GL_TESS_CONTROL_SHADER) if tcs else None
        tes_compiled = compile_glsl(gs, GL_TESS_EVALUATION_SHADER) if tes else None
        gs_compiled = compile_glsl(gs, GL_GEOMETRY_SHADER) if gs else None

        program = glCreateProgram()
        glAttachShader(program, vs_compiled)
        glAttachShader(program, fs_compiled)
        if tcs: glAttachShader(program, tcs_compiled)
        if tes: glAttachShader(program, tes_compiled)
        if gs: glAttachShader(program, gs_compiled)
            
        glLinkProgram(program)

        # Cleanup shaders
        glDeleteShader(vs_compiled)
        glDeleteShader(fs_compiled)
        if tcs: glDeleteShader(tcs_compiled)
        if tes: glDeleteShader(tes_compiled)
        if gs: glDeleteShader(gs_compiled)

        # Check for link errors
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

    def set_float(self, uniform: str, value: float):
        location = glGetUniformLocation(self.program, uniform)
        if location < 0: return
        glUniform1f(location, value)

    def set_vec3(self, uniform: str, value):
        location = glGetUniformLocation(self.program, uniform)
        if location < 0: return

        glUniform3f(location, value[0], value[1], value[2])
        
    def set_vec4(self, uniform: str, value):
        location = glGetUniformLocation(self.program, uniform)
        if location < 0: return

        glUniform4f(location, value[0], value[1], value[2], value[3])
        
    def bind_texture(self, idx: int, uniform: str, image):
        location = glGetUniformLocation(self.program, uniform)
        if location < 0: return

        # If it's not on the GPU yet, get Blender to upload it.
        if image.bindcode < 1:
            image.gl_load()
        
        # TODO: glTexParameteri calls
        glActiveTexture(GL_TEXTURE0 + idx)
        glBindTexture(GL_TEXTURE_2D, image.bindcode)
        glUniform1i(location, idx)

    # Core methods to be implemented by different shader formats

    def update_settings(self, settings):
        """Read settings universal to the renderer
        
        Parameters:
            settings (ScratchpadSettings): Instance to read
        """
        pass

    def get_renderer_properties(self):
        """Retrieve a ShaderProperties for dynamic renderer properties

        Returns:
            ShaderProperties
        """
        return None

    def update_renderer_properties(self, settings):
        """Update ShaderProperties from the PropertyGroup
        
        Parameters:
            settings (PropertyGroup): Instance to read
        """
        pass

    def get_material_properties(self):
        """Retrieve a ShaderProperties for dynamic per-material properties

        Returns:
            ShaderProperties
        """
        return None

    def update_material_properties(self, settings):
        """Update ShaderProperties from the PropertyGroup

        Parameters:
            settings (PropertyGroup): Instance to read
        """
        pass

    def recompile(self):
        """Recompile the shader from sources"""
        raise NotImplementedError('Must be implemented by a concrete class')

    def set_camera_matrices(self, view_matrix, projection_matrix):
        """Set per-camera matrices"""
        raise NotImplementedError('Must be implemented by a concrete class')

    def set_object_matrices(self, model_matrix):
        """Set per-object matrices"""
        raise NotImplementedError('Must be implemented by a concrete class')
        
    def set_lighting(self, lighting):
        """Set lighting uniforms
        
        Parameters:
            lighting (SceneLighting): Current scene lighting information
        """
        raise NotImplementedError('Must be implemented by a concrete class')
