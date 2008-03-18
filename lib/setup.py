#!/usr/bin/env python

from __future__ import nested_scopes

import os
import sys
from os.path import join,  dirname, exists


def configuration(parent_package='',
                  top_path=None
                  ):
    from numpy.distutils.misc_util import Configuration
    config = Configuration('', parent_package, top_path)

    # Extension reflmodule
    sources = [join(config.package_path,s)
               for s in ('reduction.cc','str2imat.c')]

    config.add_extension('_reduction',
                         include_dirs=[config.package_path],
                         sources=sources,
                         )

    return config


if __name__ == '__main__':
    from numpy.distutils.core      import setup
    setup(**configuration(top_path='').todict())
