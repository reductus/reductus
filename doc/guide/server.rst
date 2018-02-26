===================
Server Installation
===================

If you do not have access to the internet, or if the files that you want
to reduce are not available to `reductus`_ then you will need to run a
local version of the server. The reductus *Data* menu will have an
additional *Local* option to access the files on your computer.

To run the server, you will first need to clone the repository
using `git <https://git-scm.com/>`_::

    git clone https://github.com/reflectometry/reductus

Running a server with Docker
----------------------------

The easiest way to get started is to use a `Docker <https://www.docker.com>`_
container.  Prebuilt containers may eventually be available from an automated
build process, but for now you will need to build your own.

Clone the repo, the change directories into the repository and run::

    docker-compose build
    docker-compose up -d

This will result in a trio of docker containers being spun up, one with a
web server for the interface (reflweb), one with the backend calculation
RPC server (reductus) and one with the Redis cache.

Files in `./reflweb/testdata/` will be mapped into the server at /data, for
testing the local file handling. Changes to the python code can be
incorporated into the containers by stopping them, then repeating
the build and up commands above.

To stop::

    docker-compose stop

To access the client, if using the new Docker beta navigate to
http://localhost:8000/reflweb/web_reduction_filebrowser.html
On Windows 7, if using docker-machine, you will have to get the IP of
the default docker install and use that instead of localhost, e.g.,

::

    docker-machine ip default

*In my case it was http://192.168.99.100:8000/reflweb/web_reduction_filebrowser.html*


Running a local server
----------------------

Running in the console is more difficult because it requires a working python
setup with a lot of dependent packages.

Setup using Anaconda
~~~~~~~~~~~~~~~~~~~~

Anaconda python from continuum.io provides packages for many of the numerical
libraries needed by the reduction backend.  The program should run on python
2.7, 3.4+

Simple setup is as follows::

    conda create -n reductus numpy scipy gevent nose docutils h5py pytz werkzeug
    source activate reductus
    pip install uncertainties tinyrpc
    conda install sphinx  # if you need to build the docs

    # if you do not already have git installed
    conda install git

Build in place (if you need off-specular reduction)::

    cd path/to/reductus
    python setup.py build_ext --inplace

In the same directory, test that your environment is working::

    # Mac/Linux console
    ./test.sh

    # Windows
    nosetests --all-modules tests dataflow reflred sansred ospecred

Optional redis server (not available on Windows) for caching downloaded files::

    conda install redis redis-py

Note: setting up a usable compiler environment on Windows can be difficult
(`MinGW compiler <http://mingw-w64.org/>` or
`Microsoft Visual C++ Compiler <https://www.microsoft.com/en-us/download/details.aspx?id=44266>`)
and updating distutils.cfg to point to the right place.  Setting up the
docker containers may be a better option for Windows users.  This is only
needed for rebinning in off-specular reduction, so maybe you can avoid it.

Running the server
~~~~~~~~~~~~~~~~~~

The redis server is used for caching data files and computations.
To start the redis server (optional)::

    # if using anaconda, the next line sets the anaconda path
    source activate reductus
    cd path/to/reductus
    redis-server

If redis is not available, an in-memory cache will be used instead.

In a separate terminal, start the reflweb server::

    # if using anaconda, the next line sets the anaconda path
    source activate reductus
    cd path/to/reductus/reflweb

    # python 3
    PYTHONPATH=.. hug -p 8000 -f server_hug.py
    # browse to http://localhost:8000/static/index.html

    # python 2
    PYTHONPATH=.. python server_tinyrpc.py
    # this will automatically browse to http://localhost:8000

Updating the server
~~~~~~~~~~~~~~~~~~~

To update to the latest version of the code::

    cd path/to/reductus
    # show what you have changed locally
    git status
    # update to the latest version on the server
    git pull
    # Note that this last step may cause conflicts if your git status is
    # not empty or if you have made changes and committed to your local repo.
    # Resolving conflicts is beyond the scope of this document.

Then repeat the build step.

Running a production server
---------------------------

Build the package as usual for running a local server.

Install Apache with load-balancing.

using server_tinyrpc (python2.7)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* install mod_proxy_balancer
* copy contents of `reductus/reflweb/static` under apache home
  (usually in a folder called `reductus`)
* enable the site by adding the following to the apache configuration file

::

  <VirtualHost *:80>
        ServerName reduct.us

        ServerAdmin webmaster@localhost
        DocumentRoot /var/www/html
        Header set Cache-Control "must-revalidate"
        <Proxy "balancer://mycluster">
            BalancerMember "http://localhost:8001"
            BalancerMember "http://localhost:8002"
            BalancerMember "http://localhost:8003"
            BalancerMember "http://localhost:8004"
            BalancerMember "http://localhost:8005"
        </Proxy>
        ProxyPass "/RPC2" "balancer://mycluster"
        ProxyPassReverse "/RPC2" "balancer://mycluster"

        ErrorLog ${APACHE_LOG_DIR}/error.log
        CustomLog ${APACHE_LOG_DIR}/access.log combined
  </VirtualHost>

* start a bunch of rpc servers (in the reflweb folder) with

::

    start_tinyrpc_many.sh 8001 5

This runs `nohup python server_hug.py 8001 > /dev/null 2>&1&` for ports
8001, 8002, *etc.*

* put an entry into crontab such as

::

    @reboot cd path/to/reductus/reflweb && path/to/reductus/reflweb/start_tinyrpc_many.sh 8001 5



using hug (python3.4+)
~~~~~~~~~~~~~~~~~~~~~~

* install mod_proxy_uwsgi
* copy contents of `reductus/reflweb/static` to apache home
  (usually in a folder called `reductus`)
* enable the site by adding the following to the apache configuration file

::

  <VirtualHost *:80>
        ServerAdmin webmaster@localhost
        DocumentRoot /var/www/html
        Header set Cache-Control "must-revalidate"
        <Proxy "balancer://mycluster">
            BalancerMember "uwsgi://localhost:8001"
            BalancerMember "uwsgi://localhost:8002"
            BalancerMember "uwsgi://localhost:8003"
            BalancerMember "uwsgi://localhost:8004"
            BalancerMember "uwsgi://localhost:8005"
        </Proxy>
        ProxyPass "/RPC2" "balancer://mycluster"
        ProxyPassReverse "/RPC2" "balancer://mycluster"

        ErrorLog ${APACHE_LOG_DIR}/error.log
        CustomLog ${APACHE_LOG_DIR}/access.log combined
  </VirtualHost>

* start a bunch of rpc servers (in the reflweb folder) using

::

    start_hug_many.sh 8001 5

This runs `nohup python server_hug.py 8001 > /dev/null 2>&1&` for ports
8001, 8002, *etc.*

* put an entry into crontab such as

::

    @reboot cd path/to/reductus/reflweb && path/to/reductus/reflweb/start_hug_many.sh 8001 5
