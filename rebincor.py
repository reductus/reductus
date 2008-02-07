
# Rebinning operations
class LinearBinning(object):
    """
    Desired time binning for the dataset.
    
    start (1 Angstrom)
    stop (inf Angstrom)
    step (0.1 Angstrom)
    """
    start = 1.
    stop = inf
    step = None
    def __init__(self, **kw): _set(self,kw)

class LogBinning(object):
    """
    Desired time binning for the dataset.

    start (1 Angstrom)
    stop (inf Angstrom)
    step (1 %)
    """
    start = 1.
    stop = inf
    step = 1.
    def __init__(self, **kw): _set(self,kw)
