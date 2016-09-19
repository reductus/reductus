import sys
import threading
import SocketServer
import BaseHTTPServer
import SimpleHTTPServer

class ThreadingSimpleServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    pass
            
HandlerClass = SimpleHTTPServer.SimpleHTTPRequestHandler
ServerClass  = ThreadingSimpleServer

def start_server(host='localhost', port=0, rpc_port=8001, auto_open=True):
    """
    Start the http server after the rpc server is already running,
    to get the dynamic port information.
    
    For a static deploy using e.g. Apache, put a file "rpc_config.json" 
    in the static folder
    """
    server_address = (host, port)
    class MyRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path.endswith('rpc_config.json'):
                response = '{"port": %d, "host": "%s", "load_parallel": true}' % (rpc_port, host)
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.send_header("Content-length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)
            else:
                return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)
    httpd = ServerClass(server_address, MyRequestHandler)
    http_port = httpd.socket.getsockname()[1]
    print("http port: %d" % (http_port,))
    http_process = threading.Thread(target=httpd.serve_forever)
    if auto_open:
        import webbrowser
        webbrowser.open("http://%s:%d/web_reduction_filebrowser.html" % (host, http_port))
    http_process.start()
