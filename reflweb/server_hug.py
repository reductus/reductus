"""
To serve with uwsgi:

uwsgi --http 0.0.0.0:8002 --wsgi-file server_hug.py --callable __hug_wsgi__

To serve with hug:

hug -p 8001 -f server_hug.py
(then visit http://localhost:8001/static/index.html in your browser)

"""

import os, sys
import traceback

import hug
from falcon import HTTP_500
import msgpack as msgpack_converter

try:
    import config
except ImportError:
    import default_config as config

RPC_ENDPOINT = '/RPC2'

@hug.default_input_format(content_type='application/msgpack')
def msgpack_input_format(body, **kwargs):
    """Takes msgpack formatted data, converting it into native Python objects"""
    return msgpack_converter.unpackb(body.read(), encoding='utf-8')

from hug.format import content_type

@content_type('application/msgpack')
def msgpack(content, request=None, response=None, **kwargs):
    """MSGPACK"""
    if hasattr(content, 'read'):
        return content

    if isinstance(content, tuple) and getattr(content, '_fields', None):
        content = {field: getattr(content, field) for field in content._fields}
    return msgpack_converter.dumps(content)

# include static serving, which won't get used by backend rpc calculation servers...
@hug.static('/static')
def static_files():
    return ('./static',)

@hug.exception(Exception, output=msgpack)
def handle_exception(exception, response):
    response.status = HTTP_500
    return {'exception': repr(exception)}

import api
api.create_instruments()
router = hug.route.API(__name__)
for method in api.api_methods:
    mfunc = getattr(api, method)
    router.get('/'+method, prefixes=RPC_ENDPOINT)(mfunc)
    router.post('/'+method, prefixes=RPC_ENDPOINT, output=msgpack)(mfunc)
