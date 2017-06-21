import numpy as np

def rebin_counts_portion(x, I, xo, Io, ND_portion=1.0):
    """ 
    Identify overlaps in bin edges and rebin 
    Assumes both x and xo are sorted in increasing order.
    """
    
    # overlap map (MxN), where M is input size(x) and N is output size (xo):
    overlap = np.minimum(xo[None, 1:], x[1:, None]) - np.maximum(xo[None, :-1], x[:-1, None])
    non_overlap = (overlap < 0.0)
    overlap[non_overlap] = 0.0
    portion = overlap / (x[1:] - x[:-1])[:,None]
    Io += np.sum(I[:, None] * ND_portion * portion, axis=0)
   
def rebin_counts(x, I, xo, Io):
    Io[:] = 0.0
    rebin_counts_portion(x, I, xo, Io, ND_portion=1.0)
    

def test():
    x = np.arange(0,10,2)
    xo = np.arange(0,11,1)
    I = np.ones((4,))
    Io = np.zeros((10,))
    
    rebin_counts_portion(x, I, xo, Io)
    
