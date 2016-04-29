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

def mean(X, varX, biased=True):
    # type: (np.ndarray, np.ndarray, bool) -> (float, float)
    r"""
    Return the mean and variance of a dataset.

    If varX is estimated from the data, then *biased* is True, and the
    estimated variance is scaled by the normalized $\chi^2$.  See the
    wikipedia page for the weighted arithmetic mean for details.
    """
    total_weight = np.sum(1./varX)
    M = np.sum(X/varX)/total_weight
    varM = 1./total_weight
    if biased:
        # Scale by chisq if variance calculation is biased
        varM *= np.sum((X-M)**2/varX)/(len(X)-1)
    return M, varM


def average(X, varX, W, varW, axis=None):
    # type: (np.ndarray, np.ndarray, np.ndarray, np.ndarray, int) -> (float, float)
    r"""
    Return the weighted average of a dataset, with uncertainty in the weights.

    Note that :function:`mean` is the average weighted by *1/varX*, with a
    possible bias correction based on $\chi^2$.
    """
    # TODO: why is mean weighted by 1/variance instead of 1?
    # Note: code checked vs. monte carlo simulation in explore.gaussian_average
    Swx = np.sum(X*W, axis=axis)
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
        F = p*Fp[idx] + (1-p)*Fp[idx+1]
        # simple propagation of error formula for calculation of F, confirmed
        # by monte carlo simulation.
        varF = p**2*varFp[idx] + (1-p)**2*varFp[idx+1]
    else:
        F, varF = Fp[idx], varFp[idx]
    #print p,F,varF,idx
    if left is None: left = Fp[0],varFp[0]
    if right is None: right = Fp[-1],varFp[-1]
    F[X<Xp[0]], varF[X<Xp[0]] = left
    F[X>Xp[-1]], varF[X>Xp[-1]] = right

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
    # df/dX = (X-Y)/(X**2 + Y**2)
    # df/dY = X/(X**2 + Y**2)
    # varZ = (df/dX)**2 * varX + (df/dY)**2 * varY
    Z = np.arctan2(Y, X)
    varZ = ((X-Y)**2 * varX + X**2 * varY) / (X**2 + Y**2)**2
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
    del T   # may want to use T[:] = Y for vectors
    T = Y   # reuse T for Y
    T **=2     # T now has Y**2
    varX /= T  # varX now has varZ
    return X, varX


def mul_inplace(X, varX, Y, varY):
    """In-place multiplication with error propagation"""
    # Z = X * Y
    # varZ = Y**2 * varX + X**2 * varY
    T = Y**2   # create T with Y**2
    varX *= T  # varX now has Y**2 * varX
    del T   # may want to use T[:] = X for vectors
    T = X   # reuse T for X**2 * varY
    T **=2     # T now has X**2
    T *= varY  # T now has X**2 * varY
    varX += T  # varX now has varZ
    X *= Y     # X now has Z
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
