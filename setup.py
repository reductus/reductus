#!/usr/bin/env python

import os.path

from numpy.distutils.misc_util import Configuration
from numpy.distutils.core      import setup


def configuration():
    config = Configuration(package_name='reflred', package_path='reflred')

    # Extension reflmodule
    srcpath = os.path.join(config.package_path,'lib')
    sources = [os.path.join(srcpath,s)
               for s in ('reduction.cc','str2imat.c')]
    depends = [os.path.join(srcpath,s)
               for s in ('rebin.h', 'rebin2D.h')]

    config.add_extension('_reduction',
                         include_dirs=[srcpath],
                         depends=depends,
                         sources=sources,
                         )

    config.set_options(quiet=True) # silence debug/informational messages

    # Add subpackages (top level name spaces) and data directories.
    # Note that subpackages may have their own setup.py to drill down further.
    # Note that 'dream' is not a subpackage in our setup (no __init__.py as
    # this name may already be used), so we define our dream substructure here.
    config.add_data_dir(os.path.join('doc', 'examples'))
    config.add_subpackage('reflred')
    config.add_subpackage('ospecred')

    for line in open('reflred/__init__.py').readlines():
        if (line.startswith('__version__')):
            exec(line.strip())
            config.version = __version__
            break

    return config

if __name__ == '__main__':
    setup(**configuration().todict())
