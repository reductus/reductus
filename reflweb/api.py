import os, sys
import time
from pprint import pprint
import traceback

import dataflow
from dataflow.core import Template, sanitizeForJSON, lookup_instrument, _instrument_registry
from dataflow.cache import use_redis
from dataflow.calc import process_template
import dataflow.core as df

import dataflow.modules.refl
from dataflow.modules.refl import INSTRUMENT # default
import dataflow.modules.ospec

try:
    import config
except ImportError:
    import default_config as config

api_methods = []

def expose(action):
    """
    Decorator which adds function to the list of methods to expose in the api.
    """
    api_methods.append(action.__name__)
    return action

def sorted_ls(path, show_hidden=False):
    mtime = lambda f: os.stat(os.path.join(path, f)).st_mtime
    return list(sorted(filter(lambda x: os.path.exists(os.path.join(path, x)) and not x.startswith("."), os.listdir(path)), key=mtime))

def local_file_metadata(pathlist):
    # only absolute paths are supported:
    path = os.path.join(os.sep, *pathlist)
    dirlisting = sorted_ls(path)
    subdirs = []
    files = []
    files_metadata = {}
    for di in dirlisting:
        d = os.path.join(path, di)
        if os.path.isdir(d):
            subdirs.append(di)
        elif os.path.isfile(d):
            files.append(di)
            files_metadata[di] = {"mtime": int(os.path.getmtime(d))}
        else:
            # you've probably hit an unfulfilled path link or something.
            pass
            
    metadata = {"subdirs": subdirs, "files": files, "pathlist": pathlist, "files_metadata": files_metadata} 
    return metadata 

@expose
def get_file_metadata(source="ncnr", pathlist=None):
    if pathlist is None: pathlist = []
    import urllib
    import urllib2
    import json
    
    if source == "local":
        metadata = local_file_metadata(pathlist)
    else:
        url = config.file_helper_url[source] #'http://ncnr.nist.gov/ipeek/listftpfiles.php'
        values = {'pathlist[]' : pathlist}
        data = urllib.urlencode(values, True)
        req = urllib2.Request(url, data)
        #print "request",url,data
        response = urllib2.urlopen(req)
        fn = response.read()
        metadata = json.loads(fn)
        #print "response",json.loads(fn)
        # this converts json to python object, then the json-rpc lib converts it 
        # right back, but it is more consistent for the client this way:
        
    return metadata

@expose
def get_instrument(instrument_id=INSTRUMENT):
    """
    Make the instrument definition available to clients
    """
    instrument = lookup_instrument(instrument_id)
    return instrument.get_definition()

def refl_load(file_descriptors):
    """ 
    file_descriptors will be a list of dicts like 
    [{"path": "ncnrdata/cgd/201511/21066/data/HMDSO_17nm_dry14.nxz.cgd", "mtime": 1447353278}, ...]
    """
    modules = [{"module": "ncnr.refl.load", "version": "0.1", "config": {}}]
    template = Template("test", "test template", modules, [], "ncnr.magik", version='0.0')
    retval = process_template(template, {0: {"files": file_descriptors}}, target=(0, "output"))
    return sanitizeForJSON(retval.todict())

@expose
def find_calculated(template_def, config):
    """
    Returns a vector of true/false for each node in the template indicating
    whether that node value has been calculated yet.
    """
    template = Template(**template_def)
    retval = dataflow.calc.find_calculated(template, config)
    return retval

@expose
def calc_terminal(template_def, config, nodenum, terminal_id, return_type='full'):
    """ json-rpc wrapper for calc_single
    template_def = 
    {"name": "template_name",
     "description": "template description!",
     "modules": ["list of modules"],
     "wires": ["list of wires"],
     "instrument": "facility.instrument_name",
     "version": "2.7.3"
    }
    
    where modules in list of modules above have structure:
    module = 
    {"module": "facility.instrument_name.module_name",
     "version": "0.3.2"
    }
    
    and wires have structure:
    [["wire_start_module_id:wire_start_terminal_id", "wire_end_module_id:wire_end_terminal_id"],
     ["1:output", "2:input"],
     ["0:xslice", "3:input"]
    ]
    
    config = 
    [{"param": "value"}, ...]
    
    nodenum is the module number from the template for which you wish to get the calculated value
    
    terminal_id is the id of the terminal for that module, that you want to get the value from
    (output terminals only).
    """
    template = Template(**template_def)
    #print "template_def:", template_def, "config:", config, "target:",nodenum,terminal_id
    #print "modules","\n".join(m for m in df._module_registry.keys())
    try:
        retval = process_template(template, config, target=(nodenum, terminal_id))
    except:
        print "==== template ===="; pprint(template_def)
        print "==== config ===="; pprint(config)
        traceback.print_exc()
        raise
    if return_type == 'full':
        return sanitizeForJSON(retval.todict())
    elif return_type == 'plottable':
        return sanitizeForJSON(retval.get_plottable())
    elif return_type == 'metadata':
        return sanitizeForJSON(retval.get_metadata())
    elif return_type == 'export':
        return retval.get_export()
    else:
        raise KeyError(return_type + " not a valid return_type (should be one of ['full', 'plottable', 'metadata', 'export'])")

@expose
def calc_template(template_def, config):
    """ json-rpc wrapper for process_template """
    template = Template(**template_def)
    #print "template_def:", template_def, "config:", config
    try:
        retvals = process_template(template, config, target=(None,None))
    except:
        print "==== template ===="; pprint(template_def)
        print "==== config ===="; pprint(config)
        traceback.print_exc()
        raise
    output = {}
    for rkey, rv in retvals.items():
        module_id, terminal_id = rkey
        module_key = str(module_id)
        output.setdefault(module_key, {})
        output[module_key][terminal_id] = sanitizeForJSON(rv.todict())
    return output

@expose
def list_datasources():
    return config.data_sources.keys()

@expose    
def list_instruments():
    return _instrument_registry.keys()

def create_instruments():
    
    from dataflow.modules import load
    load.DATA_SOURCES = config.data_sources

    if config.use_redis == True:
        use_redis()
    
    # load refl instrument if nothing specified in config
    instruments = getattr(config, 'instruments', ['refl']) 
    for instrument_id in instruments:
        getattr(dataflow.modules, instrument_id).define_instrument()
    
if __name__ == '__main__':
    create_instruments()
