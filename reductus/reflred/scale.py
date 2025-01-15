import numpy as np
import functools

from reductus.dataflow.lib import err1d
from .util import extend


def apply_rescale(data, scale, dscale):
    I, varI = err1d.mul(data.v, data.dv**2, scale, dscale**2)
    data.v, data.dv = I, np.sqrt(varI)

# from https://stackoverflow.com/questions/31174295/getattr-and-setattr-on-nested-subobjects-chained-properties/54547158#54547158
def rgetattr(obj, path, *default):
    try:
        return functools.reduce(getattr, path.split('.'), obj)
    except AttributeError:
        if default:
            return default[0]
        raise

def apply_intensity_norm(data, base, align_by=None):
    assert data.normbase == base.normbase, "can't mix time and monitor normalized data"

    if align_by is None:
        # use the one suggested by the data structure, or error out if missing.
        align_by = getattr(data, 'align_intensity')
    # use "slit1.x" for 'align_by' with Candor data
    data_x, base_x = rgetattr(data, align_by), rgetattr(base, align_by)
    
    S, varS = err1d.interp(data_x, base_x, base.v, base.dv**2)
    # Candor may have only one detector bank active, and so the other may
    # have zeros in it.  Ignore those channels.
    I, varI = err1d.div(data.v, data.dv**2, S + (S==0), varS)
    data.v, data.dv = I, np.sqrt(varI)

def calculate_number(data, base, time_uncertainty=1e-6):
    """ returns the measured base flux * count time for each point """
    assert base.normbase == 'time', "can't calculate time-integrated flux from monitor-normalized base"
    if data.angular_resolution.ndim == 1:
        data_x, base_x = data.angular_resolution, base.angular_resolution
    else:
        data_x, base_x = data.slit1.x, base.slit1.x
    S, varS = err1d.interp(data_x, base_x, base.v, base.dv**2)
    F, varF = err1d.mul(data.monitor.count_time, time_uncertainty**2, S, varS)
    return F, varF


def estimate_attenuation(datasets):
    raise NotImplementedError()
    index = np.sort([d.angular_resolution[0] for d in datasets])


NORMALIZE_OPTIONS = 'auto|monitor|time|roi|power|none'
def apply_norm(data, base='auto'):
    if base == 'auto':
        # We are ignoring counter.countAgainst since monitor is almost
        # always the best choice for normalization.  Even when counting
        # against time monitor normalization protects against flucuations
        # in beam intensity.  Only reason not to use it is when the monitor
        # is bad or missing.
        if data.monitor.counts is not None and (data.monitor.counts > 0).any():
            base = 'monitor'
        elif data.monitor.count_time is not None and (data.monitor.count_time > 0).any():
            base = 'time'
        else:
            base = 'none'

    C = data.detector.counts
    varC = data.detector.counts_variance
    if base == 'monitor':
        #assert (data.monitor.counts > 0).all(), "monitor counts are zero; can't normalize by monitor"
        M = data.monitor.counts
        M[M == 0] = 1  # protect against zero counts in monitor
        varM = data.monitor.counts_variance
        varM[varM == 0] = 1  # variance on zero counts is +/- 1
        units = 'monitor'
    elif base == 'time':
        #assert (data.monitor.count_time > 0).all(), "count time is zero; can't normalize by time"
        M = data.monitor.count_time
        M[M == 0] = data.monitor.time_step/2.  # protect against zero count time
        # Uniform distribution has variance of (interval_width**2)/12
        varM = (data.monitor.time_step**2)/12.
        units = 'second'
    elif base == 'roi':
        M = data.monitor.roi_counts
        M[M == 0] = 1  # protect against zero counts in monitor
        varM = data.monitor.roi_variance
        varM[varM == 0] = 1  # variance on zero counts is +/- 1
        units = 'roi count'
    elif base == 'power':
        if data.monitor.source_power is None:
            raise ValueError("source power is unknown; can't normalize by power")
        # Power is in megawatts, not megawatt-hours, so scale by time.
        time = data.monitor.count_time/3600.
        M = data.monitor.source_power * time
        varM = data.monitor.source_power_variance * time
        units = data.monitor.source_power_units + "-hour"
    elif base == 'none':
        M = 1
        varM = 0
        units = ''
    else:
        raise ValueError("Expected %r in %s" % (base, NORMALIZE_OPTIONS))
    # Broadcast for nD detector arrays
    if C.ndim > 1:
        M, varM = extend(M, C), extend(varM, C)
    #print "norm",C,varC,M,varM
    value, variance = err1d.div(C, varC+(varC == 0), M, varM)
    data.v = value
    data.dv = np.sqrt(variance)
    data.vunits = 'counts per '+units if units else 'counts'
    data.vlabel = 'Intensity'
    data.normbase = base

    # TODO: set data scale to a nice number
    #data.scale = nice_number(M[0])

