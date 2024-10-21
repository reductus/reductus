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

# pip dependencies
install_requires = [
    'scipy', 'numpy', 'uncertainties', 'docutils',
    'pytz',
]
extras_require = {
    'server': ['msgpack', 'flask', 'flask-cors', 'requests'],
    'masked_curve_fit': ['numdifftools'],
    'nexus_files': ['h5py']
    }
extras_require['all'] = sum(extras_require.values(), [])
tests_require = ['pytest']

#sys.dont_write_bytecode = False
dist = setup(
    name='reductus',
    version='0.9.1',
    author='Paul Kienzle',
    author_email='paul.kienzle@nist.gov',
    url='https://github.com/reductus/reductus',
    description='Data reduction for neutron scattering',
    long_description_content_type="text/x-rst",
    long_description=open('README.rst').read(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
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
    install_requires=install_requires,
    extras_require=extras_require,
    tests_require=tests_require,
    )

# End of file
