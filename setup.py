#!/usr/bin/env python
import sys, os
from os.path import join as joinpath, dirname
import re

if len(sys.argv) == 1:
    sys.argv.append('install')

if sys.argv[1] == 'test':
    from subprocess import call
    sys.exit(call([sys.executable, '-m', 'pytest'] + sys.argv[2:]))
#    #sys.exit(call(['test.sh'] + sys.argv[2:]))

#sys.dont_write_bytecode = True

from setuptools import setup, Extension, find_packages

import subprocess
git_version_hash = subprocess.Popen(["git", "rev-parse", "HEAD"], stdout=subprocess.PIPE).stdout.read()
open("reflweb/git_version_hash", "wb").write(git_version_hash)
server_mtime = subprocess.Popen(["git", "log", "-1", "--pretty=format:%ct"], stdout=subprocess.PIPE).stdout.read()
open("reflweb/git_version_mtime", "wb").write(server_mtime)

packages = find_packages(exclude=['reflbin'])

#sys.dont_write_bytecode = False
dist = setup(
    name='reductus',
    version='0.1b2',
    author='Paul Kienzle',
    author_email='paul.kienzle@nist.gov',
    url='http://github.com/reductus/reductus',
    description='Data reduction for neutron scattering',
    long_description=open('README.rst').read(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'License :: Public Domain',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Chemistry',
        'Topic :: Scientific/Engineering :: Physics',
    ],
    zip_safe=False,
    packages=packages,
    include_package_data=True,
    entry_points = {
        'console_scripts': ['reductus=reflweb.run:main'],
    },
    install_requires=[
        'scipy', 'numpy', 'h5py', 'uncertainties', 'docutils', 'wheel', 'pytz', 'msgpack-python', 'flask'],
    extras_require={
        'masked_curve_fit': ['numdifftools'],
        },
    tests_require = ['pytest'],
    )

# End of file
