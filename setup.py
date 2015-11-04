#!/usr/bin/env python
import sys
from os.path import join as joinpath, dirname
import re

if len(sys.argv) == 1:
    sys.argv.append('install')

# Use our own nose-based test harness
if sys.argv[1] == 'test':
    from subprocess import call
    sys.exit(call([sys.executable, 'test.py'] + sys.argv[2:]))

#sys.dont_write_bytecode = True

from setuptools import setup, Extension, find_packages

version = None
for line in open(joinpath("reflred","__init__.py")):
    if "__version__" in line:
        version = line.split('"')[1]

packages = find_packages(exclude=['reflbin','ospecred','reflweb'])

def module_config():
    S = ("reduction.cc","str2imat.c")
    Sdeps = ("rebin.h","rebin2D.h")
    sources = [joinpath('reduction','lib',f) for f in S]
    depends = [joinpath('reduction','lib',f) for f in Sdeps]
    module = Extension('reflred._reduction',
                       sources=sources,
                       depends=depends,
                       )
    return module

#sys.dont_write_bytecode = False
dist = setup(
    name='reflred',
    version=version,
    author='Paul Kienzle',
    author_email='paul.kienzle@nist.gov',
    url='http://github.com/reflectometry/reduction/reflred',
    description='Data reduction for 1-D reflectometry',
    long_description=open('README.rst').read(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'License :: Public Domain',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Chemistry',
        'Topic :: Scientific/Engineering :: Physics',
    ],
    packages=packages,
    # needs scipy and numpy as well, but these have binary bits that don't
    # do well with pip install
    #install_requires=['six', 'uncertainties', 'numdifftools'],
)

# End of file
