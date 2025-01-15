"""
Data smoothing

Uses moving window 1-D polynomial least squares smoothing filter.

"""
from __future__ import division

import numpy as np

from reductus.dataflow.lib.err1d import interp
from reductus.dataflow.lib.wsolve import smooth

def apply_smoothing(slits, dx, degree, span):
    assert span > degree, "Span must be greater than degree"
    s = np.hstack([[d.angular_resolution, d.slit1.x, d.slit2.x] for d in slits])
    s = find_common(s.T, dx=dx).T
    #import pylab;pylab.plot(np.arange(len(s[0])),s.T); pylab.show(); import sys; sys.exit()

    for d in slits:
        if span > 2:
            v, dv = smooth(s[0], d.angular_resolution, d.v, d.dv,
                           degree=degree, span=span)
        else:
            v, var = interp(s[0], d.angular_resolution, d.v, d.dv**2)
            dv = np.sqrt(var)
        d.slit1.x = s[1]
        d.slit2.x = s[2]
        d.v, d.dv = v, dv

def find_common(x, dx):
    x = x[np.argsort(x[:, 0])]
    xo, total, n = x[0]+0, x[0]+0, 1
    out = []
    for xk in x[1:]:
        if (xk[1:] - xo[1:] <= dx).all():
            total += xk
            n += 1
            continue
        out.append(total/n)
        xo, total, n = xk+0, xk+0, 1
    out.append(total/n)
    return np.vstack(out)
