"""
Experimental replacements for log formatting and tick marks.
"""


from __future__ import division
import sys, os, re, time, math, warnings
import numpy as npy
import matplotlib as mpl
from matplotlib import verbose, rcParams
from matplotlib import cbook
from matplotlib import transforms as mtrans
from matplotlib import ticker


class LogFormatterMathtext(ticker.LogFormatter):
    """
    Format values for log axis; using exponent = log_base(value)
    """

    def __call__(self, x, pos=None):
        'Return the format for tick val x at position pos'
        self.verify_intervals()

        b = self._base
        fx = math.log(abs(x))/math.log(b)
        isDecade = self.is_decade(fx)

        usetex = rcParams['text.usetex']
        # Make sure sign shows up properly
        if x < 0: b = -b

        if not isDecade and self.labelOnlyBase:
            s = ''
        elif not isDecade:
            #if usetex:
            #    s = r'$%g^{%.2f}$'% (b, fx)
            #else:
            #    s = '$\mathdefault{%g^{%.2f}}$'% (b, fx)
            s = '%g'%(x)
        else:
            exp = self.nearest_long(fx)
            if exp == 0:
                s = 1
            elif exp == 1:
                s = '%g'%(x)
            elif usetex:
                s = r'$%g^{%d}$'% (b, self.nearest_long(fx))
            else:
                s = r'$\mathdefault{%g^{%d}}$'% (b, self.nearest_long(fx))

        return s


def decade_down(x, base=10):
    'floor x to the nearest lower decade'

    lx = math.floor(math.log(x)/math.log(base))
    return base**lx

def decade_up(x, base=10):
    'ceil x to the nearest higher decade'
    lx = math.ceil(math.log(x)/math.log(base))
    return base**lx

def is_decade(x,base=10):
    lx = math.log(x)/math.log(base)
    return lx==int(lx)

class LogLocator(ticker.Locator):
    """
    Determine the tick locations for log axes
    """

    def __init__(self, base=10.0, subs=[1.0], ntics=5):
        """
        place ticks on the location= base**i*subs[j]
        """
        self.base(base)
        self.subs(subs)
        self.numticks = 15

        # Linear subtics
        self._ntics = 5
        self._trim = True
        self._integer = False
        self._steps = [1.,2.,5.]

    def base(self,base):
        """
        set the base of the log scaling (major tick every base**i, i interger)
        """
        self._base=base+0.0

    def subs(self,subs):
        """
        set the minor ticks the log scaling every base**i*subs[j]
        """
        if subs is None:
            self._subs = None  # autosub
        else:
            self._subs = npy.asarray(subs)+0.0

    def _set_numticks(self):
        self.numticks = 15  # todo; be smart here; this is just for dev

    def linear_tics(self, vmin, vmax):
        nbins = self._ntics
        scale, offset = ticker.scale_range(vmin, vmax, nbins)
        vmin -= offset
        vmax -= offset
        raw_step = (vmax-vmin)/nbins
        scaled_raw_step = raw_step/scale

        for step in [1,2,5,10]:
            if step < scaled_raw_step:
                continue
            step *= scale
            best_vmin = step*divmod(vmin, step)[0]
            best_vmax = best_vmin + step*nbins
            if (best_vmax >= vmax):
                break
        if self._trim:
            extra_bins = int(divmod((best_vmax - vmax), step)[0])
            nbins -= extra_bins
        return (npy.arange(nbins+1) * step + best_vmin + offset)


    def __call__(self):
        'Return the locations of the ticks'
        self.verify_intervals()
        b=self._base

        linvmin, linvmax = self.viewInterval.get_bounds()

        vmin = math.log(linvmin)/math.log(b)
        vmax = math.log(linvmax)/math.log(b)
        if vmax<vmin:
            vmin, vmax = vmax, vmin
        if vmax-vmin <= 1.:
            return self.linear_tics(linvmin, linvmax)


        ticklocs = []

        numdec = math.floor(vmax)-math.ceil(vmin)

        if self._subs is None: # autosub
            if numdec>10: subs = npy.array([1.0])
            elif numdec>6: subs = npy.arange(2.0, b, 2.0)
            else: subs = npy.arange(2.0, b)
        else:
            subs = self._subs

        stride = 1
        while numdec/stride+1 > self.numticks:
            stride += 1

        for decadeStart in b**npy.arange(math.floor(vmin),
                                         math.ceil(vmax)+stride, stride):
            ticklocs.extend( subs*decadeStart )

        return npy.array(ticklocs)

    def autoscale(self):
        'Try to choose the view limits intelligently'
        self.verify_intervals()

        vmin, vmax = self.dataInterval.get_bounds()
        if vmax<vmin:
            vmin, vmax = vmax, vmin

        minpos = self.dataInterval.minpos()

        if minpos<=0:
            raise RuntimeError('No positive data to plot')
        if vmin<=0:
            vmin = minpos
        if not is_decade(vmin,self._base): vmin = decade_down(vmin,self._base)
        if not is_decade(vmax,self._base): vmax = decade_up(vmax,self._base)
        if vmin==vmax:
            vmin = decade_down(vmin,self._base)
            vmax = decade_up(vmax,self._base)
        return mtrans.nonsingular(vmin, vmax)
