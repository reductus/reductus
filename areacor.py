# This program is public domain
"""
Correction from counts per pixel to counts per unit area on the detector.

== Usage ==

    from reflectometry.reduction import load, measured_area_correction
    floodfill = load('detector measurement')
    areacor = measured_area_correction(floodfill)
    
    data = load(d).apply(areacor)

If you know the pixel widths in x and y then you don't have to extract
them from a measurement, but can instead use:

    areacor = area_correction(wx,wy,source="provenance")

This is used in some file formats which supply an area_correction()
method to return the default area correction. 


== Theory ==

Assuming the pixels have none uniform area, we can estimate the area
of each pixel by looking at the counts across the detector in a floodfill
environment.

First lets define the detector.  We will do so in one dimension, but
it is a separable problem which can be applied independently in the
x and y directions.

Detector has varying width pixels:

    |......|....|.....|....|
     w_1   w_2        w_n

    L = sum(w) = length of the detector
    C_i = measured counts in cell i
    D = sum(C)/L = average flux on the detector

Given a uniform flux on the detector, what is the probability of seeing
the particular measured set of counts P(C|w).  We will assume a Poisson
distribution for the counts in the individual pixels.

    D = flux in counts/unit area
    lambda_i = D w_i = expected counts in cell i
    P_i(C_i|D w_i) = exp(-D w_i) (D w_i)**C_i / C_i!
    P(C|w) = prod P_i(C_i|D w_i)

Minimize the log probability by setting the derivative to zero:

    log P = sum log P_i
    log P_i = -D w_i + C_i log D w_i - log C_i!
    
    d/dw_i log P = d/dw_i log P_i
                 = d/dw_i (-D w_i) + C_i d/dw_i log D w_i
                 = -D + C_i D / (D w_i)
    d/dw_i log P = 0 
        => D = C_i/w_i 
        => w_i = C_i/D = C_i L/C
"""
from reflectometry.reduction import refldata

def measured_area_correction(data):
    """
    Given a detector measurement (either a flood fill or a main
    beam scan) return an area correction which can convert counts
    per pixel to counts per unit area on a dataset.
    """
    # Collapse the detector measurement to one frame
    Cxy = sum(data.detector.counts,axis=0)
    # Find total counts
    C = sum(Cxy)
    # Find propotional counts in x and y
    Cx = sum(Cxy,axis=0)
    Cy = sum(Cxy,axis=1)
    # Find pixel width from proportional counts
    Lx = data.detector.width_x
    Ly = data.detector.width_y
    wx = Cx * Lx/C
    wy = Cy * Ly/C
    
    return AreaCorrection(wx,wy,source=data.name)

class AreaCorrection(object):
    """
    Convert detector counts from counts per pixel to counts per unit area.
    """
    properties = ["floodfill"]
    angle = 0. # degrees

    def __init__(self, wx, wy, source="unknown"):
        """
        Specify the datafile to Define the angle offset correction for the data.
        angle: rotation in degrees away from the beam
        """
        self.wx = array(wx)
        self.wy = array(wy).T

    def __call__(self, data):
        """Apply the angle correction to the data"""
        dims = [wx.shape[0],wy.shape[1]]
        assert data.detector.dims == dims, \
            "area correction needs correct detector size"
        data.detector.width_x = wx[0,:]
        data.detector.width_y = wy[:,0]
        data.detector.counts /= self.wx
        data.detector.counts /= self.wy
        return data

    def __str__(self):
        return "AreaCorrection('%s')"%source
