#!/usr/bin/env python

"""
Program to show the monte carlo error estimate of the polarization correction
operation, assuming a value and uncertainty for polarizer and flipper
efficiencies.
"""

import numpy,math,pylab
import reflectometry.reduction as reflred

eff = reflred.PolarizationEfficiency()

n = 10000

# Seed polarizer/flipper efficiencies from a gaussian distribution
eff.ff = numpy.random.randn(n)*0.02 + 0.95
eff.fp = numpy.random.randn(n)*0.02 + 0.9
eff.rf = numpy.random.randn(n)*0.02 + 0.95
eff.rp = numpy.random.randn(n)*0.02 + 0.9
eff.Ic = 50

data = reflred.PolarizedData()
data.pp.v = 51*numpy.ones(n)
data.pm.v = 12*numpy.ones(n)
data.mp.v = 13*numpy.ones(n)
data.mm.v = 49*numpy.ones(n)
data.pp.variance = data.pp.v
data.pm.variance = data.pm.v
data.mp.variance = data.mp.v
data.mm.variance = data.mm.v

eff(data)
for plt,v,label,E in [(221,data.pp.v,'++',51),
                      (222,data.pm.v,'+-',12),
                      (223,data.mp.v,'-+',13),
                      (224,data.mm.v,'--',49)]:
    pylab.subplot(plt)
    pylab.hist(v)
    legend(['%s %0.2f (%0.2f)'%(label,pylab.mean(v),pylab.std(v))])
    print "%s measurement uncertainty %.2f, corrected uncertainty %.2f"\
        %(label,math.sqrt(E),pylab.std(v))
