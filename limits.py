# This program is public domain
"""
Data limits for high dynamic range data.

Limits() is a class for collecting combined limits on multiple sets of data.

limits(x,dv=0) returns floor,ceiling for a single dataset.
"""

from copy import copy
from numpy import inf

def limits(v, dv=0):
    """
    Return data limits (floor, ceiling), where floor is the minimum
    significant value (1/2-sigma away from zero) and ceiling is the
    maximum absolute value.  If dv=0, then floor is the minimum
    non-zero absolute value.
    """
    L = Limits(v,dv=dv)
    return L.floor,L.ceiling

class Limits(object):
    """
    Collect data limits, used for selecting ranges in colour maps for example.

    A Limits() object has the following attributes::

      ceiling - the maximum absolute data value
      floor   - 1/2 the min absolute value at least 1/2-sigma away from zero
      min     - the minimum data value
      max     - the maximum data value

    The limits are collected by adding data sets to a limits object::

       L = Limits()
       for f in frames:
           L.add(f, dv=sqrt(f))

    Alternatively you can use the union operator::

       L = Limits()
       for f in frames:
           L |= Limits(f, dv=sqrt(f))

    The computed attributes are robust against values all identically
    zero, returning instead a ceiling of 1 and a floor of 1/2.  Other
    situations may still cause problems such as infinities in the
    data (infinite limits are hard to represent in a colour scale) or
    all data being identical but non-zero (in which case floor==ceiling).

    Regarding the choice of floor, the main goal of limits is to
    avoid insignificant numbers on the log scale.  The simplest algorithm
    is to test v-dv > 0, which is to say that we are asking for 1-sigma
    significance.  However, it is useful to distinguish pixels with a
    single count from those with zero counts on a 2-D detector,
    but 1 +/- 1 would fail this test.  Changing the test to v-dv >= 0
    also includes points with 0 +/- 0, which we definitely want to
    exclude.  So instead we change the test to 1/2-sigma, which
    catches 1 +/- 1 and skips 0 +/- 0.
    """
    _floor = inf
    _ceiling = -inf
    _min = inf
    _max = -inf
    def _getfloor(self):
        return self._floor/2 if self._floor<inf else self.ceiling/2
    def _getceiling(self):
        return self._ceiling if self._ceiling>0 else 1
    def _getmin(self):
        return self._min if self._min < inf else self.max/2
    def _getmax(self):
        return self._max if self._max > -inf else 1
    floor = property(_getfloor)
    ceiling = property(_getceiling)
    min = property(_getmin)
    max = property(_getmax)

    def __init__(self, *args, **kw):
        if len(args) == 1:
            self.add(*args,**kw)
        elif len(args) > 1:
            raise TypeError, "Limits() tokes 0 or 1 argument"

    def add(self, v, dv=0):
        v = numpy.array(v)
        ceiling = abs(v).max()
        if ceiling > self._ceiling: self._ceiling = ceiling

        # Protect against no values being significant
        nz = v[abs(v)-dv/2>0]
        if len(nz) > 0:
            floor = abs(nz).min()
            if floor < self._floor: self._floor = floor

        min = v.min()
        max = v.max()
        if min < self._min: self._min = min
        if max > self._max: self._max = max

    def __ior__(self, L):
        if L._ceiling > self._ceiling: self._ceiling = L._ceiling
        if L._floor < self.floor: self._floor = L._floor
        if L._max > self._max: self._max = L._max
        if L._min < self._min: self._min = L._min

    def __or__(self, L):
        retval = copy(self)
        retval |= L
        return retval
