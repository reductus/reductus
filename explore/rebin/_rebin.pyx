cimport cython

cdef extern from "rebin.h":
    cdef void rebin_counts[T](
        const size_t Nold, const double xold[], const T Iold[],
        const size_t Nnew, const double xnew[], T Inew[]) nogil
cdef extern from "rebin2D.h":
    cdef void rebin_counts_2D[T](
        const size_t Nxold, const double xold[],
        const size_t Nyold, const double yold[], const T Iold[],
        const size_t Nxnew, const double xnew[],
        const size_t Nynew, const double ynew[], T Inew[]) nogil

ctypedef fused scalar:
    cython.uchar
    cython.ushort
    cython.uint
    cython.ulong
    cython.char
    cython.short
    cython.int
    cython.long
    cython.float
    cython.double

def rebin_counts_wrapper(double[:] x, scalar[:] I, double[:] xo, scalar[:] Io):
    rebin_counts(x.size-1, &x[0], &I[0], xo.size-1, &xo[0], &Io[0])

def rebin_counts_2D_wrapper(double[:] x, double[:] y, scalar[:,:] I,
                             double[:] xo, double[:] yo, scalar[:,:] Io):
    rebin_counts_2D(x.size-1, &x[0], y.size-1, &y[0], &I[0,0],
                    xo.size-1, &xo[0], yo.size-1, &yo[0], &Io[0,0])
