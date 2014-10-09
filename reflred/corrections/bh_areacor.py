from .areacor import AreaCorrection

def brookhaven_area_correction(self):
    """
    Returns the default area correction that can be applied to the data
    for the Brookhaven detector on NG1.
    """
    nx,ny = self.detector.dims
    Ax,Ay = self.detector.solid_angle
    wx = (1+0.15*cos(2*pi*np.arange(nx)/32.))/nx * Ax
    wy = (1+0.15*cos(2*pi*np.arange(ny)/32.))/ny * Ay
    return AreaCorrection(wx,wy,source="15% * cos(2 pi k/32)")
