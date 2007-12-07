"""
GUI driver for the polarization correction code polcor.
"""

import sys
import wx,wx.aui
import icpformat
from selection import SelectionPanel, EVT_ITEM_SELECT, EVT_ITEM_VIEW
from polplot import Plotter, Plotter4



class Reduction(wx.Panel):
    def __init__(self, *args, **kw):
        wx.Panel.__init__(self, *args, **kw)

        self.data = {}
        self.plotid = {}
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
            self.selector = SelectionPanel(self)
            self.plotter = Plotter(self)
            self.metadata = wx.TextCtrl(left,style=wx.TE_MULTILINE|wx.TE_AUTO_SCROLL)
            self.slice = Plotter(right)
            self.notebook = wx.aui.AuiNotebook(self)
            self.notebook.AddPage(self.selector, "Selection")
            self.notebook.AddPage(self.plotter, "Reduction")
            self.notebook.AddPage(self.metadata, "Metadata")
            self.notebook.AddPage(self.slice, "Slice")
            self.notebook.Bind(wx.aui.EVT_AUI_RENDER,self.onRender)
            container = self.notebook

        sizer = wx.BoxSizer()
        sizer.Add(container, 1, wx.EXPAND)
        self.SetSizer(sizer)
        
        self.selector.Bind(EVT_ITEM_SELECT, self.onSelect)
        self.selector.Bind(EVT_ITEM_VIEW, self.onView)

    def load(self, filename):
        # Try loading data
        print "get data for",filename
        try:
            if filename in self.data:
                print "already loaded"
                data = self.data[filename]
            else:
                print "loading"
                data = icpformat.data(filename)
                self.data[filename] = data
        except:
            print "unable to laod %s\n  %s"%(filename, sys.exc_value)
            data = None
        return data
        
    def onView(self, event):
        filename = event.data
        data = self.load(filename)
        if data is not None:
            pt = self.metadata.GetInsertionPoint()
            self.metadata.Replace(0,self.metadata.GetLastPosition(),data.summary())
            self.metadata.SetInsertionPoint(pt)
            print "Setting point to",pt
            self.metadata.ShowPosition(pt)
            
 
    def onSelect(self, event):
        filename = event.data
        if event.enabled == True:
            data = self.load(filename)
            if data:
                im = self.plotter.surface(data.prop.polarization,data)
                self.plotid[filename] = im
        else:
            self.plotter.delete(self.plotid[filename])
            del self.plotid[filename]
        self.plotter.update()

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