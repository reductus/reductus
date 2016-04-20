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
    # in the main greenlet, run our rpc_server
    print("serving")
    rpc_server.serve_forever()
    print "done serving rpc forever"
