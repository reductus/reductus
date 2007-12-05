# This program is public domain.

import wx,os
import wx.lib.customtreectrl as tree

class DataTree(tree.CustomTreeCtrl):
    '''
    Tree to manage the selection of multiple files.
    '''

    def __init__(self, *args, **kwargs):
        kwargs['style'] = tree.TR_DEFAULT_STYLE|tree.TR_HIDE_ROOT
        super(DataTree, self).__init__(*args, **kwargs)
        self.Bind(tree.EVT_TREE_ITEM_EXPANDING, self.OnExpandItem)
        self.Bind(tree.EVT_TREE_SEL_CHANGED, self.OnSelected)
        self.Bind(tree.EVT_TREE_ITEM_CHECKED, self.OnChecked)
        self.AddRoot('')
        self._collapsing = False

    def root(self, path):
        item = self.GetRootItem()
        self.DeleteChildren(item)
        path = os.path.abspath(path)
        self.SetPyData(item, path)
        #self.SetItemHasChildren(item, os.path.isdir(path))
        #self.Toggle(item)  # Expand the path
        self.expand(item)

    def expand(self, item):
        path = self.GetPyData(item)
        if not os.path.isdir(path): return
        for file in os.listdir(path):
            if file[0] == '.': continue
            childpath = os.path.join(path,file)
            check = 0 if os.path.isdir(childpath) else 1
            child = self.AppendItem(item,file,ct_type=check)
            self.SetPyData(child,childpath)
            self.SetItemHasChildren(child, check==0)

    def OnSelected(self, event):
        item = event.GetItem()
        print "selected",self.GetItemText(item)

    def OnChecked(self, event):
        item = event.GetItem()
        self.SelectItem(item)
        print "checked",self.GetItemText(item)

    def OnExpandItem(self, event):
        item = event.GetItem()
        self.expand(item)


# Update notification for paths in path selector
wxEVT_COMMAND_PATH_UPDATED = wx.NewEventType()
EVT_PATH_UPDATED = wx.PyEventBinder(wxEVT_COMMAND_PATH_UPDATED, 1)
class PathUpdatedEvent(wx.PyCommandEvent):
    def __init__(self, id, value = "", object=None):
        wx.PyCommandEvent.__init__(self, wxEVT_COMMAND_PATH_UPDATED, id)

        self.value = value
        self.SetEventObject(object)

    def GetValue(self):
        """Retrieve the value of the control at the time
        this event was generated."""
        return self.value

class PathSelector(wx.Panel):
    """
    wx megawidget displaying a label, a path entry box and a button to
    select the path using the file dialog.
    """
    def __init__(self, parent, *args, **kw):
        label = kw.pop('label','Path')
        self.color = kw.pop('color',wx.BLACK)
        self.errorcolor = kw.pop('errorcolor',wx.RED)
        path = os.path.abspath(kw.pop('path','.'))
        super(PathSelector,self).__init__(parent, *args, **kw)
        self.label = wx.StaticText(self, -1, label)
        self.path = wx.TextCtrl(self, -1, path, style=wx.TE_PROCESS_ENTER)
        self.button = wx.Button(self, -1, "...")
        self.Bind(wx.EVT_BUTTON, self.onBrowse, self.button)
        #self.path.Bind(wx.EVT_TEXT, self.onText)
        self.path.Bind(wx.EVT_TEXT_ENTER, self.onEnter)
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        flag = wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_CENTER_HORIZONTAL|wx.ALL
        border=2
        sizer.Add(self.label, flag=flag, border=border)
        sizer.Add(self.path, 1, flag=flag|wx.GROW|wx.SHRINK, border=2)
        sizer.Add(self.button, flag=flag, border=2)
        self.SetSizer(sizer)

    def GetValue(self):
        return self.path.GetValue()

    def isvalid(self):
        return os.path.isdir(self.path.GetValue())
    
    def validate(self):
        if self.isvalid():
            self.path.SetForegroundColour(self.color)
        else:
            self.path.SetForegroundColour(self.errorcolor)
            
    def onText(self, event):
        print "onText"
        self.validate()
        
    def onEnter(self, event):
        # Forward the EVT_TEXT_ENTER events if the value is good
        #print "receiving 'Enter'"
        if self.isvalid():
            self.GetEventHandler().ProcessEvent(event)
        #event.Skip()
        pass

    def onBrowse(self, event):
        oldpath = self.path.GetValue()
        dlg = wx.DirDialog(self, message="Choose a directory",
                           style=wx.DD_DIR_MUST_EXIST, defaultPath=oldpath)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.path.Replace(0,len(oldpath),path)
            # TODO: How do I generate a EVT_TEXT_ENTER event?
            # Emulating a Return key doesn't work:
            #    self.path.EmulateKeyPress(wx.KeyEvent(wx.WXK_RETURN))
        dlg.Destroy()
        pass


class SelectionPanel(wx.Panel):
    def __init__(self, *args, **kw):
        root = kw.pop('root',None)
        if root is None: root = '.'

        super(SelectionPanel,self).__init__(*args, **kw)
        self._path = PathSelector(self,path=root)
        self.Bind(wx.EVT_TEXT_ENTER, self.onRefresh)
        self._tree = DataTree(self)
        self._tree.root(root)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self._path, flag=wx.EXPAND)
        sizer.Add(self._tree, 1, flag=wx.GROW|wx.SHRINK)
        self.SetSizer(sizer)

    def onRefresh(self, event):
        #print "refresh list"
        self._tree.root(self._path.GetValue())


def demo():
    class DemoFrame(wx.Frame):
        def __init__(self, *args, **kwargs):
            super(DemoFrame, self).__init__(*args, **kwargs)
            self.selection = SelectionPanel(self,root='..')
            
    frame = DemoFrame(None)
    frame.Show()

if __name__ == "__main__": 
    app = wx.App(False)
    demo()
    app.MainLoop()
