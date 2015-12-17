import urllib2
import datetime
import StringIO
from os.path import basename

import pytz

from reflred.formats import nexusref

DATA_SOURCE = "http://ncnr.nist.gov/pub/"

def url_load(fileinfo):
    path, file_mtime = fileinfo['path'], fileinfo['mtime']
    name = basename(path)
    try:
        url = urllib2.urlopen(DATA_SOURCE + path)
        url_mtime = url.info().getdate('last-modified')
        cm = datetime.datetime(*url_mtime[:7], tzinfo=pytz.utc)
        fm = datetime.datetime.fromtimestamp(file_mtime, pytz.utc)
        if fm < cm:
            raise ValueError("File mtime is newer than repository mtime for %r"%path)
        if fm > cm:
            raise ValueError("File mtime is older than repository mtime for %r"%path)

        fid = StringIO.StringIO(url.read())
    except urllib2.HTTPError as exc:
        raise ValueError("Could not open %r\n%s"%(path, str(exc)))
    nx_entries = nexusref.load_entries(name, fid)
    fid.close()
    url.close()
    return nx_entries

def url_load_list(filelist):
    result = [entry for fileinfo in filelist for entry in url_load(fileinfo)]
    return result
