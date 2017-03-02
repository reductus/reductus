import os, sys
import time
#import BaseHTTPServer, SocketServer
#from SimpleHTTPServer import SimpleHTTPRequestHandler
#import multiprocessing
#import webbrowser
import SocketServer
import urlparse
from pprint import pprint
import traceback
import json

from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer, SimpleJSONRPCRequestHandler
import jsonrpclib.config

try:
    import config
except ImportError:
    import default_config as config

jsonrpclib.config.use_jsonclass = False

Protocol     = "HTTP/1.0"
homepage = 'web_reduction_filebrowser.html'
# this is specifically to support pyinstaller, which uses this special
# key in sys for the temp directory for single-file executables.
currdir = getattr(sys, "_MEIPASS", os.path.dirname( __file__ ))

## not serving get requests from this for the moment...
#HandlerClass = SimpleHTTPRequestHandler
#ServerClass  = BaseHTTPServer.HTTPServer
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

rpc_config = {}
if getattr(config, 'serve_staticfiles', True) == True: 
    def do_GET(self):
        """Handles the HTTP GET request.

        Interpret all HTTP GET requests as requests for static content.
        """
        # Check that the path is legal
        #if not self.is_rpc_path_valid():
        #    self.report_404()
        #    return
        if self.path.endswith('rpc_config.json'):
            response = json.dumps(rpc_config)
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Content-length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
        else:
            # Parse query data & params to find out what was passed
            parsedParams = urlparse.urlparse(self.path)
            ## don't need the parsed GET query, at least not yet.
            #queryParsed = urlparse.parse_qs(parsedParams.query)
            #docname = os.path.basename(parsedParams.path)
            docname = parsedParams.path.lstrip('/')
            if (docname == "" or docname == "/"):
                docname = homepage
            docpath = os.path.join(currdir, 'static',  *(docname.split("/")))
            if (os.path.exists(docpath)):
                response = open(docpath, 'r').read()
            else:
                self.report_404()
                return
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            if docname.endswith('.js'):
                self.send_header("Content-type", "text/javascript")
            elif docname.endswith('.css'):
                self.send_header("Content-type", "text/css")
            elif docname.endswith('.json'):
                self.send_header("Content-type", "application/json")
            elif docname.endswith('.gif'):
                self.send_header("Content-type", "image/gif")
            elif docname.endswith('.png'):
                self.send_header("Content-type", "image/png")
            elif docname.endswith('.ico'):
                self.send_header("Content-type", "image/x-icon")
            else:
                self.send_header("Content-type", "text/html")
            self.send_header("Content-length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
    
    JSONRPCRequestHandler.do_GET = do_GET

class ThreadedJSONRPCServer(SocketServer.ThreadingMixIn, SimpleJSONRPCServer):
    pass
    
#server = SimpleJSONRPCServer(('localhost', 8001), encoding='utf8', requestHandler=JSONRPCRequestHandler)

#webbrowser.open_new_tab('http://localhost:%d/index.html?rpc_port=%d' % (http_port, rpc_port))

import dataflow
from dataflow.core import Template, sanitizeForJSON, lookup_instrument, _instrument_registry
from dataflow.cache import use_redis
from dataflow.calc import process_template
import dataflow.core as df

import dataflow.modules.refl
from dataflow.modules.refl import INSTRUMENT # default
import dataflow.modules.ospec

from dataflow import fetch
fetch.DATA_SOURCES = config.data_sources

if config.use_redis == True:
    use_redis()

dataflow.modules.refl.define_instrument()
dataflow.modules.ospec.define_instrument()

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

def find_calculated(template_def, config):
    """
    Returns a vector of true/false for each node in the template indicating
    whether that node value has been calculated yet.
    """
    template = Template(**template_def)
    retval = dataflow.calc.find_calculated(template, config)
    return retval

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

def list_datasources():
    return config.data_sources.keys()
    
def list_instruments():
    return _instrument_registry.keys()
        
if __name__ == '__main__':
    server = ThreadedJSONRPCServer((config.jsonrpc_servername, config.jsonrpc_port), encoding='utf8', requestHandler=JSONRPCRequestHandler)
    rpc_port = server.socket.getsockname()[1]
    rpc_config['host'], rpc_config['port'] = server.socket.getsockname()
    server.register_function(get_file_metadata)
    server.register_function(refl_load)
    server.register_function(calc_terminal)
    server.register_function(calc_template)
    server.register_function(get_instrument)
    server.register_function(find_calculated)
    server.register_function(list_datasources)
    server.register_function(list_instruments)
    print "serving on",rpc_port
    server.serve_forever()
    print "done serving rpc forever"
    #httpd_process.terminate()
