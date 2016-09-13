from tinyrpc.dispatch import RPCDispatcher
from tinyrpc.protocols.jsonrpc import JSONRPCProtocol

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
