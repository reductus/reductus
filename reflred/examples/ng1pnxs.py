"""
Sample data from NCNR-NG1 polarized.

This is data from March, 2002.

Note that this data has a few problems with it such as internal name not
matching external name, wavelength being incorrect and slits scans being
saturated.
"""

from os.path import join as joinpath
from glob import glob

from .. import formats
from . import get_data_path

PATH=get_data_path('ng1p')

def _load(*patterns):
    return [entry
            for pattern in patterns
            for filename in glob(joinpath(PATH, pattern))
            for entry in formats.load(filename)]

def slit():
    return _load('slit11[2345].nxs.ngd')

def back():
    return _load('jd9014[9].nxs.ngd', 'jd9015[01].nxs.ngd')

def spec():
    return _load('jd9014[678].nxs.ngd')

def rock():
    return _load('jd9014[5].nxs.ngd')
