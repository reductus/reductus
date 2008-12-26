"""
1-D and 2-D rebinning code.
"""
import numpy

from reflectometry.reduction import _reduction

def rebin(x,I,xo,Io=None):
    """
    Rebin a vector.

    x are the existing bin edges
    xo are the new bin edges
    I are the existing counts (one fewer than edges)

    Io will be used if present, but be sure that it is a contiguous
    array of the correct shape and size.
    """
    x,I,xo = [_input(v) for v in (x,I,xo)]
    Io = _output(Io,[len(xo)-1])
    _reduction.rebin(x,I,xo,Io)
    return Io

def rebin2d(x,y,I,xo,yo,Io=None):
    """
    Rebin a matrix.

    x,y are the existing bin edges
    xo,yo are the new bin edges
    I is the existing counts (one fewer than edges in each direction)

    Io will be used if present; this allows you to pass in a slice
    of an 3-D matrix, though it must be a contiguous slice for this
    to work.  Otherwise you can simply assign the return value of
    the rebinning to the slice and it will perform a copy.
    """
    x,y,I,xo,yo = [_input(v) for v in (x,y,I,xo,yo)]
    Io = _output(Io,[xo.shape[0]-1,yo.shape[0]-1])
    _reduction.rebin2d(x,y,I,xo,yo,Io)
    return Io

def _input(v, dtype='d'):
    """
    Force v to be a contiguous array of the correct type, avoiding copies
    if possible.
    """
    v = numpy.asarray(v,dtype=dtype)
    if not v.flags.contiguous:
        v = numpy.array(v,dtype=dtype)
    return v

def _output(v, shape, dtype=numpy.float64):
    """
    Create a contiguous array of the correct shape and type to hold a
    returned array, reusing an existing array if possible.
    """
    if v is None:
        return numpy.empty(shape,dtype=dtype)
    assert isinstance(v,numpy.ndarray) and v.dtype == dtype \
        and (v.shape == shape).all() and v.flags.contiguous,\
        "output vector must be contiguous %s of size %s"%(dtype,shape)
    return v


# ================ Test code ==================
# TODO: move test code to its own file
def _check1d(from_bins,val,to_bins,target):
    target = _input(target)
    for (f,F) in [(from_bins,val), (from_bins[::-1],val[::-1])]:
        for (t,T) in [(to_bins,target), (to_bins[::-1],target[::-1])]:
            result = rebin(f,F,t)
            assert numpy.linalg.norm(T-result) < 1e-14, \
                "rebin failed for %s->%s %s"%(f,t,result)

def _test1d():
    # Split a value
    _check1d([1,2,3,4],[10,20,30],[1,2.5,4],[20,40])

    # bin is a superset of rebin
    _check1d([0,1,2,3,4],[5,10,20,30],[1,2.5,3],[20,10]);

    # bin is a subset of rebin
    _check1d([ 1,   2,   3,   4,   5,  6],
             [   10,  20,  30,  40,  50],
             [ 2.5, 3.5], [25])

    # one bin to many
    _check1d([1,   2,   3,   4,   5,  6],
             [10,  20,  30,  40,  50],
             [2.1, 2.2, 2.3, 2.4 ],
             [2, 2, 2]);

    # many bins to one
    _check1d([1,   2,   3,   4,   5,  6],
             [10,  20,  30,  40,  50],
             [ 2.5, 4.5 ],
             [60])

def _check2d(x,y,z,xo,yo,zo):
    for (X,ZA) in [(x,z),(x[::-1],z[:,::-1])]:
        for (Y,Z) in [(y,ZA),(y[::-1],ZA[::-1,:])]:
            for (Xo,ZoA) in [(xo,zo),(xo[::-1],zo[:,::-1])]:
                for (Yo,Zo) in [(yo,ZoA),(yo[::-1],ZoA[::-1,:])]:
                    T = rebin2d(X,Y,Z,Xo,Yo)
                    assert numpy.linalg.norm(Zo-T) < 1e-14, \
                    "rebin2d failed for %s,%s->%s,%s\n%s\n%s\n%s"%(X,Y,Xo,Yo,Z,T,Zo)

def _uniform_test(x,y):
    z = numpy.array([x],'d') * numpy.array([y],'d').T
    xedges = numpy.concatenate([(0,),numpy.cumsum(x)])
    yedges = numpy.concatenate([(0,),numpy.cumsum(y)])
    nx = numpy.round(xedges[-1])
    ny = numpy.round(yedges[-1])
    ox = numpy.arange(nx+1)
    oy = numpy.arange(ny+1)
    target = numpy.ones([nx,ny],'d')
    _check2d(xedges,yedges,z,ox,oy,target)

def _nonuniform_test(x,y,z,ox,oy,oz):
    z,oz = _input(z),_input(oz)
    z = numpy.reshape(z,(len(x)-1,len(y)-1))
    oz = numpy.reshape(oz,(len(ox)-1,len(oy)-1))
    _check2d(x,y,z,ox,oy,oz)

def _test2d():
    _nonuniform_test([0,3,5], [0,1,3], [3,2,6,4],
                     [0,1,2,3,4,5], [0,1,2,3], [1]*15)
    # Test smallest possible result
    _nonuniform_test([-1,2,4], [0,1,3], [3,2,6,4],
                     [1,2], [1,2], [1])
    # subset/superset
    _nonuniform_test([0,1,2,3], [0,1,2,3], [1]*9,
                     [0.5,1.5,2.5], [0.5,1.5,2.5], [1]*4)
    _nonuniform_test([0,1,2,3,4], [0,1,2,3,4], [1]*16,
                     [-2,-1,2,5,6], [-2,-1,2,5,6],
                     [0,0,0,0,0,4,4,0,0,4,4,0,0,0,0,0])
    # non-square test
    _uniform_test([1,2.5,4,0.5],[3,1,2.5,1,3.5])
    _uniform_test([3,2],[1,2])

def test():
    _test2d()
    _test1d()

if __name__ == "__main__": test()
