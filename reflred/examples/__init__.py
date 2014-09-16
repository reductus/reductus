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

    key = 'REFLRED_DATA'
    if os.environ.has_key(key):
        # Check for data path in the environment
        path = os.path.join(os.environ[key],data)
        if not os.path.isdir(path):
            raise RuntimeError('Path in environment %s not a directory'%key)

    else:
        # Check for data next to the package.
        try:
            root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        except:
            raise RuntimeError("Could not find sample data")
        path = os.path.join(root,'doc','examples')

    path = os.path.join(path, dir)
    if not os.path.isdir(path):
        raise RuntimeError('Could not find sample data in '+path)
    return path
