#!/usr/bin/env python
# This program is public domain

"""
Define NeXus file structures.
Load/save NeXus files.

The NeXus class defines the NeXus file handle and operations on the file.
tree = read(filename) returns the file structure
tree points to the Group node for the root of the NeXus file.
tree.children is set of entries in the file.
Nodes have name and nxclass attributes.
"""

from copy import copy, deepcopy
import numpy as N
import os,os.path
import napi

class NeXus:
    """
    Slightly pretty interface to the NeXus file API.

    Usage:

    nx = NeXus(filename, ['r','rw','w'])

    nx.path
      - list of pairs (name,nxclass) representing the currently open dataset.
      - the final element may be a bare name if the path ends in a dataset
      e.g., [('entry1','NXentry'),('liquids','NXinstrument'),('detector','NXdetector'),
    nx.open()
      - open the file
    nx.close()
      - close the file
    nx.openpath([(name,nxclass),(name,nxclass),...,data])
      - open the path to data
    ...etc...  more documentation when we are sure we are keeping the code :-)
    
    Note: Currently only file reading is supported.

    Note: even though HDF may support multiple open data sets, the
    NeXus API does not appear to support them, so we will operate on
    the assumption that only one data set may be open at a time.
    """
    def __init__(self, filename, access='r'):
        """
        Create a file handle for interacting with NeXus files.
        """
        if access=='r':
            mode = napi.READ
        elif access=='rw':
            mode = napi.RDWR
        elif access=='w':
            mode = napi.CREATE5
        else:
            raise ValueError, "expected open as 'r', 'rw' or 'w'"
        if (mode == napi.READ or mode == napi.RDWR) \
           and not os.path.isfile(filename):
            raise ValueError, "file %s does not exist"%(filename)
        self.filename = filename
        self.mode = mode
        self.isopen = False
        self.path = [] # Currently open group/data

    def __del__(self):
        """
        Make sure the file is closed before deleting.
        """
        self.close()

    def __str__(self):
        """
        Return a string representation of the NeXus file handle.
        """
        return "NeXus(%s)"%self.filename
        
    def open(self):
        """
        Open the nexus file handle.  You will need to use nx.opengroup()
        repeatedly, followed by nx.opendata() before reading a dataset,
        or alternatively use nx.openpath() to open the file at the correct
        location for reading.
        """
        if self.isopen: return
        self.handle = napi.open(self.filename, self.mode)
        self.path = []
        self.isopen = True

    def close(self):
        """
        Close the nexus file handle.  Use nx.openpath(path) to
        reopen the file for reading data.  Use nx.close() after
        reading if you need to free system resources.
        """
        if not self.isopen: return
        self.isopen = False
        self.path = []
        napi.close(self.handle)

    def opengroup(self,name,nxclass):
        if self.isdata():
            raise RuntimeError, "Data is open---cannot open group"
        napi.opengroup(self.handle,name,nxclass)
        self.path.append((name,nxclass))

    def closegroup(self):
        if self.isdata():
            raise RuntimeError, "Data is open within group"
        napi.closegroup(self.handle)
        del self.path[-1]

    def groupinfo(self):
        """
        Returns name, nxclass and number of entries for the currently
        open group.  Unlike napi getgroupinfo, names are only the name
        of the leaf node, not the entire path to the leaf.
        """
        n,path,nxclass = napi.getgroupinfo(self.handle)
        # Convert path to just the leaf name
        name = path.split("/")[-1]
        return n,name,nxclass
        

    def opendata(self,name):
        if self.isdata():
            raise RuntimeError, "Already have data open"
        napi.opendata(self.handle, name)
        self.path.append(name)

    def closedata(self):
        if not self.isdata():
            raise RuntimeError, "Data is not open"
        napi.closedata(self.handle)
        del self.path[-1]

    def numattrs(self):
        return napi.getattrinfo(self.handle)

    def nextattr(self):
        name,length,storage = napi.getnextattr(self.handle)
        value = napi.getattr(self.handle, name, length, storage)
        return name,value,storage

    # High level functions
    def _place(self):
        """
        Return file location formatted for error messages.
        """
        if len(self.path):
            # Report on the final open path
            name = self.path[-1]
            if isinstance(end,tuple):
                return name[1]+":"+name[0]+" in "+self.filename
            else:
                return "data:"+name+" in "+self.filename
        else:
            # Root entry doesn't have a class
            return "root in "+self.filename

    def isdata(self):
        """
        Return true if the currently open object is data rather than group.
        """
        return len(self.path) > 0 and not isinstance(self.path[-1],tuple)
    
    def _maybeclosedata(self):
        """
        Close a data block if it is the last thing opened.  This is needed
        for things such as openpath, which need to close the existing group
        prior to opening a new group.
        """
        if self.isdata(): self.closedata()
        return
    
    def openpath(self,path):
        """
        Set the file cursor to the name data item and open the data.
        """
        # Make sure file is open
        if not self.isopen: self.open()
        
        # Check if correct path is open
        if len(self.path) == len(path):
            if all([o[0]==p[0] and o[1]==p[1]
                    for (o,p) in zip(self.path,path)]):
                return

        # Close existing path
        self._maybeclosedata()
        for i in range(len(self.path)):
            self.closegroup()

        # Open new path up to penulitmate level
        for i in range(len(path)-1):
            self.opengroup(*path[i])

        # The ultimate path component may be a group or a dataset
        if len(path) > 0:
            if isinstance(path[-1],tuple):
                self.opengroup(*path[-1])
            else:
                self.opendata(path[-1])

    def readattrs(self):
        """
        Return the attributes for the currently open group/data or for
        the file if no group or data object is open.
        """
        # FIXME: attr needs to be a dict extension with a storage property
        # for each item in the class
        attr = dict()
        attrtype = dict()
        for i in range(self.numattrs()):
            name,value,storage = self.nextattr()
            pair = Attr(value,storage)
            attr[name] = pair
            #print "read attr",name,storage,value
        return attr

    def readgroup(self):
        """
        Read the currently open group and all subgroups.
        """
        # TODO: does it make sense to read without recursing?
        # TODO: can we specify which NXclasses we are interested
        # in and skip those of different classes?
        n,name,nxclass = self.groupinfo()
        attr = self.readattrs()
        group = Group(nxclass,name,attr)
        entries = {}
        for i in range(n):
            name,nxclass = napi.getnextentry(self.handle)
            if nxclass == 'SDS':
                # Finally some data, but don't read it if it is big
                # Instead record the location, type and size
                self.opendata(name)
                attr = self.readattrs()
                shape,storage = napi.getinfo(self.handle)
                if N.prod(shape) < 1000:
                    value = napi.getdata(self.handle,storage,shape)
                else:
                    value = None
                data = Data(self,name,storage,shape,attr=attr,value=value)
                self.closedata()
                entries[name] = data
            else:
                #print "open for reading",nxclass,name
                self.opengroup(name,nxclass)
                entries[name] = self.readgroup()
                self.closegroup()
        group.children = entries
        return group


    def writeattrs(self,attr):
        """
        Return the attributes for the currently open group/data or for
        the file if no group or data object is open.
        """
        for name,pair in attr.iteritems():
            #print "write attr",name,pair.storage,pair.value
            napi.putattr(self.handle,name,pair.value,pair.storage)

    def writegroup(self, group):
        """
        Read the currently open group and all subgroups.
        """
        # TODO: does it make sense to read without recursing?
        # TODO: can we specify which NXclasses we are interested
        # in and skip those of different classes?
        #print "creating group",group.nxclass,group.name
        napi.makegroup(self.handle, group.name, group.nxclass)
        self.opengroup(group.name, group.nxclass)
        self.writeattrs(group.attr)
        for child in group.children.itervalues():
            if child.nxclass == 'SDS':
                # Finally some data, but don't read it if it is big
                # Instead record the location, type and size
                #print "creating data",child.name,child.shape,child.storage
                if N.prod(child.shape) > 10000:
                    # Compress the fastest moving dimension of large datasets
                    compression = N.ones(len(child.shape),'i')
                    compression[-1] = child.shape[-1]
                    napi.compmakedata(self.handle,child.name,child.shape,
                                      child.storage, 'lzw', compression)
                else:
                    # Don't use compression for small datasets
                    napi.makedata(self.handle,child.name,child.shape,
                                  child.storage)
                self.opendata(child.name)
                self.writeattrs(child.attr)
                value = child.read()
                napi.putdata(self.handle,value,child.storage)
                self.closedata()
            else:
                self.writegroup(child)
        self.closegroup()


def read(filename):
    nx = NeXus(filename,'r')
    nx.open()
    tree = nx.readgroup()
    nx.close()
    return tree

class Attr(object):
    def __init__(self,value=None,storage='char'):
        self.value,self.storage = value,storage

class Node(object):
    """
    Abstract base class for elements in nexus files.
    The individual objects may be either SDS data objects or groups.
    """
    nxclass = "unknown"
    children = None
    attr = None

    def print_attr(self,indent=0):
        if self.attr is not None:
            #print " "*indent, "Attributes:"
            names = self.attr.keys()
            names.sort()
            for k in names:
                print " "*(indent+2),k,":",self.attr[k].value

    def search(self,pattern):
        """
        Pattern = class:name@attr
        """
        if self.attr is not None:
            for k,v in self.attr.iteritems():
                pass
        for k,v in self.children.iteritems():
            pass

    def print_value(self,indent=0):
        print '\n'.join([(" "*(indent+1))+s for s in str(self).split('\n')])

    def print_tree(self,indent=0,attr=False):
        print " "*indent,self.nxclass,":",self.name
        if attr: self.print_attr(indent=indent)
        self.print_value(indent)
        names = self.children.keys()
        names.sort()
        for k in names:
            print " "*indent,k
            self.children[k].print_tree(indent+2,attr=attr)

class Data(Node):
    """
    NeXus data object.
    Operations are querying type and dimensions, reading the entire
    data block or reading a single slab.
    The NeXus file class keeps track of where the file cursor is
    pointing at any given time, opening and closing groups as necessary
    to get to the right place.
    Note that this class does not cache a copy of the data.
    """
    def __init__(self,nx,name,storage,shape,attr=None,value=None):
        self.nx = nx
        self.path = copy(nx.path) # Save the current path
        self.nxclass = "SDS" # Scientific Data Set
        self.name = name
        self.storage = storage
        self.shape = shape
        self.isstr = self.storage == 'char'
        self.isscalar = len(shape==1) and shape[0] == 1
        self.value = value
        self.children = {}
        if attr is None: attr = {}
        self.attr = attr

    def __str__(self):
        if self.value is not None:
            # If the value is already loaded we can maybe do
            # better than just printing the array dimensions.
            if self.isstr:
                return self.value
            elif self.isscalar:
                return str(self.value)
            elif N.prod(self.shape) < 8 and self.value is not None:
                return str(self.value)
        dims = 'x'.join([str(n) for n in self.shape])
        return "Data(%s %s)"%(self.storage,dims)
    def slab(self,slice):
        nx.openpath(self)
        slab = nx.readslab(self,slice)
        return slab
    def read(self):
        if self.value is not None:
            return self.value
        self.nx.openpath(self.path)
        self.value = napi.getdata(self.nx.handle,self.storage,self.shape)
        return self.value

class Group(Node):
    """
    Storage class for the 
    """
    def __init__(self,nxclass,name,attr=None):
        self.children = {}
        self.nxclass = nxclass
        self.name = name
        if attr is None: attr = {}
        self.attr = attr
    def print_value(self,indent=0):
        pass

def copyfile(fromfile,tofile):
    tree = read(fromfile)
    file = NeXus(tofile,'w')
    file.open()
    for entry in tree.children.itervalues():
        file.writegroup(entry)
    file.close()
    

def listfile(file):
    """
    Read and summarize the set of nexus files passed in on the command line.
    """
    tree = read(file)
    tree.print_tree(attr=True)

def cmdline(argv):
    op = argv[1] if len(argv) > 1 else ''
    if op == 'ls': 
        for f in argv[2:]: listfile(f)
        print "processed",len(argv[2:])
    elif op == 'copy' and len(argv)==4: 
        copyfile(argv[2],argv[3])
    else: 
        usage = """
usage: %s copy fromfile.nxs tofile.nxs
usage: %s ls *.nxs
        """%(argv[0],argv[0])
        print usage

if __name__ == "__main__":
    import sys
    cmdline(sys.argv)
