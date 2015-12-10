"""
Run a reduction workflow.

The function run_template
"""

import sys
from pprint import pprint
from inspect import getsource
from .core import lookup_module, lookup_datatype
import hashlib, redis, types, os
from copy import deepcopy
import numpy

if not sys.platform=='win32':
    os.system("nohup redis-server --maxmemory 4gb --maxmemory-policy allkeys-lru > /dev/null 2>&1 &") # ensure redis is running
server = redis.Redis("localhost")
#if not hasattr(server, 'rpush'): server.rpush = server.push

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
    all_results = {}
    fingerprints = fingerprint_template(template, config)
    for nodenum, wires in template:
        # Find the modules
        node = template.modules[nodenum]
        module_id = node['module'] # template.modules[node]
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
        kwargs = dict((k, _lookup_results(all_results, v)) 
                      for k, v in inputs.items())
        
        # Include configuration information
        configuration = {}
        configuration.update(node.get('config', {}))
        configuration.update(config.get(nodenum, {}))
        kwargs.update(configuration)
        
        # Fingerprinting
        fp = name_fingerprint(fingerprints[nodenum])
        
        # Overwrite even if there was already the same reduction?
        if server.exists(fp):# or module.name == 'Save': 
            result = {}
            for terminal in module.terminals:
                if terminal['use'] == 'out':
                    cls = lookup_datatype(terminal['datatype']).cls
                    terminal_fp = name_terminal(fp, terminal['id'])
                    result[terminal['id']] = [cls.loads(str) for str in server.lrange(terminal_fp, 0, -1)]
        else:
            result = module.action(**kwargs)
            for terminal_id, res in result.items():
                terminal_fp = name_terminal(fp, terminal_id)
                for data in res:
                    server.rpush(terminal_fp, data.dumps())
            server.set(fp, fp) # used for checking if the calculation exists; could wrap this whole thing with loop of output terminals
        all_results[nodenum] = result
    # retrieve plottable results
    ans = {}
    for nodenum, result in all_results.items():
        fp = name_plottable(fingerprints[nodenum])
        plottable = {}
        for terminal_id, arr in result.items():
            terminal_fp = name_terminal(fp, terminal_id)
            if server.exists(terminal_fp):
                plottable[terminal_id] = server.lrange(terminal_fp, 0, -1)
            else:
                plottable[terminal_id] = convert_to_plottable(arr)
                for str in plottable[terminal_id]:
                    server.rpush(terminal_fp, str)
        ans[nodenum] = plottable
    return ans

def calc_single(template, config, nodenum, terminal_id):
    """ Calculate fingerprint of terminal in question - if it exists in the cache,
    get it.  Otherwise, calculate from scratch (retrieving parent values recursively) """
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
    if server.exists(terminal_fp):
        print "retrieving cached value: " + terminal_fp
        cls = lookup_datatype(terminal['datatype']).cls
        result = [cls.loads(str) for str in server.lrange(terminal_fp, 0, -1)]
    else:
        # get inputs from parents
        print "no cached calc value: calculating..."
        parents = template.get_parents(nodenum)
        # this is a list of wires that terminate on this module
        kwargs = {}
        for wire in parents:
            source_nodenum, source_terminal_id = wire['source']
            source_data = calc_single(template, config, source_nodenum, source_terminal_id)
            target_id = wire['target'][1]
            if target_id in kwargs:
                # this explicitly assumes all data is a list
                # so that we can concatenate multiple inputs
                kwargs[target_id] += source_data
            else:
                kwargs[target_id] = source_data
        
        # Include configuration information
        configuration = {}
        configuration.update(node.get('config', {}))
        configuration.update(config.get(nodenum, {}))
        kwargs.update(configuration)
        calc_value = module.action(**kwargs)
        # pushing the value of all the outputs for this node to cache, 
        # even though only one was asked for
        for terminal_name, arr in calc_value.items():
            terminal_fp = name_terminal(fp, terminal_name)
            for data in arr:
                server.rpush(terminal_fp, data.dumps())
        result = calc_value[terminal_id]
    print "result calculated: ", fp
    return result

def get_plottable(template, config, nodenum, terminal_id):
    # Find the modules
    node = template.modules[nodenum]
    module_id = node['module'] # template.modules[node]
    module = lookup_module(module_id)
    terminal = module.get_terminal_by_id(terminal_id)
    
    all_fp = fingerprint_template(template, config)
    fp = all_fp[nodenum]
    plottable_fp = name_terminal(name_plottable(fp), terminal_id)
    binary_fp = "Binary:" + fp + ":" + terminal_id
    if server.exists(plottable_fp):
        print "retrieving cached plottable: " + plottable_fp
        plottable = server.lrange(plottable_fp, 0, -1)
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
                    server.rpush(new_fp, item)
                p = datum.get_plottable(binary_fp=bundle_fp)
            else:
                p = datum.get_plottable()
                
            plottable.append(p)
        for item in plottable:
            server.rpush(plottable_fp, item)
            
    return plottable


def get_csv(template, config, nodenum, terminal_id):
    # Find the modules
    node = template.modules[nodenum]
    module_id = node['module'] # template.modules[node]
    module = lookup_module(module_id)
    terminal = module.get_terminal_by_id(terminal_id)
    
    all_fp = fingerprint_template(template, config)
    fp = all_fp[nodenum]
    csv_fp = name_terminal(name_csv(fp), terminal_id)
    if server.exists(csv_fp):
        print "retrieving cached value: " + csv_fp
        csv = server.lrange(csv_fp, 0, -1)
    else:
        data = calc_single(template, config, nodenum, terminal_id)
        csv = convert_to_csv(data)
        for item in csv:
            server.rpush(csv_fp, item)   
    return csv

def fingerprint_template(template, config):
    """ run the fingerprint operation on the whole template, returning
    the dict of fingerprints (one per output terminal) """    
    fingerprints = {}
    index = 0
    config = deepcopy(config)
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
        configuration = {}
        # let's not grab config information from the node... like position.
        # only taking configuration defined for this group number.
        #configuration.update(node.get('config', {}))
        configuration.update(config.get(nodenum, {}))
        print "configuration for fingerprint:", configuration
        
        # Fingerprinting
        fp = finger_print(module, configuration, index, inputs_fp) # terminals included
        print nodenum, module, configuration, index, inputs_fp, fp
        fingerprints[nodenum] = fp
        index += 1
    return fingerprints

def _lookup_results(result, s):
    # Hack to figure out if we have a bundle.  Fix this!
    try:
        return [result[n][t] for n, t in s]
    except:
        try:
            return result[s[0]][s[1]]
        except:
            return None


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
    d = format_ordered(deepcopy(module.__dict__))
    fp = str(d)
    bad_args = ["position", "xtype", "width", "terminals", "height", "title", "image", "icon"]
    new_args = dict((arg, value) for arg, value in args.items() if arg not in bad_args)
    new_args = format_ordered(new_args)
    fp += str(new_args) # all arguments for the given module
    # actually, I don't think it matters what order it's in! - bbm
    #fp += str(nodenum) # node number in template order
    for item in inputs_fp:
        terminal_id, input_fp = item
        fp += terminal_id + input_fp
    fp = hashlib.sha1(fp).hexdigest()
    return fp

# new methods that keep everything ordered
def full_sort_dict(dict):
    items = dict.items()
    items.sort()
    for index, (key, value) in enumerate(items):
        items[index] = key, format_ordered(value)
    return items
def full_sort_arr(arr):
    for index, value in enumerate(arr):
        arr[index] = format_ordered(value)
    return arr
def full_sort_tuple(tuple):
    for index, value in enumerate(tuple):
        tuple = tuple_assignment(tuple, index, format_ordered(value))
    return tuple
def tuple_assignment(tuple, index, item):
    return tuple[:index] + (item,) + tuple[index + 1:]
def format_ordered(value):
    value_type = type(value)
    if value_type is types.DictType:
        return full_sort_dict(value)
    elif value_type is types.ListType:
        return full_sort_arr(value)
    elif value_type is types.TupleType:
        return full_sort_tuple(value)
    elif value_type is types.InstanceType:
        return full_sort_dict(deepcopy(value.__dict__()))
    elif value_type is types.FunctionType:
        return getsource(value)
    else:
        return value

def convert_to_plottable(result):
    print "Starting new converter"
    return [data.get_plottable() for data in result]
    
def convert_to_csv(result):
    if numpy.all([hasattr(data, 'get_csv') for data in result]):
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
