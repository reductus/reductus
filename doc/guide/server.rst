===================
Server Installation
===================

First step is to clone the repository using `git <https://git-scm.com/>`_::

    git clone https://github.com/reflectometry/reduction

Method 1: Docker Compose
------------------------

The easiest way to get started is to use a `Docker <https://www.docker.com>`_
container.  Prebuilt containers may eventually be available from an automated
build process, but for now you will need to build your own.

Clone the repo, the change directories into the repository and run::

    docker-compose build
    docker-compose up -d

This will result in a trio of docker containers being spun up, one with a
web server for the interface ('reflweb'), one with the backend calculation
RPC server ('reductus') and one with the Redis cache.

Files in ./reflweb/testdata/ will be mapped into the server at /data, for
testing the local file handling. Changes to the python code can be
incorporated into the containers by stopping them, then repeating
the build and up commands above.

To stop::

    docker-compose stop

To access the client, if using the new Docker beta navigate to
http://localhost:8000/reflweb/web_reduction_filebrowser.html
On Windows 7, if using docker-machine, you will have to get the IP of
the default docker install and use that instead of localhost, e.g. ::

    docker-machine ip default

*In my case it was http://192.168.99.100:8000/reflweb/web_reduction_filebrowser.html*


Method 2: Run directly in console
---------------------------------

Running in the console is more difficult because it requires a working python
setup with a lot of dependent packages.

Setup using Anaconda
~~~~~~~~~~~~~~~~~~~~

Anaconda python from continuum.io provides packages for many of the numerical
libraries needed by the reduction backend.  The program should run on python
2.7, 3.4 and 3.5.

Simple setup is as follows::

    conda create -n dataflow numpy scipy gevent nose docutils h5py pytz werkzeug
    source activate dataflow
    pip install uncertainties tinyrpc
    conda install sphinx  # if you need to build the docs

    # if you do not already have git installed
    conda install git

Build in place (if you need off-specular reduction)::

    cd reduction
    python setup.py build_ext --inplace

In the same directory, test that your environment is working::

    # mac/linux console
    ./test.sh

    # windows
    nosetests --all-modules tests dataflow reflred sansred ospecred

Optional redis server for caching downloaded files::

    conda install redis redis-py

Note: setting up a usable compiler environment on Windows can be difficult
(`MinGW compiler <http://mingw-w64.org/>` or
`Microsoft Visual C++ Compiler <https://www.microsoft.com/en-us/download/details.aspx?id=44266>`)
and updating distutils.cfg to point to the right place.  Setting up the
docker containers may be a better option for windows users.  This is only
needed for rebinning in off-specular reduction, so maybe you can avoid it.

Running the server
~~~~~~~~~~~~~~~~~~

Redis server is used for caching data files and computations.
To start the redis server (optional)::

    # if using anaconda, the next line sets the anaconda path
    source activate dataflow
    cd path/to/reduction
    redis-server

If redis is not available, an in-memory cache will be used instead.

In a separate terminal, start the reflweb server::

    # if using anaconda, the next line sets the anaconda path
    source activate dataflow
    cd path/to/reduction/reflweb

    # python 3
    PYTHONPATH=.. hug -p 8000 -f server_hug.py
    # browse to http://localhost:8000/static/index.html

    # python 2
    PYTHONPATH=.. python server_tinyrpc.py
    # this will automatically browse to http://localhost:8000

The menu *Data* item will have an additional *Local* option to access
the files on your computer.

Updating the server
~~~~~~~~~~~~~~~~~~~

To update to the latest version of the code::

    cd path/to/reduction
    # show what you have changed locally
    git status
    # update to the latest version on the server
    git pull
    # Note that this last step may cause conflicts if your git status is
    # not empty or if you have made changes and committed to your local repo.
    # Resolving conflicts is beyond the scope of this document.

Then repeat the build step.
