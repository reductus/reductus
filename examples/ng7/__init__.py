"""
Sample data from NCNR-NG7.

This data from July, 2004, measures water with various concentrations
for D2O on quartz.  The particular data sets contain 20% D2O.

TODO: Confirm this is correct by looking in log books!
"""

import numpy, os
import reflectometry.reduction as reflred

PATH = os.path.dirname(os.path.realpath(__file__))

def load(seqlist,base='jul04'):
    return [reflred.load(os.path.join(PATH,"%s%03d.ng7"%(base,seq)))
            for seq in seqlist]

def slits():
    return load([36])

def back():
    return load([31,32])

def spec():
    return load([37])

def rock():
    return load([33,34,35])


if __name__ == "__main__":
    print spec()[0]
