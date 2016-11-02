import numpy as np

from .. import err1d


def apply_rescale(data, scale, dscale):
    I, varI = err1d.mul(data.v, data.dv**2, scale, dscale**2)
    data.v, data.dv = I, np.sqrt(varI)


def apply_intensity_norm(data, base):
    S, varS = err1d.interp(data.angular_resolution,
                           base.angular_resolution, base.v, base.dv**2)
    I, varI = err1d.div(data.v, data.dv**2, S, varS)
    data.v, data.dv = I, np.sqrt(varI)

def estimate_attenuation(datasets):
    raise NotImplementedError()
    index = np.sort([d.angular_resolution[0] for d in datasets])



NORMALIZE_OPTIONS = 'auto|monitor|time|power|none'
NORMALIZE_DEFAULT = 'monitor'
def apply_norm(data, base='auto'):
    if base == 'auto':
        base = NORMALIZE_DEFAULT

    C = data.detector.counts
    varC = data.detector.counts_variance
    if base == 'monitor':
        M = data.monitor.counts
        varM = data.monitor.counts_variance
        varM += (varM == 0)  # variance on zero counts is +/- 1
        units = 'monitor'
    elif base == 'time':
        M = data.monitor.count_time
        # Uniform distribution has variance of interval/12
        varM = data.monitor.time_step/12.
        units = 'second'
    elif base == 'power':
        M = data.monitor.source_power
        varM = 0
        units = data.monitor.source_power_units
    elif base == 'none':
        M = 1
        varM = 0
        units = ''
    else:
        raise ValueError("Expected %r in %s" % (base, NORMALIZE_OPTIONS))
    #print "norm",C,varC,M,varM
    value, variance = err1d.div(C, varC+(varC==0), M, varM)
    data.v = value
    data.dv = np.sqrt(variance)
    data.vunits = 'counts per '+units if units else 'counts'
    data.vlabel = 'Intensity'
    data.normbase = base

    # TODO: set data scale to a nice number
    #data.scale = nice_number(M[0])

