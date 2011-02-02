# This program is public domain
"""
Alignment correction.

Sometimes the sample alignment is not perfect, and the sample may
be slightly rotated.  The net effect of this is that the Q values
stored in the data file are not correct.  The angle correction
allows you to adjust Q as if the data were taken at a slightly
different angle.

Note that this adjustment will fail to properly account for the change
in intensity due to the neutrons at the unexpected reflection angle
being filtered by the back slits, or due to the unexpected sample
footprint poorly estimating the beam spill.  Whether these effects are
significant depends on the details of the experiment geometry.

Usage
=====

    data.appy(AdjustAlignment(offset=0.01)
"""
from .correction import Correction

class AdjustAlignment(Correction):
    """
    Adjust Q if there is reason to believe either the detector
    or the sample is rotated.
    """
    properties = ["offset"]
    offset = 0. # degrees

    def __init__(self, offset=0.):
        """Define the angle offset correction for the data.
        angle: rotation in degrees away from the beam
        """
        self.offset = offset

    def apply(self, data):
        """Apply the angle correction to the data"""
        assert not data.ispolarized(), "need unpolarized data"

        data.sample.angle_x += self.offset
        data.detector.angle_x -= self.offset
        data.resetQ()

    def __str__(self):
        return "AdjustAlignment(offset=%g)"%offset
