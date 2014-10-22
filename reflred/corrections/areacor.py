# -*- coding: utf-8 -*-
# This program is public domain
"""
Correct from counts per pixel to counts per unit area on the detector.

Usage
=====

Example::

    # construct the correction based on a detector measurement
    from reflred import load, measured_area_correction
    floodfill = load('detector measurement')
    areacor = measured_area_correction(floodfill)

    # apply the correction
    data = load(d).apply(areacor)

If you want to the pixels to have equal area then you need to include
a rebin=True flag::

    areacor = measured_area_correction(floodfill,rebin=True)

You can also set the areacor.rebin attribute directly.

If you know the pixel widths in x and y then you don't have to extract
them from a measurement, but can instead use::

    areacor = area_correction(wx,wy,source="provenance")

Certain instruments have predefined area corrections, which are
returned by the area_correction() method of the refldata object.

Limitations
===========

The correction applies independently in x and y using the sum of the pixels
across that detector dimension.  Small detector rotations and misaligned
wires will lead to artificial broadening.

The correction does not apply if there are other detector artifacts, such as
pixel efficiency variation.  Sliding the detector across a narrow slit and
summing the total counts across the detector will show any efficiency
variation.  We do not attempt to correct for this.

This theory also assumes the floodfill is uniform, which will depend on
how the measurement is performed.  For example, incoherent scattering
off water will yield higher intensities closer to the beam, and measurements
of a point source with a flat detector will yield higher counts where the
detector is nearer the point.  Data not taken in the ideal condition of
sliding the detector behind a narrow slit while maintaining uniform intensity
from the beam will need to scaled appropriately before estimating pixel widths.

Even after correcting for pixel widths in x and y, there may be a residual
signal on the detector.  This can be viewed by applying the detector
correction to the floodfill itself.  As a second order pixel area effect due
to variations in wire position across the rows and columns of the detector,
the pixels could be further scaled by this variation.  The scale factor
should be S = nx*ny * F/sum(F), where F is the corrected detector image.
This is not implemented here.

Theory
======

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
        => w_i = C_i/D = L * C_i / C
"""

import numpy as np

from refl1d.rebin import rebin2d, rebin

from ..refldata import Intent
from ..pipeline import Correction

class MeasuredAreaCorrection(Correction):
    """
    Given a detector measurement (either a flood fill or a main
    beam scan) return an area correction based on the pixel widths
    estimated from the data.

    The resulting correction will scale the pixels to counts per
    unit area, so must be applied all datasets for the absolute
    reflection amplitude to be calculated.

    If rebin is true, then instead of scaling pixels to counts
    per unit area, the pixel boundaries will be adjusted so that
    they have equal area using standard rebinning techniques.

    For main beam scans, the data will need to be normalized to
    the same number of incident neutrons on all frames, and all
    frames summed together.  Time of flight data will need to be
    combined into a single file, with the time channels collapsed
    to a single channel containing all the wavelengths of interest
    for each measurement, and the resulting frames normalized and
    summed.  In any case this preprocessing should happen once
    for each beam scan, resulting in a small file that can be applied
    to multiple datasets.
    """
    parameters = [
        ["rebin", False, "",
         "if rebin, then shift counts so pixels are uniform.  If not rebin, "
         "then normalize counts by the area of each pixel."],
    ]

    def apply_list(self, datasets):
        norm = [d for d in datasets if d.intent == Intent.deff]
        if len(norm) != 1:
            ValueError("Need one and only one detector efficiency measurement")
        # TODO: maybe precalculate norm
        wx, wy = find_pixel_area(norm)
        for d in datasets:
            if d is not norm:
                area_norm(d, self.wx, self.wy, self.rebin)

class AreaCorrection(Correction):
    """
    Convert detector counts from counts per pixel to counts per unit area.
    """
    parameters = [
        ["wx", [], "mm",
         "effective pixel width in the x direction"],
        ["wy", [], "mm",
         "effective pixel width in the y direction"],
        ["source", "unknown", "",
         "source of the pixel width data"],
        ["rebin", False, "",
         "if rebin, then shift counts so pixels are uniform.  If not rebin, "
         "then normalize counts by the area of each pixel."],
    ]

    def __init__(self, **kw):
        Correction.__init__(self, **kw)
        self.wx = np.asarray(self.wx)
        self.wy = np.asarray(self.wy)

    def apply(self, data):
        area_norm(data, self.wx, self.wy, self.rebin)

def find_pixel_area(data):
    """
    Estimate pixel width and height from a flood fill of the detector.
    """
    # Collapse the detector measurement to one frame
    Cxy = np.sum(data.detector.counts,axis=0)
    # Find total counts
    C = np.sum(Cxy)
    # Find proportional counts in x and y
    Cx = np.sum(Cxy,axis=0)
    Cy = np.sum(Cxy,axis=1)
    # Find new pixel width from proportional counts
    Lx,Ly = data.detector.size
    wx = Cx / C * Lx
    wy = Cy / C * Ly

    return wx, wy


def area_norm(data, wx, wy, rebin):
    """Apply the area correction to the data"""
    # TODO: apply correction to v,dv rather than detector
    # TODO: no error propagation
    # TODO: maybe note detector efficiency correction in formula
    nx,ny = wx.shape[0],wy.shape[0]
    assert data.detector.dims == (nx,ny), \
        "area correction size does not match detector size"
    if rebin:
        # Compute bin edges
        x = np.concatenate([(0.,),np.cumsum(wx)])
        y = np.concatenate([(0.,),np.cumsum(wy)])
        Lx,Ly = np.sum(wx),np.sum(wy)
        xo = np.linspace(0,Lx,nx+1)
        yo = np.linspace(0,Ly,ny+1)

        # Rebin in place
        if data.detector.counts.ndim == 3:
            Io = np.empty((nx,ny),'d') # Intermediate storage
            for i in xrange(data.detector.counts.shape[0]):
                frame = data.detector.counts[i]
                frame[:] = rebin2d(x,y,frame,xo,yo,Io)
        else:
            Io = np.empty((nx,),'d') # Intermediate storage
            for i in xrange(data.detector.counts.shape[0]):
                frame = data.detector.counts[i]
                frame[:] = rebin(x,frame,xo,Io)

        # Set the pixel widths to a fixed size
        # TODO: force a failure until we figure out what happens with
        # TODO: lazy loading on the detector.
        data.detector.widths_x = np.zeros(nx,'d')+Lx/nx
        data.detector.widths_y = np.zeros(ny,'d')+Ly/ny
    else:
        # Scale by area
        data.detector.widths_x = wx
        data.detector.widths_y = wy

        # Normalize pixels by area
        data.detector.counts /= wx
        data.detector.counts /= wy

