#!/usr/bin/env python
import sys, os
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

import subprocess
git_version_hash = subprocess.Popen(["git", "rev-parse", "HEAD"], stdout=subprocess.PIPE).stdout.read()
open("reflweb/git_version_hash", "w").write(git_version_hash) 
server_mtime = subprocess.Popen(["git", "log", "-1", "--pretty=format:%ct"], stdout=subprocess.PIPE).stdout.read()
open("reflweb/git_version_mtime", "w").write(server_mtime) 


packages = find_packages(exclude=['reflbin'])

def module_config():
    source_root = joinpath('dataflow','lib','src')
    sources = ("reduction.cc", "str2imat.c")  ## C API wrapper
    target = 'dataflow.lib._reduction'
    # sources = ("_rebin.pyx")  ## cython wrapper
    # target = 'dataflow.lib._rebin'
    depends = ("rebin.h","rebin2D.h")
    module = Extension(target,
                       sources=[joinpath(source_root, f) for f in sources],
                       depends=[joinpath(source_root, f) for f in depends],
                       include_dirs=[source_root],
                       language="c++",
                       )
    return [module]  ## C API wrapper
    # from Cython.Build import cythonize
    # return cythonize([module])  ## cython wrapper

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
    #data_files=[('reflweb', ['reflweb/git_version_hash'])],
    ext_modules=module_config(),
    # numpy and scipy are requirements, but don't install them with pip
    install_requires=['uncertainties', 'docutils', 'wheel', 'gevent', 'werkzeug', 'tinyrpc', 'pytz', 'h5py', 'redis', 'msgpack-python'],
    extras_require = {
        'preinstalled': ['scipy', 'numpy'],
        'masked_curve_fit': ['numdifftools'],
    },
)

# End of file
