# This program is public domain
"""
Angle correction.

Sometimes the sample alignment is not perfect, and the sample may
be slightly rotated.  The net effect of this is that the Q values
stored in the data file are not correct.  The angle correction
allows you to adjust Q as if the data were taken at a slightly
different angle.

Note that this adjust will fail to properly account for the change
in intensity due to the neutrons at the unexpected reflection angle
being filtered by the back slits or missing the sample.  Whether this
is significant depends on the details of the sample geometry.

Usage:

    data.appy(AngleCorrection(angle=0.01)
"""
from reflectometry.reduction import refldata

class AdjustAlignment(object):
    """
    Adjust Q if there is reason to believe either the detector
    or the sample is rotated.
    """
    properties = ["angle"]
    angle = 0. # degrees

    def __init__(self, angle=0.):
        """Define the angle offset correction for the data.
        angle: rotation in degrees away from the beam
        """
        self.angle = angle

    def __call__(self, data):
        """Apply the angle correction to the data"""
        assert not data.ispolarized(), "need unpolarized data"

        data.sample.angle_x += angle
        data.detector.angle_x -= angle
        data.resetQ()
        data.log(str(self))
        return data

    def __str__(self):
        return "AdjustAlignment(angle=%g)"%angle
