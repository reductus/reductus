import urllib2
import datetime
import time
import StringIO
from os.path import basename

import pytz

from reflred.formats import nexusref
from reflred.iso8601 import seconds_since_epoch

DATA_SOURCE = None

def check_datasource():
    if DATA_SOURCE is None:
        raise RuntimeError("Need to set reflred.steps.load.DATA_SOURCE first!")

def url_load(fileinfo):
    path, mtime, entries = fileinfo['path'], fileinfo['mtime'], fileinfo['entries']
    name = basename(path)
    check_datasource()
    print "loading", path, entries
    try:
        url = urllib2.urlopen(DATA_SOURCE+path)
        url_time_struct = url.info().getdate('last-modified')
        t_repo = datetime.datetime(*url_time_struct[:7], tzinfo=pytz.utc)
        t_request = datetime.datetime.fromtimestamp(mtime, pytz.utc)
        if t_request > t_repo:
            print "request mtime = %s, repo mtime = %s"%(t_request, t_repo)
            raise ValueError("Requested mtime is newer than repository mtime for %r"%path)
        elif t_request < t_repo:
            print "request mtime = %s, repo mtime = %s"%(t_request, t_repo)
            raise ValueError("Requested mtime is older than repository mtime for %r"%path)

        fid = StringIO.StringIO(url.read())
    except urllib2.HTTPError as exc:
        raise ValueError("Could not open %r\n%s"%(path, str(exc)))
    nx_entries = nexusref.load_entries(name, fid, entries=entries)
    fid.close()
    url.close()
    return nx_entries

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


def url_load_list(files=None):
    if files is None: return []
    result = [entry for fileinfo in files for entry in url_load(fileinfo)]
    return result
