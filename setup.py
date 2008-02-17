#!/usr/bin/env python

from numpy.distutils.misc_util import Configuration
from numpy.distutils.core      import setup


def configuration(parent_package='',
                  top_path=None
                  ):
    config = Configuration('reduction', parent_package, top_path)

    config.add_subpackage('lib')
    config.add_data_dir('examples')
    
    return config

# Don't test setup.py
def test(): pass

if __name__ == '__main__':
    setup(**configuration(top_path='').todict())
