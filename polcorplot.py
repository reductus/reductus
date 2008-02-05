# This program is public domain
"""
Plot the data associated with the polarization efficiency correction.

This is a pair of plots locked together, one plot showing the intensity
scans for the individual cross-sections, and the estimated 2*beta, the
other showing the efficiencies of the front/back polarizers and flippers.
"""
# Boilerplate to allow relative imports for apps.
if __name__ == '__main__':
    import os; __path__=[os.path.dirname(os.path.realpath(__file__))]; del os

import wx
import matplotlib as mpl
mpl.interactive(False)
mpl.use('WXAgg')
import matplotlib.pyplot
from canvas import FigureCanvas as Canvas


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
            for data,label in zip([eff.beam.pp, eff.beam.pm, 
                                   eff.beam.mp, eff.beam.mm],
                                  ['$++$','$+-$','$-+$','$--$']):
                self.intensity.errorbar(data.x,data.v,yerr=data.dv,
                                        fmt='+',label=label)
            self.intensity.plot(eff.beam.pp.x,eff.Ic,'+',label='$I_c$')
        if self.smooth is not None:
            eff = self.smooth
            for data in [eff.beam.pp, eff.beam.pm, eff.beam.mp, eff.beam.mm]:
                self.intensity.errorbar(data.x,data.v,data.dv,'+')
            self.intensity.semilogy(eff.beam.pp.x,eff.Ic,'+')
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
            for y,lab in zip([eff.fp, eff.ff, eff.rf, eff.rp],
                             ['F pol','F flip','R pol','R flip']):
                self.efficiency.plot(eff.beam.pp.x, 100*y,'+',label=lab)
        if self.smooth is not None:
            eff = self.smooth
            ax.set_xlabel("%s (%s)"%(eff.beam.xlabel, eff.beam.xunits))
            for y in [eff.fp, eff.ff, eff.rf, eff.rp]:
                self.efficiency.plot(eff.beam.pp.x, 100*y,'-')
        ax.legend()
        self.canvas.draw_idle()

    def plot(self, raw=None, smooth=None):
        self.raw = raw
        self.smooth = smooth
        self.update_efficiency()
        self.update_intensity()

def demo():
    from .examples import e3a12 as data
    from .polcor import PolarizationEfficiency
    
    # Get some data
    beam = data.slits()
    eff = PolarizationEfficiency(beam=beam)

    # Make a frame to show it
    app = wx.PySimpleApp()
    frame = wx.Frame(None,-1,'Plottables')
    plotter = Plotter(frame)
    frame.Show()

    # render the graph to the pylab plotter
    plotter.plot(eff)
    
    app.MainLoop()
    pass    

if __name__ == "__main__": demo()      