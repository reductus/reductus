"""
Generate module definitions from function declarations.

:func:`make_modules` defines the modules available for the instrument given
a list of actions.  The doc strings of the actions define the interface.

:func:`make_template` defines a convenient syntax for creating templates
from a script.
"""
import sys
import inspect
import re

from numpy import inf

from .anno_exc import annotate_exception
from .core import Module, Template
from .rst2html import rst2html

IS_PY3 = sys.version_info[0] >= 3

# Decorators to tag action methods for an instrument

def cache(action):
    """
    Decorator which adds the *cached* attribute to the function.

    Use *@cache* to force caching to always occur (for example, when
    the function references remote resources, vastly reduces memory, or is
    expensive to compute.  Use *@nocache* when debugging a function
    so that it will be recomputed each time regardless of whether or not it
    is seen again.
    """
    action.cached = True
    return action

def nocache(action):
    """
    Decorator which adds the *cached* attribute to the function.

    Use *@cache* to force caching to always occur (for example, when
    the function references remote resources, vastly reduces memory, or is
    expensive to compute.  Use *@nocache* when debugging a function
    so that it will be recomputed each time regardless of whether or not it
    is seen again.
    """
    action.cached = False
    return action

def module(tag=""):
    """
    Decorator adds *group=tag* as an attribute to the function.

    This marks a method as a reduction step to be included in the list
    of reduction steps. If *tag* is set then the action will be placed in a
    submenu with that label.  If used as a bare function then defaults
    to a tag of "" for the top-level menu.

    For example, to register *action*::

        @module
        def action(data, par='default'):
            ...

    To register action in the *viz* submenu use::

        @module("viz")
        def viz_action(data):
            ...

    Actions can be retrieved from a module using :func:`get_modules`.
    """
    # Called as @module
    if callable(tag):
        tag.group = ""
        return tag

    # Called as @module("tag")
    def wrapper(fn):
        fn.group = tag
        return fn
    return wrapper

# From unutbu and Glenn Maynard
# https://stackoverflow.com/questions/13503079/how-to-create-a-copy-of-a-python-function/13503277#13503277
# https://stackoverflow.com/a/6528148/190597
def copy_func(f):
    """Make a copy of a function, including its attributes"""
    import types
    import functools
    g = types.FunctionType(f.__code__, f.__globals__, name=f.__name__,
                           argdefs=f.__defaults__,
                           closure=f.__closure__)
    g = functools.update_wrapper(g, f)
    g.__kwdefaults__ = f.__kwdefaults__
    return g

def copy_module(f, new_name, old_type, new_type, tag=None):
    """
    Copy a dataflow module replacing name with *new_name* and *old_type*
    with *new_type*.

    For example::

        from reductus.dataflow.automod import copy_module
        # Note: do not load symbols from steps directly into the file scope
        # or they will be defined twice as reduction modules.
        from reductus.reflred import steps

        candor_join = copy_module(
            steps.join, "candor_join", "refldata", "candordata", tag="candor")
    """
    g = copy_func(f)
    g.__name__ = new_name
    g.__doc__ = re.sub(
        r"\({old_type}([^a-zA-Z_)]*)\)".format(old_type=old_type),
        r"({new_type}\1)".format(new_type=new_type),
        f.__doc__)
    if tag is not None:
        g.group = tag
    return g

def get_modules(module, grouped=False, sorted=True):
    """
    Retrieve @module actions from a python module.

    If *grouped*, return modules grouped by action tag.

    If *sorted*, sort the actions by name attribute, otherwise they appear
    in the original order in the module.
    """
    actions = [
        fn for name in dir(module)
        for fn in [getattr(module, name)]
        if hasattr(fn, 'group')
    ]
    if sorted:
        actions.sort(key=lambda fn: fn.__name__)
    if grouped:
        from collections import defaultdict
        groups = defaultdict(list)
        for fn in actions:
            groups[fn.action].append(fn)
        return groups
    return actions

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
            s, target_index, action, {target_terminal:s})

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
        for k, v in config.items():
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

    If the field is optional, then mark the type with '?'.  If the node
    accepts zero or more values, then mark the type with '*'.  If the node
    accepts one or more values, then mark the type with '+'.  These flags
    set the *required* and *multiple* properties of the field.

    Datasets move through the template as bundles of files. If the input
    terminals for a node are all multiple inputs, then the action will
    be called once with the entire bundle as a list.  If the input terminals
    are all single input, then the action will be called once for each dataset
    in the bundle.  For mixed single/multiple inputs the first input must
    be single.  If the output is single, it is made into a length one bundle.
    If the output is multiple, then it is assumed to already be a bundle.
    With mixed single input/multiple output, all outputs are concatenated
    into one bundle.

    All fields should be the length of the first input, or length 1 if the
    the field value is the same across all inputs, or length 0 if the
    field is optional and not defined.

    The possible types are determined by the user interface.  They include
    items such as:

        str, int, bool, float, float:units, opt:opt1|opt2|...|optn

    See :func:`parse_datatype` for the complete list.

    Each instrument will have its own data types as well, which are
    associated with the wires and have enough information that they can
    be plotted.

    Every module should have a date stamp and author, with date as
    yyyy-mm-dd so that it sorts correctly.  A change notice can be
    included, separated from author by ':'.  If there are multiple
    updates to the module, precede each with '| ' so that line breaks
    are preserved in the formatted documentation.

    The resulting doc string should look okay in sphinx. For example,

    ::

        def rescale(data, scale=1.0, dscale=0.0):
            r\"""
            Rescale the count rate by some scale and uncertainty.

            **Inputs**

            data (refldata) : data to scale

            scale (float:) : amount to scale

            dscale (float:) : scale uncertainty for gaussian error propagation

            **Returns**

            output (refldata) : scaled data

            | 2015-12-17 Paul Kienzle: first release
            | 2016-02-04 Paul Kienzle: change parameter name
            \"""

    The 'float:' type indicates that it is a unitless floating point value
    rather than a floating point value for which we forgot to specify units.

    The 'r' preceding the docstring allows us to put backslashes in the
    documentation, which is convenient when we have latex markup in between
    dollar signs or in a \\:math\\: environment.
    """
    try:
        return _parse_function(action)
    except ValueError as exc:
        annotate_exception(" while initializing module " + action.__name__, exc)
        raise



timestamp = re.compile(r"^([|] )?(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})\s+(?P<author>.*?)\s*(:\s*(?P<change>.*?)\s*)?$")
def _parse_function(action):
    # grab arguments and defaults from the function definition
    argspec = inspect.getfullargspec(action)
    args = argspec.args if not inspect.ismethod(action) else argspec.args[1:]
    defaults = (dict(zip(args[-len(argspec.defaults):], argspec.defaults))
                if argspec.defaults else {})
    if argspec.varargs is not None or argspec.varkw is not None:
        raise ValueError("function contains *args or **kwargs")

    # Grab the docstring from the function
    # Note: inspect.getdoc() cleans the docstring, removing the indentation and
    # the leading and trailing carriage returns
    docstr = inspect.getdoc(action)

    # Default values for docstring portions
    description_lines = []
    input_lines = []
    output_lines = []
    version, author = "", ""
    changelog = []

    # Split docstring into sections
    state = 0 # processing description
    for line in docstr.split('\n'):
        match = timestamp.match(line)
        stripped = line.strip()
        if match is not None:
            state = 3
            version = match.group('date')
            author = match.group('author')
            changelog.append((version, author, match.group('change')))
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
    name = _unsplit_name(action.__name__)
    heading = "\n".join(("="*len(name), name, "="*len(name), ""))
    #description = "".join(description_lines)
    description = rst2html(heading + docstr, part="whole", math_output="mathjax")
    inputs = parse_parameters(input_lines)
    output_terminals = parse_parameters(output_lines)

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
    field_names = set(args[-len(defaults):] if defaults else [])
    input_terminals = [p for p in inputs if p['id'] not in field_names]
    input_fields = [p for p in inputs if p['id'] in field_names]

    # Set the defaults for the fields from the keyword arguments, and make
    # sure they are consistent with the datatype.
    for p in input_fields:
        if p['datatype'] not in FIELD_TYPES:
            raise ValueError("Invalid type %s for field %s"%(p['datatype'], p['id']))
        value = defaults[p['id']]
        if value is not None:
            # Note: validate may change the value to conform to the type
            value = validate(p, value, as_default=True)
        if p['multiple']:
            value = [value] if value is not None else []
        p['default'] = value

    for p in input_terminals + output_terminals:
        if p['datatype'] in FIELD_TYPES:
            raise ValueError("Invalid type %s for terminal %s"%(p['datatype'], p['id']))

    # Collect all the node info
    result = {
        'id': action.__name__,
        'name': name,
        'description': description,
        'inputs': input_terminals,
        'outputs': output_terminals,
        'fields': input_fields,
        'version': version,
        'author': author,
        #'changelog': changelog,
        'action_id': action.__module__ + "." + action.__name__
        }

    return result


def _unsplit_name(name):
    """
    Convert "this_name" into "This Name".
    """
    return " ".join(s.capitalize() for s in name.split('_'))


# parameter definition regular expression
parameter_re = re.compile(r"""\A
    \s*(?P<id>\w+)                           # name
    \s*(\{\s*(?P<label>.*?)\s*\})?           # { label }    (optional)
    \s*(\(                                   # (
        \s*(?P<datatype>.*?)                 #    datatype  (non-greedy)
        \s*(\[\s*(?P<length>[0-9]*)\s*\])?   #    [length]  (optional)
        \s*(?P<multiple>[?*+])?              #    multiple  (optional [*+?])
        \s*(:\s*(?P<typeattr>.*?))?          #    :typeattr (optional)
    \s*\))?                                  # )
    \s*:                                     # :
    \s*(?P<description>.*?)                  # description  (non-greedy)
    \s*\Z""", re.VERBOSE)
def parse_parameters(lines):
    """
    Interpret the doc strings for the parameters.

    Each parameter must use the form defined by the following syntax:

        id {label} (type[length]#:attr): description

    The *(type)* specifier is optional, defaulting to str.  The *[default]*
    value is rarely needed since it can be extracted from the function
    defintion.  Within the type specifier, the *[length]* is not required
    if only a single value is needed.  The multiplicity specifier *#* can be
    one of '?', '*', or '+' if there can be zero or one, zero or more or one
    or more values respectively.

    *lines* is the set of lines after ``**Inputs**`` and ``**Returns**``.
    Note that parameters are defined by consecutive non-blank lines separated
    by blank lines.  :func:`get_paragraphs` is used to gather all of the
    relevant lines together, skipping the blank bits.
    """
    ret = []
    for group in get_paragraphs(lines):
        s = " ".join(s.strip() for s in group)
        match = parameter_re.match(s)
        if match is None:
            raise ValueError("unable to parse parameter:\n  "+"  ".join(group))
        d = match.groupdict()
        if d['length'] is None:
            d['length'] = 1
        elif d['length'].strip() == "":
            d['length'] = 0
        else:
            try:
                d['length'] = int(d['length'])
            except ValueError:
                raise ValueError("bad length specifier:\n "+"  ".join(group))
            if d['length'] < 0:
                raise ValueError("length must positive:\n "+"  ".join(group))
        if d['multiple'] is None:
            d['required'] = True
            d['multiple'] = False
        elif d['multiple'] == '?':
            d['required'] = False
            d['multiple'] = False
        elif d['multiple'] == '*':
            d['required'] = False
            d['multiple'] = True
        elif d['multiple'] == '+':
            d['required'] = True
            d['multiple'] = True
        else:
            raise RuntimeError("Can't get here")
        if d['label'] is None:
            d['label'] = _unsplit_name(d['id'])
        parse_datatype(d)
        ret.append(d)
    return ret

def parse_datatype(par):
    r"""
    Interpret the data type into a base type and attributes.

    *str* : String input.

    *bool:label* : True/false.

        Boolean options can be represented using a check box in the user
        interface, using the given label.  If the label is not provided,
        then the name of the parameter will be used.  If *multiple=True*,
        then there should be a separate checkbox for each dataset, which
        could be added as a check menu item on the drop down associated
        with each graph line.

    *int:<min,max>* : Integer value.

        If a range is given, then the value should lie within the range.
        The type attribute is set as *typeattr={range: [min, max]}*, with
        range defaulting to *[-inf, inf]* if no range is given.  Note that
        inf is represented as 1e9 for integers.

    *float:units<min,max>* : Floating point value.

        Units should be a string, which may be the empty string if the value
        is unitless.  The type attribute is set as
        *typeattr={units: "units", range: [min, max]}*, with range defaulting
        to *[-inf, inf]* if no range is given.  Note that inf is represented
        as 1e300 for float.

    *opt:opt1|...|optn* : Choice list.

        Select from the list of options.  Options are sent as string
        values.  This could be represented as radio buttons, as a single
        selection list or as a dropdown list, depending on the number of
        options to choose from and the amount of screen real estate available.
        If *length=0* because *opt[]:...* was specified, then a multiple
        selection list should be used to return a list of strings. If
        *multiple=True*, then the options could show up on the drop down
        menu associated with each data line.

        Normally the option name matches the option label, unless the option
        is given as "...|name=label|...". If the final choice is "...", then
        the response is an open set response, with the list being the list of
        common options.  This can be implemented using a combo box, with
        users able to enter a string or choose one of the predefined options
        from the drop-down list.  The option may be missing, in which case
        a block separation should be indicated and the option never selected.

        The type attribute is set as
        *typeattr={choices: [[opt1,label1], ...], open: true/false}*

    *regex:pattern* -> *datatype=regex, pattern=pattern*

        String which must match the given regular expression.  The type
        attribute is set as *typeattr={pattern: "pattern"}*.  Note that
        matching is not anchored, so you probably want *^pattern$*.

        To check the pattern, use::

            if (RegExp(typeattr.pattern).test(inputstr)) {}  // javascript

            if re.search(typeattr["pattern"], inputstr): pass  # python

    *fileinfo* -> *datatype=fileinfo*

        A file identifier on the server with the following structure::

            {
                *path*: location on server,
                *mtime*: modification time,
                *source*: data repository (ncnr, ncnr_DOI, local...)
            }

        The user interface should present a list of files to choose from,
        and fill in the structure.

    *index* -> *datatype=index*

        This should be a zero-origin point number in the plotted data.  There
        are several use cases, but the first one is most sensible:

        - index[]\* -> *length=0, multiple=true*

            an arbitrary list of points should be selected for each
            dataset independently

        - index\* -> *length=1, multiple=true*

            a single point should be selected for each dataset independently

        - index -> *length=1, multiple=false*

            a single point should be selected for all lines simultaneously,
            and that point will be used in all datasets.

        - index[] -> *length=0, multiple=false*

            multiple points should be selected for all lines simultaneously,
            and those points will apply to all datasets.

    *range:axis* -> *datatype=range, axis=axis*

        This is a selection of a range from the graph, where *axis* is *x* or
        *y* for a range of *x* or *y* values, or *xy* for a region of the
        graph. This makes most sense with *length=1, multiple=false*.
        The type attribute is set as *typeattr={axis: "axis"}*.  The return
        value is *[min, max]* for *x* and *y*, or *[minx, maxx, miny, maxy]*
        for *xy*.

    *coordinate* -> *datatype=coordinate*

        A point *[x, y]* should be selected from the graph.
    """
    name = par['id']
    type = par["datatype"] if par["datatype"] else "str"
    attrstr = par["typeattr"] if par["typeattr"] else ""
    attr = {}

    #print "type: %r"%type
    if type == "int":
        try:
            min, max = parse_range(attrstr, limit=1e9)
            if int(min) != min or int(max) != max:
                raise Exception("use integers for int range")
        except Exception as exc:
            raise ValueError("invalid range for %s: %s"%(name, str(exc)))
        attr["range"] = [int(min), int(max)]

    elif type == "float":
        split_index = attrstr.find("<")
        if split_index >= 0:
            units, range = attrstr[:split_index], attrstr[split_index:]
        else:
            units, range = attrstr, ""
        try:
            min, max = parse_range(range, limit=1e300)
        except Exception as exc:
            raise ValueError("invalid range for %s: %s"%(name, str(exc)))

        attr["units"] = units.strip()
        attr["range"] = [min, max]

    elif type == "opt":
        if "|" not in attrstr:
            raise ValueError("options not specified for " + name)
        attrstr = attrstr.replace('\\', '')  # allow escaped backslashes for rst
        choices = [v.split('=', 2) for v in attrstr.split("|")]
        choices = [(v*2 if len(v) == 1 else v) for v in choices]
        choices = [[v[0].strip(), v[1].strip()] for v in choices]
        open = (choices[-1][0] == "...")
        if open:
            choices = choices[:-1]

        attr["choices"] = choices
        attr["open"] = open

    elif type == "regex":
        if not attrstr:
            raise ValueError("regex is empty for " + name)
        try:
            pattern = re.compile(attrstr)
        except Exception as exc:
            raise ValueError("regex error %r for %s"%(str(exc), name))
        # if the default is given, check that it matches the pattern
        default = par.get("default", None)
        if default and not pattern.search(default):
            raise ValueError("default %r does not match pattern %r for %s"
                             %(default, attrstr, name))
        attr["pattern"] = attrstr

    elif type == "range":
        if attrstr not in ("x", "y", "xy", "ellipse", "sector_centered"):
            raise ValueError("range must be one of x, y, xy, ellipse or sector_centered for " + name)
        attr["axis"] = attrstr

    elif type == "patch_metadata":
        attr["key"] = attrstr

    else: # type in ["str", "bool", "fileinfo", "index", "coordinate"]:
        if par["typeattr"] is not None:
            raise ValueError("No restrictions on type %s for parameter %s"
                             % (type, name))


    par["datatype"] = type
    par["typeattr"] = attr

FIELD_TYPES = set("str bool int float opt regex range index coordinate fileinfo scale patch_metadata".split())

def check_multiplicity(par, values, bundle_length):
    """
    Check the number of values for the parameter against bundle length,
    depending on whether the parameter is required or multiple.
    """
    name = par["name"]
    required = par["required"]
    multiple = par["multiple"]

    if required and len(values) == 0:
        raise ValueError("need a value for %s"%name)
    if not multiple and len(values) not in [0, 1, bundle_length]:
        raise ValueError("wrong number of values for %s"%name)

def validate(par, value, as_default=False):
    """
    Check the parameter value.

    If *as_default*, make sure that the value is a reasonable default.

    Returns the value, possibly converted to the correct type.

    Raise an error if the parameter value is not valid.
    """
    name = par["id"]
    n = par["length"]
    if n == 1:
        return _validate_one(par, value, as_default)
    elif not isinstance(value, (list, tuple)):
        raise ValueError("invalid value for %s, expected list"%name)
    elif n and len(value) != n:
        raise ValueError("invalid value for %s, wrong length"%name)
    else:
        return [_validate_one(par, v, as_default) for v in value]

def _validate_one(par, value, as_default):
    datatype = par["datatype"]
    name = par["id"]

    if datatype == "int":
        # accept float values instead of integers
        value = _type_check(name, value, int)
        min, max = par["typeattr"]["range"]
        if not min <= value <= max:
            raise ValueError("invalid value for %s, %s not in [%s, %s]"
                             %(name, value, min, max))
    elif datatype == "float":
        _type_check(name, value, float)
        min, max = par["typeattr"]["range"]
        if not min <= value <= max:
            raise ValueError("invalid value for %s, %s not in [%s, %s]"
                             %(name, value, min, max))
    elif datatype == "str":
        value = _type_check(name, value, str)

    elif datatype == "opt":
        value = _type_check(name, value, str)
        choices = par["typeattr"]["choices"]
        isopenset = par["typeattr"]["open"]
        # Note: choices is a list of pairs [["option", "display"], ...]
        if value not in list(zip(*choices))[0]:
            #print value, choices
            if not isopenset or as_default is True:
                raise ValueError("value %r not in choice list for %s"
                                 %(value, name))

    elif datatype == "regex":
        value = _type_check(name, value, str)
        pattern = par["typeattr"]["pattern"]
        if not re.match(pattern, value):
            raise ValueError("value %r not does not match %r for %s"
                             %(value, pattern, name))

    elif datatype == "range":
        range = par["typeattr"]["axis"]
        n = 4 if (range == "xy" or range == "ellipse") else 2
        value = _list_check(name, value, n, float)

    elif datatype == "index":
        value = _type_check(name, value, int)

    elif datatype == "coordinate":
        value = _list_check(name, value, 2, float)

    elif datatype == "bool":
        value = _type_check(name, value, bool)

    elif datatype == "fileinfo":
        value = _finfo_check(name, value)

    elif datatype == "scale":
        value = _type_check(name, value, float)

    elif datatype == "patch_metadata":
        value = _patch_check(name, value)

    else:
        raise ValueError("no %s type check for %s"%(datatype, name))

    return value

def _finfo_check(name, value):
    try:
        if (not isinstance(value, dict)
                or "path" not in value
                or "mtime" not in value
                or "source" not in value
                or (len(value) > 3 and "entries" not in value)
                or len(value) > 4):
            raise ValueError("wrong structure")
        value["path"] = _type_check(name, value["path"], str)
        value["mtime"] = _type_check(name, value["mtime"], int)
        value["source"] = _type_check(name, value["source"], str)
        if value.setdefault("entries", None) is not None:
            value["entries"] = _list_check(name, value["entries"], 0, str)

    except:
        #raise
        raise ValueError("value %r is not {source: str, path: str, mtime: int, entries: [str, ...]} for %s"
                         % (value, name))
    return value

def _patch_check(name, value):
    if (not isinstance(value, dict)
            or "op" not in value
            or "path" not in value
            or value["op"] not in ["test", "add", "replace", "copy", "move", "remove"]):
        raise ValueError("patch must be a dict, with valid op code and path")

    elif value["op"] in ["test", "add", "replace"]:
        if not "value" in value:
            raise ValueError("patch for test, add or replace must contain value field")
        else:
            value["value"] = _type_check(name, value["value"], str)

    elif value["op"] in ["copy", "move"]:
        if not "from" in value:
            raise ValueError("patch for copy or move must contain from field")
        else:
            value["from"] = _type_check(name, value["from"], str)

    value["op"] = _type_check(name, value["op"], str)
    value["path"] = _type_check(name, value["path"], str)

    return value

def _list_check(name, values, n, ptype):
    #print "list check", name, values, n, ptype
    if isinstance(values, tuple):
        values = list(values)
    _type_check(name, values, list)
    if n and len(values) != n:
        raise ValueError("expected list of length %d for %s"
                         %(n, name))
    try:
        values = [_type_check(name, v, ptype) for v in values]
    except:
        raise ValueError("all values in list must be of type %s for %s"
                         %(str(ptype), name))
    return values

def _type_check(name, value, ptype):
    if value is None:
        return value
    elif ptype is int and isinstance(value, float) and int(value) == value:
        value = int(value)
    elif ptype is float and isinstance(value, int):
        value = float(value)
    elif ptype is str and not IS_PY3 and isinstance(value, unicode):
        value = value.encode('utf-8')
    elif ptype is str and IS_PY3 and isinstance(value, bytes):
        value = value.decode('utf-8')
    if not isinstance(value, ptype):
        raise ValueError("expected %s for %s but got %s"
                         % (str(ptype), name, str(type(value))))
    return value


def parse_range(range, limit=inf):
    """
    Parse the range string *<min,max>*.

    *limit* sets the limiting value for the range, to use in place of inf or
    a missing limit.

    Returns (*min, max*), or *(-limit, limit)* if no range is provided.
    """
    range = range.strip()
    if range == "":
        return [-limit, limit]
    if not (range.startswith('<') and range.endswith('>') and "," in range):
        raise ValueError("expected <min, max>")
    minstr, maxstr = [v.strip() for v in range[1:-1].split(',', 2)]
    min = float(minstr) if minstr and minstr != "-inf" else -limit
    max = float(maxstr) if maxstr and maxstr != "inf" else limit
    if min >= max:
        raise ValueError("min must be less than max in (%g,%g)"%(min, max))
    if min < -limit:
        raise ValueError("min value %g must be more than %g"%(min, -limit))
    if max > limit:
        raise ValueError("max value %g must be more than %g"%(max, limit))
    return min, max

def get_paragraphs(lines):
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


def test_parse_parameters():
    all_good = """
        s1 (str) : p1 description

        s2 (str) : colon not allowed after str.
        Description can go on for many lines.
        Default value is still at the end

        s3 : input defaults to string

        i1 (int?) : optional integer
            extended description can be indented.

        i2 (int*:<0,5>) : multiple integers in <0,5>

        i3 (int[]:<3,>) : integer >= 3

        i4 ( int [ ] * : < 3, inf > ) : integer >= 3

        i5(int+:<,6>):atleastoneinteger<=6

        i6 (int:<-inf,-6>) : i <= -6

        f1 (float:s) : floating point with seconds unit

        f2 (float:<2.718, 3.142>) :floating point with range and no units

        f3 (float:neutrons/s<0,inf>) : count rates must be non-negative

        f4 ( float: neutrons/s ) : count rates must be non-negative

        f5 (float: neutrons/s <0,inf> ) : count rates must be non-negative

        f6 (float[3]) : x,y,z coordinates

        o1 (opt:a|b|c) : simple options

        o2 (opt*: space in name | allowed | ... ) : spaces in options

        o3 (opt[]: long|options
            |split) : over multiple lines

        o4 (opt: p1=Parameter 1||Parameter 2) : empty option allowed

        e1 (regex:.*) :

        r1 (range:x) : x range

        r2 (range:y ) : y range

        r3 (range: xy ) : xy range

        spinflip {Correct Spinflip Data} (bool)
            : Correct spinflip data if available.

        file_name (fileinfo) :

        point (index) :

        coord (coordinate) :
    """

    p = dict((pk['id'], pk) for pk in parse_parameters(all_good.split('\n')))
    #import pprint; pprint.pprint(p)

    assert p['s1']['description'] == 'p1 description'
    assert p['i1']['description'] == 'optional integer extended description can be indented.'
    assert p['e1']['description'] == ''

    assert p['spinflip']['label'] == 'Correct Spinflip Data'
    assert p['file_name']['label'] == 'File Name'
    assert p['r3']['label'] == 'R3'

    # See FIELD_TYPES for list of available field types
    assert p['s3']['datatype'] == 'str'
    assert p['spinflip']['datatype'] == 'bool'
    assert p['i2']['datatype'] == 'int'
    assert p['f4']['datatype'] == 'float'
    assert p['o2']['datatype'] == 'opt'
    assert p['e1']['datatype'] == 'regex'
    assert p['r1']['datatype'] == 'range'
    assert p['point']['datatype'] == 'index'
    assert p['coord']['datatype'] == 'coordinate'
    assert p['file_name']['datatype'] == 'fileinfo'

    assert p['f5']['required'] == True   # multiplicity: none
    assert p['f5']['multiple'] == False
    assert p['i1']['required'] == False  # multiplicity: ?
    assert p['i1']['multiple'] == False
    assert p['i5']['required'] == True   # multiplicity: +
    assert p['i5']['multiple'] == True
    assert p['o2']['required'] == False  # mulitplicity: *
    assert p['o2']['multiple'] == True

    assert p['f4']['length'] == 1  # no vector tag
    assert p['i4']['length'] == 0  # tagged with [ ]
    assert p['f6']['length'] == 3  # tagged with [3]

    assert p['s1']['typeattr'] == {}

    assert p['i1']['typeattr']['range'] == [-1e9, 1e9]
    assert p['i2']['typeattr']['range'] == [0, 5]
    assert p['i3']['typeattr']['range'] == [3, 1e9]
    assert p['i4']['typeattr']['range'] == [3, 1e9]
    assert p['i5']['typeattr']['range'] == [-1e9, 6]
    assert p['i6']['typeattr']['range'] == [-1e9, -6]

    assert p['f1']['typeattr']['units'] == 's'
    assert p['f2']['typeattr']['units'] == ''
    assert p['f3']['typeattr']['units'] == 'neutrons/s'
    assert p['f4']['typeattr']['units'] == 'neutrons/s'
    assert p['f5']['typeattr']['units'] == 'neutrons/s'

    assert p['f1']['typeattr']['range'] == [-1e300, 1e300]
    assert p['f2']['typeattr']['range'] == [2.718, 3.142]

    assert p['o1']['typeattr']['choices'] == [
        ['a', 'a'], ['b', 'b'], ['c', 'c']
    ]
    assert p['o2']['typeattr']['choices'] == [
        ['space in name', 'space in name'], ['allowed', 'allowed']
    ]
    assert p['o3']['typeattr']['choices'] == [
        ['long', 'long'], ['options', 'options'], ['split', 'split']
    ]
    assert p['o4']['typeattr']['choices'] == [
        ['p1', 'Parameter 1'], ['', ''], ['Parameter 2', 'Parameter 2']
    ]

    assert p['e1']['typeattr'] == {'pattern': '.*'}

    assert p['r1']['datatype'] == 'range'
    assert p['r1']['typeattr'] == {'axis': 'x'}
