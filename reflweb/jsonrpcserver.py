from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer, SimpleJSONRPCRequestHandler

class GetJSONRPCRequestHandler(SimpleJSONRPCRequestHandler):
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
        self.send_header('Access-Control-Allow-Origin', '*')           
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-type")
        
    # Add these headers to all responses
    def end_headers(self):
        self.send_header("Access-Control-Allow-Headers", 
                         "Origin, X-Requested-With, Content-Type, Accept")
        self.send_header("Access-Control-Allow-Origin", "http://localhost:8000")
        SimpleJSONRPCRequestHandler.end_headers(self)

server = SimpleJSONRPCServer(('localhost', 8080), requestHandler=GetJSONRPCRequestHandler)
server.register_function(pow)
server.register_function(lambda x,y: x+y, 'add')
server.register_function(lambda x: x, 'ping')
server.serve_forever()
