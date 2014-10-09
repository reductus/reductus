# This program is public domain

"""
Monitor normalization correction.
"""
import numpy as np

from .. import err1d
from ..pipeline import Correction

class Normalize(Correction):
    def __init__(self, base='auto'):
        """
        Define the kind of monitor normalization.
        base is 'time', 'counts', 'power', 'auto' or 'none'.
        """
        self.base = base

    def apply(self, data):
        base = data.monitor.base if self.base == 'auto' else self.base
        C = data.detector.counts
        varC = C # Poisson stats
        if base == 'counts':
            M = data.monitor.counts
            varM = M # Poisson stats
            units = 'counts per monitor count'
        elif base == 'time':
            M = data.monitor.count_time
            # Uniform distribution has variance of interval/12
            varM = data.monitor.time_step/12.
            units = 'counts per second'
        elif base == 'power':
            M = data.monitor.source_power
            varM = 0
            units = 'counts per '+data.monitor.source_power_units
        elif base == 'none':
            M = 1
            varM = 0
            units = 'counts'
        else:
            raise ValueError,\
                "Expected normalization of auto, counts, time, power or none"
        value,variance = err1d.div(C, varC, M, varM)
        data.v, data.dv = value, np.sqrt(variance)
        data.vunits = units
        data.vlabel = 'Intensity'
        data.normbase = base

    def __str__(self):
        return "Normalize('%s')"%self.base

def demo():
    import pylab
    from os.path import join as joinpath
    from ..examples import get_data_path
    from .. import formats
    from .. import corrections as cor
    path = get_data_path('ng1p')
    base = "jd916_2"
    file = joinpath(path, "%s%03d.nad"%(base,753))
    data = formats.load(file)[0]
    (data | cor.normalize()).plot()
    pylab.show()


if __name__ == "__main__":
    demo()