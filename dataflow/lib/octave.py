from __future__ import print_function

import sys
from collections import OrderedDict

import numpy as np

if sys.version_info[0] > 2:
    def decode(s):
        return s.decode('utf-8')
else:
    def decode(s):
        return s

DATA_TYPES = {
    1: "scalar",
    2: "matrix",
    3: "complex scalar",
    4: "complex matrix",
    5: "old_string",
    6: "range",
    7: "string",
}

NUMPY_TYPE_CODES = {
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

def read_octave_binary(fd):
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
        name = decode(fd.read(name_length))
        doc_length = read_len()
        doc = decode(fd.read(doc_length)) if doc_length else ''
        is_global = bool(ord(fd.read(1)))
        data_type = ord(fd.read(1))
        if data_type == 255:
            type_length = read_len()
            type_str = decode(fd.read(type_length))
        else:
            type_str = DATA_TYPES[data_type]
        #print("reading", name, type_str)
        if type_str.endswith("scalar"):
            type_code = ord(fd.read(1))
            dtype = np.dtype(endian + NUMPY_TYPE_CODES[type_code])
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
            type_code = ord(fd.read(1))
            dtype = np.dtype(endian + NUMPY_TYPE_CODES[type_code])
            data = np.frombuffer(fd.read(count*dtype.itemsize), dtype)
            # Note: Use data.copy() to make a modifiable array.
            table[name] = data.reshape(dims)
        elif type_str == "old_string":
            str_len = read_len()
            data = decode(fd.read(str_len))
            table[name] = data
        elif type_str in ("string", "sq_string"):
            nrows = read_len()
            if nrows < 0:
                ndims = -nrows
                dims = np.frombuffer(fd.read(4*ndims), len_dtype)
                count = np.prod(dims[:-1])
                # Make str() rather than bytes() in python 3
                data = np.array([decode(fd.read(dims[-1])) for _ in range(count)])
                # If speed is an issue, can instead read in the entire array as
                # one large buffer, but these will be byte arrays in python 3.
                # If so, remove the decode on the 'else' condition as well.
                #dtype = np.dtype('|S'+str(dims[-1])
                #data = np.frombuffer(fd.read(count*dims[-1]), dtype)
                table[name] = data.reshape(dims[:-1])
            else:
                data = []
                for _ in range(nrows):
                    str_len = read_len()
                    data.append(decode(fd.read(str_len)))
                table[name] = np.array(data)
        else:
            raise NotImplementedError("unknown octave type "+type_str)
        #print("read %s:%s"%(name, type_str), table[name])
    return table

def _dump(filename):
    import gzip

    if filename.endswith('.gz'):
        with gzip.open(filename, 'rb') as fd:
            table = read_octave_binary(fd)
    else:
        with open(filename, 'rb') as fd:
            table = read_octave_binary(fd)
    #for k, v in sorted(table.items()):
    #    print(k, v)
    for k, v in table.items():
        print(k, v)

if __name__ == "__main__":
    _dump(sys.argv[1])
