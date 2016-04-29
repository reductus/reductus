# This program is in the public domain
"""
Detector saturation correction.
"""
from __future__ import division

import numpy as np

from ..pipeline import Correction
from ..err1d import interp, div

# TODO: deadtime correction must feed into normalization!!
class DetectorSaturation(Correction):
    """
    Sets data to detector counts with saturation correction.

    Use this before plot to show the corrected data values.
    """
    def apply(self, data):
        v, dv = saturation_correction(data.detector.counts,
                                      data.monitor.count_time,
                                      data.detector.saturation)
        data.v, data.dv = v, dv
        data.vunits = 'counts'
        data.vlabel = 'Intensity'
        data.normbase = 'none'


class MonitorSaturation(Correction):
    """
    Sets data to monitor with saturation correction.

    Use this before plot to show the corrected monitor values.
    """
    def apply(self, data):
        v, dv = saturation_correction(data.monitor.counts,
                                      data.monitor.count_time,
                                      data.monitor.saturation)
        data.v, data.dv = v, dv
        data.vunits = 'counts'
        data.vlabel = 'Monitor Intensity'
        data.normbase = 'none'


def saturation_correction(counts, time, saturation):
    rate = counts / time
    if saturation.shape[0] == 3:
        E, varE = interp(rate, saturation[0], saturation[1], saturation[2]**2)
        C, varC = div(counts, counts, E, varE)
    else:
        E = np.interp(rate, saturation[0], saturation[1])
        C, varC = counts/E, counts/E**2
    return C, np.sqrt(varC)
