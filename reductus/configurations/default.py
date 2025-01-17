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

config = {
    # ssl_args for https serving the rpc
    # ssl_args = {"keyfile": None, "certfile": None}

    # Cache engines are diskcache, redis, or memory if not specified
    "cache": {
        "engine": "",
        "params": {"size_limit": int(4*2**30)}
    },
    "data_sources": [
        {
            "name": "local",
            "url": "file:///",
            "start_path": "",
        },
        {
            "name": "ncnr",
            "url": "https://ncnr.nist.gov/pub/",
            "start_path": "ncnrdata",
            "file_helper_url": "https://ncnr.nist.gov/ncnrdata/listftpfiles_pg.php",
        },
        {
            "name": "charlotte",
            "url": "http://charlotte.ncnr.nist.gov/pub",
            "start_path": "",
            "file_helper_url": "http://charlotte.ncnr.nist.gov/ncnrdata/listftpfiles_json.php",
        },
        # set start_path for local files to usr/local/nice/server_data/experiments
        # for instrument installs
        {
            "name": "ncnr_DOI",
            "DOI": "10.18434/T4201B",
            "file_helper_url": "https://ncnr.nist.gov/ncnrdata/listncnrdatafiles_json.php"
        },
    ],
    
    # if not set, will instantiate all instruments.
    "instruments": ["refl", "ospec", "sans", "vsans", "gans"]
}
