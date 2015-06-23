"""
Extensions to the uncertainties package.
"""
import uncertainties as err
import uncertainties.unumpy as nperr
import numpy as np

def interp(x,xp,fp,dfp,left=None,right=None):
    """
    Linear interpolation of x into points (xk,yk +/- dyk).

    xp is assumed to be in ascending order.

    left is the uncertainty value to return for points before the range of xp,
    or None for the initial value, fp[0].

    right is the uncertainty value to return for points after the range of xp,
    or None for the final value, fp[-1].
    """
    if (isinstance(x, (float, int, np.number))
            or isinstance(x, np.ndarray) and x.ndim == 0):
        fp = err.ufloat(fp,dfp)
        f = _interp([x], xp, fp, left, right)[0]
        return f.n, f.s**2
    else:
        fp = nperr.uarray(fp,dfp)
        f = _interp(x, xp, fp, left, right)
        return np.array([xi.n for xi in f]),np.array([xi.s for xi in f])

def _interp(x,xp,fp,left=None,right=None):
    idx = np.searchsorted(xp[1:-1], x)
    # Support repeated values in Xp, which will lead to 0/0 errors if the
    # interpolated point is one of the repeated values.
    p = (xp[idx+1]-x)/(xp[idx+1]-xp[idx])
    f = p*fp[idx] + (1-p)*fp[idx+1]
    if left is None: left = fp[0]
    if right is None: right = fp[-1]
    f[x<xp[0]] = left if left is not None else fp[0]
    f[x>xp[-1]] = right if right is not None else fp[-1]

    return f

def format(x,dx):
    """
    Format number with uncertainty.
    """
    return err.ufloat(x,dx).format('gS')

def solve(A,dA,b,db):
    A = nperr.umatrix(A,dA)
    b = nperr.umatrix(b,db).T
    x = A.I*b
    return x.nominal_values, x.std_devs
