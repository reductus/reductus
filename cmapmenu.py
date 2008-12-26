# This program is public domain
"""
Defines CMapMenu, a wx submenu containing colormaps.

=== Example ===

The following defines a context menu with mapper::

    import wx
    import cmapmenu

    ...
    def onContextMenu(self,event):
        popup = wx.Menu()
        item = popup.Append(wx.ID_ANY,'&Save image', 'Save image as PNG')
        wx.EVT_MENU(self, item.GetId(), self.onSaveImage)
        item = popup.Append(wx.ID_ANY,'&Grid on/off', 'Toggle grid lines')
        wx.EVT_MENU(self, item.GetId(), self.onGridToggle)
        item = popup.AppendMenu(wx.ID_ANY, "Colourmaps",
                                CMapMenu(self, self.mapper, self.canvas))

The assumption is that mapper and canvas are attributes of the panel for
which the context menu is defined.  When the new colour map is selected,
the mapper will be reset and the figure redrawn.

Sometimes you will want to do more than just update the mapper for the
current canvas.  You may for example want to record the new colormap name
in the application settings file so that it will be there when the
application is reloaded.  To do this, call CMapMenu(callback=self.OnColormap).
This will call the method OnColormap with the parameter name giving the
name of the colormap.
"""
__all__ = ['CMapMenu']

import sys
import wx
import numpy
from matplotlib import cm

def colorbar_bitmap(colormap,length,thickness=10,orientation='horizontal'):
    """
    Convert a colormap to a bitmap showing a colorbar for the colormap.

    Orientation can be vertical or horizontal (only looks at the first letter).
    """
    # Make an RGBA array from the colormap, either horizontally or vertically.
    V = colormap(numpy.linspace(0,1,length),bytes=True)
    if orientation[0].lower() == 'h':
        V = numpy.tile(V,(thickness,1))
        bitmap = wx.BitmapFromBufferRGBA(length,thickness,V)
    elif orientation[0].lower() == 'v':
        V = numpy.tile(V,(1,thickness))
        bitmap = wx.BitmapFromBufferRGBA(thickness,length,V)
    else:
        raise ValueError,"expected orientation [V]ertical or [H]orizontal"
    return bitmap

def all_colormaps():
    """
    Iterate over the available colormaps
    """
    maps = [name
            for name in cm.datad.keys()
            if not name.endswith("_r")]
    maps.sort()
    return maps

def grouped_colormaps():
    """
    Colormaps grouped by source.
    """
    mlab = ['autumn','winter','spring','summer',
            'gray','bone','copper','pink',
            'cool','hot',
            'hsv','jet','spectral',
            #'binary',   # Seems to be a reverse of gray
            'prism','flag']
    mlab_r = [m+'_r' for m in mlab]
    brewer = ['Accent','Dark2',
              'Spectral',
              'Paired',
              'Blues','Greens','Greys','Oranges','Purples','Reds',
              'Pastel1','Pastel2',
              'Set1','Set2','Set3',
              'BrBG','BuGn','BuPu','GnBu',
              'OrRd',
              'PiYG','PRGn','PuBu','PuBuGn',
              'PuOr','PuRd',
              'RdBu','RdGy','RdPu',
              'RdYlBu','RdYlGn',
              'YlGn','YlGnBu','YlOrBr','YlOrRd',
              ]
    brewer_r = [m+'_r' for m in brewer]
    gist = ['gist_ncar','gist_rainbow',
            'gist_stern','gist_earth',
            'gist_gray','gist_heat',
            #'gist_yarg',  # Seems to be a reverse of gray
            ]
    gist_r = [m+'_r' for m in gist]

    return gist + [None] + mlab + [None] + brewer

def event_callback(callback, **kw):
    """
    Add keyword arguments to the event callback.
    """
    return lambda evt: callback(evt,**kw)
class CMapMenu(wx.Menu):
    """
    Menu tree binding to a list of colormaps.
    """
    def __init__(self, window,
                 mapper=None, canvas=None, callback=None):
        """
        Define a context menu for selecting colormaps.

        Need a window to use as the event handler.
        If mapper is defined, it will be updated with the new colormap.
        If canvas is defined, it will update on idle.
        """
        wx.Menu.__init__(self)

        # OS X needs 16x16 icons; Windows and Linux can be longer
        bar_length = 32 if not sys.platform in ['darwin'] else 16
        bar_height = 16
        self.mapper,self.canvas,self.callback = mapper,canvas,callback
        self.selected = None
        self.mapid = {}
        for name in grouped_colormaps():
            if name is None:
                self.AppendSeparator()
            else:
                item = wx.MenuItem(self, wx.ID_ANY, name)
                map = cm.get_cmap(name)
                icon = colorbar_bitmap(map,bar_length,thickness=bar_height)
                item.SetBitmap(icon)
                self.AppendItem(item)
                window.Bind(wx.EVT_MENU,
                            event_callback(self._OnSelect, name=name),
                            id=item.GetId())

    def _OnSelect(self, event, name=None):
        """
        When selected, record the name, update the mapper and invoke the
        callback.
        """
        self.selected = name
        if self.mapper:
            self.mapper.set_cmap(cm.get_cmap(name))
        if self.canvas:
            self.canvas.draw_idle()
        if self.callback:
            self.callback(name)

def demo():

    class ChangeCM(object):
        def __init__(self,im):
            self.im = im
        def __call__(self, m):
            self.im.set_cmap(m.get_cmap())
            self.im.set_clim(m.get_clim())
            #self.im.update_bruteforce(m)

    from matplotlib.image import FigureImage
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as Canvas
    class Frame(wx.Frame):
        def __init__(self):
            wx.Frame.__init__(self, parent=None, title="Colourmap Selection")

            self.figure = Figure(dpi=80, figsize=(2,2))
            self.canvas = Canvas(self, -1, self.figure)
            self.axes = self.figure.gca()
            x = y = numpy.linspace(-3,3,80)
            X,Y = numpy.meshgrid(x,y)
            V = numpy.sin(Y**2+X**2)
            self.mapper = FigureImage(self.figure)
            im = self.axes.pcolor(x,y,V,shading='flat')
            try:
                cb = self.mapper.callbacksSM.connect('changed', ChangeCM(im))
            except AttributeError:   # Using 0.91 style
                self.mapper.add_observer(im)
            #self.figure.colorbar(self.mapper)

            sizer = wx.BoxSizer(wx.VERTICAL)
            sizer.Add(self.canvas,1,wx.EXPAND)
            self.SetSizer(sizer)

            self.canvas.Bind(wx.EVT_RIGHT_DOWN, self.OnContext)


        def OnContext(self, evt):
            popup = wx.Menu()
            item = popup.Append(wx.ID_ANY,'&Grid on/off', 'Toggle grid lines')
            wx.EVT_MENU(self, item.GetId(), self.OnGridToggle)
            cmapmenu = CMapMenu(self, callback = self.OnColormap,
                                mapper=self.mapper, canvas=self.canvas)
            item = popup.AppendMenu(wx.ID_ANY, "Colourmaps", cmapmenu)
            self.PopupMenu(popup, evt.GetPositionTuple())
        def OnColormap(self, name):
            print "Selected colormap",name
        def OnGridToggle(self, event):
            self.axes.grid()
            self.canvas.draw_idle()

    app = wx.App(redirect=False)
    Frame().Show()
    app.MainLoop()


if __name__ == "__main__": demo()
