"""
To serve with uwsgi:

uwsgi --http 0.0.0.0:8002 --manage-script-name --mount /=server_flask:app

To serve with python:

python server_flask.py 8002
(then visit http://localhost:8002/static/index.html in your browser)

"""

import os, sys, posixpath
import traceback

from flask import Flask, request, make_response
from werkzeug.exceptions import HTTPException
import msgpack as msgpack_converter

try:
    import config
except ImportError:
    import default_config as config

RPC_ENDPOINT = '/RPC2'

app = Flask(__name__)

@app.errorhandler(Exception)
def handle_error(e):
    code = 500
    if isinstance(e, HTTPException):
        code = e.code
    content = {'exception': repr(e), 'traceback': traceback.format_exc()}
    return make_response(msgpack_converter.dumps(content), code)

def wrap_method(mfunc):
    def wrapper(*args, **kwargs):
        real_kwargs = request.get_json() if request.get_data() else {}
        content = mfunc(*args, **real_kwargs)
        response = make_response(msgpack_converter.dumps(content))
        response.headers['Content-Type'] = 'application/msgpack'
        return response
    return wrapper

import api
api.create_instruments()
for method in api.api_methods:
    mfunc = getattr(api, method)
    wrapped = wrap_method(mfunc)
    path = posixpath.join(RPC_ENDPOINT, method)
    shortpath = posixpath.join("/", method)
    app.add_url_rule(path, path, wrapped, methods=["POST"])
    app.add_url_rule(shortpath, shortpath, wrapped, methods=["POST"])

if __name__ == '__main__':
    port = 8002
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    app.run(port=port)
