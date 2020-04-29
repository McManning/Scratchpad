
from bgl import *

from .shader import Shader

class Material:
    def bind(self):
        pass

class Mesh:
    """Minimal representation needed to render a mesh"""
    def __init__(self):
        self.is_dirty = True
        self.vertex_data = None

    def rebuild(self, eval_obj, shader: Shader):
        """Copy evaluated mesh data into buffers for updating the VBOs"""
        if not self.vertex_data:
            self.vertex_data = shader.create_vertex_data()

        # mesh = self.obj.data
        mesh = eval_obj.to_mesh()

        # Refresh triangles on the mesh
        mesh.calc_loop_triangles()
        
        # "Fast" copy vertex data / triangle indices from the mesh into buffers
        # Reference: https://blog.michelanders.nl/2016/02/copying-vertices-to-numpy-arrays-in_4.html
        vertices = [0]*len(mesh.vertices) * 3
        mesh.vertices.foreach_get('co', vertices)
        self.vertex_data.vertices = Buffer(GL_FLOAT, len(vertices), vertices)
        
        normals = [0]*len(mesh.vertices) * 3
        mesh.vertices.foreach_get('normal', normals)
        self.vertex_data.normals = Buffer(GL_FLOAT, len(normals), normals)
        print('--- loop tris:', len(mesh.loop_triangles))
        indices = [0]*len(mesh.loop_triangles) * 3
        mesh.loop_triangles.foreach_get('vertices', indices)
        self.vertex_data.indices = Buffer(GL_INT, len(indices), indices)
        
        eval_obj.to_mesh_clear()

        # let the render loop upload the new buffer data onto the GPU,
        # otherwise we may run into access violation issues. 
        self.is_dirty = True

    def update(self, obj):
        self.obj = obj
        self.model_matrix = obj.matrix_world

    def dirty(self):
        """Dirty the mesh - causing all GPU buffers to reload"""
        self.is_dirty = True

    def draw(self, shader: Shader):
        if self.is_dirty:
            shader.upload_vertex_data(self.vertex_data)
            self.is_dirty = False

        # Texture stuff go here.
        
        glBindVertexArray(self.vertex_data.VAO)
        glDrawElements(GL_TRIANGLES, self.vertex_data.indices_size, GL_UNSIGNED_INT, 0)
        glBindVertexArray(0)
