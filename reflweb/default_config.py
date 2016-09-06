#############################################################
# rename or copy this file to config.py if you make changes #
#############################################################

# change this to your fully-qualified domain name to run a 
# remote server.  The default value of localhost will
# only allow connections from the same computer.
#
# for remote (cloud) deployments, it is advised to remove 
# the "local" data_sources item below, and to serve static
# files using a standard webserver
#
# if use_redis is False, server will use in-memory cache.

# TODO: Convert this to JSON file in web-accesible ('static')
# directory.  

jsonrpc_servername = "localhost"
jsonrpc_port = 8001
# ssl_args for https serving the rpc
ssl_args = {"keyfile": None, "certfile": None}
http_port = 8000
serve_staticfiles = True
use_redis = True
data_sources = {
    "ncnr": "http://ncnr.nist.gov/pub/",
    "local": "file:///"
}
file_helper_url = {
    "ncnr": "http://ncnr.nist.gov/ipeek/listftpfiles.php"
}
instruments = ["refl"]
