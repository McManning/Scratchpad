
import os 

from .base import (
    Shader, 
    VertexData, 
    LightData, 
    ShaderData
)

# from ..loader.glsl import load_shader 

class GLSLShader(Shader):
    """Direct GLSL shader from GLSL source files"""
    name = 'GLSL'

    def load_from_settings(self, settings):
        self.vert = settings.vert_filename 
        self.frag = settings.frag_filename 
        self.geom = settings.geom_filename 
        
        if not os.path.isfile(self.vert):
            raise FileNotFoundError('Missing required vertex shader')
            
        if not os.path.isfile(self.frag):
            raise FileNotFoundError('Missing required fragment shader')
        
        self.monitored_files = [
            settings.vert_filename,
            settings.frag_filename
        ]

        if self.geom:
            self.monitored_files.append(self.geom)

        # We keep prev_mtimes - in case this was called with the same files

    def get_settings(self) -> ShaderData:
        # No settings
        return None

    def recompile(self):
        # TODO: Integrate load_shader()
        with open(self.vert) as f:
            vs = f.read()
        
        with open(self.frag) as f:
            fs = f.read()
        
        gs = None
        if (self.geom):
            with open(self.geom) as f:
                gs = f.read()
                
        self.compile_from_strings(vs, fs, gs)
        self.update_mtimes()

    def set_camera_matrices(self, view_matrix, projection_matrix):
        self.view_matrix = view_matrix
        self.projection_matrix = projection_matrix

        self.set_mat4("ViewMatrix", view_matrix.transposed())
        self.set_mat4("ProjectionMatrix", projection_matrix.transposed())
        self.set_mat4("CameraMatrix", view_matrix.inverted().transposed())

    def set_object_matrices(self, model_matrix):
        mv = self.view_matrix @ model_matrix
        mvp = self.projection_matrix @ mv

        self.set_mat4("ModelMatrix", model_matrix.transposed())
        self.set_mat4("ModelViewMatrix", mv.transposed())
        self.set_mat4("ModelViewProjectionMatrix", mvp.transposed())
        
    def set_lights(self, data: LightData):
        """Copy lighting information into shader uniforms
        
        This is inspired by Unity's LWRP where there is a main directional light
        and a number of secondary lights packed into an array buffer. 

        This particular implementation doesn't account for anything advanced
        like shadows, light cookies, etc. 
        """
        limit = 16

        positions = [0] * (limit * 4)
        directions = [0] * (limit * 4)
        colors = [0] * (limit * 4)
        attenuations = [0] * (limit * 4)

        # Feed lights into buffers
        i = 0
        for light in data.additional_lights.values():
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
        
        if data.main_light:
            self.set_vec4("_MainLightDirection", data.main_light.direction)
            self.set_vec4("_MainLightColor", data.main_light.color)

        self.set_int("_AdditionalLightsCount", i)
        self.set_vec4_array("_AdditionalLightsPosition", positions)
        self.set_vec4_array("_AdditionalLightsColor", colors)
        self.set_vec4_array("_AdditionalLightsSpotDir", directions)
        self.set_vec4_array("_AdditionalLightsAttenuation", attenuations)
        
        self.set_vec3("_AmbientColor", data.ambient_color)

    def create_vertex_data(self) -> VertexData:
        data = VertexData()
        data.use_standard_format()
        return data

    def upload_vertex_data(self, data: VertexData):
        data.upload_standard_format(self)
