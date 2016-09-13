import sys
########################################################################################
# Move this file to your webroot for deploy, and make an alias in apache site config:
#   AddHandler wsgi-script wsgi     Order allow,deny     Allow from all
#   WSGIScriptAlias /RPC2 /var/www/html/reflweb/reflweb_rpc.wsgi
########################################################################################

#activate_env=os.path.expanduser("/home/bbm/.virtualenvs/reduction/bin/activate_this.py")
#execfile(activate_env, dict(__file__=activate_env))

from werkzeug.wrappers import Response, Request

sys.path.append("path/to/reduction/reflweb_install")
from wsgi_app_init import dispatcher, protocol

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
