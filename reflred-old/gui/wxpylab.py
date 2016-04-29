import wx

import matplotlib
matplotlib.use('WxAgg')

# Wx-Pylab magic for displaying plots within an application's window.
from matplotlib._pylab_helpers import Gcf
from matplotlib.backend_bases import FigureManagerBase
import pylab

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wxagg import NavigationToolbar2Wx as Toolbar
from matplotlib.figure import Figure

class PlotPanel(wx.Panel):
    def __init__(self, *args, **kw):
        wx.Panel.__init__(self, *args, **kw)

        figure = Figure(figsize=(1,1), dpi=72)
        canvas = FigureCanvas(self, wx.ID_ANY, figure)
        self.pylab_figure = PylabFigure(canvas)

        # Instantiate the matplotlib navigation toolbar and explicitly show it.
        mpl_toolbar = Toolbar(canvas)
        mpl_toolbar.Realize()

        # Create a vertical box sizer to manage the widgets in the main panel.
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(canvas, 1, wx.EXPAND|wx.LEFT|wx.RIGHT, border=0)
        sizer.Add(mpl_toolbar, 0, wx.EXPAND|wx.ALL, border=0)

        # Associate the sizer with its container.
        self.SetSizer(sizer)
        sizer.Fit(self)


class PylabFigure(object):
    """
    Define a 'with' context manager that lets you use pylab commands to
    plot on an embedded canvas.  This is useful for wrapping existing
    scripts in a GUI, and benefits from being more familiar than the
    underlying object oriented interface.

    As a convenience, the pylab module is returned on entry.

    Example
    -------

    The following example shows how to use the WxAgg backend in a wx panel::

        from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
        from matplotlib.backends.backend_wxagg import NavigationToolbar2Wx as Toolbar
        from matplotlib.figure import Figure

        class PlotPanel(wx.Panel):
            def __init__(self, *args, **kw):
                wx.Panel.__init__(self, *args, **kw)

                figure = Figure(figsize=(1,1), dpi=72)
                canvas = FigureCanvas(self, wx.ID_ANY, figure)
                self.pylab_figure = PylabFigure(canvas)

                # Instantiate the matplotlib navigation toolbar and explicitly show it.
                mpl_toolbar = Toolbar(canvas)
                mpl_toolbar.Realize()

                # Create a vertical box sizer to manage the widgets in the main panel.
                sizer = wx.BoxSizer(wx.VERTICAL)
                sizer.Add(canvas, 1, wx.EXPAND|wx.LEFT|wx.RIGHT, border=0)
                sizer.Add(mpl_toolbar, 0, wx.EXPAND|wx.ALL, border=0)

                # Associate the sizer with its container.
                self.SetSizer(sizer)
                sizer.Fit(self)

            def plot(self, *args, **kw):
                with self.pylab_figure as pylab:
                    pylab.clf()
                    pylab.plot(*args, **kw)

    Similar patterns should work for the other backends.  Check the source code
    in matplotlib.backend_bases.* for examples showing how to use matplotlib
    with other GUI toolkits.
    """
    def __init__(self, canvas):
        self.fm = FigureManagerBase(canvas, -1)
    def __enter__(self):
        Gcf.set_active(self.fm)
        return pylab
    def __exit__(self, *args, **kw):
        Gcf._activeQue = [f for f in Gcf._activeQue if f is not self.fm]
        try: del Gcf.figs[-1]
        except: pass
        self.fm.canvas.draw()