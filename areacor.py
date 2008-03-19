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
from reflectometry.reduction import refldata,rebin2d

def measured_area_correction(data, rebin=False):
    """
    Given a detector measurement (either a flood fill or a main
    beam scan) return an area correction which can convert counts
    per pixel to counts per unit area on a dataset.
    
    If rebin is true, then rebin so all pixels have the same area.
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
    
    return AreaCorrection(wx,wy,rebin=rebin,source=data.name)

class AreaCorrection(object):
    """
    Convert detector counts from counts per pixel to counts per unit area.
    """
    properties = ["wx","wy","source","rebin"]

    def __init__(self, wx, wy, rebin=False, source="unknown"):
        """
        Create a pixel area correction function.
        
        wx,wy is the actual width of the pixels as measured on
        the detector.  This function will normalize the counts
        on the detector by pixel area.  This will change the
        pixel widths in the data file.
        
        if rebin is True then adjust pixel boundaries so the
        pixels have equal area.
        
        source is a string to report in the log as the origin
        of the correction data.
        """
        self.wx = array(wx)
        self.wy = array(wy).T
        self.source = source
        self.rebin = rebin

    def __call__(self, data):
        """Apply the area correction to the data"""
        nx,ny = self.wx.shape[0],self.wy.shape[1]
        assert data.detector.dims == [nx,ny], \
            "area correction size does not match detector size"
        if self.rebin:
            # Compute bin edges
            x = numpy.concatenate([(0.),numpy.cumsum(wx)])
            y = numpy.concatenate([(0.),numpy.cumsum(wy)])
            Lx,Ly = numpy.sum(wx),numpy.sum(wy)
            xo = numpy.linspace(0,Lx,nx+1)
            yo = numpy.linspace(0,Ly,ny+1)
            Io = numpy.empty((nx,ny),'d') # Intermediate storage

            # Rebin in place
            for i in xrange(data.detector.counts.shape[0]):
                frame = data.detector.counts[i]
                frame[:] = rebin2d(x,y,frame,xo,yo,Io)

            # Set the pixel widths to a fixed size
            data.detector.width_x = numpy.zeros(nx,'d')+Lx/nx
            data.detector.width_y = numpy.zeros(ny,'d')+Ly/ny
        else:
            # Scale by area
            data.detector.width_x = wx[0,:]
            data.detector.width_y = wy[:,0]
            
            # Normalize pixels by area
            data.detector.counts /= self.wx
            data.detector.counts /= self.wy
        return data

    def __str__(self):
        return "AreaCorrection('%s')"%source
