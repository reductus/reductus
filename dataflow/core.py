"""
Core class definitions
"""
import sys
from collections import deque
import inspect
import json
import re
import types

from numpy import NaN, inf

from .deps import processing_order

TEMPLATE_VERSION = '1.0'

_instrument_registry = []
_module_registry = {}
_datatype_registry = {}
def register_instrument(instrument):
    """
    Add a new instrument to the server.
    """
    _instrument_registry.append(instrument.id)
    for m in instrument.modules:
        register_module(m)
    for d in instrument.datatypes:
        register_datatype(d)


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
    if (datatype.id in _datatype_registry and
                datatype != _datatype_registry[datatype.id]):
        raise TypeError("Datatype already registered")
    _datatype_registry[datatype.id] = datatype


def lookup_datatype(id):
    return _datatype_registry[id]


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
    def __init__(self, id, version, name, description, icon=None,
                 inputs=None, outputs=None, fields=None, action=None,
                 author="", action_id="",
                 ):
        self.id = id
        self.version = version
        self.name = name
        self.description = description
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
        try:
            self._terminal_by_id
        except AttributeError:
            self._terminal_by_id = dict((t['id'], t)
                                        for t in self.inputs+self.outputs)
        return self._terminal_by_id[id]
        
    def get_source_code(self):
        """
        Retrieves the source code for the identified module that
        does the actual calculation.  If no module is identified
        it returns an empty string
        """
        try:
            self._source
        except AttributeError:
            self._source = "".join(inspect.getsourcelines(self.action)[0])
        return self._source

    def get_definition(self):
        return self.__getstate__()

    def __getstate__(self):
        # Don't pickle the function reference
        keys = ['version', 'id', 'name', 'description', 'icon',
                'fields', 'inputs', 'outputs', 'action_id']
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
                 instrument="", version=TEMPLATE_VERSION):
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
    def __init__(self, id, name=None, menu=None, templates=None,
                 datatypes=None, requires=None, archive=None, loaders=None):
        self.id = id
        self.name = name
        self.menu = menu
        self.templates = templates if templates is not None else []
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
            raise TypeError("unused types: %s" % ", ".join(defined - used))

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
        definition['templates'] = [t.get_definition() for t in self.templates]
        return definition

        
class DataType(object):
    """
    Data objects represent the information flowing over a wire.

    *id* : string
        Name of the data type.

    *cls* : Classs
        Python class defining the data type.
    """
    def __init__(self, id, cls):
        self.id = id
        self.cls = cls

    def get_definition(self):
        return {"id": self.id}

        
class Bundle(object):
    def __init__(self, datatype, values):
        self.datatype = datatype
        self.values = values

    def todict(self):
        values = [v.__getstate__() for v in self.values]
        return { 'datatype': self.datatype.id, 'values': values }

    @staticmethod
    def fromdict(state):
        datatype = lookup_datatype(state['datatype'])
        values = []
        for value in state['values']:
            obj = datatype.cls()
            obj.__setstate__(state)
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
    if type(obj) is types.DictionaryType:
        output = {}
        for k,v in obj.items():
            output[k] = sanitizeForJSON(v)
        return output
    elif type(obj) is types.ListType:
        return map(sanitizeForJSON, obj)
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
    if type(obj) is types.DictionaryType:
        output = {}
        for k,v in obj.items():
            output[k] = sanitizeFromJSON(v)
        return output
    elif type(obj) is types.ListType:
        return map(sanitizeFromJSON, obj)
    elif obj == _INF_STRING:
        return inf
    elif obj == _MINUS_INF_STRING:
        return -inf
    elif obj == _NAN_STRING:
        return NaN
    else:
        return obj


def make_template(name, description, diagram, instrument, version):
    """
    Convert a diagram into a template.

    A diagram is a list of action steps with configuration for each action
    and links between the steps.  Each step is indicated by a
    (string, dictionary) pair, with the string giving the action and
    the dictionary giving the configuration value for each field and
    input terminal in the action.  Links are given as 'source.terminal',
    where source is '-' to link to the action in the previous step.
    Source can also be the name of an action.  In cases where the action
    is duplicated (e.g., join), use "action => source" instead to give
    the source a unique name.  Use ',' to separate sources for multiple
    inputs sources for the same terminal.

    For example::

        diagram = [
            ["ncnr_load", {}],
            ["mark_intent", {"data": "-.output", "intent": "auto"}],
            ["group_by_intent => split", {"data": "-.output"}],

            ["join => spec", {"data": "split.specular"}],
            ["join => backp",  {"data": "split.backp"},],
            ["join => backm",  {"data": "split.backm"}],
            ["join => slit",  {"data": "split.slit", "tolerance": 0.0001}],

            ["subtract_background", {
                "data": "spec.output",
                "backp": "backp.output",
                "backm": "backm.output"}],
            ["divide_intensity",  {"data": "-.output", "base": "slit.output"}],
        ]

    Note that spacing is optional in action and source values.

    The diagram is a directed acyclic graph, and so forward references aren't
    required and aren't accepted.  Ambiguous references aren't identified, and
    if you refer to an action, the most recent action will be used as the
    source, not the first action.
    """
    def err(s):
        return "%s in step %d: [%r, %r]"%(s, target_index, action, config)
    def target_err(s):
        return "%s in step %d: [%r, %r]" %(
            s, target_index, action, {target_terminal:source_string})

    module_handles = []
    modules = []
    wires = []
    refs = {}
    for target_index, (action, config) in enumerate(diagram):

        # Split "name => ref" into "name", "ref"
        parts = [w.strip() for w in action.split('=>')]
        if len(parts) == 1:
            module_name = parts[0]
            refs[module_name] = target_index
        elif len(parts) == 2:
            module_name, ref = parts
            if ref in refs:
                raise ValueError(err("redefining source reference"))
            refs[ref] = target_index
        else:
            raise ValueError(err("too many source references"))

        try:
            module = instrument.get_module_by_id(module_name)
        except KeyError:
            raise ValueError(err("action not defined for %s"%instrument.id))
        module_handles.append(module)

        # Check that we are not setting config info for the output terminals.
        for target in module.outputs:
            target_terminal = target["id"]
            if target_terminal in config:
                raise ValueError("link should not be set on output terminal %r"
                                 %target_terminal)

        # Scan through the input terminals, and for each input terminal
        # convert the config information for that terminal into a wire.
        config = config.copy()
        for target in module.inputs:
            # retrieve the target terminal, and its configuration
            target_terminal = target["id"]
            config_value = config.pop(target_terminal, None)

            # check if it is required
            if config_value is None:
                if target["required"]:
                    raise ValueError(target_err("input terminal requires link"))
                continue

            # check for multiple links
            parts = [w.strip() for w in config_value.split(',')]
            if len(parts) > 1 and not target["multiple"]:
                raise ValueError(target_err("only one input allowed"))

            # for each given link
            for p in parts:
                # make sure it is source.terminal
                try:
                    source_id, source_terminal = p.split('.')
                except:
                    expected = {target_terminal: 'source.terminal'}
                    raise ValueError(target_err("expected %r"%(expected,)))

                # interpret source
                if source_id == '-':
                    if target_index == 0:
                        raise ValueError(target_err("no prior step"))
                    source_index = target_index-1
                elif source_id in refs:
                    source_index = refs[source_id]
                else:
                    raise ValueError(target_err("source does not exist"))

                # retrieve source terminal info
                source_module = module_handles[source_index]
                try:
                    source = source_module.get_terminal_by_id(source_terminal)
                except KeyError:
                    raise ValueError(target_err("terminal %r does not exist"
                                                % source_terminal))

                # make sure that source is an output terminal of the correct
                # data type
                if source not in source_module.outputs:
                    raise ValueError(target_err("terminal %r is not an output terminal"
                                                % source_terminal))
                if target["datatype"] != source["datatype"]:
                    raise ValueError(target_err("data types don't match"))

                # all is good; create a wire and add it to the list of wires
                wires.append({"source": [source_index, source_terminal],
                              "target": [target_index, target_terminal]})

        # TODO: validate field inputs in template, or at least check the type
        # check that the remaining config info refers to fields in the
        # module
        fields = set(p["id"] for p in module.fields)
        for k,v in config.items():
            if k not in fields:
                raise ValueError(err("unknown config field %r"%k))

        # Add the module to the list of modules in the template
        modules.append({"module": module.id,
                        "version": module.version,
                        "config": config})

    return Template(name=name, description=description, version=version,
                    modules=modules, wires=wires, instrument=instrument.id)


def make_modules(actions, prefix=""):
    """
    Convert a list of action functions into modules using auto_module.

    All ids are prefixed with prefix.
    """
    modules = []
    for action in actions:
        # Read the module defintion from the docstring
        module_description = auto_module(action)

        # Tag module ids with prefix
        module_description['id'] = prefix + module_description['id']

        # Tag each terminal data type with the data type prefix, if it is
        # not already a fully qualified name
        for v in module_description['inputs'] + module_description['outputs']:
            if '.' not in v['datatype']:
                v['datatype'] = prefix + v['datatype']

        #action = outputs_wrapper(module_description, action)
        # Define and register the module
        module = Module(action=action, **module_description)
        modules.append(module)

        #from pprint import pprint
        #pprint(module_description)

    return modules



def auto_module(action):
    """
    Given an action function, parse the docstring and return a node.

    The action name and docstring are highly stylized.

    The description is first.  It can span multiple lines.

    The parameter sections are ``**Inputs**`` and ``**Returns**``.
    These must occur on a line by themselves, with the ``**...**`` markup
    to make them show up bold in the sphinx docs.  The Inputs are split
    into input terminals and input fields depending on whether a default
    value is given in the function definition (see example below).

    Each parameter has name, type, description and optional default value.
    The name is the first on the line, followed by the type in
    (parentheses), then ':' and a description string. The parameter
    definition can span multiple lines, but the description will be
    joined to a single line.  The default value for the parameter is taken
    from the keyword argument list.  If for some reason this doesn't work,
    then add [default] in square brackets after the description, and it
    will override the keyword value.

    If the input is optional, then mark the input type with '?'.  If the node
    accepts zero or more inputs, then mark the type with '*'.  If the node
    accepts one or more inputs, then mark the type with '+'.  These flags
    set the *required* and *multiple* properties of the terminal/field.

    The possible types are determined by the user interface.  Here is the
    currently suggested types:

        str, int, bool, float, float:units, float[n]:units, opt1|opt2|...|optn

    Each instrument will have its own data types as well, which are
    associated with the wires and have enough information that they can
    be plotted.

    The resulting doc string should look okay in sphinx. For example,

    ``
        def rescale(data, scale=1.0, dscale=0.0):
            \"""
            Rescale the count rate by some scale and uncertainty.

            **Inputs**

            data (refldata) : data to scale

            scale (float:) : amount to scale

            dscale (float:) : scale uncertainty for gaussian error propagation

            **Returns**

            output (refldata) : scaled data

            2015-12-17 Paul Kienzle
            \"""
    ``

    The 'float:' type indicates that it is a floating point value with no
    units, as opposed to a floating point value for which we haven't thought
    about the units that are needed.
    """
    return _parse_function(action)


timestamp = re.compile(r"^(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})\s+(?P<author>.*?)\s*$")
def _parse_function(action):
    # Grab the docstring from the function
    # Note: inspect.getdoc() cleans the docstring, removing the indentation and
    # the leading and trailing carriage returns
    lines = inspect.getdoc(action).split('\n')

    # Default values for docstring portions
    description_lines = []
    input_lines = []
    output_lines = []
    version, author = "", ""

    # Split docstring into sections
    state = 0 # processing description
    for line in lines:
        match = timestamp.match(line)
        stripped = line.strip()
        if match is not None:
            state = 3
            version = match.group('date')
            author = match.group('author')
        elif stripped == "**Inputs**":
            state = 1
        elif line.strip() == "**Returns**":
            state = 2
        elif state == 0:
            description_lines.append(line)
        elif state == 1:
            input_lines.append(line)
        elif state == 2:
            output_lines.append(line)
        elif state == 3:
            raise ValueError("docstring continues after time stamp")
        else:
            raise RuntimeError("Unknown state %s"%state)

    # parse the sections
    description = "".join(description_lines).strip()
    inputs = _parse_parameters(input_lines)
    output_terminals = _parse_parameters(output_lines)

    # grab arguments and defaults from the function definition
    argspec = inspect.getargspec(action)
    args = argspec.args if not inspect.ismethod(action) else argspec.args[1:]
    defaults = (dict(zip(args[-len(argspec.defaults):], argspec.defaults))
                if argspec.defaults else {})
    if argspec.varargs is not None or argspec.keywords is not None:
        raise ValueError("function contains *args or **kwargs")

    # Check that all defined arguments are described
    defined = set(args)
    described = set(p['id'] for p in inputs)
    if defined-described:
        raise ValueError("Parameters defined but not described: "
                         + ",".join(sorted(defined-described)))
    if described-defined:
        raise ValueError("Parameters described but not defined: "
                         + ",".join(sorted(described-defined)))

    # Make sure there are no duplicates
    all_described = set(p['id'] for p in inputs+output_terminals)
    if len(all_described) != len(inputs)+len(output_terminals):
        raise ValueError("Parameter and return value names must be unique")

    # Split parameters into terminals (non-keyword) and fields (keyword)
    field_names = args[-len(defaults):] if defaults else []
    field_set = set(field_names)
    input_terminals = [p for p in inputs if p['id'] not in field_set]
    input_fields = [p for p in inputs if p['id'] in field_set]

    # Set the defaults for the fields from the keyword arguments
    for p in input_fields:
        if p['default'] is None:
            p['default'] = str(defaults[p['id']])

    # Collect all the node info
    result = {
        'id': action.__name__,
        'name': _unsplit_name(action.__name__),
        'description': description,
        'inputs': input_terminals,
        'outputs': output_terminals,
        'fields': input_fields,
        'version': version,
        'author': author,
        'action_id': action.__module__ + "." + action.__name__
        }

    return result


def _unsplit_name(name):
    """
    Convert "this_name" into "This Name".
    """
    return " ".join(s.capitalize() for s in name.split('_'))


# name (optional type): description [optional default]
parameter_re = re.compile("""\A
    \s*(?P<id>\w+)                           # name
    \s*([(]\s*(?P<datatype>[^)]*)\s*[)])?    # ( datatype )
    \s*:                                     # :
    \s*(?P<description>.*?)                  # non-greedy description
    \s*([[]\s*(?P<default>.*?)\s*[]])?       # [ default ]
    \s*\Z""", re.VERBOSE)
def _parse_parameters(lines):
    """
    Interpret the doc strings for the parameters.

    Each parameter must use the form defined by parameter_re above:

        name (optional type): description [optional default]

    *lines* is the set of lines after ``**Inputs**`` and ``**Returns**``.
    Note that parameters are defined by consecutive non-blank lines separated
    by blank lines.  :func:`_group_parameters` is used to gather all of the
    relevant lines together, skipping the blank bits.
    """
    ret = []
    for group in _get_paragraphs(lines):
        s = " ".join(s.strip() for s in group)
        match = parameter_re.match(s)
        if match is None:
            raise ValueError("unable to parse parameter:\n  "+"  ".join(group))
        d = match.groupdict()
        d['required'] = False
        d['multiple'] = False
        if d['datatype'].endswith('?'):
            d['datatype'] = d['datatype'][:-1]
            d['required'] = True
        elif d['datatype'].endswith('*'):
            d['datatype'] = d['datatype'][:-1]
            d['multiple'] = True
        elif d['datatype'].endswith('+'):
            d['datatype'] = d['datatype'][:-1]
            d['required'] = True
            d['multiple'] = True
        d['label'] = _unsplit_name(d['id'])
        ret.append(d)
    return ret


def _get_paragraphs(lines):
    """
    Yield a list of paragraphs defined as lines separated by blank lines.

    Each paragraph is returned as a list of lines.
    """
    group = []
    for line in lines:
        if line.strip() == "":
            if group:
                yield group
            group = []
        else:
            group.append(line)
    if group:
        yield group
