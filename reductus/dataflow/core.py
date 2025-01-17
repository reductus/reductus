"""
Core class definitions
"""
from __future__ import print_function

from dataclasses import dataclass
import sys
import importlib
import inspect
import json
from collections import OrderedDict
from importlib import resources

from numpy import nan, inf

from .deps import processing_order

TEMPLATE_VERSION = '1.0'

_instrument_registry = OrderedDict()
_module_registry = {}
_datatype_registry = {}

_loaded_instruments = set() # previously loaded instruments
def load_instrument(name):
    """
    Load the dataflow instrument definition given by the instrument *name*.

    This is a convenience function that relies on a standard layout for
    the instrument definition.  It assumes there is a reduction package
    called *name+"red"* on the python path which contains the module
    *dataflow.py*.  The module should contain the symbol *INSTRUMENT*
    giving the instrument id (for example, "ncnr.refl") and the
    function *define_instrument()* to register the instrument if *INSTRUMENT*
    is not already registered.

    The *{name}red.dataflow.define_instrument()* method should define
    the :class:`Module` reduction steps, the :class:`DataType` items
    to pass information between them and an :class:`Instrument` object
    to pull them together.  It should call :func:`register_instrument`
    on the resulting instrument object.

    Unfortunately, the instrument definition module cannot be directly
    determined from a stored template. Each step in the template does
    define *"module": id* where *id* is a dotted name such as
    *"ncnr.refl.subtract_background"*. By convention the second element
    corresponds to the input *name* for this function.

    Note: You can call *load_instrument(name)* repeatedly with the same
    name, but you can't call it if you have called *define_instrument()*
    directly.  Attempting to do so will raise a ValueError stating that
    the instrument is already defined.

    TODO: Include instrument definition module name in the saved template.
    """
    module_name = f'reductus.{name}red.dataflow'
    if module_name not in _loaded_instruments:
        module = importlib.import_module(module_name)
        _loaded_instruments.add(module_name)
        # Note: need to check for INSTRUMENT even though we've already
        # checked for module_name because the module may have been loaded
        # the traditional way using something like:
        #     import myinstred; myinstred.define_instrument()
        if module.INSTRUMENT not in _instrument_registry:
            module.define_instrument()
        else:
            raise ValueError("Instrument {module.INSTRUMENT} already defined.".format(module=module))

def register_instrument(instrument):
    """
    Add a new instrument to the server.
    """
    _instrument_registry[instrument.id] = instrument
    for m in instrument.modules:
        register_module(m)
    for d in instrument.datatypes:
        register_datatype(d)


def lookup_instrument(id):
    """
    Find a predfined instrument given its id.
    """
    return _instrument_registry[id]


def list_instruments():
    """
    Return a list of available instruments.
    """
    return list(_instrument_registry.keys())


def register_module(module):
    """
    Register a new calculation module.
    """
    if module.id in _module_registry and module != _module_registry[module.id]:
        #raise TypeError("Module already registered")
        return
    _module_registry[module.id] = module


def lookup_module(id):
    """
    Lookup a module in the registry.
    """
    return _module_registry[id]


def register_datatype(datatype):
    if (datatype.id in _datatype_registry
            and datatype != _datatype_registry[datatype.id]):
        raise TypeError("Datatype already registered", datatype, _datatype_registry[datatype.id])
    _datatype_registry[datatype.id] = datatype


def lookup_datatype(id):
    return _datatype_registry[id]


def load_templates(package):
    """
    Returns a dictionary {name: template} for the given instrument.

    Templates are defined as JSON objects, with stored in a file named
    "<instrument>.<name>.json".  All templates for an instrument should
    be stored in a templates subdirectory, made into a package by inclusion
    of an empty __init__.py file.  They can then be loaded using::

        from reductus.dataflow import core as df
        from . import templates
        ...
        instrument = df.Instrument(
            ...
            templates=df.load_templates(templates),
        )
    """
    templates = {}
    templates_dir = resources.files(package)
    for item in templates_dir.iterdir():
        if item.is_file() and item.name.endswith('.json'):
            name = item.name.split('.')[-2]
            template = json.loads(templates_dir.joinpath(item.name).read_text())
            templates[name] = template
    return templates


class Module(object):
    """
    Processing module

    A computation is represented as a set of modules connected by wires.

    *id* : string
        Module identifier. By convention this will be a dotted structure
        '<instrument class>.<operation>.<qualifier>', with qualifier optional.
        For example, use "tas.load" for triple axis data and "sans.load" for
        SANS data.  For NCNR SANS data format loaders, use "sans.load.ncnr".

    *version* : string
        Version number of the code which implements the filter calculation.
        If any code in the supporting libraries changes in a way that will
        affect the calculation results, the version number should be
        incremented.  This includes bug fixes.

    *author* : string
        Author of the module

    *name* : string
        The display name of the module. This may appear in the user interface
        in addition to any pictorial representation of the module. Usually it
        is just the name of the operation. By convention, it should have
        every word capitalized, with spaces between words.

    *action* : callable
        function which performs the action

    *action_id* : string
        fully qualified name required to import the action

    *description* : string
        A tooltip shown when hovering over the icon

    *icon* : { URI: string, terminals: { *id*: [*x*,*y*,*i*,*j*] } }
        Image representing the module, or none if the module should be
        represented by name.

        The terminal locations are identified by:

            *id* : string
                name of the terminal

            *position* : [int, int]
                (x,y) location of terminal within icon

            *direction* : [int, int]
                direction of the wire as it first leaves the terminal;
                default is straight out

    *fields* : [{Parameter}, ...]
        A form defining the constants needed for the module. For
        example, an attenuator will have an attenuation scalar. Field
        names must be distinct from terminal names.

        *id* : string
            name of the variable associated with the data; this must
            correspond to a parameter name in the module action.

        *label* : string
            display name for the field.

        *type* : string
            name of the datatype associated with the data

        *default* : object
            default value if none specified in template

        *description* : string
            A tooltip shown when hovering over the field

        *required* : boolean
            true if a value is required

        *multiple* : boolean
            true if each input should get a different value when processing
            a bundle with the module.


    *inputs*, "outputs" : [{Terminal}, ...]
        List module inputs and outputs.

        *id* : string
            name of the variable associated with the data; this must
            correspond to a parameter name in the module action.

        *label* : string
            display name for the terminal.

        *type* : string
            name of the datatype associated with the data, with the
            output of one module needing to match the input of the
            next. Using a hierarchical type system, such as
            refl.data, we can attach to generic modules like scaling
            as well as specific modules like footprint correction. By
            defining the type of data that flows through the terminal
            we can highlight valid connections automatically.

        *description* : string
            A tooltip shown when hovering over the terminal; defaults
            to datatype name

        *required* : boolean
            true if an input is required; ignored on output terminals.

        *multiple* : boolean
            true if multiple inputs are accepted on input terminals,
            or if multiple outputs are produced on output terminals.
    """
    _source = None
    _terminal_by_id = None

    def __init__(self, id, version, name, description, icon=None,
                 inputs=None, outputs=None, fields=None, action=None,
                 author="", action_id="",
                ):
        self.id = id
        self.version = version
        self.name = name
        self.description = description
        self.author = author
        self.icon = icon
        self.fields = fields if fields is not None else {}
        self.inputs = inputs
        self.outputs = outputs
        self.action = action
        self.action_id = action_id

    def get_terminal_by_id(self, id):
        """
        Lookup terminal by id, and return.
        Returns None if id does not exist.
        """
        if self._terminal_by_id is None:
            self._terminal_by_id = dict((t['id'], t)
                                        for t in self.inputs+self.outputs)
        return self._terminal_by_id[id]

    def get_source_code(self):
        """
        Retrieves the source code for the identified module that
        does the actual calculation.  If no module is identified
        it returns an empty string
        """
        if self._source is None:
            self._source = "".join(inspect.getsourcelines(self.action)[0])
        return self._source

    def get_definition(self):
        return self.__getstate__()

    @property
    def cached(self):
        return not hasattr(self.action, 'cached') or self.action.cached

    @property
    def visible(self):
        return not hasattr(self.action, 'visible') or self.action.visible

    def __getstate__(self):
        # Don't pickle the function reference
        keys = ['version', 'id', 'name', 'description', 'icon',
                'fields', 'inputs', 'outputs', 'action_id', 'visible']
        return dict([(k, getattr(self, k)) for k in keys])

    def __setstate__(self, state):
        from importlib import import_module
        for k, v in state.items():
            setattr(self, k, v)
        # Restore the function reference after unpickling
        parts = self.action_id.split('.')
        mod = import_module(".".join(parts[:-1]))
        self.action = getattr(mod, parts[-1])


class Template(object):
    """
    A template captures the computational workflow as a wiring diagram.

    *name* : string
        String identifier for the template

    *description* : string
        Extended description to be displayed as help to the template user.

    *modules* : [{TemplateModule}, ...]
        Modules used in the template

        *module* : string
            module id for template node

        *version* : string
            version number of the module

        *config* : { field: value }
            initial values for the fields

        *position* : [int,int]
            location of the module on the canvas.

    *wires* : [{TemplateWire}, ...]
        Wires connecting the modules

        *source* : [int, string]
            module id in template and terminal name in module

        *target* : [int, string]
            module id in template and terminal name in module

    *instrument* : string
        Instrument to which the template applies

    *version* : string
        Template version number
    """
    def __init__(self, name=None, description=None, modules=None, wires=None,
                 instrument="", version=TEMPLATE_VERSION, **kw):
        self.name = name
        self.description = description
        self.modules = modules
        self.wires = wires
        self.instrument = instrument
        self.version = version

    def order(self, target=None):
        """
        Return the module ids in processing order.
        """
        if target is None:
            # Order to evaluate all nodes
            pairs = [(w['source'][0], w['target'][0]) for w in self.wires]
            n = len(self.modules)
        else:
            pairs = []
            n = 0
            remaining = set([target])
            processed = set()
            while remaining:
                target = remaining.pop()
                sources = [w['source'][0] for w in self.inputs(target)]
                pairs.extend((source, target) for source in sources)
                processed.add(target)
                remaining |= set(sources) - processed
            if not pairs:  # No dependencies; calculate node only
                return [target]
        return processing_order(pairs, n)

    def dependents(self, id):
        """
        Retrieve the list of nodes that depend on a particular node, including
        the node itself.

        Note: Algorithm is O(n^2) or worse, so be prepared to rewrite if
        performance is an issue.
        """
        #print "wires", [(w['source'][0], w['target'][0]) for w in self.wires]
        remaining = set([id])
        processed = set([id])
        while remaining:
            # pick an unprocessed node
            parent = remaining.pop()
            # find which nodes depend on it
            children = set(w['target'][0] for w in self.wires
                           if w['source'][0] == parent)
            # remember to process those that are not already listed
            remaining |= children - processed
            # list the new nodes as descendents
            processed |= children
            #print "deps",id,parent,children,remaining,processed
        return processed

    def inputs(self, id):
        """
        Retrieve the data objects that go into the inputs of a module
        """
        wires = [w for w in self.wires if w['target'][0] == id]
        return wires

    def ordered(self, target=None):
        """
        Yields (module, inputs) for each module in evaluation order.

        If *target* is specified, only include modules required to
        evaluate the target.
        """
        for id in self.order(target):
            yield id, self.inputs(id)

    def dumps(self, **kw):
        """
        Convert template to json.
        """
        return json.dumps(self.__getstate__(), **kw)

    def show(self):
        """
        Print template on console as prettified json.
        """
        print(json.dumps(self.__getstate__(), indent=2, sort_keys=True,
                         separators=(',', ': ')))

    def get_definition(self):
        return self.__getstate__()

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, state):
        # As the template definition changes we need to increment the version
        # number in TEMPLATE_VERSION.  This code must be able to interpret
        # older versions of the template; it should never need to interpret
        # newer versions of the template, but should still protect against it.
        # In the initial release, clearly the the template version must
        # match TEMPLATE_VERSION since there is only one version.
        if state['version'] != TEMPLATE_VERSION:
            raise TypeError('Template definition mismatch')
        self.__dict__ = state


class Instrument(object):
    """
    An instrument is a set of modules and standard templates to be used
    for reduction

    *id* : string
        Instrument identifier. By convention this will be a dotted
        structure '<facility>.<instrument class>.<instrument>'

    *name* : string
        The display name of the instrument

    *menu* : [(string, [Module, ...]), ...]
        Modules available. Modules are organized into groups of related
        operations, such as Input, Reduce, Analyze, ...

    *datatypes* : [Datatype]
        List of datatypes used by the instrument

    *archive* : URI
        Location of the data archive for the instrument. Archives must
        implement an interface that allows data sets to be listed and
        retrieved for a particular instrument/experiment.
    """
    def __init__(self, id, name=None, menu=None, template_defs=None,
                 datatypes=None, requires=None, archive=None, loaders=None):
        self.id = id
        self.name = name
        self.menu = menu
        self.template_defs = template_defs if template_defs is not None else []
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
            used |= set(t['datatype'] for t in m.inputs+m.outputs)
        if used - defined:
            raise TypeError("undefined types: %s" % ", ".join(used - defined))
        if defined - used:
            #raise TypeError("unused types: %s" % ", ".join(defined - used))
            print("Warning: unused types: %s" % ", ".join(defined - used))

    def _check_names(self):
        names = set(m.name for m in self.modules)
        if len(names) != len(self.modules):
            raise TypeError("names must be unique within an instrument")

    def get_module_by_id(self, id):
        if '.' not in id:
            id = ".".join((self.id, id))
        for m in self.modules:
            #print "checking %r against %r"%(m.id, id)
            if m.id == id:
                return m
        else:
            raise KeyError(id + ' does not exist in instrument ' + self.name)

    def get_module_by_name(self, name):
        for m in self.modules:
            if m.name == name:
                return m
        else:
            raise KeyError(name + ' does not exist in instrument ' + self.name)

    def id_by_name(self, name):
        for m in self.modules:
            if m.name == name: return m.id
        raise KeyError(name + ' does not exist in instrument ' + self.name)

    def get_definition(self):
        keys = ['id', 'name', 'archive']
        definition = dict([(k, getattr(self, k)) for k in keys])
        definition['modules'] = [m.get_definition() for m in self.modules]
        definition['datatypes'] = [d.get_definition() for d in self.datatypes]
        definition['templates'] = self.template_defs
        return definition


@dataclass
class DataType(object):
    id: str
    cls: type
    """
    Data objects represent the information flowing over a wire.

    *id* : string
        Name of the data type.

    *cls* : Class
        Python class defining the data type.

    **Data Visualization**

    Data objects are displayed to the user, with the display format
    returned by *data.get_plottable()*.  The details of the plottable
    object are still fluid, and defined by the webreduce server.  See
    web_gui/static/js/webreduce/editor.js for the implementation.

    **Metadata**

    Information about the data object is sent to the web browser client via
    the *data.get_metadata()* method.

    **TODO**: add details about the structure and use of metadata.  It looks
    to be a simple JSON mapping of the data object which is available on
    the debug console of the browser.  Check if the webreduce client uses
    any specific fields from the object.

    **Data Export**

    Data objects define available exporters as::

        from reductus.dataflow.lib import exporters
        self.export_types = {
            "NAME" : {
                "method_name": "METHOD",
                "exporter": exporters.COMPOSITOR,
            }
        }

    where NAME is export type shown to the user, METHOD is the name of the
    data method which builds the exported object, and COMPOSITOR is
    a function that knows how to bundle entries into independent or
    concatenated export files, each with the template metadata attached.

    The export types are discovered by introspection, using a decorator
    on the entry constructor such as *@exporters.exports_HDF5("NAME")*.

    The constructor method needs to return an object of the form::

        {
            "name": "NAME",
            "entry": "ENTRY",
            "file_suffix": ".EXT",
            "value": formatted_data,
        }

    The resulting data will be saved in *NAME_ENTRY.EXT*.  For concatenated
    results the filename for the first item will be used.
    """
    def __init__(self, id, cls):
        self.id = id
        self.cls = cls
        self.export_types = self._find_exporters()

    def get_definition(self):
        return {"id": self.id, "export_types": list(self.export_types.keys())}

    def _find_exporters(self):
        exporters = {}
        for method_name in dir(self.cls):
            method = getattr(self.cls, method_name)
            if not callable(method):
                continue
            exporter = getattr(method, 'exporter', None)
            if exporter is not None:
                export_name = getattr(method, 'export_name', 'default')
                exporters[export_name] = {
                    "exporter": exporter,
                    "method_name": method_name,
                }
        return exporters

class Bundle(object):
    def __init__(self, datatype, values):
        self.datatype = datatype
        self.values = values

    def todict(self):
        values = [v.todict() for v in self.values]
        return {'datatype': self.datatype.id, 'values': values}

    def get_plottable(self):
        values = [v.get_plottable() for v in self.values]
        return {'datatype': self.datatype.id, 'values': values}

    def get_metadata(self):
        values = [v.get_metadata() for v in self.values]
        return {'datatype': self.datatype.id, 'values': values}

    def get_export(self, export_type="column", template_data=None, concatenate=True):
        if export_type not in self.datatype.export_types:
            raise ValueError("{self.datatype.id} does not provide {export_type} export.".format(self=self, export_type=export_type))
        exporter_info = self.datatype.export_types[export_type]
        exporter = exporter_info["exporter"]
        to_export = exporter(
            self.values,
            export_method=exporter_info["method_name"],
            template_data=template_data,
            concatenate=concatenate)
        return {'datatype': self.datatype.id, 'values': to_export}

    @staticmethod
    def fromdict(state):
        datatype = lookup_datatype(state['datatype'])
        values = []
        for value in state['values']:
            obj = datatype.cls()
            obj.fromdict(value)
            values.append(obj)
        return Bundle(datatype, values)


# Inf/NaN representation options:
#     javascript names: "Infinity", "-Infinity", "NaN"
#     python names: "inf", "-inf", "nan"
#     math expressions: "1/0", "-1/0", "0/0"
#     unicode symbols: u"\u221E", u"-\u221E", u"\u26A0"
#     u26A0 is WARNING SIGN (! in triangle)
#     uFFFD is REPLACEMENT CHARACTER (? in diamond)
_NAN_STRING = u"\u26A0"  # WARNING SIGN (! in triangle)
_INF_STRING = u"\u221E"  # INFINITY
_MINUS_INF_STRING = u"-\u221E"  # -INFINITY
def sanitizeForJSON(obj):
    """
    Take an object made of python objects and remove inf and nan
    """
    if isinstance(obj, dict):
        output = {}
        for k, v in obj.items():
            output[k] = sanitizeForJSON(v)
        return output
    elif isinstance(obj, list):
        return list(map(sanitizeForJSON, obj))
    elif obj == inf:
        # Use WARNING SIGN for NaN
        return _INF_STRING
    elif obj == -inf:
        return _MINUS_INF_STRING
    elif obj != obj:
        # Use WARNING SIGN for NaN
        return _NAN_STRING
    else:
        return obj


def sanitizeFromJSON(obj):
    """
    Convert inf/nan from json representation to python.
    """
    if isinstance(obj, dict):
        output = {}
        for k, v in obj.items():
            output[k] = sanitizeFromJSON(v)
        return output
    elif isinstance(obj, list):
        return map(sanitizeFromJSON, obj)
    elif obj == _INF_STRING:
        return inf
    elif obj == _MINUS_INF_STRING:
        return -inf
    elif obj == _NAN_STRING:
        return nan
    else:
        return obj

