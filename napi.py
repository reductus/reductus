# This program is public domain

"""
Provide a ctypes wrapper around the NeXus library for use in Python.

Data values are loaded/stored directly from numpy arrays.

Return codes are turned into exceptions.

Note: this implementation is incomplete.  Linking is not supported.
"""
import numpy as N
import ctypes as C
from ctypes import c_void_p, c_int, c_char_p, byref
c_void_pp = C.POINTER(c_void_p)
c_int_p = C.POINTER(c_int)

path=r'C:\\Program Files\\NeXus Data Format\\bin\\'
libname='libNeXus-0.dll'

# Open codes
READ,RDWR,CREATE=1,2,3
CREATE4,CREATE5,CREATEXML=4,5,6
NOSTRIP=128
# Status codes
OK,ERROR,EOD=1,0,-1
# Other constants
UNLIMITED=-1
MAXRANK=32
MAXNAMELEN=64
# HDF data types from numpy types
nxtype=dict(
    char=4,
    float32=5,float64=6,
    int8=20,uint8=21,
    int16=22,uint16=23,
    int32=24,uint32=25,
    int64=26,uint64=27,
    )
# Python types from HDF data types
# Other than 'char' for the string type, the python types correspond to
# the numpy data types, and can be used directly to create numpy arrays.
pytype=dict([(v,k) for (k,v) in nxtype.iteritems()])

# Compression to use when creating data blocks
compression=dict(
    none=100,
    lzw=200,
    rle=300,
    huffman=400)

def _build_storage(shape, storage):
    """
    Build space to collect a nexus data element.
    Returns arg,ret,size where
    - arg is the value to pass to C (effectively a void *)
    - ret is a lamba expression to extract the value out of the element.
    - size is the number of bytes in the data block
    Note that ret can return a string, a scalar or an array depending
    on the storage class and dimensions of the data group.
    """
    
    if len(shape) == 1 and storage == 'char':
        arg = C.create_string_buffer(shape[0])
        ret = lambda: arg.value
        size = shape[0]
    else:
        if storage=='char': storage = 'uint8'
        val = N.zeros(shape,storage)
        if len(shape) == 1 and shape[0] == 1:
            ret = lambda: val[0]
        else:
            ret = lambda: val
        arg = val.ctypes.data
        size = val.nbytes
    return arg,ret,size


# Define the interface to the dll
lib = N.ctypeslib.load_library(libname, path)

# ==== File ====
lib.nxiopen_.restype = c_int
lib.nxiopen_.argtypes = [c_char_p, c_int, c_void_pp]
def open(filename, mode):
    """
    Open the NeXus file returning a handle.
    
    Raises RuntimeError if the file could not be opened, with the
    filename as part of the error message.

    Corresponds to status = NXopen(filename,mode,&handle)
    """
    handle = c_void_p(None)
    status = lib.nxiopen_(filename,mode,byref(handle))
    if status == ERROR:
        raise RuntimeError, "Could not open %s"%(name)
    return handle

lib.nxiclose_.restype = c_int
lib.nxiclose_.argtypes = [c_void_pp]
def close(handle):
    """
    Close the NeXus file associated with handle.

    Raises RuntimeError if file could not be opened.

    Corresponds to status = NXclose(&handle)
    """
    status = lib.nxiclose_(byref(handle))
    if status == ERROR:
        raise RuntimeError, "Could not close NeXus file"

lib.nxiflush_.restype = c_int
lib.nxiflush_.argtypes = [c_void_pp]
def flush(handle):
    """
    Flush all data to the NeXus file.

    Raises RuntimeError if this fails.

    Corresponds to status = NXflush(&handle)
    """
    status = lib.nxiflush_(byref(handle))
    if status == ERROR:
        raise RuntimeError, "Could not flush NeXus file"

# ==== Group ====
lib.nximakegroup_.restype = c_int
lib.nximakegroup_.argtypes = [c_void_p, c_char_p, c_char_p]
def makegroup(handle, name, nxclass):
    """
    Create the group nxclass:name.

    Raises RuntimeError if the group could not be created.

    Corresponds to status = NXmakegroup(handle, name, nxclass)
    """
    status = lib.nximakegroup_(handle, name, nxclass)
    if status == ERROR:
        raise RuntimeError, "Could not create %s:%s"%(nxclass,name)

lib.nxiopengroup_.restype = c_int
lib.nxiopengroup_.argtypes = [c_void_p, c_char_p, c_char_p]
def opengroup(handle, name, nxclass):
    """
    Open the group nxclass:name.

    Raises ValueError if the group could not be opened.

    Corresponds to status = NXopengroup(handle, name, nxclass)
    """
    #print "open group",nxclass,name
    status = lib.nxiopengroup_(handle, name, nxclass)
    if status == ERROR:
        raise ValueError, "Could not open group %s:%s"%(nxclass,name)

lib.nxiclosegroup_.restype = c_int
lib.nxiclosegroup_.argtypes = [c_void_p]
def closegroup(handle):
    """
    Close the currently open group.

    Raises RuntimeError if the group could not be closed.

    Corresponds to status = NXclosegroup(handle)
    """
    #print "close group"
    status = lib.nxiclosegroup_(handle)
    if status == ERROR:
        raise RuntimeError, "Could not close current group"

lib.nxigetinfo_.restype = c_int
lib.nxigetinfo_.argtypes = [c_void_p, c_int_p, c_char_p, c_char_p]
def getgroupinfo(handle):
    """
    Query the currently open group returning the tuple
    numentries, path, nxclass.  The path consists of names
    of subgroups starting at the root separated by "/".

    Raises ValueError if the group could not be opened.

    Corresponds to status = NXgetgroupinfo(handle)
    """
    # Space for the returned strings
    name = C.create_string_buffer(MAXNAMELEN)
    nxclass = C.create_string_buffer(MAXNAMELEN)
    n = c_int(0)
    status = lib.nxigetgroupinfo_(handle,C.byref(n),name,nxclass)
    if status == ERROR:
        raise ValueError, "Could not get group info"
    #print "group info",nxclass.value,name.value,n.value
    return n.value,name.value,nxclass.value

lib.nxiinitgroupdir_.restype = c_int
lib.nxiinitgroupdir_.argtypes = [c_void_p]
def initgroupdir(handle):
    """
    Reset getnextentry to return the first entry in the group.

    Raises RuntimeError if this fails.

    Corresponds to status = NXinitgroupdir(handle)
    """
    status = lib.nxiinitgroupdir_(handle)
    if status == ERROR:
        raise RuntimeError, "Could not reset group scan"

lib.nxigetnextentry_.restype = c_int
lib.nxigetnextentry_.argtypes = [c_void_p, c_char_p, c_char_p, c_int_p]
def getnextentry(handle):
    """
    Return the next entry in the group as name,nxclass tuple.

    Raises RuntimeError if this fails, or if there is no next entry.

    Corresponds to status = NXinitgroupdir(handle).

    This differs from the NeXus API in that it doesn't return the storage
    class for the entry (that being of no value without also knowing the
    dimensions), and it doesn't return EOD for end of data (use getgroupinfo
    to determine the number of entries in the group instead).
    """
    name = C.create_string_buffer(MAXNAMELEN)
    nxclass = C.create_string_buffer(MAXNAMELEN)
    storage = c_int(0)
    status = lib.nxigetnextentry_(handle,name,nxclass,byref(storage))
    if status == ERROR or status ==EOD:
        raise RuntimeError, "Could not get next entry in group"
    ## Note: ignoring storage --- it is useless without dimensions
    #if nxclass == 'SDS':
    #    storage = pytype(storage.value)
    #print "group next",nxclass.value, name.value
    return name.value,nxclass.value

# ==== Data ====
lib.nxigetinfo_.restype = c_int
lib.nxigetinfo_.argtypes = [c_void_p, c_int_p, c_void_p, c_int_p]
def getinfo(handle):
    """
    Returns the tuple dimensions,type for the currently open dataset.
    Dimensions is an integer array whose length corresponds to the rank
    of the dataset and whose elements are the size of the individual
    dimensions.  Storage type is returned as a string, with 'char' for
    a stored string, '[u]int[8|16|32]' for various integer values or
    'float[32|64]' for floating point values.  No support for
    complex values.

    Raises RuntimeError if this fails.

    Corresponds to status = NXgetinfo(handle, &rank, dims, &storage_type),
    but with storage_class converted from HDF values to numpy compatible
    strings, and rank implicit in the length of the returned dimensions.
    """
    rank = c_int(0)
    shape = N.zeros(MAXRANK, 'i')
    storage = c_int(0)
    status = lib.nxigetinfo_(handle, byref(rank), shape.ctypes.data,
                                 byref(storage))
    if status == ERROR:
        raise RuntimeError, "Could not get info on current data"
    shape = shape[:rank.value]+0
    storage = pytype[storage.value]
    #print "data info",shape,storage
    return shape,storage

lib.nxiopendata_.restype = c_int
lib.nxiopendata_.argtypes = [c_void_p, c_char_p]
def opendata(handle, name):
    """
    Open the named data set within the current group.

    Raises ValueError if could not open the dataset.

    Corresponds to status = NXopendata(handle, name)
    """
    #print "opening data",name
    status = lib.nxiopendata_(handle, name)
    if status == ERROR:
        raise ValueError, "Could not open data %s"%(name)

lib.nxiclosedata_.restype = c_int
lib.nxiclosedata_.argtypes = [c_void_p]
def closedata(handle):
    """
    Close the currently open data set.

    Raises RuntimeError if this fails (e.g., because no
    dataset is open).

    Corresponds to status = NXclosedata(handle)
    """
    #print "closing data"
    status = lib.nxiclosedata_(handle)
    if status == ERROR:
        raise RuntimeError, "Could not close current data"

lib.nximakedata_.restype = c_int
lib.nximakedata_.argtypes  = [c_void_p, c_char_p, c_int, c_int, c_int_p]
def makedata(handle, name, shape, storage):
    """
    Create a data element of the given dimensions and storage class.  See
    getinfo for details on storage class.  This does not open the data
    for writing.  Set the first dimension to napi.UNLIMITED, for
    extensible data sets, and use putslab to write individual slabs.

    Raises ValueError if it fails.

    Corresponds to status=NXmakedata(handle,name,type,rank,dims)
    """
    nxstorage = nxtype[storage]
    status = lib.nximakedata_(handle,name,nxstorage,len(shape),
                              shape.ctypes.data_as(c_int_p))
    if status == ERROR:
        raise ValueError, "Could not create data %s"%(name)

lib.nxicompmakedata_.restype = c_int
lib.nxicompmakedata_.argtypes  = [c_void_p, c_char_p, c_int, c_int, c_int_p,
                                  c_int, c_int_p]
def compmakedata(handle, name, shape, storage, mode, chunk_shape):
    """
    Create a data element of the given dimensions and storage class.  See
    getinfo for details on storage class.  Compression mode is one of
    'none', 'lzw', 'rle' or 'huffman'.  chunk_shape gives the alignment
    of the compressed chunks in the data file.  It should be of the same
    length as the shape parameter, as there is a separate chunk distance
    for each dimension.

    Raises ValueError if it fails.

    Corresponds to status=NXmakedata(handle,name,type,rank,dims).
    """
    nxstorage = nxtype[storage]
    status = lib.nximakedata_(handle,name,nxstorage,len(shape),
                              shape.ctypes.data,compression[mode],
                              chunk_shape.ctypes)
    if status == ERROR:
        raise ValueError, "Could not create data %s"%(name)

lib.nxigetdata_.restype = c_int
lib.nxigetdata_.argtypes = [c_void_p, c_void_p]
def getdata(handle, shape, storage):
    """
    Return the data.  If data is a string (1-D char array), a python
    string is returned.  If data is a scalar (1-D numeric array of
    length 1), a python numeric scalar is returned.

    Raises RuntimeError if this fails.

    Corresponds to the status = NXgetdata (handle, data) function.   
    Unlike the underlying NeXus interface, getdata requires the shape
    and size of the data so that it can allocate memory to return
    the value.
    """
    # TODO: consider providing a handle to an existing array so that
    # we don't thrash memory when reading an writing many identically
    # sized data files.
    # TODO: consider making this a pure NeXus wrapper, moving the
    # string/scalar/array support to the caller.
    arg,ret,size = _build_storage(storage,shape)
    status = lib.nxigetdata_(handle,arg)
    if status == ERROR:
        raise ValueError, "Could not read data"
    #print "data",ret()
    return ret()


lib.nxiputdata_.restype = c_int
lib.nxiputdata_.argtypes = [c_void_p, c_void_p]
def putdata(handle, data, storage):
    """
    Write data into the currently open data block.

    Raises ValueError if this fails.

    Corresponds to the status = NXputdata (handle, data)
    """
    if storage == 'char':
        value = data
    elif hasattr(data,'shape') and len(data.shape)>0:
        value = data.ctypes.data
    else:
        data = N.zeros((1),storage)
        value = data.ctypes.data
    status = lib.nxiputdata_(handle,value)
    if status == ERROR:
        raise ValueError, "Could not write data"
    

# ==== Attributes ====
lib.nxiinitattrdir_.restype = c_int
lib.nxiinitattrdir_.argtypes = [c_void_p]
def initattrdir(handle):
    """
    Reset the getnextattr list to the first attribute.

    Raises RuntimeError if this fails.

    Corresponds to status = NXinitattrdir(handle)
    """
    status = lib.nxiinitattrdir_(handle)
    if status == ERROR:
        raise RuntimeError, "Could not reset attribute list"
    
lib.nxigetattrinfo_.restype = c_int
lib.nxigetattrinfo_.argtypes = [c_void_p, c_int_p]
def getattrinfo(handle):
    """
    Returns the number of attributes for the currently open
    group/data object.  Do not call getnextattr() more than
    this number of times.

    Raises RuntimeError if this fails.

    Corresponds to status = NXgetattrinfo(handl, &n)
    """
    n = c_int(0)
    status = lib.nxigetattrinfo_(handle,C.byref(n))
    if status == ERROR:
        raise RuntimeError, "Could not get attr info"
    #print "num attrs",n.value
    return n.value

lib.nxigetnextattr_.restype = c_int
lib.nxigetnextattr_.argtypes = [c_void_p, c_char_p, c_int_p, c_int_p]
def getnextattr(handle):
    """
    Returns the name, length, and storage type for the next attribute.
    Call getattrinfo to determine the number of attributes before
    calling getnextattr. Storage type is returned as a string.  See
    getinfo for details.  Length seems to be the number of elements
    in the attribute rather than the number of bytes required to
    store the entire attribute (NeXus API documentation suggests
    otherwise).  

    Raises RuntimeError if NeXus returns ERROR or EOD.

    Corresponds to status = NXgetnextattr(handle,name,&length,&storage)
    but with storage_class converted from HDF values to numpy compatible
    strings.
    """
    name = C.create_string_buffer(MAXNAMELEN)
    length = c_int(0)
    storage = c_int(0)
    status = lib.nxigetnextattr_(handle,name,byref(length),byref(storage))
    if status == ERROR or status == EOD:
        raise RuntimeError, "Could not get next attr"
    storage = pytype[storage.value]
    #print "next attr",name.value,length.value,storage
    return name.value, length.value, storage

lib.nxigetattr_.restype = c_int
lib.nxigetattr_.argtypes = [c_void_p, c_char_p, c_void_p, c_int_p]
def getattr(handle, name, length, storage):
    """
    Returns the value of the named attribute.  Requires length and
    storage from getnextattr to allocate the appropriate amount of
    space for the attribute.

    Corresponds to status = NXgetattr(handle,name,data,&length,&storage)

    Unlike NeXus API, length is the number of elements rather than the
    number of bytes to be read.
    """
    arg,ret,size = _build_storage([length],storage)
    nxstorage = c_int(nxtype[storage])
    length = c_int(size)
    status = lib.nxigetattr_(handle,name,arg,byref(length),byref(nxstorage))
    if status == ERROR:
        raise ValueError, "Could not read attr %s" % (name)
    #print "attr",name,ret()
    return ret()

lib.nxiputattr_.restype = c_int
lib.nxiputattr_.argtypes = [c_void_p, c_char_p, c_void_p, c_int, c_int]
def putattr(handle, name, value, storage):
    """
    Saves the named attribute.

    Raises ValueError if the attribute could not be saved.
    
    Corresponds to status = NXputattr(handle,name,data,length,storage)

    Unlike NeXus API, length is the number of elements rather than the
    number of bytes to be written.
    """
    nxstorage = c_int(nxtype[storage])
    if storage == 'char':
        arg = value
        length = c_int(len(value))
    elif hasattr(value,'shape') and len(value.shape)>0:
        arg = value.ctypes.data
        length = c_int(len(value))
    else:
        arg = N.array([value],storage).ctypes.data
        length = 1
    status = lib.nxiputattr_(handle,name,arg,length,nxstorage)
    if status == ERROR:
        raise ValueError, "Could not write attr %s" % (name)
