from __future__ import print_function

import sys
from collections import OrderedDict

import numpy as np

if sys.version_info[0] > 2:
    def tostr(s):
        return s.decode('utf8')
    def decode(s, encoding='utf8'):
        return s.decode(encoding)
    STR_ENCODING = 'utf8'
else:
    def tostr(s):
        return s
    def decode(s, encoding='utf8'):
        return unicode(s, encoding)
    STR_ENCODING = None

DATA_TYPES = {
    1: "scalar",
    2: "matrix",
    3: "complex scalar",
    4: "complex matrix",
    5: "old_string",
    6: "range",
    7: "string",
}

TYPE_CODES = {
    0: "u1",
    1: "u2",
    2: "u4",
    3: "i1",
    4: "i2",
    5: "i4",
    6: "f4",
    7: "f8",
    8: "u8",
    9: "i8",
}
DTYPES = {k: np.dtype(v) for k, v in TYPE_CODES.items()}

def loadoct(fd, encoding=STR_ENCODING):
    """
    Read an octave binary file from the file handle fd, returning
    an array of structures.  If encoding is not None then convert
    strings from bytes to unicode.  Default is STR_ENCODING, which
    is utf8 for python 3 and None for python 2, yielding arrays
    of type str in each dialect.
    """
    magic = fd.read(10)
    assert(magic == b"Octave-1-L" or magic == b"Octave-1-B")
    endian = "<" if magic[-1:] == b"L" else ">"
    # Float type is 0: IEEE-LE, 1: IEEE-BE, 2: VAX-D, 3: VAX-G, 4: Cray
    # Not used since Octave assumes IEEE format floats.
    _float_format = fd.read(1)
    len_dtype = np.dtype(endian + "i4")
    def read_len():
        len_bytes = fd.read(4)
        if not len_bytes:
            return None
        return np.frombuffer(len_bytes, len_dtype)[0]
    table = OrderedDict()
    while True:
        name_length = read_len()
        if name_length is None:  # EOF
            break
        name = tostr(fd.read(name_length))
        doc_length = read_len()
        doc = tostr(fd.read(doc_length)) if doc_length else ''
        is_global = bool(ord(fd.read(1)))
        data_type = ord(fd.read(1))
        if data_type == 255:
            type_str = tostr(fd.read(read_len()))
        else:
            type_str = DATA_TYPES[data_type]
        #print("reading", name, type_str)
        if type_str.endswith("scalar"):
            if type_str == "scalar":
                dtype = DTYPES[ord(fd.read(1))]
            elif type_str == "complex scalar":
                _ = fd.read(1)
                dtype = np.dtype('complex128')
            elif type_str == "float complex scalar":
                _ = fd.read(1)
                dtype = np.dtype('complex64')
            else:
                dtype = np.dtype(type_str[:-7])
            dtype = dtype.newbyteorder(endian)
            data = np.frombuffer(fd.read(dtype.itemsize), dtype)
            table[name] = data[0]
        elif type_str.endswith("matrix"):
            ndims = read_len()
            if ndims < 0:
                ndims = -ndims
                dims = np.frombuffer(fd.read(4*ndims), len_dtype)
            else:
                dims = (ndims, read_len())
            count = np.prod(dims)
            if type_str == "matrix":
                dtype = DTYPES[ord(fd.read(1))]
            elif type_str == "complex matrix":
                _ = fd.read(1)
                dtype = np.dtype('complex128')
            elif type_str == "float complex matrix":
                _ = fd.read(1)
                dtype = np.dtype('complex64')
            else:
                dtype = np.dtype(type_str[:-7])
            dtype = dtype.newbyteorder(endian)
            data = np.frombuffer(fd.read(count*dtype.itemsize), dtype)
            # Note: Use data.copy() to make a modifiable array.
            table[name] = data.reshape(dims, order='F')
        elif type_str == "old_string":
            data = fd.read(read_len())
            if encoding is not None:
                data = decode(data, encoding)
            table[name] = data
        elif type_str in ("string", "sq_string"):
            nrows = read_len()
            if nrows < 0:
                ndims = -nrows
                dims = np.frombuffer(fd.read(4*ndims), len_dtype)
                count = np.prod(dims)
                fortran_order = np.frombuffer(fd.read(count), dtype='uint8')
                c_order = np.ascontiguousarray(fortran_order.reshape(dims, order='F'))
                data = c_order.view(dtype='|S'+str(dims[-1]))
                if encoding is not None:
                    data = np.array([decode(s, encoding) for s in data.flat])
                table[name] = data.reshape(dims[:-1])
            else:
                data = [fd.read(read_len()) for _ in range(nrows)]
                if encoding is not None:
                    data = [decode(s, encoding) for s in data]
                table[name] = np.array(data)

        else:
            raise NotImplementedError("unknown octave type "+type_str)
        #print("read %s:%s"%(name, type_str), table[name])
    return table

read_octave_binary = loadoct  # CRUFT: deprecated name

def _dump(filename, encoding=STR_ENCODING):
    import gzip

    if filename.endswith('.gz'):
        with gzip.open(filename, 'rb') as fd:
            table = loadoct(fd, encoding)
    else:
        with open(filename, 'rb') as fd:
            table = loadoct(fd, encoding)
    for k, v in table.items():
        print(k, v)

if __name__ == "__main__":
    #_dump(sys.argv[1], encoding='utf8')  # unicode
    #_dump(sys.argv[1], encoding=None)  # bytes
    _dump(sys.argv[1])  # str, encoding=STR_ENCODING

