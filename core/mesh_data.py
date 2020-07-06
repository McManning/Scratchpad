
# Abstraction to expose additional internal Mesh data to Python

import bpy
from ctypes import *
import numpy as np

# TODO: Resilience against Blender version upgrades. I know this is a hard ask
# since we're accessing Blender structs directly. 

class CustomDataType:
    """CustomData.type""" 
    # Ref: https://github.com/blender/blender/blob/v2.82/source/blender/makesdna/DNA_customdata_types.h#L92
    CD_NORMAL = 8
    CD_MLOOPUV = 16
    CD_MLOOP = 26
    CD_MLOOPTANGENT = 39
    CD_CUSTOMLOOPNORMAL = 41

class CustomDataLayer(Structure):
    """Descriptor and storage for a custom data layer"""
    # Ref: https://github.com/blender/blender/blob/v2.82/source/blender/makesdna/DNA_customdata_types.h#L36
    _fields_ = [
        ('type', c_int),
        ('offset', c_int),
        ('flag', c_int),
        ('active', c_int),
        ('active_rnd', c_int),
        ('active_clone', c_int),
        ('active_mask', c_int),
        ('uid', c_int),
        ('name', c_char * 64),
        ('data', c_void_p),
    ]

if bpy.app.version[1] < 83: # 2.82
    class ID(Structure):
        # Ref: https://github.com/blender/blender/blob/v2.82/source/blender/makesdna/DNA_ID.h#L246
        # Added because it's a dependency of Mesh. Unused pointers are c_void_p
        _fields_ = [
            ('next', c_void_p),
            ('prev', c_void_p),
            ('newid', c_void_p),
            ('lib', c_void_p),

            ('name', c_char * 66),

            ('flag', c_short),

            ('tag', c_int),
            ('us', c_int),
            ('icon_id', c_int),
            ('recalc', c_int),
            
            ('_pad', c_char * 4), # Blender/2.82
            
            # ('recalc_up_to_undo_push', c_int), # Blender/master
            # ('recalc_after_undo_push', c_int), # Blender/master
    
            # ('session_uuid', c_uint), # Blender/master

            ('properties', c_void_p),
            ('override_library', c_void_p),
            ('orig_id', c_void_p),
            ('py_instance', c_void_p),
        ]
        
    class CustomData(Structure):
        """ 
            Structure which stores custom element data associated with mesh elements
            (vertices, edges or faces). The custom data is organized into a series of
            layers, each with a data type (e.g. MTFace, MDeformVert, etc.).
        """
        # Ref: https://github.com/blender/blender/blob/v2.82/source/blender/makesdna/DNA_customdata_types.h#L71
        _fields_ = [
            ('layers', POINTER(CustomDataLayer)),
        
            ('typemap', c_int * 42), # Blender/2.82
            ('_pad0', c_char * 4), # Blender/2.82
            
            # ('typemap', c_int * 48), # Blender/master
            # ('_pad', c_char * 4), # Blender/master
            
            ('totlayer', c_int),
            ('maxlayer', c_int),

            ('totsize', c_int),

            ('pool', c_void_p),
            ('external', c_void_p),
        ]
else: # 2.83.1+ 
    class ID(Structure):
        # Ref: https://github.com/blender/blender/blob/v2.83.1/source/blender/makesdna/DNA_ID.h#L246
        # Added because it's a dependency of Mesh. Unused pointers are c_void_p
        _fields_ = [
            ('next', c_void_p),
            ('prev', c_void_p),
            ('newid', c_void_p),
            ('lib', c_void_p),

            ('name', c_char * 66),

            ('flag', c_short),

            ('tag', c_int),
            ('us', c_int),
            ('icon_id', c_int),
            ('recalc', c_int),
            
            ('recalc_up_to_undo_push', c_int), # Blender/2.83.1
            ('recalc_after_undo_push', c_int), # Blender/2.83.1
    
            ('session_uuid', c_uint), # Blender/2.83.1

            ('properties', c_void_p),
            ('override_library', c_void_p),
            ('orig_id', c_void_p),
            ('py_instance', c_void_p),
        ]

    class CustomData(Structure):
        """ 
            Structure which stores custom element data associated with mesh elements
            (vertices, edges or faces). The custom data is organized into a series of
            layers, each with a data type (e.g. MTFace, MDeformVert, etc.).
        """
        # Ref: https://github.com/blender/blender/blob/v2.82/source/blender/makesdna/DNA_customdata_types.h#L71
        _fields_ = [
            ('layers', POINTER(CustomDataLayer)),
        
            ('typemap', c_int * 47),
            
            ('totlayer', c_int),
            ('maxlayer', c_int),

            ('totsize', c_int),

            ('pool', c_void_p),
            ('external', c_void_p),
        ]

class MVert(Structure):
    """
    Mesh Vertices. 
    Typically accessed from Mesh.mvert
    """
    # Ref: https://github.com/blender/blender/blob/v2.82/source/blender/makesdna/DNA_meshdata_types.h#L39
    # Blender also has MVertTri - but that's not stored on a Mesh.
    # Just soft bodies and some other stuff and BKE_mesh_runtime_verttri_from_looptri
    # Would be nice to have though so we don't need to map `loops` -> `co` from within Python.
    _fields_ = [
        ("co", c_float * 3),
        ("no", c_short * 3),
        ("flag", c_char),
        ("bweight", c_char)
    ]

class MLoop(Structure):
    """
    Mesh Loops. Each loop represents the corner of a polygon (MPoly).
    Typically accessed from Mesh.mloop
    """
    # Ref: https://github.com/blender/blender/blob/v2.82/source/blender/makesdna/DNA_meshdata_types.h#L111
    _fields_ = [
        ("v", c_uint),
        ("e", c_uint)
    ]

class MLoopUV(Structure):
    """UV coordinate for a polygon face & flag for selection & other options."""
    # Ref: https://github.com/blender/blender/blob/v2.82/source/blender/makesdna/DNA_meshdata_types.h#L327
    _fields_ = [
        ("uv", c_float * 2),
        ("flag", c_int)
    ]

class MLoopTri(Structure):
    """Lightweight triangulation data for functionality that doesn't support ngons"""
    # Ref: https://github.com/blender/blender/blob/v2.82/source/blender/makesdna/DNA_meshdata_types.h#L245
    _fields_ = [
        ("tri", c_uint * 3),
        ("poly", c_uint)
    ]

class Mesh(Structure):
    # Ref: https://github.com/blender/blender/blob/v2.82/source/blender/makesdna/DNA_mesh_types.h#L118
    # This is a partial representation of Blender's Mesh struct - only the half of the struct
    # that we care about for data extraction. This lets us avoid mocking other structs that 
    # we don't care about (e.g. Mesh_Runtime). We also don't use Mesh in an array of any sort.
    # Any pointers we don't need are replaced with `c_void_p`
    _fields_ = [
        ('id', ID),

        # Animation data (must be immediately after id for utilities to use it). 
        ('adt', c_void_p),

        # Old animation system, deprecated for 2.5.
        ('ipo', c_void_p),
        ('key', c_void_p),
        ('mat', c_void_p),
        ('mselect', c_void_p),
        
        # BMESH ONLY
        # new face structures
        ('mpoly', c_void_p),
        ('mloop', c_void_p),
        ('mloopuv', c_void_p),
        ('mloopcol', c_void_p),
        # END BMESH ONLY

        # Legacy face storage (quads & tries only),
        # faces are now stored in Mesh.mpoly & Mesh.mloop arrays.
        ('mface', c_void_p),
        ('mtface', c_void_p),
        ('tface', c_void_p),
        ('mvert', c_void_p),
        ('medge', c_void_p), 
        ('dvert', c_void_p),

        # Array of colors for tessellated faces, must be number of 
        # tessellated faces * 4 in length
        ('mcol', c_void_p),
        ('texcomesh', c_void_p),
        
        ('edit_mesh', c_void_p),

        ('vdata', CustomData),
        ('edata', CustomData),
        ('fdata', CustomData),

        # BMESH ONLY
        ('pdata', CustomData),
        ('ldata', CustomData),
        # END BMESH ONLY

        ('totvert', c_int),
        ('totedge', c_int),
        ('totface', c_int),
        ('totselect', c_int),
        
        # BMESH ONLY
        ('totpoly', c_int),
        ('totloop', c_int),
        # END BMESH ONLY
        
        # ('act_face', c_int),
        
        # ('loc', c_float * 3),
        # ('size', c_float * 3),
        
        # ('texflag', c_short),
        # ('flag', c_short),
        # ('smoothresh', c_float),

        # # customdata flag, for bevel-weight and crease, which are now optional
        # ('cd_flag', c_char),
        # ('_pad', c_char),

        # ('subdiv', c_char),
        # ('subdivr', c_char),
        # ('subsurftype', c_char),
        # ('editflag', c_char),

        # ('totcol', c_short),

        # ('remesh_voxel_size', c_float),
        # ('remesh_voxel_adaptivity', c_float),
        # ('remesh_mode', c_char),
        
        # ('_pad1', c_char * 3),
        
        # ('face_sets_color_seed', c_int),
        # ('face_sets_color_default', c_int),

        # ('mr', c_void_p),

        # ('runtime', Mesh_Runtime),
    ]


def CustomData_get_active_layer_index(data: CustomData, layer_type: int) -> int:
    """
    Return:
        Index, or -1 if there is no active layer
    """
    # Ref: https://github.com/blender/blender/blob/v2.82/source/blender/blenkernel/intern/customdata.c#L2135
    layer_index = data.typemap[layer_type]
    if layer_index == -1:
        return -1 

    return layer_index + data.layers[layer_index].active

def CustomData_get_layer(data: CustomData, layer_type: int) -> int:
    """
    Return:
        Pointer to layer data (void*)
    """
    # Ref: https://github.com/blender/blender/blob/v2.82/source/blender/blenkernel/intern/customdata.c#L2972
    layer_index = CustomData_get_active_layer_index(data, layer_type)
    if layer_index == -1:
        return None 
    
    return data.layers[layer_index].data

def assert_mesh_structs(mesh, c_mesh: Mesh):
    """Ensure that the memory mapping between mesh and c_mesh is correct.

    This can fail if the representation of C structs are mismatched from 
    how the data is stored in the current Blender version.
    """
    assert c_mesh.totvert == len(mesh.vertices), 'totvert mismatch. Mesh(ctype.Structure) may be misaligned'
    assert c_mesh.totloop == len(mesh.loops), 'totloop mismatch. Mesh(ctype.Structure) may be misaligned'
    # TODO: Assertions for CustomData (not sure what to compare with in bpy)

class MeshData:
    """Wrap a Mesh with a data accessor

    This short circuits slower methods of copying & converting mesh data to Python 
    and instead directly references the same data used within Blender via Numpy.

    Obviously - use with caution.
    """
    def __init__(self, mesh):
        """
        Properties:
            mesh (bpy.types.Mesh)
        """
        # self.mesh = mesh
        self.has_custom_normals = mesh.has_custom_normals
        
        c_mesh_ptr = cast(mesh.as_pointer(), POINTER(Mesh))
        c_mesh = c_mesh_ptr.contents # Does a COPY here.

        assert_mesh_structs(mesh, c_mesh)
        self.c_mesh = c_mesh

        self.mvert_len = len(mesh.vertices)
        self.mvert = cast(mesh.vertices[0].as_pointer(), POINTER(MVert))
        
        self.mloop_len = len(mesh.loops)
        self.mloop = cast(mesh.loops[0].as_pointer(), POINTER(MLoop))

        self.mlooptri_len = len(mesh.loop_triangles)
        self.mlooptri = cast(mesh.loop_triangles[0].as_pointer(), POINTER(MLoopTri))

        # Cached data
        self.__co = None 
        self.__normals = None 

    @property
    def vertices(self):
        """Get a Numpy array of MVert structs.

        Since most Blender data is aligned to loops (UVs, vertex colors, custom normals)
        it's typically best to use that instead of the vertex list.
        
        Returns:
            Numpy array with shape (mvert_len,)
        """
        # TODO: Cache?
        return np.ctypeslib.as_array(self.mvert, shape=(self.mvert_len,))

    @property
    def loops(self):
        """Get a Numpy array of MLoop structs
        
        Returns:
            Numpy array with shape (mloop_len,)
        """
        return np.ctypeslib.as_array(self.mloop, shape=(self.mloop_len,))
    
    @property
    def looptris(self):
        """Get a Numpy array of MLoopTri structs
        
        Returns:
            Numpy array with shape (mlooptri_len,)
        """
        return np.ctypeslib.as_array(self.mlooptri, shape=(self.mlooptri_len,))

    @property
    def triangles(self):
        """Get a flat Numpy array of loop indices that make up mesh triangles
        
        Returns:
            Numpy array with shape (mloop_len * 3,)
        """
        return self.looptris['tri'].flatten()

    def calculate_normals(self):
        """
        Generate and cache a Numpy array of vertex normals.

        This aligns with loops (mloop_len) and accounts for custom split normals
        """
        v = self.loops['v']

        if not self.has_custom_normals:
            # `no` is stored as a short, so we need to convert before retrieving.
            # TODO: Maybe leave this up to the shader instead? It's one less CPU operation
            self.__normals = self.vertices['no'][v].astype(np.float32) / 32767.0
        else:
            # TODO: Algorithm for split normal loading.
            # const float(*loop_normals)[3] = static_cast<const float(*)[3]>(CustomData_get_layer(&mesh->ldata, CD_NORMAL));
            # p_data = CustomData_get_layer(self.c_mesh.ldata, CustomDataType.CD_NORMAL)
            # p_loop_normals = cast(p_data, POINTER(c_float))

            # # incorrect. 
            # self.__normals = np.ctypeslib.as_array(p_loop_normals, shape=(self.mloop_len,3))

            # This works for cd normal, and don't need to convert.
            raise 'Custom normals not yet supported'

    def calculate_co(self):
        """
        Generate and cache a Numpy array of vertex coordinates.

        This aligns with loops (mloop_len), rather than MVert
        """
        # TODO: We typically pull normals & positions at the same time.
        # Is there a performance boost by only doing the `v = ...` step once?
        v = self.loops['v']
        self.__co = self.vertices['co'][v]

    @property
    def co(self):
        """Get a Numpy array of vertex coordinates aligned with loops
        
        Return:
            Numpy array with shape (mloop_len, 3)
        """    
        if self.__co is None:
            self.calculate_co()

        return self.__co

    @property
    def normals(self):
        """Get a Numpy array of vertex normals aligned with loops
        
        Return:
            Numpy array with shape (mloop_len, 3) 
        """
        if self.__normals is None:
            self.calculate_normals()

        return self.__normals

    @property
    def texcoord0(self):
        raise Exception('Not implemented')

    def __repr__(self):
        return '<MeshData(name={}, vertices={}, loops={}, looptris={}, co={}, no={})>'.format(
            self.c_mesh.id.name,
            self.mvert_len,
            self.mloop_len,
            self.mlooptri_len,
            self.co.shape,
            self.normals.shape
        )


if __name__ == '__main__':
    MESH_NAME = 'Cube.001'

    mesh = bpy.data.meshes[MESH_NAME]

    # Ensure triangulated faces are available
    mesh.calc_loop_triangles()

    # Calculates tangent space for normal mapping AND split normals, if not already
    mesh.calc_tangents() 

    mesh_data = MeshData(mesh)
    print(mesh_data)

    print(mesh_data.co)
    print(mesh_data.normals)
    