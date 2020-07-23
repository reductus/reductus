#!/usr/bin/env python
import sys
import os

from setuptools import setup, find_packages

if len(sys.argv) == 1:
    sys.argv.append('install')

if sys.argv[1] == 'test':
    from subprocess import call
    sys.exit(call([sys.executable, '-m', 'pytest'] + sys.argv[2:]))

# Create the resource file dataflow/git_revision
if os.system('"{sys.executable}" dataflow/rev.py'.format(sys=sys)) != 0:
    print("setup.py failed to build dataflow/git_revision", file=sys.stderr)
    sys.exit(1)

packages = find_packages(exclude=['reflbin'])

#sys.dont_write_bytecode = False
dist = setup(
    name='reductus',
    version='0.1b2',
    author='Paul Kienzle',
    author_email='paul.kienzle@nist.gov',
    url='https://github.com/reductus/reductus',
    description='Data reduction for neutron scattering',
    long_description=open('README.rst').read(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'License :: Public Domain',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.7',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Chemistry',
        'Topic :: Scientific/Engineering :: Physics',
    ],
    zip_safe=False,
    packages=packages,
    include_package_data=True,
    entry_points = {
        'console_scripts': ['reductus=web_gui.run:main'],
    },
    install_requires=[
        'scipy', 'numpy', 'h5py', 'uncertainties', 'docutils',
        'wheel', 'pytz', 'msgpack-python', 'flask',
        ],
    extras_require={
        'masked_curve_fit': ['numdifftools'],
        },
    tests_require=['pytest'],
    )

# End of file
