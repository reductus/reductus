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

class AngleCorrection(object):
    """
    Angle Correction object.  Must implement the correction interface.
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
        
        Qz = adjust_angle(data,angle=self.angle)
        data.Q = Qz
        return data

def adjust_angle(data,angle=0.):
    """
    Adjust Q if there is reason to believe either the detector
    or the sample is rotated.
    """
    theta_in = data.theta_in + angle
    theta_out = data.theta_out - angle
    Qz = 2*pi/data.wavelenth*(sin(theta_out*pi/180) - sin(theta_in*pi/180))
    return Qz
