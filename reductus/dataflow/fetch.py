"""
Need to configure a list of data sources from which to fetch files.  This is
done by setting the global *DATA_SOURCE* variable in the dataflow.fetch module

Each datasources needs to specify the name of the data source, its URL
and a path within the URL which will provide a list of files.  Alternatively,
if the data source has an associated DOI, then specify the DOI.

For example::

    from reductus.dataflow import fetch
    fetch.DATA_SOURCES = [
        {
            "name": "ncnr_DOI",
            "DOI": "10.18434/T4201B",
        },
        {
            "name": "ncnr",
            "url": "https://ncnr.nist.gov/pub/",
            "start_path": "ncnrdata",
        },
        {
            "name": "charlotte",
            "url": "http://charlotte.ncnr.nist.gov/pub",
            "start_path": "",
        },
        {
            "name": "nice_local",
            "url": "file:///",
            "start_path": "usr/local/nice/server_data/experiments",
        },
        {
            "name": "local",
            "url": "file:///",
            "start_path": "",
        },
    ]

"""

from __future__ import print_function

import datetime
import time
from posixpath import basename, join, sep
import os
import hashlib

import urllib

import pytz

from .calc import _format_ordered, generate_fingerprint
from .cache import get_cache
from .doi_resolve import get_target
from .lib.iso8601 import seconds_since_epoch

# override this if you want to point these to another place.
# in particular, remove the "local" option if deploying in the cloud!

DATA_SOURCES = []
FILE_HELPERS = []
DEFAULT_DATA_SOURCE = "ncnr"


def check_datasource(source):
    datasource = next((x for x in DATA_SOURCES if x['name'] == source), {})
    if datasource == {}:
        raise RuntimeError("Need to set dataflow.modules.load.DATA_SOURCES['" + source + "'] first!")
    if "url" in datasource:
        source_url = datasource["url"]
    elif "DOI" in datasource:
        source_url = get_target(datasource["DOI"])
        print("resolving DOI %s to url %s" % (datasource["DOI"], source_url))
        datasource["url"] = source_url # cache for next access
    else:
        source_url = ""
        raise RuntimeError("Must have url specified for data source: " + source + " in config.")
    return source_url


def url_get(fileinfo, mtime_check=True):
    source = fileinfo.get("source", DEFAULT_DATA_SOURCE)
    path, mtime, entries = fileinfo['path'], fileinfo.get('mtime', None), fileinfo.get('entries', None)
    isLocal = (source == 'local')

    if isLocal:
        # no caching for local files.
        with open(path, 'rb') as localfile:
            ret = localfile.read()

    else:
        import requests
        # fingerprint the get, leaving off entries information:
        cache = get_cache()
        fileinfo_minimal = {'path': path, 'mtime': mtime}
        config_str = str(_format_ordered(fileinfo_minimal))
        fp = generate_fingerprint(("url_get", config_str))
        if cache.file_exists(fp):
            ret = cache.retrieve_file(fp)
            print("getting " + path + " from cache!")
        else:
            name = basename(path)
            source_url = check_datasource(source)
            full_url = join(source_url, urllib.parse.quote(path.strip(sep), safe='/:'))
            print("loading", full_url, name)
            req = None  # Need placeholder for req in case requests.get fails.
            try:
                req = requests.get(full_url)
                req.raise_for_status()
                url_mtime = req.headers.get('last-modified', None)
                url_time_struct = time.strptime(url_mtime, '%a, %d %b %Y %H:%M:%S %Z')
                t_repo = datetime.datetime(*url_time_struct[:6], tzinfo=pytz.utc)

                # Check timestamp if requested and if timestamp is provided
                if mtime_check and mtime is not None:
                    t_request = datetime.datetime.fromtimestamp(mtime, pytz.utc)
                    if t_request != t_repo:
                        print("request mtime = %s, repo mtime = %s"%(t_request, t_repo))
                        compare = "older" if t_request < t_repo else "newer"
                        raise ValueError("Requested mtime is %s than repository mtime for %r"
                                        % (compare, path))

                ret = req.content
                print("caching " + path)
                cache.store_file(fp, ret)

            except requests.HTTPError as exc:
                raise ValueError("Could not open %r\n%s"%(path, str(exc)))
            finally:
                if req is not None:
                    req.close()

    return ret
