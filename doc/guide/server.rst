===================
Server Installation
===================

Installing the Windows binary
-----------------------------

We provide a binary package for Windows containing python and all the
components required to run ReflWeb as a local service.   The latest version
is available at:

    TODO: url of windows ci service (maybe appveyor or shippable?)


Setup using Anaconda
--------------------

Anaconda python from continuum.io provides packages for many of the numerical
libraries needed by the reduction backend.  The program should run on python
2.7, 3.4 and 3.5.

Simple setup is as follows::

    conda create -n dataflow numpy scipy gevent nose docutils h5py pytz werkzeug
    source activate dataflow
    pip install uncertainties tinyrpc
    conda install sphinx  # if you need to build the docs

Download the repository::

    # if you do not already have git install
    conda install git
    git clone https://github.com/reflectometry/reduction

Build::

    cd reduction
    python setup.py build_ext --inplace


(in the same directory, test if desired)::

    nosetests --all-modules reflred
    nosetests --all-modules dataflow

Optional redis server for caching downloaded files::

    conda install redis redis-py

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

Updating the server
-------------------
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

Running a production server
---------------------------
Using Apache, with load-balancing:

using server_tinyrpc (python2.7)
++++++++++++++++++++++++++++++++

* install mod_proxy_balancer
* copy contents of reduction/reflweb/static to apache home somewhere (usually a folder called reductus)
* enable a site with this configuration, e.g.:

::

  <VirtualHost *:80>
        ServerName h3.umd.edu

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

* start a bunch of rpc servers with (in the reflweb folder)::

  start_tinyrpc_many.sh 8001 5

* this runs `nohup python server_tinyrpc.py 8001 > /dev/null 2>&1&` etc.
* a sample crontab entry is 
::
  
  @reboot cd /home/bbm/reduction/reflweb && /home/bbm/reduction/reflweb/start_tinyrpc_many.sh 8001 5



using hug (python3.4+)
++++++++++++++++++++++++++++++++

* install mod_proxy_uwsgi
* copy contents of reduction/reflweb/static to apache home somewhere (usually a folder called reductus)
* enable a site with this configuration:

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

* start a bunch of rpc servers using (in the reflweb folder)::

  start_hug_many.sh 8001 5

* this runs `nohup python server_tinyrpc.py 8001 > /dev/null 2>&1&` etc.
* a sample crontab entry looks like
::

  @reboot cd /home/bbm/reduction/reflweb && /home/bbm/reduction/reflweb/start_hug_many.sh 8001 5

