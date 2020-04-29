
from bgl import *

from .shader import Shader

class Material:
    def bind(self):
        pass

class Mesh:
    """Minimal representation needed to render a mesh"""
    def __init__(self):
        # Once on setup, create a VAO to store VBO/EBO and settings
        VAO = Buffer(GL_INT, 1)
        glGenVertexArrays(1, VAO)
        self.VAO = VAO[0]

        VBO = Buffer(GL_INT, 2)
        glGenBuffers(2, VBO)
        self.VBO = VBO

        EBO = Buffer(GL_INT, 1)
        glGenBuffers(1, EBO)
        self.EBO = EBO[0]
        
        self.is_dirty = True
        self.indices_size = 0

        # ..and in cleanup:
        # might need to be buffer refs
        # glDeleteVertexArrays(1, VAO)
        # glDeleteBuffers(1, VBO)
        # glDeleteBuffers(1, EBO)

    def rebuild(self, eval_obj, shader: Shader):
        """Copy evaluated mesh data into buffers for updating the VBOs"""

        # mesh = self.obj.data
        mesh = eval_obj.to_mesh()

        # Refresh triangles on the mesh
        # mesh.calc_loop_triangles()
        
        # Fast copy vertex data / triangle indices from the mesh into buffers
        # Reference: https://blog.michelanders.nl/2016/02/copying-vertices-to-numpy-arrays-in_4.html
        vertices = [0]*len(mesh.vertices) * 3
        mesh.vertices.foreach_get('co', vertices)
        self.vertices = Buffer(GL_FLOAT, len(vertices), vertices)
        
        normals = [0]*len(mesh.vertices) * 3
        mesh.vertices.foreach_get('normal', normals)
        self.normals = Buffer(GL_FLOAT, len(normals), normals)
        
        indices = [0]*len(mesh.loop_triangles) * 3
        mesh.loop_triangles.foreach_get('vertices', indices)
        self.indices = Buffer(GL_INT, len(indices), indices)
        
        eval_obj.to_mesh_clear()

        # let the render loop set the new buffer data into the VAO,
        # otherwise we may run into access violation issues. 
        self.is_dirty = True

    def rebuild_vbos(self, shader: Shader):
        # Bind the VAO so we can upload new buffers
        glBindVertexArray(self.VAO)

        # Copy verts
        glBindBuffer(GL_ARRAY_BUFFER, self.VBO[0])
        glBufferData(GL_ARRAY_BUFFER, len(self.vertices) * 4, self.vertices, GL_STATIC_DRAW) # GL_STATIC_DRAW - for inactive mesh
        shader.set_vertex_attribute('Position', 0)

        # Copy normals
        glBindBuffer(GL_ARRAY_BUFFER, self.VBO[1])
        glBufferData(GL_ARRAY_BUFFER, len(self.normals) * 4, self.normals, GL_STATIC_DRAW)
        shader.set_vertex_attribute('Normal', 0)

        # TODO: Tangent, Binormal, Color, Texcoord0-7
        # TODO: Probably don't do per-mesh VAO. See: https://stackoverflow.com/a/18487155

        # Copy indices
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.EBO)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, len(self.indices) * 4, self.indices, GL_STATIC_DRAW)

        # Cleanup, just so bad code elsewhere doesn't also write to this VAO
        glBindVertexArray(0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        self.indices_size = len(self.indices)

    def update(self, obj):
        self.obj = obj
        self.model_matrix = obj.matrix_world

    def dirty(self):
        """Dirty the mesh - causing all GPU buffers to reload"""
        self.is_dirty = True

    def draw(self, shader: Shader):
        if self.is_dirty:
            self.rebuild_vbos(shader)
            self.is_dirty = False

        # Texture stuff go here.
        
        glBindVertexArray(self.VAO)
        glDrawElements(GL_TRIANGLES, self.indices_size, GL_UNSIGNED_INT, 0)
        glBindVertexArray(0)
