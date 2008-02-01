"""
GUI driver for the polarization correction code polcor.
"""

import sys
import wx,wx.aui
from selection import SelectionPanel, EVT_ITEM_SELECT, EVT_ITEM_VIEW
from polplot import Plotter, Plotter4

# Set up a file extension registry; use this to classify the available
# datasets in a directory tree, and to mark and load the files in the
# tree.
class Registry:
    def __init__(self): self.registry = None
    def __in__(self, ext):
        return ext in self.registry
    def associate(self,ext,factory):
        if extension in self.registry:
            self.registry[ext].insert(0,factory)
        else:
            self.registry[ext] = [factory]
registry = Registry()

#import nexusref, 
import ncnr_ng1, ncnr_ng7
for m in [ncnr_ng1, ncnr_ng7]:
    m.register_extensions(registry)



class Reduction(wx.Panel):
    def __init__(self, *args, **kw):
        wx.Panel.__init__(self, *args, **kw)

        self.data = {}
        self.plotlist = []
        if True:
            # Use simple sashes
            splitter = wx.SplitterWindow(self)
            splitter.SetSashGravity(0.3)
            left = wx.SplitterWindow(splitter)
            left.SetSashGravity(0.3)
            right = wx.SplitterWindow(splitter)
            right.SetSashGravity(0.0)

            self.selector = SelectionPanel(left)
            self.metadata = wx.TextCtrl(left,style=wx.TE_MULTILINE|wx.TE_AUTO_SCROLL)
            self.plotter = Plotter4(right)
            self.slice = Plotter(right)
            
            splitter.SplitVertically(left,right,170)
            left.SplitHorizontally(self.selector,self.metadata,-100)
            right.SplitHorizontally(self.plotter,self.slice,-1)
            container = splitter
        else:
            # Use AUI notebook
            self.notebook = wx.aui.AuiNotebook(self)
            self.selector = SelectionPanel(self.notebook)
            self.plotter = Plotter4(self.notebook)
            self.metadata = wx.TextCtrl(self,style=wx.TE_MULTILINE|wx.TE_RICH2)
            self.slice = Plotter(self)
            self.notebook.AddPage(self.selector, "Selection")
            self.notebook.AddPage(self.plotter, "Reduction")
            self.notebook.AddPage(self.metadata, "Metadata")
            self.notebook.AddPage(self.slice, "Slice")
            #self.notebook.Bind(wx.aui.EVT_AUI_RENDER,self.onRender)
            container = self.notebook

        sizer = wx.BoxSizer()
        sizer.Add(container, 1, wx.EXPAND)
        self.SetSizer(sizer)
        
        self.selector.Bind(EVT_ITEM_SELECT, self.onSelect)
        self.selector.Bind(EVT_ITEM_VIEW, self.onView)

    def load(self, filename):
        # Check if it is already loaded
        if filename in self.data:
            return self.data[filename]
        
        # Try loading data, guessing format from file extension
        ext = os.path.splitext(filename)[1]
        try:
            if ext in ['.nxs']:
                data = nxsformat.data(filename)
            elif ext in ['.na1','.nb1','.nc1','.nd1','.ng1',
                         '.ca1','.cb1','.cc1','.cd1','.cg1',
                         '.ng7']:
                data = icpformat.data(filename)

            if data.prop.polarization == "":
                # TODO Temporary hack: unpolarized data dumped into ++ 
                data.prop.polarization = "++"
            self.data[filename] = data
        except:
            print "unable to laod %s\n  %s"%(filename, sys.exc_value)
            data = None
        return data

    def onView(self, event):
        filename = event.data
        data = self.load(filename)
        if data is not None:
            # TODO this isn't shifting the text control on aqua
            # Tried setting focus first without success:
            #   focuswin = wx.Window.FindFocus()
            #   self.metadata.SetFocus()
            #   ...
            #   if focuswin: focuswin.SetFocus()            
            #self.metadata.SetFocus()
            pt = self.metadata.GetInsertionPoint()
            self.metadata.Replace(0,self.metadata.GetLastPosition(),data.summary())
            self.metadata.SetInsertionPoint(pt)
            # See if simulating a right-left sequence moves the view
            #kevent = wx.KeyEvent(wx.EVT_CHAR)
            #kevent.m_keyCode = wx.WXK_RIGHT
            #self.metadata.EmulateKeyPress(kevent)
            #kevent.m_keyCode = wx.WXK_LEFT
            #self.metadata.EmulateKeyPress(kevent)
            #print "Setting point to",pt
            self.metadata.ShowPosition(pt)
            
 
    def onSelect(self, event):
        filename = event.data
        if event.enabled == True:
            # Adding a plot
            data = self.load(filename)
            if data:
                im = self.plotter.surface(data.prop.polarization,data)
                self.plotlist.append(filename)
        else:
            if filename in self.plotlist:
                self.plotlist.remove(filename)
                self.plotter.clear()
                for f in self.plotlist:
                    data = self.load(f)
                    im = self.plotter.surface(data.prop.polarization,data)

    def onRender(self, event):
        # AUI only - ignored
        print "rendering"
        mgr = self.notebook.GetAuiManager()
        print "perspective",mgr.SavePerspective()


def demo():
    frame = wx.Frame(None, -1, 'Polarization Correction')
    reduction = Reduction(frame)
    frame.SetSize((600,400))
    frame.Show()
    
if __name__ == "__main__":
    app = wx.PySimpleApp(False)
    demo()
    app.MainLoop()
