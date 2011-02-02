# This program is public domain
"""
Data corrections for reflectometry.


"""

# TODO Autogenerate these entries from the corrections themselves.
# TODO This serves to improve maintainability by only listing the
# TODO objects in one place, and improve documentation by copying
# TODO the complete description of constructor arguments and function
# TODO description.

# TODO find a better way to delay loading of symbols

def normalize(*args, **kw):
    """Normalization correction; should be applied first"""
    from .normcor import Normalize
    return Normalize(*args, **kw)

def polarization_efficiency(*args, **kw):
    """Polarization efficiency correction"""
    from .polcor import PolarizationEfficiency
    return PolarizationEfficiency(*args, **kw)

def smooth(*args, **kw):
    """Data smoothing using 1-D moving window least squares filter"""
    from .smoothcor import Smooth
    return Smooth(*args, **kw)

def water_intensity(*args, **kw):
    """Intensity estimate from water scatter"""
    from .ratiocor import WaterIntensity
    return WaterIntensity(*args, **kw)

def ratio_intensity(*args, **kw):
    """Intensity estimate from reflection off a standard sample"""
    from .ratiocor import RatioIntensity
    return RatioIntensity(*args, **kw)

def measured_area_correction(*args, **kw):
    """Detector area correction from file"""
    from .areacor import measured_area_correction
    return measured_area_correction(*args,**kw)

def area_correction(*args, **kw):
    """Detector area correction from file"""
    from .areacor import AreaCorrection
    return AreaCorrection(*args,**kw)
