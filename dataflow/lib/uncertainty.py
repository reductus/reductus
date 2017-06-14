"""
Based on scalars or numpy vectors, this class allows you to store and
manipulate values+uncertainties, with propagation of gaussian error for
addition, subtraction, multiplication, division, power, exp, log
and trig.  Also includes mean, weighted average, and linear interpolation.

Storage properties are determined by the numbers used to set the value
and uncertainty.  Be sure to use floating point uncertainty vectors
for inplace operations since numpy does not do automatic type conversion.
Normal operations can use mixed integer and floating point.  In place
operations (a*=b, etc.) create at most one extra copy for each operation.
The copy operation c=a*b by contrast uses four intermediate vectors, so
shouldn't be used for huge arrays.
"""
from __future__ import division

__all__ = ['Uncertainty']

from copy import copy

import numpy as np

from . import err1d
from .formatnum import format_uncertainty
from . import wsolve


# TODO: rename to Measurement and add support for units?
# TODO: C implementation of *, /, **?
class Uncertainty(object):
    __slots__ = ('x', 'variance')
    __array_priority__ = 20.   # force array*uncertainty to use our __rmul__

    # Constructor
    def __init__(self, x, variance=None):
        self.x, self.variance = x, variance

    def __copy__(self):
        return Uncertainty(copy(self.x), copy(self.variance))

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
        return Uncertainty(self.x.conj(), self.variance)
    conjugate = conj
    def real(self):
        return Uncertainty(self.x.real(), self.variance)
    def imag(self):
        return Uncertainty(self.x.imag(), self.variance)

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
        return Uncertainty(self.x.compress(*args, **kw),
                           self.variance.compress(*args, **kw))
    copy = __copy__
    def diagonal(self, *args, **kw):
        return Uncertainty(self.x.diagonal(*args, **kw),
                           self.variance.diagonal(*args, **kw))
    def ravel(self, *args, **kw):
        return Uncertainty(self.x.ravel(*args, **kw),
                           self.variance.ravel(*args, **kw))
    def reshape(self, *args, **kw):
        return Uncertainty(self.x.reshape(*args, **kw),
                           self.variance.reshape(*args, **kw))
    def repeat(self, *args, **kw):
        return Uncertainty(self.x.repeat(*args, **kw),
                           self.variance.repeat(*args, **kw))
    def resize(self, *args, **kw):
        return Uncertainty(self.x.resize(*args, **kw),
                           self.variance.resize(*args, **kw))
    def squeeze(self, *args, **kw):
        return Uncertainty(self.x.squeeze(*args, **kw),
                           self.variance.squeeze(*args, **kw))
    def swapaxes(self, *args, **kw):
        return Uncertainty(self.x.swapaxes(*args, **kw),
                           self.variance.swapaxes(*args, **kw))
    def take(self, *args, **kw):
        return Uncertainty(self.x.take(*args, **kw),
                           self.variance.take(*args, **kw))
    def transpose(self, *args, **kw):
        return Uncertainty(self.x.transpose(*args, **kw),
                           self.variance.transpose(*args, **kw))
    def view(self, *args, **kw):
        return Uncertainty(self.x.view(*args, **kw),
                           self.variance.view(*args, **kw))

    # Make standard deviation available
    def _getdx(self):
        return np.sqrt(self.variance)
    def _setdx(self, dx):
        # Direct operation
        #    variance = dx**2
        # Indirect operation to avoid temporaries
        self.variance[:] = dx
        self.variance **= 2
    dx = property(_getdx, _setdx, doc="standard deviation")

    def rand(self, size=None):
        return np.random.randn(size=size)*self.dx + self.x

    # Numpy array slicing operations
    def __len__(self):
        return len(self.x)
    def __getitem__(self, key):
        return Uncertainty(self.x[key], self.variance[key])
    def __setitem__(self, key, value):
        self.x[key] = value.x
        self.variance[key] = value.variance
    def __delitem__(self, key):
        del self.x[key]
        del self.variance[key]
    def __iter__(self):
        for x, variance in zip(self.x.flat, self.variance.flat):
            yield Uncertainty(x, variance)

    # Normal operations: may be of mixed type
    def __add__(self, other):
        if isinstance(other, Uncertainty):
            return Uncertainty(*err1d.add(self.x, self.variance, other.x, other.variance))
        else:
            return Uncertainty(self.x+other, self.variance+0) # Force copy
    def __sub__(self, other):
        if isinstance(other, Uncertainty):
            return Uncertainty(*err1d.sub(self.x, self.variance, other.x, other.variance))
        else:
            return Uncertainty(self.x-other, self.variance+0) # Force copy
    def __mul__(self, other):
        if isinstance(other, Uncertainty):
            return Uncertainty(*err1d.mul(self.x, self.variance, other.x, other.variance))
        else:
            return Uncertainty(self.x*other, self.variance*other**2)
    def __truediv__(self, other):
        if isinstance(other, Uncertainty):
            return Uncertainty(*err1d.div(self.x, self.variance, other.x, other.variance))
        else:
            return Uncertainty(self.x/other, self.variance/other**2)
    def __pow__(self, other):
        if isinstance(other, Uncertainty):
            return Uncertainty(*err1d.pow2(self.x, self.variance, other.x, other.variance))
        else:
            return Uncertainty(*err1d.pow(self.x, self.variance, other))

    # Reverse operations are definitely of mixed type
    def __radd__(self, other):
        return Uncertainty(self.x+other, self.variance+0) # Force copy
    def __rsub__(self, other):
        return Uncertainty(other-self.x, self.variance+0)
    def __rmul__(self, other):
        return Uncertainty(self.x*other, self.variance*other**2)
    def __rtruediv__(self, other):
        return Uncertainty(other/self.x, self.variance*other**2/self.x**4)
    def __rpow__(self, other):
        return exp(np.log(other)*self)

    # In-place operations: may be of mixed type
    def __iadd__(self, other):
        if isinstance(other, Uncertainty):
            self.x, self.variance \
                = err1d.add_inplace(self.x, self.variance, other.x, other.variance)
        else:
            self.x += other
        return self
    def __isub__(self, other):
        if isinstance(other, Uncertainty):
            self.x, self.variance \
                = err1d.sub_inplace(self.x, self.variance, other.x, other.variance)
        else:
            self.x -= other
        return self
    def __imul__(self, other):
        if isinstance(other, Uncertainty):
            self.x, self.variance \
                = err1d.mul_inplace(self.x, self.variance, other.x, other.variance)
        else:
            self.x *= other
            self.variance *= other**2
        return self
    def __itruediv__(self, other):
        if isinstance(other, Uncertainty):
            self.x, self.variance \
                = err1d.div_inplace(self.x, self.variance, other.x, other.variance)
        else:
            self.x /= other
            self.variance /= other**2
        return self
    def __ipow__(self, other):
        if isinstance(other, Uncertainty):
            self.x, self.variance \
                = err1d.pow2_inplace(self.x, self.variance, other.x, other.variance)
        else:
            self.x, self.variance = err1d.pow_inplace(self.x, self.variance, other)
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
        return Uncertainty(-self.x, self.variance)
    def __pos__(self):
        return self
    def __abs__(self):
        return Uncertainty(np.abs(self.x), self.variance)

    def __str__(self):
        #return str(self.x)+" +/- "+str(numpy.sqrt(self.variance))
        if np.isscalar(self.x):
            return format_uncertainty(self.x, np.sqrt(self.variance))
        else:
            content = ", ".join(format_uncertainty(v, dv)
                                for v, dv in zip(self.x, np.sqrt(self.variance)))
            return "".join(("[", content, "]"))
    def __repr__(self):
        return "Uncertainty(%s,%s)"%(str(self.x), str(self.variance))

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

    def mean(self, axis=None, dtype=None, out=None, keepdims=False, biased=True):
        r"""
        Compute the uncertainty-weighted average of the dataset.

        If varX is estimated from the data, then use *biased=True* so that the
        estimated variance is scaled by the normalized $\chi^2$.  See the
        wikipedia page for the weighted arithmetic mean for details.

        See numpy.mean for details on the remaining parameters.
        """
        if out is not None:
            out = out.x, out.variance
        M, varM = err1d.mean(x.x, x.variance, *args, **kw)
        return Uncertainty(M, varM)

    def sum(self, axis=None, dtype=None, out=None, keepdims=False):
        r"""
        Return the sum of an uncertain dataset.

        See numpy.sum for details on the interface.
        """
        if out is not None:
            new_out = out.x, out.variance
        else:
            new_out = (None, None)
        M, varM = err1d.sum(self.x, self.variance, axis=axis,
                            dtype=dtype, out=new_out, keepdims=keepdims)
        return Uncertainty(M, varM) if out is None else new_out

    def cumsum(self, axis=None, dtype=None, out=None, keepdims=False):
        r"""
        Return the cumulative sum of an uncertain dataset.

        See numpy.cumsum for details on the interface.
        """
        if out is not None:
            new_out = out.x, out.variance
        else:
            new_out = (None, None)
        M, varM = err1d.cumsum(self.x, self.variance, axis=axis,
                               dtype=dtype, out=new_out, keepdims=keepdims)
        return Uncertainty(M, varM) if out is None else new_out

    def std(self, *args, **kw):
        raise TypeError("Use mean() to compute the mean and variance of uncertainty items")

    def var(self, *args, **kw):
        raise TypeError("Use mean() to compute the mean and variance of uncertainty items")

    def average(self, axis=None, weights=None):
        r"""
        Return the weighted average of a data set.

        Note that mean(A) is the same as average(A, weights=1)
        """
        # TODO: give difference between mean and average
        M, varM = err1d.average(self.x, self.variance, w, w.variance, axis=axis)
        return Uncertainty(M, varM)

    # TODO: comparisons returning p-value?

    def log(self):
        return Uncertainty(*err1d.log(self.x, self.variance))
    def exp(self):
        return Uncertainty(*err1d.exp(self.x, self.variance))
    def sin(self):
        return Uncertainty(*err1d.sin(self.x, self.variance))
    def cos(self):
        return Uncertainty(*err1d.cos(self.x, self.variance))
    def tan(self):
        return Uncertainty(*err1d.tan(self.x, self.variance))
    def arcsin(self):
        return Uncertainty(*err1d.arcsin(self.x, self.variance))
    def arccos(self):
        return Uncertainty(*err1d.arccos(self.x, self.variance))
    def arctan(self):
        return Uncertainty(*err1d.arctan(self.x, self.variance))
    def arctan2(self, other):
        Uncertainty(*err1d.arctan2(self.x, self.variance, other.x, other.variance))

# numpy.method(x) calls x.method() if x has a method attribute, so just use
# the names from the numpy namespace.
sum = np.sum
cumsum = np.cumsum
mean = np.mean
#average = np.average   ## np.average(x) does not call x.average()
log = np.log
exp = np.exp
sin = np.sin
cos = np.cos
tan = np.tan
arcsin = np.arcsin
arccos = np.arccos
arctan = np.arctan
arctan2 = np.arctan2

def average(x, axis=None, weights=None):
    r"""
    Return the weighted average of a data set.
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
    return Uncertainty(F, varF)


def smooth(x, xp, fp, degree=2, span=5):
    """
    Windowed least squares smoothing.
    """
    if span > 2:
        y, dy = wsolve.smooth(x, xp, fp, fp.dx, degree=degree, span=span)
        return Uncertainty(y, dy**2)
    else:
        # TODO: smooth with extrapolate, but interp will not.
        return interp(x, xp, fp)


def test():
    a = Uncertainty(5, 3)
    b = Uncertainty(4, 2)

    # Scalar operations
    z = a+4
    assert z.x == 5+4 and z.variance == 3
    z = a-4
    assert z.x == 5-4 and z.variance == 3
    z = a*4
    assert z.x == 5*4 and z.variance == 3*4**2
    z = a/4
    assert z.x == 5./4 and z.variance == 3./4**2

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

if __name__ == "__main__": test()
