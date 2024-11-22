from __future__ import print_function

import sys
import posixpath
import zipfile
import json

import numpy

def bytes_to_str(s):
    # type: (AnyStr) -> str
    return s.decode('utf-8') if isinstance(s, bytes) else s  # type: ignore

builtin_open = open

__version__ = "0.0.1"


class Node(object):
    _attrs_filename = ".attrs"

    def __init__(self, parent_node=None, path="/", nxclass=None, attrs=None):
        self.root = self if parent_node is None else parent_node.root
        self.readonly = self.root.readonly
        if path.startswith("/"):
            # absolute path
            self.path = path
        else:
            # relative
            self.path = posixpath.join(parent_node.path, path)

    def makeAttrs(self):
        attr_data = self.root.open(posixpath.join(self.path, self._attrs_filename), "r").read()
        return json.loads(bytes_to_str(attr_data))

    @property
    def parent(self):
        return self.root[posixpath.dirname(self.name)]

    @property
    def groups(self):
        return dict([(gn, Group(self, gn)) for gn in self.groupnames])

    @property
    def groupnames(self):
        return  [x for x in self.root.listdir(self.path) if self.root.isdir(posixpath.join(self.path, x))]

    @property
    def name(self):
        return self.path

    def keys(self):
        return [x for x in self.root.listdir(self.path)
                if not x.endswith('.attrs') and not x.endswith('.link')]

    def values(self):
        keys = self.keys()
        return [self[k] for k in keys]

    def items(self):
        keys = self.keys()
        return [(k, self[k]) for k in keys]

    def __contains__(self, key):
        return self.root.exists(posixpath.join(self.path, key))

    def __getitem__(self, path):
        """ get an item based only on its path.
        Can assume that next-to-last segment is a group (dataset is lowest level)
        """
        if path.startswith("/"):
            # absolute path
            full_path = path
        else:
            # relative
            full_path = posixpath.join(self.path, path)

        #os_path = posixpath.join(self.os_path, full_path.lstrip("/"))
        if self.root.exists(full_path):
            if self.root.isdir(full_path):
                # it's a group
                return Group(self, full_path)
            elif self.root.exists(full_path + ".link"):
                # it's a link
                return makeSoftLink(self, full_path)
            else:
                # it's a field
                return FieldFile(self, full_path)
        else:
            # the item doesn't exist
            raise KeyError(path)

    def get(self, path, default_value):
        try:
            value = self.__getitem__(path)
            return value
        except KeyError:
            return default_value

    def add_field(self, path, **kw):
        FieldFile(self, path, **kw)

    def add_group(self, path, nxclass, attrs={}):
        Group(self, path, nxclass, attrs)


class File(Node):
    def __init__(self, filename, file_obj=None):
        self.readonly = True
        Node.__init__(self, parent_node=None, path="/")
        if file_obj is None:
            file_obj = builtin_open(filename, mode='rb')
        self.zipfile = zipfile.ZipFile(file_obj)
        self.attrs = self.makeAttrs()
        self.filename = filename
        self.mode = "r"

    def flush(self):
        # might make this do writezip someday.
        pass

    def isdir(self, path):
        """ abstraction for looking up paths:
        should work for unpacked directories and packed zip archives """
        path = path.lstrip("/")
        if path == "":
            return True # root path
        else:
            filenames = self.root.zipfile.namelist()
            return (path.rstrip("/") + "/") in filenames

    def listdir(self, path):
        """ abstraction for looking up paths:
        should work for unpacked directories and packed zip archives """
        path = path.strip("/")
        return [posixpath.basename(fn.rstrip("/"))
                for fn in self.zipfile.namelist()
                if posixpath.dirname(fn.rstrip("/")) == path]

    def exists(self, path):
        path = path.strip("/")
        filenames = self.root.zipfile.namelist()
        return path in filenames or self.isdir(path)

    def read(self, path):
        return self.open(path, "r").read()

    def getsize(self, path):
        path = path.lstrip("/")
        return self.zipfile.getinfo(path).file_size

    def open(self, path, mode):
        path = path.lstrip("/")
        return self.zipfile.open(path, "r")

    def __repr__(self):
        return "<HDZIP file \"%s\" (mode %s)>" % (self.filename, self.mode)

    def close(self):
        # there seems to be only one read-only mode
        self.zipfile.close()


class Group(Node):
    def __init__(self, node, path, nxclass="NXCollection", attrs={}):
        Node.__init__(self, parent_node=node, path=path)
        if path.startswith("/"):
            # absolute path
            self.path = path
        else:
            # relative
            self.path = posixpath.join(node.path, path)

        self.attrs = self.makeAttrs()

    def __repr__(self):
        return "<HDZIP group \"" + self.path + "\">"


class FieldFile(object):
    _formats = {
        'S': '%s',
        'f': '%.8g',
        'i': '%d',
        'u': '%d',
        'b': '%d'}

    _attrs_suffix = ".attrs"

    def __init__(self, node, path, **kw):
        self.root = node.root
        if not path.startswith("/"):
            # relative path:
            path = posixpath.join(node.path, path)
        self.path = path
        attr_data = self.root.open(self.path + self._attrs_suffix, "r").read()
        self.attrs = json.loads(bytes_to_str(attr_data))
        self._value = None


    def __repr__(self):
        return ("<HDZIP field \"%s\" %s \"%s\">"
                % (self.name, str(self.attrs['shape']), self.attrs['dtype']))

    def __getitem__(self, slice_def):
        return self.value.__getitem__(slice_def)

    def __setitem__(self, slice_def, newvalue):
        raise Exception("read only")

    # promote a few attrs items to python object attributes:
    @property
    def shape(self):
        return self.attrs.get('shape', None)

    @property
    def dtype(self):
        return self.attrs.get('dtype', None)

    @property
    def name(self):
        return self.path


    @property
    def parent(self):
        return self.root[posixpath.dirname(self.name)]

    @property
    def value(self):
        if self._value is None:
            attrs = self.attrs
            target = self.path
            try:
                infile = self.root.open(target, 'rb')
                dtype_str = str(attrs['format'])
                # CRUFT: <l4, <d8 are not sensible dtypes
                if dtype_str == '<l4': dtype_str = '<i4'
                if dtype_str == '<l8': dtype_str = '<i8'
                if dtype_str == '<d8': dtype_str = '<f8'
                dtype_str = dtype_str.replace('S', 'U')
                dtype = numpy.dtype(dtype_str)
                if attrs.get('binary', False) == True:
                    s = infile.read()
                    d = numpy.frombuffer(s, dtype=dtype).copy()
                elif self.root.getsize(target) == 0:
                    d = numpy.array([], dtype=dtype)
                elif self.root.getsize(target) == 1:
                    # empty entry: only contains \n
                    # this is only possible with empty string being written.
                    d = numpy.array([''], dtype=dtype)
                elif dtype.kind == 'S':
                    data = [[v for v in line[:-1].split(b'\t')]
                            for line in infile]
                    d = numpy.squeeze(numpy.array(data))
                    d = _unescape_str(d)
                elif dtype.kind == 'U':
                    data = [[v.decode('utf-8') for v in line[:-1].split(b'\t')]
                            for line in infile]
                    d = numpy.squeeze(numpy.array(data))
                    d = _unescape_str(d)
                else:
                    d = numpy.loadtxt(infile, dtype=dtype, delimiter='\t')
            finally:
                infile.close()
            if 'shape' in attrs:
                try:
                    d = d.reshape(attrs['shape'])
                except Exception:
                    # literally do nothing.  Should be logging this.
                    pass
            self._value = d
        return self._value

def _unescape_str(data):
    if data.size:
        # Hide the \\ in \1 so that it doesn't get processed twice.  At the
        # end, convert it back to \\.  This allows us to support \\t without
        # it turning into a tab character or a backslash tab sequence.
        # Don't convert empty arrays since the change type
        data = numpy.char.replace(data, '\\\\', '\1')
        data = numpy.char.replace(data, '\\t', '\t')
        data = numpy.char.replace(data, '\\r', '\r')
        data = numpy.char.replace(data, '\\n', '\n')
        data = numpy.char.replace(data, '\1', '\\')

    return data

def makeSoftLink(parent, path):
    orig_attrs_path = path.lstrip("/") + ".link"
    attr_data = parent.root.open(orig_attrs_path, 'r').read()
    linkinfo = json.loads(bytes_to_str(attr_data))
    target = linkinfo['target']
    target_obj = parent.root[target]
    target_obj.orig_path = path
    return target_obj

#compatibility with h5nexus:
group = Group
field = FieldFile
open = File
