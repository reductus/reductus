"""
Convert reduction flows to and from the stored representation.

The stored representation is given in terms of python primitives
which are suitable for calls to json loads/dumps.  The reduction
flows are represented using our internal instrument classes.  Only
the templates and the reduction flows need to be stored.


The following functions are available:

    dumps

        Convert reduction flow object to storable string.

    loads

        Convert storable string to reduction flow object.

"""
__all__ = ['dumps', 'loads']

import json

from . import core

def dumps(obj):
    if isinstance(obj, core.Template):
        classname = 'Template'
        version, state = obj.__getstate__()
    elif isinstance(obj, core.DataType):
        classname = 'DataType'
        version, state = obj.__getstate__()
    else:
        raise TypeError('unknown object "%s"' % str(type(obj)))

    return json.dumps([classname, version, state])

def loads(str):
    classname, version, state = json.loads(str)
    if classname == 'Template':
        obj = core.Template()
    elif classname == 'DataType':
        obj = core.DataType()
    else:
        raise TypeError('unknown object "%s"' % classname)
    obj.__setstate__((version, state))
    return obj

