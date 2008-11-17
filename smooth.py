"""
Data smoothing

Uses moving window 1-D polynomial least squares smoothing filter.

Usage
=====

Create and apply the filter::

    from reflectometry.reduction.corrections import smooth
    ...
    data.apply(smooth(degree=2,span=12))

"""
__all__ = ['Smooth']

import numpy

from reflectometry.reduction.wsolve import wpolyfit


class Smooth(object):
    """
    Moving window 1-D polynomial least squares smoothing filter.

    The parameters are the polynomial order and the window size.
    The window size is the number of consecutive points used to
    smooth the data.  The window size must be odd.
    """

    properties = ['degree','span']
    degree = 2
    """Polynomial order for smoothing"""
    span = 11
    """Number of points used to fit smoothing polynomial"""

    def __init__(self, **kw):
        """
        Define the smoothing polynomial.
        """
        for k,v in kw.iteritems():
            assert hasattr(self,k), "No %s in %s"%(k,self.__class__.__name__)
            setattr(self,k,v)
        assert self.span%2==1, "Span must be odd"

    def __call__(self, data):
        """Apply the correction to the data"""
        if data.ispolarized():
            lines = [data.pp, data.pm, data.mp, data.mm]
        else:
            lines = [data]
        for L in lines:
            v,dv = smooth(L.x, L.v, L.dv, degree=self.degree, span=self.span)
            L.v,L.dv = v,dv
        data.log(str(self))

    def __str__(self):
        return "Smooth(degree=%d,span=%d)"%(self.degree,self.span)

# TODO: check for equal spacing and use Savitsky-Golay since it will
# TODO: be orders of magnitude faster. Precompute the SG coefficients
# TODO: in the Smooth class.


def smooth(x, y, dy=None, degree=2, span=5):
    """
    Moving least squares smoother.

    If x is equally spaced, then this is equivalent to a Savitsky-Golay
    filter of the same degree and span.
    """
    if dy == None: dy = numpy.ones(y.shape)
    yp,dyp = numpy.empty(y.shape),numpy.empty(y.shape)

    n = len(x)
    k = (span-1)/2

    poly = wpolyfit(x[:span], y[:span], dy[:span], degree=degree)
    yp[:k+1],dyp[:k+1] = poly.ci(x[:k+1])

    for i in range(k+1,n-k+1):
        poly = wpolyfit(x[i-k:i+k],y[i-k:i+k],dy[i-k:i+k], degree=degree)
        yp[i:i+1],dyp[i:i+1] = poly.ci(x[i:i+1])

    poly = wpolyfit(x[-span:],y[-span:],dy[-span:],degree=degree)
    yp[-k-1:],dyp[-k-1:] = poly.ci(x[-k-1:])

    return yp,dyp


def demo():
    import pylab
    from reflectometry.reduction.examples import e3a12 as dataset
    data = dataset.slits()
    pylab.errorbar(data.pp.x,data.pp.v,data.pp.dv,fmt='xg')
    data.apply(Smooth(degree=2,span=7))
    pylab.semilogy(data.pp.x, data.pp.v, '-g',
                   data.pp.x, data.pp.v-data.pp.dv, '-.g',
                   data.pp.x, data.pp.v+data.pp.dv, '-.g')
    pylab.show()

if __name__ == "__main__": demo()
