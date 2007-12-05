"""PolPlot2D is a panel for 4 cross-section 2D polarized reflectometry data.
"""

import wx,numpy,os

import matplotlib as mpl
mpl.interactive(False)
#Use the WxAgg back end. The Wx one takes too long to render
mpl.use('WXAgg')


import matplotlib.cm
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.backend_bases import LocationEvent
from matplotlib.font_manager import FontProperties


def _rescale(lo,hi,step,pt=None,bal=None):
    """
    Rescale (lo,hi) by step, returning the new (lo,hi)
    The scaling is centered on pt, with positive values of step
    driving lo/hi away from pt and negative values pulling them in.
    If bal is given instead of point, it is already in [0,1] coordinates.
    
    This is a helper function for step-based zooming.
    """
    step *= 3   # 1% change is too tiny
    if step > 0: scale = float(hi-lo)*step/100
    else: scale = float(hi-lo)*step/(100-step)
    if bal is None: bal = float(pt-lo)/(hi-lo)
    lo = lo - bal*scale
    hi = hi + (1-bal)*scale
    return (lo,hi)

def error_msg(msg, parent=None):
    """
    Signal an error condition -- in a GUI, popup a error dialog
    """
    # Code brought with minor podifications from mpl.backends.backend_wx
    # Copyright (C) Jeremy O'Donoghue & John Hunter, 2003-4
    dialog =wx.MessageDialog(parent  = parent,
                             message = msg,
                             caption = 'Polplot error',
                             style=wx.OK | wx.CENTRE)
    dialog.ShowModal()
    dialog.Destroy()
    return None


def save_canvas(canvas,filebase):
    """
    Given a canvas and a a base filename, construct a file save
    dialog to save the canvas.
    """
    # Code brought with minor modifications from mpl.backends.backend_wx
    # Copyright (C) Jeremy O'Donoghue & John Hunter, 2003-4
    filetypes, exts, filter_index = canvas._get_imagesave_wildcards()
    default_file = filebase + "." + canvas.get_default_filetype()
    dlg = wx.FileDialog(canvas, "Save to file", "", default_file, filetypes,
                        wx.SAVE|wx.OVERWRITE_PROMPT|wx.CHANGE_DIR)
    dlg.SetFilterIndex(filter_index)
    if dlg.ShowModal() == wx.ID_OK:
        dirname  = dlg.GetDirectory()
        filename = dlg.GetFilename()
        #DEBUG_MSG('Save file dir:%s name:%s' % (dirname, filename), 3, self)
        format = exts[dlg.GetFilterIndex()]
        # Explicitly pass in the selected filetype to override the
        # actual extension if necessary
        try:
            canvas.print_figure(os.path.join(dirname, filename), format=format)
        except Exception, e:
            error_msg(str(e))
    return

def update_cmap(canvas,mapper,mapname):
    def fn(event):
        mapper.set_cmap(mpl.cm.__dict__[mapname])
        canvas.draw_idle()
    return fn
    
def cmap_menu(canvas,mapper):
    """
    Create a menu of available colourmaps.
    """
    # TODO: add bitmaps showing the colormaps into the menu
    # TODO: only include useful maps
    # TODO: provide reversal as a transformation on colorbar
    # TODO: provide better names on the menu
    # TODO: add bright, graded_hsv and random

    menu = wx.Menu()
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
              'BrBG','BUGn','BuPu','GnBu',
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
    
 
    #maps = mpl.cm.cmapnames
    #maps.sort()
    separator = False
    for set in [gist, gist_r, mlab, mlab_r, brewer, brewer_r]:
        if separator: menu.AppendSeparator()
        separator = True
        for m in set:
            item = menu.Append(wx.ID_ANY,m)
            wx.EVT_MENU(canvas, item.GetId(), update_cmap(canvas,mapper,m))
    return menu

class Plotter(wx.Panel):
    """
    The PlotPanel has a Figure and a Canvas. OnSize events simply set a 
    flag, and the actually redrawing of the
    figure is triggered by an Idle event.
    """
    def __init__(self, parent, id = -1, color = None,\
        dpi = None, style = wx.NO_FULL_REPAINT_ON_RESIZE, **kwargs):

        # Set up the panel parameters        
        wx.Panel.__init__(self, parent, id = id, style = style, **kwargs)
        self.Bind(wx.EVT_IDLE, self._onIdle)
        self.Bind(wx.EVT_SIZE, self._onSize)
        self.Bind(wx.EVT_CONTEXT_MENU, self.onContextMenu)

        # Create the figure        
        self.figure = mpl.figure.Figure(None, dpi)
        self.canvas = NoRepaintCanvas(self, -1, self.figure)
        self.canvas.Bind(wx.EVT_MOUSEWHEEL, self.onMouseWheel)
        self.canvas.mpl_connect('key_press_event',self.onKeyPress)
        self.canvas.mpl_connect('button_press_event',self.onButtonPress)
        self.SetColor(color)
        self._resizeflag = True
        self._SetSize()
        
        # Create four subplots with no space between them.
        # Leave space for the colorbar.
        # Use a common set of axes.
        self.pp = self.figure.add_subplot(221)
        self.mm = self.figure.add_subplot(222,sharex=self.pp,sharey=self.pp)
        self.pm = self.figure.add_subplot(223,sharex=self.pp,sharey=self.pp)
        self.mp = self.figure.add_subplot(224,sharex=self.pp,sharey=self.pp)
        
        self.axes = [self.pp, self.mm, self.pm, self.mp]
        self.grid = True
        self.coloraxes = self.figure.add_axes([0.88, 0.2, 0.04, 0.6])
        self.figure.subplots_adjust(left=.1, bottom=.1, top=.9, right=0.85,
                                    wspace=0.0, hspace=0.0)

        # Create the colorbar
        # Provide an empty handle to attach colormap properties
        self.colormapper = mpl.image.FigureImage(self.figure)
        self.colormapper.set_array(numpy.zeros((1,1)))
        self.figure.colorbar(self.colormapper,self.coloraxes)

        # Provide slots for the graph labels
        self.tbox = self.figure.text(0.5, 0.95, '',
                                     horizontalalignment='center',
                                     fontproperties=FontProperties(size=16))
        self.xbox = self.figure.text(0.5,0.01,'',
                                     verticalalignment='bottom',
                                     horizontalalignment='center',
                                     rotation='horizontal')
        self.ybox = self.figure.text(0.01,0.5,'',
                                     horizontalalignment='left',
                                     verticalalignment='center',
                                     rotation='vertical')
        self.zbox = self.figure.text(0.99,0.5,'',
                                     horizontalalignment='right',
                                     verticalalignment='center',
                                     rotation='vertical')

        self.xscale = 'linear'
        self.yscale = 'linear'
        self.zscale = 'linear'

    def onKeyPress(self,event):
        if not event.inaxes: return
        # Let me zoom and unzoom even without the scroll wheel
        if event.key == 'a':
            self.zoom(event,5.)
        elif event.key == 'z':
            self.zoom(event,-5.)

    def onButtonPress(self,event):
        # TODO: finish binder so that it allows tagging of fully qualified
        # events on an artist by artist basis.
        if event.inaxes == self.coloraxes:
            self.colormapper.set_clim(vmin=self.vmin,vmax=self.vmax)
            self.canvas.draw_idle()
        elif event.inaxes != None:
            self.pp.axis('auto')
            self.canvas.draw_idle()

    def onMouseWheel(self,event):
        """Translate mouse wheel events into matplotlib events"""
        # TODO: Wheel events belong inside matplotlib
        delta = event.GetWheelDelta()
        rotation = event.GetWheelRotation()
        rate = event.GetLinesPerAction()
        step = rate*float(rotation)/delta
        x = event.GetX()
        y = self.figure.bbox.height() - event.GetY()
        # event.Skip()  # Let other handlers act on this event
        mplevent = LocationEvent("wheel",self.figure.canvas,x,y,guiEvent=event)

        # TODO: step needs to be part of event
        self.zoom(mplevent,step)

    def zoom(self, event, step):
        # TODO: handle logscale properly
        ax = event.inaxes

        # Icky hardcoding of colorbar zoom.
        if ax == self.coloraxes:
            lo,hi = self.colormapper.get_clim()
            lo,hi = _rescale(lo,hi,step,bal=event.ydata)
            self.colormapper.set_clim(lo,hi)
        else:
            if event.xdata is not None:
                lo,hi = ax.get_xlim()
                lo,hi = _rescale(lo,hi,step,pt=event.xdata)
                ax.set_xlim((lo,hi))
            if event.ydata is not None:
                lo,hi = ax.get_ylim()
                lo,hi = _rescale(lo,hi,step,pt=event.ydata)
                ax.set_ylim((lo,hi))
            
        self.canvas.draw_idle()

    
    # These are properties which the user should control but for which
    # a particular plottable might want to set a reasonable default.
    # For now leave control with the plottable.
    def set_xscale(self, scale='linear'):
        for axes in self.axes: axes.set_xscale(scale)
        self.xscale = scale
        
    def get_xscale(self):
        return self.xscale

    def set_yscale(self, scale='linear'):
        for axes in self.axes: axes.set_yscale(scale)
        self.yscale = scale
        
    def get_yscale(self):
        return self.yscale

    def set_vscale(self, scale='linear'):
        """Alternate between log and linear colormap"""
        self.mapper = LogNorm(*self.mapper.get_clim())
        self.vscale = scale
        
    def get_vscale(self):
        return self.vscale
    

    def SetColor(self, rgbtuple):
        """Set figure and canvas colours to be the same"""
        if not rgbtuple:
            rgbtuple = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE).Get()
        col = [c/255.0 for c in rgbtuple]
        self.figure.set_facecolor(col)
        self.figure.set_edgecolor(col)
        self.canvas.SetBackgroundColour(wx.Colour(*rgbtuple))

    def _onSize(self, event):
        self._resizeflag = True

    def _onIdle(self, evt):
        if self._resizeflag:
            self._resizeflag = False
            self._SetSize()
            self.draw()

    def _SetSize(self, pixels = None):
        """
        This method can be called to force the Plot to be a desired size, which 
        defaults to the ClientSize of the panel
        """
        if not pixels:
            pixels = self.GetClientSize()
        self.canvas.SetSize(pixels)
        self.figure.set_size_inches(pixels[0]/self.figure.get_dpi(),
        pixels[1]/self.figure.get_dpi())

    def draw(self):
        """Where the actual drawing happens"""
        self.figure.canvas.draw_idle()

    # Context menu implementation
    def onSaveImage(self, evt):
        """
        Figure save dialog
        """
        save_canvas(self.canvas,"polplot")

    # Context menu implementation
    def onLoadData(self, evt):
        """
        Data load dialog
        """
        path = None
        dlg = wx.FileDialog(self, message="Choose a file", style=wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
        dlg.Destroy()
        if path is None: return

        import readicp,data
        fields = readicp.read(path)
        x = numpy.arange(len(fields['columns']['COUNTS']))+1
        y = numpy.arange(fields['detector'].shape[1])+1
        v = numpy.log10(fields['detector'].T+1)
        data = data.Data(x=x,y=y,v=v)
        ax = self.menuevent.inaxes
        #for im in ax.images: im.remove()
        im = self.menuevent.inaxes.pcolorfast(data.xedges,data.yedges,data.v)
        self.vmin = numpy.min(data.v)
        self.vmax = numpy.max(data.v)
        self.colormapper.add_observer(im)
        self.colormapper.set_clim(self.vmin,self.vmax)
        self.canvas.draw_idle()

    def onGridToggle(self, event):
        self.grid = not self.grid
        self.render()
        self.canvas.draw_idle()
        
    def onContextMenu(self, event):
        """
        Default context menu for a plot panel
        """
        # Define a location event for the position of the popup
        
        # TODO: convert from screen coords to window coords
        x,y = event.GetPosition()
        self.menuevent = LocationEvent("context",self.figure.canvas,
                                       x,y,guiEvent=event)
        
        popup = wx.Menu()
        item = popup.Append(wx.ID_ANY,'&Save image', 'Save image as PNG')
        wx.EVT_MENU(self, item.GetId(), self.onSaveImage)
        item = popup.Append(wx.ID_ANY,'&Grid on/off', 'Toggle grid lines')
        wx.EVT_MENU(self, item.GetId(), self.onGridToggle)
        item = popup.AppendMenu(wx.ID_ANY, "Colourmaps", 
                                cmap_menu(self.canvas, self.colormapper))
        if self.menuevent.inaxes and self.menuevent.inaxes != self.coloraxes:
            popup.Append(315,'&Load data', 'Load data into the current cross section')
            wx.EVT_MENU(self, 315, self.onLoadData)
        #popup.Append(315,'&Properties...','Properties editor for the graph')
        #wx.EVT_MENU(self, 315, self.onProp)

        pos = event.GetPosition()
        pos = self.ScreenToClient(pos)
        self.PopupMenu(popup, pos)
        
    
    ## The following is plottable functionality
    def properties(self,prop):
        """Set some properties of the graph.
        
        The set of properties is not yet determined.
        """
        # The particulars of how they are stored and manipulated (e.g., do 
        # we want an inventory internally) is not settled.  I've used a
        # property dictionary for now.
        #
        # How these properties interact with a user defined style file is
        # even less clear.

        # Properties defined by plot
        self.xbox.set_text(r"$%s$" % prop["xlabel"])
        self.ybox.set_text(r"$%s$" % prop["ylabel"])
        self.vbox.set_text(r"$%s$" % prop["vlabel"])
        self.tbox.set_text(r"$%s$" % prop["title"])

        # Properties defined by user
        #self.axes.grid(True)

    def clear(self):
        """Reset the plot"""
        
        # TODO: Redraw is brutal.  Render to a backing store and swap in
        # TODO: rather than redrawing on the fly?
        # TODO: Want to retain graph properties such as grids and limits
        for ax in self.axes:
            ax.clear()
            ax.hold(True)
        
        # Label the four cross sections
        props = dict(va='center',ha='left',
                     bbox=dict(facecolor='yellow',alpha=0.67))
        self.pp.text( 0.05, 0.9, '$++$', props, transform=self.pp.transAxes)
        self.pm.text( 0.05, 0.9, '$+-$', props, transform=self.pm.transAxes)
        self.mp.text( 0.05, 0.9, '$-+$', props, transform=self.mp.transAxes)
        self.mm.text( 0.05, 0.9, '$--$', props, transform=self.mm.transAxes)

        #self.pp.get_yticklabels()[0].set_visible(False)
        #self.mp.get_xticklabels()[0].set_visible(False)
        self.vmin, self.vmax = numpy.inf,-numpy.inf


    def render(self):
        """Commit the plot after all objects are drawn"""
        # TODO: this is when the backing store should be swapped in.

        # Hide tick labels for interior axes
        for l in self.pp.get_xticklabels(): l.set_visible(False)
        for l in self.mm.get_xticklabels(): l.set_visible(False)
        for l in self.mm.get_yticklabels(): l.set_visible(False)
        for l in self.mp.get_yticklabels(): l.set_visible(False)
        
        # TODO: Hide tick labels from pm that might overlap neighbours
        # The proper algorithm would be to suppress all tick labels
        # which are within half the font height of the end of the
        # axis.  Second best is to suppress those within 10% of the
        # end of the axis. The current method is to remove the last
        # two, but it doesn't work very well.
        #self.pm.yaxis.get_majorticklabels()[-1].set_visible(False)
        #self.pm.xaxis.get_majorticklabels()[-1].set_visible(False)
        #self.pm.yaxis.get_majorticklabels()[-2].set_visible(False)
        #self.pm.xaxis.get_majorticklabels()[-2].set_visible(False)

        # Set the limits on the colormap
        vmin = self.vmin if self.vmin < self.vmax else 0
        vmax = self.vmax if self.vmin < self.vmax else 1
        self.colormapper.set_clim(vmin=vmin,vmax=vmax)
        #self.colormapper.set_cmap(mpl.cm.cool)

        for ax in self.axes: ax.grid(alpha=0.4,visible=self.grid)
        pass

    def xaxis(self,label,units):
        """xaxis label and units.
        
        Axis labels know about units.
        
        We need to do this so that we can detect when axes are not
        commesurate.  Currently this is ignored other than for formatting
        purposes.
        """
        if units != "": label = label + " (" + units + ")"
        self.xbox.set_text(r"$%s$" % (label))
        pass
    
    def yaxis(self,label,units):
        """yaxis label and units."""
        if units != "": label = label + " (" + units + ")"
        self.ybox.set_text(r"$%s$" % (label))
        pass

    def vaxis(self,label,units):
        """vaxis label and units."""
        if units != "": label = label + " (" + units + ")"
        self.vbox.set_text(r"$%s$" % (label))
        pass

    def surfacepol(self,poldata):
        for slice,data in [('++',poldata.pp),('--',poldata.mm),
                        ('+-',poldata.pm),('-+',poldata.mp)]:
            self.surface(slice,data)
        pass

    def surface(self,slice,data):
        if slice == '++': ax = self.pp
        elif slice == '+-': ax = self.pm
        elif slice == '-+': ax = self.mp
        elif slice == '--': ax = self.mm
        else: raise ValueError, "expected polarization crosssection"
        
        # Should be the following:
        #    im = ax.pcolor(data.xedges,data.yedges,data.v,shading='flat')
        # but this won't work in all versions of mpl, so first figure out
        # if we are using pcolorfast or pcolormesh then adjust the kwargs.
        try:
            p=ax.pcolorfast
            kw={}
        except AttributeError:
            p=ax.pcolormesh
            kw=dict(shading='flat')
        im = p(data.xedges,data.yedges,data.v,**kw)
        self.colormapper.add_observer(im)
        self.vmin = min(self.vmin, numpy.min(data.v))
        self.vmax = max(self.vmax, numpy.max(data.v))
        pass


    

class NoRepaintCanvas(FigureCanvasWxAgg):
    """We subclass FigureCanvasWxAgg, overriding the _onPaint method, so that
    the draw method is only called for the first two paint events. After that,
    the canvas will only be redrawn when it is resized.
    """
    def __init__(self, *args, **kwargs):
        FigureCanvasWxAgg.__init__(self, *args, **kwargs)
        self._drawn = 0

    def _onPaint(self, evt):
        """
        Called when wxPaintEvt is generated
        """
        if not self._isRealized:
            self.realize()
        if self._drawn < 2:
            self.draw(repaint = False)
            self._drawn += 1
        self.gui_repaint(drawDC=wx.PaintDC(self))


def demo():
    import data
    # Get some data
    d = data.peakspol(n=355)

    # Make a frame to show it
    app = wx.PySimpleApp()
    frame = wx.Frame(None,-1,'Plottables')
    plotter = Plotter(frame)
    frame.Show()

    # render the graph to the pylab plotter
    plotter.clear()
    plotter.surfacepol(d)
    plotter.render()
    
    app.MainLoop()
    pass

if __name__ == "__main__": demo()
