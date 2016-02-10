import sys
import BaseHTTPServer, SocketServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer, SimpleJSONRPCRequestHandler
import jsonrpclib.config

import multiprocessing
import webbrowser
import time

try:
    import config
except ImportError:
    import default_config as config

jsonrpclib.config.use_jsonclass = False
HandlerClass = SimpleHTTPRequestHandler
ServerClass  = BaseHTTPServer.HTTPServer
Protocol     = "HTTP/1.0"

if sys.argv[1:]:
    port = int(sys.argv[1])
else:
    port = 8000
#server_address = ('localhost', 0 ) # get next open socket

#HandlerClass.protocol_version = Protocol
#httpd = ServerClass(server_address, HandlerClass)
#http_port = httpd.socket.getsockname()[1]
#print "http port: ", http_port

#sa = httpd.socket.getsockname()
#print "Serving HTTP on", sa[0], "port", sa[1], "..."
## httpd.serve_forever()
#http_process = multiprocessing.Process(target=httpd.serve_forever)
#http_process.start()

class JSONRPCRequestHandler(SimpleJSONRPCRequestHandler):
    """JSON-RPC and documentation request handler class.

    Handles all HTTP POST requests and attempts to decode them as
    XML-RPC requests.

    Handles all HTTP GET requests and interprets them as requests
    for web pages, js, json or css.
    
    Put all static files to be served in 'static' subdirectory.
    """
    
    #rpc_paths = ('/', '/RPC2')
    rpc_paths = () # accept all
    def __init__(self, request, client_address, server):
        #print "init of request handler", request, time.ctime(), self.timeout
        SimpleJSONRPCRequestHandler.__init__(self, request, client_address, server)
    
    def do_OPTIONS(self):
        print 'sending response', time.ctime()
        self.send_response(200)
        #self.send_header('Access-Control-Allow-Origin', 'http://localhost:8000')
        #self.send_header('Access-Control-Allow-Origin', "http://localhost:%d" % (http_port,))           
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.end_headers()

    # Add these headers to all responses
    def end_headers(self):
        self.send_header("Access-Control-Allow-Headers", 
                          "Origin, X-Requested-With, Content-Type, Accept")
        self.send_header("Access-Control-Allow-Origin", "*")
        SimpleJSONRPCRequestHandler.end_headers(self)
    

class ThreadedJSONRPCServer(SocketServer.ThreadingMixIn, SimpleJSONRPCServer):
    pass
    
#server = SimpleJSONRPCServer(('localhost', 8001), encoding='utf8', requestHandler=JSONRPCRequestHandler)
server = ThreadedJSONRPCServer((config.jsonrpc_servername, config.jsonrpc_port), encoding='utf8', requestHandler=JSONRPCRequestHandler)
rpc_port = server.socket.getsockname()[1]
#webbrowser.open_new_tab('http://localhost:%d/index.html?rpc_port=%d' % (http_port, rpc_port))

import h5py, os

def categorize_files(path='./'):
    fns = os.listdir(path)
    fns.sort()
    output = {}
    for fn in fns:
        try:
            f = h5py.File(os.path.join(path, fn))
            for entry in f.keys():
                _name = f[entry].get('DAS_logs/sample/name').value.flatten()[0]
                output.setdefault(_name, {})
                _num = f[entry].get('DAS_logs/trajectoryData/fileNum').value.flatten()[0]
                _scanType = f[entry].get('DAS_logs/trajectoryData/_scanType')
                if _scanType is not None:
                    _scanType = _scanType.value.flatten()[0]
                else:
                    _scanType = 'uncategorized'
                output[_name].setdefault(_scanType, {})
                output[_name][_scanType]['%d:%s' % (_num, entry)] = {'filename': fn, 'entry': entry}
        except:
            pass
            
    #return json.dumps(output)
    return output

def get_file_metadata(pathlist=None):
    if pathlist is None: pathlist = []
    print pathlist
    import urllib
    import urllib2

    url = config.file_helper #'http://ncnr.nist.gov/ipeek/listftpfiles.php'
    values = {'pathlist[]' : pathlist}
    data = urllib.urlencode(values, True)
    req = urllib2.Request(url, data)
    response = urllib2.urlopen(req)
    fn = response.read()
    print fn
    return fn

from dataflow.core import Template, sanitizeForJSON
from dataflow.cache import use_redis
from dataflow import core as df
from dataflow.calc import process_template
from reflred.steps import load, steps
from reflred.refldata import ReflData

use_redis()
load.DATA_SOURCE = config.data_repository
INSTRUMENT_PREFIX = "ncnr.refl."

modules = df.make_modules(steps.ALL_ACTIONS, prefix=INSTRUMENT_PREFIX)
for m in modules:
        df.register_module(m)
loader_name = INSTRUMENT_PREFIX + "super_load"
loader = [m for m in modules if m.id == loader_name][0]

refldata = df.Data(INSTRUMENT_PREFIX+"refldata", ReflData,
                   loaders=[{'function': loader, 'id': 'LoadNeXuS'}])
#df.register_module(loader)
df.register_datatype(refldata)

#from dataflow.modules.load import load_module, load_action
#from reflred.refldata import ReflData
#rdata = Data("ncnr.refl.data", ReflData, loaders=[{'function':load_action, 'id':'LoadNeXuS'}])
#register_module(load_module)
#df.register_datatype(refldata)
    
def refl_load(file_descriptors):
    """ 
    file_descriptors will be a list of dicts like 
    [{"path": "ncnrdata/cgd/201511/21066/data/HMDSO_17nm_dry14.nxz.cgd", "mtime": 1447353278}, ...]
    """
    modules = [{"module": "ncnr.refl.load", "version": "0.1", "config": {}}]
    template = Template("test", "test template", modules, [], "ncnr.magik", version='0.0')
    refl = calc_single(template, {0: {"files": file_descriptors}}, 0, "output")
    return [r._toDict(sanitized=True) for r in refl]

def find_calculated(template_def, config):
    """
    Returns a vector of true/false for each node in the template indicating
    whether that node value has been calculated yet.
    """
    template = Template(**template_def)
    retval = find_calculated(template, config)
    return retval

def calc_terminal(template_def, config, nodenum, terminal_id):
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
    #print "template_def:", template_def, "config:", config
    retval = process_template(template, config, target=(nodenum, terminal_id))
    return sanitizeForJSON(retval.todict())
    
def calc_template(template_def, config):
    """ json-rpc wrapper for process_template """
    template = Template(**template_def)
    retvals = process_template(template, config, target=(None,None))
    output = {}
    for rkey, rv in retvals.items():
        module_id, terminal_id = rkey
        module_key = str(module_id)
        output.setdefault(module_key, {})
        output[module_key][terminal_id] = sanitizeForJSON(rv.todict())
    return output
    
def get_jstree(path='./'):
    files = categorize_files(path)
    categories = ['SPEC','BG','ROCK','SLIT','uncategorized']
    output = {'core': {'data': []}}
    sample_names = files.keys()
    for sample in sample_names:
        samp_out = {"text": sample}
        samp_out['children'] = []
        for cat in categories:
            if not cat in files[sample]: break
            cat_out = {"text": cat, "children": []}
            item_keys = files[sample][cat].keys()
            item_keys.sort()
            for child in item_keys:
                cat_out['children'].append({"text": child, "extra_data": {
                    "filename": files[sample][cat][child]['filename'],
                    "entry": files[sample][cat][child]['entry'],
                    "path": path}});
            samp_out['children'].append(cat_out)
        output['core']['data'].append(samp_out)
    return output 
        
    
server.register_function(get_jstree) # deprecated
server.register_function(get_file_metadata)
server.register_function(refl_load)
server.register_function(calc_terminal)
server.register_function(calc_template)
server.register_function(find_calculated)
server.serve_forever()
print "done serving rpc forever"
#httpd_process.terminate()
