"""
Uncertainty propagation class
=============================

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

"""

"""


__all__ = ['Uncertainty']

import numpy as np

from . import err1d
from .formatnum import format_uncertainty
from . import wsolve


# TODO: rename to Measurement and add support for units?
# TODO: C implementation of *,/,**?
class Uncertainty(object):
    __slots__ = ('x','variance')
    # Make standard deviation available
    def _getdx(self): return np.sqrt(self.variance)
    def _setdx(self,dx):
        # Direct operation
        #    variance = dx**2
        # Indirect operation to avoid temporaries
        self.variance[:] = dx
        self.variance **= 2
    dx = property(_getdx,_setdx,doc="standard deviation")

    def rand(self, size=None):
        return np.random.randn(size=size)*self.dx + self.x

    # Constructor
    def __init__(self, x, variance=None):
        self.x, self.variance = x, variance

    # Numpy array slicing operations
    def __len__(self):
        return len(self.x)
    def __getitem__(self,key):
        return Uncertainty(self.x[key],self.variance[key])
    def __setitem__(self,key,value):
        self.x[key] = value.x
        self.variance[key] = value.variance
    def __delitem__(self, key):
        del self.x[key]
        del self.variance[key]
    def __iter__(self):
        for x,variance in zip(self.x, self.variance):
            yield Uncertainty(x, variance)

    # Normal operations: may be of mixed type
    def __add__(self, other):
        if isinstance(other,Uncertainty):
            return Uncertainty(*err1d.add(self.x,self.variance,other.x,other.variance))
        else:
            return Uncertainty(self.x+other, self.variance+0) # Force copy
    def __sub__(self, other):
        if isinstance(other,Uncertainty):
            return Uncertainty(*err1d.sub(self.x,self.variance,other.x,other.variance))
        else:
            return Uncertainty(self.x-other, self.variance+0) # Force copy
    def __mul__(self, other):
        if isinstance(other,Uncertainty):
            return Uncertainty(*err1d.mul(self.x,self.variance,other.x,other.variance))
        else:
            return Uncertainty(self.x*other, self.variance*other**2)
    def __truediv__(self, other):
        if isinstance(other,Uncertainty):
            return Uncertainty(*err1d.div(self.x,self.variance,other.x,other.variance))
        else:
            return Uncertainty(self.x/other, self.variance/other**2)
    def __pow__(self, other):
        if isinstance(other,Uncertainty):
            return Uncertainty(*err1d.pow2(self.x,self.variance,other.x,other.variance))
        else:
            return Uncertainty(*err1d.pow(self.x,self.variance,other))

    # Reverse operations are definitely of mixed type
    def __radd__(self, other):
        return Uncertainty(self.x+other, self.variance+0) # Force copy
    def __rsub__(self, other):
        return Uncertainty(other-self.x, self.variance+0)
    def __rmul__(self, other):
        return Uncertainty(self.x*other, self.variance*other**2)
    def __rtruediv__(self, other):
        return Uncertainty(other/self.x,self.variance*other**2/self.x**4)
    def __rpow__(self, other):
        return exp(np.log(other)*self)

    # In-place operations: may be of mixed type
    def __iadd__(self, other):
        if isinstance(other,Uncertainty):
            self.x,self.variance \
                = err1d.add_inplace(self.x,self.variance,other.x,other.variance)
        else:
            self.x+=other
        return self
    def __isub__(self, other):
        if isinstance(other,Uncertainty):
            self.x,self.variance \
                = err1d.sub_inplace(self.x,self.variance,other.x,other.variance)
        else:
            self.x-=other
        return self
    def __imul__(self, other):
        if isinstance(other,Uncertainty):
            self.x, self.variance \
                = err1d.mul_inplace(self.x,self.variance,other.x,other.variance)
        else:
            self.x *= other
            self.variance *= other**2
        return self
    def __itruediv__(self, other):
        if isinstance(other,Uncertainty):
            self.x,self.variance \
                = err1d.div_inplace(self.x,self.variance,other.x,other.variance)
        else:
            self.x /= other
            self.variance /= other**2
        return self
    def __ipow__(self, other):
        if isinstance(other,Uncertainty):
            self.x,self.variance \
                = err1d.pow2_inplace(self.x, self.variance, other.x,other.variance)
        else:
            self.x,self.variance = err1d.pow_inplace(self.x, self.variance, other)
        return self

    # Use true division instead of integer division
    def __div__(self, other): return self.__truediv__(other)
    def __rdiv__(self, other): return self.__rtruediv__(other)
    def __idiv__(self, other): return self.__itruediv__(other)


    # Unary ops
    def __neg__(self):
        return Uncertainty(-self.x,self.variance)
    def __pos__(self):
        return self
    def __abs__(self):
        return Uncertainty(np.abs(self.x),self.variance)

    def __str__(self):
        #return str(self.x)+" +/- "+str(numpy.sqrt(self.variance))
        if np.isscalar(self.x):
            return format_uncertainty(self.x,np.sqrt(self.variance))
        else:
            content = ", ".join(format_uncertainty(v,dv)
                    for v,dv in zip(self.x,np.sqrt(self.variance)))
            return "".join(("[",content,"]"))
    def __repr__(self):
        return "Uncertainty(%s,%s)"%(str(self.x),str(self.variance))

    # Not implemented
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
    def __long__(self): return NotImplemented
    def __float__(self): return self.x
    def __oct__(self): return NotImplemented
    def __hex__(self): return NotImplemented
    def __index__(self): return NotImplemented
    def __coerce__(self): return NotImplemented

    # TODO: comparisons returning p-value?

def log(x):
    return Uncertainty(*err1d.log(x.x,x.variance))
def exp(x):
    return Uncertainty(*err1d.exp(x.x,x.variance))
def sin(x):
    return Uncertainty(*err1d.sin(x.x,x.variance))
def cos(x):
    return Uncertainty(*err1d.cos(x.x,x.variance))
def tan(x):
    return Uncertainty(*err1d.tan(x.x,x.variance))
def arcsin(x):
    return Uncertainty(*err1d.arcsin(x.x,x.variance))
def arccos(x):
    return Uncertainty(*err1d.arccos(x.x,x.variance))
def arctan(x):
    return Uncertainty(*err1d.arctan(x.x,x.variance))
def arctan2(y, x):
    Uncertainty(*err1d.arctan2(y.x, y.variance, x.x, x.variance))


def mean(x, biased=True):
    r"""
    Return the mean and variance of a dataset.

    If variance is estimated from the data, then *biased* is True, and the
    estimated variance is scaled by the normalized $\chi^2$.
    """
    M, varM = err1d.mean(x, x.variance, biased=biased)
    return Uncertainty(M, varM)


def average(x, w):
    r"""
    Return the weighted average of a data set.
    """
    M, varM = err1d.average(x, x.variance, w, w.variance)
    return Uncertainty(M, varM)


def interp(x,xp,fp,left=None,right=None):
    """
    Linear interpolation of x into points (xk,yk +/- dyk).

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
    a = Uncertainty(5,3)
    b = Uncertainty(4,2)

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
    z = Uncertainty(np.array([1,2,3,4,5]),np.array([2,1,2,3,2]))
    assert z[2].x == 3 and z[2].variance == 2
    assert (z[2:4].x == [3,4]).all()
    assert (z[2:4].variance == [2,3]).all()
    z[2:4] = Uncertainty(np.array([8,7]),np.array([4,5]))
    assert z[2].x == 8 and z[2].variance == 4
    A = Uncertainty(np.array([a.x]*2),np.array([a.variance]*2))
    B = Uncertainty(np.array([b.x]*2),np.array([b.variance]*2))

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
    assert str(Uncertainty(5,3)) == "5.0(17)"
    assert str(Uncertainty(15,3)) == "15.0(17)"
    assert str(Uncertainty(151.23356,0.324185**2)) == "151.23(32)"

    xp = np.array([2.,3.])
    fp = Uncertainty(np.array([3.,1.]),np.array([0.04,0.16]))
    z = interp(2.4, xp, fp)
    assert abs(z.x-2.2) < 2e-15
    assert abs(z.variance-0.04) < 2e-15
    z = interp([0.,2.,2.4,3.,4.], xp, fp)
    assert np.linalg.norm(z.x - [3,3,2.2,1,1]) < 2e-15
    assert np.linalg.norm(z.variance - [0.04,0.04,0.04,0.16,0.16]) < 2e-15
    xp = np.array([2.,3.,3.,4.])
    fp = Uncertainty(np.array([3.,1.,3.,1.]),np.array([0.04,0.16,0.04,0.16]))
    z = interp([2.5,3.,3.5], xp, fp)
    assert np.linalg.norm(z.x - [2,3,2]) < 2e-15
    assert np.linalg.norm(z.variance - [0.05,0.04,0.05]) < 2e-15

if __name__ == "__main__": test()
