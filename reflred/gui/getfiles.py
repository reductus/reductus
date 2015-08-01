"""
GUI driver for the polarization correction code polcor.
"""

import sys
import os
import traceback

import wx,wx.aui

from .. import formats
from ..formats.icpformat import gzopen
from .selection import SelectionPanel, EVT_ITEM_SELECT, EVT_ITEM_VIEW
from .wxpylab import PlotPanel

class DataSelection(wx.Panel):
    def __init__(self, *args, **kw):
        path = kw.pop('root','.')
        wx.Panel.__init__(self, *args, **kw)

        self.datasets = {}
        self.selected = {}
        if True:
            # Use simple sashes
            splitter = wx.SplitterWindow(self)
            self.selector = SelectionPanel(splitter, root=path)
            right = wx.SplitterWindow(splitter)
            self.metadata = wx.TextCtrl(right,style=wx.TE_MULTILINE|wx.TE_AUTO_SCROLL)
            self.plotter = PlotPanel(right)

            splitter.SetSashGravity(0.3)
            splitter.SplitVertically(self.selector, right, 200)
            right.SetSashGravity(0.3)
            right.SplitHorizontally(self.metadata, self.plotter, 120)
            container = splitter
        else:
            # Use AUI notebook
            self.notebook = wx.aui.AuiNotebook(self)
            self.selector = SelectionPanel(self.notebook, root=path)
            self.metadata = wx.TextCtrl(self,style=wx.TE_MULTILINE|wx.TE_RICH2)
            self.plotter = PlotPanel(self.notebook)
            self.notebook.AddPage(self.selector, "Selection")
            self.notebook.AddPage(self.metadata, "Metadata")
            self.notebook.AddPage(self.plotter, "Plot")
            #self.notebook.Bind(wx.aui.EVT_AUI_RENDER,self.onRender)
            container = self.notebook

        sizer = wx.BoxSizer()
        sizer.Add(container, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.selector.Bind(EVT_ITEM_SELECT, self.onSelect)
        self.selector.Bind(EVT_ITEM_VIEW, self.onView)

    def load(self, filename):
        # Check if it is already loaded
        if filename in self.datasets:
            return self.datasets[filename]

        if os.path.isdir(filename):
            return []

        # Try loading data, guessing format from file extension
        try:
            data = formats.load(filename)
        except:
            metadata = ["=== %s ==="%filename]
            if not filename.lower().endswith('.log'):
                metadata += [str(sys.exc_value), "", traceback.format_exc(),
                             "=============="]
            try:
                with gzopen(filename) as fid:
                    metadata += [line.rstrip() for line in fid]
            except:
                pass
            self._show_metadata("\n".join(metadata))
            data = []
        else:
            pass
            #if data.prop.polarization == "":
            #    # TODO Temporary hack: unpolarized data dumped into ++
            #    data.prop.polarization = "++"
        self.datasets[filename] = data
        return data

    def _show_metadata(self, metadata):
        # TODO this isn't shifting the text control on aqua
        # Tried setting focus first without success:
        #   focuswin = wx.Window.FindFocus()
        #   self.metadata.SetFocus()
        #   ...
        #   if focuswin: focuswin.SetFocus()
        #self.metadata.SetFocus()
        pt = self.metadata.GetInsertionPoint()
        metadata = metadata.decode('latin-1').encode('utf8')
        self.metadata.Replace(0,self.metadata.GetLastPosition(),metadata)
        self.metadata.SetInsertionPoint(pt)
        # See if simulating a right-left sequence moves the view
        #kevent = wx.KeyEvent(wx.EVT_CHAR)
        #kevent.m_keyCode = wx.WXK_RIGHT
        #self.metadata.EmulateKeyPress(kevent)
        #kevent.m_keyCode = wx.WXK_LEFT
        #self.metadata.EmulateKeyPress(kevent)
        #print "Setting point to",pt
        self.metadata.ShowPosition(pt)

    def onView(self, event):
        filename = event.data
        wx.GetTopLevelParent(self).SetTitle(filename)
        data = self.load(filename)

        if data:
            self._show_metadata("=== %s ===\n"%filename + str(data[0]))
            with self.plotter.pylab_figure as pylab:
                pylab.clf()
                pylab.hold(True)
                for filename,filedata in sorted(self.selected.items()):
                    for part in filedata:
                        part.plot()
                for part in data:
                    part.plot()
                pylab.legend()


    def onSelect(self, event):
        filename = event.data
        print "selected",filename
        if event.enabled == True:
            data = self.load(filename)
            if data:
                self.selected[filename] = data
        else:
            if filename in self.selected:
                del self.selected[filename]

    def onRender(self, event):
        # AUI only - ignored
        print "rendering"
        mgr = self.notebook.GetAuiManager()
        print "perspective",mgr.SavePerspective()


def demo(path='.'):
    frame = wx.Frame(None, -1, "Selector")
    reduction = DataSelection(frame, root=path)
    frame.SetSize((600,400))
    frame.Show()

if __name__ == "__main__":
    app = wx.App(False)
    path = sys.argv[1] if len(sys.argv)>1 else '.'
    demo(path)
    app.MainLoop()