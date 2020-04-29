
from .base import (
    Shader, 
    VertexData, 
    LightData, 
    ShaderData
)

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

class FallbackShader(Shader):
    """Built-in fallback for when a user shader fails to load"""
    name = 'Default'

    def load_from_settings(self, settings):
        # No settings used for the fallback
        pass

    def get_settings(self) -> ShaderData:
        # No settings
        return None

    def recompile(self):
        self.prev_mtimes = []
        self.compile_from_strings(VS_FALLBACK, FS_FALLBACK)

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
