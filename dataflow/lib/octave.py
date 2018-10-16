import sys
from struct import unpack
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

STRUCT_TYPE_CODES = {
    0: "B",
    1: "H",
    2: "I",
    3: "b",
    4: "h",
    5: "i",
    6: "f",
    7: "d",
    8: "L",
    9: "l",
}

def read_octave_binary(fd):
    magic = fd.read(10)
    assert(magic == b"Octave-1-L")
    endian = ">" if fd.read(1) == 0 else "<"
    len_fmt = endian + "i"
    def read_len():
        len_bytes = fd.read(4)
        if not len_bytes:
            return 0
        return unpack(len_fmt, len_bytes)[0]
    table = OrderedDict()
    while True:
        name_length = read_len()
        if name_length <= 0:
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
        print("reading", name, type_str)
        if type_str == "scalar":
            type_code = ord(fd.read(1))
            dtype = endian + STRUCT_TYPE_CODES[type_code]
            table[name] = unpack(dtype, fd.read(8))
        elif type_str == "matrix":
            ndims = read_len()
            if ndims < 0:
                ndims = -ndims
                dims = unpack(endian + "%di"%ndims, fd.read(4*ndims))
            else:
                dims = (ndims, read_len())
            count = np.prod(dims)
            type_code = ord(fd.read(1))
            ## Don't know why np.fromfile isn't working.  Shouldn't have
            ## to read the data into a string, unpack it into a tuple then
            ## convert that to an array.  Should be able to directly read
            ## into the array.  For now, the other works.
            #dtype = endian + NUMPY_TYPE_CODES[type_code]
            #data = np.fromfile(fd, dtype=dtype, count=count)
            dtype = endian + str(count) + STRUCT_TYPE_CODES[type_code]
            type_size = np.dtype(NUMPY_TYPE_CODES[type_code]).itemsize
            data = np.array(unpack(dtype, fd.read(count*type_size)))
            table[name] = data.reshape(dims)
        elif type_str == "old_string":
            str_len = read_len()
            data = decode(fd.read(str_len))
            table[name] = data
        elif type_str in ("string", "sq_string"):
            nrows = read_len()
            if nrows < 0:
                ndims = -nrows
                dims = unpack(endian + "%di"%ndims, fd.read(4*ndims))
                count = np.prod(dims[:-1])
                dtype = "S%d"%dims[-1]
                data = np.fromfile(fd, dtype=dtype, count=count)
                table[name] = data.reshape(dims[:-1])
            else:
                data = []
                for _ in range(nrows):
                    str_len = read_len()
                    data.append(fd.read(str_len))
                table[name] = np.array(data)
        else:
            raise NotImplementedError("unknown octave type "+type_str)
        print("read %s:%s"%(name, type_str), table[name])
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