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

Method 1: pip install
~~~~~~~~~~~~~~~~~~~~~~

::

    pip install "reductus[all]"

Then start the server with::

    reductus

For the very latest development version use the following::

    pip install "git+https://github.com/reductus/reductus.git#egg=reductus[all]"

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

*In my case it was http://192.168.99.100:8000/webreduce/index.html*


Method 3: Run from repo (development)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Clone the repo, then install in "editable" mode (might be a good idea to make
a virtualenv first)::

    python -m pip install -e .
    python -m pip install -r requirements.txt
    web_gui/run.py

or without install (and with headless flag)::

    PYTHONPATH=. python -m web_gui.run -x

Browse to the URL indicated (probably http://localhost:8002/).

Change the server as needed then restart. The debug mode flag (-d) may make
the restart unnecessary in some cases. Use headless (-x) to avoid starting
a new browser tab each time. The development server is only accessible from
localhost unless the "external" option is used (--external).

To debug external javascript packages (e.g., treejs or d3-science), you
will need to clone the repo and link it into web_gui/webreduce/js, then
update web_gui/webreduce/js/libraries.js to point to the local version rather
than the version on the web.

Update times on the browser may be very slow, particularly when accessing
the NCNR data source. To speed things up, copy `configurations/default.py`
to `configurations/config.py` and modify it to use `"force_IPV4": True`.
You can also set "auto-reload newer files" to false (unchecked) in the
web client.  It is not a sticky setting at the moment, so it gets reset
to checked every time you reload the client page. You can set the default
as `check_mtimes: false` in `web_gui/webreduce/js/menu.js`.

Method 4: Run from repo (production)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After testing your fixes you can check that they work in the production server.

Install node.js and build javascript packages. This step is outlined
in .github/workflows/client_build.yml. If you have changed an external
javascript package you will need to update
web_gui/webreduce/js/libraries_production.js with the path to the
development version, much like you did for the development server.

::

    cd web_gui/webreduce
    npm install
    rm -rf dist
    npm run build
    cd ../..

Then start the server with::

    cd web_gui
    python run.py

and visit the page http://localhost:8002/webreduce/dist/index.html
