import sys, os
import SocketServer
import SimpleHTTPServer
import BaseHTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer, SimpleJSONRPCRequestHandler, SimpleJSONRPCDispatcher
import socket

import urlparse

import jsonrpclib.config

import webbrowser

jsonrpclib.config.use_jsonclass = False

currdir = os.path.dirname( __file__ )

class JSONRPCRequestHandler(SimpleHTTPRequestHandler, SimpleJSONRPCRequestHandler):
    """JSON-RPC and documentation request handler class.

    Handles all HTTP POST requests and attempts to decode them as
    XML-RPC requests.

    Handles all HTTP GET requests and interprets them as requests
    for web pages, js, json or css.
    
    Put all static files to be served in 'static' subdirectory.
    """
    #rpc_paths = ('/', '/RPC2')
    rpc_paths = () # accept all
    
    def do_OPTIONS(self):
        self.send_response(200, "ok")       
        #self.send_header('Access-Control-Allow-Origin', 'http://localhost:8000')
        #self.send_header('Access-Control-Allow-Origin', "http://localhost:%d" % (http_port,))           
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.end_headers()
        self.connection.shutdown(0)
        
    # Add these headers to all responses
    def end_headers(self):
        self.send_header("Access-Control-Allow-Headers", 
                         "Origin, X-Requested-With, Content-Type, Accept")
        self.send_header("Access-Control-Allow-Origin", "*") #"http://localhost:%d" % (server_address[1],))
        SimpleJSONRPCRequestHandler.end_headers(self)
        

import thread

class Browser2DPlot:
    def __init__(self, data=None):
        self.server = SimpleJSONRPCServer(('localhost', 0), encoding='utf8', requestHandler=JSONRPCRequestHandler)
        self.rpc_port = self.server.socket.getsockname()[1]
        self.data = data
        self.server.register_function(self.get_plottable, 'get_plottable')
        self.server.register_function(self.kill_server, 'shutdown') 
        webbrowser.open_new_tab('http://localhost:%d/sliceplot.html' % (self.rpc_port,))
        self.server.serve_forever()
        
    def get_plottable(self):
        return self.data
    
    def kill_server(self):
        thread.start_new_thread(self.server.shutdown, ())

def test():
    data = open("testdata/offspec_qxqz.json").read()
    plotter = Browser2DPlot(data)

