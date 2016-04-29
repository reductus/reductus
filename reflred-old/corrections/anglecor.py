# This program is public domain
"""
Alignment correction.
"""
from ..pipeline import Correction

class AdjustAlignment(Correction):
    """
    Adjust angles for misaligned sample.

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
    """
    parameters = [
        ['offset', 0., 'degrees',
         'sample rotation relative to the nominal incident angle'],
    ]
    def apply(self, data):
        if self.offset != 0.0:
            data.sample.angle_x += self.offset
            data.detector.angle_x -= self.offset
            data.formula = data.formula+"[theta offset=%g]"%self.offset
