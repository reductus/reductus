import urllib2
import datetime
import time
from posixpath import basename, join

import pytz

from reflred.iso8601 import seconds_since_epoch

# override this if you want to point these to another place.
# in particular, remove the "local" option if deploying in the cloud!
DATA_SOURCES = {}
DEFAULT_DATA_SOURCE = "ncnr"

def check_datasource(source):
    if not source in DATA_SOURCES:
        raise RuntimeError("Need to set reflred.steps.load.DATA_SOURCES['" + source + "'] first!")

def url_get(fileinfo):
    path, mtime, entries = fileinfo['path'], fileinfo['mtime'], fileinfo['entries']
    source = fileinfo.get("source", DEFAULT_DATA_SOURCE)
    name = basename(path)
    check_datasource(source)
    full_url = join(DATA_SOURCES[source], path)
    print "loading", path, entries
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
    except urllib2.HTTPError as exc:
        raise ValueError("Could not open %r\n%s"%(path, str(exc)))
    finally:
        url.close()
        
    return ret

def find_mtime(path):
    check_datasource()
    try:
        url = urllib2.urlopen(DATA_SOURCE+path)
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
