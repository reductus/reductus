from tinyrpc.dispatch import RPCDispatcher
from tinyrpc.protocols.jsonrpc import JSONRPCProtocol
from werkzeug.wrappers import Response, Request

try:
    import config
except ImportError:
    import default_config as config

dispatcher = RPCDispatcher()
protocol = JSONRPCProtocol()
import api
from api import api_methods, create_instruments
create_instruments()
for method in api_methods:
    dispatcher.add_method(getattr(api, method), method)

def application(environ, start_response):
    request = Request(environ)
    access_control_headers = {
        'Access-Control-Allow-Methods': 'POST',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type, X-Requested-With, Accept, Origin'
    }
    if request.method == 'OPTIONS':
        response = Response(headers=access_control_headers)
    elif request.method == 'POST':
        # message is encoded in POST, read it...
        message = request.stream.read()
        request = protocol.parse_request(message)
        result = dispatcher.dispatch(request)
        # send reply
        response = Response(result.serialize(), headers=access_control_headers)
    else:
        # nothing else supported at the moment
        response = Response('Only POST supported', 405)

    return response(environ, start_response)
