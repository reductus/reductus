#!/usr/bin/env python
"""
Dump a nice data stream to the terminal.
"""
from __future__ import print_function, division

import sys
import json
#from pprint import pprint
if sys.version_info.major > 2:
    import bz2
else:
    import bz2file as bz2

def pretty(data, indent=0):
    """
    Pretty print for json structure, one item per line.
    """
    if indent == 0:
        print("{")
        pretty(data, indent=4)
        print("}")
        return
    for k, v in sorted(data.items()):
        if isinstance(v, dict):
            print(" "*indent + '%r: {'%k)
            pretty(v, indent=indent+4)
            print(" "*indent + "},")
        else:
            print(" "*indent + '%r: %r,'%(k, v))

def show_stream(filename):
    """
    Dump a nice data stream to the file using pretty print
    """
    with bz2.BZ2File(filename) as file_handle:
        for line in file_handle:
            if sys.version_info.major > 2:
                line = line.decode('utf-8')
            data = json.loads(line)
            #pprint(data, width=8000)
            pretty(data)

def main():
    """
    Process all sys arguments as stream files
    """
    for filename in sys.argv[1:]:
        print("====== %s ======" % filename)
        show_stream(filename)

if __name__ == "__main__":
    main()
