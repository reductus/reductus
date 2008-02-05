#!/usr/bin/env python

from numpy.distutils.misc_util import Configuration
from numpy.distutils.core      import setup


def configuration(parent_package='',
                  top_path=None
                  ):
    config = Configuration('reduction', parent_package, top_path)

    config.add_data_files('*.py')
    
    return config


if __name__ == '__main__':
    setup(**configuration(top_path='').todict())
