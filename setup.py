#!/usr/bin/env python

import os
import sys

from numpy.distutils.core import setup
from numpy.distutils.misc_util import Configuration

def configuration(parent_package='', top_path=None):
    config = Configuration('reflred', parent_package, top_path)
    config.set_options(quiet=True) # silence debug/informational messages

    # Add subpackages (top level name spaces) and data directories.
    # Note that subpackages may have their own setup.py to drill down further.
    # Note that 'dream' is not a subpackage in our setup (no __init__.py as
    # this name may already be used), so we define our dream substructure here.
    config.add_data_dir(os.path.join('doc', 'examples'))
    config.add_subpackage('reflred')

    for line in open('reflred/__init__.py').readlines():
        if (line.startswith('__version__')):
            exec(line.strip())
            config.version = __version__
            break

    return config


if __name__ == '__main__':
    if len(sys.argv) == 1: sys.argv.append('install')
    setup(**configuration(top_path='').todict())
