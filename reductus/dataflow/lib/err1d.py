# This program is public domain
"""
Error propagation algorithms for linear approximation to error.

This is a set of functions for processing uncertainties on arrays,
with both in-place and returned options.  See the :mod:`uncertainty`
module for an object-oriented wrapper.

Warning: like the underlying numpy library, the inplace operations
may return values of the wrong type if some of the arguments are
integers, so be sure to create them with floating point inputs.

Linear error approximation relies on linearity and independence.
These conditions may be broken in some circumstances.   The
*uncertainties* package on pypi does an excellent job of propagating
error through expressions, including those where the variable is used
multiple times.  Unfortunately, it is slow for large arrays, and so
this package is still needed.
"""
from __future__ import division  # Get true division

import numpy as np

# TODO: use numba for faster vector processing
# Most operations can be done in-place with one pass through the data saving
# both time and memory while being simpler to code.

def mean(X, varX, biased=True, axis=None, dtype=None, out=None, keepdims=False):
    # type: (np.ndarray, np.ndarray, bool) -> (float, float)
    r"""
    Return the mean and variance of a dataset.

    If varX is estimated from the data, then use *biased=True* so that the
    estimated variance is scaled by the normalized $\chi^2$.  See the
    wikipedia page for the weighted arithmetic mean for details.
    """
    # Use preallocated output (e.g., within an array slice) if provided
    Mout, varMout = (None, None) if out is None else out
    total_weight = np.sum(1./varX, axis=axis, dtype=dtype, keepdims=keepdims)
    M = np.sum(X/varX, axis=axis, dtype=dtype, out=Mout, keepdims=keepdims)
    if varMout is None:
        varM = 1./total_weight
    else:
        varM = varMout
        varM.fill(1.)
        varM /= total_weight
    if biased:
        # Scale by normalized chisq if variance calculation is biased
        chisq = np.sum((X-M)**2/varX, axis=axis, dtype=dtype, keepdims=keepdims)
        dof = np.prod(X.shape)/np.prod(chisq.shape) - 1
        varM *= chisq/dof
    return M, varM


def sum(X, varX, axis=None, dtype=None, out=None, keepdims=False):
    # type: (np.ndarray, np.ndarray, ...) -> (float, float)
    r"""
    Return the sum and variance of a dataset.

    Follows the numpy sum interface, except a pair of output arrays is required
    if you want to reuse an output.
    """
    Mout, varMout = (None, None) if out is None else out
    M = np.sum(X, axis=axis, dtype=dtype, out=Mout, keepdims=keepdims)
    varM = np.sum(varX, axis=axis, dtype=dtype, out=varMout, keepdims=keepdims)
    return M, varM


def cumsum(X, varX, axis=None, dtype=None, out=None):
    # type: (np.ndarray, np.ndarray, ...) -> (float, float)
    r"""
    Return the cumulative sum and variance of a dataset.

    Follows the numpy cumsum interface, except a pair of output arrays is
    required if you want to reuse an output.
    """
    Mout, varMout = (None, None) if out is None else out
    M = np.cumsum(X, axis=axis, dtype=dtype, out=Mout)
    varM = np.cumsum(varX, axis=axis, dtype=dtype, out=varMout)
    return M, varM


def average(X, varX, W, varW, axis=None):
    # type: (np.ndarray, np.ndarray, np.ndarray, np.ndarray, int) -> (float, float)
    r"""
    Return the weighted average of a dataset, with uncertainty in the weights.

    This is usual weighted average formula with gaussian uncertainty
    propagation. Use W=1, varW=0 for the simple gaussian average.

    Results checked against Monte Carlo simulation in explore/gaussian_average.py
    """
    # TODO: make this work for nD arrays when axis somewhere in the middle.
    # This requires keepdims for Swx, Sw, and then remove dim at the end
    Swx = np.sum(X*W, axis=axis)
    # Note: only need to check for W as scalar. The X in the expression of
    # varM will automatically promote all other scalars to vectors as needed.
    if np.isscalar(W):
        Sw = W*(np.prod(X.shape) if axis is None else X.shape[axis])
    else:
        Sw = np.sum(W, axis=axis)
    M = Swx/Sw
    varM = np.sum((W/Sw)**2*varX + ((X*Sw - Swx)/Sw**2)**2*varW, axis=axis)
    return M, varM


def interp(X, Xp, Fp, varFp, left=None, right=None):
    # type: (np.ndarray, np.ndarray, np.ndarray, np.ndarray, int) -> (np.ndarray, np.ndarray)
    """
    Linear interpolation of x points into points (xk,fk +/- dfk).

    xp is assumed to be monotonically increasing.  The interpolated
    value is undefined at duplicate points.

    Fp, varFp can be n-dimensional.

    left is (value,variance) to use for points before the range of xp, or
    None for the initial value.

    right is (value,variance) to use for points after the range of xp, or
    None for the final value.
    """
    idx = np.searchsorted(Xp[1:-1], X, side="right")
    if len(Xp) > 1:
        # Support repeated values in Xp, which will lead to 0/0 errors if the
        # interpolated point is one of the repeated values.
        p = (Xp[idx+1]-X)/(Xp[idx+1]-Xp[idx])
        if Fp.ndim > 1: # n-D support requires manual broadcast
            extra_dims = (np.newaxis,)*(Fp.ndim-1)
            p = p[(..., *extra_dims)]
        F = p*Fp[idx] + (1-p)*Fp[idx+1]
        # simple propagation of error formula for calculation of F, confirmed
        # by monte carlo simulation.
        varF = p**2*varFp[idx] + (1-p)**2*varFp[idx+1]
    else:
        F, varF = Fp[idx], varFp[idx]
    #print p,F,varF,idx
    if left is None:
        left = Fp[0], varFp[0]
    if right is None:
        right = Fp[-1], varFp[-1]
    F[X < Xp[0]], varF[X < Xp[0]] = left
    F[X > Xp[-1]], varF[X > Xp[-1]] = right

    return F, varF


def div(X, varX, Y, varY):
    """Division with error propagation"""
    # Direct algorithm:
    #   Z = X/Y
    #   varZ = (varX/X**2 + varY/Y**2) * Z**2
    #        = (varX + varY * Z**2) / Y**2
    # Indirect algorithm to minimize intermediates
    #np.seterr(all='raise')
    Z = X/Y      # truediv => Z is a float
    varZ = Z**2  # Z is a float => varZ is a float
    varZ *= varY
    varZ += varX
    # Z/Y/Y is more expensive than Z/Y**2 (poor data locality going through
    # the Y array twice), but it avoids creating a temporary for Y**2.
    # Also, happens to avoid integer overflow on Y**2...
    varZ /= Y
    varZ /= Y
    return Z, varZ


def mul(X, varX, Y, varY):
    """Multiplication with error propagation"""
    # Direct algorithm:
    Z = X * Y
    varZ = Y**2 * varX + X**2 * varY
    # Indirect algorithm won't ensure floating point results
    #   varZ = Y**2
    #   varZ *= varX
    #   Z = X**2   # Using Z to hold the temporary
    #   Z *= varY
    #   varZ += Z
    #   Z[:] = X
    #   Z *= Y
    return Z, varZ


def sub(X, varX, Y, varY):
    """Subtraction with error propagation"""
    Z = X - Y
    varZ = varX + varY
    return Z, varZ


def add(X, varX, Y, varY):
    """Addition with error propagation"""
    Z = X + Y
    varZ = varX + varY
    return Z, varZ

def sqrt(X, varX):
    """Square root with error propagation"""
    # Direct algorithm
    #   Z = X**n = sqrt(X)
    #   varZ = n*n * varX/X**2 * Z**2 = varX/(4*X)
    # Indirect algorithm to minimize intermediates
    Z = np.sqrt(X)
    varZ = varX/X
    varZ /= 4
    return Z, varZ

def exp(X, varX):
    """Exponentiation with error propagation"""
    Z = np.exp(X)
    varZ = varX * Z**2
    return Z, varZ


def log(X, varX):
    """Logarithm with error propagation"""
    Z = np.log(X)
    varZ = varX / X**2
    return Z, varZ


def sin(X, varX):
    return np.sin(X), varX*np.cos(X)**2


def cos(X, varX):
    return np.cos(X), varX*np.sin(X)**2


def tan(X, varX):
    return np.tan(X), varX/np.cos(X)**2


def arcsin(X, varX):
    return np.arcsin(X), varX/(1-X**2)


def arccos(X, varX):
    return np.arccos(X), varX/(1-X**2)


def arctan(X, varX):
    return np.arctan(X), varX/(1+X**2)**2


def arctan2(Y, varY, X, varX):
    # df/dX = Y/(X**2 + Y**2)
    # df/dY = X/(X**2 + Y**2)
    # varZ = (df/dX)**2 * varX + (df/dY)**2 * varY
    Z = np.arctan2(Y, X)
    varZ = (Y**2 * varX + X**2 * varY) / (X**2 + Y**2)**2
    return Z, varZ


# Confirm this formula before using it
# def pow(X,varX, Y,varY):
#    Z = X**Y
#    varZ = (Y**2 * varX/X**2 + varY * numpy.log(X)**2) * Z**2
#    return Z,varZ
#

def pow(X, varX, n):
    """X**n with error propagation"""
    # Direct algorithm
    #   Z = X**n
    #   varZ = n*n * varX/X**2 * Z**2
    # Indirect algorithm to minimize intermediates
    Z = X**n
    varZ = varX/X
    varZ /= X
    varZ *= Z
    varZ *= Z
    varZ *= n**2
    return Z, varZ


def pow2(X, varX, Y, varY):
    """X**Y with error propagation"""
    # Direct algorithm
    #   Z = X**Y
    #   varZ = Z**2 * ((Y*varX/X)**2 + (log(X)*varY)**2)
    Z = X**Y
    varZ = varX/X
    varZ *= Y
    varZ *= varZ
    T = np.log(X)
    T *= varY
    T *= T
    varZ += T
    del T
    varZ *= Z
    varZ *= Z
    return Z, varZ


def div_inplace(X, varX, Y, varY):
    """In-place division with error propagation"""
    # Z = X/Y
    # varZ = (varX + varY * (X/Y)**2) / Y**2 = (varX + varY * Z**2) / Y**2
    X /= Y     # X now has Z = X/Y
    T = X**2   # create T with Z**2
    T *= varY  # T now has varY * Z**2
    varX += T  # varX now has varX + varY*Z**2
    del T      # may want to use T[:] = Y for vectors
    T = Y**2   # reuse T for Y**2
    varX /= T  # varX now has varZ
    return X, varX


def mul_inplace(X, varX, Y, varY):
    """In-place multiplication with error propagation"""
    # Z = X * Y
    # varZ = Y**2 * varX + X**2 * varY
    T = Y**2   # create T with Y**2
    varX *= T  # varX now has Y**2 * varX
    del T      # may want to use T[:] = X for vectors
    T = X**2   # reuse T for X**2 * varY
    T *= varY  # T now has X**2 * varY
    varX += T  # varX now has varZ = X**2*varY + Y**2*varX
    X *= Y     # X now has Z = X*Y
    return X, varX


def sub_inplace(X, varX, Y, varY):
    """In-place subtraction with error propagation"""
    # Z = X - Y
    # varZ = varX + varY
    X -= Y
    varX += varY
    return X, varX


def add_inplace(X, varX, Y, varY):
    """In-place addition with error propagation"""
    # Z = X + Y
    # varZ = varX + varY
    X += Y
    varX += varY
    return X, varX


def pow_inplace(X, varX, n):
    """In-place X**n with error propagation"""
    # Direct algorithm
    #   Z = X**n
    #   varZ = abs(n) * varX/X**2 * Z**2
    # Indirect algorithm to minimize intermediates
    varX /= X
    varX /= X     # varX now has varX/X**2
    X **= n       # X now has Z = X**n
    varX *= X
    varX *= X     # varX now has varX/X**2 * Z**2
    varX *= n**2  # varX now has varZ
    return X, varX


def pow2_inplace(X, varX, Y, varY):
    """In-place X**Y with error propagation"""
    # Direct algorithm
    #   Z = X**Y
    #   varZ = Z**2 * ((Y*varX/X)**2 + (log(X)*varY)**2)
    varX /= X
    varX *= Y
    varX *= varX # varX now has (Y*varX/X)**2
    T = np.log(X)
    T *= varY
    T *= T
    varX += T # varX now has (Y*varX/X)**2 + (log(X)*varY)**2
    del T
    X **= Y   # X now has Z = X**Y
    varX *= X
    varX *= X # varX now has varZ
    return X, varX

def test():
    X, varX = 2, 0.04
    Y, varY = 3, 0.09
    N = 3
    def _check(op, result, variance):
        if op is pow:
            Z, varZ = op(X, varX, N)
        else:
            Z, varZ = op(X, varX, Y, varY)
        assert abs(Z-result)/result < 1e-13 and (varZ-variance)/variance < 1e-13, \
            "expected (%g,%g) got (%g,%g)"%(result, variance, Z, varZ)

    _check(add, X+Y, varX + varY)
    _check(sub, X-Y, varX + varY)
    _check(mul, X*Y, Y**2*varX + X**2*varY)
    _check(div, X/Y, (Y**2*varX + X**2*varY)/Y**4)
    _check(pow, X**N, varX/X**2 * X**(2*N) * N**2)
    _check(pow2, X**Y, X**(2*Y) * ((Y*varX/X)**2 + (np.log(X)*varY)**2))

def test_against_uncertainties_package():
    try:
        from uncertainties import ufloat
        from uncertainties import umath
        from math import sqrt as math_sqrt
    except ImportError:
        return
    X, varX = 0.5, 0.04
    Y, varY = 3, 0.09
    N = 3
    ux = ufloat(X, math_sqrt(varX))
    uy = ufloat(Y, math_sqrt(varY))

    def _compare(result, u):
        Z, varZ = result
        assert abs(Z-u.n)/u.n < 1e-13 and (varZ-u.s**2)/u.s**2 < 1e-13, \
            "expected (%g,%g) got (%g,%g)"%(u.n, u.s**2, Z, varZ)

    def _check_pow(u):
        _compare(pow(X, varX, N), u)

    def _check_unary(op, u):
        _compare(op(X, varX), u)

    def _check_binary(op, u):
        _compare(op(X, varX, Y, varY), u)

    _check_pow(ux**N)
    _check_binary(add, ux+uy)
    _check_binary(sub, ux-uy)
    _check_binary(mul, ux*uy)
    _check_binary(div, ux/uy)
    _check_binary(pow2, ux**uy)

    _check_unary(exp, umath.exp(ux))
    _check_unary(log, umath.log(ux))
    _check_unary(sqrt, umath.sqrt(ux))
    _check_unary(sin, umath.sin(ux))
    _check_unary(cos, umath.cos(ux))
    _check_unary(tan, umath.tan(ux))
    _check_unary(arcsin, umath.asin(ux))
    _check_unary(arccos, umath.acos(ux))
    _check_unary(arctan, umath.atan(ux))
    _check_binary(arctan2, umath.atan2(ux, uy))

def test_average():
    def _compare(result, u):
        Z, varZ = result
        U, varU = u
        assert abs(Z-U)/U < 1e-13 and (varZ-varU)/varU < 1e-13, \
            "expected (%g,%g) got (%g,%g)"%(U, varU, Z, varZ)
    x = np.array([1, 2, 3])
    xvar = np.array([0.2, 0.1, 0.05])
    xvar_const = np.array([0.2, 0.2, 0.2])
    w = np.array([1, 1, 1])
    wvar = np.array([0, 0, 0])
    s, svar = sum(x, xvar)
    # Test simple gaussian average gives the correct result
    _compare(average(x, xvar, 1, 0), (s/3, svar/9))
    # Test that program accepts scalar and vector inputs
    _compare(average(x, xvar_const[0], 1, 0), average(x, xvar_const, w, wvar))

if __name__ == "__main__":
    test()
    test_against_uncertainties_package()
    test_average()
