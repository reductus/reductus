"""
1-D and 2-D rebinning code.
"""
import numpy as np

try:
    from typing import Sequence, Optional, Union
except ImportError:
    pass

def rebin(x, I, xo, dtype=np.float64):
    # type: (Sequence, Sequence, Sequence, Union[str, type]) -> np.ndarray
    """
    Rebin a vector.

    *x* are the existing bin edges.

    *xo* are the new bin edges.

    *I* are the existing counts (one fewer than edges).

    *dtype* is the type to use for the intensity vectors.  This can be
    integer (uint8, uint16, uint32) or real (float32 or f, float64 or d).
    The edge vectors are all coerced to doubles.

    Note that total intensity is not preserved for integer rebinning.
    The algorithm uses truncation so total intensity will be down on
    average by half the total number of bins.
    """
    # Coerce to arrays and check shape
    I = np.asarray(I)
    x, xo = np.asarray(x, dtype='d'), np.asarray(xo, dtype='d')
    if len(x.shape) != 1 or len(xo.shape) != 1 or len(x)-1 != len(I):
        raise TypeError("input array incorrect shape %s"%str(I.shape))

    ix = _rebin_counts(x, I, xo, dtype=dtype)
    return ix


def _rebin_counts(x, I, xo, dtype):
    # type: (np.ndarray, np.ndarray, np.ndarray, np.ndarray) -> None

    # Sort directions ascending vs. descending
    if x[0] > x[-1]:
        x, I = x[::-1], I[::-1]
    reverse_xo = xo[0] > xo[-1]
    if reverse_xo:
        xo = xo[::-1]

    cc = np.empty(len(x), dtype=np.float64)
    cc[0] = 0
    cc[1:] = np.cumsum(I)
    integral = np.interp(xo, x, cc)  # result is always float64
    ix = np.diff(integral)

    # Set proper return type, rounding to nearest integer for integral types.
    # This may add/remove counts if we hit exactly 0.5 on some bins.
    if dtype == np.float32:
        ix = np.asarray(ix, dtype=dtype)
    elif dtype != np.float64:
        ix = np.asarray(ix+0.5, dtype=dtype)

    return ix[::-1] if reverse_xo else ix


def rebin2d(x, y, I, xo, yo, dtype=np.float64):
    # type: (Sequence, Sequence, Sequence, Sequence, Sequence, Union[str, type]) -> np.ndarray
    """
    Rebin a matrix.

    x, y are the existing bin edges
    xo, yo are the new bin edges
    I is the existing counts (one fewer than edges in each direction)

    For example, with x representing the column edges in each row and
    y representing the row edges in each column, the following
    represents a uniform field::

        >>> from reductus.dataflow.lib.rebin import rebin2d
        >>> x, y = [0, 2, 4, 5], [0, 1, 3]
        >>> z = [[2, 2, 1], [4, 4, 2]]

    We can check this by rebinning with uniform size bins::

        >>> xo, yo = range(6), range(4)
        >>> rebin2d(y, x, z, yo, xo) # doctest: +SKIP
        array([[1., 1., 1., 1., 1.],
               [1., 1., 1., 1., 1.],
               [1., 1., 1., 1., 1.]])

    dtype is the type to use for the output intensity.  This can be
    integer (uint8, uint16, uint32) or real (float32 or f, float64 or d).
    The edge vectors are all coerced to doubles.  Default is the dtype
    of the input intensity.

    Note that total intensity is not preserved for integer rebinning.
    The algorithm uses truncation so total intensity will be down on
    average by half the total number of bins.
    """
    # Coerce inputs to arrays
    I = np.asarray(I)
    x, y, xo, yo = (np.asarray(v, dtype='d') for v in (x, y, xo, yo))
    shape_in = (x.shape[0]-1, y.shape[0]-1)
    if shape_in != I.shape or any(len(v.shape) != 1 for v in (x, y, xo, yo)):
        raise TypeError("input array incorrect shape %s"%str(I.shape))

    Io = _rebin_counts_2D(x, y, I, xo, yo, dtype=dtype)
    return Io


def _rebin_counts_2D(x, y, I, xo, yo, dtype):
    # type: (np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray) -> None

    # Arrange indices so they are ascending.
    # Slices are cheap---they don't make copies.
    if x[0] > x[-1]:
        x, I = x[::-1], I[::-1, :]
    if y[0] > y[-1]:
        y, I = y[::-1], I[:, ::-1]
    reverse_xo = xo[0] > xo[-1]
    if reverse_xo:
        xo = xo[::-1]
    reverse_yo = yo[0] > yo[-1]
    if reverse_yo:
        yo = yo[::-1]

    # Create a cumulative sum.  Use float64 for integers to minimize
    # overflow issues, even though it costs 2x in terms of space for int32.
    intermediate_dtype = np.float32 if dtype == np.float32 else np.float64
    csx = np.empty((len(x), len(y)-1), dtype=intermediate_dtype)
    csx[0, :] = 0
    csx[1:, :] = I
    np.cumsum(csx, out=csx, axis=0)

    xindices = np.interp(xo, x, np.arange(len(x)))  # result is float64
    xindices_whole = np.floor(xindices).astype(int)
    xindices_frac = np.fmod(xindices, 1.0)  # result is float64
    # The only way an index will match the highest bin edge is for lookups at
    # or outside the range of the source.  In this case the fractional portion
    # will always == 0.0, so clipping this to the bin edge below is safe and
    # allows us to use the source weights unmodified.
    xintegral = I[xindices_whole.clip(max=len(x)-2), :]  # result is I.dtype
    xintegral = np.asarray(xintegral, dtype=intermediate_dtype)  # int=>float
    xintegral *= xindices_frac[:, None]
    xintegral += csx[xindices_whole, :]
    del csx
    # rebinned over x
    ix = np.diff(xintegral, axis=0)
    # Note: inplace diff, which returns -delta in xintegral[0:-1], is only a
    # few percent faster, and is much more subject to implementation details
    # in the overlapping region, so don't use it.  Numpy 1.13 promises to
    # create a temporary for inplace operations on overlapping regions, so
    # the minor performance gains are likely to disappear anyway.
    #xintegral[:-1] -= xintegral[1:]
    #ix = xintegral[:-1]
    del xintegral

    csy = np.empty((len(xo)-1, len(y)), dtype=intermediate_dtype)
    csy[:, 0] = 0
    csy[:, 1:] = ix
    np.cumsum(csy, out=csy, axis=1)

    yindices = np.interp(yo, y, np.arange(len(y)))
    yindices_whole = np.floor(yindices).astype(int)
    yindices_frac = np.fmod(yindices, 1.0)
    yintegral = ix[:, yindices_whole.clip(max=len(y)-2)]
    # ix is already the correct dtype, so no need to change it
    yintegral *= yindices_frac[None, :]
    yintegral += csy[:, yindices_whole]
    del csy
    # rebinned over x and y
    ixy = np.diff(yintegral, axis=1)
    #yintegral[:-1] -= yintegral[1:]
    #ixy = yintegral[:-1]
    del yintegral

    if ixy.dtype != dtype:
        # If return type is float, then the intermediate type will be the
        # same float32/float64.  If the return type is integer then the
        # intermediate type will be float64 and needs to be converted to int.
        ixy = np.asarray(ixy+0.5, dtype=dtype)

    if reverse_xo:
        ixy = ixy[::-1, :]
    if reverse_yo:
        ixy = ixy[:, ::-1]
    return ixy


# ================ Test code ==================
def _check1d(from_bins, val, to_bins, target):
    """
    Test 1D rebinning *from_bins* => *to_bins* of counts *val* => *target*.

    The expected *target* must be precomputed in order to test that the right
    value is produced.

    Tests all combinations of increasing/decreasing source/target bin edges.

    Yields a sequence of test functions *t() -> None* which raise errors if
    the result is unexpected.  *t.description* is set to the name of the
    test variant so that nosetests will have slightly nicer error reporting.
    """
    target = np.asarray(target, dtype='d')
    for (f, F) in [(from_bins, val), (from_bins[::-1], val[::-1])]:
        for (t, T) in [(to_bins, target), (to_bins[::-1], target[::-1])]:
            test_name = "rebin %s->%s: %s->%s"%(f, t, F, T)
            def test():
                result = rebin(f, F, t)
                assert np.linalg.norm(T-result) < 1e-14, \
                    "rebin failed %s: %s "%(test_name, result)
            test.description = test_name
            yield test


def _test1d():
    # Split a value
    for t in _check1d([1, 2, 3, 4], [10, 20, 30],
                      [1, 2.5, 4], [20, 40]):
        t()

    # bin is a superset of rebin
    for t in _check1d([0, 1, 2, 3, 4], [5, 10, 20, 30],
                      [1, 2.5, 3], [20, 10]):
        t()

    # bin is a subset of rebin
    for t in _check1d([1, 2, 3, 4, 5, 6], [10, 20, 30, 40, 50],
                      [2.5, 3.5], [25]):
        t()

    # one bin to many
    for t in _check1d([1, 2, 3, 4, 5, 6], [10, 20, 30, 40, 50],
                      [2.1, 2.2, 2.3, 2.4], [2, 2, 2]):
        t()

    # many bins to one
    for t in _check1d([1, 2, 3, 4, 5, 6], [10, 20, 30, 40, 50],
                      [2.5, 4.5], [60]):
        t()


def _check2d(x, y, z, xo, yo, zo):
    # type: (Sequence, Sequence, Sequence, Sequence, Sequence, Sequence) -> None
    result = rebin2d(x, y, z, xo, yo)
    target = np.array(zo, dtype=result.dtype)
    assert result.dtype == target.dtype
    assert np.linalg.norm(target-result) < 1e-14, \
        "rebin2d failed for %s, %s->%s, %s\n%s\n%s" % (x, y, xo, yo, z, zo)


def _uniform_test(x, y):
    z = np.array([y], 'd') * np.array([x], 'd').T
    xedges = np.concatenate([(0, ), np.cumsum(x)])
    yedges = np.concatenate([(0, ), np.cumsum(y)])
    nx = int(np.round(xedges[-1]))
    ny = int(np.round(yedges[-1]))
    ox = np.arange(nx+1)
    oy = np.arange(ny+1)
    target = np.ones([nx, ny], 'd')
    return _check2d(xedges, yedges, z, ox, oy, target)


def _test2d():
    x, y, I = [0, 3, 5, 7], [0, 1, 3], [[3, 6], [2, 4], [2, 4]]
    xo, yo, Io = range(8), range(4), [[1]*3]*7
    x, y, I, xo, yo, Io = [np.array(A, 'd') for A in [x, y, I, xo, yo, Io]]

    # Try various types and orders on a non-square matrix
    _check2d(x, y, I, xo, yo, Io)
    _check2d(x[::-1], y, I[::-1, :], xo, yo, Io)
    _check2d(x, y[::-1], I[:, ::-1], xo, yo, Io)
    _check2d(x, y, I, [7, 3, 0], yo, [[4]*3, [3]*3])
    _check2d(x, y, I, xo, [3, 2, 0], [[1, 2]]*7)
    _check2d(y, x, I.T, yo, xo, Io.T)  # C vs. Fortran ordering

    # Test smallest possible result
    _check2d([-1, 2, 4], [0, 1, 3],
             [[3, 6], [2, 4]], [1, 2], [1, 2], [1])
    # subset/superset
    _check2d([0, 1, 2, 3], [0, 1, 2, 3],
             [[1]*3]*3, [0.5, 1.5, 2.5], [0.5, 1.5, 2.5], [[1]*2]*2)
    for dtype in ['uint8', 'uint16', 'uint32', 'uint64', 'float32', 'float64']:
        _check2d(
            [0, 1, 2, 3, 4], [0, 1, 2, 3, 4],
            np.array([[1]*4]*4, dtype=dtype),
            [-2, -1, 2, 5, 6], [-2, -1, 2, 5, 6],
            np.array([[0, 0, 0, 0], [0, 4, 4, 0], [0, 4, 4, 0], [0, 0, 0, 0]],
                      dtype=dtype)
            )
    # non-square test
    _uniform_test([1, 2.5, 4, 0.5], [3, 1, 2.5, 1, 3.5])
    _uniform_test([3, 2], [1, 2])


def test():
    _test1d()
    _test2d()


if __name__ == "__main__":
    test()
