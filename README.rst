=======================
Reflectometry Reduction
=======================

This project provides tools for reflectometry reduction.

reflred

    A python package for loading, modifying and saving reflectivity data sets.

reflbin

    A C program for rebinning NCNR 2-D ICP data sets.

reflweb

    RPC access to reduction libraries, with javascript frontend (stateless)


To load data from a local store in web reduction, go to
menu->data->add source->local (must be running the server locally,
with the local datastore enabled in config)


Installation and use
--------------------

Method 1: Docker Compose
~~~~~~~~~~~~~~~~~~~~~~~~
This is the easiest way to get started.  Clone the repo, the change directories
into the repository and run::

    docker-compose build
    docker-compose up -d

This will result in a trio of docker containers being spun up, one with a web
server for the interface ('reflweb'), one with the backend calculation RPC
server ('reductus') and one with the Redis cache.

Files in ./reflweb/testdata/ will be mapped into the server at /data, for
testing the local file handling. Changes to the python code can be
incorporated into the containers by stopping them, then repeating the build
and up commands above.

To stop::

    docker-compose stop

To access the client, if using the new Docker beta navigate to
http://localhost:8000/reflweb/web_reduction_filebrowser.html On Windows 7,
if using docker-machine, you will have to get the IP of the default docker
install and use that instead of localhost, e.g. ::

    docker-machine ip default

*In my case it was http://192.168.99.100:8000/reflweb/web_reduction_filebrowser.html*

Method 2: Run directly in console
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
You must have a C99 build environment set up before starting.
Clone the repo, then install (might be a good ideat to make a virtualenv first),
e.g.

::

    python setup.py install

Then start the server with::

    cd reflweb
    python server_flask.py 8002
    
and visit the page http://localhost:8002/static/index.html
