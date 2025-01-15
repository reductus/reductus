/*
 Perform Levenberg-Marquardt least-squares minimization, based on MINPACK-1.

 AUTHORS
 The original version of this software, called LMFIT, was written in FORTRAN
 as part of the MINPACK-1 package by XXX.

 Craig Markwardt converted the FORTRAN code to IDL.  The information for the
 IDL version is:
 Craig B. Markwardt, NASA/GSFC Code 662, Greenbelt, MD 20770
 craigm@lheamail.gsfc.nasa.gov
 UPDATED VERSIONs can be found on my WEB PAGE:
 http://cow.physics.wisc.edu/~craigm/idl/idl.html

 Mark Rivers created this Python version from Craig's IDL version.
 Mark Rivers, University of Chicago
 Building 434A, Argonne National Laboratory
 9700 South Cass Avenue, Argonne, IL 60439
 rivers@cars.uchicago.edu
 Updated versions can be found at http://cars.uchicago.edu/software

 Sergey Koposov converted the Mark's Python version from Numeric to numpy
 Sergey Koposov, University of Cambridge, Institute of Astronomy,
 Madingley road, CB3 0HA, Cambridge, UK
 koposov@ast.cam.ac.uk
 Updated versions can be found at http://code.google.com/p/astrolibpy/source/browse/trunk/
 
 Alexander Zhang (under William Ratcliff) converted Sergey's Python version into Javascript
 Alexander Zhang, Montgomery Blair High School, NIST Centre for Neutron Research
 Building 235, Room B174
 100 Bureau Drive, MS 6100, Gaithersburg, MD 20899
 alexander.zhang@nist.gov/ylem@nist.gov
 Updated versions can be found at https://github.com/scattering/webfit/tree/master/static/lib
 

 DESCRIPTION

 MPFIT uses the Levenberg-Marquardt technique to solve the
 least-squares problem.  In its typical use, MPFIT will be used to
 fit a user-supplied function (the "model") to user-supplied data
 points (the "data") by adjusting a set of parameters.  MPFIT is
 based upon MINPACK-1 (LMDIF.F) by More' and collaborators.

 For example, a researcher may think that a set of observed data
 points is best modelled with a Gaussian curve.  A Gaussian curve is
 parameterized by its mean, standard deviation and normalization.
 MPFIT will, within certain constraints, find the set of parameters
 which best fits the data.  The fit is "best" in the least-squares
 sense; that is, the sum of the weighted squared differences between
 the model and data is minimized.

 The Levenberg-Marquardt technique is a particular strategy for
 iteratively searching for the best fit.  This particular
 implementation is drawn from MINPACK-1 (see NETLIB), and is much faster
 and more accurate than the version provided in the Scientific Python package
 in Scientific.Functions.LeastSquares.
 This version allows upper and lower bounding constraints to be placed on each
 parameter, or the parameter can be held fixed.

 The user-supplied Python function should return an array of weighted
 deviations between model and data.  In a typical scientific problem
 the residuals should be weighted so that each deviate has a
 gaussian sigma of 1.0.  If X represents values of the independent
 variable, Y represents a measurement for each value of X, and ERR
 represents the error in the measurements, then the deviates could
 be calculated as follows:

 DEVIATES = (Y - F(X)) / ERR

 where F is the analytical function representing the model.  You are
 recommended to use the convenience functions MPFITFUN and
 MPFITEXPR, which are driver functions that calculate the deviates
 for you.  If ERR are the 1-sigma uncertainties in Y, then

 TOTAL( DEVIATES^2 )

 will be the total chi-squared value.  MPFIT will minimize the
 chi-square value.  The values of X, Y and ERR are passed through
 MPFIT to the user-supplied function via the FUNCTKW keyword.

 Simple constraints can be placed on parameter values by using the
 PARINFO keyword to MPFIT.  See below for a description of this
 keyword.

 MPFIT does not perform more general optimization tasks.  See TNMIN
 instead.  MPFIT is customized, based on MINPACK-1, to the
 least-squares minimization problem.


 USER FUNCTION

 The user must define a function which returns the appropriate
 values as specified above.  The function should return the weighted
 deviations between the model and the data.  It should also return a status
 flag and an optional partial derivative array.  For applications which
 use finite-difference derivatives -- the default -- the user
 function should be declared in the following way:

 def myfunct(p, fjac=None, x=None, y=None, err=None)
 # Parameter values are passed in "p"
 # If fjac==None then partial derivatives should not be
 # computed.  It will always be None if MPFIT is called with default
 # flag.
 model = F(x, p)
 # Non-negative status value means MPFIT should continue, negative means
 # stop the calculation.
 status = 0
 return([status, (y-model)/err]

 See below for applications with analytical derivatives.

 The keyword parameters X, Y, and ERR in the example above are
 suggestive but not required.  Any parameters can be passed to
 MYFUNCT by using the functkw keyword to MPFIT.  Use MPFITFUN and
 MPFITEXPR if you need ideas on how to do that.  The function *must*
 accept a parameter list, P.

 In general there are no restrictions on the number of dimensions in
 X, Y or ERR.  However the deviates *must* be returned in a
 one-dimensional Numeric array of type Float.

 User functions may also indicate a fatal error condition using the
 status return described above. If status is set to a number between
 -15 and -1 then MPFIT will stop the calculation and return to the caller.


 ANALYTIC DERIVATIVES

 In the search for the best-fit solution, MPFIT by default
 calculates derivatives numerically via a finite difference
 approximation.  The user-supplied function need not calculate the
 derivatives explicitly.  However, if you desire to compute them
 analytically, then the AUTODERIVATIVE=0 keyword must be passed to MPFIT.
 As a practical matter, it is often sufficient and even faster to allow
 MPFIT to calculate the derivatives numerically, and so
 AUTODERIVATIVE=0 is not necessary.

 If AUTODERIVATIVE=0 is used then the user function must check the parameter
 FJAC, and if FJAC!=None then return the partial derivative array in the
 return list.
 def myfunct(p, fjac=None, x=None, y=None, err=None)
 # Parameter values are passed in "p"
 # If FJAC!=None then partial derivatives must be comptuer.
 # FJAC contains an array of len(p), where each entry
 # is 1 if that parameter is free and 0 if it is fixed.
 model = F(x, p)
 Non-negative status value means MPFIT should continue, negative means
 # stop the calculation.
 status = 0
 if (dojac):
 pderiv = zeros([len(x), len(p)], Float)
 for j in range(len(p)):
 pderiv[:,j] = FGRAD(x, p, j)
 else:
 pderiv = None
 return([status, (y-model)/err, pderiv]

 where FGRAD(x, p, i) is a user function which must compute the
 derivative of the model with respect to parameter P[i] at X.  When
 finite differencing is used for computing derivatives (ie, when
 AUTODERIVATIVE=1), or when MPFIT needs only the errors but not the
 derivatives the parameter FJAC=None.

 Derivatives should be returned in the PDERIV array. PDERIV should be an m x
 n array, where m is the number of data points and n is the number
 of parameters.  dp[i,j] is the derivative at the ith point with
 respect to the jth parameter.

 The derivatives with respect to fixed parameters are ignored; zero
 is an appropriate value to insert for those derivatives.  Upon
 input to the user function, FJAC is set to a vector with the same
 length as P, with a value of 1 for a parameter which is free, and a
 value of zero for a parameter which is fixed (and hence no
 derivative needs to be calculated).

 If the data is higher than one dimensional, then the *last*
 dimension should be the parameter dimension.  Example: fitting a
 50x50 image, "dp" should be 50x50xNPAR.


 CONSTRAINING PARAMETER VALUES WITH THE PARINFO KEYWORD

 The behavior of MPFIT can be modified with respect to each
 parameter to be fitted.  A parameter value can be fixed; simple
 boundary constraints can be imposed; limitations on the parameter
 changes can be imposed; properties of the automatic derivative can
 be modified; and parameters can be tied to one another.

 These properties are governed by the PARINFO structure, which is
 passed as a keyword parameter to MPFIT.

 PARINFO should be a list of dictionaries, one list entry for each parameter.
 Each parameter is associated with one element of the array, in
 numerical order.  The dictionary can have the following keys
 (none are required, keys are case insensitive):

 'value' - the starting parameter value (but see the START_PARAMS
 parameter for more information).

 'fixed' - a boolean value, whether the parameter is to be held
 fixed or not.  Fixed parameters are not varied by
 MPFIT, but are passed on to MYFUNCT for evaluation.

 'limited' - a two-element boolean array.  If the first/second
 element is set, then the parameter is bounded on the
 lower/upper side.  A parameter can be bounded on both
 sides.  Both LIMITED and LIMITS must be given
 together.

 'limits' - a two-element float array.  Gives the
 parameter limits on the lower and upper sides,
 respectively.  Zero, one or two of these values can be
 set, depending on the values of LIMITED.  Both LIMITED
 and LIMITS must be given together.

 'parname' - a string, giving the name of the parameter.  The
 fitting code of MPFIT does not use this tag in any
 way.  However, the default iterfunct will print the
 parameter name if available.

 'step' - the step size to be used in calculating the numerical
 derivatives.  If set to zero, then the step size is
 computed automatically.  Ignored when AUTODERIVATIVE=0.

 'mpside' - the sidedness of the finite difference when computing
 numerical derivatives.  This field can take four
 values:

 0 - one-sided derivative computed automatically
 1 - one-sided derivative (f(x+h) - f(x)  )/h
 -1 - one-sided derivative (f(x)   - f(x-h))/h
 2 - two-sided derivative (f(x+h) - f(x-h))/(2*h)

 Where H is the STEP parameter described above.  The
 "automatic" one-sided derivative method will chose a
 direction for the finite difference which does not
 violate any constraints.  The other methods do not
 perform this check.  The two-sided method is in
 principle more precise, but requires twice as many
 function evaluations.  Default: 0.

 'mpmaxstep' - the maximum change to be made in the parameter
 value.  During the fitting process, the parameter
 will never be changed by more than this value in
 one iteration.

 A value of 0 indicates no maximum.  Default: 0.

 'tied' - a string expression which "ties" the parameter to other
 free or fixed parameters.  Any expression involving
 constants and the parameter array P are permitted.
 Example: if parameter 2 is always to be twice parameter
 1 then use the following: parinfo(2).tied = '2 * p(1)'.
 Since they are totally constrained, tied parameters are
 considered to be fixed; no errors are computed for them.
 [ NOTE: the PARNAME can't be used in expressions. ]

 'mpprint' - if set to 1, then the default iterfunct will print the
 parameter value.  If set to 0, the parameter value
 will not be printed.  This tag can be used to
 selectively print only a few parameter values out of
 many.  Default: 1 (all parameters printed)


 Future modifications to the PARINFO structure, if any, will involve
 adding dictionary tags beginning with the two letters "MP".
 Therefore programmers are urged to avoid using tags starting with
 the same letters; otherwise they are free to include their own
 fields within the PARINFO structure, and they will be ignored.

 PARINFO Example:
 parinfo = [{'value':0., 'fixed':0, 'limited':[0,0], 'limits':[0.,0.]}
 for i in range(5)]
 parinfo[0]['fixed'] = 1
 parinfo[4]['limited'][0] = 1
 parinfo[4]['limits'][0]  = 50.
 values = [5.7, 2.2, 500., 1.5, 2000.]
 for i in range(5): parinfo[i]['value']=values[i]

 A total of 5 parameters, with starting values of 5.7,
 2.2, 500, 1.5, and 2000 are given.  The first parameter
 is fixed at a value of 5.7, and the last parameter is
 constrained to be above 50.


 EXAMPLE

 import mpfit
 import numpy.oldnumeric as Numeric
 x = arange(100, float)
 p0 = [5.7, 2.2, 500., 1.5, 2000.]
 y = ( p[0] + p[1]*[x] + p[2]*[x**2] + p[3]*sqrt(x) +
 p[4]*log(x))
 fa = {'x':x, 'y':y, 'err':err}
 m = mpfit('myfunct', p0, functkw=fa)
 print 'status = ', m.status
 if (m.status <= 0): print 'error message = ', m.errmsg
 print 'parameters = ', m.params

 Minimizes sum of squares of MYFUNCT.  MYFUNCT is called with the X,
 Y, and ERR keyword parameters that are given by FUNCTKW.  The
 results can be obtained from the returned object m.


 THEORY OF OPERATION

 There are many specific strategies for function minimization.  One
 very popular technique is to use function gradient information to
 realize the local structure of the function.  Near a local minimum
 the function value can be taylor expanded about x0 as follows:

 f(x) = f(x0) + f'(x0) . (x-x0) + (1/2) (x-x0) . f''(x0) . (x-x0)
 -----   ---------------   -------------------------------  (1)
 Order  0th               1st                                     2nd

 Here f'(x) is the gradient vector of f at x, and f''(x) is the
 Hessian matrix of second derivatives of f at x.  The vector x is
 the set of function parameters, not the measured data vector.  One
 can find the minimum of f, f(xm) using Newton's method, and
 arrives at the following linear equation:

 f''(x0) . (xm-x0) = - f'(x0)                                                  (2)

 If an inverse can be found for f''(x0) then one can solve for
 (xm-x0), the step vector from the current position x0 to the new
 projected minimum.  Here the problem has been linearized (ie, the
 gradient information is known to first order).  f''(x0) is
 symmetric n x n matrix, and should be positive definite.

 The Levenberg - Marquardt technique is a variation on this theme.
 It adds an additional diagonal term to the equation which may aid the
 convergence properties:

 (f''(x0) + nu I) . (xm-x0) = -f'(x0)                            (2a)

 where I is the identity matrix.  When nu is large, the overall
 matrix is diagonally dominant, and the iterations follow steepest
 descent.  When nu is small, the iterations are quadratically
 convergent.

 In principle, if f''(x0) and f'(x0) are known then xm-x0 can be
 determined.  However the Hessian matrix is often difficult or
 impossible to compute.  The gradient f'(x0) may be easier to
 compute, if even by finite difference techniques.  So-called
 quasi-Newton techniques attempt to successively estimate f''(x0)
 by building up gradient information as the iterations proceed.

 In the least squares problem there are further simplifications
 which assist in solving eqn (2).  The function to be minimized is
 a sum of squares:

 f = Sum(hi^2)                                                                                 (3)

 where hi is the ith residual out of m residuals as described
 above.  This can be substituted back into eqn (2) after computing
 the derivatives:

 f'  = 2 Sum(hi  hi')
 f'' = 2 Sum(hi' hj') + 2 Sum(hi hi'')                                (4)

 If one assumes that the parameters are already close enough to a
 minimum, then one typically finds that the second term in f'' is
 negligible [or, in any case, is too difficult to compute].  Thus,
 equation (2) can be solved, at least approximately, using only
 gradient information.

 In matrix notation, the combination of eqns (2) and (4) becomes:

 hT' . h' . dx = - hT' . h                                                 (5)

 Where h is the residual vector (length m), hT is its transpose, h'
 is the Jacobian matrix (dimensions n x m), and dx is (xm-x0).  The
 user function supplies the residual vector h, and in some cases h'
 when it is not found by finite differences (see MPFIT_FDJAC2,
 which finds h and hT').  Even if dx is not the best absolute step
 to take, it does provide a good estimate of the best *direction*,
 so often a line minimization will occur along the dx vector
 direction.

 The method of solution employed by MINPACK is to form the Q . R
 factorization of h', where Q is an orthogonal matrix such that QT .
 Q = I, and R is upper right triangular.  Using h' = Q . R and the
 ortogonality of Q, eqn (5) becomes

 (RT . QT) . (Q . R) . dx = - (RT . QT) . h
 RT . R . dx = - RT . QT . h             (6)
 R . dx = - QT . h

 where the last statement follows because R is upper triangular.
 Here, R, QT and h are known so this is a matter of solving for dx.
 The routine MPFIT_QRFAC provides the QR factorization of h, with
 pivoting, and MPFIT_QRSOLV provides the solution for dx.


 REFERENCES

 MINPACK-1, Jorge More', available from netlib (www.netlib.org).
 "Optimization Software Guide," Jorge More' and Stephen Wright,
 SIAM, *Frontiers in Applied Mathematics*, Number 14.
 More', Jorge J., "The Levenberg-Marquardt Algorithm:
 Implementation and Theory," in *Numerical Analysis*, ed. Watson,
 G. A., Lecture Notes in Mathematics 630, Springer-Verlag, 1977.


 MODIFICATION HISTORY

 Translated from MINPACK-1 in FORTRAN, Apr-Jul 1998, CM
 Copyright (C) 1997-2002, Craig Markwardt
 This software is provided as is without any warranty whatsoever.
 Permission to use, copy, modify, and distribute modified or
 unmodified copies is granted, provided this copyright and disclaimer
 are included unchanged.

 Translated from MPFIT (Craig Markwardt's IDL package) to Python,
 August, 2002.  Mark Rivers
 Converted from Numeric to numpy (Sergey Koposov, July 2008)
 
 Translated from MPFIT(Sergey Koposov's astrolibpy library) to Javascript, 
 July, 2014. Alexander Zhang
 */

var lmfit = lmfit || {};
$(document).ready(function () {
/*
        Original FORTRAN documentation
        **********

        subroutine lmdif

        the purpose of lmdif is to minimize the sum of the squares of
        m nonlinear functions in n variables by a modification of
        the levenberg-marquardt algorithm. the user must provide a
        subroutine which calculates the functions. the jacobian is
        then calculated by a forward-difference approximation.

        the subroutine statement is

          subroutine lmdif(fcn,m,n,x,fvec,ftol,xtol,gtol,maxfev,epsfcn,
                                               diag,mode,factor,nprint,info,nfev,fjac,
                                               ldfjac,ipvt,qtf,wa1,wa2,wa3,wa4)

        where

          fcn is the name of the user-supplied subroutine which
                calculates the functions. fcn must be declared
                in an external statement in the user calling
                program, and should be written as follows.

                subroutine fcn(m,n,x,fvec,iflag)
                integer m,n,iflag
                double precision x(n),fvec(m)
                ----------
                calculate the functions at x and
                return this vector in fvec.
                ----------
                return
                end

                the value of iflag should not be changed by fcn unless
                the user wants to terminate execution of lmdif.
                in this case set iflag to a negative integer.

          m is a positive integer input variable set to the number
                of functions.

          n is a positive integer input variable set to the number
                of variables. n must not exceed m.

          x is an array of length n. on input x must contain
                an initial estimate of the solution vector. on output x
                contains the final estimate of the solution vector.

          fvec is an output array of length m which contains
                the functions evaluated at the output x.

          ftol is a nonnegative input variable. termination
                occurs when both the actual and predicted relative
                reductions in the sum of squares are at most ftol.
                therefore, ftol measures the relative error desired
                in the sum of squares.

          xtol is a nonnegative input variable. termination
                occurs when the relative error between two consecutive
                iterates is at most xtol. therefore, xtol measures the
                relative error desired in the approximate solution.

          gtol is a nonnegative input variable. termination
                occurs when the cosine of the angle between fvec and
                any column of the jacobian is at most gtol in absolute
                value. therefore, gtol measures the orthogonality
                desired between the function vector and the columns
                of the jacobian.

          maxfev is a positive integer input variable. termination
                occurs when the number of calls to fcn is at least
                maxfev by the end of an iteration.

          epsfcn is an input variable used in determining a suitable
                step length for the forward-difference approximation. this
                approximation assumes that the relative errors in the
                functions are of the order of epsfcn. if epsfcn is less
                than the machine precision, it is assumed that the relative
                errors in the functions are of the order of the machine
                precision.

          diag is an array of length n. if mode = 1 (see
                below), diag is internally set. if mode = 2, diag
                must contain positive entries that serve as
                multiplicative scale factors for the variables.

          mode is an integer input variable. if mode = 1, the
                variables will be scaled internally. if mode = 2,
                the scaling is specified by the input diag. other
                values of mode are equivalent to mode = 1.

          factor is a positive input variable used in determining the
                initial step bound. this bound is set to the product of
                factor and the euclidean norm of diag*x if nonzero, or else
                to factor itself. in most cases factor should lie in the
                interval (.1,100.). 100. is a generally recommended value.

          nprint is an integer input variable that enables controlled
                printing of iterates if it is positive. in this case,
                fcn is called with iflag = 0 at the beginning of the first
                iteration and every nprint iterations thereafter and
                immediately prior to return, with x and fvec available
                for printing. if nprint is not positive, no special calls
                of fcn with iflag = 0 are made.

          info is an integer output variable. if the user has
                terminated execution, info is set to the (negative)
                value of iflag. see description of fcn. otherwise,
                info is set as follows.

                info = 0  improper input parameters.

                info = 1  both actual and predicted relative reductions
                                  in the sum of squares are at most ftol.

                info = 2  relative error between two consecutive iterates
                                  is at most xtol.

                info = 3  conditions for info = 1 and info = 2 both hold.

                info = 4  the cosine of the angle between fvec and any
                                  column of the jacobian is at most gtol in
                                  absolute value.

                info = 5  number of calls to fcn has reached or
                                  exceeded maxfev.

                info = 6  ftol is too small. no further reduction in
                                  the sum of squares is possible.

                info = 7  xtol is too small. no further improvement in
                                  the approximate solution x is possible.

                info = 8  gtol is too small. fvec is orthogonal to the
                                  columns of the jacobian to machine precision.

          nfev is an integer output variable set to the number of
                calls to fcn.

          fjac is an output m by n array. the upper n by n submatrix
                of fjac contains an upper triangular matrix r with
                diagonal elements of nonincreasing magnitude such that

                               t        t                 t
                          p *(jac *jac)*p = r *r,

                where p is a permutation matrix and jac is the final
                calculated jacobian. column j of p is column ipvt(j)
                (see below) of the identity matrix. the lower trapezoidal
                part of fjac contains information generated during
                the computation of r.

          ldfjac is a positive integer input variable not less than m
                which specifies the leading dimension of the array fjac.

          ipvt is an integer output array of length n. ipvt
                defines a permutation matrix p such that jac*p = q*r,
                where jac is the final calculated jacobian, q is
                orthogonal (not stored), and r is upper triangular
                with diagonal elements of nonincreasing magnitude.
                column j of p is column ipvt(j) of the identity matrix.

          qtf is an output array of length n which contains
                the first n elements of the vector (q transpose)*fvec.

          wa1, wa2, and wa3 are work arrays of length n.

          wa4 is a work array of length m.

        subprograms called

          user-supplied ...... fcn

          minpack-supplied ... dpmpar,enorm,fdjac2,,qrfac

          fortran-supplied ... dabs,dmax1,dmin1,dsqrt,mod

        argonne national laboratory. minpack project. march 1980.
        burton s. garbow, kenneth e. hillstrom, jorge j. more

        **********
*/
    lmfit.lmfit = function (fcn, xall, functkw, parinfo, ftol, xtol, gtol, damp, maxiter, factor, nprint, iterfunct, iterkw, nocovar, rescale, autoderivative, quiet, diag, epsfcn, debug) {
        
		/*
		Inputs:
        fcn:
           The function to be minimized.  The function should return the weighted
           deviations between the model and the data, as described above.

        xall:
           An array of starting values for each of the parameters of the model.
           The number of parameters should be fewer than the number of measurements.

           This parameter is optional if the parinfo keyword is used (but see
           parinfo).  The parinfo keyword provides a mechanism to fix or constrain
           individual parameters.

  Keywords:

         autoderivative:
                If this is set, derivatives of the function will be computed
                automatically via a finite differencing procedure.  If not set, then
                fcn must provide the (analytical) derivatives.
                   Default: set (=1)
                   NOTE: to supply your own analytical derivatives,
                                 explicitly pass autoderivative=0

         ftol:
                A nonnegative input variable. Termination occurs when both the actual
                and predicted relative reductions in the sum of squares are at most
                ftol (and status is accordingly set to 1 or 3).  Therefore, ftol
                measures the relative error desired in the sum of squares.
                   Default: 1E-10

         functkw:
                A dictionary which contains the parameters to be passed to the
                user-supplied function specified by fcn via the standard Python
                keyword dictionary mechanism.  This is the way you can pass additional
                data to your user-supplied function without using global variables.

                Consider the following example:
                   if functkw = {'xval':[1.,2.,3.], 'yval':[1.,4.,9.],
                                                 'errval':[1.,1.,1.] }
                then the user supplied function should be declared like this:
                   def myfunct(p, fjac=None, xval=None, yval=None, errval=None):

                Default: {}   No extra parameters are passed to the user-supplied
                                          function.

         gtol:
                A nonnegative input variable. Termination occurs when the cosine of
                the angle between fvec and any column of the jacobian is at most gtol
                in absolute value (and status is accordingly set to 4). Therefore,
                gtol measures the orthogonality desired between the function vector
                and the columns of the jacobian.
                   Default: 1e-10

         iterkw:
                The keyword arguments to be passed to iterfunct via the dictionary
                keyword mechanism.  This should be a dictionary and is similar in
                operation to FUNCTKW.
                   Default: {}  No arguments are passed.

         iterfunct:
                The name of a function to be called upon each NPRINT iteration of the
                MPFIT routine.  It should be declared in the following way:
                   def iterfunct(myfunct, p, iter, fnorm, functkw=None,
                                                 parinfo=None, quiet=0, dof=None, [iterkw keywords here])
                   # perform custom iteration update

                iterfunct must accept all three keyword parameters (FUNCTKW, PARINFO
                and QUIET).

                myfunct:  The user-supplied function to be minimized,
                p:              The current set of model parameters
                iter:    The iteration number
                functkw:  The arguments to be passed to myfunct.
                fnorm:  The chi-squared value.
                quiet:  Set when no textual output should be printed.
                dof:      The number of degrees of freedom, normally the number of points
                                  less the number of free parameters.
                See below for documentation of parinfo.

                In implementation, iterfunct can perform updates to the terminal or
                graphical user interface, to provide feedback while the fit proceeds.
                If the fit is to be stopped for any reason, then iterfunct should return a
                a status value between -15 and -1.  Otherwise it should return None
                (e.g. no return statement) or 0.
                In principle, iterfunct should probably not modify the parameter values,
                because it may interfere with the algorithm's stability.  In practice it
                is allowed.

                Default: an internal routine is used to print the parameter values.

                Set iterfunct=None if there is no user-defined routine and you don't
                want the internal default routine be called.

         maxiter:
                The maximum number of iterations to perform.  If the number is exceeded,
                then the status value is set to 5 and MPFIT returns.
                Default: 200 iterations

         nocovar:
                Set this keyword to prevent the calculation of the covariance matrix
                before returning (see COVAR)
                Default: clear (=0)  The covariance matrix is returned

         nprint:
                The frequency with which iterfunct is called.  A value of 1 indicates
                that iterfunct is called with every iteration, while 2 indicates every
                other iteration, etc.  Note that several Levenberg-Marquardt attempts
                can be made in a single iteration.
                Default value: 1

         parinfo
                Provides a mechanism for more sophisticated constraints to be placed on
                parameter values.  When parinfo is not passed, then it is assumed that
                all parameters are free and unconstrained.  Values in parinfo are never
                modified during a call to MPFIT.

                See description above for the structure of PARINFO.

                Default value: None  All parameters are free and unconstrained.

         quiet:
                Set this keyword when no textual output should be printed by MPFIT

         damp:
                A scalar number, indicating the cut-off value of residuals where
                "damping" will occur.  Residuals with magnitudes greater than this
                number will be replaced by their hyperbolic tangent.  This partially
                mitigates the so-called large residual problem inherent in
                least-squares solvers (as for the test problem CURVI,
                http://www.maxthis.com/curviex.htm).
                A value of 0 indicates no damping.
                   Default: 0

                Note: DAMP doesn't work with autoderivative=0

         xtol:
                A nonnegative input variable. Termination occurs when the relative error
                between two consecutive iterates is at most xtol (and status is
                accordingly set to 2 or 3).  Therefore, xtol measures the relative error
                desired in the approximate solution.
                Default: 1E-10

   Outputs:

         Returns an object of type mpfit.  The results are attributes of this class,
         e.g. mpfit.status, mpfit.errmsg, mpfit.params, npfit.niter, mpfit.covar.

         .status
                An integer status code is returned.  All values greater than zero can
                represent success (however .status == 5 may indicate failure to
                converge). It can have one of the following values:

                -16
                   A parameter or function value has become infinite or an undefined
                   number.  This is usually a consequence of numerical overflow in the
                   user's model function, which must be avoided.

                -15 to -1
                   These are error codes that either MYFUNCT or iterfunct may return to
                   terminate the fitting process.  Values from -15 to -1 are reserved
                   for the user functions and will not clash with MPFIT.

                0  Improper input parameters.

                1  Both actual and predicted relative reductions in the sum of squares
                   are at most ftol.

                2  Relative error between two consecutive iterates is at most xtol

                3  Conditions for status = 1 and status = 2 both hold.

                4  The cosine of the angle between fvec and any column of the jacobian
                   is at most gtol in absolute value.

                5  The maximum number of iterations has been reached.

                6  ftol is too small. No further reduction in the sum of squares is
                   possible.

                7  xtol is too small. No further improvement in the approximate solution
                   x is possible.

                8  gtol is too small. fvec is orthogonal to the columns of the jacobian
                   to machine precision.

         .fnorm
                The value of the summed squared residuals for the returned parameter
                values.

         .covar
                The covariance matrix for the set of parameters returned by MPFIT.
                The matrix is NxN where N is the number of  parameters.  The square root
                of the diagonal elements gives the formal 1-sigma statistical errors on
                the parameters if errors were treated "properly" in fcn.
                Parameter errors are also returned in .perror.

                To compute the correlation matrix, pcor, use this example:
                   cov = mpfit.covar
                   pcor = cov * 0.
                   for i in range(n):
                          for j in range(n):
                                 pcor[i,j] = cov[i,j]/sqrt(cov[i,i]*cov[j,j])

                If nocovar is set or MPFIT terminated abnormally, then .covar is set to
                a scalar with value None.

         .errmsg
                A string error or warning message is returned.

         .nfev
                The number of calls to MYFUNCT performed.

         .niter
                The number of iterations completed.

         .perror
                The formal 1-sigma errors in each parameter, computed from the
                covariance matrix.  If a parameter is held fixed, or if it touches a
                boundary, then the error is reported as zero.

                If the fit is unweighted (i.e. no errors were given, or the weights
                were uniformly set to unity), then .perror will probably not represent
                the true parameter uncertainties.

                *If* you can assume that the true reduced chi-squared value is unity --
                meaning that the fit is implicitly assumed to be of good quality --
                then the estimated parameter uncertainties can be computed by scaling
                .perror by the measured chi-squared value.

                   dof = len(x) - len(mpfit.params) # deg of freedom
                   # scaled uncertainties
                   pcerror = mpfit.perror * sqrt(mpfit.fnorm / dof)
				   */
		var machep=Math.pow(2, -52);
        if (lmfit.typeOf(functkw) == 'undefined') {
            functkw = {};
        }
        if (lmfit.typeOf(ftol) == 'undefined') {
            ftol = Math.pow(10, -5);
        }
        if (lmfit.typeOf(xtol) == 'undefined') {
            xtol = Math.pow(10, -5);
        }
        if (lmfit.typeOf(gtol) == 'undefined') {
            gtol = Math.pow(10, -5);
        }
        if (lmfit.typeOf(damp) == 'undefined') {
            damp = 0;
        }
        if (lmfit.typeOf(maxiter) == 'undefined') {
            maxiter = 200;
        }
        if (lmfit.typeOf(factor) == 'undefined') {
            factor = 100
        }
        if (lmfit.typeOf(nprint) == 'undefined') {
            nprint = 1
        }
        if (lmfit.typeOf(iterfunct) == 'undefined') {
            iterfunct = 'default';
        }
        if (lmfit.typeOf(iterkw) == 'undefined') {
            iterkw = {};
        }
        if (lmfit.typeOf(nocovar) == 'undefined') {
            nocovar = 0;
        }
        if (lmfit.typeOf(rescale) == 'undefined') {
            rescale = 0
        }
        if (lmfit.typeOf(autoderivative) == 'undefined') {
            autoderivative = 1
        }
        if (lmfit.typeOf(quiet) == 'undefined') {
            quiet = 0
        }
        if (lmfit.typeOf(debug) == 'undefined') {
            debug = 0
        }
        this.niter = 0;
        this.params, this.covar, this.perror;
        this.status = 0;
        this.debug = debug;
        this.errmsg = '';
        this.nfev = 0;
        this.damp = damp;
        this.dof = 0;
        if (lmfit.typeOf(fcn) == 'undefined') {
            this.errmsg = "Usage: parms=mpfit('myfunct',...)";
            return;

        }
        if (iterfunct == 'default') {
            iterfunct = lmfit.defiter;
        }
//        Parameter damping doesn't work when user is providing their own
//         gradients.
        if (this.damp != 0 && autoderivative == 0) {
            this.errmsg = "error: keywords DAMP and autoderivative are mutually exclusive";
            return;
        }
//        Parameters can either be stored in parinfo, or x. x takes precedence if it exists
        if (lmfit.typeOf(xall) == 'undefined' && lmfit.typeOf(parinfo) == 'undefined') {
            this.errmsg = "error: must puass parameters in P or PARINFO";
            return;
        }
        //skip checking the type of PARINFO because we assume the user is somewhat smart and because js is nice
//        If the parameters were not specified at the command line, then
//         extract them from PARINFO
        if (lmfit.typeOf(xall) == 'undefined') {
            xall = lmfit.parinfo(parinfo, 'value');
            if (lmfit.typeOf(xall) == 'undefined') {
                this.errmsg = "error: either p or parinfo(*)['value'] must be supplied]";
                return;
            }
        }
        var npar = xall.length;
        this.fnorm = -1;
        var fnorm1 = -1;
//        TIED parameters?
        var ptied = lmfit.parinfo(parinfo, 'tied', '', npar);
        this.qanytied = 0;
        for (var i = 0; i < npar; i++) {
            if (lmfit.typeOf(ptied[i]) == 'undefined') {
                this.qanytied = 1;
            }
        }
        this.ptied = ptied;
//        FIXED parameters ?

        var pfixed = lmfit.parinfo(parinfo, 'fixed', 0, npar);
        for (i = 0; i < pfixed.length; i++) {
            if (pfixed[i] == 1) {
                pfixed[i] = true;
            }
            else {
                pfixed[i] = false;
            }
        }
        for (var i = 0; i < npar; i++) {
            pfixed[i] = pfixed[i];//Tied parameters are also effectively fixed

        }
//        Finite differencing step, absolute and relative, and sidedness of deriv.
        var step = lmfit.parinfo(parinfo, 'step', 0, npar);
        var dstep = lmfit.parinfo(parinfo, 'dstep', 0, npar);
        var dside = lmfit.parinfo(parinfo, 'dside', 0, npar);

//        Maximum and minimum steps allowed to be taken in one iteration
        var maxstep = lmfit.parinfo(parinfo, 'mpmaxstep', 0, npar);
        var minstep = lmfit.parinfo(parinfo, 'mpminstep', 0, npar);
        var qmin = [];
        for (var i = 0; i < minstep.length; i++) {
            if (minstep[i] != 0) {
                qmin.push(true);
            } else {
                qmin.push(false);
            }
        }
        for (var i = 0; i < qmin.length; i++) {
            qmin[i] = false;
        }
        var qmax = [];
        for (var i = 0; i < maxstep.length; i++) {
            if (maxstep[i] != 0) {
                qmax.push(true);
            } else {
                qmax.push(false);
            }
        }
        for (var i = 0; i < minstep.length; i++) {
            if (minstep[i] == false && maxstep[i] == false && maxstep[i] < minstep[i]) {
                this.errmsg = "error: mpminstep is greater than mpmaxstep";
                return;
            }
        }
        var wh = [];
        for (i = 0; i < qmin.length; i++) {
            if (qmin[i] != 0 || qmax[i] != 0) {
                wh.push(i);
            }
        }
        var qminmax = 0;
        for (var i = 0; i < wh.length; i++) {
            if (wh[i] > 0) {
                qminmax++;
            }
        }
//        Finish up the free parameters
        var ifree = [];
        for (var i = 0; i < pfixed.length; i++) {
            if (pfixed != 1) {
                ifree.push(i);
            }
        }
        var nfree = ifree.length;
        if (nfree == 0) {
            this.errmsg = 'error: no free parameters';
            return;
        }

//        Compose only VARYING parameters
        this.params = []; //this.params is the set of parameters to be returned
        for (i = 0; i < xall.length; i++) {
            this.params.push(xall[i]);
        }
        var x = [];
        for (i = 0; i < ifree.length; i++) {
            x.push(this.params[ifree[i]]);
        }

//        Limited parameters ?
        var limited = lmfit.parinfo(parinfo, 'limited', [0, 0], npar);
        var limits = lmfit.parinfo(parinfo, 'limits', [0, 0], npar);
        var qulim = [], ulim = [], qllim = [], llim = [], qanylim = [];
        if (lmfit.typeOf(limited) == 'undefined' && lmfit.typeOf(limits) == 'undefined') {
//            Error checking on limits in parinfo
            for (var i = 0; i < xall.length; i++) {
                if (xall[i] < limits[i][0] || xall[i] < limits[i][1])//may need to check that some of the limits are actually defined
                {
                    this.errmsg = 'error: parameters are not within PARINFO limits';
                    return;
                }
            }
            for (var i = 0; i < xall.length; i++) {
                if (limits[i][0] >= limits[i][0] && pfixed == 0) {
                    this.errmsg = 'error: PARINFO parameter limits are not consistent';
                    return;
                }
            }
            for (i = 0; i < ifree.length; i++) {
                qulim = limited[ifree[i]][1];
                ulim = limits[ifree[i]][1];
                qllim = limited[ifree[i]][0];
                llim = limits[ifree[i]][0];
            }
            for (var i = 0; i < qulim.length; i++) {
                if (qulim[i] == 0) {
                    qanylim++;
                }
            }
            for (var i = 0; i < qllim.length; i++) {
                if (qllim[i] == 0) {
                    qanylim++;
                }
            }
            if (qanylim > 1) {
                qanylim = 1;
            }

        } else {
//            Fill in local variables with dummy values
            qulim = [];
            for (var i = 0; i < nfree; i++) {
                qulim.push(0);
            }
            for (i = 0; i < x.length; i++) {
                ulim[i] = 0;
                llim[i] = 0;
            }

            qllim = qulim;

            qanylim = 0;
        }
        n = x.length;
//        Check input parameters for errors
        if ((n < 0) || (ftol <= 0) || (xtol <= 0) || (gtol <= 0) || (maxiter < 0) || (factor <= 0)) {
            this.errmsg = 'error: input keywords are inconsistent';
            return;
        }
        if (rescale != 0) {
            this.errmsg = 'error: DIAG parameter scales are inconsistent';
            if (diag.length < n) {
                return;
            }
            for (var i = 0; i < diag.length; i++) {
                if (diag[i] <= 0) {
                    return;
                }
            }
            this.errmsg = '';
        }
        var a = lmfit.call(fcn, this.params, functkw);
        this.status = a.status;
        var fvec = a.f;
        if (this.status < 0) {
            this.errmsg = 'error: first call to function failed';
            return;
        }
        //skip some rounding checks
        var m = fvec.length;
        if (m < n) {
            this.errmsg = 'error: number of parameters must not exceed data'
            return;
        }
        this.dof = m - nfree;
        this.fnorm = lmfit.enorm(fvec);
//        Initialize Levenberg-Marquardt parameter and iteration counter
        var par = 0;
        this.niter = 1;
        var qtf = [];
        for (i = 0; i < x.length; i++) {
            qtf.push(0);
        }
        this.status = 0;

//        Beginning of the outer loop

        while (true) {
//            If requested, call fcn to enable printing of iterates
            for (i = 0; i < ifree.length; i++) {
                this.params[ifree[i]] = x[i];
            }
            if (this.qanytied) {
                this.params = lmfit.tie(this.params, ptied);

            }
            if (nprint > 0 && lmfit.typeOf(iterfunct) != 'undefined') {
                if ((this.niter - 1) % nprint == 0) {
                    var mperr = 0;
                    var xnew0 = [];
                    for (i = 0; i < this.params.length; i++) {
                        xnew0.push(this.params[i]);
                    }
                    var dof = Math.max(fvec.length - x.length, 0);
                    var status = iterfunct(fcn, this.params, this.niter, Math.pow(this.fnorm, 2), functkw, quiet, null, parinfo, null, null, dof);
                    if (lmfit.typeOf(status) != 'undefined') {
                        this.status = status;
                    }
//                     Check for user termination
                    if (this.status < 0) {
                        this.errmsg = 'WARNING: premature terminatoin by iterfunct';
                        return;
                    }
//                    If parameters were changed (grrr..) then re-tie
                    var a = 0;
                    for (var i = 0; i < xnew0.length; i++) {
                        a = Math.max(a, xnew0[i] - this.params[i]);
                    }
                    if (a > 0) {
                        if (this.qanytied) {
                            this.params = lmfit.tie(this.params, ptied);

                        }
                        for (i = 0; i < ifree.length; i++) {


                            x[i] = this.params[ifree[i]];
                        }
                    }
                }
            }
//            Calculate the jacobian matrix
            this.status = 2;
            var catch_msg = 'calling MPFIT_FDJAC2';
            var temp = lmfit.fdjac2(fcn, x, fvec, step, qulim, ulim, dside, epsfcn, autoderivative, functkw, this.params, ifree, dstep);
            var fjac = temp.fjac;
            if (lmfit.typeOf(fjac) == 'undefined') {
                this.errmsg = 'WARNING: premature termination by FDJAC2';
                return;
            }
//            Determine if any of the parameters are pegged at the limits
            if (qanylim) {
                catch_msg = 'zeroing derivatives of pegged parameters';
                var whlpeg=[];
                for (i = 0; i < qllim.length; i++) {
                    if (qllim[i] != 0 && x == llim[i]) {
                        whlpeg.push(i);
                    }
                }
                var nlpeg = whlpeg.length;
                var whupeg=[];
                for (i = 0; i < qulim.length; i++) {
                    if (qulim[i] != 0 && x == ulim[i]) {
                        whupeg.push(i);
                    }
                }
                var nupeg = whupeg.length;
//                See if any "pegged" values should keep their derivatives
                if (nlpeg > 0) {
//                    Total derivative of sum wrt lower pegged parameters
                    for (i = 0; i < nlpeg; i++) {
                        var sum0 = 0;
                        for (j = 0; j < fjac.lengh; j++) {
                            sum0 += fvec[j] * fjac[j][whlpeg[i]];

                        }
                        if (sum0 > 0) {
                            for (j = 0; j < fjac.legnth; j++) {
                                fjac[j][whlpeg[i]] = 0;
                            }
                        }
                    }
                }

                if (nupeg > 0) {
                    for (i = 0; i < nupeg; i++) {
                        var sum0 = 0;
//                        Total derivative of sum wrt upper pegged parameters
                        for (j = 0; j < fvec.length; j++) {
                            sum0 += fvec[j] * fjac[j][whupeg[i]];
                        }
                        if (sum0 < 0) {
                            for (j = 0; i < fjac.length; j++) {
                                fjac[j][whupeg[i]] = 0;
                            }
                        }
                    }
                }
            }
//            Compute the QR factorization of the jacobian
            var a = lmfit.qrfac(fjac, 1);
            fjac = a.a;
            var ipvt = a.ipvt;
            var wa1 = a.rdiag;
            var wa2 = a.acnorm;
            var wa3 = [];

//            On the first iteration if "diag" is unspecificed, scale
//            according to the norms of the columns of the initial jacobian
            catch_msg = 'rescaling diagonal elements';
            if (this.niter == 1) {
                if (rescale == 0 || diag.length < n) {
                    diag = [];
                    for (i = 0; i < wa2.length; i++) {
                        diag[i] = wa2[i];
                    }
                    for (i = 0; i < diag.length; i++) {
                        if (diag[i] == 0) {
                            diag[i] = 1;
                        }
                    }
                }
//                  On the first iteration, calculate the norm of the scaled x
//                  and initialize the step bound delta
                for (i = 0; i < diag.length; i++) {

                    //DO IT: wa3 does not necessairly push the values
                    wa3.push(diag[i] * x[i]);
                    var xnorm = lmfit.enorm(wa3);
                    var delta = factor * xnorm;
                    if (delta == 0) {
                        delta = factor;
                    }
                }
            }
            //Form (q transpose)*fvec and store the first n components in qtf
            catch_msg = 'forming (qtranspose)*fvec';
            var wa4 = [];
            for (i = 0; i < fvec.length; i++) {
                wa4[i] = fvec[i];
            }
            for (j = 0; j < n; j++) {
                var lj = ipvt[j];
                var temp3 = fjac[j][lj];
                if (temp3 != 0) {
                    var fj = [], wj = [], sum = 0;
                    for (i = j; i < fjac.length; i++) {
                        fj.push(fjac[i][lj]);
                        wj.push(wa4[i]);
                        sum += fj[i - j] * wj[i - j];

                    }
                    for (i = j; i < wa4.length; i++) {
                        wa4[i] = wj[i - j] - fj[i - j] * sum / temp3;
                    }

                }
                fjac[j][lj] = wa1[j];
                qtf[j] = wa4[j];

            }
//             From this point on, only the square matrix, consisting of the
//             triangle of R, is needed.
            var tempMatrix = new Array(n);
            for (i = 0; i < n; i++) {
                tempMatrix[i]=new Array(n);
                for (var z = 0; z < n; z++) {
                    tempMatrix[i][z] = 0;
                }
            }
            for (i = 0; i < n; i++) {
                for (j = 0; j < n; j++) {
                    tempMatrix[i][j] = fjac[i][j];
                }
            }
            fjac = tempMatrix;
            var temp = new Array(fjac.length);
            for (i = 0; i < fjac.length; i++) {
                temp[i]=new Array(fjac[i].length);
                for (z = 0; z < temp[0].length; z++) {
                    temp[i][z] = fjac[i][z];
                }
            }
            for(i=0; i<n; i++)
            {
                for(var z=0; z<temp.length;z++ )
                {
                    temp[z][i]=fjac[z][ipvt[i]];
                }
            }

            fjac = [];
            for (i = 0; i < temp.length; i++) {
                fjac[i] = temp[i];
            }

//            Check for overflow.  This should be a cheap test here since FJAC
//            has been reduced to a (small) square matrix, and the test is
//            O(N^2).
//            wh = where(finite(fjac) EQ 0, ct)
//            if ct GT 0 then goto, FAIL_OVERFLOW

//            Compute the norm of the scaled gradient
            catch_msg = 'computing the scaled gradient';
            var gnorm = 0;
            if (this.fnorm != 0) {
                for (j = 0; j < n; j++) {
                    var l = ipvt[j];
                    if (wa2[l] != 0) {
                        sum0 = 0;
                        var sum=0;
                        for (i = 0; i < j + 1; i++) {

                            sum += fjac[i][j] * qtf[i];

                        }
                        sum0=sum/this.fnorm;
                        gnorm = Math.max(gnorm, Math.abs(sum0 / wa2[l]));
                    }
                }
            }
//            Test for convergence of the gradient norm
            if (gnorm <= gtol) {
                this.status = 4;
                break;

            }
            if (maxiter == 0) {
                this.status = 5;
                break;

            }
//            Rescale if necessary

            if (rescale == 0) {
                //cheap way of doing numpy.choose(diag>wa2 ,(wa2,diag);
                var temp=new Array(2);
                temp[0]=[];
                for(i=0; i<wa2.length; i++)
                {
                    temp[0].push(wa2[i]);
                }
                temp[1]=[];
                for(i=0; i<diag.length; i++)
                {
                    temp[1].push(diag[i]);
                }
                var boolean=[];
                for(i=0; i<diag.length; i++)
                {
                    if(diag[i]>wa2[i])
                    {
                        boolean.push(1);
                    } else{
                        boolean.push(0);
                    }
                }

                for(i=0; i< boolean.length; i++)
                {
                    diag[i]=temp[boolean[i]][i];
                }
            }

//            Beginning of the inner loop
            while (true) {
                var alpha;
//                Determine the levenberg-marquardt parameter
                catch_msg = 'calculating LM parameteR(MPFIT_)';
                var a = lmfit.lmpar(fjac, ipvt, diag, qtf, delta, wa1, wa2, par);
                fjac = a.r;
                par = a.par;
                wa1 = a.x;
                wa2 = a.sdiag;
//                Store the direction p and x+p. Calculate the norm of p

                for(i=0; i<wa1.length; i++)
                {
                    wa1[i]=-wa1[i];
                }
                if (qanylim == 0 && qminmax == 0) {
//                    No parameter limits, so just move to new position WA2
                    alpha = 1;
                    for (i = 0; i < wa2.length; i++) {
                        wa2[i] = x[i] + wa1[i];
                    }

                }
                else {
//                    Respect the limits.  If a step were to go out of bounds, then
//                    we should take a step in the same direction but shorter distance.
//                    The step should take us right to the limit in that case.
                    alpha = 1;
                    if (qanylim) {
//                        Do not allow any steps out of bounds
                        catch_msg = 'checking for a step out of bounds';
                        if (nlpeg > 0) //very questionable
                        {
                            for (i = 0; i < whlpeg.length; i++) {
                                if (wa1[whlpeg[i]] < 0) {
                                    wa1[whlpeg[i]] = 0;
                                } else if (wa1[whlpeg[i]] > Math.max(wa1)) {
                                    wa1[whlpeg[i]] = Math.max(wa1);
                                }
                            }
                        }
                        if (nupeg > 0) {
                            for (i = 0; i < whupeg.length; i++) {
                                if (wa1[whupeg[i]] > 0) {
                                    wa1[whupeg[i]] = 0;
                                } else if (wa1[whupeg[i]] < Math.min(wa1)) {
                                    wa1[whupeg[i]] = Math.min(wa1);
                                }
                            }
                        }
                        var dwa1 = true;
                        var whl=[];
                        for (i = 0; i < wa1.length; i++) {
                            if (qllim[i] && (x[i] + wa1[i]) < llim[i]) {
                                wh1.push(i);
                            }
                        }
                        if (whl.length > 0) {
                            var t=[];
                            for (i = 0; i < whl.length; i++) {
                                t.push((llim[whl[i]] - x[whl[i]]) / wa1[whl[i]]);
                                alpha = Math.min(alpha, t);
                            }
                        }
                        var whu=[];
                        for (i = 0; i < wa1.length; i++) {
                            if (qulim[i] && (x[i] + wa1[i]) > ulim[i]) {
                                whu.push(i);
                            }
                        }
                        if (whu.length > 0) {
                            var t=[];
                            for (i = 0; i < whl.length; i++) {
                                t.push((ulim[whu[i]] - x[whu[i]]) / wa1[whu[i]]);
                                alpha = Math.min(alpha, t);
                            }
                        }

                    }

//                    Obey any max step values

                    if (qminmax) {
                        var nwa1=[];
                        for (i = 0; i < wa1.length; i++) {
                            nwa1.push(wa1[i] * alpha);
                        }
                        var whmax=[];
                        for (i = 0; i < qmax.length; i++) {
                            if (qmax[i] != 0 && maxstep[i] > 0) {
                                whmax.push(i);
                            }
                        }
                        if (whmax.length > 0) {
                            var mrat=[];
                            for (i = 0; i < whmax.length; i++) {
                                mrat.push(Math.max(Math.abs(nwa1[whmax[i]]), Math, abs(maxstep[ifree[whmax[i]]])));
                            }
                            if (mrat.length > 1)//questionable move from array to scalar
                            {
                                alpha = alpha / mrat;
                            }
                        }

                    }

//                    Scale the resulting vector

                    for (i = 0; i < wa1.length; i++) {
                        wa1[i] = wa1[i] * alpha;

                    }
                    for (i = 0; i < wa2.length; i++) {
                        wa2[i] = x[i] + wa1[i];
                    }

//                    Adjust the final output values.  If the step put us exactly
//                    on a boundary, make sure it is exact.
                    var sgnu=[];
                    for (i = 0; i < ulim.length; i++) {
                        if (ulim[i] >= 0) {
                            sgnu.push(1);
                        } else {
                            sgnu.push(-1);
                        }

                    }
                    var sgnl=[];
                    for (i = 0; i < llim.length; i++) {
                        if (llim[i] >= 0) {
                            sgnl.push(1);
                        } else {
                            sgnl.push(-1);
                        }

                    }

//                      Handles case of
//                            ... nonzero *LIM ... ...zero * LIM

                    //skip some rounding
                    var ulim1=[];
                    for(var i=0; i<ulim.length; i++){
                        ulim1.push(ulim[i]);
                    }
                    var llim1 = [];
                    for(var i=0; i<llim.length; i++){
                        llim1.push(llim[i]);
                    }
                    var wh=[];
                    for (i = 0; i < qulim; i++) {
                        if (qulim[i] != 0 && wa2[i] >= ulim1[i]) {
                            wh.push(i);
                        }
                    }
                    if (wh.length > 0) {
                        for (i = 0; i < wh.length; i++) {
                            wa2[wh[i]] = ulim[wh[i]];
                        }
                    }
                    var wh=[];
                    for (i = 0; i < qllim; i++) {
                        if (qllim[i] != 0 && wa2[i] >= llim1[i]) {
                            wh.push(i);
                        }
                    }
                    if (wh.length > 0) {
                        for (i = 0; i < wh.length; i++) {
                            wa2[wh[i]] = llim[wh[i]];
                        }
                    }

                }//endelse
                var wa3=[];
                for (i = 0; i < wa1.length; i++) {
                    wa3.push(diag[i] * wa1[i]);
                }
                var pnorm = lmfit.enorm(wa3);

//                On the first iteration, adjust the initial step bound
                if (this.niter == 1) {
                    delta = Math.min(delta, pnorm);
                }
                for (i = 0; i < ifree.length; i++) {
                    this.params[ifree[i]] = wa2[i];
                }

//                Evaluate the function at x+p and calculate its norm
                mperr = 0;
                catch_msg = 'calling fcn';
                var a = lmfit.call(fcn, this.params, functkw);
                this.status = a.status;
                wa4 = a.f;
                if (this.status < 0) {
                    this.errmsg = 'warning: premature termination by fcn';
                    return;
                }
                fnorm1 = lmfit.enorm(wa4);

//                Compute the scaled actual reduction
                catch_msg = 'computing convergence criteria';
                var actred = -1;
                if (.1 * fnorm1 < this.fnorm) {
                    actred = -Math.pow(fnorm1 / this.fnorm, 2) + 1;

                }

//                Compute the scaled predicted reduction and the scaled directional
//                derivative
                for (j = 0; j < n; j++) {
                    wa3[j] = 0;
                    for (i = 0; i < j + 1; i++) {
                        wa3[i] = wa3[i] + fjac[i][j] * wa1[ipvt[j]];
                    }
                }

//                Remember, alpha is the fraction of the full LM step actually
//                taken
                var j=[];
                for(i=0; i<wa3.length; i++)
                {
                    j.push(alpha*wa3[i]);
                }
                var temp1 = lmfit.enorm(j) / this.fnorm;
                var temp2 = (Math.sqrt(alpha * par) * pnorm) / this.fnorm;
                var prered = temp1 * temp1 + (temp2 * temp2) / 0.5;
                var dirder = -(temp1 * temp1 + temp2 * temp2);

//                Compute the ratio of the actual to the predicted reduction.
                var ratio = 0;
                if (prered != 0) {
                    ratio = actred / prered;
                }

//                Update the step bound
                if (ratio <= .25) {
                    if (actred >= 0) {
                        temp = .5;
                    }
                    else {
                        temp = .5 * dirder / (dirder + .5 * actred);
                    }
                    if ((0.1 * fnorm1) >= this.fnorm || (temp < 0.1)) {
                        temp = .1
                    }
                    delta = temp * Math.min(delta, pnorm / .1);
                    par = par / temp;
                }
                else {
                    if (par == 0 || ratio >= .75) {
                        delta = pnorm / .5;
                        par = .5 * par;
                    }
                }
//                Test for successful iteration
                if (ratio >= .0001) {
//                    Successful iteration.  Update x, fvec, and their norms
                    for (i = 0; i < wa2.length; i++) {
                        x[i] = wa2[i];

                    }
                    for (i = 0; i < x.length; i++) {
                        wa2[i] = diag[i] * x[i];
                    }
                    fvec = wa4;
                    xnorm = lmfit.enorm(wa2);
                    this.fnorm = fnorm1;
                    this.niter++;


                }

//                Tests for convergence
                if (Math.abs(actred) <= ftol && (prered <= ftol) && (0.5 * ratio <= 1)) {
                    this.status = 1;
                }
                if (delta <= xtol * xnorm) {
                    this.status = 2;
                }
                if ((Math.abs(actred) <= ftol) && (prered <= ftol) && (0.5 * ratio <= 1) && (this.status == 2)) {
                    this.status = 3;
                }
                if (this.status != 0) {
                    break;
                }

//                Tests for termination and stringent tolerances
                if (this.niter >= maxiter) {
                    this.status = 5;
                }

                if (Math.abs(actred) <= machep && prered <= machep && .5 * ratio <= 1) {
                    this.status = 6;
                }
                if (delta <= machep * xnorm) {
                    this.status = 7;
                }
                if (gnorm <= machep) {
                    this.status = 8;
                }
                if (this.status != 0) {
                    break;
                }
//                End of inner loop. Repeat if iteration unsuccessful
                if (ratio >= .0001) {
                    break;
                }
                //DO THIS overflow check skipped
//                Check for over/underflow
//                if ~numpy.all(numpy.isfinite(wa1) & numpy.isfinite(wa2) & \
//                numpy.isfinite(x)) or ~numpy.isfinite(ratio):
//                errmsg = ('''ERROR: parameter or function value(s) have become
//                'infinite; check model function for over- 'and underflow''')
//                self.status = -16
//                break

//                wh = where(finite(wa1) EQ 0 OR finite(wa2) EQ 0 OR finite(x) EQ 0, ct)
//                if ct GT 0 OR finite(ratio) EQ 0 then begin

            }
            if (this.status != 0) {
                break;
            }

        }//end of outer loop
        catch_msg = 'in the termination phase';
//        Termination, either normal or user imposed.
        if (this.params.length == 0) {
            return;
        }
        if (nfree == 0) {
            this.params=[];
            for(i=0; i<xall.length; i++)
            {
                this.params.push(xall[i]);
            }
        }
        else {
            for (i = 0; i < ifree.length; i++) {
                this.params[ifree[i]] = x[i];
            }
        }
        if (nprint < 0 && this.status > 0) {
            catch_msg = 'calling fcn';
            var a = lmfit.call(fcn, this.params, functkw);
            status = a.status;
            fvec = a.f;
            catch_msg = 'in the termination phase';
            this.fnorm = lmfit.enorm(fvec);
        }
        if (lmfit.typeOf(this.fnorm) != 'undefined' && lmfit.typeOf(fnorm1) != 'undefined') {
            this.fnorm = Math.max(this.fnorm, fnorm1);
            this.fnorm = Math.pow(this.fnorm, 2);
        }
        this.covar = undefined;
        this.perror = undefined;
//        (very carefully) set the covariance matrix COVAR
        if (this.status > 0 && nocovar == 0 && lmfit.typeOf(n) != 'undefined' && lmfit.typeOf(fjac) != 'undefined' && lmfit.typeOf(ipvt) != 'undefined') {
            var sz = [fjac.length, fjac[0].length];
            if (n > 0 && sz[0] >= n && sz[1] >= n && ipvt.length >= n) {
                catch_msg = 'computing the covariance matrix';
                var tempfjac=new Array(n), tempipvt=new Array(n);
                for (i = 0; i < n; i++) {
                    tempfjac[i]=new Array(n);
                    for (j = 0; j < n; j++) {
                        tempfjac[i][j] = fjac[i][j];
                    }
                    tempipvt[i] = ipvt[i];
                }
                var cv = lmfit.calc_covar(tempfjac, tempipvt);

//                var tempcv = [];
//                for(i=0; i<cv.length; i++){
//                    tempcv[i]=cv[i];
//                }
//                cv = new Array(n);
//                var counter = 0;
//                for (i = 0; i < n; i++) {
//                    cv[i]=new Array(n);
//                    for (j = 0; j < n; j++) {
//                        cv[i][j] = tempcv[counter];
//                        counter++;
//                    }
//                }
                var nn = xall.length;

//                Fill in actual covariance matrix, accounting for fixed
//                parameters.
                this.covar=new Array(nn);
                for (i = 0; i < nn; i++) {
                    this.covar[i]=[];
                    for (j = 0; j < nn; j++) {
                        this.covar[i].push(0);
                    }
                }
                for (i = 0; i < n; i++) {
                    for (j = 0; j < ifree.length; j++) {
                        this.covar[ifree[j]][ifree[i]] = cv[j][i];
                    }
                }

//                Compute errors in parameters
                catch_msg = 'computing parameter errors';
                this.perror=[];
                for (i = 0; i < nn; i++) {
                    this.perror.push(0);
                }
                var tempcovar = Matrix.create(this.covar);
                var d = tempcovar.diagonal().elements;
                wh = [];
                for (i = 0; i < d.length; i++) {
                    if (d[i] >= 0) {
                        wh.push(i);
                    }
                }
                if (wh.length > 0) {
                    for (i = 0; i < wh.length; i++) {
                        this.perror[wh[i]] = Math.sqrt(d[wh[i]]);
                    }
                }
		console.log(this.covar);
            }
        }
        return {p:x, covar: this.covar, error: this.perror, chisq: this.fnorm};
    };

    /*
     Procedure to parse the parameter values in PARINFO, which is a list of dictionaries
     */
    lmfit.parinfo = function (parinfo, key, def, n) {
        if(this.debug) {
            console.log('entering parinfo');
        }
        var values;
        if (lmfit.typeOf(key) == 'undefined') {
            key = 'a';
        }
        if (lmfit.typeOf(n) == 'undefined') {
            n = 0;
        }
        if (n == 0 && lmfit.typeOf(parinfo) != 'undefined') {
            n = parinfo.length;
        }
        if (n == 0) {
            values = def;
            return {values: values};
        }
        values = [];
        for (i = 0; i < n; i++) {
            if (lmfit.typeOf(parinfo) != 'undefined') //unchecked for the key because no dictionary
            {
                values.push(parinfo[i][key]);
            } else {
                values.push(def);
            }

        }

//        Convert to numeric arrays if possible
        return values;
    };

    /*
     Call user function or procedure, with _EXTRA or not, with
     derivatives or not.
     */
    lmfit.call = function (fcn, x, functkw, fjac) {
        if(this.debug) {
            console.log('entering call...');
        }
        if (this.qantied) {
            x = lmfit.tie(x, this.ptied);
        }
        this.nfev = this.nfev + 1;
        var x1 = [], y = [], err = [];
        x1 = functkw['x'];
        y = functkw['y'];
	err=functkw['err'];
        if (lmfit.typeOf(fjac) == 'undefined') {
            var a = fcn(x, fjac, x1, y, err); //some funk with double astericks
            var status = a.status;
            var f = a.f;
            if (this.damp > 0) {
//                  Apply the damping if requested.  This replaces the residuals
//                  with their hyperbolic tangent.  Thus residuals larger than
//                  DAMP are essentially clipped.
                f = Math.tanh(f / this.damp);
            }
            return {status: status, f: f};
        } else {
            var a = fcn(x, fjac, functkw);
            return {
                status: a.status,
                f: a.f
            };
        }

    };

    /*
     Call user function or procedure, with _EXTRA or not, with
     derivatives or not.
     */
    lmfit.fdjac2 = function (fcn, x, fvec, step, ulimited, ulimit, dside, epsfcn, autoderivative, functkw, xall, ifree, dstep) { //no clue what types any of these are
        if(this.debug) {
            console.log('entering fdjac2...');
        }
        if (lmfit.typeOf(autoderivative) == 'undefined') {
            autoderivative = 1;
        }
        var machep = Math.pow(2, -52);
        if (lmfit.typeOf(epsfcn) == 'undefined') {
            epsfcn = machep;
        }
        if (lmfit.typeOf(xall) == 'undefined') {
            xall = x;
        }
        if (lmfit.typeOf(ifree) == 'undefined') {
            ifree=[];
            for (i = 0; i < xall.length; i++) {
                ifree.push(i);
            }
        }
        if (lmfit.typeOf(step) == 'undefined') {
            step = x * 0;
        }
        var nall = xall.length;

        var eps = Math.sqrt(Math.max(epsfcn, machep));
        var m = fvec.length;
        var n = x.length;
        var mperr = 0;
        var fjac = [];
//        Compute analytical derivative if requested
        if (autoderivative == 0) {


            for (i = 0; i < nall; i++) {
                fjac.push(0);
            }
            fjac[ifree] = 1;
            var a = lmfit.call(fcn, xall, functkw, fjac);//questionable call
            var status = a.status;
            ;
            var fp = a.f;
            if (fjac.length != m * nall) {
                console.log('error: derivative matrix was not computed properly');
                return;
            }
//             This definition is consistent with CURVEFIT
//             Sign error found (thanks Jesus Fernandez <fernande@irm.chu-caen.fr>)
            var counter;
            var temp=[];
            for(var i=0; i<fjac.length; i++){
                temp.push(fjac[i]);
            }
            while (fjac.length > 0) {
                fjac.pop();
            }
            fjac = new Array(m);
            for (i = 0; i < m; i++) {
                fjac[i] = new Array(nall);
                for (j = 0; j < nall; j++) {
                    fjac[i][j] = temp[counter];
                    counter++;
                }
            }
            for (i = 0; i < m; i++) {
                for (j = 0; j < nall; j++) {
                    fjac[i][j] = -f[i][j];
                }
            }
            temp=[];
            for(var i=0; i<fjac.length; i++){
                temp.push(fjac[i]);
            }
            if (ifree.length < nall) {
                while (fjac.length > 0) {
                    fjac.pop();
                }
                for (i = 0; i < fjac.length; i++) {
                    fjac.push(temp[i][ifree]);
                }
                temp=[];
                for(var i=0; i<fjac.length; i++){
                    temp.push(fjac[i]);
                }
                counter = 0;
                for (i = 0; i < m; i++) {
                    for (j = 0; j < nall; j++) {
                        fjac[i][j] = temp[counter];
                    }
                }
                return fjac;
            }
        }
        fjac = new Array(m);
        for (i = 0; i < m; i++) {
            fjac[i] = new Array(nall);
            for (j = 0; j < nall; j++) {
                fjac[i][j] = 0;
            }
        }
        var h = [];
        for (i = 0; i < x.length; i++) {
            h.push(eps * x[i]);
        }
//         if STEP is given, use that
//         STEP includes the fixed parameters
        if (lmfit.typeOf(step) != 'undefined') {
            var stepi = [];
            for (i = 0; i < ifree.length; i++) {
                stepi[i] = step[ifree[i]];
            }
            var wh = [];
            for (i = 0; i < stepi.length; i++) {
                if (stepi[i] > 0) {
                    wh.push(i);
                }
            }
            if (wh.length > 0) {
                for (i = 0; i < wh.length; i++) {
                    h[wh[i]] = stepi[wh[i]];
                }
            }
        }
//         if relative step is given, use that
//         DSTEP includes the fixed parameters
        if (dstep.length > 0) {
            var dstepi = [];
            for (i = 0; i < ifree.length; i++) {
                dstepi[i] = dstep[ifree[i]];
            }
            for (i = 0; i < stepi.length; i++) {
                if (dstepi[i] > 0) {
                    wh.push(i);
                }
            }
            if (wh.length > 0) {
                for (i = 0; i < wh.length; i++) {
                    h[wh[i]] = Math.abs(dstepi[wh[i]] * x[wh[i]]);
                }
            }

        }
//        In case any of the step values are zero
        for (i = 0; i < h.length; i++) {
            if (h[i] == 0) {
                h[i] = eps;
            }
        }//questionable whether this is even needed
//         Reverse the sign of the step if we are up against the parameter
//         limit, or if the user requested it.
//         DSIDE includes the fixed parameters (ULIMITED/ULIMIT have only
//         varying ones)
        var check = [];
        for (i = 0; i < ifree.length; i++) {
            if (dside[ifree[i]] == -1) {
                check.push(true);
            } else {
                check.push(false);
            }
        }
        var mask = check;
        if (ulimited.length > 0 && ulimit.length > 0) {
            for (i = 0; i < ulimited.length; i++) {
                mask[i] = (mask[i] || (ulimited[i] != 0 && x > ulimit[i] - h[i]));
            }
            var wh=[];
            for (i = 0; i < mask.length; i++) {
                if (mask[i] != 0) {
                    wh.push(i);
                }
            }
            if (wh.length != 0) {
                for (i = 0; i < wh.length; i++) {
                    h[wh[i]] = -h[wh[i]];
                }
            }
        }
//        Loop through parameters, computing the derivative for each

        for (var z = 0; z < n; z++) {
            var xp = [];
            for (i = 0; i < xall.length; i++) {
                xp[i] = xall[i];
            }
            xp[ifree[z]] = xp[ifree[z]] + h[z];
            var a = lmfit.call(fcn, xp, functkw);
            var status = a.status;
            var fp = a.f;
            if (status < 0) {
                return;
            }
            if (Math.abs(dside[ifree[z]]) <= 1) {
//            # COMPUTE THE ONE-SIDED DERIVATIVE
//             Note optimization fjac(0:*,j)
                for (var i = 0; i < fjac.length; i++) {
                    fjac[i][z] = (fp[i] - fvec[i]) / h[z];
                }
            } else {

//             COMPUTE THE TWO-SIDED DERIVATIVE
                xp[ifree[z]] = xall[ifree[z]] - h[z]
                mperr = 0;
                var a = lmfit.call(fcn, xp, functkw);
                status = a.status;
                var fm = a.f;
                if (status < 0) {
                    return;
                }
//                 Note optimization fjac(0:*,j)
                for (i = 0; i < fjac; i++) {
                    fjac[i][z] = (fp - fm) / (2 * h[z]);
                }
            }
        }
        return {fjac: fjac};


    };

    /*Original FORTRAN documentation
     **********

     subroutine qrfac

     this subroutine uses householder transformations with column
     pivoting (optional) to compute a qr factorization of the
     m by n matrix a. that is, qrfac determines an orthogonal
     matrix q, a permutation matrix p, and an upper trapezoidal
     matrix r with diagonal elements of nonincreasing magnitude,
     such that a*p = q*r. the householder transformation for
     column k, k = 1,2,...,min(m,n), is of the form

     t
     i - (1/u(k))*u*u

     where u has zeros in the first k-1 positions. the form of
     this transformation and the method of pivoting first
     appeared in the corresponding linpack subroutine.

     the subroutine statement is

     subroutine qrfac(m,n,a,lda,pivot,ipvt,lipvt,rdiag,acnorm,wa)

     where

     m is a positive integer input variable set to the number
     of rows of a.

     n is a positive integer input variable set to the number
     of columns of a.

     a is an m by n array. on input a contains the matrix for
     which the qr factorization is to be computed. on output
     the strict upper trapezoidal part of a contains the strict
     upper trapezoidal part of r, and the lower trapezoidal
     part of a contains a factored form of q (the non-trivial
     elements of the u vectors described above).

     lda is a positive integer input variable not less than m
     which specifies the leading dimension of the array a.

     pivot is a logical input variable. if pivot is set true,
     then column pivoting is enforced. if pivot is set false,
     then no column pivoting is done.

     ipvt is an integer output array of length lipvt. ipvt
     defines the permutation matrix p such that a*p = q*r.
     column j of p is column ipvt(j) of the identity matrix.
     if pivot is false, ipvt is not referenced.

     lipvt is a positive integer input variable. if pivot is false,
     then lipvt may be as small as 1. if pivot is true, then
     lipvt must be at least n.

     rdiag is an output array of length n which contains the
     diagonal elements of r.

     acnorm is an output array of length n which contains the
     norms of the corresponding columns of the input matrix a.
     if this information is not needed, then acnorm can coincide
     with rdiag.

     wa is a work array of length n. if pivot is false, then wa
     can coincide with rdiag.

     subprograms called

     minpack-supplied ... dpmpar,enorm

     fortran-supplied ... dmax1,dsqrt,min0

     argonne national laboratory. minpack project. march 1980.
     burton s. garbow, kenneth e. hillstrom, jorge j. more

     **********

     PIVOTING / PERMUTING:

     Upon return, A(*,*) is in standard parameter order, A(*,IPVT) is in
     permuted order.

     RDIAG is in permuted order.
     ACNORM is in standard parameter order.


     NOTE: in IDL the factors appear slightly differently than described
     above.  The matrix A is still m x n where m >= n.

     The "upper" triangular matrix R is actually stored in the strict
     lower left triangle of A under the standard notation of IDL.

     The reflectors that generate Q are in the upper trapezoid of A upon
     output.

     EXAMPLE:  decompose the matrix [[9.,2.,6.],[4.,8.,7.]]
     aa = [[9.,2.,6.],[4.,8.,7.]]
     mpfit_qrfac, aa, aapvt, rdiag, aanorm
     IDL> print, aa
     1.81818*       0.181818*       0.545455*
     -8.54545+        1.90160*       0.432573*
     IDL> print, rdiag
     -11.0000+       -7.48166+

     The components marked with a * are the components of the
     reflectors, and those marked with a + are components of R.

     To reconstruct Q and R we proceed as follows.  First R.
     r = fltarr(m, n)
     for i = 0, n-1 do r(0:i,i) = aa(0:i,i)  # fill in lower diag
     r(lindgen(n)*(m+1)) = rdiag

     Next, Q, which are composed from the reflectors.  Each reflector v
     is taken from the upper trapezoid of aa, and converted to a matrix
     via (I - 2 vT . v / (v . vT)).

     hh = ident                                                             identity matrix
     for i = 0, n-1 do begin
     v = aa(*,i) & if i GT 0 then v(0:i-1) = 0       # extract reflector
     hh = hh # (ident - 2*(v # v)/total(v * v))  # generate matrix
     endfor

     Test the result:
     IDL> print, hh # transpose(r)
     9.00000         4.00000
     2.00000         8.00000
     6.00000         7.00000

     Note that it is usually never necessary to form the Q matrix
     explicitly, and MPFIT does not.*/
    lmfit.qrfac = function (b, pivot) {
        if(this.debug) {
            console.log("entering qrfac...");
        }
        if (lmfit.typeOf(pivot) == 'undefined') {
            pivot = 0;
        }
        var a = Matrix.create(b);

        var machep = Math.pow(2, -52);
        var sz = [b.length, b[0].length];
        var m = sz[0];
        var n = sz[1];

//        Compute the initial column norms and initialize arrays
        var acnorm = [];
        for (i = 0; i < n; i++) {
            acnorm.push(0);
        }
        for (j = 0; j < n; j++) {
            acnorm[j] = lmfit.enorm(a.col(j + 1).elements);
        }
        var rdiag = [];
        for (i = 0; i < acnorm.length; i++) {
            rdiag[i] = acnorm[i];
        }
        var wa = [];
        for (i = 0; i < rdiag.length; i++) {
            wa[i] = rdiag[i];
        }
        var ipvt = [];
        for (i = 0; i < n; i++) {
            ipvt.push(i);
        }
//        Reduce a to r with householder transformations
        var minmn = Math.min(m, n);
        for (j = 0; j < minmn; j++) {
            if (pivot != 0) {
//            Bring the column of largest norm into the pivot position
                var rmax = -100;
                for (i = j; i < rdiag.length; i++) {
                    rmax = Math.max(rmax, rdiag[i]);
                }
                var kmax = [];
                for (var i = j; i < rdiag.length; i++) {
                    if (rdiag[i] == rmax) {
                        kmax.push(i - j);
                    }
                }
                var ct = kmax.length;
                for (i = 0; i < kmax.length; i++) {
                    kmax[i] += j;
                }
                if (ct > 0) {
                    kmax = kmax[0];
//                      Exchange rows via the pivot only.  Avoid actually exchanging
//                      the rows, in case there is lots of memory transfer.  The
//                      exchange occurs later, within the body of MPFIT, after the
//                      extraneous columns of the matrix have been shed.
                    if (kmax != j) {
                        var temp = ipvt[j];
                        ipvt[j] = ipvt[kmax];
                        ipvt[kmax] = temp;
                        rdiag[kmax] = rdiag[j];
                        wa[kmax] = wa[j];
                    }
                }
            }
            var lj = ipvt[j];
            var ajj = [];
            for (i = j; i < a.elements.length; i++) {
                ajj.push(a.elements[i][lj]);
            }
            var ajnorm = lmfit.enorm(ajj);
            if (ajnorm == 0) {
                break;
            }
            if (a.elements[j][lj] < 0) {
                ajnorm = -ajnorm;
            }
            for (i = 0; i < ajj.length; i++) {
                ajj[i] = ajj[i] / ajnorm;
            }
            ajj[0] = ajj[0] + 1;
//             *** Note optimization a(j:*,j)
            for (i = j; i < a.elements.length; i++) {
                a.elements[i][lj] = ajj[i - j];
            }

//            Apply the transformation to the remaining columns
//            and update the norms
//
//            NOTE to SELF: tried to optimize this by removing the loop,
//            but it actually got slower.  Reverted to "for" loop to keep
//            it simple.
            var lk;
            var ajk = [];
            if (j + 1 < n) {
                for (k = j + 1; k < n; k++) {
                    lk = ipvt[k];
                    ajk = [];
                    for (i = j; i < a.elements.length; i++) {
                        ajk.push(a.elements[i][lk]);

                    }
//                    *** Note optimization a(j:*,lk)
//                    (corrected 20 Jul 2000)
                    if (a.elements[j][lj] != 0) {

                        var sum = 0;
                        for (i = 0; i < ajk.length; i++) {
                            sum += ajk[i] * ajj[i];
                        }
                        for (i = j; i < a.elements.length; i++) {

                            a.elements[i][lk] = ajk[i - j] - ajj[i - j] * sum / a.elements[j][lj];
                        }
                        if (pivot != 0 && rdiag[k] != 0) {
                            var temp = a.elements[j][lk] / rdiag[k];
                            rdiag[k] = rdiag[k] * Math.sqrt(Math.max(0, 1 - Math.pow(temp, 2)));
                            temp = rdiag[k] / wa[k];
                            if (0.05 * temp * temp <= machep) {
                                var temp1 = [];
                                for (i = j + 1; i < a.elements.length; i++) {
                                    temp1.push(a.elements[i][lk]);
                                }
                                rdiag[k] = lmfit.enorm(temp1);
                                wa[k] = rdiag[k];
                            }
                        }

                    }
                }
            }
            rdiag[j] = -ajnorm;
        }
        return {a: a.elements, ipvt: ipvt, rdiag: rdiag, acnorm: acnorm};


    };

    /* for debug purposes*/
    lmfit.__str__ = function () {
        return {
            params: this.params,
            niter: this.niter,
            covar: this.covar,
            perror: this.perror,
            status: this.status,
            debug: this.debug,
            errmsg: this.errmsg,
            nfev: this.nfev,
            damp: this.damp
        }
    };

    /*
     Default procedure to be called every iteration.  It simply prints
     the parameter values.
     */
    lmfit.defiter = function (fcn, x, iter, fnorm, functkw, quiet, iterstop, parinfo, format, pformat, dof) {
        if(this.debug) {
            console.log('entering defiter...');
        }
        if (lmfit.typeOf(quiet) == 'undefined') {
            quiet = 0;
        }
        if (lmfit.typeOf(pformat) == 'undefined') {
            pformat = '%.10g';
        }
        if (lmfit.typeOf(dof) == 'undefined') {
            dof = 1;
        }
        if (quiet) {
            return;
        }
        if (lmfit.typeOf(fnorm) == 'undefined') {
            var a = lmfit.call(fcn, x, functkw);
            var status = a.status;
            var fvec = a.f;
            fnorm = Math.pow(lmfit.enorm(fvec), 2);
        }
//        Determine which parameters to print
        var nprint = x.length;
        console.log("Iter:" + iter + " Chi-sq:" + fnorm + " DOF:" + dof);
        /*for(var key in parinfo)
         {
         var obj=parinfo[key];
         for (var prop in obj)
         {
         if (obj.hasOwnProperty(prop))
         {
         console.log(key+": "+obj);
         }
         }
         }*/
        var a;
        for (i = 0; i < nprint; i++) {
            if (lmfit.typeOf(parinfo) != 'undefined' && lmfit.typeOf(parinfo[i]['parname']) != 'undefined') {
                a = '   ' + parinfo[i]['parname'] + ' = ';
            } else {
                a = '   P' + i + ' = ';
            }
            if (lmfit.typeOf(parinfo) != 'undefined' && lmfit.typeOf(parinfo[i]['mpprint']) != 'undefined') {
                iprint = parinfo[i]['mpprint'];
            } else {
                iprint = 1;
            }
            if (iprint) {
                console.log(a + x[i]);
            }

        }
        return 0;

    };

    /*
     Original FORTRAN documentation
     **********

     subroutine qrsolv

     given an m by n matrix a, an n by n diagonal matrix d,
     and an m-vector b, the problem is to determine an x which
     solves the system

     a*x = b ,     d*x = 0 ,

     in the least squares sense.

     this subroutine completes the solution of the problem
     if it is provided with the necessary information from the
     factorization, with column pivoting, of a. that is, if
     a*p = q*r, where p is a permutation matrix, q has orthogonal
     columns, and r is an upper triangular matrix with diagonal
     elements of nonincreasing magnitude, then qrsolv expects
     the full upper triangle of r, the permutation matrix p,
     and the first n components of (q transpose)*b. the system
     a*x = b, d*x = 0, is then equivalent to

     t        t
     r*z = q *b ,  p *d*p*z = 0 ,

     where x = p*z. if this system does not have full rank,
     then a least squares solution is obtained. on output qrsolv
     also provides an upper triangular matrix s such that

     t   t                      t
     p *(a *a + d*d)*p = s *s .

     s is computed within qrsolv and may be of separate interest.

     the subroutine statement is

     subroutine qrsolv(n,r,ldr,ipvt,diag,qtb,x,sdiag,wa)

     where

     n is a positive integer input variable set to the order of r.

     r is an n by n array. on input the full upper triangle
     must contain the full upper triangle of the matrix r.
     on output the full upper triangle is unaltered, and the
     strict lower triangle contains the strict upper triangle
     (transposed) of the upper triangular matrix s.

     ldr is a positive integer input variable not less than n
     which specifies the leading dimension of the array r.

     ipvt is an integer input array of length n which defines the
     permutation matrix p such that a*p = q*r. column j of p
     is column ipvt(j) of the identity matrix.

     diag is an input array of length n which must contain the
     diagonal elements of the matrix d.

     qtb is an input array of length n which must contain the first
     n elements of the vector (q transpose)*b.

     x is an output array of length n which contains the least
     squares solution of the system a*x = b, d*x = 0.

     sdiag is an output array of length n which contains the
     diagonal elements of the upper triangular matrix s.

     wa is a work array of length n.

     subprograms called

     fortran-supplied ... dabs,dsqrt
     argonne national laboratory. minpack project. march 1980.
     burton s. garbow, kenneth e. hillstrom, jorge j. more*/
    lmfit.qrsolv = function (r, ipvt, diag, qtb, sdiag) {
        if(this.debug) {
        console.log("entering qrsolv");
        }
        var sz = r.dimensions();
        var m = sz.rows;
        var n = sz.cols;

//         copy r and (q transpose)*b to preserve input and initialize s.
//         in particular, save the diagonal elements of r in x.

        for (var j = 0; j < n; j++) {
            for (var i = 0; i < n; i++) {
                r.elements[i][j] = r.elements[j][i];
            }
        }
        var x = r.diagonal().elements;
        var wa =[];
            for(i=0; i<qtb.length; i++)
            {
             wa[i]=qtb[i];
            }

//       Eliminate the diagonal matrix d using a givens rotation

        for (j = 0; j < n; j++) {
            var l = ipvt[j];
            if (diag[l] == 0) {
                break;
            }
            for (i = j; i < sdiag.length; i++) {
                sdiag[i] = 0;
            }
            sdiag[j] = diag[l];

//            The transformations to eliminate the row of d modify only a
//            single element of (q transpose)*b beyond the first n, which
//            is initially zero.

            var qtbpj = 0;
            for (var k = j; k < n; k++) {
                if (sdiag[k] == 0) {
                    break;
                }
                var cotan, sine, cosine, tang;
                if (Math.abs(r.elements[k][k]) < Math.abs(sdiag[k])) {
                    cotan = r.elements[k][k] / sdiag[k];
                    sine = 0.5 / Math.sqrt(.25 + .25 * cotan * cotan);
                    cosine = sine * cotan;
                } else {
                    tang = sdiag[k] / r.elements[k][k];
                    cosine = 0.5 / Math.sqrt(.25 + .25 * tang * tang);
                    sine = cosine * tang;
                }

//                Compute the modified diagonal element of r and the
//                modified element of ((q transpose)*b,0).

                r.elements[k][k] = cosine * r.elements[k][k] + sine * sdiag[k];
                var temp = cosine * wa[k] + sine * qtbpj;
                qtbpj = -sine * wa[k] + cosine * qtbpj;
                wa[k] = temp;

//                Accumulate the transformation in the row of s

                if (n > k + 1) {
                    temp=[];
                    for (i = k + 1; i < n; i++) {
                        temp.push(cosine * r.elements[i][k] + sine * sdiag[i]);
                    }
                    for(i=k+1; i<n; i++) {
                        sdiag[i] = -sine * r.elements[i][k] + cosine * sdiag[i];
                    }
                    for(i=k+1; i<n; i++){
                        r.elements[i][k] = temp[i-k-1];
                    }
                }
            }
            sdiag[j] = r.elements[j][j];
            r.elements[j][j] = x[j];


        }
//          Solve the triangular system for z.  If the system is singular
//          then obtain a least squares solution
        var nsing = n;
        var wh=[];
        for (i = 0; i < sdiag.length; i++) {
            if (sdiag[i] == 0) {
                wh.push(i);

            }
        }
        if (wh.length > 0) {
            nsing = wh[0];
            for (i = nsing; i < wa.length; i++) {
                wa[i] = 0;
            }
        }
        if (nsing >= 1) {
            wa[nsing - 1] = wa[nsing - 1] / sdiag[nsing - 1];
            for (j = nsing - 2; j > -1; j--) {
                var sum0=0;

                for (k = j + 1; k < nsing; k++) {
                    sum0 += r.elements[k][j] * wa[k];
                }
                wa[j] = (wa[j] - sum0) / sdiag[j];
            }
        }

//        Permute the components of z back to components of x

        for(i=0; i<ipvt.length; i++) {
            x[ipvt[i]] = wa[i];  //questionable; ipvt is a 1d array, x is a 1d array
        }
        return {r: r, x: x, sdiag: sdiag};      //questionable return


    };

    /*        Original FORTRAN documentation

     subroutine lmpar

     given an m by n matrix a, an n by n nonsingular diagonal
     matrix d, an m-vector b, and a positive number delta,
     the problem is to determine a value for the parameter
     par such that if x solves the system

     a*x = b ,        sqrt(par)*d*x = 0 ,

     in the least squares sense, and dxnorm is the euclidean
     norm of d*x, then either par is zero and

     (dxnorm-delta) .le. 0.1*delta ,

     or par is positive and

     abs(dxnorm-delta) .le. 0.1*delta .

     this subroutine completes the solution of the problem
     if it is provided with the necessary information from the
     qr factorization, with column pivoting, of a. that is, if
     a*p = q*r, where p is a permutation matrix, q has orthogonal
     columns, and r is an upper triangular matrix with diagonal
     elements of nonincreasing magnitude, then lmpar expects
     the full upper triangle of r, the permutation matrix p,
     and the first n components of (q transpose)*b. on output
     lmpar also provides an upper triangular matrix s such that

     t   t                             t
     p *(a *a + par*d*d)*p = s *s .

     s is employed within lmpar and may be of separate interest.

     only a few iterations are generally needed for convergence
     of the algorithm. if, however, the limit of 10 iterations
     is reached, then the output par will contain the best
     value obtained so far.

     the subroutine statement is

     subroutine lmpar(n,r,ldr,ipvt,diag,qtb,delta,par,x,sdiag,
     wa1,wa2)

     where

     n is a positive integer input variable set to the order of r.

     r is an n by n array. on input the full upper triangle
     must contain the full upper triangle of the matrix r.
     on output the full upper triangle is unaltered, and the
     strict lower triangle contains the strict upper triangle
     (transposed) of the upper triangular matrix s.

     ldr is a positive integer input variable not less than n
     which specifies the leading dimension of the array r.

     ipvt is an integer input array of length n which defines the
     permutation matrix p such that a*p = q*r. column j of p
     is column ipvt(j) of the identity matrix.

     diag is an input array of length n which must contain the
     diagonal elements of the matrix d.

     qtb is an input array of length n which must contain the first
     n elements of the vector (q transpose)*b.

     delta is a positive input variable which specifies an upper
     bound on the euclidean norm of d*x.

     par is a nonnegative variable. on input par contains an
     initial estimate of the levenberg-marquardt parameter.
     on output par contains the final estimate.

     x is an output array of length n which contains the least
     squares solution of the system a*x = b, sqrt(par)*d*x = 0,
     for the output par.

     sdiag is an output array of length n which contains the
     diagonal elements of the upper triangular matrix s.

     wa1 and wa2 are work arrays of length n.

     subprograms called

     minpack-supplied ... dpmpar,enorm,qrsolv

     fortran-supplied ... dabs,dmax1,dmin1,dsqrt

     argonne national laboratory. minpack project. march 1980.
     burton s. garbow, kenneth e. hillstrom, jorge j. more
     */
    lmfit.lmpar = function (y, ipvt, diag, qtb, delta, x, sdiag, par) {  //must check the typeOf r array/matrix
        if(this.debug) {
            console.log('entering lmpar...');
        }
        r=Matrix.create(y);
        var sz = [y.length, y[0].length];
        var m = sz[0];
        var n = sz[1];

//         Compute and store in x the gauss-newton direction.  If the
//         jacobian is rank-deficient, obtain a least-squares solution

        var nsing = n;

        var wa1 = [];
        for(i=0; i<qtb.length; i++){
            wa1[i]=qtb[i];
        }
        //skipping some rounding stuffs
        if (nsing >= 1) {
            for (j = nsing - 1; j > -1; j--) {
                wa1[j] = wa1[j] / r.elements[j][j];
                if (j - 1 >= 0) {
                    for (i = 0; i < j; i++) {
                        wa1[i] = wa1[i] - r.elements[i][j] * wa1[j];
                    }
                }
            }
        }
//      Note: ipvt here is a permutaiton array
        for(i=0; i<ipvt.length; i++)
        {
            x[ipvt[i]]=wa1[i];
        }
        //x[ipvt] = wa1; //questionble "permutation array"

        var iter = 0;
        var wa2=[];
        for(i=0; i<diag.length; i++) {
            wa2.push(diag[i] * x[i]);//may have to change this because javascript doesn't support array * array operatoins
        }
        var dxnorm = lmfit.enorm(wa2);
        var fp = dxnorm - delta;
        if (fp <= 0.1 * delta) {
            return {r: r.elements, par:0, x:x, sdiag:sdiag};
        }
//         If the jacobian is not rank deficient, the newton step provides a
//         lower bound, parl, for the zero of the function.  Otherwise set
//         this bound to zero.

        var parl = 0;
        if (nsing >= n) {
            for(i=0; i<ipvt.length; i++) {
                wa1[i] = diag[ipvt[i]] * wa2[ipvt[i]] / dxnorm;//again the permutation array questionability
            }
            wa1[0] = wa1[0] / r.elements[0][0];
            for (j = 1; j < n; j++) {
                var sum0=0;
                for (i = 0; i < j; i++) {
                    sum0 += r.elements[i][j] * wa1[i];


                }
                wa1[j] = (wa1[j] - sum0) / r.elements[j][j];
            }
            var temp = lmfit.enorm(wa1);
            parl = ((fp / delta) / temp) / temp;


        }
//             Calculate an upper bound, paru, for the zero of the function
        for (j = 0; j < n; j++) {
            var sum0=0;
            for (i = 0; i < j + 1; i++) {
                sum0 += r.elements[i][j] * qtb[i];

            }
            wa1[j] = sum0 / diag[ipvt[j]];
        }
        var gnorm = lmfit.enorm(wa1);
        var paru = gnorm / delta;
        //skip some rounding checks
//         If the input par lies outside of the interval (parl,paru), set
//         par to the closer endpoint
        if (lmfit.typeOf(par) == 'undefined') {
            par = parl;
            par = Math.min(par, paru);
        } else {
            par = Math.max(par, parl);
            par = Math.min(par, paru);
        }
        if (par == 0) {
            par = gnorm / dxnorm;
        }
//        Beginning of an interation
        while (true)  //unsure whether it will throw an exception
        {
            iter++;
//            Evaluate the function at the current value of par
            var temp = Math.sqrt(par);
            wa1=[];
            for(var i=0; i<diag.length; i++) {
                wa1[i] = temp * diag[i]; //unsure whether will throw error due to scalar*array
            }
            var a = lmfit.qrsolv(r, ipvt, wa1, qtb, sdiag);
            r = a.r;
            x = a.x;
            sdiag = a.sdiag;
            for(i=0; i<diag.length; i++) {
                wa2[i] = diag[i] * x[i];
            }
            dxnorm = lmfit.enorm(wa2);
            temp = fp;
            fp = dxnorm - delta;

            if ((Math.abs(fp) <= 0.1 * delta) || ((parl == 0) && (fp <= temp) && (temp < 0)) || (iter == 10)) {
                break;
            }
//            Compute the newton correction
            for(i=0; i<ipvt.length; i++) {
                wa1[i] = diag[ipvt[i]] * wa2[ipvt[i]] / dxnorm;
            }
            for (j = 0; j < n - 1; j++) {
                wa1[j] = wa1[j] / sdiag[j];
                for (i = j + 1; j < n; j++) {
                    wa1[i] = wa1[1] - r.elements[i][j] * wa1[j];

                }
            }
            wa1[n - 1] = wa1[n - 1] / sdiag[n - 1];
            temp = lmfit.enorm(wa1);
            var parc = ((fp / delta) / temp) / temp;
//            Depending on the sign of the function, update parl or paru
            if (fp > 0) {
                par = Math.max(parl, par);
            }
            if (fp < 0) {
                paru = Math.min(paru, par);
            }
//            Compute an improved estimate for par
            par = Math.max(parl, par + parc);
//            End of an iteration
        }
//        Termination
        return {r: r.elements, par: par, x: x, sdiag: sdiag};
    };


    /*
     Procedure to tie one parameter to another
     */
    lmfit.tie = function (p, ptied) {
        if(this.debug) {
            console.log('entering tie...');
        }
        if (lmfit.typeOf(ptied) == 'undefined') {
            return;
        }
        for (i = 0; i < ptied.length; i++) {
            p[i] = ptied[i];
        }
        return p;
    };

    /*             Original FORTRAN documentation
     **********

     subroutine covar

     given an m by n matrix a, the problem is to determine
     the covariance matrix corresponding to a, defined as

     t
     inverse(a *a) .

     this subroutine completes the solution of the problem
     if it is provided with the necessary information from the
     qr factorization, with column pivoting, of a. that is, if
     a*p = q*r, where p is a permutation matrix, q has orthogonal
     columns, and r is an upper triangular matrix with diagonal
     elements of nonincreasing magnitude, then covar expects
     the full upper triangle of r and the permutation matrix p.
     the covariance matrix is then computed as

     t      t
     p*inverse(r *r)*p  .

     if a is nearly rank deficient, it may be desirable to compute
     the covariance matrix corresponding to the linearly independent
     columns of a. to define the numerical rank of a, covar uses
     the tolerance tol. if l is the largest integer such that

     abs(r(l,l)) .gt. tol*abs(r(1,1)) ,

     then covar computes the covariance matrix corresponding to
     the first l columns of r. for k greater than l, column
     and row ipvt(k) of the covariance matrix are set to zero.

     the subroutine statement is

     subroutine covar(n,r,ldr,ipvt,tol,wa)

     where

     n is a positive integer input variable set to the order of r.

     r is an n by n array. on input the full upper triangle must
     contain the full upper triangle of the matrix r. on output
     r contains the square symmetric covariance matrix.

     ldr is a positive integer input variable not less than n
     which specifies the leading dimension of the array r.

     ipvt is an integer input array of length n which defines the
     permutation matrix p such that a*p = q*r. column j of p
     is column ipvt(j) of the identity matrix.

     tol is a nonnegative input variable used to define the
     numerical rank of a in the manner described above.

     wa is a work array of length n.

     subprograms called

     fortran-supplied ... dabs

     argonne national laboratory. minpack project. august 1980.
     burton s. garbow, kenneth e. hillstrom, jorge j. more

     **********/
    lmfit.calc_covar = function (rr, ipvt, tol) {
        if(this.debug) {
            console.log("entering calc_covar...");
        }
        if (lmfit.typeOf(rr.length) == 'undefined' || lmfit.typeOf(rr[0].length) == 'undefined') {
            console.log("rr not 2d array, calc_covar failed");
            return -1;

        }
        var s = [rr.length, rr[0].length];
        var n = s[0];
        if (s[0] != s[1]) {
            console.log("r must be square matrix");
            return -1;
        }
        if (ipvt == lmfit.typeOf('undefined')) {//unsure whether this actually catches a null imput
            ipvt=[];
            for (i = 0; i < n; i++) {
                ipvt.push(i);
            }
        }
        var r = [];
        for(i=0; i<rr.length; i++){
            r[i]=rr[i];
        }
        r.shape = [n, n]; //unsure whether this will actually do anything

//        For the inverse of r in the full upper triangle of r
        var l = -1;
        if (lmfit.typeOf(tol) == 'undefined') {
            tol = 1 * Math.pow(10, -14);
        }
        var tolr = tol * Math.abs(r[0][0]);
        var temp;
        for (k = 0; k < n; k++) {
            if (Math.abs(r[k][k]) <= tolr) {
                break;
            }
            r[k][k] = 1 / r[k][k];
            for (j = 0; j < k; j++) {
                temp = r[k][k] * r[j][k];
                r[j][k] = 0;
                for (i = 0; i < j + 1; i++) {
                    r[i][k] = r[i][k] - temp * r[i][j];
                }
                
            }
            l = k;

        }

//          Form the full upper triangle of the inverse of (r transpose)*r
//          in the full upper triangle of r
        if (l >= 0) {
            for (k = 0; k < l + 1; k++) {
                for (j = 0; j < k; j++) {
                    temp = r[j][k];
                    for (i = 0; i < j + 1; i++) {
                        r[i][j] = r[i][j] + temp * r[i][k];
                    }
                    
                }
				temp = r[k][k];
                for (i = 0; i < k + 1; i++) {
                    r[i][k] = temp * r[i][k];
                    }
            }
        }
//         For the full lower triangle of the covariance matrix
//         in the strict lower triangle or and in wa
        var wa=[];
        for (i = 0; i < n; i++) {
            wa.push(r[0][0]);
        }
        for (j = 0; j < n; j++) {
            var jj = ipvt[j];
            sing = Boolean(j > l);
            for (i = 0; i < j + 1; i++) {
                if (sing) {
                    r[i][j] = 0
                }
                var ii = ipvt[i];
                if (ii > jj) {
                    r[ii][jj] = r[i][j];
                }
                if (ii < jj) {
                    r[jj][ii] = r[i][j];
                }
            }
            wa[jj] = r[j][j];

        }
//        Symmetrize the covariance matrix in r
        for (j = 0; j < n; j++) {
            for (i = 0; i < j + 1; i++) {
                r[i][j] = r[j][i];
                r[j][j] = wa[j];
            }
        }
        return r;
    };
    lmfit.enorm = function (x) {
        var sq = 0;
        for (var i = 0; i < x.length; i++) {
            sq += x[i] * x[i];

        }
        return Math.sqrt(sq);

    };

    lmfit.typeOf = function (x) {
        return typeof x;
    };
//numerical constants for rounding and stuff
    this.machep = Math.pow(2, -53);
    this.maxnum = Math.pow(2, 53);
    this.minnum = 0 - Math.pow(2, 53);
    this.maxlog = Math.log(this.maxnum);
    this.minlog = Math.log(this.minnum);
    this.rdwarf = Math.sqrt(this.minnum * 1.5) * 10;
    this.rgiant = Math.sqrt(this.maxnum) * .01;
    this.amin = function (x) {
        var min = 99999;
        for (a = 0; a < x.length; a++) {
            min = Math.min(min, x[a]);
        }
        return min;
    };
    this.amax = function (x) {
        var max = -99999;
        for (a = 0; a < x.length; a++) {
            max = Math.max(max, x[a]);
        }
        return max;
    }

})
