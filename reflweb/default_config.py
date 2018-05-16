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
# ssl_args = {"keyfile": None, "certfile": None}
http_port = 8000
serve_staticfiles = True
#use_redis = True
use_diskcache = True
diskcache_params = {"size_limit": int(4*2**30), "shards": 5}
data_sources = [
    {
        "name": "local",
        "url": "file:///",
        "start_path": "",
    },
    {
        "name": "ncnr",
        "url": "http://ncnr.nist.gov/pub/",
        "start_path": "ncnrdata",
    },
    {
        "name": "charlotte",
        "url": "http://charlotte.ncnr.nist.gov/pub",
        "start_path": "",
    },
    # set start_path for local files to usr/local/nice/server_data/experiments
    # for instrument installs
    #{
    #    "name": "ncnr_DOI",
    #    "DOI": "10.18434/T4201B",
    #},
]
file_helper_url = {
    "charlotte": "http://charlotte.ncnr.nist.gov/ipeek/listftpfiles.php",
    "ncnr": "https://ncnr.nist.gov/ipeek/listftpfiles.php",
    "ncnr_DOI": "https://ncnr.nist.gov/ipeek/listncnrdatafiles.php"
}
instruments = ["refl", "ospec", "sans"]
