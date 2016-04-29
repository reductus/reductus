"""
Sample data from NCNR-NG7.

This data from July, 2004, measures water with various concentrations
for D2O on quartz.  The particular data sets contain 20% D2O.

TODO: Confirm this is correct by looking in log books!
"""

import numpy, os
from . import get_data_path
from .. import formats

PATH=get_data_path('ng7')

def load(seqlist,base='jul04'):
    return [formats.load(os.path.join(PATH,"%s%03d.ng7"%(base,seq)))
            for seq in seqlist]

def slits():
    return load([36])

def back():
    return load([31,32])

def spec():
    return load([37])

def rock():
    return load([33,34,35])
