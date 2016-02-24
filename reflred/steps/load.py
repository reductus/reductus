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
    path, file_mtime = fileinfo['path'], fileinfo['mtime']
    entries = fileinfo.get('entries', None)
    name = basename(path)
    check_datasource()
    try:
        url = urllib2.urlopen(DATA_SOURCE+path)
        url_mtime = url.info().getdate('last-modified')
        cm = datetime.datetime(*url_mtime[:7], tzinfo=pytz.utc)
        fm = datetime.datetime.fromtimestamp(file_mtime, pytz.utc)
        print cm
        print fm
        if fm < cm:
            raise ValueError("File mtime is newer than repository mtime for %r"%path)
        elif fm > cm:
            raise ValueError("File mtime is older than repository mtime for %r"%path)

        fid = StringIO.StringIO(url.read())
    except urllib2.HTTPError as exc:
        raise ValueError("Could not open %r\n%s"%(path, str(exc)))
    nx_entries = nexusref.load_entries(name, fid, entries = entries)
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
