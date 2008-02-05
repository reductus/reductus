#!/usr/bin/env python

"""
Program to show the monte carlo error estimate of the polarization correction
operation, assuming a value and uncertainty for polarizer and flipper
efficiencies.
"""
n = 100000
err = 5
Ic = 100000
doplot = False


import numpy,math,pylab
import reflectometry.reduction as reflred

eff = reflred.PolarizationEfficiency()

# Seed polarizer/flipper efficiencies from a gaussian distribution
eff.ff = numpy.random.normal(0.95,0.01*err,n)
eff.fp = numpy.random.normal(0.90,0.01*err,n)
eff.rf = numpy.random.normal(0.95,0.01*err,n)
eff.rp = numpy.random.normal(0.90,0.01*err,n)
eff.Ic = numpy.random.normal(Ic,numpy.sqrt(Ic),n)

data = reflred.PolarizedData()
for V,v in [(data.pp,Ic), (data.pm,Ic/5), (data.mp,Ic/5), (data.mm,Ic)]:
    V.v = numpy.ones(n)*v
    V.variance = V.v   # Variance is poisson variance
    V.v = numpy.random.normal(V.v,V.dv)  # Randomize inputs

eff(data)  # Apply polarization efficiency correction to data

for plt,d,label,E in [(221,data.pp,'++',Ic),
                      (222,data.pm,'+-',Ic/5),
                      (223,data.mp,'-+',Ic/5),
                      (224,data.mm,'--',Ic)]:
    if doplot:
        pylab.subplot(plt)
        pylab.hist(d.v)
        pylab.legend(['%s %0.2f (%0.2f)'%(label,pylab.mean(d.v),pylab.std(d.v))])
    print "%s measurement uncertainty %.2f, corrected uncertainty %.3f, value %.3f"\
        %(label,math.sqrt(E),pylab.std(d.v),numpy.mean(d.v))
if doplot: pylab.show()
