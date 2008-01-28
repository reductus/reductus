"""PolPlot2D is a panel for 4 cross-section 2D polarized reflectometry data.
"""

import wx,numpy,os
from math import log10, pow

import matplotlib as mpl
mpl.interactive(False)
#Use the WxAgg back end. The Wx one takes too long to render
mpl.use('WXAgg')

from copy import deepcopy
import matplotlib.cm
import matplotlib.colors
from canvas import FigureCanvas as Canvas
#from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as Canvas
from matplotlib.backend_bases import LocationEvent
from matplotlib.font_manager import FontProperties
from matplotlib.colors import Normalize,LogNorm

import ticker


def _rescale(lo,hi,step,pt=None,bal=None,scale='linear'):
    """
    Rescale (lo,hi) by step, returning the new (lo,hi)
    The scaling is centered on pt, with positive values of step
    driving lo/hi away from pt and negative values pulling them in.
    If bal is given instead of point, it is already in [0,1] coordinates.
    
    This is a helper function for step-based zooming.
    """
    # Convert values into the correct scale for a linear transformation
    # TODO: use proper scale transformers
    if scale=='log': 
        lo,hi = log10(lo),log10(hi)
        if pt is not None: pt = log10(pt)

    # Compute delta from axis range * %, or 1-% if persent is negative
    if step > 0:
        delta = float(hi-lo)*step/100
    else:
        delta = float(hi-lo)*step/(100-step)

    # Add scale factor proportionally to the lo and hi values, preserving the
    # point under the mouse
    if bal is None: 
        bal = float(pt-lo)/(hi-lo)
    lo = lo - bal*delta
    hi = hi + (1-bal)*delta

    # Convert transformed values back to the original scale
    if scale=='log': 
        lo,hi = pow(10.,lo),pow(10.,hi)

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
    # Allows the programmer to specify the base for the filename.
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

def bbox_union(bboxes):
    """
    Return a Bbox that contains all of the given bboxes.
    """
    from matplotlib._transforms import Bbox, Point, Value
    if len(bboxes) == 1:
        return bboxes[0]

    x0 = numpy.inf
    y0 = numpy.inf
    x1 = -numpy.inf
    y1 = -numpy.inf

    for bbox in bboxes:
        xs = bbox.intervalx().get_bounds()
        ys = bbox.intervaly().get_bounds()
        x0 = min(x0, numpy.min(xs))
        y0 = min(y0, numpy.min(ys))
        x1 = max(x1, numpy.max(xs))
        y1 = max(y1, numpy.max(ys))

    return Bbox(Point(Value(x0), Value(y0)), Point(Value(x1), Value(y1)))


class Plotter(wx.Panel):
    def __init__(self, parent, id = -1, dpi = None, **kwargs):
        wx.Panel.__init__(self, parent, id=id, **kwargs)
        self.figure = mpl.figure.Figure(dpi=dpi, figsize=(2,2))
        self.canvas = Canvas(self, -1, self.figure)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas,1,wx.EXPAND)
        self.SetSizer(sizer)
    
class Plotter4(wx.Panel):
    """
    The PlotPanel has a Figure and a Canvas. OnSize events simply set a 
    flag, and the actually redrawing of the
    figure is triggered by an Idle event.
    """
    def __init__(self, parent, id = -1, dpi = None, color=None, **kwargs):
        # TODO: inherit directly from Canvas --- it is after all a panel.

        # Set up the panel parameters        
        #style = wx.NO_FULL_REPAINT_ON_RESIZE
        wx.Panel.__init__(self, parent, id = id, **kwargs)
        self.Bind(wx.EVT_CONTEXT_MENU, self.onContextMenu)

        # Create the figure        
        self.figure = mpl.figure.Figure(dpi=dpi, figsize=(2,2))
        #self.canvas = NoRepaintCanvas(self, -1, self.figure)
        self.canvas = Canvas(self, -1, self.figure)
        self.canvas.mpl_connect('key_press_event',self.onKeyPress)
        self.canvas.mpl_connect('button_press_event',self.onButtonPress)
        self.canvas.mpl_connect('scroll_event',self.onWheel)
        # TODO use something for pan events
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas,1,wx.EXPAND)
        self.SetSizer(sizer)
        # Construct an idle timer.  This won't be needed when matplotlib
        # supports draw_idle for wx.
        #self.idle_timer = wx.CallLater(1,self.onDrawIdle)
        #self.Fit()
        
        # Create four subplots with no space between them.
        # Leave space for the colorbar.
        # Use a common set of axes.
        self.pp = self.figure.add_subplot(221)
        self.mm = self.figure.add_subplot(222,sharex=self.pp,sharey=self.pp)
        self.pm = self.figure.add_subplot(223,sharex=self.pp,sharey=self.pp)
        self.mp = self.figure.add_subplot(224,sharex=self.pp,sharey=self.pp)
        self.figure.subplots_adjust(left=.1, bottom=.1, top=.9, right=0.85,
                                    wspace=0.0, hspace=0.0)
        
        self.axes = [self.pp, self.mm, self.pm, self.mp]
        self.grid = True

        # Create the colorbar
        # Provide an empty handle to attach colormap properties
        self.coloraxes = self.figure.add_axes([0.88, 0.2, 0.04, 0.6])
        self.colormapper = mpl.image.FigureImage(self.figure)
        self.colormapper.set_array(numpy.ones(1))
        self.colorbar = self.figure.colorbar(self.colormapper,self.coloraxes)

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
        self.set_vscale('log')
   
        # Set up the default plot
        self.clear()
        
        self._sets = {} # Container for all plotted objects

    def autoaxes(self):
        bbox = bbox_union([ax.dataLim for ax in self.axes])
        xlims = bbox.intervalx().get_bounds()
        ylims = bbox.intervaly().get_bounds()
        self.pp.axis(xlims+ylims)
            
    def onKeyPress(self,event):
        #if not event.inaxes: return
        # Let me zoom and unzoom even without the scroll wheel
        if event.key == 'a':
            setattr(event,'step',5.)
            self.onWheel(event)
        elif event.key == 'z':
            setattr(event,'step',-5.)
            self.onWheel(event)

    def onButtonPress(self,event):
        # TODO: finish binder so that it allows tagging of fully qualified
        # events on an artist by artist basis.
        if event.inaxes == self.coloraxes:
            self.colormapper.set_clim(vmin=self.vmin,vmax=self.vmax)
            self.canvas.draw_idle()
        elif event.inaxes != None:
            self.autoaxes()
            self.canvas.draw_idle()

    def onWheel(self, event):
        """
        Process mouse wheel as zoom events
        """
        ax = event.inaxes
        step = event.step

        # Icky hardcoding of colorbar zoom.
        if ax == self.coloraxes:
            # rescale colormap: the axes are already scaled to 0..1, 
            # so use bal instead of pt for centering
            lo,hi = self.colormapper.get_clim()
            lo,hi = _rescale(lo,hi,step,bal=event.ydata,scale=self.vscale)
            self.colormapper.set_clim(lo,hi)
        elif ax != None:
            # Event occurred inside a plotting area
            lo,hi = ax.get_xlim()
            lo,hi = _rescale(lo,hi,step,pt=event.xdata)
            ax.set_xlim((lo,hi))

            lo,hi = ax.get_ylim()
            lo,hi = _rescale(lo,hi,step,pt=event.ydata)
            ax.set_ylim((lo,hi))
        else:
            # Check if zoom happens in the axes
            xdata,ydata = None,None
            x,y = event.x,event.y
            for ax in self.axes:
                insidex,_ = ax.xaxis.contains(event)
                if insidex:
                    xdata,_ = ax.transAxes.inverse_xy_tup((x,y))
                    #print "xaxis",x,"->",xdata
                insidey,_ = ax.yaxis.contains(event)
                if insidey:
                    _,ydata = ax.transAxes.inverse_xy_tup((x,y))
                    #print "yaxis",y,"->",ydata
            if xdata is not None:
                lo,hi = ax.get_xlim()
                lo,hi = _rescale(lo,hi,step,bal=xdata)
                ax.set_xlim((lo,hi))
            if ydata is not None:
                lo,hi = ax.get_ylim()
                lo,hi = _rescale(lo,hi,step,bal=ydata)
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
        if scale == 'linear':
            vmapper = Normalize(*self.colormapper.get_clim())
            vformat = mpl.ticker.ScalarFormatter()
            vlocate = mpl.ticker.AutoLocator()
        else:
            vmapper = LogNorm(*self.colormapper.get_clim())
            vformat = mpl.ticker.LogFormatterMathtext(base=10,labelOnlyBase=False)
            vlocate = mpl.ticker.LogLocator(base=10)
        self.colormapper.set_norm(vmapper)
        self.colorbar.formatter = vformat
        self.colorbar.locator = vlocate
        
        self.vscale = scale
        
    def get_vscale(self):
        return self.vscale

    # Context menu implementation
    def onSaveImage(self, evt):
        """
        Figure save dialog
        """
        save_canvas(self.canvas,"polplot")

    # Context menu implementation
    def onGridToggle(self, event):
        self.grid = not self.grid
        for ax in self.axes: ax.grid(alpha=0.4,visible=self.grid)
        self.draw()
        
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
        self.colormapper.set_clim(vmin=1,vmax=10)

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
        #vmin = self.vmin if self.vmin < self.vmax else 1
        #vmax = self.vmax if self.vmin < self.vmax else 2
        #self.colormapper.set_cmap(mpl.cm.cool)
        #self.coloraxes.xaxis.set_major_formatter(mpl.ticker.LogFormatterMathtext())
        #print "setting formatter---doesn't seem to work"
        #self.coloraxes.yaxis.set_major_formatter(mpl.ticker.NullFormatter())

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
        # TODO Ack! adding 1 for the purposes of visualization! Fix log plots!
        x,y,v = data.xedges,data.yedges,data.v+1
        try:
            im = ax.pcolorfast(x,y,v)
        except AttributeError:
            im = ax.pcolormesh(x,y,v,shading='flat')
        self.colormapper.add_observer(im)
        
        self.vmin = min(self.vmin, numpy.min(v))
        self.vmax = max(self.vmax, numpy.max(v))
        self.colormapper.set_clim(vmin=self.vmin,vmax=self.vmax)
        self.autoaxes()
        self.canvas.draw_idle()
        
        return im


def demo():
    import data
    # Get some data
    d = data.peakspol(n=355)

    # Make a frame to show it
    app = wx.PySimpleApp()
    frame = wx.Frame(None,-1,'Plottables')
    plotter = Plotter4(frame)
    frame.Show()

    # render the graph to the pylab plotter
    plotter.clear()
    plotter.set_vscale('linear')
    plotter.surfacepol(d)
    
    app.MainLoop()
    pass

if __name__ == "__main__": demo()
