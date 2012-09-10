"""
Solve a potentially over-determined system with uncertainty in
the values.

Given: A x = y +/- dy
Use:   s = wsolve(A,y,dy)

wsolve uses the singular value decomposition for increased accuracy.
Estimates the uncertainty for the solution from the scatter in the data.

The returned model object s provides:

    s.x      solution
    s.std    uncertainty estimate assuming no correlation
    s.rnorm  residual norm
    s.DoF    degrees of freedom
    s.cov    covariance matrix
    s.ci(p)  confidence intervals at point p
    s.pi(p)  prediction intervals at point p
    s(p)     predicted value at point p

Example
=======

Weighted system::

    import numpy,wsolve
    A = numpy.matrix("1,2,3;2,1,3;1,1,1",'d').A
    xin = numpy.array([1,2,3],'d')
    dy = numpy.array([0.2,0.01,0.1])
    y = numpy.random.normal(numpy.dot(A,xin),dy)
    print A,y,dy
    s = wsolve.wsolve(A,y,dy)
    print "xin,x,dx", xin, s.x, s.std

Note there is a counter-intuitive result that scaling the estimated
uncertainty in the data does not affect the computed uncertainty in
the fit.  This is the correct result --- if the data were indeed
selected from a process with ten times the uncertainty, you would
expect the scatter in the data to increase by a factor of ten as
well.  When this new data set is fitted, it will show a computed
uncertainty increased by the same factor.  Monte carlo simulations
bear this out.  The conclusion is that the dataset carries its own
information about the variance in the data, and the weight vector
serves only to provide relative weighting between the points.
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


import numpy as np

# Grab erfc from scipy if it is available; if not then we can only
# calculate confidence intervals for sigma = 1
try:
    from scipy import stats
    from scipy.special import erfc
except:
    # If scipy is missing we will not be able to calculate confidence
    # intervals or prediction intervals.
    pass

class LinearModel(object):
    """
    Model evaluator for linear solution to Ax = y.

    Computes a confidence interval (range of likely values for the
    mean at x) or a prediction interval (range of likely values
    seen when measuring at x).  The prediction interval tells
    you the width of the distribution at x.  This should be the same
    regardless of the number of measurements you have for the value
    at x.  The confidence interval tells you how well you know the
    mean at x.  It should get smaller as you increase the number of
    measurements.  Error bars in the physical sciences usually show
    a 1-alpha confidence value of erfc(1/sqrt(2)), representing
    a 1 sigma standandard deviation of uncertainty in the mean.

    Confidence intervals for linear system are given by::

        x' p +/- sqrt( Finv(1-a,1,df) var(x' p) )

    where for confidence intervals::

        var(x' p) = sigma^2 (x' inv(A'A) x)

    and for prediction intervals::

        var(x' p) = sigma^2 (1 + x' inv(A'A) x)


    Stored properties::

        DoF = len(y)-len(x) = degrees of freedom
        rnorm = 2-norm of the residuals y-Ax
        x = solution to the equation Ax = y

    Computed properties::

        cov = covariance matrix [ inv(A'A); O(n^3) ]
        var = parameter variance [ diag(cov); O(n^2)]
        std = standard deviation of parameters [ sqrt(var); O(n^2) ]
        p = test statistic for chisquare goodness of fit [ chi2.sf; O(1) ]

    Methods::

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
        return C * np.dot(self._SVinv,self._SVinv.T)
    def _var(self):
        C = self.rnorm**2/self.DoF if self.DoF>0 else 1
        return C * np.sum( self._SVinv**2, axis=1)
    def _std(self):
        return np.sqrt(self._var())
    def _p(self):
        from scipy import stats
        return stats.chi2.sf(self.rnorm**2,self.DoF)

    cov = property(_cov,doc="covariance matrix")
    var = property(_var,doc="result variance")
    std = property(_std,doc="result standard deviation")
    p = property(_p,doc="probability of rejection")

    def _interval(self,X,alpha,pred):
        """
        Helper for computing prediction/confidence intervals.
        """

        # Comments from QR decomposition solution to Ax = y:
        #
        #   Rather than A'A we have R from the QR decomposition of A, but
        #   R'R equals A'A.  Note that R is not upper triangular since we
        #   have already multiplied it by the permutation matrix, but it
        #   is invertible.  Rather than forming the product R'R which is
        #   ill-conditioned, we can rewrite x' inv(A'A) x as the equivalent
        #      x' inv(R) inv(R') x = t t', for t = x' inv(R)
        #
        # We have since switched to an SVD solver, which gives us
        #
        #    invC = A'A  = (USV')'USV' = VSU'USV' = VSSV'
        #    C = inv(A'A) = inv(VSSV') = inv(V')inv(SS)inv(V)
        #      = Vinv(SS)V' = Vinv(S) inv(S)V'
        #
        # Substituting, we get
        #
        #    x' inv(A'A) x = t t', for t = x' Vinv(S)
        #
        # Since x is a vector, t t' is the inner product sum(t**2).
        # Note that LAPACK allows us to do this simultaneously for many
        # different x using sqrt(sum(T**2,axis=1)), with T = X' Vinv(S).
        #
        # Note: sqrt(F(1-a;1,df)) = T(1-a/2;df)
        #
        y = np.dot(X,self.x).ravel()
        s = stats.t.ppf(1-alpha/2,self.DoF)*self.rnorm/np.sqrt(self.DoF)
        t = np.dot(X,self._SVinv)
        dy = s*np.sqrt(pred + np.sum( t**2, axis=1))
        return y,dy

    def __call__(self, A):
        """
        Return the prediction for a linear system at points in the
        rows of A.
        """
        return np.dot(np.asarray(A),self.x)

    def ci(self, A, sigma=1):
        """
        Compute the calculated values and the confidence intervals
        for the linear model evaluated at A.

        sigma=1 corresponds to a 1-sigma confidence interval

        Confidence intervals are sometimes expressed as 1-alpha values,
        where alpha = erfc(sigma/sqrt(2)).
        """
        alpha = erfc(sigma/np.sqrt(2))
        return self._interval(np.asarray(A),alpha,0)

    def pi(self, A, p=0.05):
        """
        Compute the calculated values and the prediction intervals
        for the linear model evaluated at A.

        p = 1-alpha = 0.05 corresponds to 95% prediction interval
        """
        return self._interval(np.asarray(A),p,1)

def wsolve(A,y,dy=1,rcond=1e-12):
    """
    Given a linear system y = A*x + e(dy), estimates x,dx

    A is an n x m array
    y is an n x k array or vector of length n
    dy is a scalar or an n x 1 array
    x is a m x k array
    """
    # The ugliness v[:,np.newaxis] transposes a vector
    # The ugliness np.dot(a,b) is a*b for a,b matrices
    # The ugliness vh.T.conj() is the hermitian transpose

    # Make sure inputs are arrays
    A,y,dy = np.asarray(A),np.asarray(y),np.asarray(dy)
    result_dims = y.ndim
    if dy.ndim == 1: dy = dy[:,np.newaxis]
    if y.ndim == 1: y = y[:,np.newaxis]

    # Apply weighting if dy is not a scalar
    # If dy is a scalar, it cancels out of both sides of the equation
    # Note: with A,dy arrays instead of matrices, A/dy operates element-wise
    # Since dy is a row vector, this divides each row of A by the corresponding
    # element of dy.
    if dy.ndim == 2:  A,y = A/dy,y/dy

    # Singular value decomposition: A = U S V.H
    # Since A is an array, U, S, VH are also arrays
    # The zero indicates an economy decomposition, with u nxm rathern than nxn
    u,s,vh = np.linalg.svd(A,0)

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
    Uy = np.dot(u.T.conj(), y)
    x = np.dot(SVinv, Uy)

    DoF = y.shape[0] - x.shape[0]
    rnorm = np.linalg.norm(y - np.dot(A,x))

    return LinearModel(x=x, DoF=DoF, SVinv=SVinv, rnorm=rnorm)

def _poly_matrix(x,degree,origin=False):
    """
    Generate the matrix A used to fit a polynomial using a linear solver.
    """
    if origin:
        n = np.array(range(degree,0,-1))
    else:
        n = np.array(range(degree,-1,-1))
    return np.asarray(x)[:,None]**n[None,:]

class PolynomialModel(object):
    """
    Model evaluator for best fit polynomial p(x) = y.

    Stored properties::

        DoF = len(y)-len(x) = degrees of freedom
        rnorm = 2-norm of the residuals y-Ax
        coeff = coefficients
        degree = polynomial degree

    Computed properties::

        cov = covariance matrix [ inv(A'A); O(n^3) ]
        var = coefficient variance [ diag(cov); O(n^2)]
        std = standard deviation of coefficients [ sqrt(var); O(n^2) ]
        p = test statistic for chisquare goodness of fit [ chi2.sf; O(1) ]

    Methods::

        __call__(x): return the polynomial evaluated at x
        ci(x,sigma=1):  return confidence interval evaluated at x
        pi(x,alpha=0.05):  return prediction interval evaluated at x

    Note that the covariance matrix will not include the ones column if
    the polynomial goes through the origin.
    """
    def __init__(self, x,y,dy, s, origin=False):
        self.x,self.y,self.dy = x,y,dy
        self.origin = origin
        self.coeff = np.ravel(s.x)
        if origin: self.coeff = np.hstack((self.coeff,0))
        self.degree = len(self.coeff)-1
        self.DoF = s.DoF
        self.rnorm = s.rnorm
        self._conf = s
    def _cov(self):
        return self._conf.cov
    def _std(self):
        return np.sqrt(self._var())
    def _var(self):
        var = np.ravel(self._conf.var)
        if self.origin: var = np.hstack((var,0))
        return var
    def _p(self):
        return self._conf.p
    cov = property(_cov,doc="covariance matrix")
    var = property(_var,doc="result variance")
    std = property(_std,doc="result standard deviation")
    p = property(_p,doc="probability of rejection")


    def __call__(self, x):
        """
        Evaluate the polynomial at x.
        """
        return np.polyval(self.coeff,x)

    def ci(self, x, sigma=1):
        """
        Evaluate the polynomial and the confidence intervals at x.

        sigma=1 corresponds to a 1-sigma confidence interval
        """
        A = _poly_matrix(x,self.degree,self.origin)
        return self._conf.ci(A,sigma)

    def pi(self, x, p=0.05):
        """
        Evaluate the polynomial and the prediction intervals at x.

        p = 1-alpha = 0.05 corresponds to 95% prediction interval
        """
        A = _poly_matrix(x,self.degree,self.origin)
        return self._conf.pi(A,p)

    def __str__(self):
        # TODO: better polynomial pretty printing using formatnum
        return "Polynomial(%s)"%self.coeff

    def plot(self,fmt='s'):
        """
        Plot the data, the fit and the confidence region.

        Returns (plotline, barlines, caplines, fitline, fill)

        plotline is the Line2D object showing the data markers
        barlines, caplines are the error bar lines returned from errorbar
        fitline is the Line2D object returned from fit
        fill is the PolyCollection showing the confidence region
        """
        import pylab
        H,H1,H2 = pylab.errorbar(self.x,self.y,yerr=self.dy,fmt=fmt,alpha=0.9)
        c = H.get_color()
        pylab.hold(True)
        px=np.linspace(np.min(self.x),np.max(self.x),200)
        py,pdy = self.pi(px)
        cy,cdy = self.ci(px)
        H3 = pylab.plot(px,py,'-',
                   #px,py+pdy,'-.',px,py-pdy,'-.',
                   #px,cy+cdy,'-.',px,cy-cdy,'-.',
                   color=c, alpha=0.9,
                   )
        H4 = pylab.fill_between(px,cy-cdy,cy+cdy,alpha=0.6,color=c)
        return H,H1,H2,H3,H4

def wpolyfit(x,y,dy=1,degree=None,origin=False):
    """
    Return the polynomial of degree n that
    minimizes sum( (p(x_i) - y_i)**2/dy_i**2).

    if origin is True, the fit should go through the origin.
    """
    assert degree != None, "Missing degree argument to wpolyfit"

    A = _poly_matrix(x,degree,origin)
    s = wsolve(A,y,dy)
    return PolynomialModel(x,y,dy,s,origin=origin)


def demo():
    import pylab

    # Make fake data
    x = np.linspace(-15,5,15)
    th = np.polyval([.2,3,1,5],x)  # polynomial
    dy = np.sqrt(np.abs(th))        # poisson uncertainty estimate
    y = np.random.normal(th,dy)    # but normal generator

    # Fit to a polynomial
    poly = wpolyfit(x,y,dy=dy,degree=3)

    # Plot the result
    poly.plot()
    pylab.show()

def test():
    """
    smoke test...make sure the function continues to return the same
    result for a particular system.
    """
    x = np.array([0,1,2,3,4],'d')
    y = np.array([  2.5,   7.9,  13.9,  21.1,  44.4],'d')
    dy = np.array([ 1.7,  2.4,  3.6,  4.8,  6.2],'d')
    poly = wpolyfit(x,y,dy,1)
    px = np.array([1.5],'d')
    py,pi = poly.pi(px)
    py,ci = poly.ci(px)

    ## Uncomment these to show target values
    #print "Tp = [%.16g, %.16g]"%(p[0],p[1])
    #print "Tdp = [%.16g, %.16g]"%(dp[0],dp[1])
    #print "Tpi,Tci = %.16g, %.16g"%(pi,ci)
    Tp = np.array([7.787249069840737, 1.503992847461524])
    Tdp = np.array([1.522338103010216, 2.117633626902384])
    Tpi,Tci = 7.611128464981324, 2.342860389884832

    perr = np.max(np.abs(poly.coeff-Tp))
    dperr = np.max(np.abs(poly.std-Tdp))
    cierr = np.abs(ci-Tci)
    pierr = np.abs(pi-Tpi)
    assert perr < 1e-15,"||p-Tp||=%g"%perr
    assert dperr < 1e-15,"||dp-Tdp||=%g"%dperr
    assert cierr < 1e-15,"||ci-Tci||=%g"%cierr
    assert pierr < 1e-15,"||pi-Tpi||=%g"%pierr
    assert py == poly(px),"direct call to poly function fails"

if __name__ == "__main__":
    test()
    #demo()
