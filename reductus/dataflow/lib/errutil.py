"""
Extensions to the uncertainties package.

:func:`interp` is a drop-in replacement for numpy.interp which operates on
uncertainty values.

:func:`interp_err` and :func:`solve_err` operate on value and uncertainty in
different variables, but uses the machinery of the uncertainties package to
do the logic.

:func:`format_err` is a helper function for formatting value + uncertainty in
different variables.
"""


from uncertainties import ufloat
from uncertainties.unumpy import \
    uarray, umatrix, nominal_values as uval, std_devs as udev
import numpy as np

def interp_err(x, xp, fp, dfp, left=None, right=None):
    """
    Linear interpolation of x into points (xk,yk +/- dyk).

    xp is assumed to be in ascending order.

    left is the uncertainty value to return for points before the range of xp,
    or None for the initial value, fp[0].

    right is the uncertainty value to return for points after the range of xp,
    or None for the final value, fp[-1].
    """
    is_scalar_x = np.isscalar(x)
    if is_scalar_x:
        fp = ufloat(fp, dfp)
        f = interp([x], xp, fp, left, right)[0]
        return f.n, f.s
    else:
        fp = uarray(fp, dfp)
        f = interp(x, xp, fp, left, right)
        return uval(f), udev(f)

def format_err(x, dx):
    """
    Format number with uncertainty.
    """
    return ufloat(x, dx).format('gS')


def solve_err(A, dA, b, db):
    A = umatrix(A, dA)
    b = umatrix(b, db).T
    x = A.I*b
    return uval(x), udev(x)


def interp(x, xp, fp, left=None, right=None):
    """
    1-D interpolation of *x* into *(xp,fp)*.

    *xp* must be an increasing vector.  *x* can be scalar or vector.

    If *x* is beyond the range of *xp*, returns *left/right*, or the value of
    *fp* at the end points if *left/right* is not defined.

    Implemented in pure python so *fp* can be an extended numeric type such
    as complex or value+uncertainty.
    """
    is_scalar_x = np.isscalar(x)
    if len(xp) == 1:
        f = fp[np.zeros_like(x, dtype='i')]
    else:
        xp = np.asarray(xp)
        if np.any(np.diff(xp) < 0.):
            raise ValueError("interp needs a sorted list")
        if not is_scalar_x:
            x = np.asarray(x)
        idx = np.searchsorted(xp[1:-1], x)
        # Support repeated values in Xp, which will lead to 0/0 errors if the
        # interpolated point is one of the repeated values.
        p = (xp[idx+1]-x)/(xp[idx+1]-xp[idx])
        f = p*fp[idx] + (1-p)*fp[idx+1]

    if is_scalar_x:
        if x < xp[0]:
            return left if left is not None else fp[0]
        elif x > xp[-1]:
            return right if right is not None else fp[-1]
        else:
            return f
    else:
        f[x < xp[0]] = left if left is not None else fp[0]
        f[x > xp[-1]] = right if right is not None else fp[-1]
        return f
