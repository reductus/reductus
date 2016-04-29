"""
Some machines allow the sample to be rotated by 180
degrees, reversing the usual sense of the angles.

We provide two corrections, one which reverses the usual sense of the
angles, and the other which assumes that all reflection is from the
top of the film and there is no back reflectivity.

ReverseCorrection
FrontCorrection
"""

import numpy as np

from ..pipeline import Correction

class ReverseCorrection(Correction):
    """
    Reverse the sense of the reflection angles, making positive angles
    negative and vice versa
    """
    def apply(self,data):
        data.sample.angle_x = -data.sample.angle_x
        data.detector.angle_x = -data.detector.angle_x
        data.formula = data.formula + "[rev]"

class FrontCorrection(Correction):
    """
    Assume all reflection is off the top surface, reversing the sense
    of negative angles.
    """
    def apply(self,data):
        idx = data.sample.angle_x < 0
        if np.any(idx):
            data.sample.angle_x[idx] *= -1.0
            data.detector.angle_x[idx] *= -1.0
            data.formula = data.formula + "[front]"
