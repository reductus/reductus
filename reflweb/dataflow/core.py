"""
Core class definitions
"""
from . import config
from .deps import processing_order

from collections import deque
import simplejson
import inspect

_registry = {}
_registry_data = {}
def register_instrument(instrument):
    """
Add a new instrument to the server.
"""
    config.INSTRUMENTS.append(instrument.id)
    for m in instrument.modules:
        register_module(m)
    for d in instrument.datatypes:
        register_datatype(d)
def register_module(module):
    """
Register a new calculation module.
"""
    if module.id in _registry and module != _registry[module.id]:
        return
        #raise TypeError("Module already registered")
    _registry[module.id] = module
    
def lookup_module(id):
    """
Lookup a module in the registry.
"""
    return _registry[id]
def register_datatype(datatype):
    if datatype.id in _registry_data and datatype != _registry_data[datatype.id]:
        raise TypeError("Datatype already registered")
    _registry_data[datatype.id] = datatype
def lookup_datatype(id):
    return _registry_data[id]

class Module(object):
    """
Processing module

A computation is represented as a set of modules connected by wires.

Attributes
----------

id : string

Module identifier. By convention this will be a dotted structure
'<operation>.<instrument class>.<instrument>', with instrument
optional for generic operations.

version : string

Version number of the code which implements the filter calculation.
If the calculation changes, the version number should be incremented.

name : string

The display name of the module. This may appear in the user interface
in addition to any pictorial representation of the module. Usually it
is just the name of the operation. By convention, it should have
every word capitalized, with spaces between words.

description : string

A tooltip shown when hovering over the icon

icon : { URI: string, terminals: { string: [x,y,i,j] } }

Image representing the module, or none if the module should be
represented by name.

The terminal locations are identified by:

id : string
name of the terminal
position : [int, int]
(x,y) location of terminal within icon

direction : [int, int]
direction of the wire as it first leaves the terminal;
default is straight out

fields : Form

An inputEx form defining the constants needed for the module. For
example, an attenuator will have an attenuation scalar. Field
names must be distinct from terminal names.

terminals : [Terminal]

List module inputs and outputs.

id : string
name of the variable associated with the data
datatype : string
name of the datatype associated with the data, with the
output of one module needing to match the input of the
next. Using a hierarchical type system, such as
data1d.refl, we can attach to generic modules like scaling
as well as specific modules like footprint correction. By
defining the type of data that flows through the terminal
we can highlight valid connections automatically.

use : string | "in|out"
whether this is an input parameter or an output parameter
description : string
A tooltip shown when hovering over the terminal; defaults
to datatype name
required : boolean
true if an input is required; ignored on output terminals.
multiple : boolean
true if multiple inputs are accepted; ignored on output
terminals.

xtype : string
name of the xtype to be used for this container.
Common ones include WireIt.Container, WireIt.ImageContainer
and the locally-defined AutosizeImageContainer (see lang_common.js)
"""
    def __init__(self, id, version, name, description, icon=None,
                 terminals=None, fields=None, action=None, xtype=None, filterModule=None):
        self.id = id
        self.version = version
        self.name = name
        self.description = description
        self.icon = icon
        self.fields = fields
        self.terminals = terminals
        self.action = action
        self.xtype = xtype
        self.filterModule = filterModule

    def get_terminal_by_id(self, id):
        """ 
Lookup terminal by id, and return.
Returns None if id does not exist.
"""
        terminal_lookup = dict((t['id'], t) for t in self.terminals)
        return terminal_lookup[id]
        
    def get_source_code(self):
        """
Retrieves the source code for the identified module that
does the actual calculation.  If no module is identified
it returns an empty string
"""
        source = ""
        if self.filterModule is not None:
            source = "".join(inspect.getsourcelines(self.filterModule)[0])
        return source        
        
class Template(object):
    """
A template captures the computational workflow as a wiring diagram.

Attributes
----------

name : string
String identifier for the template

version : string

Version number of the template

description : string
Extended description to be displayed as help to the template user.
instrument : string
Instrument to which the template applies

modules : [TemplateModule]

Modules used in the template
module : string
module id for template node

version : string

version number of the module

config : map
initial values for the fields
position : [int,int]
location of the module on the canvas.

wires : [TemplateWire]

Wires connecting the modules
source : [int, string]
module id in template and terminal name in module
target : [int, string]
module id in template and terminal name in module
"""
    def __init__(self, name, description, modules, wires, instrument,
                 version='0.0'):
        self.name = name
        self.description = description
        self.modules = modules
        self.wires = wires
        self.instrument = instrument
        self.version = version

    def order(self):
        """
Return the module ids in processing order.
"""
        pairs = [(w['source'][0], w['target'][0]) for w in self.wires]
        return processing_order(len(self.modules), pairs)

    def __iter__(self):
        """
Yields module#, inputs for each module in the template in order.
"""
        for id in self.order():
            inputs = [w for w in self.wires if w['target'][0] == id]
            yield id, inputs

    def __getstate__(self):
        """
Version aware pickler. Returns (version, state)
"""
        return '1.0', self.__dict__
    def __setstate__(self, state):
        """
Version aware unpickler. Expects (version, state)
"""
        version, state = state
        if version != '1.0':
            raise TypeError('Template definition mismatch')
        self.__dict__ = state
        
    def get_parents(self, id):
        """
Retrieve the data objects that go into the inputs of a module
"""  
        parents = [w for w in self.wires if w['target'][0] == id]
        return parents


class Instrument(object):
    """
An instrument is a set of modules and standard templates to be used
for reduction

Attributes
----------

id : string

Instrument identifier. By convention this will be a dotted
structure '<facility>.<instrument class>.<instrument>'

name : string

The display name of the instrument

menu : [(string, [Module, ...]), ...]
Modules available. Modules are organized into groups of related
operations, such as Input, Reduce, Analyze, ...

datatypes : [Datatype]
List of datatypes used by the instrument
archive : URI
Location of the data archive for the instrument. Archives must
implement an interface that allows data sets to be listed and
retrieved for a particular instrument/experiment.
"""
    def __init__(self, id, name=None, menu=None,
                 datatypes=None, requires=None, archive=None, loaders=None):
        self.id = id
        self.name = name
        self.menu = menu
        self.datatypes = datatypes
        self.requires = requires
        self.archive = archive
        self.loaders = loaders

        self.modules = []
        for _, m in menu:
            self.modules.extend(m)
        self._check_datatypes()
        self._check_names()

    def _check_datatypes(self):
        defined = set(d.id for d in self.datatypes)
        used = set()
        for m in self.modules:
            used |= set(t['datatype'] for t in m.terminals)
        if used - defined:
            raise TypeError("undefined types: %s" % ", ".join(used - defined))
        if defined - used:
            raise TypeError("unused types: %s" % ", ".join(defined - used))

    def _check_names(self):
        names = set(m.name for m in self.modules)
        if len(names) != len(self.modules):
            raise TypeError("names must be unique within an instrument")
        
    def id_by_name(self, name):
        for m in self.modules:
            if m.name == name: return m.id
        raise KeyError(name + ' does not exist in instrument ' + self.name)
        
class Data(object):
    """
Data objects represent the information flowing over a wire.

Attributes
----------

name : string
User visible identifier for the data. Usually this is file name.

datatype : string
Type of the data. This determines how the data may be plotted
and filtered.
intent : string
What role the data is intended for, such as 'background' for
data that is used for background subtraction.

dataid : string
Key to the data. The data itself can be stored and retrieved by key.

history : list

History is the set of modules used to create the data. Each module
is identified by the module id, its version number and the module
configuration used for this data set. For input terminals, the
configuration will be {string: [int,...]} identifying
the connection between nodes in the history list for each input.

module : string

version : string

inputs : { <input terminal name> : [(<hist iindex>, <output terminal>), ...] }

config : { <field name> : value, ... }
dataid : string
"""
    def __new__(subtype, id, cls, loaders=[]):
        obj = object.__new__(subtype)
        obj.id = id
        obj.cls = cls
        obj.loaders = loaders
        return obj
    
    def __getstate__(self):
        return "1.0", __dict__
    
    def __setstate__(self, state):
        version, state = state
        self.__dict__ = state
        
    def get_plottable(self):
        return simplejson.dumps({})
    
    def dumps(self):
        return ""
    
    @classmethod
    def loads(cls, str):
        return Data(str, Data)


# ============= Parent traversal =============
class Node(object):
    """
Base node

A diagram is created by connecting nodes with wires.
parents : [Node]
List of parents that this node has
params : dictionary
Somehow matches a parameter to its current value,
which will be compared to the previous value as found
in the database.
"""
    def __init__(self, parents, params):
        self.parents = parents
        self.params = params
        
    def searchDirty(self):
        queue = deque([self])
        while queue:
            node = queue.popleft()
            if node.isDirty():
                return True
            for parent in node.parents:
                queue.append(parent)
        return False
        
    def isDirty(self):
        # Use inspect or __code__ for introspection?
        return self.params != self._get_inputs()
    
    def _get_inputs(self):
        # Get data from database
        #pass
        data = {'maternal grandpa':{'id':'maternal grandpa'},
                'maternal grandma':{'id':'maternal grandma'},
                'mom':{'id':'mom'},
                'paternal grandpa':{'id':'paternal grandpa'},
                'paternal grandma':{'id':'paternal grandma'},
                'dad':{'id':'dad'},
                'son':{'id':'son'}, }
        return data.get(self.params['id'], {})
    
if __name__ == '__main__':
    head = Node([Node([Node([], {'id':'maternal grandpa'}),
                       Node([], {'id':'maternal grandma'})],
                      {'id':'mom'}),
                 Node([Node([], {'id':'paternal grandpa'}),
                       Node([], {'id':'paternal grandma'})],
                      {'id':'dad'})],
                {'id':'son'})
    print "Dirty" if head.searchDirty() else "Clean"
