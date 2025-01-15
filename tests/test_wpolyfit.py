"""
Tests for wpolyfit.

Test cases are taken from the NIST Statistical Reference Datasets
   https://www.itl.nist.gov/div898/strd/

These problems are chosen to challenge statistical software, and
cannot be expected to be matched precisely in limited precision
machines (the target results were computed using 100 digit arithmetic).
The individual tests vary, but relative error should be between 1e-8
and 1e-16.
"""

## Author: Paul Kienzle
## This program is public domain
from __future__ import print_function

import sys
import numpy as N
from reductus.dataflow.lib.wsolve import wpolyfit

VERBOSE = 1

def show_result(name, p, dp, Ep, Edp, tol=2e-16):
    # compute relative error
    err_p = abs((p-Ep)/Ep) if (Ep != 0).all() else abs(p-Ep)
    err_dp = abs((dp-Edp)/Edp) if (Edp != 0).all() else abs(dp-Edp)
    # If expected value is zero use absolute error
    print(name, p, dp, Ep, Edp, err_p, err_dp)
    err_p[Ep == 0] = p[Ep == 0]
    err_dp[Edp == 0] = dp[Edp == 0]
    if VERBOSE > 0:
        print("Test:", name)
        print("parameter   expected value   rel. error")
        for i in range(len(p)):
            print("%12.5g  %12.5g %12.5g"%(p[i], Ep[i], err_p[i]))
        print("p-error     expected value   rel. error")
        for i in range(len(p)):
            print("%12.5g  %12.5g %12.5g"%(dp[i], Edp[i], err_dp[i]))
        print("-"*39)
    assert (err_p < tol).all() and (err_dp < tol).all(),\
        "wsolve %s exceeded tolerance of %g"%(name, tol)

def check_uncertainty(n=10000):
    """
    This function computes a number of fits to simulated data
    to determine how well the values and uncertainties reported
    by the wpolyfit solver correspond to individual fits of the data.

    For large N the reported parameters do indeed converge to the mean
    parameter values for fits to resampled data.  Reported parameter
    uncertainty estimates are not supported by MC.
    """
    ##          x         y          dy
    data = N.matrix("""
        0.0013852  0.2144023  0.020470;
        0.0018469  0.2516856  0.022868;
        0.0023087  0.3070443  0.026362;
        0.0027704  0.3603186  0.029670;
        0.0032322  0.4260864  0.033705;
        0.0036939  0.4799956  0.036983
        """).A
    x, y, dy = data[:, 0], data[:, 1], data[:, 2]
    if True: # simpler system to analyze
        x = N.linspace(2, 4, 12)
        y = 3*x+5
        dy = y
    p = wpolyfit(x, y, dy=dy, degree=1)
    P = N.empty((2, n), 'd')
    for i in range(n):
        #pi = N.polyfit(x,N.random.normal(y,dy),degree=1)
        pi = wpolyfit(x, N.random.normal(y, dy), dy=dy, degree=1)
        P[:, i] = pi.coeff
    #print("P", P)
    Ep, Edp = N.mean(P, 1), N.std(P, 1)
    show_result("uncertainty check", p.coeff, p.std, Ep, Edp)

    if False:
        import pylab
        pylab.hist(P[0, :])
        pylab.show()
    """ # Not yet converted from octave
    input('Press <Enter> to see some sample regression lines: ');
    t = [x(1), x(length(x))];
    [p,s] = wpolyfit(x,y,dy,1); dp=sqrt(sumsq(inv(s.R'))'/s.df)*s.normr;
    hold off;
    for i=1:15, plot(t,polyval(p(:)+randn(size(dp)).*dp,t),'-g;;'); hold on; end
    errorbar(x,y,dy,"~b;;");
    [yf,dyf]=polyconf(p,x,s,0.05,'ci');
    plot(x,yf-dyf,"-r;;",x,yf+dyf,'-r;95% confidence interval;')
    hold off;
    """


def check(name, data, target, origin=False, tol=2e-16):
    """
    name   data set name
    data   [y,x]
    target [p,dp] but low to high rather than high to low
    """
    p = wpolyfit(data[:, 1], data[:, 0], degree=target.shape[0]-1, origin=origin)
    Ep, Edp = N.flipud(target).T
    show_result(name, p.coeff, p.std, Ep, Edp, tol=tol)


def run_tests():
##Procedure:     Linear Least Squares Regression
##Reference:     Filippelli, A., NIST.
##Model:         Polynomial Class
##               11 Parameters (B0,B1,...,B10)
##
##               y = B0 + B1*x + B2*(x**2) + ... + B9*(x**9) + B10*(x**10) + e

##Data:
##            y          x
    data = N.matrix("""
            0.8116   -6.860120914;
            0.9072   -4.324130045;
            0.9052   -4.358625055;
            0.9039   -4.358426747;
            0.8053   -6.955852379;
            0.8377   -6.661145254;
            0.8667   -6.355462942;
            0.8809   -6.118102026;
            0.7975   -7.115148017;
            0.8162   -6.815308569;
            0.8515   -6.519993057;
            0.8766   -6.204119983;
            0.8885   -5.853871964;
            0.8859   -6.109523091;
            0.8959   -5.79832982;
            0.8913   -5.482672118;
            0.8959   -5.171791386;
            0.8971   -4.851705903;
            0.9021   -4.517126416;
            0.909    -4.143573228;
            0.9139   -3.709075441;
            0.9199   -3.499489089;
            0.8692   -6.300769497;
            0.8872   -5.953504836;
            0.89     -5.642065153;
            0.891    -5.031376979;
            0.8977   -4.680685696;
            0.9035   -4.329846955;
            0.9078   -3.928486195;
            0.7675   -8.56735134;
            0.7705   -8.363211311;
            0.7713   -8.107682739;
            0.7736   -7.823908741;
            0.7775   -7.522878745;
            0.7841   -7.218819279;
            0.7971   -6.920818754;
            0.8329   -6.628932138;
            0.8641   -6.323946875;
            0.8804   -5.991399828;
            0.7668   -8.781464495;
            0.7633   -8.663140179;
            0.7678   -8.473531488;
            0.7697   -8.247337057;
            0.77     -7.971428747;
            0.7749   -7.676129393;
            0.7796   -7.352812702;
            0.7897   -7.072065318;
            0.8131   -6.774174009;
            0.8498   -6.478861916;
            0.8741   -6.159517513;
            0.8061   -6.835647144;
            0.846    -6.53165267;
            0.8751   -6.224098421;
            0.8856   -5.910094889;
            0.8919   -5.598599459;
            0.8934   -5.290645224;
            0.894    -4.974284616;
            0.8957   -4.64454848;
            0.9047   -4.290560426;
            0.9129   -3.885055584;
            0.9209   -3.408378962;
            0.9219   -3.13200249;
            0.7739   -8.726767166;
            0.7681   -8.66695597;
            0.7665   -8.511026475;
            0.7703   -8.165388579;
            0.7702   -7.886056648;
            0.7761   -7.588043762;
            0.7809   -7.283412422;
            0.7961   -6.995678626;
            0.8253   -6.691862621;
            0.8602   -6.392544977;
            0.8809   -6.067374056;
            0.8301   -6.684029655;
            0.8664   -6.378719832;
            0.8834   -6.065855188;
            0.8898   -5.752272167;
            0.8964   -5.132414673;
            0.8963   -4.811352704;
            0.9074   -4.098269308;
            0.9119   -3.66174277;
            0.9228   -3.2644011
            """).A

##Certified values:
##                      p                       dP
    target = N.matrix("""
                -1467.48961422980         298.084530995537;
                -2772.17959193342         559.779865474950;
                -2316.37108160893         466.477572127796;
                -1127.97394098372         227.204274477751;
                -354.478233703349         71.6478660875927;
                -75.1242017393757         15.2897178747400;
                -10.8753180355343         2.23691159816033;
                -1.06221498588947         0.221624321934227;
                -0.670191154593408E-01    0.142363763154724E-01;
                -0.246781078275479E-02    0.535617408889821E-03;
                -0.402962525080404E-04    0.896632837373868E-05
                """).A
    check("Filippelli, A., NIST.", data, target, tol=1e-7)


##Procedure:     Linear Least Squares Regression
##
##Reference:     Pontius, P., NIST.
##               Load Cell Calibration.
##
##Model:         Quadratic Class
##               3 Parameters (B0,B1,B2)
##               y = B0 + B1*x + B2*(x**2)


##Data:       y             x
    data = N.matrix("""
         .11019        150000;
         .21956        300000;
         .32949        450000;
         .43899        600000;
         .54803        750000;
         .65694        900000;
         .76562       1050000;
         .87487       1200000;
         .98292       1350000;
        1.09146       1500000;
        1.20001       1650000;
        1.30822       1800000;
        1.41599       1950000;
        1.52399       2100000;
        1.63194       2250000;
        1.73947       2400000;
        1.84646       2550000;
        1.95392       2700000;
        2.06128       2850000;
        2.16844       3000000;
         .11052        150000;
         .22018        300000;
         .32939        450000;
         .43886        600000;
         .54798        750000;
         .65739        900000;
         .76596       1050000;
         .87474       1200000;
         .98300       1350000;
        1.09150       1500000;
        1.20004       1650000;
        1.30818       1800000;
        1.41613       1950000;
        1.52408       2100000;
        1.63159       2250000;
        1.73965       2400000;
        1.84696       2550000;
        1.95445       2700000;
        2.06177       2850000;
        2.16829       3000000
        """).A

##               Certified Regression Statistics
##
##                                          Standard Deviation
##                     Estimate             of Estimate
    target = N.matrix("""
              0.673565789473684E-03    0.107938612033077E-03;
              0.732059160401003E-06    0.157817399981659E-09;
             -0.316081871345029E-14    0.486652849992036E-16
             """).A
    check("Pontius, P., NIST", data, target, tol=5e-12)


#Procedure:     Linear Least Squares Regression
#Reference:     Eberhardt, K., NIST.
#Model:         Linear Class
#               1 Parameter (B1)
#
#               y = B1*x + e

#Data:     y     x
    data = N.matrix("""
         130    60;
         131    61;
         132    62;
         133    63;
         134    64;
         135    65;
         136    66;
         137    67;
         138    68;
         139    69;
         140    70
         """).A

#               Certified Regression Statistics
#
#                                 Standard Deviation
#               Estimate             of Estimate
    target = N.matrix("""
          0                    0;
          2.07438016528926     0.165289256198347E-01
          """).A

    check("Eberhardt, K., NIST", data, target, origin=True, tol=1e-14)


#Reference:     Wampler, R. H. (1970).
#               A Report of the Accuracy of Some Widely-Used Least
#               Squares Computer Programs.
#               Journal of the American Statistical Association, 65, 549-565.
#
#Model:         Polynomial Class
#               6 Parameters (B0,B1,...,B5)
#
#               y = B0 + B1*x + B2*(x**2) + B3*(x**3)+ B4*(x**4) + B5*(x**5)
#
#               Certified Regression Statistics
#
#                                          Standard Deviation
#     Parameter        Estimate               of Estimate
    target = N.matrix("""
                1.00000000000000        0.000000000000000;
                1.00000000000000        0.000000000000000;
                1.00000000000000        0.000000000000000;
                1.00000000000000        0.000000000000000;
                1.00000000000000        0.000000000000000;
                1.00000000000000        0.000000000000000
                """).A

#Data:            y     x
    data = N.matrix("""
                 1     0;
                 6     1;
                63     2;
               364     3;
              1365     4;
              3906     5;
              9331     6;
             19608     7;
             37449     8;
             66430     9;
            111111    10;
            177156    11;
            271453    12;
            402234    13;
            579195    14;
            813616    15;
           1118481    16;
           1508598    17;
           2000719    18;
           2613660    19;
           3368421    20
           """).A
    check("Wampler1", data, target, tol=1e-8)

##Reference:     Wampler, R. H. (1970).
##               A Report of the Accuracy of Some Widely-Used Least
##               Squares Computer Programs.
##               Journal of the American Statistical Association, 65, 549-565.
##Model:         Polynomial Class
##               6 Parameters (B0,B1,...,B5)
##
##               y = B0 + B1*x + B2*(x**2) + B3*(x**3)+ B4*(x**4) + B5*(x**5)
##
##               Certified Regression Statistics
##                                       Standard Deviation
## Parameter         Estimate               of Estimate
    target = N.matrix("""
                1.00000000000000         0.000000000000000;
                0.100000000000000        0.000000000000000;
                0.100000000000000E-01    0.000000000000000;
                0.100000000000000E-02    0.000000000000000;
                0.100000000000000E-03    0.000000000000000;
                0.100000000000000E-04    0.000000000000000
                """).A

#Data:          y       x
    data = N.matrix("""
            1.00000    0;
            1.11111    1;
            1.24992    2;
            1.42753    3;
            1.65984    4;
            1.96875    5;
            2.38336    6;
            2.94117    7;
            3.68928    8;
            4.68559    9;
            6.00000   10;
            7.71561   11;
            9.92992   12;
           12.75603   13;
           16.32384   14;
           20.78125   15;
           26.29536   16;
           33.05367   17;
           41.26528   18;
           51.16209   19;
           63.00000   20
           """).A
    check("Wampler2", data, target, tol=1e-12)


##Reference:   Wampler, R. H. (1970).
##             A Report of the Accuracy of Some Widely-Used Least
##             Squares Computer Programs.
##             Journal of the American Statistical Association, 65, 549-565.
##
##Model:       Polynomial Class
##             6 Parameters (B0,B1,...,B5)
##
##             y = B0 + B1*x + B2*(x**2) + B3*(x**3)+ B4*(x**4) + B5*(x**5)
##
##             Certified Regression Statistics
##
##                                        Standard Deviation
##   Parameter          Estimate             of Estimate
    target = N.matrix("""
                  1.00000000000000         2152.32624678170;
                  1.00000000000000         2363.55173469681;
                  1.00000000000000         779.343524331583;
                  1.00000000000000         101.475507550350;
                  1.00000000000000         5.64566512170752;
                  1.00000000000000         0.112324854679312
                  """).A

#Data:           y      x
    data = N.matrix("""
              760.     0;
            -2042.     1;
             2111.     2;
            -1684.     3;
             3888.     4;
             1858.     5;
            11379.     6;
            17560.     7;
            39287.     8;
            64382.     9;
           113159.    10;
           175108.    11;
           273291.    12;
           400186.    13;
           581243.    14;
           811568.    15;
          1121004.    16;
          1506550.    17;
          2002767.    18;
          2611612.    19;
          3369180.    20
          """).A
    check("Wampler3", data, target, tol=5e-10)

##Model:         Polynomial Class
##               6 Parameters (B0,B1,...,B5)
##
##               y = B0 + B1*x + B2*(x**2) + B3*(x**3)+ B4*(x**4) + B5*(x**5)
##
##              Certified Regression Statistics
##
##                                          Standard Deviation
##     Parameter          Estimate             of Estimate
    target = N.matrix("""
                  1.00000000000000         215232.624678170;
                  1.00000000000000         236355.173469681;
                  1.00000000000000         77934.3524331583;
                  1.00000000000000         10147.5507550350;
                  1.00000000000000         564.566512170752;
                  1.00000000000000         11.2324854679312
                  """).A

#Data:            y     x
    data = N.matrix("""
              75901    0;
            -204794    1;
             204863    2;
            -204436    3;
             253665    4;
            -200894    5;
             214131    6;
            -185192    7;
             221249    8;
            -138370    9;
             315911   10;
             -27644   11;
             455253   12;
             197434   13;
             783995   14;
             608816   15;
            1370781   16;
            1303798   17;
            2205519   18;
            2408860   19;
            3444321   20
            """).A

    check("Wampler4", data, target, tol=1e-8)


##Model:         Polynomial Class
##               6 Parameters (B0,B1,...,B5)
##
##               y = B0 + B1*x + B2*(x**2) + B3*(x**3)+ B4*(x**4) + B5*(x**5)
##
##               Certified Regression Statistics
##
##                                          Standard Deviation
##     Parameter          Estimate             of Estimate
    target = N.matrix("""
                  1.00000000000000         21523262.4678170;
                  1.00000000000000         23635517.3469681;
                  1.00000000000000         7793435.24331583;
                  1.00000000000000         1014755.07550350;
                  1.00000000000000         56456.6512170752;
                  1.00000000000000         1123.24854679312
                  """).A

##Data:            y     x
    data = N.matrix("""
             7590001     0;
           -20479994     1;
            20480063     2;
           -20479636     3;
            25231365     4;
           -20476094     5;
            20489331     6;
           -20460392     7;
            18417449     8;
           -20413570     9;
            20591111    10;
           -20302844    11;
            18651453    12;
           -20077766    13;
            21059195    14;
           -19666384    15;
            26348481    16;
           -18971402    17;
            22480719    18;
           -17866340    19;
            10958421    20
            """).A
    check("Wampler5", data, target, tol=5e-7)

if __name__ == "__main__":
    VERBOSE = ('-q' not in sys.argv)
    #check_uncertainty(n=10000)
    run_tests()
    print("OK", file=sys.stderr)
