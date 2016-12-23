import urllib2
import datetime
from posixpath import basename, join, sep
from dataflow.calc import _format_ordered
from dataflow.cache import get_file_cache
import hashlib
#

import pytz

from reflred.iso8601 import seconds_since_epoch

# override this if you want to point these to another place.
# in particular, remove the "local" option if deploying in the cloud!
DATA_SOURCES = {}
DEFAULT_DATA_SOURCE = "ncnr"

def check_datasource(source):
    try:
        datasource = DATA_SOURCES[source]
    except KeyError:
        raise RuntimeError("Need to set dataflow.modules.load.DATA_SOURCES['" + source + "'] first!")
    if isinstance(datasource, str):
        source_url = datasource
    elif isinstance(datasource, dict) and "url" in datasource:
        source_url = datasource["url"]
    elif isinstance(datasource, dict) and "DOI" in datasource:
        from dataflow.modules.doi_resolve import get_target
        source_url = get_target(datasource["DOI"])
        print("resolving DOI %s to url %s" % (datasource["DOI"], source_url))
        datasource["url"] = source_url # cache for next access
    else:
        source_url = ""
        raise RuntimeError("Must have url specified for data source: " + source + " in config.")
    return source_url
        

def url_get(fileinfo):
    path, mtime, entries = fileinfo['path'], fileinfo['mtime'], fileinfo['entries']
    # fingerprint the get, leaving off entries information:
    cache = get_file_cache()
    fileinfo_minimal = {'path': path, 'mtime': mtime}
    config_str = str(_format_ordered(fileinfo_minimal))
    parts = ["url_get", config_str]
    fp = hashlib.sha1(":".join(parts)).hexdigest()
    if cache.exists(fp):
        ret = cache.get(fp)
        print("getting " + path + " from cache!")
    else:
        source = fileinfo.get("source", DEFAULT_DATA_SOURCE)
        name = basename(path)
        source_url = check_datasource(source)
        full_url = join(source_url, path.strip(sep))
        url = None
        print("loading", full_url, name)
        try:
            url = urllib2.urlopen(full_url)
            url_time_struct = url.info().getdate('last-modified')
            t_repo = datetime.datetime(*url_time_struct[:7], tzinfo=pytz.utc)
            t_request = datetime.datetime.fromtimestamp(mtime, pytz.utc)
            if t_request > t_repo:
                print "request mtime = %s, repo mtime = %s"%(t_request, t_repo)
                raise ValueError("Requested mtime is newer than repository mtime for %r"%path)
            elif t_request < t_repo:
                print "request mtime = %s, repo mtime = %s"%(t_request, t_repo)
                raise ValueError("Requested mtime is older than repository mtime for %r"%path)

            ret = url.read()
            print "caching " + path
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

    return { 'path': path, 'mtime': timestamp }


def url_get_list(files=None):
    if files is None: return []
    result = [entry for fileinfo in files for entry in url_get(fileinfo)]
    return result
