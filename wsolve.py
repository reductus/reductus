import numpy as N

def wsolve(A,y,dy=1,rcond=1e-12):
    """
    Given a linear system y = A*x + e(dy), estimates x,dx
    """
    # The ugliness v[:,N.newaxis] is a vector transpose
    # The ugliness N.dot(a,b) is a*b for a,b matrices
    # The ugliness vh.T.conj() is the hermitian transpose

    # Apply weighting
    A, y = (1/dy)[:,N.newaxis]*N.array(A), (1/dy)*y

    # Singular value decomposition: A = U S V.H
    u,s,vh = N.linalg.svd(A,0)
    # FIXME what to do with illconditioned systems?
    if (s<rcond*s[0]).any(): raise ValueError, "matrix is singular"
    #s[s<rcond*s[0]] = 0.

    # Solve: x = V inv(S) U.H y
    # S diagonal elements => 1/S is inv(S)
    x = N.dot(N.dot(vh.T.conj(),(1/s)[:,N.newaxis]*u.T.conj()), y)
    # covariance matrix A'A is VSSV'
    # inv(A'A)  is V inv(S)**2 V'
    # diag(inv(A'A)) is sumsq(inv(S) V')
    dx = N.sqrt(N.sum( ((1/s)[:,N.newaxis]*N.array(vh))**2 ))
    return x,dx

def wpolyfit(x,y,dy=1,n=1,origin=False):
    """
    Return the coefficients of a polynomial p(x) of degree n that
    minimizes sum( (p(x_i) - y_i)**2/dy_i**2).

    dy, if present, gives the standard error of the observations.
    if origin is True, the fit should go through the origin.
    """
    if origin:
        A = N.vstack(x**k for k in range(n,0,-1))
    else:
        A = N.vstack(x**k for k in range(n,-1,-1))

    p,dp = wsolve(A.T,y,dy)
    if origin:
        p.append(0)
    return p,dp

def demo1():
    import pylab
    
    # Make fake data
    x = N.linspace(-15,5,15)
    th = N.polyval([.2,3,1,5],x)  # polynomial
    dy = N.sqrt(N.abs(th))       # poisson uncertainty estimate
    y = N.random.normal(th,dy)   # but normal generator

    # Fit to a polynomial
    p,dp = wpolyfit(x,y,dy,3)

    # Plot the result
    pylab.errorbar(x,y,yerr=dy,fmt='x')
    pylab.hold(True)
    px=N.linspace(x[0],x[-1],200)
    pylab.plot(px,N.polyval(p,px))
    pylab.show()

if __name__ == "__main__": demo1()
