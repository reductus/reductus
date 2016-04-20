import os, sys
import time
import urlparse
from pprint import pprint
import traceback

try:
    import config
except ImportError:
    import default_config as config

import gevent
import gevent.wsgi
import gevent.queue
from tinyrpc.protocols.jsonrpc import JSONRPCProtocol
from tinyrpc.transports.wsgi import WsgiServerTransport
from tinyrpc.server.gevent import RPCServerGreenlets
from tinyrpc.dispatch import RPCDispatcher

#webbrowser.open_new_tab('http://localhost:%d/index.html?rpc_port=%d' % (http_port, rpc_port))

        
if __name__ == '__main__':
    dispatcher = RPCDispatcher()
    transport = WsgiServerTransport(queue_class=gevent.queue.Queue)

    # start wsgi server as a background-greenlet
    wsgi_server = gevent.wsgi.WSGIServer((config.jsonrpc_servername, config.jsonrpc_port), transport.handle)
    gevent.spawn(wsgi_server.serve_forever)
    wsgi_server.update_environ()
    actual_host, actual_port = wsgi_server.address
    print(wsgi_server.address)

    rpc_server = RPCServerGreenlets(
        transport,
        JSONRPCProtocol(),
        dispatcher
    )
    
    import reflweb.api
    from reflweb.api import api_methods, create_instruments
    create_instruments()
    for method in api_methods:
        dispatcher.add_method(getattr(reflweb.api, method), method)
    if config.serve_staticfiles == True:
        from reflweb.httpserver import start_server
        os.chdir("static")
        start_server(config.jsonrpc_servername, config.http_port, rpc_port=actual_port)
    # in the main greenlet, run our rpc_server
    print("serving")
    rpc_server.serve_forever()
    print "done serving rpc forever"
