"""
To serve with uwsgi:

uwsgi --http 0.0.0.0:8002 --manage-script-name --mount /=server_flask:app

To serve with python:

python server_flask.py
(then visit http://localhost:5000/static/index.html in your browser)

"""

import os, sys, posixpath
import traceback

from flask import Flask, request, make_response
import msgpack as msgpack_converter

try:
    import config
except ImportError:
    import default_config as config

RPC_ENDPOINT = '/RPC2'

app = Flask(__name__)

def wrap_method(mfunc):
    def wrapper(*args, **kwargs):
        real_kwargs = request.get_json() if request.get_data() else {}
        resp = make_response(msgpack_converter.dumps(mfunc(*args, **real_kwargs)))
        resp.headers['Content-Type'] = 'application/msgpack'
        return resp
    return wrapper

import api
api.create_instruments()

wrapped_funcs = {}
for method in api.api_methods:
    mfunc = getattr(api, method)
    wrapped = wrap_method(mfunc)
    path = posixpath.join(RPC_ENDPOINT, method)
    app.add_url_rule(path, path, wrapped, methods=["GET", "POST"])
    
if __name__ == '__main__':
    app.run()
    

