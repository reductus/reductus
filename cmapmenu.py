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
                                CMapMenu(self.mapper,self.canvas))

The assumption is that mapper and canvas are attributes of the panel for
which the context menu is defined.  When the new colour map is selected,
the mapper will be reset and the figure redrawn.  

Note that mapper and canvas are not required.  In anycase, the OnSelect 
method of CMapMenu will be invoked with the new colormap name.  This
can be used, for example, to set a new default colormap in a persistent
store, or to coordinate the colormaps on multiple canvases.
"""

import wx
import matplotlib.cm
import numpy

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
            for name in matplotlib.cm.datad.keys() 
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

def _menu_callback(callback, name):
    return lambda evt: callback(name)
class CMapMenu(wx.Menu):
    """
    Menu tree binding to a list of colormaps.
    """
    def __init__(self, mapper=None, canvas=None):
        """
        Define a context menu for selecting colormaps.

        If mapper is defined, it will be updated with the new colormap.
        If canvas is defined, it will update on idle.
        """
        wx.Menu.__init__(self)

        self.mapper,self.canvas = mapper,canvas
        self.selected = None
        self.mapid = {}
        for name in grouped_colormaps():
            if name is None:
                self.AppendSeparator()
            else:
                item = self.Append(wx.ID_ANY,name)
                map = matplotlib.cm.get_cmap(name)
                icon = colorbar_bitmap(map,16,thickness=16)
                item.SetBitmap(icon)
                self.Bind(wx.EVT_MENU, 
                          _menu_callback(self._OnSelect,name),
                          id=item.GetId())

    def _OnSelect(self, name):
        """
        When selected, record the name and call the subclass OnSelect method.
        """
        self.selected = name
        if self.mapper: 
            self.mapper.set_cmap(matplotlib.cm.get_cmap(name))
        if self.canvas:
            self.canvas.draw_idle()
        self.OnSelect(name)

    def OnSelect(self,name):
        """
        Action to take when the color is selected.

        Override this method to perform a specific action.
        """

    def Popup(self,window,position=None):
        """
        Popup the colourmap menu on the window at the selected position.

        Returns the name of the colourmap selected, or None if no 
        selection was made.

        The actual colourmap is available using::
             matplotlib.cm.get_cmap(name)
        """
        self.selected = None
        window.PopupMenu(self,position)
        return self.selected

def demo():
    class Frame(wx.Frame):
        def __init__(self):
            wx.Frame.__init__(self, parent=None, title="Hello")
            self.Bind(wx.EVT_RIGHT_DOWN, self.OnContext)
        def OnContext(self, evt):
            print CMapMenu().Popup(self,evt.GetPositionTuple())

    app = wx.App(redirect=False)
    Frame().Show()
    app.MainLoop()


if __name__ == "__main__": demo()

