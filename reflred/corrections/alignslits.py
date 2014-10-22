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
__all__ = ['AlignSlits']

import numpy as np

from ..pipeline import Correction
from ..wsolve import wpolyfit


class AlignSlits(Correction):
    """
    Align slits with a moving window 1-D polynomial least squares filter.

    *dx* is the size within which slit openings are considered equivalent.
    The default is 0.01 mm.

    *degree* is the polynomial degree, and *span* is the number of consecutive
    points used to fit the polynomial. *span* must larger  than *degree*.
    Odd sized *span* is preferred.  *degree=1* and  *span=2* is
    equivalent to linear interpolation.
    """
    parameters = [
        ['degree', 2, '', 'polynomial degree'],
        ['span', 11, '', 'number of consecutive points in the fit'],
        ['dx', 0.01, 'mm', 'size within which slits are considered equivalent'],
        ]

    def apply(self, data):
        """Apply the correction to the data"""
        # TODO: how to check parameter consistency
        # Maybe on __init__, but does not allow UI to update property directly
        # Maybe on assignment, but doesn't allow update to one parameter without
        # the other.
        # Maybe provide check method which returns a list of invalid parameters
        # and the reason, or nothing if all parameter values are valid.
        assert self.span>self.degree, "Span must be greater than degree"
        if data.ispolarized:
            lines = [data.pp, data.pm, data.mp, data.mm]
        else:
            lines = [data]
        xp = find_common([v.slit1.x for v in lines], dx=self.dx)
        for L in lines:
            v,dv = smooth(xp, L.slit1.x, L.v, L.dv,
                          degree=self.degree, span=self.span)
            L.v,L.dv = v,dv

def find_common(datasets, dx):
    x = np.sort(np.hstack(datasets))
    xo,sum,n = x[0],x[0],1
    out = []
    for i,xi in enumerate(x[1:]):
        if xi - xo <= dx:
            sum += xi
            n += 1
            continue
        out.append(sum/n)
        xo,sum,n = xi,xi,1
    out.append(sum/n)
    return np.array(out)

def smooth(xp, x, y, dy=None, degree=1, span=2):
    """
    Moving least squares smoother.

    If x is equally spaced, then this is equivalent to a Savitsky-Golay
    filter of the same degree and span.  Default is linear interpolation,
    with *degree=1* and *span=2*.
    """
    if dy == None: dy = np.ones(y.shape)
    yp,dyp = np.empty(xp.shape),np.empty(xp.shape)

    n = len(x)
    k = (span-1)//2


    if n <= span:
        if n <= degree: degree = n-1
        poly = wpolyfit(x,y,dy,degree=degree)
        yp[:], dyp[:] = poly.ci(xp)
    else:
        idx = np.searchsorted(x[k:-k],xp)
        for i,start in enumerate(idx):
            poly = wpolyfit(x[start:start+span],
                            y[start:start+span],
                            dy[start:start+span],
                            degree=degree)
            yp[i],dyp[i] = poly.ci(xp[i])
    return yp,dyp


def demo():
    import pylab
    from ..examples import ng1p as dataset
    data = dataset.slits()[0]
    print data.pp.v
    print data.pp.dv
    pylab.errorbar(data.pp.slit1.x,data.pp.v,data.pp.dv,fmt='xg')
    data |= AlignSlits(degree=2,span=7)
    pylab.semilogy(data.pp.slit1.x, data.pp.v, '-g',
                   data.pp.slit1.x, data.pp.v-data.pp.dv, '-.g',
                   data.pp.slit1.x, data.pp.v+data.pp.dv, '-.g',
                   hold=True)
    pylab.show()

if __name__ == "__main__":
    demo()
