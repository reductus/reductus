import datetime
from os.path import basename
try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

import pytz

from dataflow.lib.iso8601 import seconds_since_epoch
from dataflow.fetch import url_get

from . import nexusref
from . import xrawref

DATA_SOURCES = {}

def check_datasource(source):
    if not source in DATA_SOURCES:
        raise RuntimeError("Need to set reflred.steps.load.DATA_SOURCES['" + source + "'] first!")

def url_load(fileinfo):
    path, mtime, entries = fileinfo['path'], fileinfo['mtime'], fileinfo['entries']
    filename = basename(path)
    content = url_get(fileinfo)
    if filename.endswith('.raw') or filename.endswith('.ras'):
        return xrawref.load_from_string(filename, content, entries=entries)
    else:
        return nexusref.load_from_string(filename, content, entries=entries)

def find_mtime(path, source="ncnr"):
    check_datasource(source)
    try:
        url = urllib2.urlopen(DATA_SOURCES[source]+path)
        mtime = url.info().getdate('last-modified')
    except urllib2.HTTPError as exc:
        raise ValueError("Could not open %r\n%s"%(path, str(exc)))
    mtime_obj = datetime.datetime(*mtime[:7], tzinfo=pytz.utc)
    timestamp = seconds_since_epoch(mtime_obj)

    return {'path': path, 'mtime': timestamp, 'source': source, 'entries': None}


def url_load_list(files=None):
    if files is None:
        return []
    result = [entry for fileinfo in files for entry in url_load(fileinfo)]
    return result
