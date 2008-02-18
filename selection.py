# This program is public domain.

import wx,os,re,time
import wx.lib.customtreectrl as tree
import wx.lib.newevent

class Datasets:
    # TODO: Datasets is not yet used.  Want a selection widget that
    # displays available datasets and metadata.  Furthermore, said
    # selection widget should have transparent access to the various
    # data portals, presumably reverting to portal queries to retrieve
    # the relevant information.  This will require coordination with
    # the SNS, ISIS, NCNR, etc. to locate and query the various data
    # servers.
    '''
    A dataset is a set of files with an embedded sequence number.  The
    Dataset class gathers filenames one at a time and composes them
    into datasets.

    The sequence number is assumed to be at most three digits, and to
    be the last three digits before the extension.  The dataset includes
    both the sequence number and the extension.

    For each dataset there is a count of the number of files in the
    dataset (max 1000) and the starting and ending sequence numbers.
    The filenames associated with the smallest and largest sequence
    numbers are retained so the starting and ending time can be read
    from the directory or the file (using method latest()).  The entire
    list of files in the dataset is also available.

    Only files in the set of valid extensions are considered datasets.
    All others are classed as 'other'.
    '''

    # The following pattern matches:
    #    name ([^.]*?), the *? meaning match as few characters as possible
    #    seq ([0-9]{1,3})?, the {1,3} matches one to three digits, ()? optional
    #    junk [^.0-9], stuff after the sequence number such as bkg
    #    ext  ([.].*)?, with ()? being an optional group
    # Note that name is empty if there is no sequence number, meaning
    # unsequenced items will all be dumped into the same dataset.
    pattern = re.compile('^(?P<name>[^.]*?)(?P<seq>[0-9]{1,3})?(?P<junk>[^.0-9]*?)(?P<ext>[.].*)?$')
    #match = pattern.match('Field5T4345bkg.uxd')
    #dict((a,match.group(a)+"") for a in ['name','seq','junk','ext'])

    class Dataset:
        count = 0
        files = None
        min = 1000
        max = -1
        minfile = ''
        maxfile = ''
        time = None # Time of the highest sequence number
        def __init__(self): self.files = []
        def add(self, seq, filename):
            if seq < self.min:
                self.min = seq
                self.minfile = filename
            if seq > self.max:
                self.max = seq
                self.maxfile = filename
                self.time = None
            self.count += 1
            self.files.append(filename)
        def latest(self):
            if self.time is not None:
                self.time = os.path.getmtime(self.maxfile)
            return time.strformat('%Y-%m-%d',time.localtime(self.time))

    def __init__(self, extensions=None):
        self.seen = set()
        self.extensions = extensions
        self.dataset = {}

    def walk(self, pattern="", recurse=False, revisit=False):
        """
        Walk a file pattern adding all new files into the list
        of available datasets.  The pattern has an implicit '*'
        at the end, thus matching all leading elements.  If recurse
        is true, then enter subdirectories.  If revisit is true,
        revisit subdirectories that have already been visited.

        Note: the goal of revisit is to support refresh on the
        list of available files, however revisiting a whole
        subtree can be expensive.  Ideally this would run in
        a separate thread with yields to the GUI which could
        update the list of available datasets and/or a waitbar
        while this is happening.  Yet again good interface trumps
        clean separation?
        """
        for file in glob.iglob(pattern+'*'):
            if revisit or file in self.seen: continue
            if recurse and os.path.isdir(file):
                self.seen.add(file)
                self.walk(os.path.join(file,'*'))
            else:
                self.add(filename)
        pass

    def add(self, filename):
        """
        Add a single file to a dataset.
        """
        if filename in self.seen: return
        self.seen.add(filename)
        base = os.path.basename(filename)
        match = self.pattern.match(base)
        name = match.group('name')
        seq = match.group('seq')
        seq = int(seq) if seq is not None else 0
        ext = match.group('ext')
        if ext in self.extensions or self.extensions is None:
            item = base+ext
            if item not in self.dataset:
                self.dataset[item] = Dataset()
            self.dataset[item].add(seq,filename)
        pass

    def __add__(self, other):
        """
        Merge two datasets (e.g., from different subtrees)

        Not sure yet if this is necessary --- maybe we want to enter
        the subtrees and see what is available?
        """
        pass

# Update notification for paths in path selector
SelectItemEvent,EVT_ITEM_SELECT = wx.lib.newevent.NewEvent()
ViewItemEvent,EVT_ITEM_VIEW = wx.lib.newevent.NewEvent()

class DirTree(tree.CustomTreeCtrl):
    '''
    Traditional directory tree to manage the selection of multiple files.
    '''

    def __init__(self, *args, **kwargs):
        kwargs['style'] = tree.TR_DEFAULT_STYLE|tree.TR_HIDE_ROOT
        super(DirTree, self).__init__(*args, **kwargs)
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
        self._tree = DirTree(self)
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
