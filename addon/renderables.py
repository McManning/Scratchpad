
from bgl import *

from .mesh_data import MeshData
from .debug import init_log, log, op_log
from .vao import (
    VAO,
    VertexBuffer,
) 

class Material:
    def bind(self):
        pass

class Mesh:
    """Mesh data stored on the GPU for rendering.
    
    This manages the copy operations of Blender data to GPU buffers as 
    well as the actual rendering itself of the mesh from the render thread.
    """

    # Has the VAO backbuffer been filled and is ready to be swapped
    is_backbuffer_ready: bool 

    # Main VAO to use for glDrawElements
    vao: VAO

    # Backbuffer used to stream in new buffer data
    vao_backbuffer: VAO

    total_indices: int 
    total_vertices: int 

    def __repr__(self):
        return '<Mesh(name={})>'.format(
            self.obj.name if self.obj else ''
        )

    def __init__(self):
        self.is_backbuffer_ready = False
        self.vao = VAO()
        self.vao_backbuffer = VAO()

    def update(self, obj):
        self.obj = obj
        self.model_matrix = obj.matrix_world

    def rebuild(self, eval_obj):
        """Prepare the mesh to be copied to the GPU the next time the render thread executes.

        Parameters:
            eval_obj (bpy.types.Object): Object to convert to a temp `bpy.types.Mesh`
        """
        init_log('Rebuild Mesh')

        # mesh = self.obj.data
        mesh = eval_obj.to_mesh()
        log('Convert eval_obj to mesh')

        # Ensure triangulated faces are available
        mesh.calc_loop_triangles()
        log('calc_loop_triangles')

        # Calculates tangent space for normal mapping AND split normals, if not already
        # TODO: this is REALLY slow for large meshes. Need to reduce calls to this to only when necessary.
        # 0.0678s on 31k vertices. 
        # mesh.calc_tangents()
        # log('calc_tangents')
        
        op_log('Total setup time')

        self.eval_obj = eval_obj 
        self.eval_mesh = mesh 
        self.is_backbuffer_ready = True

    def rebuild_on_render_v4(self, shader):
        """Fill the VAO backbuffer with new mesh data 

        Parameters:
            shader (BaseShader): Shader program that houses the VAO target
        """
        init_log('Rebuild on Render v4')
        
        vao = self.vao_backbuffer
        mesh = self.eval_mesh 
        
        # TODO: Could setup on rebuild() update loop instead.
        data = MeshData(mesh) 
        op_log('Load into MeshData')

        # Pipe mesh data into VBOs
        co = vao.get_vertex_buffer(VertexBuffer.POSITION)
        co.set_data(data.co)
        log('Upload co')

        no = vao.get_vertex_buffer(VertexBuffer.NORMAL)
        no.set_data(data.normals)
        log('Upload no')

        indices = vao.get_index_buffer()
        indices.set_data(data.triangles)
        log('Upload indices')

        op_log('Set buffers')

        # Upload buffers to the GPU
        vao.upload(shader.program)
        op_log('Total VAO write time')

        # Cleanup
        self.eval_obj.to_mesh_clear()
        op_log('Total Cleanup time')

        self.is_backbuffer_ready = True

    def draw(self, shader):
        print('Draw', self)

        # Swap backbuffer with the active VAO 
        if self.is_backbuffer_ready:
            self.rebuild_on_render_v4(shader)

            # TODO: Backbuffer swap seems unnecessary here (since we're
            # creating and filling and immediately swapping in one whole step)
            # but eventually I'd like to slowly fill the backbuffer over multiple
            # frames for larger meshes IF that ends up being the solution to 
            # improve visual performance when editing large (1mil+ vert) meshes.

            print('Swap backbuffer')
            vao = self.vao 
            self.vao = self.vao_backbuffer
            self.vao_backbuffer = vao
            self.is_backbuffer_ready = False
            print('Done with swap')

        print('Bind VAO')
        self.vao.bind(shader.program)
        print('Draw elements', self.vao.total_indices)

        # Texture stuff go here.

        glDrawElements(GL_TRIANGLES, self.vao.total_indices, GL_UNSIGNED_INT, 0)
        
        print('Unbind?')
        self.vao.unbind()
        print('Done')
