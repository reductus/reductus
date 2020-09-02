============================
Neutron Scattering Reduction
============================


.. image:: https://img.shields.io/pypi/v/reductus.svg
    :target: https://pypi.org/project/reductus/

.. image:: https://img.shields.io/pypi/pyversions/reductus.svg
    :target: https://pypi.org/project/reductus/

.. image:: https://travis-ci.org/reductus/reductus.svg?branch=master
    :target: https://travis-ci.org/reductus/reductus

This project provides tools for data reduction for neutron and xray scattering.

reflred

    A python package for loading, modifying and saving reflectivity data sets.

ospecred

    A python package for loading, modifying and saving off-specular reflectivity data sets.

sansred

    A python package for loading, modifying and saving small-angle neutron scattering (SANS) data sets.

web_gui

    RPC access to reduction libraries, with javascript frontend (stateless)


To load data from a local store in web reduction, go to
menu->data->add source->local (must be running the server locally,
with the local datastore enabled in config)


Installation and use
--------------------

Method 1: pypi install
~~~~~~~~~~~~~~~~~~~~~~

::

    pip install reductus

Then start the server with::

    reductus


Method 2: Docker Compose
~~~~~~~~~~~~~~~~~~~~~~~~
This is the easiest way to get started.  Clone the repo, the change directories
into the repository and run::

    docker-compose build
    docker-compose up -d

This will result in a trio of docker containers being spun up, one with a web
server for the interface ('web_gui'), one with the backend calculation RPC
server ('reductus') and one with the Redis cache.

Files in ./web_gui/testdata/ will be mapped into the server at /data, for
testing the local file handling. Changes to the python code can be
incorporated into the containers by stopping them, then repeating the build
and up commands above.

To stop::

    docker-compose stop

To access the client, if using the new Docker beta navigate to
http://localhost:8000/web_gui/web_reduction_filebrowser.html On Windows 7,
if using docker-machine, you will have to get the IP of the default docker
install and use that instead of localhost, e.g. ::

    docker-machine ip default

*In my case it was http://192.168.99.100:8000/web_gui/web_reduction_filebrowser.html*

Method 3: Clone github repo and build, run directly in console
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Clone the repo, then install (might be a good idea to make a virtualenv first),
e.g.

::

    python setup.py install

Maybe need to install the web client::

    cd web_gui/reduce
    wget https://github.com/reductus/reductus/releases/download/sid/dist.zip
    unzip dist.zip

Then start the server with::

    cd web_gui
    python server_flask.py 8002

and visit the page http://localhost:8002/static/index.html

Method 4: Run from repo
~~~~~~~~~~~~~~~~~~~~~~~
Clone the repo.

Install node.js and build javascript packages. This step are outlined
in .github/workflows/client_build.yml.

::

    cd web_gui/webreduce
    npm install -g parcel-bundler
    rm -rf dist
    npm run build --if-present
    cd ../..

Then start the server. There is no compiled code, so no need to install,
but you do need to put the repo on the python path::

    PYTHONPATH=. web_gui/run.py
