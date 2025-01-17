from __future__ import print_function

import re

try:
    import urllib.request as urllib2
except ImportError:
    import urllib2

NIST_DOI_ROOT = "10.18434"
NCNR_DATA_EXT = "T4201B"

NCNR_DATA_DOI = "/".join([NIST_DOI_ROOT, NCNR_DATA_EXT])

def get_DOI_metadata(doi=NCNR_DATA_DOI):
    url = "https://ezid.cdlib.org/id/doi:%s" % (doi,)
    c = urllib2.urlopen(url)
    anvl = c.read()
    metadata = dict(tuple(unescape(v).strip() for v in l.split(":", 1)) \
      for l in anvl.decode("UTF-8").splitlines())
    return metadata

def unescape(s):
    return re.sub("%([0-9A-Fa-f][0-9A-Fa-f])", lambda m: chr(int(m.group(1), 16)), s)

def get_target(doi=NCNR_DATA_DOI):
    # an easier way to get the target value... not tested extensively
    url = "https://dx.doi.org/%s" % (doi,)
    file_pointer = urllib2.urlopen(url)
    return file_pointer.url

if __name__ == '__main__':
    m = get_DOI_metadata()
    print("metadata: %s\n" % m)
    n = get_target()
    print("target: %s" % n)
