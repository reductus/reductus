# This program is public domain
"""
Rescale dataset.
"""
import numpy as np

from ..pipeline import Correction
from ..uncertainty import Uncertainty as U

class Rescale(Correction):
    """
    Adjust Q if there is reason to believe either the detector
    or the sample is rotated.
    """
    parameters = [
        ["scale", 1., "", "multiplication factor for data"],
        ["uncertainty", 0., "", "uncertainty in scale"],
    ]
    def apply(self, data):
        v, scale = U(data.v, data.dv**2), U(self.scale, self.uncertainty**2)
        z = v * scale
        data.v, data.dv = z.x, z.dx
