# This program is public domain
"""
Data corrections for reflectometry.
"""

def apply_standard_corrections(data):
    """
    Standard corrections that all data loaders should apply to put the data
    into plottable form.

    These are:

    #. :class:`divergencecor.AngularDivergence`
    #. :class:`intentcor.Intent`
    #. :class:`normcor.Normalize`

    Each data loader should call *apply_standard_corrections* near the end
    of its load method. The reduction steps are not logged and users may
    override them in their own reduction chain.

    If the format does not define slit parameters, but can otherwise set
    the angular divergence (e.g., a tabletop x-ray machine which records
    the divergence in its datafile), then set the slit parameters with
    arbitrary values (such as 1 mm for slit openings, and -2000 and -1000
    mm for slit distances), call *apply_standard_corrections*, then set
    self.angular_divergence to whatever is indicated in the data file.

    If the format defines the intent, then set data.intent before calling
    *apply_standard_corrections*.  The *Intent* correction uses 'auto', so
    it will preserve the intent in the file, or infer it if it is not present.

    Normalize just sets data.v,data.dv to counts/monitor.  This is easy for
    the user to override if they want a different kind of normalization.
    """
    divergence().apply(data)
    intent(intent='auto').apply(data) # use stored intent if present
    normalize().apply(data)

def intent(**kw):
    """Mark the intent of the measurement"""
    from .intentcor import InferIntent
    return InferIntent(**kw)

def divergence(**kw):
    """Compute angular divergence"""
    from .divergencecor import AngularResolution
    return AngularResolution(**kw)

def normalize(**kw):
    """Normalization correction; should be applied first"""
    from .normcor import Normalize
    return Normalize(**kw)

def join(**kw):
    """Join related files together into a single file"""
    from .joincor import Join
    return Join(**kw)

def background(**kw):
    """Background subtraction"""
    from .backcor import Background
    return Background(**kw)

def polarization(**kw):
    """Polarization efficiency correction"""
    from .polcor import PolarizationCorrection
    return PolarizationCorrection(**kw)

def smooth_slits(**kw):
    """Data smoothing using 1-D moving window least squares filter"""
    from .smoothslits import SmoothSlits
    return SmoothSlits(**kw)

def water_intensity(**kw):
    """Intensity estimate from water scatter"""
    from .ratiocor import WaterIntensity
    return WaterIntensity(**kw)

def ratio_intensity(**kw):
    """Intensity estimate from reflection off a standard sample"""
    from .ratiocor import RatioIntensity
    return RatioIntensity(**kw)

def measured_area_correction(**kw):
    """Detector area correction from file"""
    from .areacor import MeasuredAreaCorrection
    return MeasuredAreaCorrection(**kw)

def area_correction(**kw):
    """Detector area correction from file"""
    from .areacor import AreaCorrection
    return AreaCorrection(**kw)

def brookhaven_area_correction(**kw):
    """Correct for the standard brookhaven detector pixel width"""
    from .bh_areacor import BrookhavenAreaCorrection
    return BrookhavenAreaCorrection(**kw)

def rescale(**kw):
    """Scale the dataset"""
    from .rescalecor import Rescale
    return Rescale(**kw)
