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

    return_node, return_terminal = target

    results = {}
    fingerprints = fingerprint_template(template, config)
    for node, input_wires in template.ordered(target=return_node):
        node_info = template.modules[node]
        module = lookup_module(node_info['module'])
        input_terminals = module.inputs
        output_terminals = module.outputs
        # Initialize input terminals to empty bundles
        inputs = dict((t["id"], []) for t in input_terminals)
        if cache.exists(fingerprints[node]):
            print "already cached", node
            continue
        

        # Extend input terminals from the bundles on the wires
        for wire in input_wires:
            source_node, source_terminal = wire["source"]
            target_node, target_terminal = wire["target"]
            # Make key a tuple; wire["source"] won't work because it is
            # a mutable list, and can't be used as a dictionary key, but
            # an (int, string) tuple can be.
            key = source_node, source_terminal
            if tuple(key) not in results:
                fp = fingerprints[source_node]
                print "retrieving cached value for node %d:"%source_node, fp
                bundles = _retrieve(cache, fp)
                results.update(((source_node,k),v) for k,v in bundles.items())
            inputs[target_terminal].extend(results[key].values)

        # Check arity of module. If the input terminals are all multiple
        # inputs, then the action needs to be called once with the bundle.
        # If the input terminals are all single input, then the action
        # needs to be called once for each dataset in the bundle.
        # For mixed single/multiple inputs the first input must be single.
        # If the output is single, it is made into a length one bundle.
        # If the output is multiple, then it is assumed to already be
        # a bundle.  With mixed single input/multiple output, all outputs
        # are concatenated into one bundle.
        multiple = all(t["multiple"] == True for t in input_terminals)

        # Fields set for the current node
        fields = config.get(str(node), {})

        # Run the calculation
        print "calculating values for node", node, node_info
        if multiple or not input_terminals:

            # Get default field values from template
            node_config = node_info.get('config', {})

            # Paste in field values from template application
            node_config.update(fields)

            # Paste in the input terminal values
            node_config.update(inputs)

            # Perform action and make sure outputs forms a list.
            outputs = module.action(**node_config)
            if len(output_terminals) <= 1:
                outputs = [outputs]

            # Outputs is a list, so map it into a dictionary based on
            # terminal id.  Single outputs need to be converted to lists
            # of length 1.
            bundles = dict((t["id"],(v if t["multiple"] else [v]))
                           for t,v in zip(output_terminals, outputs))
        else:
            # Single input, so call once for each datasets
            bundles = dict((t["id"], []) for t in output_terminals)
            # Assume that all inputs are the same length as the first input,
            # or are length 1 (e.g., subtract background from list of specular)
            # or are length 0 (e.g., no background specified, so background
            # comes in as None).  Length 0 inputs are only allowed if the
            # terminal is not a required input.  Fields may or may not need
            # to be duplicated.
            n = len(inputs[input_terminals[0]["id"]])
            for i in range(n):
                # Get default field values from template
                node_config = node_info.get('config', {})

                # Substitute field values, one per input if the field is
                # multiple, otherwise one for all inputs.
                for f in module.fields:
                    fid = f["id"]
                    if fid in fields:
                        bundle = fields[fid]
                        if f["multiple"]:
                            node_config[fid] = bundle
                        elif len(bundle) == 0:
                            if f["required"]:
                                raise ValueError("missing required input for %r for %d: %s"
                                                 % (node, fid, node_info["module"]))
                            # No need to specify default
                        elif len(bundle) == 1:
                            node_config[fid] = bundle[0]
                        else:
                            node_config[fid] = bundle[i]
                    # else:
                    #     pass # No need to specify default

                # Substitute input terminal values
                for t in input_terminals:
                    tid = t["id"]
                    bundle = inputs[tid]
                    if t["multiple"]:
                        node_config[tid] = bundle
                    elif len(bundle) == 0:
                        if t["required"]:
                            raise ValueError("missing required input %r for %d: %s"
                                             % (node, tid, node_info["module"]))
                        node_config[tid] = None
                    elif len(bundle) == 1:
                        node_config[tid] = bundle[0]
                    else:
                        node_config[tid] = bundle[i]

                # Perform action and make sure outputs forms a list
                outputs = module.action(**node_config)
                if len(output_terminals) <= 1:
                    outputs = [outputs]

                # Gather outputs
                for t, v in zip(output_terminals, outputs):
                    if t["multiple"]:
                        bundles[t["id"]].extend(v)
                    else:
                        bundles[t["id"]].append(v)

        data = {}
        for t in output_terminals:
            tid = t["id"]
            datatype = lookup_datatype(t["datatype"])
            data[t["id"]] = Bundle(datatype=datatype, values=bundles[tid])
        print "caching", node, module.id
        #print "caching", module.id, bundles
        #print "caching",_serialize(bundles, output_terminals)
        _store(cache, fingerprints[node], data)
        results.update(((node,k),v) for k,v in data.items())

    #print list(sorted(results.keys()))
    if return_node is not None:
        #print "returning", return_node, return_terminal
        #print "key",_cache_key(fingerprints[return_node], return_terminal)
        return results[(return_node,return_terminal)]
    else:
        return results


def _store(cache, fp, data):
    stored = dict((k, v.todict()) for k,v in sorted(data.items()))
    string = json.dumps(sanitizeForJSON(stored))
    cache.set(fp, string)

def _retrieve(cache, fp):
    string = cache.get(fp)
    stored = sanitizeFromJSON(json.loads(string))
    data = dict((k, Bundle.fromdict(v)) for k,v in stored)
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
    config = module['config']
    config.update(node_config)
    config_str = str(_format_ordered(config))
    parts = [module['module'], module['version'], config_str] + inputs_fp
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
