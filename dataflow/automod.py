"""
Generate module definitions from function declarations.

:func:`make_modules` defines the modules available for the instrument given
a list of actions.  The doc strings of the actions define the interface.

:func:`make_template` defines a convenient syntax for creating templates
from a script.
"""
import inspect
import re

from numpy import inf

from .core import Module, Template

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
    inputs = parse_parameters(input_lines)
    output_terminals = parse_parameters(output_lines)

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
            p['default'] = defaults[p['id']]

    # Check the types on the input fields
    for p in input_fields:
        if p['datatype'] not in FIELD_TYPES:
            raise ValueError("Invalid type %s for %s"%(p['datatype'], p['id']))

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


# parameter definition regular expression
parameter_re = re.compile("""\A
    \s*(?P<id>\w+)                           # name
    \s*([(]                                  # (
        \s*(?P<datatype>.*?)                 #    datatype  (non-greedy)
        \s*([[]\s*(?P<length>[0-9]*)\s*[]])? #    [length]  (optional)
        \s*(?P<multiple>[?*+])?              #    multiple  (optional [*+?])
        \s*(:\s*(?P<typeattr>.*?))?          #    :typeattr (optional)
    \s*[)])?                                 # )
    \s*:                                     # :
    \s*(?P<description>.*?)                  # description  (non-greedy)
    \s*([[]\s*(?P<default>.*?)\s*[]])?       # [default]    (optional)
    \s*\Z""", re.VERBOSE)
def parse_parameters(lines):
    """
    Interpret the doc strings for the parameters.

    Each parameter must use the form defined by the following syntax:

        name (type[length]#:attr): description [default]

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
            except:
                ValueError("bad length specifier:\n "+"  ".join(group))
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
        attribute is set as *typeattr={pattern: "pattern"}*.

    *fileinfo* -> *datatype=fileinfo*

        A file identifier on the server with the following structure::

            {
                *path*: location on server,
                *mtime*: modification time
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
        The type attribute is set as *typeattr={axis: "axis"}*.

    *coordinate* -> *datatype=coordinate*

        A point *[x, y]* should be selected from the graph.
    """
    name = par['id']
    type = par["datatype"] if par["datatype"] else "str"
    attrstr = par["typeattr"] if par["typeattr"] else ""
    attr = {}

    #print "type: %r"%type
    if type == "bool":
        # bare attrstr below tests for not None and not empty string
        attr["label"] = attrstr if attrstr else name

    elif type == "int":
        try:
            min, max = parse_range(attrstr, limit=1e9)
            if int(min) != min or int(max) != max:
                raise Exception("use integers for int range")
        except Exception, exc:
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
        except Exception, exc:
            raise ValueError("invalid range for %s: %s"%(name, str(exc)))

        attr["units"] = units.strip()
        attr["range"] = [min, max]

    elif type == "opt":
        if "|" not in attrstr:
            raise ValueError("options not specified for parameter " + name)
        choices = [v.split('=') for v in attrstr.split("|", 2)]
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
            re.compile(attrstr)
        except Exception, exc:
            raise ValueError("regex error %r for %s"%(str(exc),name))
        attr["pattern"] = attrstr

    elif type == "range":
        if attrstr not in ("x", "y", "xy"):
            raise ValueError("range must be one of x, y or xy for " + name)
        attr["range"] = attrstr

    else: # type in ["str", "fileinfo", "index", "coordinate"]:
        if par["typeattr"] is not None:
            raise ValueError("No restrictions on type %s for parameter %s"
                             % (type, name))


    par["datatype"] = type
    par["typeattr"] = attr

FIELD_TYPES = set("str bool int float opt regex range index coordinate fileinfo".split())

def parse_range(range, limit=inf):
    range = range.strip()
    if range == "":
        return [-limit, limit]
    if not (range.startswith('<') and range.endswith('>') and "," in range):
        raise ValueError("expected <min, max>")
    minstr, maxstr = [v.strip() for v in range[1:-1].split(',', 2)]
    min = float(minstr) if minstr and minstr != "-inf" else -limit
    max = float(maxstr) if maxstr and maxstr != "inf" else limit
    if min >= max:
        raise ValueError("min must be less than max")
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
        s1 (str) : p1 description [s1]

        s2 (str) : colon not allowed after str.
        Description can go on for many lines.
        Default value is still at the end [s2 default]

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

        filename (fileinfo) :

        datapoint (index) :

        coord (coordinate) :
    """

    p = dict((p['id'], p) for p in parse_parameters(all_good.split('\n')))

    #import pprint; pprint.pprint(p)

    assert p['s1']['default'] == 's1'
    assert p['s2']['default'] == 's2 default'
    assert p['s3']['default'] is None

    assert p['s1']['description'] == 'p1 description'
    assert p['i1']['description'] == 'optional integer extended description can be indented.'
    assert p['e1']['description'] == ''

    assert p['s3']['datatype'] == 'str'
    assert p['o2']['datatype'] == 'opt'

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
        ['p1', 'Parameter 1'], ['',''], ['Parameter 2', 'Parameter 2']
    ]

    assert p['e1']['typeattr'] == {'pattern': '.*'}

    assert p['r1']['typeattr'] == {'range': 'x'}
