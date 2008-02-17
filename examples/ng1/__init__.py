"""
Sample data from NCNR-NG1.

This is data from March, 2002.

Note that this data has a few problems with it such as internal name not
matching external name, wavelength being incorrect and slits scans being
saturated.

TODO: Ask Ursula Perez-Salas what this data contains.
"""

import numpy, os
import reflectometry.reduction as reflred

PATH = os.path.dirname(os.path.realpath(__file__))

def load(seqlist,base='psih1'):
    return [reflred.load(os.path.join(PATH,"%s%03d.ng1"%(base,seq)))
            for seq in seqlist]

def slits():
    return load([6,7,8,9,10,11],base='ibeam')

def back():
    return load([9,10,11,12,13,15,16,17,18,19])

def spec():
    return load([2,3,4,6,7])

def rock():
    return load([1,5,8])


if __name__ == "__main__":
    print spec()[0]
