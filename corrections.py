# This program is public domain
"""
Data corrections for reflectometry.
"""

# TODO Autogenerate these entries from the corrections themselves.
# TODO This serves to improve maintainability by only listing the
# TODO objects in one place, and improve documentation by copying
# TODO the complete description of constructor arguments and function
# TODO description.

# TODO Find a way to do lazy importing.  Corrections are
# TODO stored as class name in the log file, but they are not
# TODO available as top level names in reflred.  Instead we
# TODO provide a lookup function to import the class given
# TODO the correction.

def load_class(class_name):
    """
    Returns the named class from whatever submodule it happens to live in.

    This allows us to keep smaller files and shorter load times by delaying
    the loading of corrections until they are needed, though at some
    inconvenience to the developer.  For the most part developers will be
    able to use the equivalent factory method to return an item of the class,
    generally using the lower case class name with underscore separating the
    words.
    """
    map = dict(Normalize='normalize',
               PolarizationEfficiency='polcor',
               WaterIntensity='ratiocor',
               RaitioIntensity='ratiocor')
    module_name = map[class_name]
    module = __import__('reflectometry.reduction.'+module_name,
                        fromlist=[class_name])
    cls = getattr(module,class_name)
    return cls
    
def normalize(*args, **kw):
    """Normalization correction; should be applied first"""
    from reflectometry.reduction.normalize import Normalize
    return Normalize(*args, **kw)

def polarization_efficiency(*args, **kw):
    """Polarization efficiency correction"""
    from reflectometry.reduction.polcor import PolarizationEfficiency
    return PolarizationEfficiency(*args, **kw)

def water_intensity(*args, **kw):
    """Intensity estimate from water scatter"""
    from reflectometry.reduction.ratiocor import WaterIntensity
    return WaterIntensity(*args, **kw)

def ratio_intensity(*args, **kw):
    """Intensity estimate from reflection off a standard sample"""
    from reflectometry.reduction.ratiocor import RatioIntensity
    return RatioIntensity(*args, **kw)
