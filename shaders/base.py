
import os
import json
import numpy as np
from bgl import *

class CompileError(Exception):
    pass

class LinkError(Exception):
    pass

# TODO: Third exception class for throwing from within compile().
# I want logic in CompileError/LinkError to handle GLSL specific
# error messages and format the results nicely (e.g. syntax errors
# for specific files and lines). 

class ShaderProperties:
    """ Collection of user-editable properties that can be changed 
        on a per-shader instance basis. For example, editable uniforms
        within an OGSFX file
    """
    # Allowable field types that match up with register_dynamic_property_group.
    FIELD_TYPES = [
        'float', 'color', 'boolean', 
        'vec2', 'vec3', 'vec4',
        'source_file', 'image'
    ]

    def __init__(self):
        self.definitions = []
        self.values = {}

    @property
    def is_empty(self):
        return len(self.definitions) < 1

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
            field_type (str):       One of `ShaderProperties.FIELD_TYPES`
            key (str):              Lookup key for reading the value back
            title (str):            Human readable title
            description (str):      Hover description block for Blender
            default_value (mixed):  Initial value, if not set
            min_value (float):      Minimum value for field_type `float`
            max_value (float):      Maximum value for field_type `float`
        """
        if field_type not in self.FIELD_TYPES:
            raise Exception(
                'Field type `{}` not supported by ShaderProperties'.format(field_type)
            )

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
    buffer_size = 1024
    length = Buffer(GL_INT, 1)
    info_log = Buffer(GL_BYTE, [buffer_size])
    glGetShaderInfoLog(shader, buffer_size, length, info_log)

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
    err = ''.join(chr(info_log[i]) for i in range(length[0]))
    raise CompileError(stage + ' Shader Error:\n' + err)

def compile_program(vs: str, fs: str, tcs: str = None, tes: str = None, gs: str = None):
    """Compile a new GL program from the given source strings
        
    Parameters:
        vs (str): Vertex shader source
        fs (str): Fragment shader source
        tcs (str): Tessellation control shader source
        tes (str): Tessellation evaluation shader source
        gs (str): Geometry shader source

    Returns:
        New GL Program
    """
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
        bufferSize = 1024
        length = Buffer(GL_INT, 1)
        infoLog = Buffer(GL_BYTE, [bufferSize])
        glGetProgramInfoLog(program, bufferSize, length, infoLog)
        
        err = ''.join(chr(infoLog[i]) for i in range(length[0]))
        raise LinkError(err)

    return program 

class BaseShader:
    """Base encapsulation of shader compilation and configuration.
    
    Different shader abstraction formats inherit from this base 
    but ultimately they all end up as GLSL one way or another

    Attributes:
        program (int): 
        last_error (str): Last error message by a call to compile()
        watched (list[str]): List of filenames to monitor for disk changes
        prev_mtimes (list[int]): mtimes recorded for all monitored files
    """

    # program: int
    # last_error: str
    # watched: list 
    # prev_mtimes: list

    def __init__(self):
        self.program = -1
        self.last_error = None
        self.watched = []
        self.prev_mtimes = []

    @property
    def is_compiled(self) -> bool:
        return self.program > -1 and glIsProgram(self.program)

    def needs_recompile(self) -> bool:
        """Does this shader need to be recompiled from updated settings"""
        return not self.is_compiled or self.mtimes_changed()

    def update_mtimes(self):
        self.prev_mtimes = self.mtimes()

    def mtimes(self):
        """Aggregate file modication times from monitored files"""
        return [os.stat(file).st_mtime for file in self.watched]

    def mtimes_changed(self) -> bool:
        """Check if the file update time has changed in any of the source files"""
        return self.prev_mtimes != self.mtimes() 

    def watch(files: list):
        """Monitor one or more files for changes on disk.

        This replaces the previous watchlist with a new one.

        Parameters:
            files (list[str]): List of filenames to monitor
        """
        self.watched = files
        # We keep mtimes as-is, in case they changed the file   
        # list to the same values and order. 
        
    def set_mat4(self, uniform: str, mat):
        """Set a mat4 uniform

        Parameters:
            uniform (str)
            value (mathutils.Quaternion | list[float])
        """
        location = glGetUniformLocation(self.program, uniform)
        if location < 0: return # Skip uniforms that were optimized out for being unused

        mat_buffer = np.reshape(mat, (16, )).tolist()
        mat_buffer = Buffer(GL_FLOAT, 16, mat_buffer)
        glUniformMatrix4fv(location, 1, GL_FALSE, mat_buffer)

    def set_vec3_array(self, uniform: str, arr):
        """Set a vec3[] uniform

        Parameters:
            uniform (str)
            value (list[mathutils.Vector | list[float]])
        """
        location = glGetUniformLocation(self.program, uniform)
        if location < 0: return

        buffer = Buffer(GL_FLOAT, len(arr), arr)
        glUniform3fv(location, len(arr), buffer)
        
    def set_vec4_array(self, uniform: str, arr: list):
        """Set a vec4[] uniform

        Parameters:
            uniform (str)
            value (list[mathutils.Vector | list[float]])
        """
        location = glGetUniformLocation(self.program, uniform)
        if location < 0: return

        buffer = Buffer(GL_FLOAT, len(arr), arr)
        glUniform4fv(location, len(arr), buffer)
    
    def set_int(self, uniform: str, value: int):
        """Set an int uniform

        Parameters:
            uniform (str)
            value (int)
        """
        location = glGetUniformLocation(self.program, uniform)
        if location < 0: return

        glUniform1i(location, value)

    def set_float(self, uniform: str, value: float):
        """Set a float uniform

        Parameters:
            uniform (str)
            value (float)
        """
        location = glGetUniformLocation(self.program, uniform)
        if location < 0: return
        glUniform1f(location, value)

    def set_vec3(self, uniform: str, value):
        """Set a vec3 uniform

        Parameters:
            uniform (str)
            value (mathutils.Vector | list[float])
        """
        location = glGetUniformLocation(self.program, uniform)
        if location < 0: return

        glUniform3f(location, value[0], value[1], value[2])
        
    def set_vec4(self, uniform: str, value):
        """Set a vec4 uniform

        Parameters:
            uniform (str)
            value (mathutils.Vector | list[float])
        """
        location = glGetUniformLocation(self.program, uniform)
        if location < 0: return

        glUniform4f(location, value[0], value[1], value[2], value[3])
        
    def bind_texture(self, idx: int, uniform: str, image):
        """Bind a `bpy.types.Image` to GL

        Parameters:
            idx (int):                  Offset from GL_TEXTURE0 to bind
            uniform (str):              Uniform name to bind the texture
            image (bpy.types.Image):    Source image in Blender
        """
        location = glGetUniformLocation(self.program, uniform)
        if location < 0: return

        # If it's not on the GPU yet, get Blender to upload it.
        if image.bindcode < 1:
            image.gl_load()
        
        # TODO: glTexParameteri calls
        glActiveTexture(GL_TEXTURE0 + idx)
        glBindTexture(GL_TEXTURE_2D, image.bindcode)
        glUniform1i(location, idx)

    # Methods to be implemented by different shader formats

    def bind(self, render_pass: str):
        """Bind the GL program for the given pass
        
        Properties:
            render_pass (str): Pass name. E.g. `Shadow`, `Main`
        """
        # Override to handle binding on each pass. E.g. switching programs
        # or updating uniform values to represent that pass.

        # TODO: Rename pass to Technique? A shader may contain multiple passes,
        # but under a specific technique (e.g. for composite or for shadowing z-depth)
        glUseProgram(self.program)
        
    def unbind(self):
        """Cleanup this shader after all meshes have rendered with it
        
        This method is called after each pass
        """
        pass
        
    def set_camera_matrices(self, view_matrix, projection_matrix):
        """Set per-camera matrices
        
        Parameters:
            view_matrix (mathutils.Quaternion)
            projection_matrix (mathutils.Quaternion)
        """
        self.view_matrix = view_matrix
        self.projection_matrix = projection_matrix

        self.set_mat4("ViewMatrix", view_matrix.transposed())
        self.set_mat4("ProjectionMatrix", projection_matrix.transposed())
        self.set_mat4("CameraMatrix", view_matrix.inverted().transposed())

    def set_object_matrices(self, model_matrix):
        """Set per-object matrices
        
        Parameters:
            model_matrix (mathutils.Quaternion)
        """
        mv = self.view_matrix @ model_matrix
        mvp = self.projection_matrix @ mv

        self.set_mat4("ModelMatrix", model_matrix.transposed())
        self.set_mat4("ModelViewMatrix", mv.transposed())
        self.set_mat4("ModelViewProjectionMatrix", mvp.transposed())
        
    def get_properties(self):
        """Retrieve a ShaderProperties for non-material properties specific to this shader.
        
        For example, this includes source files to monitor or different renderer
        properties to enable independent of the material properties. 
    
        Any properties that may trigger a recompile of the shader program(s) 
        should be placed within this ShaderProperties group.

        If your shader does not contain properties, return None

        Returns:
            ShaderProperties | None
        """
        return None

    def update_properties(self, props):
        """Update ShaderProperties from the PropertyGroup
        
        Parameters:
            props (BaseDynamicMaterialProperties): Instance to read
        """
        pass

    def get_material_properties(self):
        """Retrieve a ShaderProperties for dynamic per-material properties

        These are properties that would be passed into uniforms or texture
        samplers within a shader program. E.g. the albedo or emissive texture
        and color of a material provided by the artist. 

        If your shader does not contain material properties, return None

        Returns:
            ShaderProperties | None
        """
        return None

    def update_material_properties(self, props):
        """Update ShaderProperties from the PropertyGroup

        Parameters:
            props (BaseDynamicMaterialProperties): Instance to read
        """
        # TODO: Rename. These are dynamic properties stored
        # on bpy.types.Material.scratchpad_dynamic
        pass

    def compile(self):
        """Compile the shader from sources

        This method may be called whenever watched files are modified
        or another event triggers a recompilation.
        
        Throwing exceptions during compilation will be caught and reported to the user.
        It is recommended that either a `CompileError` or `LinkError` be thrown.
        
        A successful compilation will set `self.program` to a valid GLSL program.
        """
        raise NotImplementedError('Must be implemented by a concrete class')

    def set_lighting(self, lighting):
        """Set lighting uniforms from scene light data
        
        Parameters:
            lighting (SceneLighting): Current scene lighting information
        """
        pass
