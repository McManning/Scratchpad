
import numpy as np 
from bgl import *

class VertexBuffer:
    """Management for a single VBO.

    Buffer data is stored in Numpy to make use of high performance 
    Python Buffers and raw memory access to be able to pass data 
    quickly between Python and GLSL.
    """

    POSITION  = 'Position'
    NORMAL    = 'Normal'
    TEXCOORD0 = 'Texcoord0'
    TEXCOORD1 = 'Texcoord1'
    TEXCOORD2 = 'Texcoord2'
    TEXCOORD3 = 'Texcoord3'
    TEXCOORD4 = 'Texcoord4'
    TEXCOORD5 = 'Texcoord5'
    TEXCOORD6 = 'Texcoord6'
    TEXCOORD7 = 'Texcoord7'
    
    @property
    def data(self):
        """Access to the underlying Numpy array containing this buffer's data"""
        if self._data is None:
            raise Exception('np.array not initialized. Call resize() first')
        
        return self._data

    def __init__(self, attr: str):
        """Create a new VertexBuffer

        Parameters:
            attr (str): Attribute name to use while binding to a program.
                        Use one of the enums, e.g. `VertexBuffer.NORMAL`
        """
        self.attr = attr # Attribute name
        self._data = None # np.array
        self.buffer = None # bgl.Buffer
        self.count = 0
        self.components = 0

        vbo = Buffer(GL_INT, 1)
        glGenBuffers(1, vbo)
        self.vbo = vbo[0]

    def destroy(self):
        glDeleteBuffers(1, self.vbo)
        if self.buffer: glDeleteBuffers(1, self.buffer)

    def as_pointer(self):
        """Access to the raw pointer to this buffer's data"""
        raise NotImplementedError('TODO')

    def resize(self, components: int, count: int):
        """Reallocate memory to hold `components * count` floats.

        If the components * count size doesn't change from the last 
        time this is called, this method does nothing.

        Parameters:
            components (int): Number of components (e.g. 3 for a vec3)
            count (int): Number of instances
        """
        if components == self.components and count == self.count: return

        size = components * count 

        # Don't completely reallocate if we don't need to
        data = self._data 
        if data is None:
            data = np.empty(size, 'f')
        else:
            # Refcheck is turned off here - we'll be creating a new
            # bgl.Buffer to point to the new memory address anyway.
            data.resize(size, refcheck=False)

        # Create a new buffer to point to the new array in memory.
        buffer = Buffer(GL_FLOAT, size, data)

        self.count = count 
        self.components = components 
        self._data = data
        self.buffer = buffer 

    def set_data(self, arr):
        """Set an existing numpy array as our data array.
        
        Parameters:
            arr (np.Array): Array in the shape `(count, components)`
        """
        self._data = arr.flatten()
        self.count = arr.shape[0]
        self.components = arr.shape[1]
        self.buffer = Buffer(GL_FLOAT, self.components * self.count, self._data)

    def upload(self, program):
        location = glGetAttribLocation(program, self.attr)
        if location < 0: return 

        size_in_bytes = self.components * self.count * 4

        # Is this a slow memcpy operation then? 
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, size_in_bytes, self.buffer, GL_DYNAMIC_DRAW) # GL_STATIC_DRAW)
        
        glEnableVertexAttribArray(location)
        glVertexAttribPointer(location, self.components, GL_FLOAT, GL_FALSE, 0, 0)

        # glBufferSubData(GL_ARRAY_BUFFER, 0, size_in_bytes, data)


class IndexBuffer:
    """Management for a single EBO"""
    
    @property
    def data(self):
        """Access to the underlying Numpy array containing this buffer's data"""
        if self._data is None:
            raise Exception('np.array not initialized. Call resize() first')
        
        return self._data

    def __init__(self):
        self._data = None # np.array
        self.buffer = None # bgl.Buffer
        self.count = 0

        ebo = Buffer(GL_INT, 1)
        glGenBuffers(1, ebo)
        self.ebo = ebo[0]

    def destroy(self):
        glDeleteBuffers(1, self.ebo)
        if self.buffer: glDeleteBuffers(1, self.buffer)

    def as_pointer(self):
        """Access to the raw pointer to this buffer's data"""
        raise NotImplementedError('TODO')

    def resize(self, count: int):
        if count == self.count: return 

        # Don't completely reallocate if we don't need to
        data = self._data 
        if data is None:
            data = np.empty(count, 'i')
        else:
            # Refcheck is turned off here - we'll be creating a new
            # bgl.Buffer to point to the new memory address anyway.
            data.resize(count, refcheck=False)

        # Create a new buffer to point to new array in memory.
        buffer = Buffer(GL_INT, count, data)

        self.count = count 
        self._data = data
        self.buffer = buffer 

    def set_data(self, arr):
        """Set an existing numpy array as our data array.
        
        Array is expected to be in the shape (count,)
        """
        self._data = arr
        self.count = arr.shape[0]
        self.buffer = Buffer(GL_INT, self.count, self._data)

    def upload(self, program):
        size_in_bytes = self.count * 4

        # print('Set EBO', len(self.buffer))
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, size_in_bytes, self.buffer, GL_DYNAMIC_DRAW) # GL_STATIC_DRAW)

        # glBufferSubData(GL_ELEMENT_ARRAY_BUFFER, 0, size_in_bytes, data)


class VAO:
    """Abstraction for managing an active vertex array object
    
    Usage:
        vao = VAO()

        # Read mesh triangle indices into indices buffer
        indices = vao.get_index_buffer()
        indices.resize(len(mesh.loop_triangles) * 3)
        mesh.loop_triangles.foreach_get('vertices', indices.data)

        # Read vertex positions (3 component vectors) into buffer
        co = vao.get_vertex_buffer(VertexBuffer.POSITION)
        co.resize(3, len(mesh.vertices))
        mesh.vertices.foreach_get('co', co.data)

        # Bind and render using the VAO 
        vao.bind(program)
        glDrawElements(GL_TRIANGLES, vao.total_indices, GL_UNSIGNED_INT, 0)
        vao.unbind()
    """
    def __init__(self):
        vao = Buffer(GL_INT, 1)
        glGenVertexArrays(1, vao)
        self.vao = vao[0]

        self.vertex_buffers = dict()
        self.index_buffer = IndexBuffer()

    @property
    def total_indices(self):
        return self.index_buffer.count

    def get_vertex_buffer(self, attr: str) -> VertexBuffer:
        if attr in self.vertex_buffers:
            return self.vertex_buffers[attr]

        buf = VertexBuffer(attr)
        self.vertex_buffers[attr] = buf
        return buf

    def get_index_buffer(self) -> IndexBuffer:
        return self.index_buffer

    def destroy(self):
        self.index_buffer.destroy()
        for buf in self.vertex_buffers.values():
            buf.destroy()

    def upload(self, program):
        self.bind(program)
        
        for buf in self.vertex_buffers.values():
            buf.upload(program)
        
        self.index_buffer.upload(program)
        self.unbind()

    def bind(self, program):
        glBindVertexArray(self.vao)
        
    def unbind(self):
        glBindVertexArray(0)

