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

hook_path = os.path.join(".git", "hooks", "post-merge")
if not os.path.exists(hook_path):
    print("creating hook for updating version")
    import stat
    open(hook_path, "w").write("#!/bin/sh\n\ngit rev-parse HEAD > reflweb/git_version_hash\necho 'updated hash'")
    st = os.stat(hook_path)
    os.chmod(hook_path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
 

packages = find_packages(exclude=['reflbin'])

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
    #data_files=[('reflweb', ['reflweb/git_version_hash'])],
    ext_modules=[module_config()],
    # numpy and scipy are requirements, but don't install them with pip
    install_requires=['uncertainties', 'docutils'],
    extras_require = {
        'preinstalled': ['scipy', 'numpy'],
        'masked_curve_fit': ['numdifftools'],
    },
)

# End of file
