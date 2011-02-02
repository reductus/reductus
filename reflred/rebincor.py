# This program is public domain
from numpy import inf

# Rebinning operations
class LinearBinning(object):
    """
    Desired time binning for the dataset.

    start (0 Angstrom)
    stop (inf Angstrom)
    step (0.1 Angstrom)

    Note that the limit will automatically cut off at the time bin
    boundaries, so can be infinite.
    """
    start = 0
    stop = inf
    step = 0.1
    def __init__(self, start=0.,stop=inf,step=0.1):
        self.start,self.step,self.stop = start,step,stop

    def __str__(self):
        return "LinearBinning(start=%g,stop=%g,step=%g)"\
            %(self.start,self.stop,self.step)

class LogBinning(object):
    """
    Desired time binning for the dataset.

    start (1 Angstrom)
    stop (inf Angstrom)
    step (1 %)

    Note that the upper limit will automatically cut off at the maximum
    time bin boundary, so it can be infinite.
    """
    start = 1
    stop = 10
    step = 1
    def __init__(self, start=1.,stop=inf,step=1):
        self.start,self.step,self.stop = start,step,stop

    def __str__(self):
        return "LogBinning(start=%g,stop=%g,step=%g)"\
            %(self.start,self.stop,self.step)
