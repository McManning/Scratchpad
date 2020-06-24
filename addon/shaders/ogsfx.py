
import os 
from typing import List

from .base import (
    BaseShader, 
    ShaderProperties,
)

from .fallback import (
    VS_FALLBACK,
    FS_FALLBACK
)

class OGSFXShader(BaseShader):
    """Load an OGSFX source file as a shader"""

    def __init__(self):
        super(OGSFXShader, self).__init__()

        self.properties = ShaderProperties()
        self.properties.add('source_file', 'filename', 'Filename', '.ogsfx file to load')

        self.material_properties = ShaderProperties()

    def get_renderer_properties(self):
        return self.properties

    def update_renderer_properties(self, settings):
        self.properties.from_property_group(settings)

        if not os.path.isfile(settings.filename):
            raise FileNotFoundError('Missing required OGSFX file')
        
        self.filename = settings.filename
        self.monitored_files = [settings.filename]

    def get_material_properties(self):
        return self.material_properties

    def update_material_properties(self, settings):
        self.material_properties.from_property_group(settings)
        # TODO: Texture reloading or something? Here or in the ShaderProperties?
        
    def recompile(self):
        # For now, uses fallback
        self.compile_from_strings(VS_FALLBACK, FS_FALLBACK)
        self.update_mtimes()

        # Pretend some settings have loaded from the .ogsfx
        props = self.get_material_properties()
        props.clear()
        
        props.add('float', 'buzz', 'Mat Buzz', 'More info about mat buzz', 0, 0, 1.0)
        props.add('color', 'my_color', 'my color', 'more info about color', (1.0, 0.15, 0.15))
        props.add('boolean', 'my_bool', 'Some boolean')

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
        
    def set_lighting(self, lighting):
        """...
        
        Parameters:
            lighting (SceneLighting): Current scene lighting information
        """
        pass

    def bind(self):
        super(OGSFXShader, self).bind()
        # Other setup work
        
    def unbind(self):
        super(OGSFXShader, self).unbind()
        