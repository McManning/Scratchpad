
import os
from time import time

from ..base import (
    BaseShader, 
    ShaderProperties,
    compile_program
)

from .preprocessor import GLSLPreprocessor

class GLSLShader(BaseShader):
    """Direct GLSL shader from GLSL source files"""

    # Version directive to automatically add to source files
    COMPAT_VERSION = '330 core'

    # Maximum lights to send to shaders as _AdditionalLights* uniforms
    MAX_ADDITIONAL_LIGHTS = 16

    def __init__(self):
        super(GLSLShader, self).__init__()

        self.properties = ShaderProperties()
        # self.properties.add('boolean', 'use_composite_file', 'Use Separate Stage Sources', '')
        # self.properties.add('source_file', 'composite_file', 'Source File', 'GLSL Source file containing all stages')

        self.properties.add('source_file', 'vert_filename', 'Vertex', 'GLSL Vertex shader source file')
        self.properties.add('source_file', 'tesc_filename', 'Tessellation Control', 'GLSL Tessellation Control shader source file')
        self.properties.add('source_file', 'tese_filename', 'Tessellation Evaluation', 'GLSL Tessellation Evaluation shader source file')
        self.properties.add('source_file', 'geom_filename', 'Geometry', 'GLSL Geometry shader source file')
        self.properties.add('source_file', 'frag_filename', 'Fragment', 'GLSL Fragment shader source file')

        self.material_properties = ShaderProperties()
        self.material_properties.add('float', 'my_float', 'My Float', 'Something about my float', 0.5, 0, 1)
        self.material_properties.add('image', 'diffuse', 'Diffuse', 'Diffuse color channel texture')

    def get_properties(self):
        return self.properties

    def update_properties(self, props):
        self.properties.from_property_group(props)
        
        # Check for minimum required files
        if not os.path.isfile(props.vert_filename):
            raise FileNotFoundError('Missing required vertex shader')
            
        if not os.path.isfile(props.frag_filename):
            raise FileNotFoundError('Missing required fragment shader')
        
        self.stages = { 
            'vs': props.vert_filename,
            'tcs': props.tesc_filename, 
            'tes': props.tese_filename,
            'gs': props.geom_filename,
            'fs': props.frag_filename
        }

        # Monitor each stage file for changes
        self.watch([f for f in self.stages.values() if f])
        
    def get_material_properties(self):
        return self.material_properties

    def update_material_properties(self, props):
        self.material_properties.from_property_group(props)

        self.diffuse = props.diffuse

    def compile(self):
        sources = {}

        # Mapping between a shader stage and array of include files.
        # Used for resolving the source of compilation errors
        # TODO: Implement as part of the compilation process - somehow.
        # (Probably as a feature of base shader - since everything can do this)
        self.includes = {}
        
        preprocessor = GLSLPreprocessor()

        for stage, filename in self.stages.items():
            source = None
            if filename:
                # TODO: Stage defines (e.g. #define VERTEX - useful?)
                # Would be more useful if there was a single input field
                source = '#version {}\n{}'.format(
                    self.COMPAT_VERSION, 
                    preprocessor.parse_file(filename)
                )
                self.includes[stage] = preprocessor.includes

            sources[stage] = source

        # We update mtimes first so that if a compilation fails
        # we can still detect file changes
        self.update_mtimes()

        self.program = compile_program(
            sources['vs'], 
            sources['fs'], 
            sources['tcs'], 
            sources['tes'], 
            sources['gs']
        )

    def bind_textures(self):
        # TODO: WIP
        if self.diffuse:
            print('binding diffuse', self.diffuse.bindcode)
            self.bind_texture(0, 'diffuse', self.diffuse)
        else:
            print('no diffuse')

    def bind(self, render_pass: str):
        """Bind the GL program for the given pass
        
        Properties:
            render_pass (str): Pass name. E.g. `Shadow`, `Main`
        """
        super(GLSLShader, self).bind(render_pass)
        self.bind_textures()

    def set_lighting(self, lighting):
        """Copy lighting information into shader uniforms
        
        This is inspired by Unity's URP where there is a main directional light
        and a number of secondary lights packed into an array buffer. 

        This particular implementation doesn't account for anything advanced
        like shadows, light cookies, etc. Nor does it try to calculate per-object
        light arrays to support a ridiculous number of lights. 

        Parameters:
            lighting (SceneLighting): Current scene lighting information
        """
        limit = self.MAX_ADDITIONAL_LIGHTS

        positions = [0] * (limit * 4)
        directions = [0] * (limit * 4)
        colors = [0] * (limit * 4)
        attenuations = [0] * (limit * 4)

        # Feed lights into buffers
        i = 0
        for light in lighting.additional_lights.values():
            # print('Light', i)
            v = light.position
            # print('    Position', v)
            positions[i * 4] = v[0]
            positions[i * 4 + 1] = v[1]
            positions[i * 4 + 2] = v[2]
            positions[i * 4 + 3] = v[3]
            
            v = light.direction
            # print('    Direction', v)
            directions[i * 4] = v[0]
            directions[i * 4 + 1] = v[1]
            directions[i * 4 + 2] = v[2]
            directions[i * 4 + 3] = v[3]

            v = light.color
            # print('    Color', v)
            colors[i * 4] = v[0]
            colors[i * 4 + 1] = v[1]
            colors[i * 4 + 2] = v[2]
            colors[i * 4 + 3] = v[3]

            v = light.attenuation
            # print('    Attenuation', v)
            attenuations[i * 4] = v[0]
            attenuations[i * 4 + 1] = v[1]
            attenuations[i * 4 + 2] = v[2]
            attenuations[i * 4 + 3] = v[3]

            i += 1
        
        if lighting.main_light:
            self.set_vec4("_MainLightDirection", lighting.main_light.direction)
            self.set_vec4("_MainLightColor", lighting.main_light.color)

        self.set_int("_AdditionalLightsCount", i)
        self.set_vec4_array("_AdditionalLightsPosition", positions)
        self.set_vec4_array("_AdditionalLightsColor", colors)
        self.set_vec4_array("_AdditionalLightsSpotDir", directions)
        self.set_vec4_array("_AdditionalLightsAttenuation", attenuations)
        
        self.set_vec3("_AmbientColor", lighting.ambient_color)
