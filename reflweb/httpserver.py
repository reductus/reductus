import sys
import threading

try:
    import socketserver
    from http import server as baseserver
    simpleserver = baseserver
except ImportError:
    import SocketServer as socketserver
    import BaseHTTPServer as baseserver
    import SimpleHTTPServer as simpleserver

IS_PY3 = sys.version_info[0] >= 3
if IS_PY3:
    def bytes_to_str(s):
        # type: (AnyStr) -> str
        return s.decode('utf-8') if isinstance(s, bytes) else s  # type: ignore
    def str_to_bytes(s):
        # type: (AnyStr) -> str
        return s.encode('utf-8') if isinstance(s, str) else s  # type: ignore
else:  # python 2.x
    def bytes_to_str(s):
        # type: (AnyStr) -> str
        return s
    str_to_bytes = bytes_to_str


class ThreadingSimpleServer(socketserver.ThreadingMixIn, baseserver.HTTPServer):
    pass
            
HandlerClass = simpleserver.SimpleHTTPRequestHandler
ServerClass  = ThreadingSimpleServer

def start_server(host='localhost', port=0, rpc_port=8001, auto_open=True):
    """
    Start the http server after the rpc server is already running,
    to get the dynamic port information.
    
    For a static deploy using e.g. Apache, put a file "rpc_config.json" 
    in the static folder
    """
    server_address = (host, port)
    class MyRequestHandler(simpleserver.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path.endswith('rpc_config.json'):
                response = b'{"port": %d, "host": "%s", "load_parallel": true}' % (rpc_port, str_to_bytes(host))
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.send_header("Content-length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)
            else:
                return simpleserver.SimpleHTTPRequestHandler.do_GET(self)
    httpd = ServerClass(server_address, MyRequestHandler)
    http_port = httpd.socket.getsockname()[1]
    print("http port: %d" % http_port)
    http_process = threading.Thread(target=httpd.serve_forever)
    if auto_open:
        import webbrowser
        webbrowser.open("http://%s:%d/web_reduction_filebrowser.html" % (host, http_port))
    http_process.start()
