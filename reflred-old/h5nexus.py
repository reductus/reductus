"""
NeXus file interface.
"""
__all__ = ["open", "group", "field", "append", "extend", "link",
           "walk", "datasets", "summary"]
import sys
import os

from nice.lib.platform_h5py import h5py as h5
import numpy

from . import iso8601

# Conforms to the following version of the NeXus standard
__version__ = "4.2.1"

# Version of the library
api_version = "0.1"

_MEMFILE_COUNT = 0

def open(filename, mode="r", timestamp=None, creator=None, **kw): #@ReservedAssignment
    """
    Open a NeXus file.

    *mode* : string
        File open mode.

        ==== =========================================
        Mode Behavior
        ---- -----------------------------------------
        r    open existing file read-only
        r+   open existing file read-write
        w    create empty file
        w-   create empty file, fail if exists
        a    open file read-write or create empty file
        mem  create empty in-memory file
        ==== =========================================

    *timestamp* : string, datetime, time_struct or float
        On file creation, records a timestamp for the file.  This can be
        a float returned by time.time(), a time_struct returned by
        time.localtime(time.time()), an ISO 8601 string or a datetime
        object such as that returned by datetime.datetime.now().
    *creator* : string
        On file creation, records the name of the program or facility that
        created the data.  If not specified, then the creator field will
        not be written.

    Additional keywords (*driver*, *libver*) are passed to the h5py File
    function.  This allows, for example, the creation of unbuffered
    files which write the data immediately when it arrives without the
    need to flush.  See the h5py documentation for details.

    In memory file objects could be created using driver="core" and
    backing_store=True|False.  However, even when backing_store is
    False, the filename must be unique within the process, so we instead
    provide the special open mode of "mem".  If a filename is provided,
    then the file is opened with the core driver and backing_store=True.
    When it is not provided a unique temporary filename is generated
    and backing_store=False.

    Returns an H5 file object.
    """
    if mode=="mem":
        mode = "a"
        if filename:
            kw.update({'driver':'core', 'backing_store':True})
        else:
            kw.update({'driver':'core', 'backing_store':False})
            global _MEMFILE_COUNT
            _MEMFILE_COUNT += 1
            filename = "temp%05d.nxs"%_MEMFILE_COUNT

    preexisting = os.path.exists(filename)

    try:
        f = h5.File(filename, mode, **kw)
    except IOError:
        annotate_exception("when opening %s with mode %s"%(filename,mode))
        raise
        
        
    if (mode == "a" and not preexisting) or mode == "w":
        if timestamp is None:
            timestr = iso8601.now()
        else:
            # If given a time string, check that it is valid
            try:
                timestamp = iso8601.parse_date(timestamp)
            except TypeError:
                pass
            timestr = iso8601.format_date(timestamp)
        f.attrs['NX_class'] = 'NXroot'
        f.attrs['file_name'] = filename
        f.attrs['file_time'] = timestr
        f.attrs['HDF5_Version'] = h5.version.hdf5_version
        f.attrs['NeXus_version'] = __version__
        if creator is not None:
            f.attrs['creator'] = creator
    return f

def group(node, path, nxclass, attrs={}):
    """
    Create a NeXus group.

    *path* can be absolute or relative to the node.

    This function marks the group with its NeXus class name *nxclass*.
    Unlike the underlying H5py create_group method on node, the entire
    path up to the created group must exist.

    Returns an H5 group object.
    """
    node,child = _get_path(node,path)
    try:
        group = node.create_group(child)
    except:
        annotate_exception("when creating group %s"%path)
        raise
    group.attrs['NX_class'] = nxclass.encode('UTF-8')
    for k,v in attrs.items(): group.attrs[k] = v
    return group

def link(node, link):
    """
    Create an internal link from an HDF-5 group or dataset to another
    dataset.

    *node* : h5 object
        Target of the link.
    *link* : string
        Path where link should be created.  This can be an absolute path,
        or it can be relative to the parent group of the node.

    A 'target' attribute is added to the target object indicating its
    path.  When processing the file later, you can locate the target
    of the link using::

        str(node.name) == node.attrs['target']

    The NeXus standard also supports external links using the standard
    HDF-5 external linking interface::

        h5file[link] = nexus.h5.ExternalLink(filename,path)
    """
    if not 'target' in node.attrs:
        node.attrs["target"] = str(node.name) # Force string, not unicode
    try:
        node.parent[link] = node
    except:
        annotate_exception("when linking %s to %s"%(link,node.name))
        raise

def update_hard_links(root, nodes):
    """
    Replace all links to nodes within root.  Perform this on all nodes at
    once since walking the hdf tree is expensive.
    """
    for node in nodes:
        if not 'target' in node.attrs:
            node.attrs["target"] = str(node.name) # Force string, not unicode
    _update_hard_links(root, dict((str(node.name), node) for node in nodes))

def _update_hard_links(root, nodes):    
    #print "relink checking",root.name
    for fieldID,field in root.items():
        target = field.attrs.get('target', '')
        if (target in nodes and target != str(field.name)):
            # If field is linked to node and field is not itself
            #print "relink",field.name,"to",link.name
            del root[fieldID]
            root[fieldID] = nodes[target]
        elif isinstance(field, h5.Group) and not field.name:
            # If group, then recurse
            update_hard_links(field, nodes)

BOOL = numpy.dtype('bool')
UINT8 = numpy.dtype('uint8')
FLOAT32 = numpy.dtype('float32')

def _map_type(dtype):
    if dtype is None: return None
    dtype = numpy.dtype(dtype)
    if dtype == BOOL:
        return UINT8
    else:
        return dtype

# Default chunk size for extensible objects
CHUNK_SIZE = 1000
# Options passed to h5 create_dataset
_CREATE_OPTS = ['chunks','maxshape','compression',
                'compression_opts','shuffle','fletcher32']
def field(node, path, **kw):
    """
    Create a data object.
    
    Returns the data set created, or None if the data is empty.

    :Parameters:

    *node* : H5 object
        Handle to an H5 object.  This could be a file or a group.

    *path* : string
        Path to the data.  This could be a full path from the root
        of the file, or it can be relative to a group.  Path components
        are separated by '/'.

    *data* : array or string
        If the data is known in advance, then the value can be given on
        creation. Otherwise, use *shape* to give the initial storage
        size and *maxshape* to give the maximum size.

    *units* : string
        Units to display with data.  Required for numeric data.

    *label* : string
        Axis label if data is numeric.  Default for field dataset_name
        is "Dataset name (units)".

    *attrs* : dict
        Additional attributes to be added to the dataset.


    :Storage options:

    *dtype* : numpy.dtype
        Specify the storage type for the data.  The set of datatypes is
        limited only by the HDF-5 format, and its h5py interface.  Usually
        it will be 'int32' or 'float32', though others are possible.
        Data will default to *data.dtype* if *data* is specified, otherwise
        it will default to 'float32'.

    *shape* : [int, ...]
        Specify the initial shape of the storage and fill it with zeros.
        Defaults to [1, ...], or to the shape of the data if *data* is
        specified.

    *maxshape* : [int, ...]
        Maximum size for each dimension in the dataset.  If any dimension
        is None, then the dataset is resizable in that dimension.
        For a 2-D detector of size (Nx,Ny) with Nt time of flight channels
        use *maxshape=[Nx,Ny,Nt]*.  If the data is to be a series of
        measurements, then add an additional empty dimension at the front,
        giving *maxshape=[None,Nx,Ny,Nt]*.  If *maxshape* is not provided,
        then use *shape*.

    *chunks* : [int, ...]
        Storage block size on disk, which is also the basic compression
        size.  By default *chunks* is set from maxshape, with the
        first unspecified dimension set such that the chunk size is
        greater than nexus.CHUNK_SIZE. :func:`make_chunks` is used
        to determine the default value.

    *compression* : 'none|gzip|szip|lzf' or int
        Dataset compression style.  If not specified, then compression
        defaults to 'szip' for large datasets, otherwise it defaults to
        'none'. Datasets are considered large if each frame in maxshape
        is bigger than CHUNK_SIZE.  Eventmode data, with its small frame
        size but large number of frames, will need to set compression
        explicitly.  If compression is an integer, then use gzip compression
        with that compression level.

    *compression_opts* : ('ec|nn', int)
        szip compression options.

    *shuffle* : boolean
        Reorder the bytes before applying 'gzip' or 'hzf' compression.

    *fletcher32* : boolean
        Enable error detection of the dataset.

    :Returns:

    *dataset* : h5 object
        Reference to the created dataset.
    """
    node,child = _get_path(node,path)
    if child.startswith('_'): child = "U"+child
    target = "/".join((node.name,child))
    
    # Make sure we get an error we understand when trying to overwrite a field
    if child in node:
        raise ValueError("data object already exists at %s"%target)

    # Set the default field creation opts
    create_opts = {}
    for k in _CREATE_OPTS:
        v = kw.pop(k,None)
        if v is not None: create_opts[k] = v
    # TODO: any maxshape provided by the caller is being overwritten below
    # if the code thinks it needs to set maxshape.

    data = kw.pop('data', None)
    dtype = kw.pop('dtype', None)
    shape = kw.pop('shape', None)
    units = kw.pop('units', None)
    label = kw.pop('label', None)
    attrs = kw.pop('attrs', {})
    
    if kw: raise TypeError("unknown keyword(s) "+", ".join(kw.keys()))

    try: 
        dtype = _map_type(dtype)
    except:
        annotate_exception("when creating %r of type %r"%(target, dtype))
        raise


    # Fill in default creation options
    if data is not None:
        #print "known data",data
        # Creating a field with existing data
        # Note that NeXus doesn't support scalar field values.
        try: data = data.encode('UTF-8')
        except AttributeError: pass
        if numpy.isscalar(data): data = [data]
        # Note: may want to use array of vlen strings for string list
        # Try converting a list into a string separated by "\n"
        if isinstance(data, list):
            try: data = '\n'.join(data)
            except: pass
        #print node, path, dtype
        if dtype is None:
            # Infer type from array
            data = numpy.asarray(data)
            # Force type conversion for inferred type
            data = numpy.asarray(data, _map_type(data.dtype))
        else:
            try:
                data = numpy.asarray(data, dtype=dtype)
            except TypeError:
                raise TypeError("data type %r not understood when creating %s"
                                %(dtype,target))
        dtype = data.dtype
        if ('compression' not in create_opts
            and data.nbytes > CHUNK_SIZE):
            create_opts['compression'] = 9
        # NAPI requires an extra dimension for string arrays
        if shape is None: 
            shape = data.shape
        # TODO: what's going on with arrays of strings in nexus? Why the extra dimension
        if dtype.kind=='S':
            shape = list(data.shape)+[1]
            if 'maxshape' in create_opts: create_opts['maxshape'].append(1)
        create_opts['shape'] = shape
        # HDF can't handle length 0 fixed size arrays
        if not all(shape):
            create_opts['maxshape'] = [(dim if dim else None) for dim in shape]
        create_opts['data'] = data
    else:
        # Creating a field to be filled in later
        maxshape = create_opts.pop('maxshape', None)
        chunks = create_opts.pop('chunks', None)
        compression = create_opts.pop('compression', None)
        if dtype is None: dtype = FLOAT32  # default type to float32
        if shape and maxshape is None:
            raise TypeError("Need to specify shape or maxshape for dataset %s"%target)
        if shape is None:
            shape = [(k if k else 0) for k in maxshape]
        if maxshape is None:
            maxshape = shape
        if chunks is None:
            chunks = make_chunks(maxshape, dtype, CHUNK_SIZE)
        if compression is None:
            size = numpy.prod([d for d in maxshape if d])*dtype.itemsize
            compression = 9 if size > CHUNK_SIZE else None
        elif compression == 'none':
            compression = None
        create_opts.update(shape=shape,maxshape=maxshape,dtype=dtype,
                           compression=compression,chunks=chunks)

    # Numeric data needs units
    if dtype.kind in ('u','i','f','c') and units is None:
        raise TypeError("Units required for numeric data at %s"%target)
    
    # Label defaults to 'Field (units)'
    if label is None:
        name = " ".join(child.split('_')).capitalize()
        if units:
            label = "%s (%s)"%(name,units)
        else:
            label = name

    #print "create_opts", create_opts
    # Create the data
    try:
        if 'data' in create_opts and data.size == 0:
            return
        dataset = node.create_dataset(child, **create_opts)
    except:
        annotate_exception("when creating field %s"%target)
        raise
    attrs=attrs.copy()
    if units is not None:
        attrs['units'] = units
    if label: # not None or ""
        attrs['long_name'] = label
    for k,v in attrs.items():
        try:
            #print type(v),v
            # Note: may want to use array of vlen strings for option list
            # Try converting a list into a string separated by "|"
            if isinstance(v, list):
                try: v = '|'.join(v)
                except: pass
            #try: v = v.encode('UTF-8')
            #except AttributeError: pass
            try: v = ''.join([xi for xi in v if ord(xi) < 128])
            except: pass
            dataset.attrs[k] = v
        except:
            #print k,v
            annotate_exception("when creating attribute %s@%s"%(target,k))
            raise
    return dataset

def append(node, data):
    """
    Append to a data node.

    Like list.append, this extends the node by one frame and writes
    the data to the end.  The data shape should match the shape of
    a single frame of the node, so it will have one fewer dimensions
    and data.shape[:] == node.shape[1:].

    Append is equivalent to::

        node.resize(node.shape[0]+1, axis=0)
        node[-1] = data
    """
    #print node.shape, data.shape
    try:
        node.resize(node.shape[0]+1, axis=0)
        node[-1] = data
    except Exception, exc:
        args = exc.args
        exc.args = tuple([args[0]+" while appending to %s"%node.name]+list(args[1:]))
        raise

def extend(node, data):
    """
    Extend the data in the node.

    Like list.extend, this extends the node by as many frames as there
    are in the data and writes the data to the end.  The data shape should
    match the shape of a group of frames of the node, so it will have the
    same number of dimensions and data.shape[1:] == node.shape[1:].

    For more complicated operations, use node.resize to expand the
    data space then assign directly to the desired slice.
    """
    if len(data) > 0:
        node.resize(node.shape[0]+data.shape[0], axis=0)
        node[-data.shape[0]:] = data

def make_chunks(maxshape, dtype, min_chunksize):
    """
    Determine chunk size for storage.

    *maxshape* : [int, ...]
        The storage dimensions, with extensible dimensions indicated by None.
    *dtype* : numpy.dtype
        Storage type.
    *min_chunksize* : int
        Minimum size recommended for the chunk.
    """
    varying_idx = [i for i,v in enumerate(maxshape) if v is None]
    if varying_idx:
        chunks = [(v if v else 1) for v in maxshape] # Non-zero dims
        fixed_size = numpy.prod(chunks) * numpy.dtype(dtype).itemsize
        chunks[varying_idx[0]] = min_chunksize//fixed_size + 1
        chunks = tuple(chunks)
    else:
        chunks = None
    return chunks

def _name(node):
    return node.name.split("/")[-1]

def walk(node, topdown=True):
    """
    Walk an HDF-5 tree.

    Yields a sequence of (parent,groups,datasets).

    *node* is root of the tree, which should be an HDF-5 group.

    *topdown* is true if parent node should be visited before children.

    Like os.walk, groups can be modified during a topdown traversal to limit
    the set of groups visited.
    """
    #print "entering walk with",node
    if not isinstance(node, h5.Group):
        raise TypeError("must walk a group")
    groups, datasets = [],[]
    for n in node.values():
        if isinstance(n, h5.Dataset):
            datasets.append(n)
        elif isinstance(n, h5.Group):
            groups.append(n)
        else:
            raise TypeError("Expected group or dataset")
    if topdown:
        yield node, groups, datasets
        for g in groups:
            for args in walk(g, topdown=topdown): yield args
    else:
        for g in groups:
            for args in walk(g, topdown=topdown): yield args
        yield node, groups, datasets

def datasets(root):
    """
    Return all datasets within a node or any of its children.

    Each dataset is a list of paths which point to it.   For example,
    the average temperature at the sample may be linked to
    *DAS_logs/Temperature/average_value*, *sample/temperature*,
    *sample/temperature_env/average_value* and *data/temperature*.

    The datasets are not returned in any particular order.
    """
    datasets = {}
    links = root.file.id.links
    for node, _groups, fields in walk(root):
        for f in fields:
            # Save name since softlink handling chases down links
            linkname = f.name
            # Chase down link to a file location or an external file
            while True:
                linkinfo = links.get_info(f.name)
                if linkinfo.type == h5.h5l.TYPE_SOFT:
                    f = node[links.get_val(f.name)]
                    continue
                elif linkinfo.type == h5.h5l.TYPE_HARD:
                    location = linkinfo.u
                    break
                elif linkinfo.type == h5.h5l.TYPE_EXTERNAL:
                    location = links.get_value(f.name)
                    break
            # Return list associated with location, or create new one
            linkset = datasets.setdefault(location,[])
            # Add name to list
            linkset.append(linkname)
    return list(datasets.values())  # Return copy of items

def copy_to_static(source,target):
    """
    Copy a file from one location to another, but make all datasets fixed size.
    """
    links = []
    rootlen = len(source.parent.name)+1 if source != source.parent else 1
    for node, _groups, datasets in walk(source):
        relpath = node.name[rootlen:]
        # Copy group and attributes for parent
        # Subgroups will become parents in next iteration
        if relpath: # Don't try to create root group
            current = target.create_group(name=relpath)
        else:
            current = target
        for k,v in node.attrs.iteritems():
            current.attrs[k] = v
            #print "attr",k,v,type(v)
        # Copy data and attributes for datasets
        for obj in datasets:
            name = obj.name.split('/')[-1]

            # If it is a link save it for later since the target of the link
            # may not yet exist in the tree.
            if 'target' in obj.attrs and obj.attrs['target'] != obj.name:
                link = "/".join((node.name, name))
                links.append((obj, link))
                continue

            # if it is data, then write it
            if obj.compression:
                t = current.create_dataset(
                    name=name,
                    shape=obj.shape,
                    dtype=obj.dtype,
                    data=obj,
                    chunks=obj.chunks,
                    compression=obj.compression,
                    compression_opts=obj.compression_opts,
                    shuffle=obj.shuffle,
                    fletcher32=obj.fletcher32,
                    #maxshape=obj.maxshape,
                    )
            else:
                t = current.create_dataset(
                    name=name,
                    data=obj.value,
                    )
            for k,v in obj.attrs.iteritems():
                t.attrs[k] = v

    #for node, link in links:
    #    print "linking",node.name,"to",link
    #    node.parent[link] = node

def summarystr(group, indent=0, attrs=True, recursive=True):
    """
    Return the structure of the HDF 5 tree as a string.

    *group* is the starting group.

    *indent* is the indent for each line.

    *attrs* is False if attributes should be hidden

    *recursive* is False to show only the current level of the tree.
    """
    return "\n".join(_tree_format(group, indent, attrs, recursive))

def summary(group, indent=0, attrs=True, recursive=True):
    """
    Print the structure of an HDF5 tree.

    *group* is the starting group.

    *indent* is the indent for each line.

    *attrs* is False if attributes should be hidden

    *recursive* is False to show only the current level of the tree.
    """
    for s in _tree_format(group, indent, attrs, recursive):
        print s

def _tree_format(node, indent, attrs, recursive):
    """
    Return an iterator for the lines in a formatted HDF5 tree.

    Individual lines are not terminated by newline.
    """
    if not isinstance(node, h5.Group):
        raise TypeError("must walk a group")

    # Find fields and subgroups within the group; do this ahead of time
    # so that we can show all fields before any subgroups.
    groups, datasets = [],[]
    for n in node.values():
        if isinstance(n, h5.Dataset):
            datasets.append(n)
        elif isinstance(n, h5.Group):
            groups.append(n)
        else:
            raise TypeError("Expected group or dataset")

    # Yield group as "nodename(nxclass)"
    yield "".join( (" "*indent, _group_str(node)) )

    # Yield group attributes as "  @attr: value"
    indent += 2
    if attrs:
        for s in _yield_attrs(node, indent):
            yield s

    # Yield fields as "  field[NxM]: value"
    for field in datasets:
        #print field

        # Field name is tail of path
        name = field.name.split('/')[-1]

        # Short circuit links
        if 'target' in field.attrs and field.attrs['target'] != field.name:
            yield "".join( (" "*indent, name, " -> ", field.attrs['target']) )
            continue

        # Format field dimensions
        ndim = len(field.shape)
        if ndim > 1 or (ndim == 1 and field.shape[0] > 1):
            shape = '['+'x'.join( str(dim) for dim in field.shape )+']'
        else:
            shape = ''
        #shape = '['+'x'.join( str(dim) for dim in field.shape)+']'+str(field.dtype)

        # Format string or numeric value
        size = numpy.prod(field.shape)
        if field.dtype.kind == 'S':
            if ndim == 0:
                value = _limited_str(field.value)
            elif ndim==1 or (ndim==2 and field.shape[1]==1):
                value = field.value.flatten()
                if size == 1:
                    value = _limited_str(value[0])
                elif size <= 5:
                    value = ", ".join(_limited_str(v,width=10) for v in value)
                else:
                    value = _limited_str(value[0])+', ... '
                value = '['+value+']'
            else:
                value = '[[...]]'
        else:
            if ndim == 0:
                value = "%g"%field.value
            elif ndim == 1:
                if size == 0:
                    value = '[]'
                elif size == 1:
                    value = "%g"%field.value[0]
                elif size <= 6:
                    value = ' '.join("%g"%v for v in field.value)
                else:
                    value =  ' '.join("%g"%v for v in field.value[:6]) + ' ...'
                value = '['+value+']'
            else:
                value = '[[...]]'
                
        dtype = ' '+str(field.dtype)

        # Yield field: value
        yield "".join( (" "*indent, name, shape, dtype, ': ', value) )

        # Yield attributes
        if attrs:
            for s in _yield_attrs(field, indent+2):
                yield s

    # Yield groups.
    # If recursive, show group details, otherwise just show name.
    if recursive:
        for g in groups:
            for s in _tree_format(g, indent, attrs, recursive):
                yield s
    else:
        for g in groups:
            yield "".join( (" "*indent, _group_str(g)) )

def _yield_attrs(node, indent):
    """
    Iterate over the attribute values of the node, excluding NX_class.
    """
    #print "dumping",node.name,"attrs",node.attrs.keys()
    for k in sorted(node.attrs.keys()):
        if k not in ("NX_class", "target"):
            yield "".join( (" "*indent, "@", k, ": ", str(node.attrs[k])) )

def _group_str(node):
    """
    Return the name and nexus class of a node.
    """
    if node.name == "/": return "root"
    nxclass = "("+node.attrs["NX_class"]+")" if "NX_class" in node.attrs else ""
    return node.name.split("/")[-1] + nxclass

def _limited_str(s, width=40):
    """
    Returns the string trimmed to a maximum of one line of width+3 characters,
    with ... substituted for any trimmed characters.  Leading and trailing
    blanks are removed.
    """
    s = str(s).strip()
    ret = s.split('\n')[0][:width]
    return ret if len(ret) == len(s) else ret+"..."


# ==== Helper routines ====
def _get_path(node, path):
    """
    Lookup path relative to node.
    
    Returns the parent-child pair, where
    parent is the group handle where the child should be and child is the
    name of the child.
    
    Raises KeyError if the parent group does not exist, but does not check
    for child.
    """
    if '/' in path:
        parentpath,child = path.rsplit('/',1)
        try:
            node = node[parentpath]
        except KeyError:
            raise KeyError("Path %s doesn't exist"%(node.name+"/"+path))
    else:
        child = path
    return node,child

def annotate_exception(msg, exc=None):
    """
    Add an annotation to the current exception, which can then be forwarded
    to the caller using a bare "raise" statement to reraise the annotated
    exception.
    """
    if not exc: exc = sys.exc_info()[1]
        
    args = exc.args
    if not args:
        arg0 = msg
    else:
        arg0 = " ".join((args[0],msg))
    exc.args = tuple([arg0] + list(args[1:]))


# ============= Test functions ==========

def test():
    from nice.writer import h5nexus

    # Sample data
    counts = [4, 2, 10, 45, 2150, 58, 6, 2, 3, 0]
    twotheta = numpy.arange(len(counts))*0.2+1.

    # Create the file
    nxs = h5nexus.open('writer_2_1.hdf5', 'w', driver='core', backing_store=False)
    entry = h5nexus.group(nxs, 'entry', 'NXentry')
    h5nexus.group(entry, 'data', 'NXdata')
    h5nexus.group(entry, 'instrument', 'NXinstrument')
    detector = h5nexus.group(nxs,'/entry/instrument/detector', 'NXdetector')
    h5nexus.field(detector, 'two_theta', data=twotheta, dtype="float32",
                units="degrees")
    h5nexus.field(detector, 'counts', data=counts, dtype="int32",
                units="counts", attrs={'signal': 1, 'axes': 'two_theta'})
    h5nexus.link(detector['two_theta'], '/entry/data/two_theta')
    h5nexus.link(detector['counts'], '/entry/data/counts')

    # Check that the data was written
    assert numpy.linalg.norm(numpy.array(counts)
                             - nxs['/entry/data/counts']) == 0
    assert numpy.linalg.norm(twotheta
                             - nxs['/entry/instrument/detector/two_theta']) <=1e-6

    # Search for unique datasets
    S = datasets(nxs)
    #print S
    assert len(S) == 2
    S1,S2 = set(S[0]),set(S[1])
    Gcounts = set(('/entry/data/counts','/entry/instrument/detector/counts'))
    G2theta = set(('/entry/data/two_theta','/entry/instrument/detector/two_theta'))
    assert (S1 == Gcounts and S2 == G2theta) or (S1 == G2theta and S2 == Gcounts)

    # All done
    nxs.close()

def main():
    """
    Print a summary tree describing the hdf file.
    """
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "-a":
            files,attrs = sys.argv[2:],True
        else:
            files,attrs = sys.argv[1:],False
        for fname in files:
            h = open(fname, "r")
            print "===",fname,"==="
            summary(h["/"], attrs=attrs)
            h.close()
    else:
        print "usage: python -m nice.stream.nexus [-a] files"

if __name__ == "__main__": main()
