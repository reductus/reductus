# This code is in the public domain

# Define data file formats
from reflectometry.reduction.formats import *

# ========= Data corrections ========
def normalize(*args, **kw):
    """Normalization correction; should be applied first"""
    from reflectometry.reduction.normalize import Normalize
    return Normalize(*args, **kw)

def polcor(*args, **kw):
    """Normalization correction; should be applied first"""
    from reflectometry.reduction.polcor import PolarizationEfficiency
    return PolarizationEfficiency(*args, **kw)
