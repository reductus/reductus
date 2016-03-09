"""
Run a reduction workflow.

The function run_template
"""

import json
import hashlib
import contextlib
from inspect import getsource

from .cache import get_cache
from .core import lookup_module, lookup_datatype
from .core import sanitizeForJSON, sanitizeFromJSON, Bundle

def find_calculated(template, config):
    """
    Returns a boolean vector indicating whether or not each node in the
    template has been computed and cached.
    """
    cache = get_cache()

    fingerprints = fingerprint_template(template, config)
    return [cache.exists(fingerprints[node])
            for node, _ in enumerate(template.modules)]


def process_template(template, config, target=(None,None)):
    """
    Evaluate the template.

    If *target=(node number, "terminal id")* is specified, then only
    calculate the nodes required to evaluate the target.

    For each node, if its fingerprint is already in the cache, retrieve
    the cached value and use it for subsequent nodes.  If not, then run
    the node action and place the results in the cache.

    If *target* is specified, then return the target as a json serialized
    object containing the list of values on the specified output terminal.
    """
    cache = get_cache()

    results = {}
    return_node, return_terminal = target

    fingerprints = fingerprint_template(template, config)
    for node, input_wires in template.ordered(target=return_node):
        node_info = template.modules[node]
        module = lookup_module(node_info['module'])
        node_id = "%d: %s"%(node, node_info['module'])
        input_terminals = module.inputs
        output_terminals = module.outputs

        # Build the inputs; if the returning an input terminal, put it in the
        # results set.   This is extra work for the case where the results
        # have already been computed, but it simplifies the code for the
        # case where the return target is an input terminal.
        inputs = _get_inputs(results, input_wires, input_terminals)
        if return_node == node and return_terminal in inputs:
            # We are returning inputs, so treat them as if it were outputs.
            # That means putting them into a bundle so that we can convert
            # to and from JSON.  But we have to find the terminal first so
            # that we know the datatype.  Since we are only returning the
            # inputs, we don't need to compute the node outputs, and we
            # can return immediately.
            for terminal in input_terminals:
                if terminal["id"] == return_terminal:
                    return _bundle(terminal, inputs[return_terminal])

        # Use cached value if it exists, skipping to the next loop iteration.
        fp = fingerprints[node]
        if cache.exists(fp):
            print "retrieving cached value for node %d:"%node, fp
            bundles = _retrieve(cache, fp)
            results.update((_key(node, k), v) for k, v in bundles.items())
            continue

        # Fields set for the current node
        template_fields = node_info.get('config', {})
        user_fields = config.get(str(node), {})

        # Evaluate the node
        outputs = _eval_node(node_id, module, inputs, template_fields, user_fields)

        # Collect the outputs
        bundles = {}
        for terminal in output_terminals:
            tid = terminal["id"]
            bundles[tid] = _bundle(terminal, outputs[tid])
        print "caching", node, module.id
        #print "caching", module.id, bundles
        #print "caching",_serialize(bundles, output_terminals)
        _store(cache, fingerprints[node], bundles)
        results.update((_key(node, k), v) for k, v in bundles.items())

    #print list(sorted(results.keys()))

    if return_node is None:
        return results
    else:
        return results[_key(return_node, return_terminal)]


def _bundle(terminal, values):
    """
    Build a bundle for the terminal values.  The bundle has to carry the
    datatype around so that it has enough information to convert values
    to and from JSON.
    """
    datatype = lookup_datatype(terminal["datatype"])
    return Bundle(datatype=datatype, values=values)

def _key(node, terminal):
    """
    Combine *node* and *terminal* to a key into the results set for the
    current template.

    Returns a string unique within the template that can be used in JSON.
    """
    return ":".join((str(node), str(terminal)))


def _get_inputs(results, input_wires, input_terminals):
    """
    Lookup the inputs to all terminals from the results dictionary.

    *results* are the previous results.

    *input_wires* are all wires connecting to the input terminals for this
    node.  Each wire is represented by a dictionary linking the upstream
    source to the nodes target terminal as
    *{source: [node, terminal], target: [node, terminal]}*

    *input_terminals* is the list of input terminals for the node.

    Returns *{terminal: [dataset, ...]}* for all input terminals.
    """
    # Create bundles for the input terminals
    inputs = dict((terminal["id"], []) for terminal in input_terminals)
    for wire in input_wires:
        source_node, source_terminal = wire["source"]
        target_node, target_terminal = wire["target"]
        # Make key a tuple; wire["source"] won't work because it is
        # a mutable list, and can't be used as a dictionary key, but
        # an (int, string) tuple can be.
        v = results[_key(source_node, source_terminal)].values
        inputs[target_terminal].extend(v)
    return inputs


def _eval_node(node_id, module, inputs, template_fields, user_fields):
    """
    Run the action for the node.

    *id* is a string identifier for the node, for errors and logging

    *module* is the module activated by the node.

    *inputs* contains the input terminal info as *{terminal: [data, ...]}*.

    *template_fields* contains the field values stored in the
    template as *{field: [value, ...]}*.

    *user_fields* contains the field values sent as part of the template
    config as *{field: [value, ...]}*.

    Returns the output terminal bundle as *(terminal: [data, ...]}*.
    """
    input_terminals = module.inputs
    output_terminals = module.outputs

    # Check arity of module. If the input terminals are all multiple
    # inputs, then the action needs to be called once with the bundle.
    # If the input terminals are all single input, then the action
    # needs to be called once for each dataset in the bundle.
    # For mixed single/multiple inputs the first input must be single.
    # If the output is single, it is made into a length one bundle.
    # If the output is multiple, then it is assumed to already be
    # a bundle.  With mixed single input/multiple output, all outputs
    # are concatenated into one bundle.
    multiple = all(terminal["multiple"] for terminal in input_terminals)

    # Run the calculation
    print "calculating values for node", node_id
    if multiple or not input_terminals:
        # Get default field values from template
        action_args = template_fields.copy()

        # Paste in field values from template application
        action_args.update(user_fields)

        # Paste in the input terminal values
        action_args.update(inputs)

        # Do the work
        result = _do_action(module, **action_args)

        # Gather the output.  Action outputs a list, so map it into a
        # dictionary based on terminal id.  If the output is not multiple,
        # it needs to be converted to a list of length 1.
        outputs = dict((terminal["id"],(v if terminal["multiple"] else [v]))
                       for terminal, v in zip(output_terminals, result))

    else:
        # Single input, so call once for each datasets
        outputs = dict((terminal["id"], []) for terminal in output_terminals)
        # Assume that all inputs are the same length as the first input,
        # or are length 1 (e.g., subtract background from list of specular)
        # or are length 0 (e.g., no background specified, so background
        # comes in as None).  Length 0 inputs are only allowed if the
        # terminal is not a required input.  Fields may or may not need
        # to be duplicated.
        n = len(inputs[input_terminals[0]["id"]])
        for k in range(n):
            # Get default field values from template
            action_args = template_fields.copy()

            # Substitute field values, one per input if the field is
            # multiple, otherwise one for all inputs.
            for field in module.fields:
                fid = field["id"]
                bundle = None
                if fid in template_fields:
                    bundle = template_fields[fid]
                if fid in user_fields:
                    bundle = user_fields[fid]
                if bundle is not None:
                    if field["multiple"]:
                        action_args[fid] = bundle
                    elif len(bundle) == 0:
                        if field["required"]:
                            raise ValueError("missing required input %r for %s"
                                             % (fid, node_id))
                            # No need to specify default
                    elif len(bundle) == 1:
                        action_args[fid] = bundle[0]
                    else:
                        action_args[fid] = bundle[k]
                        # else:
                        #     pass # No need to specify default

            # Substitute input terminal values
            for terminal in input_terminals:
                tid = terminal["id"]
                bundle = inputs[tid]
                if terminal["multiple"]:
                    action_args[tid] = bundle
                elif len(bundle) == 0:
                    if terminal["required"]:
                        raise ValueError("missing required input %r for %s"
                                         % (tid, node_id))
                    action_args[tid] = None
                elif len(bundle) == 1:
                    action_args[tid] = bundle[0]
                else:
                    action_args[tid] = bundle[k]

            # Do the work
            result = _do_action(module, **action_args)

            # Gather outputs
            for terminal, v in zip(output_terminals, result):
                if terminal["multiple"]:
                    outputs[terminal["id"]].extend(v)
                else:
                    outputs[terminal["id"]].append(v)

    return outputs


def _do_action(module, **action_args):
    """
    Perform the module action, returning the results as a list.

    Because we know the number of outputs expected (each one is a terminal),
    we can convert no outputs or a single output to lists of length 0 and 1
    respectively.  This makes the module actions more natural to write.
    """
    num_outputs = len(module.outputs)
    result = module.action(**action_args)
    if num_outputs == 1:
        result = [result]
    elif num_outputs == 0:
        result = []
    return result



def _store(cache, fp, data):
    """
    Store the output terminals associated with a node.

    *cache* is the interface to the cache (which may be an in-memory
    store, or may be a redis handle).

    *fp* is the finger print of the node, which is based on the finger
    print of its config plus the finger prints of all its inputs.

    *data* is a dictionary of *{terminal: [dataset, dataset, ...]}*.
    """
    stored = dict((k, v.todict()) for k,v in sorted(data.items()))
    string = json.dumps(sanitizeForJSON(stored))
    cache.set(fp, string)

def _retrieve(cache, fp):
    """
    Retrieve data from the cache.

    *cache* is the interface to the cache (which may be an in-memory
    store, or may be a redis handle).

    *fp* is the finger print of the node, which is based on the finger
    print of its config plus the finger prints of all its inputs.

    Returns *data* as a dictionary of *{ terminal: [dataset, dataset, ...]}*.
    """
    string = cache.get(fp)
    stored = sanitizeFromJSON(json.loads(string))
    data = dict((str(terminal), Bundle.fromdict(values))
                for terminal,values in stored.items())
    return data

def fingerprint_template(template, config):
    """
    run the fingerprint operation on the whole template, returning
    the dict of fingerprints (one per output terminal)
    """
    fingerprints = {}
    for node, inputs in template.ordered():
        # Get fingerprints for terminal inputs
        inputs_fp = []
        for wire in inputs:
            source_node, source_terminal = wire['source']
            target_node, target_terminal = wire['target']
            source_fp = fingerprints[source_node]
            inputs_fp.extend([source_terminal, target_terminal, source_fp])

        # Get field values
        node_config = config.get(str(node), {})

        # Get module id and version
        module = template.modules[node]

        # Create and store fingerprint
        fp = fingerprint_node(module, node_config, inputs_fp)
        fingerprints[node] = fp
        #print "template fp", node, module, node_config, inputs_fp, fp

    return fingerprints


def fingerprint_node(module, node_config, inputs_fp):
    """
    Create a unique sha1 hash for a module based on its attributes and inputs.
    """
    config = module.get('config', {})
    config.update(node_config)
    config_str = str(_format_ordered(config))
    current_module_version = lookup_module(module['module']).version
    parts = [module['module'], current_module_version, config_str] + inputs_fp
    fp = hashlib.sha1(":".join(parts)).hexdigest()
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
        print "fingerprinting function",value
        return getsource(value)
    elif hasattr(value, '__getstate__'):
        print "fingerprinting class using getstate",value
        return [value.__class__.__name__, _format_ordered(value.__getstate__())]
    elif hasattr(value, '__dict__'):
        print "fingerprinting class using dict",value
        return [value.__class__.__name__, _format_ordered(value.__dict__)]
    else:
        return value


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
            actual = process_template(template, config)
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
        result = process_template(template, config)

    if verbose:
        print 'result: ', json.dumps(result, sort_keys=True, indent=2)
    for key, value in result.items():
        for output in value.get('output',[]):
            if not isinstance(output, dict):
                #print key, 'plot: ', output.get_plottable()
                pass

# internal tests
def test_format_ordered():
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
