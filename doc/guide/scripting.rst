===============================
Running a template from ipython
===============================

There are a couple of use cases for running a template in the ipython
console or a jupyter notebook.  One is when you are trying to debug
problems with the components, and you want the flexibility to look at
the inputs available to it.  Another is when you are developing a new
kind of transformation and you want to grab the output of the preceeding
steps on an existing reduction.

You may want to fetch the data from the reduction server either running
locally or remotely, or you may want to skip the server and run the
components directly.  For now we will assume you are computing locally.

Setting up the development environment
--------------------------------------

We will assume you have a python environment, such as Anaconda for windows
or Mac, and that you have a C compiler available ("conda install mingw" or
download and install "Microsoft C++ for Python" on windows; on mac you
need to install X Code and install the X Code command line tools ---
instructions discoverable in your favourite search engine).  You will
also need git (download and install git-bash for windows; mac comes with it).

You will need to have a local copy of the sources on your machine::

     $ cd preferred/working/directory
     $ git clone https://github.com/reflectometry/reductus.git
     $ cd reductus
     $ python setup.py build_ext --inplace

With mingw, you will need to add "--ccompiler=mingw32" to the last line.
This will allow you to run directly from the local repositories without
installing. (not sure

Preparing python
----------------

Configure a python session to run the template::

     $ cd ~/path/to/reductus
     $ ipython --pylab
     >>> import web_gui.config

It either case, you first need to create the template and save it to
your disk.  To load the template into python, type the following::

    >>> import json
    >>> from pprint import pprint
    >>> template = json.load(open('~/Downloads/some_template.json'))
    >>> pprint(json)

Scan through the list of nodes to find the one containing the data of
interest.  This could be tricky since different nodes sometimes have
the same name.   You should be able to guess the correct one by looking
at the y value of the node position.  You will need to count from the
start of the node list until you see the node you are interested.  For
example, it might be node 9.  Confirm the count by typing::

    template['modules'][9]

You can now compute the value of that node.  You should first turn
on
