import datetime
from os.path import basename
from io import BytesIO
try:
    import urllib.request as urllib2
except ImportError:
    import urllib2


import pytz

from dataflow.lib.iso8601 import seconds_since_epoch
from dataflow.fetch import url_get

from . import nexusref
from . import xrawref
from . import candor

DATA_SOURCES = {}

def _fetch_url_uncached(url):
    # type: (str) -> str
    import urllib2
    try:
        fd = urllib2.urlopen(url)
        ret = fd.read()
    finally:
        fd.close()
    return ret


def fetch_url(url, url_cache="/tmp"):
    """
    Fetch a file from a url.

    The content of the file will be cached in */tmp/_path_to_file.ext* for
    the url *http://path/to/file.ext*.  If *url_cache* is None, then no caching
    is performed.  Set *url_cache* to the private cache directory if you don't
    want the files cleaned by the tmp reaper.
    """
    from urlparse import urlparse
    import os

    if url_cache is None:
        return _fetch_url_uncached(url)

    cached_path = os.path.join(url_cache, urlparse(url).path.replace('/', '_'))
    if os.path.exists(cached_path):
        with open(cached_path) as fd:
            ret = fd.read()
    else:
        ret = _fetch_url_uncached(url)
        with open(cached_path, 'wb') as fd:
            fd.write(ret)
    return ret


def load_from_string(filename, data, entries=None, loader=None):
    """
    Load a nexus file from a string, e.g., as returned from url.read().
    """
    fd = BytesIO(data)
    entries = loader(filename, fd, entries=entries)
    fd.close()
    return entries


def load_from_uri(uri, entries=None, url_cache="/tmp", loader=None):
    """
    Load a file from disk or from http://, https:// or file://.

    Remote files are cached in *url_cache*.  Use None to fetch without caching.

    *loader(name, [entries])* does the actual loading.
    """
    if uri.startswith('file://'):
        return loader(uri[7:], entries=entries)
    elif uri.startswith('http://') or uri.startswith('https://'):
        filename = os.path.basename(uri)
        data = fetch_url(uri, url_cache=url_cache)
        return load_from_string(filename, data, entries=entries, loader=loader)
    else:
        return loader(uri, entries=entries)


def check_datasource(source):
    if not source in DATA_SOURCES:
        raise RuntimeError("Need to set reflred.steps.load.DATA_SOURCES['" + source + "'] first!")

def url_load(fileinfo, check_timestamps=True):
    path, mtime, entries = fileinfo['path'], fileinfo.get('mtime', None), fileinfo.get('entries', None)
    filename = basename(path)
    content = url_get(fileinfo, mtime_check=check_timestamps)
    if filename.endswith('.raw') or filename.endswith('.ras'):
        return load_from_string(filename, content, entries=entries,
                                loader=xrawref.load_entries)
    elif filename.endswith('.nxs.cdr'):
        return load_from_string(filename, content, entries=entries,
                                loader=candor.load_entries)
    else:
        return load_from_string(filename, content, entries=entries,
                                loader=nexusref.load_entries)

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


def url_load_list(files=None, check_timestamps=True):
    if files is None:
        return []
    result = [entry for fileinfo in files for entry in url_load(fileinfo, check_timestamps=check_timestamps)]
    return result
