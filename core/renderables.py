
import bpy
from bgl import *

from .mesh_data import MeshData
from .debug import init_log, log, op_log, debug, IS_DEBUG
from .vao import (
    VAO,
    VertexBuffer,
)

class ScratchpadMaterial:
    def __init__(self):
        self.shader = None # BaseShader impl
        self.renderables = {} # Set of Renderables with this material

class Renderable:
    def draw(self, shader):
        pass

class ScratchpadMesh(Renderable):
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
        return '<ScratchpadMesh(name={}) at {}>'.format(
            self.obj.name if self.obj else '',
            id(self)
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
        # mesh = eval_obj.to_mesh()
        # log('Convert eval_obj to mesh')

        # # Ensure triangulated faces are available
        # mesh.calc_loop_triangles()
        # log('calc_loop_triangles')

        # # Calculates tangent space for normal mapping AND split normals, if not already
        # # TODO: this is REALLY slow for large meshes. Need to reduce calls to this to only when necessary.
        # # 0.0678s on 31k vertices. 
        # # mesh.calc_tangents()
        # # log('calc_tangents')
        
        # op_log('Total setup time')

        # this is the same as self.obj ?
        self.eval_obj = eval_obj 
        # self.eval_mesh = mesh 
        self.is_backbuffer_ready = True

    def rebuild_on_render(self, shader):
        """Fill the VAO with new mesh data.

        This "safe" version uses foreach_get() operations to fetch data.

        Parameters:
            shader (BaseShader): Shader program that houses the VAO target
        """
        init_log('Rebuild on Render: {}'.format(self))
        
        vao = self.vao
        
        mesh = self.eval_obj.to_mesh()
        log('to_mesh() from {}'.format(id(self.eval_obj)))

        mesh.calc_loop_triangles()
        log('calc_loop_triangles()')

        vertices_len = len(mesh.vertices)
        loops_len = len(mesh.loops)
        looptris_len = len(mesh.loop_triangles)

        # Pipe mesh data into VBOs
        co = vao.get_vertex_buffer(VertexBuffer.POSITION)
        co.resize(3, vertices_len)
        mesh.vertices.foreach_get('co', co.data)
        log('Upload co')

        no = vao.get_vertex_buffer(VertexBuffer.NORMAL)
        no.resize(3, vertices_len)
        mesh.vertices.foreach_get('normal', no.data)
        log('Upload no')

        indices = vao.get_index_buffer()
        indices.resize(looptris_len * 3)
        mesh.loop_triangles.foreach_get('vertices', indices.data)
        log('Upload indices')

        op_log('Set buffers')

        # Upload buffers to the GPU
        vao.upload(shader.program)
        op_log('Total VAO write time')

        # Cleanup
        self.eval_obj.to_mesh_clear()
        # mesh_owner.to_mesh_clear()
        op_log('Total Cleanup time')

    def rebuild_on_render_unsafe(self, shader):
        """Fill the VAO with new mesh data 

        This unsafe version uses direct C struct access to fetch data.

        Parameters:
            shader (BaseShader): Shader program that houses the VAO target
        """
        init_log('Rebuild on Render (unsafe): {}'.format(self))
        
        vao = self.vao

        # depsgraph = bpy.context.evaluated_depsgraph_get()
        # log('depsgraph {}'.format(depsgraph))

        # mesh_owner = self.eval_obj.evaluated_get(depsgraph)
        # log('mesh_owner {}'.format(mesh_owner))

        # mesh = mesh_owner.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)

        # Moved to the render thread - otherwise we get access violations when 
        # trying to use multiple viewports. But really - there should only be 
        # one mesh instance across all viewports.
        mesh = self.eval_obj.to_mesh()
        log('to_mesh() from {}'.format(id(self.eval_obj)))

        mesh.calc_loop_triangles()
        log('calc_loop_triangles()')

        # mesh = self.eval_mesh 
        
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
        # mesh_owner.to_mesh_clear()
        op_log('Total Cleanup time')


    def draw(self, shader):
        debug('Draw', self)

        # Swap backbuffer with the active VAO 
        if self.is_backbuffer_ready:
            self.is_backbuffer_ready = False
            self.rebuild_on_render(shader)

            # TODO: Backbuffer swap is unnecessary here (since we're
            # creating and filling and immediately swapping in one whole step)
            # but eventually I'd like to slowly fill the backbuffer over multiple
            # frames for larger meshes IF that ends up being the solution to 
            # improve visual performance when editing large (1mil+ vert) meshes.

            # print('Swap backbuffer')
            # vao = self.vao 
            # self.vao = self.vao_backbuffer
            # self.vao_backbuffer = vao
            # print('Done with swap')

        vao = self.vao
        debug('Bind {}'.format(vao))

        vao.bind(shader.program)

        # TODO: Texture stuff
        
        if not IS_DEBUG:
            # No validation check, assume stable
            glDrawElements(GL_TRIANGLES, self.vao.total_indices, GL_UNSIGNED_INT, 0)
        else:
            debug_print_current_gl_bindings()

            if vao.is_valid():
                glDrawElements(GL_TRIANGLES, self.vao.total_indices, GL_UNSIGNED_INT, 0)
            else:
                debug('Invalid state for glDrawElements. Current bindings:')
                debug_print_current_gl_bindings()
                debug('\tBound VAO: {}'.format(vao))

        vao.unbind()
        debug('Done')


def debug_print_current_gl_bindings():
    """Print out the currently bound buffers for debugging"""
    buf = Buffer(GL_INT, 1)

    glGetIntegerv(GL_CURRENT_PROGRAM, buf)
    debug('\tProgram: {}'.format(buf[0]))

    glGetIntegerv(GL_VERTEX_ARRAY_BINDING, buf)
    debug('\tVAO: {}'.format(buf[0]))

    glGetIntegerv(GL_ARRAY_BUFFER_BINDING, buf)
    debug('\tVBO: {}'.format(buf[0]))

    glGetIntegerv(GL_ELEMENT_ARRAY_BUFFER_BINDING, buf)
    debug('\tEBO: {}'.format(buf[0]))
