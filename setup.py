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

packages = find_packages(exclude=['reflbin', 'reflweb'])

def module_config():
    S = ("reduction.cc","str2imat.c")
    Sdeps = ("rebin.h","rebin2D.h")
    sources = [joinpath('reflred','lib',f) for f in S]
    depends = [joinpath('reflred','lib',f) for f in Sdeps]
    module = Extension('reflred._reduction',
                       sources=sources,
                       depends=depends,
                       include_dirs=[joinpath('reflred','lib')]
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
    include_package_data=True,
    ext_modules=[module_config()],
    # numpy and scipy are requirements, but don't install them with pip
    install_requires=['uncertainties', 'docutils'],
    extras_require = {
        'preinstalled': ['scipy', 'numpy'],
        'masked_curve_fit': ['numdifftools'],
    },
)

# End of file
