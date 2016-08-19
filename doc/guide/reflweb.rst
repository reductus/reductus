=======
ReflWeb
=======

ReflWeb is a reduction client in html+json for composing templates and
displaying the results.  This is the primary interface to data reduction.
ReflWeb can also act as a web service for evaluating reflectometry reduction
templates.

There are some cases where you want to run your own version of the server.
In particular,

* the files you want to reduce are not available in the public repository,

* you want to develop your own reduction steps, or

* you want to load your own type of files.


Installing the Windows binary
-----------------------------

We provide a binary package for Windows containing python and all the
components required to run ReflWeb as a local service.   The latest version
is available at:

    TODO: url of windows ci service (maybe appveyor or shippable?)


Setup using Anaconda
--------------------

Anaconda python from continuum.io provides packages for many of the numerical
libraries needed by the reduction backend.  Simple setup is as follows::

    conda create -n dataflow numpy scipy gevent nose docutils h5py pytz werkzeug
    source activate dataflow
    pip install uncertainties tinyrpc

Download the repository::

    # if you do not already have git install
    conda install git
    git clone https://github.com/reflectometry/reduction

Build and test::

    cd reduction
    python setup.py build_ext --inplace
    nosetests --all-modules reflred
    nosetests --all-modules dataflow

Optional redis server for caching downloaded files::

    conda install redis redis-py

Track changes to the repository::

    cd path/to/reduction
    # show what you have changed locally
    git status
    # update to the latest version on the server
    git pull
    # Note that this last step may cause conflicts if your git status is
    # not empty or if you have made changes and committed to your local repo.
    # Resolving conflicts is beyond the scope of this document.


Running the server
------------------

Redis server is used for caching data files and computations.
To start the redis server::

    # if using anaconda, the next line sets the anaconda path
    source activate dataflow
    cd path/to/reduction
    redis-server

If redis is not available, an in-memory cache will be used instead.

In a separate terminal, start the reflweb server::

    # if using anaconda, the next line sets the anaconda path
    source activate dataflow
    cd path/to/reduction
    cd reflweb
    PYTHONPATH=.. python server_tinyrpc

This will start a local server on 127.0.0.1:8000 and open the browser to that
page.  The menu *Data* item will have an additional *Local* option to access
the files on your computer.


