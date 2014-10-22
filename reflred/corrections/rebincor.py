# This program is public domain
from numpy import inf

from ..pipeline import Correction

# Rebinning operations
class LinearBinning(Correction):
    """
    Desired time binning for the dataset.

    Note that the limit will automatically cut off at the time bin
    boundaries, so can be infinite.
    """
    parameters = [
        ['start', 0, 'us', 'first bin edge'],
        ['step', 0.1, 'us', 'time step per bin'],
        ['stop', inf, 'us', 'last bin edge'],
    ]

class LogBinning(Correction):
    """
    Desired time binning for the dataset.

    Note that the upper limit will automatically cut off at the maximum
    time bin boundary, so it can be infinite.
    """
    parameters = [
        ['start', 0, 'us', 'first bin edge'],
        ['step', 10, '%', 'time step per bin'],
        ['stop', inf, 'us', 'last bin edge'],
        ]
