# This program is in the public domain
"""
Monitor normalization correction.
"""
import numpy as np

from .. import err1d
from ..pipeline import Correction

# TODO: Separate display normalization from internal values
# TODO: Add filter to convert time to monitor
# TODO: Need detector and monitor deadtime correction
class Normalize(Correction):
    """
    Define the kind of monitor normalization.

    For example, if base='monitor' and scale=1000, then the normalization
    will be counts per 1000 monitor counts.

    Note that operations that combine datasets require the same
    normalization on the points.  :class:`joincor.Join` in particular
    requires normalization by monitor, with scale of 1 to get the
    correct value.
    """

    parameters = [
        ['base', 'auto', 'time|monitor|power|auto|none',
         'normalization measurement to use for the intensity'],
        ['scale', 1, '',
         'scale factor for normalization'],
    ]
    def apply(self, data):
        v, dv, base, units = norm(data, self.base, self.scale)
        data.v, data.dv = v, dv
        data.vunits = units
        data.vlabel = 'Intensity'
        data.normbase = base

def norm(data, base='auto', scale=1):
    if base == 'auto':
        base = 'monitor'
    C = data.detector.counts
    varC = C # Poisson stats
    if base == 'monitor':
        M = data.monitor.counts
        varM = M # Poisson stats
        units = 'counts per %s monitor'%scale
    elif base == 'time':
        M = data.monitor.count_time
        # Uniform distribution has variance of interval/12
        varM = data.monitor.time_step/12.
        units = 'counts per %s second'%scale
    elif base == 'power':
        M = data.monitor.source_power
        varM = 0
        units = ('counts per %s '%scale)+data.monitor.source_power_units
    elif base == 'none':
        M = 1
        varM = 0
        units = 'counts'
        scale = 1
    else:
        raise ValueError,\
            "Expected normalization of auto, counts, time, power or none"
    value,variance = err1d.div(C, varC+(varC==0), M, varM+(varM==0))
    #print "normcor", data.filename
    #print "C",C,varC+(varC==0)
    #print "M",M,varM+(varM==0)
    #print "value",value
    #print "variance",variance
    return value*scale, np.sqrt(variance)*scale, base, units

def demo():
    import pylab
    from ..examples import ng1p as group
    from .. import corrections as cor
    data = group.spec()
    # Normalize by time instead of the default monitor counts
    (data | cor.normalize('time')).plot()
    #data.plot()
    pylab.show()


if __name__ == "__main__":
    demo()