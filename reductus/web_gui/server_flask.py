"""
To serve with uwsgi:

uwsgi --http 0.0.0.0:8002 --manage-script-name --mount /=server_flask:app

To serve with python:

python server_flask.py 8002
(then visit http://localhost:8002 in your browser)

"""
import os, sys, posixpath
import traceback
import logging
import pkg_resources

from flask import Flask, request, make_response, redirect, send_from_directory
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
import msgpack as msgpack_converter
import json
import mimetypes
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("text/html", ".html")
mimetypes.add_type("application/json", ".json")
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/javascript", ".mjs")
mimetypes.add_type("image/png", ".png")
mimetypes.add_type("image/svg+xml", ".svg")

def create_app(config=None):
    from reductus.web_gui import api

    RPC_ENDPOINT = '/RPC2'
    STATIC_FOLDER = "webreduce"
    STATIC_PATH = pkg_resources.resource_filename('reductus.web_gui', 'webreduce/')
    DIST_PATH = "dist"
    CLIENT = "index.html"

    app = Flask(__name__, static_folder=STATIC_PATH, static_url_path='/webreduce')
    CORS(app)
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

    @app.route('/')
    def root():
        if os.path.exists(os.path.join(STATIC_PATH, DIST_PATH, CLIENT)):
            return redirect(posixpath.join(STATIC_FOLDER, DIST_PATH, CLIENT))
        else:
            return redirect(posixpath.join(STATIC_FOLDER, CLIENT))

    @app.route('/robots.txt')
    def static_from_root():
        return send_from_directory(app.static_folder, request.path[1:])

    @app.errorhandler(Exception)
    def handle_error(e):
        code = 500
        if isinstance(e, HTTPException):
            code = e.code
        content = {'exception': repr(e), 'traceback': traceback.format_exc()}
        logging.info(content['traceback'])
        response = make_response(msgpack_converter.packb(content, use_bin_type=True), code)
        response.headers['Content-Type'] = "application/msgpack"
        return response

    def wrap_method(mfunc):
        def wrapper(*args, **kwargs):
            if request.method == "GET":
                real_kwargs = request.args.to_dict()
            else:
                real_kwargs = request.get_json() if request.get_data() else {}
            return_type = request.headers.get("Accept", "application/msgpack")
            if return_type not in ["application/json", "application/msgpack"]:
                # fall back to application/json for debugging GET requests
                return_type = "application/json"
            if return_type not in ["application/json", "application/msgpack"]:
                code = 406
                content = {'exception': 
                    'no valid Accept return type provided. \
                    (leave unspecified or use one of application/json or application/msgpack)'}
                return_type = "application/json"
                packed = json.dumps(content)
            else:
                content = mfunc(*args, **real_kwargs)
                if return_type == "application/msgpack":
                    packed = msgpack_converter.packb(content, use_bin_type=True)
                else:
                    packed = json.dumps(content)

            response = make_response(packed)
            response.headers['Content-Type'] = return_type
            return response
        return wrapper

    api.initialize(config)

    for method in api.api_methods:
        mfunc = getattr(api, method)
        wrapped = wrap_method(mfunc)
        path = posixpath.join(RPC_ENDPOINT, method)
        shortpath = posixpath.join("/", method)
        app.add_url_rule(path, path, wrapped, methods=["POST", "GET"])
        app.add_url_rule(shortpath, shortpath, wrapped, methods=["POST", "GET"])

    from reductus.rev import print_revision
    print_revision()

    return app

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    port = 8002
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    app = create_app()
    app.run(port=port)
