# This code is in the public domain

from polcor import *
from normalize import *

def load_ng7(file):
    "NCNR NG-7 file loader"
    from .ncnr_ng7 import NG7Icp
    data = NG7Icp(file)
    data.load()
    data.resetQ()
    return data

def load_ng1(file):
    "NCNR NG-7 file loader"
    from .ncnr_ng1 import NG1Icp
    data = NG1Icp(file)
    data.load()
    data.resetQ()
    return data
