"""
Solve a potentially over-determined system with uncertainty in
the values.

Given: A x = y +/- dy
Use:   s = wsolve(A,y,dy)

wsolve uses the singular value decomposition for increased accuracy.
Estimates the uncertainty for the solution from the scatter in the data.

The returned object s provides:

    s.x      solution
    s.std    uncertainty estimate assuming no correlation
    s.rnorm  residual norm
    s.DoF    degrees of freedom
    s.cov    covariance matrix
    s.ci(x)  confidence intervals computed at x
    s.pi(x)  prediction intervals computed at x

Example: weighted system

import numpy,wsolve
A = numpy.matrix("1,2,3;2,1,3;1,1,1",'d').A
xin = numpy.array([1,2,3],'d')
dy = numpy.array([0.2,0.01,0.1])
y = numpy.random.normal(numpy.dot(A,xin),dy)
print A,y,dy
s = wsolve.wsolve(A,y,dy)
print "xin,x,dx", xin, s.x, s.std

Note there is a counter-intuitive result that scaling the
uncertainty in the data does not affect the uncertainty in
the fit.  Indeed, if you perform a monte carlo simulation
with x,y datasets selected from a normal distribution centered
on y with width 10*dy instead of dy you will see that the
variance in the parameters indeed increases by a factor of 100.
However, if the error bars really do increase by a factor of 10
you should expect a corresponding increase in the scatter of
the data, which will increase the variance computed by the fit,
so indeed the dataset carries its own information about the
variance of the data, with the weight vector serving only to
provide relative weighting between the points.
"""

# FIXME: test second example
#
# Example 2: weighted overdetermined system  y = x1 + 2*x2 + 3*x3 + e
#
#    A = fullfact([3,3,3]); xin=[1;2;3];
#    y = A*xin; dy = rand(size(y))/50; y+=dy.*randn(size(y));
#    [x,s] = wsolve(A,y,dy);
#    dx = s.normr*sqrt(sumsq(inv(s.R'))'/s.df);
#    res = [xin, x, dx]


import numpy as N

class Confidence(object):
    """
    Confidence object returned from linear solver.

    Stored properties:
    DoF = len(y)-len(x) = degrees of freedom
    rnorm = 2-norm of the residuals y-Ax
    x = solution to the equation Ax = y

    Computed properties:
    cov = covariance matrix [ inv(A'A); O(n^3) ]
    var = parameter variance [ diag(cov); O(n^2)]
    std = standard deviation of parameters [ sqrt(var); O(n^2) ]
    p = test statistic for chisquare goodness of fit [ chi2.sf; O(1) ]

    Methods:
    ci(A,sigma=1):  return confidence interval evaluated at A
    pi(A,alpha=0.05):  return prediction interval evaluated at A
    """
    def __init__(self, x=None, DoF=None, SVinv=None, rnorm=None):
        """

        """
        # V,S where USV' = A
        self.x = x
        self.DoF = DoF
        self.rnorm = rnorm
        self._SVinv = SVinv

    # covariance matrix invC = A'A  = (USV')'USV' = VSU'USV' = VSSV'
    # C = inv(A'A) = inv(VSSV') = inv(V')inv(SS)inv(V) = Vinv(SS)V'
    # diag(inv(A'A)) is sum of the squares of the columns inv(S) V'
    # and is also the sum of the squares of the rows of V inv(S)
    def _cov(self):
        # FIXME: don't know if we need to scale by C, but it will
        # at least make things consistent
        C = self.rnorm**2/self.DoF if self.DoF>0 else 1
        return C * N.dot(self._SVinv,self._SVinv.T)
    def _var(self):
        C = self.rnorm**2/self.DoF if self.DoF>0 else 1
        return C * N.sum( self._SVinv**2, axis=1)
    def _std(self):
        return N.sqrt(self._var())
    def _p(self):
        from scipy import stats
        return stats.chi2.sf(self.rnorm**2,self.DoF)

    cov = property(_cov,doc="covariance matrix")
    var = property(_var,doc="result variance")
    std = property(_std,doc="result standard deviation")
    p = property(_p,doc="probability of rejection")

    def _interval(self,A,alpha,pred):
        """
        Helper for computing prediction/confidence intervals.
        """
        from scipy import stats
        y = N.dot(A,self.x)
        s = stats.t.ppf(1-alpha/2,self.DoF)*S.normr/sqrt(self.DoF)
        dy = s*sqrt(pred+N.sum( (N.dot(self.invR,A))**2, axis=0))
        return y,dy

    def ci(self, A, sigma=1):
        """
        Compute the calculated values and the confidence intervals
        for the linear model evaluated at A.

        sigma=1 corresponds to a 1-sigma confidence interval
        """
        print "wsolve.Confidence.ci is not yet tested"
        alpha = erfc(sigma/sqrt(2))
        return _interval(A,alpha,0)

    def pi(self, A, p=0.05):
        """
        Compute the calculated values and the prediction intervals
        for the linear model evaluated at A.

        p = 1-alpha = 0.05 corresponds to 95% prediction interval
        """
        print "wsolve.Confidence.pi is not yet tested"
        return _interval(A,p,1)

def wsolve(A,y,dy=1,rcond=1e-12):
    """
    Given a linear system y = A*x + e(dy), estimates x,dx

    A is an n x m array
    y is an n x k array or vector of length n
    dy is a scalar or an n x 1 array
    x is a m x k array
    """
    # The ugliness v[:,N.newaxis] transposes a vector
    # The ugliness N.dot(a,b) is a*b for a,b matrices
    # The ugliness vh.T.conj() is the hermitian transpose

    # Make sure inputs are arrays
    A,y,dy = N.array(A),N.array(y),N.array(dy)
    result_dims = y.ndim
    if dy.ndim == 1: dy = dy[:,N.newaxis]
    if y.ndim == 1: y = y[:,N.newaxis]

    # Apply weighting if dy is not a scalar
    # If dy is a scalar, it cancels out of both sides of the equation
    # Note: with A,dy arrays instead of matrices, A/dy operates element-wise
    # Since dy is a row vector, this divides each row of A by the corresponding
    # element of dy.
    if dy.ndim == 2:  A,y = A/dy,y/dy

    # Singular value decomposition: A = U S V.H
    # Since A is an array, U, S, VH are also arrays
    # The zero indicates an economy decomposition, with u nxm rathern than nxn
    u,s,vh = N.linalg.svd(A,0)

    # FIXME what to do with ill-conditioned systems?
    #if s[-1]<rcond*s[0]: raise ValueError, "matrix is singular"
    #s[s<rcond*s[0]] = 0.  # Can't do this because 1/s below will fail

    # Solve: x = V inv(S) U.H y
    # S diagonal elements => 1/S is inv(S)
    # A*D, D diagonal multiplies each column of A by the corresponding diagonal
    # D*A, D diagonal multiplies each row of A by the corresponding diagonal
    # Computing V*inv(S) is slightly faster than inv(S)*U.H since V is smaller
    # than U.H.  Similarly, U.H*y is somewhat faster than V*U.H
    SVinv = vh.T.conj()/s
    Uy = N.dot(u.T.conj(), y)
    x = N.dot(SVinv, Uy)

    DoF = y.shape[0] - x.shape[0]
    rnorm = N.linalg.norm(y - N.dot(A,x))

    return Confidence(x=x, DoF=DoF, SVinv=SVinv, rnorm=rnorm)

def wpolyfit(x,y,dy=1,deg=None,origin=False):
    """
    Return the coefficients of a polynomial p(x) of degree n that
    minimizes sum( (p(x_i) - y_i)**2/dy_i**2).

    if origin is True, the fit should go through the origin.
    """
    assert deg != None, "Missing degree argument to wpolyfit"
    if origin:
        A = N.vstack(x**k for k in range(deg,0,-1))
    else:
        A = N.vstack(x**k for k in range(deg,-1,-1))

    s = wsolve(A.T,y,dy)
    p,dp = N.ravel(s.x),N.ravel(s.std)
    if origin:
        p = N.hstack((p,0))
        dp = N.hstack((dp,0))
    return p,dp

def demo():
    import pylab

    # Make fake data
    x = N.linspace(-15,5,15)
    th = N.polyval([.2,3,1,5],x)  # polynomial
    dy = N.sqrt(N.abs(th))       # poisson uncertainty estimate
    y = N.random.normal(th,dy)   # but normal generator

    # Fit to a polynomial
    p,dp = wpolyfit(x,y,dy=dy,deg=3)

    # Plot the result
    pylab.errorbar(x,y,yerr=dy,fmt='x')
    pylab.hold(True)
    px=N.linspace(x[0],x[-1],200)
    pylab.plot(px,N.polyval(p,px))
    pylab.show()

def test():
    """
    smoke test...make sure the function continues to return the same
    result for a particular system.
    """
    x = N.array([0,1,2,3,4],'d')
    y = N.array([  2.5,   7.9,  13.9,  21.1,  44.4],'d')
    dy = N.array([ 1.7,  2.4,  3.6,  4.8,  6.2],'d')
    p,dp = wpolyfit(x,y,dy,1)

    #print "Tp = [%.16g, %.16g]"%(p[0],p[1])
    #print "Tdp = [%.16g, %.16g]"%(dp[0],dp[1])
    Tp = N.array([7.787249069840737, 1.503992847461524])
    Tdp = N.array([1.522338103010216, 2.117633626902384])

    perr = N.max(N.abs(p-Tp))
    dperr = N.max(N.abs(dp-Tdp))
    assert  perr < 1e-15,"||p-Tp||=%g"%perr
    assert  dperr < 1e-15,"||dp-Tdp||=%g"%dperr

if __name__ == "__main__":
    test()
#    demo()
