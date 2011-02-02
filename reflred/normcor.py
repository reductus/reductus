# This program is public domain

"""
Monitor normalization correction.
"""

from numpy import sqrt
from .correction import Correction
from . import err1d

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
        data.R,data.varR = err1d.div(C,varC,M,varM)
        data.vunits = units
        data.vlabel = 'Intensity'

    def __str__(self):
        return "Normalize('%s')"%self.base
