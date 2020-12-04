"""
Based on scalars or numpy vectors, this class allows you to store and
manipulate values+uncertainties, with propagation of gaussian error for
addition, subtraction, multiplication, division, power, exp, log
and trig.  Also includes mean, weighted average, and linear interpolation.

Storage properties are determined by the numbers used to set the value
and uncertainty.  Inputs are coerced to floating point vectors since
numpy does not do automatic type conversion for in-place operations.
If you want single precision or extended precision floats be sure to
set x and variance to one of the those types before calling.

To save memory for huge arrays, the original data is used if it is a
floating point type. In place operations (a*=b, etc.) create at most one
extra copy for each operation. The out-of-place operation c=a*b by contrast
uses four intermediate vectors, so shouldn't be used for huge arrays.
"""
from __future__ import division

__all__ = ['Uncertainty']

from copy import copy

import numpy as np

from . import err1d
from .formatnum import format_uncertainty
from . import wsolve

def float_array(v):
    """
    Convert v to a floating point array if it is not one already.
    """
    if isinstance(v, np.ndarray) and np.issubdtype(v.dtype, np.inexact):
        return v
    if isinstance(v, int):
        return float(v)
    if isinstance(v, float):
        return v
    return np.asarray(v, np.float64)

def _U(x, variance):
    """
    Create an uncertainty object without type-checking.
    """
    #print("creating", x, variance)
    self = Uncertainty.__new__(Uncertainty)
    self._x = x
    self._variance = variance
    return self

# TODO: rename to Measurement and add support for units?
# TODO: C or numba implementation of *, /, **?
# TODO: use __array_function__ for sum, mean, etc.
# TODO: use __array_ufunc__ for all ops rather __mul__, etc.

_UNARY_DISPATCH = {
    np.log: err1d.log,
    np.exp: err1d.exp,
    np.sqrt: err1d.sqrt,
    np.sin: err1d.sin,
    np.cos: err1d.cos,
    np.tan: err1d.tan,
    np.arcsin: err1d.arcsin,
    np.arccos: err1d.arccos,
    np.arctan: err1d.arctan,
    np.negative: lambda a: (-a.x, a.variance),
    np.positive: lambda a: (a.x, a.variance),
    np.absolute: lambda a: (abs(a.x), a.variance),
}
_BINARY_DISPATCH = {
    np.arctan2: err1d.arctan2,
    np.add: err1d.add,
    np.subtract: err1d.sub,
    np.multiply: err1d.mul,
    np.true_divide: err1d.div,
    np.divide: err1d.div,
    np.power: err1d.mul,
    np.multiply: err1d.mul,
    np.multiply: err1d.mul,
}

class Uncertainty(object):
    __slots__ = ('_x', '_variance')
    __array_priority__ = 20.   # force array*uncertainty to use our __rmul__

    # Constructor
    def __init__(self, x, variance=None, dx=None):
        # Assign x first so that its type gets assigned properly.
        self.x = x
        # If standard deviation is given, turn it into variance.
        if dx is not None:
            if variance is not None:
                raise TypeError("Only one of variance and dx can be specified")
            variance = float_array(dx)**2
        # If variance is not given, set it to zero of the correct shape.
        if variance is None:
            variance = np.zeros_like(self.x)
        # Assign variance, possibly coercing its type.
        self.variance = variance

    def __array_ufunc__(self, ufunc, method, *args, **kwargs):
        #print(f"ufunc self:{self} ufunc:{ufunc}, method:{method}, args:{args}, {kwargs}")
        if method != "__call__":
            return NotImplemented
        f = _UNARY_DISPATCH.get(ufunc, None)
        if f is not None:
            a, = args
            return _U(*f(a.x, a.variance))
        #print(f"ufunc {ufunc}")
        f = _BINARY_DISPATCH.get(ufunc, None)
        if f is not None:
            a, b = args
            ax, av = (a.x, a.variance) if isinstance(a, Uncertainty) else (a, 0)
            bx, bv = (b.x, b.variance) if isinstance(b, Uncertainty) else (b, 0)
            return _U(*f(ax, av, bx, bv))
        return NotImplemented 

    def __copy__(self):
        return _U(copy(self.x), copy(self.variance))

    @property
    def x(self):
        return self._x
    @x.setter
    def x(self, v):
        self._x = float_array(v)

    @property
    def variance(self):
        return self._variance
    @variance.setter
    def variance(self, v):
        self._variance = float_array(v)

    @property
    def dtype(self):
        return self.x.dtype
    @property
    def flat(self):
        return iter(self)
    @property
    def ndim(self):
        return self.x.ndim
    @property
    def shape(self):
        return self.x.shape
    @property
    def size(self):
        return self.x.size
    @property
    def T(self):
        return self.transpose()
    # undefined properties:
    #    base, ctypes, data, flags, itemsize, nbytes, strides

    # Comparisons are not well defined for uncertainty objects.  For example,
    # is it true that (3 +/- 0.1) > (2 +/- 10)?  Running a quick simulation,
    # it is only true 54% of the time, so it is neither True nor False.
    # Similarly for equality/inequality.  The following functions are therefore
    # ill-defined:
    #     >, >=, <, <=, ==, !=, bool, all, any, nonzero
    #     argmax, amax, nanmax, maximum, fmax
    #     argmin, amin, nanmin, minimum, fmin
    #     argsort, sort, argpartition, partition, searchsorted
    #     clip, ptp
    # Could perhaps set a p-value for all operations, defaulting to p=0.05,
    # and using two-tailed tests.  That would at least give a partial ordering.
    # Bool, all, and any would involve a comparison against zero.  Maximum
    # likelihood could be used for maximum/minimum, and for the comparisons
    # used for sorting, which amounts to simply using the x value and ignoring
    # the variance.  For now, leave it undefined.

    # getfield, setfield, astype, byteswap, newbyteorder, setflags: use A.x.op

    # TODO: dump, dumps
    # TODO: item, itemset
    # TODO: tobytes, tofile, tolist, tostring

    # choose: index array will not be an uncertainty object, so no choose
    # method, but still may want to implement a choose function.  What happens
    # with np.choose when choices are all uncertainty objects?

    # cumsum mean, sum, std, var: see below
    # TODO: cumprod, prod, dot, trace

    # TODO: round() could truncate x to the number of digits defined by the
    # standard deviation and truncate variance to two digits.

    # TODO: assuming real, imag are identically distributed.  Is that true?
    def conj(self):
        return _U(self.x.conj(), self.variance+0.)
    conjugate = conj
    def real(self):
        return _U(self.x.real, self.variance)
    def imag(self):
        return _U(self.x.imag, self.variance)

    def fill(self, a):
        if isinstance(a, Uncertainty):
            self.x.fill(a.x)
            self.variance.fill(a.variance)
        else:
            self.x.fill(a)
            self.variance.fill(0.)

    # Array shaping/selection operations
    def compress(self, *args, **kw):
        # TODO: if out is supplied, then split it into out.x, out.variance
        return _U(self.x.compress(*args, **kw),
                  self.variance.compress(*args, **kw))
    copy = __copy__
    def diagonal(self, *args, **kw):
        return _U(self.x.diagonal(*args, **kw),
                  self.variance.diagonal(*args, **kw))
    def ravel(self, *args, **kw):
        return _U(self.x.ravel(*args, **kw),
                  self.variance.ravel(*args, **kw))
    def reshape(self, *args, **kw):
        return _U(self.x.reshape(*args, **kw),
                  self.variance.reshape(*args, **kw))
    def repeat(self, *args, **kw):
        return _U(self.x.repeat(*args, **kw),
                  self.variance.repeat(*args, **kw))
    def resize(self, *args, **kw):
        return _U(self.x.resize(*args, **kw),
                  self.variance.resize(*args, **kw))
    def squeeze(self, *args, **kw):
        return _U(self.x.squeeze(*args, **kw),
                  self.variance.squeeze(*args, **kw))
    def swapaxes(self, *args, **kw):
        return _U(self.x.swapaxes(*args, **kw),
                  self.variance.swapaxes(*args, **kw))
    def take(self, *args, **kw):
        return _U(self.x.take(*args, **kw),
                  self.variance.take(*args, **kw))
    def transpose(self, *args, **kw):
        return _U(self.x.transpose(*args, **kw),
                  self.variance.transpose(*args, **kw))
    def view(self, *args, **kw):
        return _U(self.x.view(*args, **kw),
                  self.variance.view(*args, **kw))
    def flatten(self, *args, **kw):
        return _U(self.x.flatten(*args, **kw),
                  self.variance.flatten(*args, **kw))

    # Make standard deviation available
    def _getdx(self):
        return np.sqrt(self.variance)
    def _setdx(self, dx):
        # Direct operation
        #    variance = dx**2
        # Indirect operation to avoid temporary
        self.variance[:] = dx
        self.variance **= 2
    dx = property(_getdx, _setdx, doc="standard deviation")

    def rand(self, size=None):
        return np.random.randn(size=size)*self.dx + self.x

    # Numpy array slicing operations
    def __len__(self):
        return len(self.x)
    def __getitem__(self, key):
        return _U(self.x[key], self.variance[key])
    def __setitem__(self, key, value):
        self.x[key] = value.x
        self.variance[key] = value.variance
    def __delitem__(self, key):
        del self.x[key]
        del self.variance[key]
    def __iter__(self):
        for x, variance in zip(self.x.flat, self.variance.flat):
            yield _U(x, variance)

    # Normal operations: may be of mixed type
    def __add__(self, other):
        if isinstance(other, Uncertainty):
            return _U(*err1d.add(self.x, self.variance, other.x, other.variance))
        else:
            return _U(self.x+other, self.variance+0.)  # Force copy
    def __sub__(self, other):
        if isinstance(other, Uncertainty):
            return _U(*err1d.sub(self.x, self.variance, other.x, other.variance))
        else:
            return _U(self.x-other, self.variance+0.)  # Force copy
    def __mul__(self, other):
        if isinstance(other, Uncertainty):
            return _U(*err1d.mul(self.x, self.variance, other.x, other.variance))
        else:
            return _U(self.x*other, self.variance*other**2)
    def __truediv__(self, other):
        if isinstance(other, Uncertainty):
            return _U(*err1d.div(self.x, self.variance, other.x, other.variance))
        else:
            return _U(self.x/other, self.variance/other**2)
    def __pow__(self, other):
        if isinstance(other, Uncertainty):
            return _U(*err1d.pow2(self.x, self.variance, other.x, other.variance))
        else:
            return _U(*err1d.pow(self.x, self.variance, other))

    # Reverse operations are definitely of mixed type
    def __radd__(self, other):
        return _U(self.x+other, self.variance+0.)  # Force copy
    def __rsub__(self, other):
        return _U(other-self.x, self.variance+0.)  # Force copy
    def __rmul__(self, other):
        return _U(self.x*other, self.variance*other**2)
    def __rtruediv__(self, other):
        return _U(other/self.x, self.variance*other**2/self.x**4)
    def __rpow__(self, other):
        return exp(np.log(other)*self)

    # In-place operations: may not be of mixed type
    # Note that the inplace operations are only inplace for numpy vectors.
    # For scalars, need to assign the new value of the array.
    def __iadd__(self, other):
        if isinstance(other, Uncertainty):
            self._x, self._variance = \
                err1d.add_inplace(self.x, self.variance, other.x, other.variance)
        else:
            self.x += other
        return self
    def __isub__(self, other):
        if isinstance(other, Uncertainty):
            self._x, self._variance = \
                err1d.sub_inplace(self.x, self.variance, other.x, other.variance)
        else:
            self.x -= other
        return self
    def __imul__(self, other):
        if isinstance(other, Uncertainty):
            self._x, self._variance = \
                err1d.mul_inplace(self.x, self.variance, other.x, other.variance)
        else:
            self.x *= other
            self.variance *= other**2
        return self
    def __itruediv__(self, other):
        if isinstance(other, Uncertainty):
            self._x, self._variance = \
                err1d.div_inplace(self.x, self.variance, other.x, other.variance)
        else:
            self.x /= other
            self.variance /= other**2
        return self
    def __ipow__(self, other):
        if isinstance(other, Uncertainty):
            self._x, self._variance = \
                err1d.pow2_inplace(self.x, self.variance, other.x, other.variance)
        else:
            self._x, self._variance = \
                err1d.pow_inplace(self.x, self.variance, other)
        return self

    # always uses true division, even if division is not imported from future
    def __div__(self, other):
        return self.__truediv__(other)
    def __rdiv__(self, other):
        return self.__rtruediv__(other)
    def __idiv__(self, other):
        return self.__itruediv__(other)

    # Unary ops
    def __neg__(self):
        return _U(-self.x, self.variance+0.)  # foce copy
    def __pos__(self):
        return self
    def __abs__(self):
        return _U(np.abs(self.x), self.variance+0.)  # force copy

    def __str__(self):
        #return str(self.x)+" +/- "+str(numpy.sqrt(self.variance))
        if np.isscalar(self.x):
            return format_uncertainty(self.x, self.dx)
        # TODO: don't need to format the entire matrix when printing summary
        formatted = [format_uncertainty(v, dv)
                     for v, dv in zip(self.x.flat, self.dx.flat)]
        with np.printoptions(formatter={'str_kind': lambda s: s}):
            return str(np.array(formatted).reshape(self.x.shape))
    def __repr__(self):
        result = "Uncertainty(%s,%s)"%(repr(self.x), repr(self.variance))
        return result.replace(' ', '').replace('\n', '').replace('array', '')

    #def __format__(self, *args, **kw):
    #    print("calling format with", args, kw)
    #    return str(self)

    # Not implemented
    def __matmul__(self, other): return NotImplemented
    def __rmatmul__(self, other): return NotImplemented
    def __imatmul__(self, other): return NotImplemented

    # Integer operations not defined
    def __floordiv__(self, other): return NotImplemented
    def __mod__(self, other): return NotImplemented
    def __divmod__(self, other): return NotImplemented
    def __lshift__(self, other): return NotImplemented
    def __rshift__(self, other): return NotImplemented
    def __and__(self, other): return NotImplemented
    def __xor__(self, other): return NotImplemented
    def __or__(self, other): return NotImplemented

    def __rfloordiv__(self, other): return NotImplemented
    def __rmod__(self, other): return NotImplemented
    def __rdivmod__(self, other): return NotImplemented
    def __rlshift__(self, other): return NotImplemented
    def __rrshift__(self, other): return NotImplemented
    def __rand__(self, other): return NotImplemented
    def __rxor__(self, other): return NotImplemented
    def __ror__(self, other): return NotImplemented

    def __ifloordiv__(self, other): return NotImplemented
    def __imod__(self, other): return NotImplemented
    def __ilshift__(self, other): return NotImplemented
    def __irshift__(self, other): return NotImplemented
    def __iand__(self, other): return NotImplemented
    def __ixor__(self, other): return NotImplemented
    def __ior__(self, other): return NotImplemented

    def __invert__(self): return NotImplemented  # For ~x
    def __complex__(self): return NotImplemented
    def __int__(self): return NotImplemented
    def __float__(self): return NotImplemented  # don't silently ignore variance
    def __long__(self): return NotImplemented
    def __oct__(self): return NotImplemented
    def __hex__(self): return NotImplemented
    def __index__(self): return NotImplemented
    def __coerce__(self): return NotImplemented

    # Want to support numpy ufunc handling so that np.sin(A)
    # returns Uncertainty(*err1d.sin(A)) when A is an uncertainty object.
    # numpy.sin(x) first calls np.asarray(x) to coerce the input into an
    # array-like shape, then runs through the ufunc on each element of x.
    # This process will not work if __array__ is defined.
    #def __array__(self): return NotImplemented

    def mean(self, axis=None, dtype=None, out=None, keepdims=False, biased=False):
        r"""
        Compute the uncertainty-weighted average of the dataset.

        Use *v.mean(biased=True)* when the variance in the individual points
        is estimated from the data. The result is scaled by the normalized
        $\chi^2$ to correct the bias.[1] Use *v.mean(biased=False)* for the
        variance-weighted average without the $\chi^2$ correction.
        wikipedia page for the weighted arithmetic mean for details.

        [1] https://en.wikipedia.org/wiki/Weighted_arithmetic_mean#Variance_weights
        """
        out_pair = None if out is None else (out.x, out.variance)
        M, varM = err1d.mean(
            self.x, self.variance, biased=biased,
            axis=axis, dtype=dtype, out=out_pair, keepdims=keepdims)
        return _U(M, varM) if out is None else out

    def sum(self, axis=None, dtype=None, out=None, keepdims=False):
        r"""
        Return the sum of an uncertain dataset.

        See numpy.sum for details on the interface.
        """
        out_pair = None if out is None else (out.x, out.variance)
        M, varM = err1d.sum(self.x, self.variance, axis=axis,
                            dtype=dtype, out=out_pair, keepdims=keepdims)
        return _U(M, varM) if out is None else out

    def cumsum(self, axis=None, dtype=None, out=None):
        r"""
        Return the cumulative sum of an uncertain dataset.

        See numpy.cumsum for details on the interface.
        """
        out_pair = None if out is None else (out.x, out.variance)
        M, varM = err1d.cumsum(self.x, self.variance, axis=axis,
                               dtype=dtype, out=out_pair)
        return _U(M, varM) if out is None else out

    def std(self, *args, **kw):
        raise TypeError("Use mean() to compute the mean and variance of uncertainty items")

    def var(self, *args, **kw):
        raise TypeError("Use mean() to compute the mean and variance of uncertainty items")

    def average(self, axis=None, weights=None, returned=False):
        r"""
        Return the weighted average of a data set.

        Note that mean(A) is the same as average(A, weights=1)
        """
        # TODO: explain difference between mean and average
        w, wvar = (
            (weights.x, weights.variance) if isinstance(weights, Uncertainty)
            else (1, 0) if weights is None
            else (weights, 0))
        M, varM = err1d.average(self.x, self.variance, w, wvar, axis=axis)
        return _U(M, varM)

    # TODO: comparisons returning p-value?
    def __eq__(self, other):
        if not isinstance(other, Uncertainty):
            return False
        return (self._x == other._x) & (self._variance == other._variance)

# numpy.method(x) calls x.method() if x has a method attribute, so just use
# the names from the numpy namespace.
sum = np.sum
cumsum = np.cumsum
mean = np.mean
#average = np.average   ## np.average(x) does not call x.average()
log = np.log
exp = np.exp
sqrt = np.sqrt
sin = np.sin
cos = np.cos
tan = np.tan
arcsin = np.arcsin
arccos = np.arccos
arctan = np.arctan
arctan2 = np.arctan2

def average(x, axis=None, weights=None, returned=False):
    r"""
    Return the weighted average of a data set.

    This uses $\sum w_k x_k / \sum w_k$ with gaussian uncertainty propagation
    with $\Delta w_k$ and $\Delta x_k$. Use $w_k = 1 \pm 0$ for a simple
    gaussian average.
    """
    return x.average(axis=axis, weights=weights)


def interp(x, xp, fp, left=None, right=None):
    """
    Linear interpolation of x into points (xk, yk +/- dyk).

    xp is assumed to be in ascending order.

    left is the uncertainty value to return for points before the range of xp,
    or None for the initial value, fp[0].

    right is the uncertainty value to return for points after the range of xp,
    or None for the final value, fp[-1].
    """
    if left is None: left = fp[0]
    if right is None: right = fp[-1]
    left = (left.x, left.variance)
    right = (right.x, right.variance)

    if isinstance(x, np.ndarray) and x.ndim > 0:
        F, varF = err1d.interp(x, xp, fp.x, fp.variance, left, right)
    else:
        F, varF = err1d.interp([x], xp, fp.x, fp.variance, left, right)
        F, varF = F[0], varF[0]
    return _U(F, varF)


def smooth(x, xp, fp, degree=2, span=5):
    """
    Windowed least squares smoothing.
    """
    if span > 2:
        y, dy = wsolve.smooth(x, xp, fp, fp.dx, degree=degree, span=span)
        return _U(y, dy**2)
    else:
        # TODO: smooth with extrapolate, but interp will not.
        return interp(x, xp, fp)

def polyfit(x, y, deg, rcond=None, full=False, w=None, cov=False):
    """
    Like numpy.polyfit, but uses uncertainty as the default weight and returns
    coeffients with uncertainty.

    Does not support *full=True*.
    """
    if full:
        raise NotImplementedError("full=True not supported")

    xvar = getattr(x, 'variance', None)
    if xvar is not None:
        if (xvar != 0.).any():
            raise NotImplementedError("Errors in variables not yet supported")
        xval = x.x
    else:
        xval = x
    # WARNING: numpy docs say use 1/sigma for weight, not 1/sigma^2
    yval, yerr = y.x, y.dx

    if w is None:
        w = 1/yerr

    p, V = np.polyfit(xval, yval, deg, rcond=rcond, full=False, w=w, cov=True)
    pvar = np.diagonal(V, axis1=0, axis2=1)
    coeff = _U(p, pvar)
    return (coeff, V) if cov else coeff

def test():
    a = Uncertainty(5, 3)
    b = Uncertainty(4, 2)
    v = Uncertainty([5, 4], [3, 2])

    # Uscalar op scalar
    z = a+4
    assert z.x == 5+4 and z.variance == 3
    z = a-4
    assert z.x == 5-4 and z.variance == 3
    z = a*4
    assert z.x == 5*4 and z.variance == 3*4**2
    z = a/4
    assert z.x == 5./4 and z.variance == 3./4**2

    # Uvector op scalar
    z = v+4
    assert (z == Uncertainty([5+4, 4+4], [3, 2])).all()
    z = v-4
    assert (z == Uncertainty([5-4, 4-4], [3, 2])).all()
    z = v*4
    assert (z == Uncertainty([5*4, 4*4], [3*4**2, 2*4**2])).all()
    z = v/4
    assert (z == Uncertainty([5/4, 4/4], [3./4**2, 2./4**2])).all()

    # Reverse scalar operations
    z = 4+a
    assert z.x == 4+5 and z.variance == 3
    z = 4-a
    assert z.x == 4-5 and z.variance == 3
    z = 4*a
    assert z.x == 4*5 and z.variance == 3*4**2
    z = 4/a
    assert z.x == 4./5 and abs(z.variance - 3./5**4 * 4**2) < 1e-15

    # Power operations
    z = a**2
    assert z.x == 5**2 and z.variance == 4*3*5**2
    z = a**1
    assert z.x == 5**1 and z.variance == 3
    z = a**0
    assert z.x == 5**0 and z.variance == 0
    z = a**-1
    assert z.x == 5**-1 and abs(z.variance - 3./5**4) < 1e-15

    # Binary operations
    z = a+b
    assert z.x == 5+4 and z.variance == 3+2
    z = a-b
    assert z.x == 5-4 and z.variance == 3+2
    z = a*b
    assert z.x == 5*4 and z.variance == (5**2*2 + 4**2*3)
    z = a/b
    assert z.x == 5./4 and abs(z.variance - (3./5**2 + 2./4**2)*(5./4)**2) < 1e-15

    # ===== Inplace operations =====
    # Scalar operations
    y = a+0; y += 4
    z = a+4
    assert y.x == z.x and abs(y.variance-z.variance) < 1e-15
    y = a+0; y -= 4
    z = a-4
    assert y.x == z.x and abs(y.variance-z.variance) < 1e-15
    y = a+0; y *= 4
    z = a*4
    assert y.x == z.x and abs(y.variance-z.variance) < 1e-15
    y = a+0; y /= 4
    z = a/4
    assert y.x == z.x and abs(y.variance-z.variance) < 1e-15

    # Power operations
    y = a+0; y **= 4
    z = a**4
    assert y.x == z.x and abs(y.variance-z.variance) < 1e-15

    # Binary operations
    y = a+0; y += b
    z = a+b
    assert y.x == z.x and abs(y.variance-z.variance) < 1e-15
    y = a+0; y -= b
    z = a-b
    assert y.x == z.x and abs(y.variance-z.variance) < 1e-15
    y = a+0; y *= b
    z = a*b
    assert y.x == z.x and abs(y.variance-z.variance) < 1e-15
    y = a+0; y /= b
    z = a/b
    assert y.x == z.x and abs(y.variance-z.variance) < 1e-15


    # =============== vector operations ================
    # Slicing
    z = Uncertainty(np.array([1, 2, 3, 4, 5]), np.array([2, 1, 2, 3, 2]))
    assert z[2].x == 3 and z[2].variance == 2
    assert (z[2:4].x == [3, 4]).all()
    assert (z[2:4].variance == [2, 3]).all()
    z[2:4] = Uncertainty(np.array([8, 7]), np.array([4, 5]))
    assert z[2].x == 8 and z[2].variance == 4
    A = Uncertainty(np.array([a.x]*2), np.array([a.variance]*2))
    B = Uncertainty(np.array([b.x]*2), np.array([b.variance]*2))

    # TODO complete tests of copy and inplace operations for vectors and slices.

    # Binary operations
    z = A+B
    assert (z.x == 5+4).all() and (z.variance == 3+2).all()
    z = A-B
    assert (z.x == 5-4).all() and (z.variance == 3+2).all()
    z = A*B
    assert (z.x == 5*4).all() and (z.variance == (5**2*2 + 4**2*3)).all()
    z = A/B
    assert (z.x == 5./4).all()
    assert (abs(z.variance - (3./5**2 + 2./4**2)*(5./4)**2) < 1e-15).all()

    # printing; note that sqrt(3) ~ 1.7
    assert str(Uncertainty(5, 3)) == "5.0(17)"
    assert str(Uncertainty(15, 3)) == "15.0(17)"
    assert str(Uncertainty(151.23356, 0.324185**2)) == "151.23(32)"

    xp = np.array([2., 3.])
    fp = Uncertainty(np.array([3., 1.]), np.array([0.04, 0.16]))
    z = interp(2.4, xp, fp)
    assert abs(z.x-2.2) < 2e-15
    assert abs(z.variance-0.04) < 2e-15
    z = interp([0., 2., 2.4, 3., 4.], xp, fp)
    assert np.linalg.norm(z.x - [3, 3, 2.2, 1, 1]) < 2e-15
    assert np.linalg.norm(z.variance - [0.04, 0.04, 0.04, 0.16, 0.16]) < 2e-15
    xp = np.array([2., 3., 3., 4.])
    fp = Uncertainty(np.array([3., 1., 3., 1.]), np.array([0.04, 0.16, 0.04, 0.16]))
    z = interp([2.5, 3., 3.5], xp, fp)
    assert np.linalg.norm(z.x - [2, 3, 2]) < 2e-15
    assert np.linalg.norm(z.variance - [0.05, 0.04, 0.05]) < 2e-15

    # Make sure polyfit is called with uncertainties
    xp = np.array([1., 2., 3., 4.])
    fp = Uncertainty(np.array([1., 3., 3., 3.]), np.array([0.04, 0.16, 0.04, 0.16]))
    p, C = polyfit(xp, fp, 1, cov=True)
    np_p, np_C = np.polyfit(xp, fp.x, 1, w=1/fp.dx, cov=True)
    assert np.linalg.norm(p.x - np_p) < 2e-15
    assert np.linalg.norm(p.variance - np.diagonal(np_C)) < 2e-15

    # Test numpy ufunc redirection
    assert np.log(a) == _U(*err1d.log(a.x, a.variance))
    assert np.exp(a) == _U(*err1d.exp(a.x, a.variance))
    assert np.sqrt(a) == _U(*err1d.sqrt(a.x, a.variance))
    assert np.sin(a) == _U(*err1d.sin(a.x, a.variance))
    assert np.cos(a) == _U(*err1d.cos(a.x, a.variance))
    assert np.tan(a) == _U(*err1d.tan(a.x, a.variance))
    # arcsin/arccos require values in [-1, 1]
    assert np.arcsin(a/6) == _U(*err1d.arcsin(a.x/6, a.variance/36))
    assert np.arccos(a/6) == _U(*err1d.arccos(a.x/6, a.variance/36))
    assert np.arctan(a) == _U(*err1d.arctan(a.x, a.variance))
    assert np.arctan2(a, b) == _U(*err1d.arctan2(a.x, a.variance, b.x, b.variance))

    # Test array forms
    assert (np.log(v) == _U(*err1d.log(v.x, v.variance))).all()
    assert (np.exp(v) == _U(*err1d.exp(v.x, v.variance))).all()
    assert (np.sqrt(v) == _U(*err1d.sqrt(v.x, v.variance))).all()
    assert (np.sin(v) == _U(*err1d.sin(v.x, v.variance))).all()
    assert (np.cos(v) == _U(*err1d.cos(v.x, v.variance))).all()
    assert (np.tan(v) == _U(*err1d.tan(v.x, v.variance))).all()
    # arcsin/arccos require values in [-1, 1]
    assert (np.arcsin(v/6) == _U(*err1d.arcsin(v.x/6, v.variance/36))).all()
    assert (np.arccos(v/6) == _U(*err1d.arccos(v.x/6, v.variance/36))).all()
    assert (np.arctan(v) == _U(*err1d.arctan(v.x, v.variance))).all()
    assert (np.arctan2(v, v) == _U(*err1d.arctan2(v.x, v.variance, v.x, v.variance))).all()

    # Check vector operations
    s = a+b
    assert np.sum(v) == s
    assert (np.cumsum(v) == _U([a.x, s.x], [a.variance, s.variance])).all()
    # Check in-place cumsum
    c = v.copy()
    np.cumsum(c, out=c)
    assert (np.cumsum(v) == c).all()
    # Mean and average uses err1d
    assert np.mean(v) == _U(*err1d.mean(v.x, v.variance, biased=False))
    assert v.mean(biased=True) == _U(*err1d.mean(v.x, v.variance, biased=True))
    assert v.mean(biased=False) == _U(*err1d.mean(v.x, v.variance, biased=False))
    assert average(v) == _U(*err1d.average(v.x, v.variance, 1, 0))
    assert average(v, weights=2) == _U(*err1d.average(v.x, v.variance, 2, 0))

    # rmul with array - Uarray
    A = Uncertainty([[5, 4], [3, 2]], [[1, 1], [1, 1]])
    B = np.array([3, 4])
    C = B[None, :] * A
    assert C[1, 1] == B[1]*A[1, 1]
    C = A * B[None, :]
    assert C[1, 1] == B[1]*A[1, 1]
    C = A * A
    assert C[1, 1] == A[1, 1]*A[1, 1]

    # Don't care about the format at the moment, but make sure that arrays print
    str(A)

if __name__ == "__main__":
    test()
