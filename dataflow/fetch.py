"""
Need to configure a list of data sources from which to fetch files.  This is
done by setting the global *DATA_SOURCE* variable in the dataflow.fetch module

Each datasources needs to specify the name of the data source, its URL
and a path within the URL which will provide a list of files.  Alternatively,
if the data source has an associated DOI, then specify the DOI.

For example::

    from dataflow import fetch
    fetch.DATA_SOURCES = [
        {
            "name": "ncnr_DOI",
            "DOI": "10.18434/T4201B",
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
import hashlib

try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

import pytz

from .calc import _format_ordered, generate_fingerprint
from .cache import get_file_cache
from .doi_resolve import get_target
from .lib.iso8601 import seconds_since_epoch

# override this if you want to point these to another place.
# in particular, remove the "local" option if deploying in the cloud!

DATA_SOURCES = []
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
    path, mtime, entries = fileinfo['path'], fileinfo.get('mtime', None), fileinfo.get('entries', None)
    # fingerprint the get, leaving off entries information:
    cache = get_file_cache()
    fileinfo_minimal = {'path': path, 'mtime': mtime}
    config_str = str(_format_ordered(fileinfo_minimal))
    fp = generate_fingerprint(("url_get", config_str))
    if cache.exists(fp):
        ret = cache.get(fp)
        print("getting " + path + " from cache!")
    else:
        source = fileinfo.get("source", DEFAULT_DATA_SOURCE)
        name = basename(path)
        source_url = check_datasource(source)
        full_url = join(source_url, urllib2.quote(path.strip(sep), safe='/:'))
        url = None
        print("loading", full_url, name)
        try:
            url = urllib2.urlopen(full_url)
            if mtime_check:
                url_mtime = url.headers['last-modified']
                url_time_struct = time.strptime(url_mtime, '%a, %d %b %Y %H:%M:%S %Z')
                t_repo = datetime.datetime(*url_time_struct[:6], tzinfo=pytz.utc)
                t_request = datetime.datetime.fromtimestamp(mtime, pytz.utc)
                if mtime is None:
                    raise ValueError("timestamp checking enabled but no timestamp provided")
                elif t_request > t_repo:
                    print("request mtime = %s, repo mtime = %s"%(t_request, t_repo))
                    raise ValueError("Requested mtime is newer than repository mtime for %r"%path)
                elif t_request < t_repo:
                    print("request mtime = %s, repo mtime = %s"%(t_request, t_repo))
                    raise ValueError("Requested mtime is older than repository mtime for %r"%path)

            ret = url.read()
            print("caching " + path)
            cache.set(fp, ret)
        except urllib2.HTTPError as exc:
            raise ValueError("Could not open %r\n%s"%(path, str(exc)))
        finally:
            if url is not None:
                url.close()

    return ret

def find_mtime(path):
    check_datasource()
    try:
        url = urllib2.urlopen(DEFAULT_DATA_SOURCE+path)
        mtime = url.info().getdate('last-modified')
    except urllib2.HTTPError as exc:
        raise ValueError("Could not open %r\n%s"%(path, str(exc)))
    mtime_obj = datetime.datetime(*mtime[:7], tzinfo=pytz.utc)
    timestamp = seconds_since_epoch(mtime_obj)

    return {'path': path, 'mtime': timestamp}

def url_get_list(files=None):
    if files is None:
        return []
    result = [entry for fileinfo in files for entry in url_get(fileinfo)]
    return result
