# This program is public domain

"""
DANSE canvas for WxAgg.

Supports mpl plots in a wx.aui context.  Removes the need for the
NoRepaintCanvas found on the web.

Adds support for mpl.connect('mouse_wheel_event',callback)
"""

import wx
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg, _convert_agg_to_wx_bitmap
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backend_bases import MouseEvent

# TODO: should use the following for a scroll event, rather than
# pretending it is a mouse event.
class ScrollEvent(MouseEvent):
    """
    A event on the mouse wheel

    The following additional attributes are defined and shown with
    their default values

    x      = None       # x position - pixels from left of canvas
    y      = None       # y position - pixels from bottom of canvas
    inaxes = None       # the Axes instance if mouse us over axes
    xdata  = None       # x coord of mouse in data coords
    ydata  = None       # y coord of mouse in data coords
    step   = None       # the number of steps taken (up is positive)
    button = None       # 'up' or 'down' (deprecated)
    key    = None       # the key pressed: None, chr(range(255), shift, win, or control
     
    Step should be 1. for a single click.  The wheel event may correspond
    to more than one click.  High precision wheels may return floating point
    numbers corresponding to portions of a click.
    """
    x      = None       # x position - pixels from left of canvas
    y      = None       # y position - pixels from right of canvas
    inaxes = None       # the Axes instance if mouse us over axes
    xdata  = None       # x coord of mouse in data coords
    ydata  = None       # y coord of mouse in data coords
    button = None
    key    = None
    step   = None

    def __init__(self, name, canvas, x, y, button, key, step,
                 guiEvent=None):
        """
        x, y in figure coords, 0,0 = bottom, left
        button pressed 'up' or 'down' (deprecated)
        """
        MouseEvent.__init__(self, name, canvas, x, y, button, key,
                            guiEvent=guiEvent)
        self.step = step



class FigureCanvas(FigureCanvasWxAgg):
    """
    Add features to the wx agg canvas for better support of AUI and
    faster plotting.
    """

    # Belongs in backens/backend_wx
    def __init__(self, *args, **kw):
        super(FigureCanvas,self).__init__(*args, **kw)
        self._isRendered = False
        
        # Create an timer for handling draw_idle requests
        # If there are events pending when the timer is
        # complete, reset the timer and continue.  The
        # alternative approach, binding to wx.EVT_IDLE,
        # doesn't behave as nicely.
        self.idletimer = wx.CallLater(1,self._onDrawIdle)
 
        # Support for mouse wheel
        self.Bind(wx.EVT_MOUSEWHEEL, self._onMouseWheel)

    # Belongs in backends/backend_wxagg
    def draw(self, drawDC=None):
        """
        Render the figure using agg.
        """
        #print "drawing"
        # Only draw if window is shown, otherwise graph will bleed through
        # on the notebook style AUI widgets.
        if self.IsShownOnScreen():
            #print "on screen"
            #import traceback; traceback.print_stack()
            self._isRendered = True
            FigureCanvasWxAgg.draw(self)
            self.bitmap = _convert_agg_to_wx_bitmap(self.get_renderer(), None)
            self.gui_repaint(drawDC=drawDC)
        else:
            self._isRendered = False
    
    # Belongs in backends/backend_wx
    def draw_idle(self, *args, **kwargs):
        """
        Render after a delay if no other render requests have been made.
        """
        self.idletimer.Restart(5, *args, **kwargs)  # Delay by 5 ms

    def _onMouseWheel(self, evt):
        """Translate mouse wheel events into matplotlib events"""
        # Determine mouse location
        x = evt.GetX()
        y = self.figure.bbox.height() - evt.GetY()

        # Convert delta/rotation/rate into a floating point step size
        delta = evt.GetWheelDelta()
        rotation = evt.GetWheelRotation()
        rate = evt.GetLinesPerAction()
        #print "delta,rotation,rate",delta,rotation,rate
        step = rate*float(rotation)/delta

        # Convert to mpl event
        evt.Skip()
        self.scroll_event(x, y, step, guiEvent=evt)

    def scroll_event(self, x, y, step=1, guiEvent=None):
        """
        Backend derived classes should call this function on any
        scroll wheel event.  x,y are the canvas coords: 0,0 is lower,
        left.  button and key are as defined in MouseEvent
        """
        button = 'up' if step >= 0 else 'down'
        self._button = button
        s = 'scroll_event'
        event = ScrollEvent(s, self, x, y, button, self._key,
                                 step=step, guiEvent=guiEvent)
        self.callbacks.process(s, event)


    def _onDrawIdle(self, *args, **kwargs):
        #print "idle callback"
        if wx.GetApp().Pending():
            self.idletimer.Restart(5, *args, **kwargs)
        else:
            self.draw(*args, **kwargs)

    def _onPaint(self, evt):
        """
        Called when wxPaintEvt is generated
        """

        if not self._isRealized:
            self.realize()

        # Need to draw the graph the first time it is shown otherwise
        # it is a black canvas.  After that we can use the rendered 
        # bitmap for updates.
        if self._isRendered:
            #print "painting rendered"
            self.gui_repaint(drawDC=wx.PaintDC(self))
        else:
            #print "painting not rendered"
            self.draw(drawDC=wx.PaintDC(self))

        evt.Skip()
