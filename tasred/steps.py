import os
import json
from posixpath import basename, join
from copy import copy, deepcopy
from io import BytesIO
import numpy as np
from time import time,strftime

# Action names
__all__ = [] # type: List[str]

# Action methods
ALL_ACTIONS = [] # type: List[Callable[Any, Any]]

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
    __all__.append(action.__name__)

    # Sort modules alphabetically
    ALL_ACTIONS.sort(key=lambda action: action.__name__)
    __all__.sort()

    # This is a decorator, so return the original function
    return action

@module
def LoadTAS(filelist=None, check_timestamps=True):
    """
    loads a data file into a TAS obj and returns that.

    **Inputs**

    filelist (fileinfo[]): Files to open.
    
    check_timestamps (bool): verify that timestamps on file match request

    **Returns**

    output (raw[]): all the entries loaded.

    2018-04-26 Brian Maranville
    """
    from dataflow.fetch import url_get
    from .readncnr5 import datareader
    if filelist is None:
        filelist = []
    data = []
    for fileinfo in filelist:
        path, mtime, entries = fileinfo['path'], fileinfo.get('mtime', None), fileinfo.get('entries', None)
        name = basename(path)
        fid = BytesIO(url_get(fileinfo, mtime_check=check_timestamps))
        entry = datareader(name)
        entry.readbuffer(name, fid)
        data.append(entry)

    return data
