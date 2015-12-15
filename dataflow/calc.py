"""
Run a reduction workflow.

The function run_template
"""

import hashlib
import contextlib
from inspect import getsource
from copy import deepcopy

import numpy as np

from .cache import get_cache
from .core import lookup_module, lookup_datatype


def run_template(template, config):
    """
    Evaluate the template using the configured values.

    *template* is a :class:`dataflow.core.Template` structure representing 
    the computation.
    
    *config* is a dictionary, with config[node] containing the values for
    the fields and input terminals at each node in the template.  
    Note: this version keeps all intermediates, and so isn't suitable for
    large data sets.
    """
    cache = get_cache()

    all_results = {}
    fingerprints = fingerprint_template(template, config)
    for nodenum, wires in template:
        # Find the modules
        node = template.modules[nodenum]
        module_id = node['module']  # template.modules[node]
        module = lookup_module(module_id)
        inputs = _map_inputs(module, wires)
        
        parents = template.get_parents(nodenum)
        # this is a list of wires that terminate on this module
        inputs_fp = []
        for wire in parents:
            source_nodenum, source_terminal_id = wire['source']
            target_nodenum, target_terminal_id = wire['target']
            input_fp = fingerprints[source_nodenum]
            inputs_fp.append([target_terminal_id, input_fp])

        # substitute values for inputs
        input_args = dict((k, _lookup_results(all_results, v))
                          for k, v in inputs.items())

        # Include configuration information
        node_config = node.get('config', {})  # Template defaults
        node_config.update(config[nodenum])  # Instance arguments
        node_config.update(input_args)

        # Fingerprinting
        fp = name_fingerprint(fingerprints[nodenum])
        
        # Overwrite even if there was already the same reduction?
        if cache.exists(fp):  # or module.name == 'Save':
            result = {}
            for terminal in module.terminals:
                if terminal['use'] == 'out':
                    cls = lookup_datatype(terminal['datatype']).cls
                    terminal_fp = name_terminal(fp, terminal['id'])
                    result[terminal['id']] = [cls.loads(s)
                            for s in cache.lrange(terminal_fp, 0, -1)]
        else:
            result = module.action(**node_config)
            for terminal_id, res in result.items():
                terminal_fp = name_terminal(fp, terminal_id)
                for data in res:
                    cache.rpush(terminal_fp, data.dumps())
            cache.set(fp, fp)  # used for checking if the calculation exists;
            # could wrap this whole thing with loop over output terminals
        all_results[nodenum] = result
    # retrieve plottable results
    ans = {}
    for nodenum, result in all_results.items():
        fp = name_plottable(fingerprints[nodenum])
        plottable = {}
        for terminal_id, arr in result.items():
            terminal_fp = name_terminal(fp, terminal_id)
            if cache.exists(terminal_fp):
                plottable[terminal_id] = cache.lrange(terminal_fp, 0, -1)
            else:
                plottable[terminal_id] = convert_to_plottable(arr)
                for s in plottable[terminal_id]:
                    cache.rpush(terminal_fp, s)
        ans[nodenum] = plottable
    return ans

def calc_single(template, config, nodenum, terminal_id):
    """
    Return the value for a terminal.

    If the terminal fingerprint is already in the cache, retrieve it and
    return the associated value.  If not, then compute the value for the
    terminal and place it in the cache.
    """
    cache = get_cache()

    # Find the modules
    node = template.modules[nodenum]
    module_id = node['module'] # template.modules[node]
    module = lookup_module(module_id)
    terminal = module.get_terminal_by_id(terminal_id)
    if terminal['use'] != 'out':
        # then this is an input terminal... can't get it!
        return {}
    
    all_fp = fingerprint_template(template, config)
    fp = name_fingerprint(all_fp[nodenum])
    terminal_fp = name_terminal(fp, terminal_id)
    if cache.exists(terminal_fp):
        print "retrieving cached value: " + terminal_fp
        cls = lookup_datatype(terminal['datatype']).cls
        result = [cls.loads(s) for s in cache.lrange(terminal_fp, 0, -1)]
    else:
        # get inputs from parents
        print "no cached calc value: calculating..."
        parents = template.get_parents(nodenum)
        # this is a list of wires that terminate on this module
        input_args = {}
        for wire in parents:
            source_nodenum, source_terminal_id = wire['source']
            source_data = calc_single(template, config, source_nodenum,
                                      source_terminal_id)
            target_id = wire['target'][1]
            if target_id in input_args:
                # this explicitly assumes all data is a list
                # so that we can concatenate multiple inputs
                input_args[target_id] += source_data
            else:
                input_args[target_id] = source_data
        
        # Include configuration information
        node_config = node.get('config', {})  # Template defaults
        node_config.update(config.get(str(nodenum), {}))  # Instance arguments
        node_config.update(input_args)

        calc_value = module.action(**node_config)
        # pushing the value of all the outputs for this node to cache, 
        # even though only one was asked for
        for terminal_name, arr in calc_value.items():
            terminal_fp = name_terminal(fp, terminal_name)
            for data in arr:
                cache.rpush(terminal_fp, data.dumps())
        result = calc_value[terminal_id]
    print "result calculated: ", fp
    return result

def get_plottable(template, config, nodenum, terminal_id):
    cache = get_cache()

    # Find the modules
    node = template.modules[nodenum]
    module_id = node['module'] # template.modules[node]
    module = lookup_module(module_id)
    terminal = module.get_terminal_by_id(terminal_id)
    
    all_fp = fingerprint_template(template, config)
    fp = all_fp[nodenum]
    plottable_fp = name_terminal(name_plottable(fp), terminal_id)
    binary_fp = "Binary:" + fp + ":" + terminal_id
    if cache.exists(plottable_fp):
        print "retrieving cached plottable: " + plottable_fp
        plottable = cache.lrange(plottable_fp, 0, -1)
    else:
        print "no cached plottable: calculating..."
        data = calc_single(template, config, nodenum, terminal_id)
        plottable = []
        binary_data = []
        for dnum, datum in enumerate(data):
            if hasattr(datum, 'use_binary') and datum.use_binary() == True:
                binary_data = datum.get_plottable_binary()
                # need this so we can lookup by bundle number later
                bundle_fp = binary_fp + ":" + str(dnum)
                for i, item in enumerate(binary_data):
                    # need this so we can look up individual plottable columns later
                    new_fp = bundle_fp + ":" + str(i)
                    cache.rpush(new_fp, item)
                p = datum.get_plottable(binary_fp=bundle_fp)
            else:
                p = datum.get_plottable()
                
            plottable.append(p)
        for item in plottable:
            cache.rpush(plottable_fp, item)
            
    return plottable


def get_csv(template, config, nodenum, terminal_id):
    cache = get_cache()

    # Find the modules
    node = template.modules[nodenum]
    module_id = node['module'] # template.modules[node]
    module = lookup_module(module_id)
    terminal = module.get_terminal_by_id(terminal_id)
    
    all_fp = fingerprint_template(template, config)
    fp = all_fp[nodenum]
    csv_fp = name_terminal(name_csv(fp), terminal_id)
    if cache.exists(csv_fp):
        print "retrieving cached value: " + csv_fp
        csv = cache.lrange(csv_fp, 0, -1)
    else:
        data = calc_single(template, config, nodenum, terminal_id)
        csv = convert_to_csv(data)
        for item in csv:
            cache.rpush(csv_fp, item)
    return csv

def fingerprint_template(template, config):
    """ run the fingerprint operation on the whole template, returning
    the dict of fingerprints (one per output terminal) """    
    fingerprints = {}
    index = 0
    for nodenum, wires in template:
        # Find the modules
        node = template.modules[nodenum]
        module_id = node['module'] # template.modules[node]
        module = lookup_module(module_id)
        parents = template.get_parents(nodenum)
        # this is a list of wires that terminate on this module
        inputs_fp = []
        for wire in parents:
            source_nodenum, source_terminal_id = wire['source']
            target_nodenum, target_terminal_id = wire['target']
            input_fp = fingerprints[source_nodenum]
            inputs_fp.append([target_terminal_id, input_fp])
        #inputs = _map_inputs(module, wires)
        
        # Include configuration information
        node_config = {}
        # let's not grab config information from the node... like position.
        # only taking configuration defined for this group number.
        #configuration.update(node.get('config', {}))
        node_config.update(config.get(str(nodenum), {}))  # keys must be strings...
        #node_config.update(config[nodenum])
        print "configuration for fingerprint:", node_config
        
        # Fingerprinting
        fp = finger_print(module, node_config, index, inputs_fp)  # terminals included
        print nodenum, module, node_config, index, inputs_fp, fp
        fingerprints[nodenum] = fp
        index += 1
    return fingerprints

def _lookup_results(result, s):
    # Hack to figure out if we have a bundle.  Fix this!
    try:
        return [_lookup_results(result, (node_name, terminal))
                for node_name, terminal in s]
    except TypeError:
        pass

    node_name, terminal = s
    try:
        node = result[node_name]
    except KeyError:
        raise KeyError("Could not find node %s"%node_name)
    try:
        return node[terminal]
    except KeyError:
        raise KeyError("Could not find terminal %r in %r for node %s"
                       % (terminal, node.keys(), node_name))


def _map_inputs(module, wires):
    """
    Figure out which wires go to which input terminals.

    *module* : Module

    *wires* : [TemplateWire]

    Returns { id : None | source | [source, ...] }.

    id will range over the set of input terminals.

    source is a pair (int, string) giving the node number of the
    connecting terminal and its terminal name.
    """
    kwargs = {}
    for terminal in module.terminals:
        if terminal['use'] != "in": continue

        collect = [w['source'] for w in wires if w['target'][1] == terminal['id']]
        if len(collect) == 0:
            if terminal['required']:
                raise TypeError("Missing input for %s.%s"
                                % (module.id, terminal['id']))
            elif terminal['multiple']:
                kwargs[terminal['id']] = collect
            else:
                kwargs[terminal['id']] = None
        elif terminal['multiple']:
            kwargs[terminal['id']] = collect
        elif len(collect) > 1:
            raise TypeError("Excess input for %s.%s"
                            % (module.id, terminal['id']))
        else:
            kwargs[terminal['id']] = collect[0]
    return kwargs

def finger_print(module, args, nodenum, inputs_fp):
    """
    Create a unique sha1 hash for a module based on its attributes and inputs.
    """
    d = _format_ordered(deepcopy(module.__dict__))
    parts = [str(d)]
    bad_args = ["position", "xtype", "width", "terminals", "height", "title", "image", "icon"]
    new_args = dict((arg, value) for arg, value in args.items() if arg not in bad_args)
    new_args = _format_ordered(new_args)
    parts.append(str(new_args)) # all arguments for the given module
    # [actually, I don't think it matters what order it's in! - bbm]
    # [how can sha1 not be order dependent?? - pak]
    #fp += str(nodenum) # node number in template order
    parts.extend(part for item in inputs_fp for part in item)

    fp = hashlib.sha1("".join(parts)).hexdigest()
    return fp

# new methods that keep everything ordered
def _format_ordered(value):
    if isinstance(value, dict):
        return list((k, _format_ordered(v)) for k, v in sorted(value.items()))
    elif isinstance(value, list):
        return [_format_ordered(v) for v in value]
    elif isinstance(value, tuple):
        return tuple(_format_ordered(v) for v in value)
    elif callable(value):
        return getsource(value)
    elif hasattr(value, '__dict__'):
        return [value.__class__.__name__, _format_ordered(value.__dict__)]
    else:
        return value

def convert_to_plottable(result):
    print "Starting new converter"
    return [data.get_plottable() for data in result]
    
def convert_to_csv(result):
    if np.all([hasattr(data, 'get_csv') for data in result]):
        print "Starting CSV converter"
        print len(result)
        return [data.get_csv() for data in result]
    else:
        print "No CSV converter available for this datatype"
        return [""]
    
def name_fingerprint(fp):
    return "Fingerprint:" + fp
def name_plottable(fp):
    return "Plottable:" + fp
def name_csv(fp):
    return "CSV:" + fp
def name_terminal(fp, terminal_id):
    return fp + ":" + terminal_id


# ===== Test support ===
@contextlib.contextmanager
def push_seed(seed=None): # pragma no cover
    """
    Set a temporary seed to the numpy random number generator, restoring it
    at the end of the context.  If seed is None, then get a seed from
    /dev/urandom (or the windows analogue).
    """
    from numpy.random import get_state, set_state, seed as set_seed
    state = get_state()
    set_seed(seed)
    yield
    set_state(state)

def verify_examples(source_file, tests, target_dir, seed=1): # pragma no cover
    """
    Run a set of templates, comparing the results against previous results.

    *source_file* should be *__file__*, which is the name of the lookup_module
    containing the test templates.

    *tests* is a list of tuples *(filename, (template, config))* where
    *filename* is  the name of the file containing the expected results
    from running *(template, config)*.  For example::

        verify_examples(__file__, tests=[
            ('bt7_example.test', (bt7_template, bt7_config)),
            ])

    *target_dir* is the directory which contains the expected result from
    running the template with the given configuration.  If it is not given,
    then it defaults to the "tests" subdirectory of the directory containing
    *source_file*.

    *seed* is the numpy random number generator (RNG) seed to use for the test.
    Before running each test, the RNG state is captured, the seed is set,
    the test is run, and the state is restored.  This allows you to run an
    individual example with :func:`run_example` and get the same result.
    *seed* defaults to 1.

    For each test, the expected results should be found in *target_dir/filename*
    If this file doesn't exist then the actual results will be stored and the
    test will pass.  If the file does exist, then the expected results are
    loaded and compared to the actual results.  New test results should be
    added/updated in the instrument repository.

    Raises *AssertionError* if any tests fail, indicating which files contain
    the expected result and the actual result.
    """
    import tempfile
    import os
    import json
    from os.path import join, exists, dirname
    import logging; logging.basicConfig(level=logging.WARNING)

    # No cache, so default to memory cache

    errors = []
    for (filename, (template, config)) in tests:
        print("checking %s"%filename)
        with push_seed(seed):
            actual = run_template(template, config)
        target_path = join(target_dir, filename)
        actual_str = json.dumps(actual, sort_keys=True)
        if not exists(target_path):
            if not exists(dirname(target_path)):
                os.makedirs(dirname(target_path))
            with open(target_path, 'wb') as fid:
                fid.write(actual_str)
        else:
            with open(target_path, 'rb') as fid:
                target_str = fid.read()
            if not actual_str == target_str:
                actual_path = join(tempfile.gettempdir(),filename)
                if not exists(dirname(actual_path)):
                    os.makedirs(dirname(actual_path))
                with open(actual_path, 'wb') as fid:
                    fid.write(actual_str)
                errors.append("  %r does not match target %r"
                              % (actual_path, target_path))
    if errors: # pragma no cover
        raise AssertionError("\n".join(errors))

def run_example(template, config, seed=None, verbose=False): # pragma no cover
    import json

    if verbose:
        from . import wireit
        print 'template: ', json.dumps(wireit.template_to_wireit_diagram(template),
                                       sort_keys=True, indent=2)
        print 'config: ', json.dumps(config, sort_keys=True, indent=2)

    with push_seed(seed):
        result = run_template(template, config)

    if verbose:
        print 'result: ', json.dumps(result,sort_keys=True, indent=2)
    for key, value in result.items():
        for output in value.get('output',[]):
            if not isinstance(output, dict):
                #print key, 'plot: ', output.get_plottable()
                pass

# internal tests
def test_ordered():
    udict,odict = {'x':2,'a':3}, [('a',3),('x',2)]
    def ufn(a): return a
    class A(object):
        def __init__(self):
            self.x, self.a = 2,3
    class A2:
        def __init__(self):
            self.x, self.a = 2,3
    pairs = [
        (udict,odict),
        ({'first':udict,'second':'ple'}, [('first',odict), ('second','ple')]),
        ([1,udict,3], [1,odict,3]),
        ((1,udict,3), (1,odict,3)),
        (ufn, "    def ufn(a): return a\n"),
        (A(), ['A', odict]),
        (A2(), ['A2', odict]),
        ]

    for u,o in pairs:
        actual = _format_ordered(u)
        print "%s => %r =? %r"%(str(u),actual,o)
        assert actual == o
