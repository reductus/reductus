# This code is in the public domain

from polcor import *

def load_ng7(file):
    "NCNR NG-7 file loader"
    from .ncnr_ng7 import NG7Icp
    return NG7Icp(file)

def load_ng1(file):
    "NCNR NG-7 file loader"
    from .ncnr_ng1 import NG1Icp
    return NG1Icp(file)

