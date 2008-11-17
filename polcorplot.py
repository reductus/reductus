# This program is public domain
"""
Plot the data associated with the polarization efficiency correction.

This is a pair of plots locked together, one plot showing the intensity
scans for the individual cross-sections, and the estimated 2*beta, the
other showing the efficiencies of the front/back polarizers and flippers.
"""

import numpy
import wx
import matplotlib as mpl
mpl.interactive(False)
mpl.use('WXAgg')
import matplotlib.pyplot
#from canvas import FigureCanvas as Canvas
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as Canvas


class Plotter(wx.Panel):
    def __init__(self, parent, id = -1, dpi = None, **kwargs):
        wx.Panel.__init__(self, parent, id=id, **kwargs)
        self.figure = mpl.figure.Figure(dpi=dpi, figsize=(2,2))
        self.canvas = Canvas(self, -1, self.figure)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas,1,wx.EXPAND)
        self.SetSizer(sizer)

        self.intensity = self.figure.add_subplot(211)
        mpl.pyplot.setp(self.intensity.get_xticklabels(), visible=False)
        self.efficiency = self.figure.add_subplot(212, sharex=self.intensity)

        self.raw = None
        self.smooth = None

    def update_intensity(self):
        ax = self.intensity
        ax.clear()
        ax.set_ylabel("Counts")
        if self.raw is not None:
            eff = self.raw
            for data,label,color in zip([eff.beam.pp, eff.beam.pm,
                                         eff.beam.mp, eff.beam.mm],
                                         ['$I++$','$I+-$','$I-+$','$I--$'],
                                         ['r','g','b','m']):
                self.intensity.errorbar(data.x,data.v,yerr=data.dv,
                                        fmt='x'+color,label=label)
            self.intensity.plot(eff.beam.pp.x,eff.Ic,'xc',label='$I_c$')
        if self.smooth is not None:
            eff = self.smooth
            for data,color in zip([eff.beam.pp, eff.beam.pm,
                                   eff.beam.mp, eff.beam.mm],
                                  ['r','g','b','m']):
                self.intensity.errorbar(data.x,data.v,data.dv,fmt='-'+color)
            self.intensity.semilogy(eff.beam.pp.x,eff.Ic,'-c')
        ax.legend()
        ax.set_yscale('log')
        self.canvas.draw_idle()

    def update_efficiency(self):
        ax = self.efficiency
        ax.clear()
        ax.set_ylabel("Efficiency (%)")
        # Draw rectangle above 1.0 showing invalid efficiencies.
        if self.raw is not None:
            eff = self.raw
            ax.set_xlabel("%s (%s)"%(eff.beam.xlabel, eff.beam.xunits))
            for y,lab,color in zip([eff.fp, eff.ff, eff.rf, eff.rp],
                                   ['F pol','F flip','R pol','R flip'],
                                   ['r','g','b','m']):
                self.efficiency.plot(eff.beam.pp.x, 100*y,'x'+color,label=lab)
        if self.smooth is not None:
            eff = self.smooth
            ax.set_xlabel("%s (%s)"%(eff.beam.xlabel, eff.beam.xunits))
            for y,color in zip([eff.fp, eff.ff, eff.rf, eff.rp],
                               ['r','g','b','m']):
                self.efficiency.plot(eff.beam.pp.x, 100*y,'-'+color)
        ax.set_ylim(ymax=105)
        ax.axhspan(100,1000,facecolor='0.8',alpha=0.5)
        ax.legend()
        self.canvas.draw_idle()

    def plot(self, raw=None, smooth=None):
        self.raw = raw
        self.smooth = smooth
        self.update_efficiency()
        self.update_intensity()

def demo():
    from examples import e3a12 as data
    from polcor import PolarizationEfficiency
    from smooth import Smooth

    # Get a slit scan and compute the raw efficiency
    beam = data.slits()
    eff = PolarizationEfficiency(beam=beam, FRbalance=0.6, clip=False)
    # Smooth it and comput the smoothed efficiency
    beam.apply(Smooth(degree=2,span=13))
    effsmooth = PolarizationEfficiency(beam=beam, FRbalance=0.6, clip=True)

    # Make a frame to show it
    app = wx.PySimpleApp()
    frame = wx.Frame(None,-1,'Plottables')
    plotter = Plotter(frame)
    frame.Show()

    # render the graph to the pylab plotter
    plotter.plot(eff, effsmooth)

    app.MainLoop()
    pass

if __name__ == "__main__": demo()
