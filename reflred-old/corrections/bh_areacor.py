import numpy as np
from numpy import cos, pi

from ..pipeline import Correction
from .areacor import area_norm

class BrookhavenAreaCorrection(Correction):
    """
    Normalize detector counts by pixel area for the Brookhaven detector on NG1.
    """
    parameters = [
        ["rebin", False, "",
         "if rebin, then shift counts so pixels are uniform.  If not rebin, "
         "then normalize counts by the area of each pixel."],
    ]

    def apply(self, data):
        wx, wy = brookhaven_pixel_area(data)
        area_norm(data, wx, wy, self.rebin)

def brookhaven_pixel_area(data):
    """
    Returns the default area correction that can be applied to the data
    for the Brookhaven detector on NG1.
    """
    nx,ny = data.detector.dims
    ax,ay = data.detector.solid_angle
    wx = (1+0.15*cos(2*pi*np.arange(nx)/32.))/nx * ax
    wy = (1+0.15*cos(2*pi*np.arange(ny)/32.))/ny * ay

