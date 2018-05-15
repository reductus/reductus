import numpy as np

def rebin_counts_broadcast(x, I, xo, Io, ND_portion=1.0):
    """
    Identify overlaps in bin edges and rebin
    Assumes both x and xo are sorted in increasing order.
    """
    # overlap map (MxN), where M is input size(x) and N is output size (xo):
    overlap = (np.minimum(xo[None, 1:], x[1:, None])
               - np.maximum(xo[None, :-1], x[:-1, None])).clip(min=0.0)
    portion = overlap / (x[1:] - x[:-1])[:, None]
    Io += np.sum(I[:, None] * ND_portion * portion, axis=0)

def rebin_counts_portion_transfer(x, I, xo, Io, ND_portion=1.0):
    """
    Identify overlaps in bin edges and rebin
    Assumes both x and xo are sorted in increasing order.
    """

    # overlap map (MxN), where M is input size(x) and N is output size (xo):
    overlap = (np.minimum(xo[None, 1:], x[1:, None])
               - np.maximum(xo[None, :-1], x[:-1, None])) #.clip(min=0.0)
    mask = (overlap > 0)
    xi, xoi = np.indices(overlap.shape)
    inlist = xi[mask]
    outlist = xoi[mask]
    weights = (overlap * I[:, None] * ND_portion / (x[1:] - x[:-1])[:, None])[mask]
    hist, bins = np.histogram(outlist, bins=np.arange(Io.shape[0]+1), weights=weights)
    Io += hist

def rebin_counts_portion(x, I, xo, Io, ND_portion=1.0):
    # use this one for 1D: very fast.
    cc = np.empty_like(x)
    cc[0] = 0.0
    cc[1:] = np.cumsum(I*ND_portion)
    integral = np.interp(xo, x, cc)
    Io += np.diff(integral)

def rebin_counts(x, I, xo, Io):
    input_direction = np.sign(x[-1] - x[0])
    output_direction = np.sign(xo[-1] - xo[0])
    input_slice = slice(None, None, int(input_direction))
    output_slice = slice(None, None, int(output_direction))

    Io[:] = 0.0
    rebin_counts_portion(x[input_slice], I[input_slice], xo[output_slice], Io[output_slice], ND_portion=1.0)

def rebin_counts_2D_bruteforce(x, y, I, xo, yo, Io):

    xoverlap = (np.minimum(xo[None, 1:], x[1:, None]) - np.maximum(xo[None, :-1], x[:-1, None])).clip(min=0.0)
    xportion = xoverlap / (x[1:] - x[:-1])[:, None]
    yoverlap = (np.minimum(yo[None, 1:], y[1:, None]) - np.maximum(yo[None, :-1], y[:-1, None])).clip(min=0.0)
    yportion = yoverlap / (y[1:] - y[:-1])[:, None]

    weighted_overlap = I[:, None, :, None] * xportion[:, :, None, None] * yportion[None, None, :, :]
    Io += np.sum(np.sum(weighted_overlap, axis=0), axis=1)

def rebin_counts_2D_indexing(x, y, I, xo, yo, Io):
    output = np.empty_like(Io)
    csx = np.empty((len(x), len(y)-1))
    ix = np.empty((len(xo)-1, len(y)-1))
    csx[0, :] = 0.0
    csx[1:, :] = np.cumsum(I, axis=0)
    for i in range(len(y)-1):
        integral = np.interp(xo, x, csx[:, i])
        # integral has shape (len(xo),)
        ix[:, i] = np.diff(integral)
        # ix[:,i] has shape (len(xo)-1,)
        # np.diff(integral) has shape(len(xo)-1,)

    csy = np.empty((len(xo)-1, len(y)))
    # shape is (len(xo)-1, len(y)-1)
    csy[:, 0] = 0.0
    csy[:, 1:] = np.cumsum(ix, axis=1)
    for j in range(len(xo)-1):
        integral = np.interp(yo, y, csy[j, :])
        # has shape (len(yo),)
        output[j, :] = np.diff(integral)
        # output[j, :] has shape (len(yo)-1)

    Io += output

def rebin_counts_2D_indexing_new(x, y, I, xo, yo, Io):
    # use this one for 2D.
    csx = np.empty((len(x), len(y)-1))
    csx[0, :] = 0.0
    csx[1:, :] = np.cumsum(I, axis=0)

    xindices = np.interp(xo, x, np.arange(len(x), dtype='float'))
    xindices_whole = np.floor(xindices).astype(int)
    xindices_frac = np.fmod(xindices, 1.0)
    # the only way an index will match the highest bin edge is for lookups at or outside the range of the
    # source.  In this case the fractional portion will always == 0.0, so clipping this to the bin edge below
    # is safe and allows us to use the source weights unmodified
    xintegral = csx[xindices_whole, :] + I[xindices_whole.clip(max=len(x)-2), :]*xindices_frac[:, None]
    # rebinned over x
    ix = np.diff(xintegral, axis=0)

    csy = np.empty((len(xo)-1, len(y)))
    csy[:, 0] = 0.0
    csy[:, 1:] = np.cumsum(ix, axis=1)

    yindices = np.interp(yo, y, np.arange(len(y), dtype='float'))
    yindices_whole = np.floor(yindices).astype(int)
    yindices_frac = np.fmod(yindices, 1.0)
    yintegral = csy[:, yindices_whole] + ix[:, yindices_whole.clip(max=len(y)-2)]*yindices_frac[None, :]
    # rebinned over x and y
    ixy = np.diff(yintegral, axis=1)

    Io += ixy

def rebin_counts_2D_indexing_newer(x, y, I, xo, yo, Io):
    # use this one for 2D.
    csx = np.empty((len(x), len(y)-1))
    csx[0, :] = 0.0
    csx[1:, :] = I
    np.cumsum(csx, out=csx, axis=0)

    xindices = np.interp(xo, x, np.arange(len(x), dtype='float'))
    xindices_whole = np.floor(xindices).astype(int)
    xindices_frac = np.fmod(xindices, 1.0)
    # the only way an index will match the highest bin edge is for lookups at or outside the range of the
    # source.  In this case the fractional portion will always == 0.0, so clipping this to the bin edge below
    # is safe and allows us to use the source weights unmodified
    xintegral = I[xindices_whole.clip(max=len(x)-2), :]
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

    csy = np.empty((len(xo)-1, len(y)))
    csy[:, 0] = 0.0
    csy[:, 1:] = ix
    np.cumsum(csy, out=csy, axis=1)

    yindices = np.interp(yo, y, np.arange(len(y), dtype='float'))
    yindices_whole = np.floor(yindices).astype(int)
    yindices_frac = np.fmod(yindices, 1.0)
    yintegral = ix[:, yindices_whole.clip(max=len(y)-2)]
    yintegral *= yindices_frac[None, :]
    yintegral += csy[:, yindices_whole]
    del csy
    # rebinned over x and y
    ixy = np.diff(yintegral, axis=1)
    #yintegral[:-1] -= yintegral[1:]
    #ixy = yintegral[:-1]

    Io += ixy
    
def rebin_counts_2D(x, y, I, xo, yo, Io): 
    x_input_direction = np.sign(x[-1] - x[0])
    y_input_direction = np.sign(y[-1] - y[0])
    x_output_direction = np.sign(xo[-1] - xo[0])
    y_output_direction = np.sign(yo[-1] - yo[0])
    
    x_s = slice(None, None, int(x_input_direction))
    y_s = slice(None, None, int(y_input_direction))
    xo_s = slice(None, None, int(x_output_direction))
    yo_s = slice(None, None, int(y_output_direction))
    
    Io[:] = 0
    rebin_counts_2D_indexing_newer(x[x_s], y[y_s], I[x_s, y_s], xo[xo_s], yo[yo_s], Io[xo_s, yo_s])

def test(sizex=101):
    sizexo = int(sizex/2)
    x = np.linspace(0.0, 100.0, sizex)
    xo = np.linspace(0.0, 110.0, sizexo)
    I = np.ones((sizex-1,), dtype="float")
    Io = np.zeros((sizexo-1,), dtype="float")

    rebin_counts_portion(x, I, xo, Io)
    return Io

def test_c(sizex=101):
    from . import rebin
    sizexo = int(sizex/2)
    x = np.linspace(0.0, 100.0, sizex)
    xo = np.linspace(0.0, 110.0, sizexo)
    I = np.ones((sizex-1,), dtype="float")
    Io = np.zeros((sizexo-1,), dtype="float")

    rebin.rebin(x, I, xo, Io)
    return Io

def test2D(sizex=101, sizey=75):
    sizexo = int(sizex/2)
    sizeyo = int(sizey/2)
    x = np.linspace(5.0, 100.0, sizex)
    xo = np.linspace(0.0, 110.0, sizexo)
    y = np.linspace(5.0, 50.0, sizey)
    yo = np.linspace(0.0, 60.0, sizeyo)
    I = np.ones((sizex-1, sizey-1), dtype="float")
    Io = np.zeros((sizexo-1, sizeyo-1), dtype="float")

    rebin_counts_2D_indexing_new(x, y, I, xo, yo, Io)
    return I, Io

def test2D_newer(sizex=101, sizey=75):
    sizexo = int(sizex/2)
    sizeyo = int(sizey/2)
    x = np.linspace(5.0, 100.0, sizex)
    xo = np.linspace(0.0, 110.0, sizexo)
    y = np.linspace(5.0, 50.0, sizey)
    yo = np.linspace(0.0, 60.0, sizeyo)
    I = np.ones((sizex-1, sizey-1), dtype="float")
    #Io = np.zeros((sizexo-1, sizeyo-1), dtype="float")

    Io = rebin_counts_2D_indexing_newer(x, y, I, xo, yo)
    return I, Io

def test2D_c(sizex=101, sizey=75):
    from . import rebin
    sizexo = int(sizex/2)
    sizeyo = int(sizey/2)
    x = np.linspace(5.0, 100.0, sizex)
    xo = np.linspace(0.0, 110.0, sizexo)
    y = np.linspace(5.0, 50.0, sizey)
    yo = np.linspace(0.0, 60.0, sizeyo)
    I = np.ones((sizex-1, sizey-1), dtype="float")
    Io = np.zeros((sizexo-1, sizeyo-1), dtype="float")

    Io = rebin.rebin2d(x, y, I, xo, yo)
    return I, Io
