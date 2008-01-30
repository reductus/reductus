# This program is public domain
"""
Plot the data associated with the polarization efficiency correction.

This is a pair of plots locked together, one plot showing the intensity
scans for the individual cross-sections, and the estimated 2*beta, the
other showing the efficiencies of the front/back polarizers and flippers.
"""

class Plotter(wx.Panel):
    def __init__(self, parent, id = -1, dpi = None, **kwargs):
        wx.Panel.__init__(self, parent, id=id, **kwargs)
        self.figure = mpl.figure.Figure(dpi=dpi, figsize=(2,2))
        self.canvas = Canvas(self, -1, self.figure)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas,1,wx.EXPAND)
        self.SetSizer(sizer)

        self.intensity = self.figure.subplot(211)
        self.efficiency = self.figure.subplot(212)
        
        self.polraw = None
        self.polsmooth = None
        self.effraw = None
        self.effsmooth = None
    
    def update_intensity(self):
        self.intensity.clear()
        if self.polraw is not None:
            for xs in [self.polraw.pp, self.polraw.pm, self.polraw.mp, self.polraw.mm]:
                self.intensity.plot(xs.x,xs.y,xs.dy,'+')
        if self.polsmooth is not None:
            for xs in [self.polsmooth.pp, self.polsmooth.pm, self.polsmooth.mp, self.polsmooth.mm]:
                self.intensity.plot(xs.x,xs.y,'-')
        self.canvas.draw_idle()
    
    def update_efficiency(self):
        self.efficiency.clear()
        # Draw rectangle above 1.0 showing invalid efficiencies.
        ??
        if self.effraw is not None:
            for xs in [self.effraw.fp, self.polraw.ff, self.polraw.rf, self.polraw.rp]:
                self.efficiency.plot(xs.x, xs.y,xs.dy,'+')
        if self.effraw is not None:
            for xs in [self.effraw.fp, self.polraw.ff, self.polraw.rf, self.polraw.rp]:
                self.efficiency.plot(xs.x, xs.y,xs.dy,'+')
        self.canvas.draw_idle() 
              