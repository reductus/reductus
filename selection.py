# This program is public domain.

import wx,os
import wx.lib.customtreectrl as tree

# EVT_COMMAND_TREE_...
#    BEGIN/END LABEL_EDIT/DRAG
#    BEGIN RDRAG
#    DELETE ITEM
#    ITEM EXPAND(ED/ING)/COLLAPS(ED/ING)/ACTIVATED
#    ITEM GETTOOLTIP/MENU
#    ITEM RIGHT/MIDDLE CLICK
#    GET/SET INFO
#    SEL CHANG(ED/ING)
#    STATE IMAGE_CLICK
#    KEY DOWN
# Mouse Events:
#    item, flags = tree.HitTest(event.GetPosition())
#        


class DataTree(tree.CustomTreeCtrl):
    '''
    Tree to manage reflectometry datasets.
    '''

    def __init__(self, *args, **kwargs):
        kwargs['style'] = tree.TR_DEFAULT_STYLE|tree.TR_HIDE_ROOT
        super(DataTree, self).__init__(*args, **kwargs)
        #self.Bind(wx.EVT_TREE_ITEM_COLLAPSING, self.OnCollapseItem)
        self.Bind(tree.EVT_TREE_ITEM_EXPANDING, self.OnExpandItem)
        self.Bind(tree.EVT_TREE_SEL_CHANGED, self.OnSelected)
        self.Bind(tree.EVT_TREE_ITEM_CHECKED, self.OnChecked)
        self.AddRoot('')
        self._collapsing = False

    def add(self, path):
        path = os.path.abspath(path)
        item = self.AppendItem(self.GetRootItem(), path)
        self.SetPyData(item, path)
        self.SetItemHasChildren(item, os.path.isdir(path))
        self.Toggle(item)  # Expand the path

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

    def OnCollapseItem(self, event):
        # Be prepared, self.CollapseAndReset below may cause
        # another wx.EVT_TREE_ITEM_COLLAPSING event being triggered.
        if self._collapsing:
            event.Veto()
            return

        self._collapsing = True
        item = event.GetItem()
        self.CollapseAndReset(item)
        self.SetItemHasChildren(item)
        self._collapsing = False

class SelectionPanel(wx.Panel):
    def __init__(self, *args, **kw):
        root = kw.pop('root',None)
        super(SelectionPanel,self).__init__(*args, **kw)
        self._tree = DataTree(self)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self._tree, 1, flag=wx.GROW|wx.SHRINK)
        self.SetSizer(sizer)

        # Populate the tree with the list of root directories containing data
        if root is None: root = '.'
        self._tree.add(root)


    def refresh(self):
        pass


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
