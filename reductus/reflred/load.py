from os.path import basename
from io import BytesIO

from reductus.dataflow.fetch import url_get


def load_from_string(filename, data, entries=None, loader=None):
    """
    Load a nexus file from a string, e.g., as returned from url.read().
    """
    with BytesIO(data) as fd:
        entries = loader(filename, fd, entries=entries)
    return entries

def url_load(fileinfo, check_timestamps=True, loader=None):
    path, entries = fileinfo['path'], fileinfo.get('entries', None)
    filename = basename(path)
    content = url_get(fileinfo, mtime_check=check_timestamps)
    if loader is not None:
        return load_from_string(filename, content, entries=entries,
                                loader=loader)
    elif filename.endswith('.raw') or filename.endswith('.ras') or filename.endswith('.xrdml'):
        from . import xrawref
        return load_from_string(filename, content, entries=entries,
                                loader=xrawref.load_entries)
    elif filename.endswith('.nxs.cdr'):
        from . import candor
        return load_from_string(filename, content, entries=entries,
                                loader=candor.load_entries)
    else:
        from . import nexusref
        return load_from_string(filename, content, entries=entries,
                                loader=nexusref.load_entries)

def url_load_list(files=None, check_timestamps=True, loader=None):
    if files is None:
        return []
    result = [
        entry
        for fileinfo in files
        for entry in url_load(
            fileinfo, check_timestamps=check_timestamps, loader=loader,
            )
        ]
    return result

def setup_fetch():
    #from web_gui import default_config
    from reductus.dataflow.cache import set_test_cache
    from reductus.dataflow import fetch

    set_test_cache()
    fetch.DATA_SOURCES = [
        {
            "name": "file",
            "url": "file:///",
            "start_path": "",
        },
        {
            "name": "https",
            "url": "https://",
            "start_path": "",
        },
        {
            "name": "http",
            "url": "http://",
            "start_path": "",
        },
        {
            "name": "nice",
            "url": "file:///",
            "start_path": "usr/local/nice/server_data/experiments",
        },
        {
            "name": "DOI",
            "DOI": "10.18434/T4201B",
        },
        {
            "name": "ncnr",
            "url": "https://ncnr.nist.gov/pub/",
            "start_path": "",
        },
        {
            "name": "charlotte",
            "url": "http://charlotte.ncnr.nist.gov/pub",
            "start_path": "",
        },
    ]

def fetch_uri(uri, loader=None):
    import os.path

    if '://' not in uri:
        # some sort of filename...
        source, path = 'local', os.path.realpath(os.path.expanduser(uri))
    else:
        source, path = uri.split('://')
    entries = url_load(
        {'source': source, 'path': path},
        check_timestamps=False,
        loader=loader,
        )
    return entries
