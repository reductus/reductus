"""
Data smoothing

Uses moving window 1-D polynomial least squares smoothing filter.

Usage
=====

Create and apply the filter::

    from reflred.corrections import smooth
    ...
    data | smooth(degree=2,span=12)

"""
from __future__ import division

__all__ = ['SmoothSlits']

from copy import copy

import numpy as np

from ..refldata import Intent
from ..pipeline import Correction
from ..wsolve import wpolyfit

from .divergencecor import AngularResolution


class SmoothSlits(Correction):
    """
    Align slits with a moving window 1-D polynomial least squares filter.

    Updates *slit1.x*, *slit2.x* and *angular_resolution* attributes of the
    slit measurements so they all use a common set of points.

    Odd sized *span* is preferred.  *span* must be larger than *degree*.
    *degree=1* and *span=2* is equivalent to linear interpolation.
    """
    parameters = [
        ['degree', 1, '', 'polynomial degree'],
        ['span', 7, '', 'number of consecutive points in the fit'],
        ['dx', 0.01, 'mm', 'size within which slits are considered equivalent'],
        ]

    def apply_list(self, datasets):
        """Apply the correction to the data"""
        # TODO: how to check parameter consistency
        # Maybe on __init__, but does not allow UI to update property directly
        # Maybe on assignment, but doesn't allow update to one parameter without
        # the other.
        # Maybe provide check method which returns a list of invalid parameters
        # and the reason, or nothing if all parameter values are valid.
        assert self.span>self.degree, "Span must be greater than degree"
        slits = [d for d in datasets if Intent.isslit(d.intent)]
        # update the slit datasets in place
        smooth_slits(slits, dx=self.dx, degree=self.degree, span=self.span)
        return datasets

def smooth_slits(slits, dx, degree, span):
    divergence = AngularResolution()
    s = np.hstack([[d.angular_resolution,d.slit1.x,d.slit2.x] for d in slits])
    s = find_common(s.T, dx=dx).T
    #import pylab;pylab.plot(np.arange(len(s[0])),s.T); pylab.show(); import sys; sys.exit()

    for d in slits:
        v, dv = smooth(s[0], d.angular_resolution, d.v, d.dv,
                       degree=degree, span=span)
        d.slit1, d.slit2 = copy(d.slit1), copy(d.slit2)
        d.slit1.x = s[1]
        d.slit2.x = s[2]
        d.v, d.dv = v, dv
        # Update the calculated resolution
        divergence.apply(d)

def find_common(x, dx):
    x = x[np.argsort(x[:,0])]
    xo, sum, n = x[0]+0, x[0]+0, 1
    out = []
    for xk in x[1:]:
        if (xk[1:] - xo[1:] <= dx).all():
            sum += xk
            n += 1
            continue
        out.append(sum/n)
        xo, sum, n = xk+0, xk+0, 1
    out.append(sum/n)
    return np.vstack(out)

def smooth(xp, x, y, dy=None, degree=1, span=2):
    """
    Moving least squares smoother.

    If x is equally spaced, then this is equivalent to a Savitsky-Golay
    filter of the same degree and span.  Default is linear interpolation,
    with *degree=1* and *span=2*.
    """
    if dy is None:
        dy = np.ones(y.shape)
    yp, dyp = np.empty(xp.shape), np.empty(xp.shape)

    n = len(x)
    k = (span+1)//2


    if n <= span:
        if n <= degree:
            degree = n-1
        poly = wpolyfit(x, y, dy, degree=degree)
        yp[:], dyp[:] = poly.ci(xp)
    else:
        idx = np.searchsorted(x[k:-k], xp)
        for i, start in enumerate(idx):
            poly = wpolyfit(x[start:start+span],
                            y[start:start+span],
                            dy[start:start+span],
                            degree=degree)
            #if i%10 == 0:
            #    from ..wsolve import wpolyplot;wpolyplot(poly)
            yp[i], dyp[i] = [v[0] for v in poly.ci([xp[i]])]

    return yp, dyp


def demo():
    import pylab
    from ..examples import ng1p as group
    from ..corrections import join
    data = group.slit() | join()
    pylab.subplot(211)
    for d in data: d.plot()
    pylab.subplot(212)
    data |= SmoothSlits(degree=1,span=17)
    for d in data: d.plot()
    pylab.show()

if __name__ == "__main__":
    demo()
