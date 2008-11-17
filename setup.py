#!/usr/bin/env python

import os.path

from numpy.distutils.misc_util import Configuration
from numpy.distutils.core      import setup


def configuration(parent_package='',
                  top_path=None
                  ):
    config = Configuration('reduction', parent_package, top_path)

    config.add_subpackage('lib')
    config.add_data_dir('examples')

    # Extension reflmodule
    srcpath = os.path.join(config.package_path,'lib')
    sources = [os.path.join(srcpath,s)
               for s in ('reduction.cc','str2imat.c')]

    config.add_extension('_reduction',
                         include_dirs=[srcpath],
                         sources=sources,
                         )


    return config

if __name__ == '__main__':
    setup(**configuration(top_path='').todict())
