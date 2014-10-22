"""
Support files for the application.

This includes tools to help with testing, documentation, command line
parsing, etc. which are specific to this application, rather than general
utilities.
"""
import os

def get_data_path(dir=""):
    """
    Locate the examples directory.
    """
    from os.path import dirname, abspath, join as joinpath, isdir

    key = 'REFLRED_DATA'
    if os.environ.has_key(key):
        # Check for data path in the environment
        path = os.environ[key]
        if not isdir(path):
            raise RuntimeError('Path in environment %s not a directory'%key)

    else:
        # Check for data next to the package.
        try:
            root = dirname(dirname(dirname(abspath(__file__))))
        except:
            raise RuntimeError("Could not find sample data")
        path = joinpath(root,'doc','examples')

    path = joinpath(path, dir)
    if not isdir(path):
        raise RuntimeError('Could not find sample data in '+path)
    return path
