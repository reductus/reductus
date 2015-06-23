"""
Alternative import for h5py that allows "natural names" access to fields and attributes.

Groups and datasets are accessed using group.Fname, where name is the name of the 
field in the h5py Group object.

Attributes are accessed using group.Aname or dataset.Aname, where name is the name
of the attribute in the Group or Dataset object.

After importing h5natural, ll files opened with h5py will have the additional 
attributes.
"""

# Make all top level h5py objects available
from h5py import *
import new

# Define method calls for __dir__ and __getattr__
# group objects are different from dataset objects
def __dir__(self):
    attrs = ['A'+str(s) for s in self.attrs.keys()] if hasattr(self,'attrs') else []
    fields = ['F'+str(s) for s in self.keys()] if hasattr(self,'keys') else []
    return attrs + fields + dir(self.__class__)

def __getattr__(self, key):
    if key[0]=='A': 
        return self.attrs[key[1:]]
    elif key[0]=='F':
        return self[key[1:]]
    else:
        raise AttributeError('%r object has not attribute %r'
                             %(self.__class__.__name__,key))

Group.__dir__ = new.instancemethod(__dir__, None, Group)
Group.__getattr__ = new.instancemethod(__getattr__, None, Group)
Dataset.__dir__ = new.instancemethod(__dir__, None, Dataset)
Dataset.__getattr__ = new.instancemethod(__getattr__, None, Dataset)

# clean up namespace
del new, __dir__, __getattr__

