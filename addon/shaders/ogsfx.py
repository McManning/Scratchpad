
import os 
from typing import List

from .base import (
    Shader, 
    VertexData, 
    LightData
)

from .fallback import (
    VS_FALLBACK,
    FS_FALLBACK
)

class OGSFXShader(Shader):
    """Load an OGSFX source file as a shader"""
    name = 'Maya OGSFX'

    def update_settings(self, settings):
        if not os.path.isfile(settings.ogsfx_filename):
            raise FileNotFoundError('Missing required OGSFX file')
        
        self.filename = settings.ogsfx_filename
        self.monitored_files = [settings.ogsfx_filename]

    def update_shader_properties(self, settings):
        self.properties.from_property_group(settings)
        # TODO: Texture reloading or something? Here or in the ShaderProperties?

    def recompile(self):
        # For now, uses fallback
        self.compile_from_strings(VS_FALLBACK, FS_FALLBACK)
        self.update_mtimes()

        # Pretend some settings have loaded from the .ogsfx
        self.properties.clear()
        self.properties.add('fizz', 'Some Fizz', 'float', 0.5)
        self.properties.add('buzz', 'so buzz', 'float', 0, 0, 1.0)
        self.properties.add('my_color', 'my color', 'color', (1.0, 0.15, 0.15))
        self.properties.add('my_bool', 'Some boolean prop', 'boolean', True)

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
        # No lighting information used for the fallback
        pass

    def create_vertex_data(self) -> VertexData:
        data = VertexData()
        data.use_standard_format()
        return data

    def upload_vertex_data(self, data: VertexData):
        data.upload_standard_format(self)

    def bind(self):
        super(OGSFXShader, self).bind()
        # Other setup work
        
    def unbind(self):
        super(OGSFXShader, self).unbind()
        