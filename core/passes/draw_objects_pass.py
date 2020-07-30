
from .render_pass import RenderPass

class DrawObjectsPass(RenderPass):
    def execute(self, data):
        """
        Parameters:
            data (RenderData)
        """
        camera = data.camera
        lights = data.lights 

        for mat in data.renderables:
            shader = mat.shader
            
            if shader.last_error:
                shader = ScratchpadRenderEngine.fallback_shader

            shader.bind('Main')
            shader.set_camera_matrices(
                camera.view_matrix,
                camera.projection_matrix
            )
            
            shader.set_lighting(lights)

            for r in data.renderables[mat]:
                r.draw(shader)

            shader.unbind()
