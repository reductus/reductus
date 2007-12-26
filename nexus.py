#!/usr/bin/env python
# This program is public domain

"""
Main class:

NeXus(file,mode) 
   - structure-based interface to NeXus files.



Helper classes:

Group(name,class)
    - NeXus group containing fields
Data(name)
    - NeXus data within a field
"""

# TODO: Rather than carrying around the 'storage' name for attributes
# TODO: and data values, we could be storing them directly as numpy
# TODO: types.  We should be able to infer type directly from the value,
# TODO: particularly if we use numpy types for scalars.

from copy import copy, deepcopy
import numpy as N
import os,os.path
import nxs

class NeXus(nxs.NeXus):
    """
    Structure-based interface to the NeXus file API.

    Usage:

    nx = NeXus(filename, ['r','rw','w'])
    nx.read()
      - read the structure of the NeXus file.  This returns a NeXus tree.
    nx.write(root)
      - write a NeXus tree to the file.

    Example:

      nx = NeXus('REF_L_1346.nxs','r')
      tree = nx.read()
      for entry in tree.nxdict.itervalues():
          process(entry)
      copy = NeXus('modified.nxs','w')
      copy.write(tree)

    Note that the large datasets are not loaded immediately.  Instead, the
    when the data set is requested, the file is reopened, the data read, and
    the file closed again.  open/close are available for when we want to
    read/write slabs without the overhead of moving the file cursor each time.
    The Data nodes in the returned tree hold the node values.



    Additional functions used by the Data class:
    
    nx.readpath(path)
      - read data from a particular path in the nexus file.
    nx.writepath(path,value,storage=NXstorage)
      - write data to a particular path.  [Not implemented]
    nx.openpath()
      - open to a particular data for slab read/write [Not implemented]
    nx.readslab(path,type,dims)
      - return a slab of data. [Not implemented]
    nx.writeslab(path,type,dims)
      - write a slab of data. [Not implementd]
    nx.open()
      - open the file; done implicitly on read/write/readpath
    nx.close()
      - close the file; done implicitly on read/write/readpath

    """
    def read(self):
        """
        Read the nexus file structure from the file.  Reading of large datasets
        will be postponed.  Returns a tree of Group, Data and Link nodes.
        """
        # return to root
        self.open()
        self.openpath("/")
        root = self._readgroup()
        self.close()
        return root

    def write(self, tree):
        """
        Write the nexus file structure to the file.  The file is assumed to
        start empty.  
        
        Updating individual nodes can be done using the napi interface, with
        nx.handle as the nexus file handle.
        """
        self.open()
        links = []
        # Root node is special --- only write its children.
        # TODO: maybe want to write root node attributes?
        for entry in tree.nxdict.itervalues():
            links += self._writegroup(entry, path="")
        self._writelinks(links)
        self.close()

    def readpath(self, path):
        """
        Read the data on a particular file path.
        
        Returns a numpy array containing the data, a python scalar, or a
        string depending on the shape and storage class.
        """
        self.open()
        self.openpath(path)
        return self.getdata()

    def _readattrs(self):
        """
        Return the attributes for the currently open group/data or for
        the file if no group or data object is open.
        """
        # FIXME: attr needs to be a dict extension with a storage property
        # for each item in the class
        attr = dict()
        attrtype = dict()
        for i in range(self.getattrinfo()):
            name,length,nxtype = self.getnextattr()
            value = self.getattr(name, length, nxtype)
            pair = Attr(value,nxtype)
            attr[name] = pair
            #print "read attr",name,nxtype,value
        return attr

    def _readdata(self,name,path):
        """
        Read a data node, returning Data or Link depending on the
        nature of the node.
        """
        # Finally some data, but don't read it if it is big
        # Instead record the location, type and size
        path = "/"+path+"/"+name
        self.opendata(name)
        attr = self._readattrs()
        if 'target' in attr and attr['target'].value != path:
            # This is a linked dataset; don't try to load it.
            #print "read link %s->%s"%(attr['target'].value,path)
            data = Link(name,attr=attr)
        else:
            dims,type = self.getinfo()
            if N.prod(dims) < 1000:
                value = self.getdata()
            else:
                value = None
            data = Data(name,type,dims,
                        file=self,path=path,attr=attr,value=value)
        self.closedata()
        return data

    def _readchildren(self,n,path):
        children = {}
        for i in range(n):
            name,nxclass = self.getnextentry()
            if nxclass == 'SDS':
                children[name] = self._readdata(name,path)
            else:
                #print "open for reading",nxclass,name
                self.opengroup(name,nxclass)
                children[name] = self._readgroup()
                self.closegroup()
        return children

    def _readgroup(self):
        """
        Read the currently open group and all subgroups.
        """
        # TODO: does it make sense to read without recursing?
        # TODO: can we specify which NXclasses we are interested
        # in and skip those of different classes?
        n,path,nxclass = self.getgroupinfo()
        name = path.split("/")[-1]
        #print "reading group",path,name
        attr = self._readattrs()
        if 'target' in attr and attr['target'].value != path:
            # This is a linked group; don't try to load it.
            #print "read group link %s->%s"%(attr['target'].value,path)
            group = Link(name,attr=attr)
        else:
            children = self._readchildren(n,path)
            # If we are subclassed with a handler for the particular
            # NXentry class name use that constructor for the group
            # rather than the generic Group class.
            if hasattr(self,nxclass):
                factory = getattr(self,nxclass)
            else:
                factory = self.Group
            group = factory(nxclass,name,attr=attr,dict=children)
        return group

    def NXroot(self,*args,**kw): return NXroot(*args,**kw)
    def Group(self,*args,**kw): return Group(*args,**kw)

    def _writeattrs(self,attr):
        """
        Return the attributes for the currently open group/data or for
        the file if no group or data object is open.
        """
        for name,pair in attr.iteritems():
            #print "write attr",name,pair.nxtype,pair.value
            self.putattr(name,pair.value,pair.nxtype)

    def _writedata(self, data, path):
        """
        Write the given data node.
        
        Links cannot be written until the linked group is created, so
        this routine returns the set of links that need to be written.
        Call writelinks on the list.
        """
        
        path = path + "/" + data.nxname
        #print 'write data',path

        # If the data is linked then 
        if hasattr(data,'_link_target'):
            return [(path, data._link_target)]

        # Finally some data, but don't read it if it is big
        # Instead record the location, type and size
        #print "creating data",child.nxname,child.nxdims,child.nxtype
        if N.prod(data.nxdims) > 10000:
            # Compress the fastest moving dimension of large datasets
            slab_dims = N.ones(len(data.nxdims),'i')
            slab_dims[-1] = data.nxdims[-1]
            self.compmakedata(data.nxname, data.nxtype, data.nxdims, 
                              'lzw', slab_dims)
        else:
            # Don't use compression for small datasets
            self.makedata(data.nxname, data.nxtype, data.nxdims)
        self.opendata(data.nxname)
        self._writeattrs(data.nxattr)
        value = data.read()
        if value is not None: self.putdata(value)
        self.closedata()
        return []

    def _writegroup(self, group, path):
        """
        Write the given group structure, including the data.
        
        Links cannot be written until the linked group is created, so
        this routine returns the set of links that need to be written.
        Call writelinks on the list.
        """
        path = path + "/" + group.nxname
        #print 'write group',path

        links = []
        self.makegroup(group.nxname, group.nxclass)
        self.opengroup(group.nxname, group.nxclass)
        self._writeattrs(group.nxattr)
        if hasattr(group, '_link_target'):
            links += [(path, group._link_target)]
        for child in group.nxdict.itervalues():
            if child.nxclass == 'SDS':
                links += self._writedata(child,path)
            elif hasattr(child,'_link_target'):
                links += [(path+"/"+child.nxname,child._link_target)]
            else:
                links += self._writegroup(child,path)
        self.closegroup()
        return links

    def _writelinks(self, links):
        """
        Create links within the NeXus file as indicated by the set of pairs
        returned by writegroup.
        """
        gid = {}
        
        # identify targets
        for path,target in links:
            gid[target] = None
            
        # find gids for targets
        for target in gid.iterkeys():
            #sprint "target",target
            self.openpath(target)
            # Can't tell from the name if we are linking to a group or
            # to a dataset, so cheat and rely on getdataID to signal
            # an error if we are not within a group.
            try:
                gid[target] = self.getdataID()
            except RuntimeError:
                gid[target] = self.getgroupID()

        # link sources to targets
        for path,target in links:
            if path != target:
                # ignore self-links
                parent = "/".join(path.split("/")[:-1])
                #print "link %s -> %s"%(parent,target)
                self.openpath(parent)
                self.makelink(gid[target])
        
            


def read(filename):
    file = NeXus(filename,'r')
    tree = file.read()
    file.close()
    return tree

class Attr(object):
    """
    Attributes need to keep track of nxtype as well as attribute value.
    """
    def __init__(self,value=None,nxtype='char'):
        self.value,self.nxtype = value,nxtype

class Node(object):
    """
    Abstract base class for elements in nexus files.
    The individual objects may be either SDS data objects or groups.
    """
    nxclass = "unknown"
    nxname = "unknown"
    nxattr = None
    nxdict = None

    def __str__(self):
        return "%s:%s"%(self.nxclass,self.nxname)
    
    def readattr(self, name, default=None):
        return self.nxattr[name].value if name in self.nxattr else default

    def __getattr__(self, key):
        """
        Shimmer the various pieces of information in the nexus class and
        present them in a common namespace.
        
        if the key is in the attribute list, return the attribute value
        if the key is the name of a group element (which must be unique)
           return the group element
        if the key matches the class of a group element (and if only one
           group element matches) return that element

        e.g., for a single entry file, the following indicates the type
        of measurement in that file:
        
           root.NXentry.NXinstrument.definition.value

        private fields are tagged with a leading _
        public fields are tagged with nx (e.g., nxclass)

        TODO: It's not clear that this is a good idea.
        
        1. name collision: there may be attributes of and fields of the
        same class which have the same name, particularly if the instution
        has added private names to the nexus file.
        2. name collision: there may be multiple entries in a group with
        the same class name; this can lead to runtime errors when e.g., an
        institution decides to store all four polarization cross sections
        as different entries in the same file.
        3. name collision: private fields added by a subclass may conflict
        with names in nexus file
        4. name collision: method names are in the same namespace.
        
        However improve readability significantly over the alternative:
        
            root.findclass("NXentry")[0].findclass("NXinstrument")[0].nxdict['definition'].value
        
        Another issue to consider is supplying default values for missing
        information, e.g., if there is no slit 4, set slit 4 to infinitely open.
        This is done in dict using: s.get('name',default), but we may want to 
        do this on a multilevel namespace.  Here is a not-so-good example:
             s.get('NXinstrument.monochromator.wavelength_error',0.01)

        Consider using fixed attributes for the different namespaces, NX for
        classes, F for fields, and A for attributes:
            root.NX.entry.NX.instrument.F.definition.value
        Consider using a naming convention in which all real attributes have
        lowercase names and 
            root.NXentry.NXinstrument.Fdefinition
        """
        if key in self.nxattr:
            return self.nxattr[key].value
        elif key in self.nxdict:
            return self.nxdict[key]
        else:
            match = self.findclass(key)
            if len(match) == 1: 
                return match[0]
            else:
                raise AttributeError, \
                    "%s:%s does not have %s"%(self.nxclass,self.nxname,key)

    def findclass(self,nxclass):
        """
        Return the set of subclasses that have a particular classname.
        
        E.g., root.match("NXentry") returns the set of entries
        """
        return [entry
                for entry in self.nxdict.itervalues()
                if entry.nxclass == nxclass]
        
    def search(self,pattern):
        """
        Pattern = class:name@attr
        """
        if self.nxattr is not None:
            for k,v in self.nxattr.iteritems():
                pass
        for k,v in self.nxdict.iteritems():
            pass

    def print_name(self,indent=0):
        print " "*indent+self.nxname,':',self.nxclass

    def print_value(self,indent=0):
        pass

    def print_attr(self,indent=0):
        if self.nxattr is not None:
            #print " "*indent, "Attributes:"
            names = self.nxattr.keys()
            names.sort()
            for k in names:
                print " "*indent+k,":",self.nxattr[k].value
                
    def print_tree(self,indent=0,attr=False):
        # Print node
        self.print_name(indent=indent)
        if attr: self.print_attr(indent=indent+2)
        self.print_value(indent=indent+2)
        # Print children
        names = self.nxdict.keys()
        names.sort()
        for k in names:
            self.nxdict[k].print_tree(indent=indent+2,attr=attr)

class Data(Node):
    """
    NeXus data node.
    Operations are querying type and dimensions, reading the entire
    data block or reading a single slab.
    The NeXus file class keeps track of where the file cursor is
    pointing at any given time, opening and closing groups as necessary
    to get to the right place.
    Note that this class does not cache a copy of the data.
    """
    def __init__(self,name,dtype='',shape=[],file=None,path=None,
                 attr=None,value=None):
        self._file = file
        self._path = path
        self.nxclass = "SDS" # Scientific Data Set
        self.nxname = name
        self.nxtype = dtype
        self.nxdims = shape
        self.nxdict = {}
        self.nxattr = {} if attr is None else attr
        self.value = value

    def __str__(self):
        if self.value is not None:
            # If the value is already loaded we can maybe do
            # better than just printing the array dimensions.
            if self.nxtype == 'char':
                return self.value
            elif len(self.nxdims) == 1 and self.nxdims[0]==1:
                return str(self.value)
            elif N.prod(self.nxdims) < 8:
                return str(self.value)
        return ""

    def print_value(self,indent=0):
        v = str(self)
        if v != "":
            print '\n'.join([(" "*indent)+s for s in v.split('\n')])

    def print_name(self,indent=0):
        dims = 'x'.join([str(n) for n in self.nxdims])
        print " "*indent + "%s : Data(%s %s)"%(self.nxname, self.nxtype,dims)

    def slab(self,slice):
        slab = self._file.readslab(self,slice)
        return slab

    def read(self):
        """
        Possibly delayed read of data.
        """
        if self.value is not None:
            return self.value
        self.value = self._file.readpath(self._path)
        return self.value

class Link(Node):
    def __init__(self,name,attr=None):
        self.nxdict = {}
        self.nxclass = '_link'
        self.nxname = name
        self.nxattr = {} if attr is None else attr
        self._link_target = self.nxattr['target'].value
    def __str__(self):
        return "Link(%s)"%(self._link_target)

class Group(Node):
    """
    NeXus group node.  Group nodes have no data associated with them,
    but they do have attributes and children.
    """
    def __init__(self,nxclass,name,attr=None,dict={}):
        self.nxdict = dict
        self.nxclass = nxclass
        self.nxname = name
        self.nxattr = {} if attr is None else attr
    def print_value(self,indent=0):
        pass

class NXroot(Group):
    def datasets(self): return self.findclass("NXentry")

def copyfile(fromfile,tofile):
    """
    Copy the complete structure from one named NeXus file to another.
    
    Not terribly useful of course since the operating system has a
    copy command which does the same thing, but it does provide a
    complete demonstration of the read/write capabilities of the library.
    """
    forest = read(fromfile)
    file = NeXus(tofile,'w5')
    file.write(forest)

def listfile(file):
    """
    Read and summarize the named nexus file.
    """
    tree = read(file)
    tree.print_tree(attr=True)

def cmdline(argv):
    """
    Process command line commands in argv.  argv should contain
    program name, command, arguments, where command is one of
    the following:
        copy fromfile.nxs tofile.nxs
        ls f1.nxs f2.nxs ...
    """
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
