import zipfile
import json
import numpy

_formats = {
        'S': '%s',
        'f': '%.8g',
        'i': '%d',
        'u': '%d',
        'b': '%d'}

def hzf_to_dict(filename):
    output = {}
    root = zipfile.ZipFile(filename)
    fns = root.namelist()
    for fn in fns:
        path = fn.split("/")
        if fn.endswith("/"):
            # directory
            output[fn] = None
        elif path[-1].endswith(".attrs") or path[-1].endswith(".link"):
            # attributes or link file: write unmodified
            output[fn] = json.loads(root.open(fn, 'r').read())
        else:
            if (fn + ".link") in fns:
                output[fn] = None
            elif (fn + ".attrs") in fns:
                # data file, have to rely on attrs:
                attrs = json.loads(root.open(fn + ".attrs", "r").read())
                with root.open(fn, 'r') as infile:
                    dtype = str(attrs['format'])
                    # CRUFT: <l4, <d8 are not sensible dtypes
                    if dtype == '<l4': dtype = '<i4'
                    if dtype == '<d8': dtype = '<f8'
                    dtype=numpy.dtype(dtype)
                    if attrs.get('binary', False) == True:
                        d = numpy.fromfile(infile, dtype=dtype)
                    else:
                        if root.getinfo(fn).file_size == 1:
                            # empty entry: only contains \n
                            # this is only possible with empty string being written.
                            d = numpy.array([''], dtype=dtype)
                        else:
                            d = numpy.loadtxt(infile, dtype=dtype, delimiter='\t')
                            if dtype.kind == 'S':
                                d = numpy.char.replace(d, r'\t', '\t')
                                d = numpy.char.replace(d, r'\r', '\r')
                                d = numpy.char.replace(d, r'\n', '\n')
                output[fn] = d.tolist()
    return output
            
            
