# This program is public domain

"""
Error propogation algorithms for 1-D data.
"""

def div(X,varX, Y,varY):
    varZ = (varX + varY * (X/Y)**2) / Y**2
    Z = X/Y
    return Z, varZ

def mul(X,varX, Y,varY):
    varZ = Y**2 * varX + X**2 * varY
    Z = X * Y
    return Z, varZ

def sub(X,varX, Y, varY):
    varZ = X**2 + Y**2
    Z = X - Y
    return Z, varZ

def add(X,varX, Y,varY):
    varZ = X**2 + Y**2
    Z = X + Y
    return Z, varZ

def inv(X,varX):
    varZ = varX/X**4
    Z = 1/Z
    return Z, varZ

def pavg(X,varX,dQX, Y,varY,dQY, tol=1e-10):
    """
    Average to values assuming poisson statistics for uncertainties.

## Join run 1 and run 2, averaging the points that are near to each other.
## If only one run is given, then nearby points will be averaged.
##
## To average y1, ..., yn, use:
##     w = sum( y/dy^2 )
##     y = sum( (y/dy)^2 )/w
##     dy = sqrt ( y/w )
## Note that pavg(y1,...,yn) == pavg(y1,pavg(y2, ..., pavg(yn-1,yn)...))
## to machine precision, as tested against for example
##     pavg(logspace(-10,10,10))
##
## The above formula gives the expected result for combining two
## measurements, assuming there is no uncertainty in the monitor:
##    measure N counts during M monitors
##    rate:                   r = N/M
##    rate uncertainty:      dr = sqrt(N)/M
##    weighted rate:          r/dr^2 = (N/M) / (N/M^2) =  M
##    weighted rate squared:  r^2/dr^2 = (N^2/M) / (N/M^2) = N
##
##    for two measurements Na, Nb
##    w = ra/dra^2 + rb/drb^2 = Ma + Mb
##    y = ((ra/dra)^2 + (rb/drb)^2)/w = (Na + Nb)/(Ma + Mb)
##    dy = sqrt(y/w) = sqrt( (Na + Nb)/ w^2 ) = sqrt(Na+Nb)/(Ma + Mb)
##
## We are actually using a more complicated expression for rate which
## includes attenuators and for rate uncertainty which includes attenuator
## and monitor uncertainty propogated using gaussian statistics, so in
## practice it will be:
##    r = A*N/M
##   dr = sqrt( A^2*(1+N/M)*N/M^2 + (dA*N/M)^2 )
##
## Comparing the separately measured versus the combined values for
## e.g., Na = 7, Ma=2000, Nb=13, Mb=4000, Aa=Ab=1, dAa=dAb=0
## yields a relative error on the order of 1e-6.  Below the critical
## edge, with the monitor rate 10% of the detector rate,
## e.g., Na=20400, Ma=2000, Nb=39500, Mb=4000
## yields a relative error on the order of 0.02%.
##
## Computing monitor uncertainty is useful for estimating the 
## uncertainty in your reduced data.  For example, the error bars 
## scale by a factor of 3 below the critical edge in the example above.  
## Using Poisson error propogation is important in low count regions 
## only, and there only marginally so.
##
## We can't mix points with significantly different resolution dQ.
##
## See also test_run_avg

    """
    raise NotImplementedError
