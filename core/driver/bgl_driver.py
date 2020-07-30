"""
Abstraction between the low level renderer and the rest of the engine.

In a perfect world - this'll make it easier to upgrade once Blender 
moves onward to Vulkan/Metal/whatever they choose.
"""

from bgl import *

class Graphics:
    @staticmethod
    def compile_program():
        pass
        # from shaders/base

    @staticmethod
    def enable_features(depth_test: bool):
        """Enable specific driver features
        """
        if depth_test:
            glEnable(GL_DEPTH_TEST)

    @staticmethod
    def clear_render_target(clear_depth: bool, clear_color: bool, background_color: tuple, depth: float = 1.0):
        """Clear the current render target
        """
        glClearColor(background_color[0], background_color[1], background_color[2], depth)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

class CommandBuffer:
    pass
    # TODO: Eventually will be buffered. 
    # For now, we treat this as an immediate mode.

    # def clear_render_target(self, clear_depth: bool, clear_color: bool, background_color: tuple, depth: float = 1.0):
    #     """Clear the current render target
    #     """
    #     glClearColor(background_color[0], background_color[1], background_color[2], depth)
    #     glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    # def draw_renderables(self, renderables: dict, technique: str = 'Main'):
    #     for mat in renderables:
    #         shader = mat.shader
            
    #         if shader.last_error:
    #             shader = fallback_shader # ???

    #         shader.bind(technique)
    #         shader.set_camera_matrices(
    #             region3d.view_matrix, # ????
    #             region3d.window_matrix
    #         )
            
    #         shader.set_lighting(self.lighting) # ????

    #         for r in renderables[mat]:
    #             shader.set_object_matrices(r.model_matrix)
    #             r.draw(shader)

    #         shader.unbind()

# VAO/EBO/VBO needs to be here as well I guess.
# Unity has Mesh.UploadMeshData
# and Mesh.SetVertexBuffer


    # add static fallback shader 

# Unity property block applies a set of crap to a material
# per-instance of mesh using it. 

# I assume a command buffer is a:
# 1. bind shader program used to render a material
# execute everything in the buffer for that program (set glUniform etc)
# and draw geometry.

# they also have a "attach command buffers to stages of camera" stuff
# so that the camera sets up view matrices, then draws, etc. 
# so, presumably, for each material program under a camera ... somehow...
# all those buffers are executed. 

