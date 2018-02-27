from __future__ import print_function

import sys
import os
from pprint import pprint
import traceback
import json
try:
    from urllib.parse import urlencode
    import urllib.request as urllib2
except ImportError:
    from urllib import urlencode
    import urllib2

import dataflow
from dataflow.core import Template, lookup_instrument, _instrument_registry
from dataflow.cache import use_redis, use_diskcache
from dataflow.calc import process_template
import dataflow.core as df

import dataflow.modules.refl
from dataflow.modules.refl import INSTRUMENT # default
import dataflow.modules.ospec
import dataflow.modules.sans
from dataflow import fetch

try:
    from reflweb import config
except ImportError:
    from reflweb import default_config as config

IS_PY3 = sys.version_info[0] >= 3

# for local and development installs of the server, the .git folder
# will exist in parent (reduction) folder...
if os.path.exists(os.path.join(os.path.dirname(__file__), "..", ".git")):
    import subprocess
    server_git_hash = subprocess.Popen(["git", "rev-parse", "HEAD"], stdout=subprocess.PIPE).stdout.read().strip()
    if IS_PY3: server_git_hash = server_git_hash.decode('ascii')
    server_mtime = int(subprocess.Popen(["git", "log", "-1", "--pretty=format:%ct"], stdout=subprocess.PIPE).stdout.read().strip())
    print("running git rev-parse HEAD", server_git_hash, server_mtime)
else:
    # otherwise for prebuilt systems use the packaged file that was created in setup.py
    import pkg_resources
    if pkg_resources.resource_exists("reflweb", "git_version_hash"):
        server_git_hash = pkg_resources.resource_string("reflweb", "git_version_hash").strip()
        if IS_PY3: server_git_hash = server_git_hash.decode('ascii')
        server_mtime = int(pkg_resources.resource_string("reflweb", "git_version_mtime").strip())
    else:
        server_git_hash = "unknown"
        server_mtime = 0

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

    metadata = {
        "subdirs": subdirs,
        "files": files,
        "pathlist": pathlist,
        "files_metadata": files_metadata
        }
    return metadata

@expose
def get_file_metadata(source="ncnr", pathlist=None):
    if pathlist is None:
        pathlist = []

    if source == "local":
        metadata = local_file_metadata(pathlist)
    else:
        url = config.file_helper_url[source] #'http://ncnr.nist.gov/ipeek/listftpfiles.php'
        values = {'pathlist[]' : pathlist}
        data = urlencode(values, True)
        req = urllib2.Request(url, data.encode('ascii'))
        #print("request", url, data, req, type(req))
        response = urllib2.urlopen(req)
        fn = response.read()
        #print("response", fn)
        metadata = json.loads(fn.decode('ascii'))
        #print("parsed response", metadata)
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
    return retval.todict()

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
    except Exception:
        print("==== template ===="); pprint(template_def)
        print("==== config ===="); pprint(config)
        #traceback.print_exc()
        raise
    if return_type == 'full':
        return retval.todict()
    elif return_type == 'plottable':
        return retval.get_plottable()
    elif return_type == 'metadata':
        return retval.get_metadata()
    elif return_type == 'export':
        # inject git version hash into export data:
        to_export = retval.get_export()
        to_export["server_git_hash"] = server_git_hash
        to_export["server_mtime"] = server_mtime
        return to_export

    raise KeyError(return_type + " not a valid return_type (should be one of ['full', 'plottable', 'metadata', 'export'])")

@expose
def calc_template(template_def, config):
    """ json-rpc wrapper for process_template """
    template = Template(**template_def)
    #print "template_def:", template_def, "config:", config
    try:
        retvals = process_template(template, config, target=(None, None))
    except Exception:
        print("==== template ===="); pprint(template_def)
        print("==== config ===="); pprint(config)
        #traceback.print_exc()
        raise
    output = {}
    for rkey, rv in retvals.items():
        module_id, terminal_id = rkey
        module_key = str(module_id)
        output.setdefault(module_key, {})
        output[module_key][terminal_id] = rv.todict()
    return output

@expose
def list_datasources():
    return config.data_sources

@expose
def list_instruments():
    return list(_instrument_registry.keys())

def create_instruments():

    fetch.DATA_SOURCES = config.data_sources

    if getattr(config, 'use_redis', False):
        redis_params = getattr(config, "redis_params", {})
        use_redis(**redis_params)
    elif getattr(config, 'use_diskcache', False):
        diskcache_params = getattr(config, "diskcache_params", {})
        use_diskcache(**diskcache_params)

    # load refl instrument if nothing specified in config
    instruments = getattr(config, 'instruments', ['refl'])
    for instrument_id in instruments:
        getattr(dataflow.modules, instrument_id).define_instrument()


if __name__ == '__main__':
    create_instruments()
