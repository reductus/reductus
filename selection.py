# This program is public domain.

import wx,os
import wx.lib.customtreectrl as tree
import wx.lib.newevent

# Update notification for paths in path selector
SelectItemEvent,EVT_ITEM_SELECT = wx.lib.newevent.NewEvent()
ViewItemEvent,EVT_ITEM_VIEW = wx.lib.newevent.NewEvent()

class DataTree(tree.CustomTreeCtrl):
    '''
    Tree to manage the selection of multiple files.
    '''

    def __init__(self, *args, **kwargs):
        kwargs['style'] = tree.TR_DEFAULT_STYLE|tree.TR_HIDE_ROOT
        super(DataTree, self).__init__(*args, **kwargs)
        self.Bind(tree.EVT_TREE_ITEM_EXPANDING, self.onExpandItem)
        #self.Bind(tree.EVT_TREE_SEL_CHANGED, self.onSelected)
        #self.Bind(tree.EVT_TREE_ITEM_CHECKED, self.onChecked)
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

    def onSelected(self, event):
        item = event.GetItem()
        print "selected",self.GetItemText(item)

    def onChecked(self, event):
        item = event.GetItem()
        print "checked",self.GetItemText(item)

    def onExpandItem(self, event):
        item = event.GetItem()
        if not item.HasChildren():
            self.expand(item)


# Update notification for paths in path selector
PathSelectedEvent,EVT_PATH_SELECTED = wx.lib.newevent.NewEvent()
class PathSelector(wx.Panel):
    """
    wx megawidget displaying a label, a path entry box and a button to
    select the path using the file dialog.
    
    Events:
    
    self.Bind(EVT_PATH_SELECTED, self.onPath)
    ...
    def onPath(self, event): print "path",event.path
    """
    def __init__(self, parent, *args, **kw):
        label = kw.pop('label','Path')
        self.validcolor = kw.pop('validcolor',wx.BLACK)
        self.errorcolor = kw.pop('errorcolor',wx.RED)
        path = os.path.abspath(kw.pop('path','.'))
        super(PathSelector,self).__init__(parent, *args, **kw)
        self.label = wx.StaticText(self, -1, label)
        self.path = wx.TextCtrl(self, -1, path, style=wx.TE_PROCESS_ENTER)
        self.button = wx.Button(self, -1, "...")
        self.Bind(wx.EVT_BUTTON, self.onBrowse, self.button)
        self.path.Bind(wx.EVT_TEXT, self.onText)
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
        # TODO Change the background to pink if the text is invalid;
        # the following doesn't seem to force a repaint, even when followed
        # by a self.path.Refresh()
        return
        if self.isvalid():
            self.path.SetForegroundColour(self.validcolor)
        else:
            self.path.SetForegroundColour(self.errorcolor)
            
    def onText(self, event):
        # This is the text before it is changed rather than after
        self.validate()
        self.path.Refresh()
        
    def onEnter(self, event):
        if self.isvalid():
            wx.PostEvent(self,PathSelectedEvent(path=self.path.GetValue()))

    def onBrowse(self, event):
        oldpath = self.path.GetValue()
        dlg = wx.DirDialog(self, message="Choose a directory",
                           style=wx.DD_DIR_MUST_EXIST) #, defaultPath=oldpath)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.path.Replace(0,len(oldpath),path)
            wx.PostEvent(self,PathSelectedEvent(path=self.path.GetValue()))
        dlg.Destroy()
        pass


class SelectionPanel(wx.Panel):
    def __init__(self, *args, **kw):
        root = kw.pop('root',None)
        if root is None: root = '.'

        super(SelectionPanel,self).__init__(*args, **kw)
        self._path = PathSelector(self,path=root)
        self._tree = DataTree(self)
        self._tree.root(root)
        self._path.Bind(EVT_PATH_SELECTED, self.onRefresh)
        self._tree.Bind(tree.EVT_TREE_ITEM_CHECKED, self.onChecked)
        self._tree.Bind(tree.EVT_TREE_SEL_CHANGED, self.onSelected)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self._path, flag=wx.EXPAND)
        sizer.Add(self._tree, 1, flag=wx.GROW|wx.SHRINK)
        self.SetSizer(sizer)

    def onRefresh(self, event):
        self._tree.root(self._path.GetValue())

    def onChecked(self, event):
        item = event.GetItem()
        self._tree.SelectItem(item)
        wx.PostEvent(self,SelectItemEvent(data=self._tree.GetPyData(item),
                                          enabled=self._tree.IsItemChecked(item)))
        #print "checked",self._tree.GetItemText(item)

    def onSelected(self, event):
        item = event.GetItem()
        if self._tree.IsSelected(item):
            wx.PostEvent(self,ViewItemEvent(data=self._tree.GetPyData(item)))
        #print "selected",self._tree.GetItemText(item)


def demo():
    class DemoFrame(wx.Frame):
        def __init__(self, *args, **kwargs):
            super(DemoFrame, self).__init__(*args, **kwargs)
            self.selection = SelectionPanel(self,root='..')
            #self.Bind(tree.EVT_TREE_SEL_CHANGED, self.onSelected)
            self.selection.Bind(EVT_ITEM_SELECT, self.onChecked)

        def onSelected(self, event):
            item = event.GetItem()
            print "selected",item
            
        def onChecked(self, event):
            print "checked",event.data,event.enabled

    frame = DemoFrame(None)
    frame.Show()

if __name__ == "__main__": 
    app = wx.App(False)
    demo()
    app.MainLoop()
