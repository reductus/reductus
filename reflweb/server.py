import sys
import BaseHTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer, SimpleJSONRPCRequestHandler
import multiprocessing
import webbrowser

HandlerClass = SimpleHTTPRequestHandler
ServerClass  = BaseHTTPServer.HTTPServer
Protocol     = "HTTP/1.0"

if sys.argv[1:]:
    port = int(sys.argv[1])
else:
    port = 8000
server_address = ('localhost', 0 ) # get next open socket

HandlerClass.protocol_version = Protocol
httpd = ServerClass(server_address, HandlerClass)
http_port = httpd.socket.getsockname()[1]
print "http port: ", http_port

sa = httpd.socket.getsockname()
print "Serving HTTP on", sa[0], "port", sa[1], "..."
# httpd.serve_forever()
http_process = multiprocessing.Process(target=httpd.serve_forever)
http_process.start()

class JSONRPCRequestHandler(SimpleJSONRPCRequestHandler):
    """JSON-RPC and documentation request handler class.

    Handles all HTTP POST requests and attempts to decode them as
    XML-RPC requests.

    Handles all HTTP GET requests and interprets them as requests
    for web pages, js, json or css.
    
    Put all static files to be served in 'static' subdirectory.
    """
    rpc_paths = ['/', '/RPC2']
    
    def do_OPTIONS(self):           
        self.send_response(200, "ok")       
        # self.send_header('Access-Control-Allow-Origin', 'http://localhost:8000')
        self.send_header('Access-Control-Allow-Origin', "http://localhost:%d" % (http_port,))           
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-type")
        
    # Add these headers to all responses
    def end_headers(self):
        self.send_header("Access-Control-Allow-Headers", 
                         "Origin, X-Requested-With, Content-Type, Accept")
        self.send_header("Access-Control-Allow-Origin", "http://localhost:%d" % (http_port,))
        SimpleJSONRPCRequestHandler.end_headers(self)

server = SimpleJSONRPCServer(('localhost', 0), requestHandler=JSONRPCRequestHandler)
rpc_port = server.socket.getsockname()[1]
webbrowser.open_new_tab('http://localhost:%d/index.html?rpc_port=%d' % (http_port, rpc_port))
server.register_function(pow)
server.register_function(lambda x,y: x+y, 'add')
server.register_function(lambda x: x, 'ping')

import h5py, os, simplejson

def categorize_files(path='./'):
    fns = os.listdir(path)
    print fns
    fns.sort()
    categories = {\
        'Specular': 'SPEC',
        'Background': 'BG', 
        'Rocking': 'ROCK',
        'Slit': 'SLIT'}
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
                output[_name][_scanType]['%d:%s' % (_num, entry)] = {'filename': fn}
        except:
            pass
            
    #return simplejson.dumps(output)
    return output

server.register_function(categorize_files)
server.serve_forever()
print "done serving rpc forever"
httpd_process.terminate()
