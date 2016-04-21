import os, sys
import time
import SocketServer
import urlparse
from pprint import pprint
import traceback
import json

try:
    import config
except ImportError:
    import default_config as config
    
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer, SimpleJSONRPCRequestHandler
import jsonrpclib.config

jsonrpclib.config.use_jsonclass = False

Protocol     = "HTTP/1.0"
homepage = 'web_reduction_filebrowser.html'
# this is specifically to support pyinstaller, which uses this special
# key in sys for the temp directory for single-file executables.
currdir = getattr(sys, "_MEIPASS", os.path.dirname( __file__ ))

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
    
#webbrowser.open_new_tab('http://localhost:%d/index.html?rpc_port=%d' % (http_port, rpc_port))


        
if __name__ == '__main__':
    server = ThreadedJSONRPCServer((config.jsonrpc_servername, config.jsonrpc_port), encoding='utf8', requestHandler=JSONRPCRequestHandler)
    rpc_port = server.socket.getsockname()[1]
    rpc_config['host'], rpc_config['port'] = server.socket.getsockname()
    import api
    from api import api_methods, create_instruments
    create_instruments()
    for method in api_methods:
        server.register_function(getattr(api, method), method)
    print "serving on",rpc_port
    server.serve_forever()
    print "done serving rpc forever"
    #httpd_process.terminate()
