from posixpath import basename, join
from copy import copy, deepcopy
from io import BytesIO

ALL_ACTIONS = []

def cache(action):
    """
    Decorator which adds the *cached* attribute to the function.

    Use *@cache* to force caching to always occur (for example, when
    the function references remote resources, vastly reduces memory, or is
    expensive to compute.  Use *@nocache* when debugging a function
    so that it will be recomputed each time regardless of whether or not it
    is seen again.
    """
    action.cached = True
    return action

def nocache(action):
    """
    Decorator which adds the *cached* attribute to the function.

    Use *@cache* to force caching to always occur (for example, when
    the function references remote resources, vastly reduces memory, or is
    expensive to compute.  Use *@nocache* when debugging a function
    so that it will be recomputed each time regardless of whether or not it
    is seen again.
    """
    action.cached = False
    return action

def module(action):
    """
    Decorator which records the action in *ALL_ACTIONS*.

    This just collects the action, it does not otherwise modify it.
    """
    ALL_ACTIONS.append(action)

    # This is a decorator, so return the original function
    return action

#################
# Loader stuff
#################

@cache
@module
def LoadRawUSANS(filelist=None, check_timestamps=True, det_deadtime=7e-6, trans_deadtime=1.26e-5):
    """
    loads a data file into a RawSansData obj and returns that.

    **Inputs**

    filelist (fileinfo[]): Files to open.
    
    check_timestamps (bool): verify that timestamps on file match request

    det_deadtime {main deadtime (s)} (float): main detector deadtime, in seconds

    trans_deadtime {trans deadtime (s)} (float): transmission detector deadtime, in seconds 

    **Returns**

    output (data[]): all the entries loaded.

    2020-01-28 Brian Maranville
    """
    from dataflow.fetch import url_get
    from .loader import readUSANSNexus
    from .usansdata import USansData
    if filelist is None:
        filelist = []
    data = []
    for fileinfo in filelist:
        path, mtime, entries = fileinfo['path'], fileinfo.get('mtime', None), fileinfo.get('entries', None)
        name = basename(path)
        fid = BytesIO(url_get(fileinfo, mtime_check=check_timestamps))
        entries = readUSANSNexus(name, fid)
        
        data.extend(entries)

    return data