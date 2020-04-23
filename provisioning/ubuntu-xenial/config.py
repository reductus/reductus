#############################################################
# rename or copy this file to config.py if you make changes #
#############################################################

# change this to your fully-qualified domain name to run a 
# remote server.  The default value of localhost will
# only allow connections from the same computer.
#jsonrpc_servername = "h3.umd.edu"
jsonrpc_servername = "localhost"
jsonrpc_port = 8001
http_port = 8000
serve_staticfiles = False
#use_redis = True
use_diskcache = True
diskcache_params = {"size_limit": int(4*2**30), "shards": 5}
use_msgpack = True
data_sources = [
    {
        "name": "ncnr",
        "url": "https://www.ncnr.nist.gov/pub/",
        "start_path": "ncnrdata",
        "file_helper_url": "https://www.ncnr.nist.gov/ipeek/listftpfiles.php"
    },
]
instruments = ["refl", "ospec", "sans"]
