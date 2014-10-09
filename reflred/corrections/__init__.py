# This program is public domain
"""
Data corrections for reflectometry.


"""

def intent(*args, **kw):
    """Mark the intent of the measurement"""
    from .intentcor import Intent
    return Intent(*args, **kw)

def divergence(*args, **kw):
    """Compute angular divergence"""
    from .divergencecor import AngularResolution
    return AngularResolution(*args, **kw)

def normalize(*args, **kw):
    """Normalization correction; should be applied first"""
    from .normcor import Normalize
    return Normalize(*args, **kw)

def polarization_efficiency(*args, **kw):
    """Polarization efficiency correction"""
    from .polcor import PolarizationEfficiency
    return PolarizationEfficiency(*args, **kw)

def align_slits(*args, **kw):
    """Data smoothing using 1-D moving window least squares filter"""
    from .alignslits import AlignSlits
    return AlignSlits(*args, **kw)

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

def brookhaven_area_correction(*args, **kw):
    from .bh_areacor import brookhaven_area_correction
    return brookhaven_area_correction(*args, **kw)
