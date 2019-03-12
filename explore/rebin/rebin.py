"""
1-D and 2-D rebinning code.
"""
import numpy as np

try:
    from . import _reduction  ## C API wrapper
    #from . import _rebin  ## cython wrapper
except ImportError:
    import warnings
    warnings.warn("Reduction module not compiled...rebinning unavailable")

try:
    #from typing import Sequence, Optional, Union
    pass
except ImportError:
    pass

def rebin(x, I, xo, Io=None, dtype=np.float64):
    # type: (Sequence, Sequence, Sequence, Optional[np.ndarray], Union[str, type]) -> np.ndarray
    """
    Rebin a vector.

    x are the existing bin edges
    xo are the new bin edges
    I are the existing counts (one fewer than edges)

    Io will be used if present, but be sure that it is a contiguous
    array of the correct shape and size.

    dtype is the type to use for the intensity vectors.  This can be
    integer (uint8, uint16, uint32) or real (float32 or f, float64 or d).
    The edge vectors are all coerced to doubles.

    Note that total intensity is not preserved for integer rebinning.
    The algorithm uses truncation so total intensity will be down on
    average by half the total number of bins.
    """
    from .rebin_python import rebin_counts
    # Coerce axes to float arrays
    x, xo = _input(x, dtype='d'), _input(xo, dtype='d')
    shape_in = np.array([x.shape[0]-1])
    shape_out = np.array([xo.shape[0]-1])

    # Coerce counts to correct type and check shape
    if dtype is None:
        dtype = getattr(I, 'dtype', np.float64)
    I = _input(I, dtype=dtype)
    if shape_in != I.shape:
        raise TypeError("input array incorrect shape %s"%I.shape)

    # Create output vector
    Io = _output(Io, shape_out, dtype=dtype)

    rebin_counts(x, I, xo, Io)
    return Io

def rebin2d(x, y, I, xo, yo, Io=None, dtype=None):
    # type: (Sequence, Sequence, Sequence, Sequence, Sequence, Optional[np.ndarray], Union[str, type]) -> np.ndarray
    """
    Rebin a matrix.

    x, y are the existing bin edges
    xo, yo are the new bin edges
    I is the existing counts (one fewer than edges in each direction)

    For example, with x representing the column edges in each row and
    y representing the row edges in each column, the following
    represents a uniform field::

        >>> from reflred.rebin import rebin2d
        >>> x, y = [0, 2, 4, 5], [0, 1, 3]
        >>> z = [[2, 2, 1], [4, 4, 2]]

    We can check this by rebinning with uniform size bins::

        >>> xo, yo = range(6), range(4)
        >>> rebin2d(y, x, z, yo, xo)
        array([[ 1.,  1.,  1.,  1.,  1.],
               [ 1.,  1.,  1.,  1.,  1.],
               [ 1.,  1.,  1.,  1.,  1.]])

    dtype is the type to use for the intensity vectors.  This can be
    integer (uint8, uint16, uint32) or real (float32 or f, float64 or d).
    The edge vectors are all coerced to doubles.

    Note that total intensity is not preserved for integer rebinning.
    The algorithm uses truncation so total intensity will be down on
    average by half the total number of bins.

    Io will be used if present, if it is contiguous and if it has the
    correct shape and type for the input.  Otherwise it will raise a
    TypeError.  This will allow you to rebin the slices of an appropriately
    ordered matrix without making copies.
    """
    from .rebin_python import rebin_counts_2D
    # Coerce axes to float arrays
    x, y, xo, yo = [_input(v, dtype='d') for v in (x, y, xo, yo)]
    shape_in = np.array([x.shape[0]-1, y.shape[0]-1])
    shape_out = np.array([xo.shape[0]-1, yo.shape[0]-1])

    # Coerce counts to correct type and check shape
    if dtype is None:
        dtype = getattr(I, 'dtype', np.float64)
    I = _input(I, dtype=dtype)
    if (shape_in != I.shape).any():
        raise TypeError("input array incorrect shape %s"%str(I.shape))

    # Create output vector
    Io = _output(Io, shape_out, dtype=dtype)

    rebin_counts_2D(x, y, I, xo, yo, Io)
    return Io

def _input(v, dtype='d'):
    # type: Sequence -> np.ndarray
    """
    Force v to be a contiguous array of the correct type, avoiding copies
    if possible.
    """
    return np.ascontiguousarray(v, dtype=dtype)

def _output(v, shape, dtype=np.float64):
    """
    Create a contiguous array of the correct shape and type to hold a
    returned array, reusing an existing array if possible.
    """
    if v is None:
        return np.empty(shape, dtype=dtype)
    if not (isinstance(v, np.ndarray)
            and v.dtype == np.dtype(dtype)
            and v.shape == shape
            and v.flags.contiguous):
        raise TypeError("output vector must be contiguous %s of size %s"
                        %(dtype, shape))
    return v


# ================ Test code ==================
# TODO: move test code to its own file
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
    target = _input(target)
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
    for t in _check1d([1, 2, 3, 4], [10, 20, 30], [1, 2.5, 4], [20, 40]):
        yield t

    # bin is a superset of rebin
    for t in _check1d([0, 1, 2, 3, 4], [5, 10, 20, 30], [1, 2.5, 3], [20, 10]):
        yield t

    # bin is a subset of rebin
    for t in _check1d([1, 2, 3, 4, 5, 6], [10, 20, 30, 40, 50], [2.5, 3.5], [25]):
        yield t

    # one bin to many
    for t in _check1d([1, 2, 3, 4, 5, 6], [10, 20, 30, 40, 50], [2.1, 2.2, 2.3, 2.4], [2, 2, 2]):
        yield t

    # many bins to one
    for t in _check1d([1, 2, 3, 4, 5, 6], [10, 20, 30, 40, 50], [2.5, 4.5], [60]):
        yield t

def _check2d(x, y, z, xo, yo, zo):
    # type: (Sequence, Sequence, Sequence, Sequence, Sequence, Sequence) -> None
    result = rebin2d(x, y, z, xo, yo)
    target = np.array(zo, dtype=result.dtype)
    assert np.linalg.norm(target-result) < 1e-14, \
        "rebin2d failed for %s, %s->%s, %s\n%s\n%s" % (x, y, xo, yo, z, zo)

def _uniform_test(x, y):
    z = np.array([y], 'd') * np.array([x], 'd').T
    xedges = np.concatenate([(0, ), np.cumsum(x)])
    yedges = np.concatenate([(0, ), np.cumsum(y)])
    nx = np.round(xedges[-1])
    ny = np.round(yedges[-1])
    ox = np.arange(nx+1)
    oy = np.arange(ny+1)
    target = np.ones([nx, ny], 'd')
    return _check2d(xedges, yedges, z, ox, oy, target)

def _test2d():
    x, y, I = [0, 3, 5, 7], [0, 1, 3], [[3, 6], [2, 4], [2, 4]]
    xo, yo, Io = range(8), range(4), [[1]*3]*7
    x, y, I, xo, yo, Io = [np.array(A, 'd') for A in [x, y, I, xo, yo, Io]]

    # Try various types and orders on a non-square matrix
    yield lambda: _check2d(x, y, I, xo, yo, Io)
    yield lambda: _check2d(x[::-1], y, I[::-1, :], xo, yo, Io)
    yield lambda: _check2d(x, y[::-1], I[:, ::-1], xo, yo, Io)
    yield lambda: _check2d(x, y, I, [7, 3, 0], yo, [[4]*3, [3]*3])
    yield lambda: _check2d(x, y, I, xo, [3, 2, 0], [[1, 2]]*7)
    yield lambda: _check2d(y, x, I.T, yo, xo, Io.T)  # C vs. Fortran ordering

    # Test smallest possible result
    yield lambda: _check2d([-1, 2, 4], [0, 1, 3],
                           [[3, 6], [2, 4]], [1, 2], [1, 2], [1])
    # subset/superset
    yield lambda: _check2d([0, 1, 2, 3], [0, 1, 2, 3],
                           [[1]*3]*3, [0.5, 1.5, 2.5], [0.5, 1.5, 2.5], [[1]*2]*2)
    #for dtype in ['uint8', 'uint16', 'uint32', 'uint64', 'float32', 'float64']:
    #    yield lambda: _check2d(
    #        [0, 1, 2, 3, 4], [0, 1, 2, 3, 4],
    #        np.array([[1]*4]*4, dtype=dtype),
    #        [-2, -1, 2, 5, 6], [-2, -1, 2, 5, 6],
    #        np.array([[0, 0, 0, 0], [0, 4, 4, 0], [0, 4, 4, 0], [0, 0, 0, 0]], dtype=dtype)
    #        )
    # non-square test
    #yield lambda: _uniform_test([1, 2.5, 4, 0.5], [3, 1, 2.5, 1, 3.5])
    #yield lambda: _uniform_test([3, 2], [1, 2])

def test():
    for t in _test1d(): yield t
    for t in _test2d(): yield t

def main():
    for t in test(): t()

if __name__ == "__main__":
    main()
