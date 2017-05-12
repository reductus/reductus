==================
Client user manual
==================

Overview
========
The user directs a reduction by setting the parameters within the
reduction dataflow template chosen... The data is loaded in the left-most
modules and then flows *to the right* through the reduction steps.

The dataflow diagram at the bottom of the client is made up of
*modules* that are wired together, with *inputs* on the left and
*outputs* on the right.  Inspection of the data flowing into an input
or out of an output can be done by clicking on them, while clicking on a
module itself will bring up a menu of the parameters in the rightmost
panel of the client.

Loading data files
==================
In the `reductus`_ application,
the leftmost modules in any reduction will be the *loaders*, which take a
raw data file (or often, just a URI link to where the raw data file
can be found online) and convert it into a data structure which can be used
by the rest of the reduction system.

Data files are primarily loaded from the NCNR online data repository, which
can be found by Digital Object Identifier `(DOI) 10.18434/T4201B`_

Within that repository, data is organized into folders corresponding to
the instrument on which the data was taken, and then a folder named after
the start month of the reactor cycle in which the data was taken,
and then the (NCNR-issued) `IMS`_ number corresponding to the experiment, e.g.
'ng7/201701/22325' for an experiment on the NG7 reflectometer, during the
beam cycle that began Jan 2017 (2017-01) with IMS number 22325.

The main reduction server can only work with publicly-available data from
the DOI-resolved repository - to work with any other data (local files,
for instance) the user must install a local copy of the reduction server,
as described in :doc:`server`

.. _(DOI) 10.18434/T4201B: https://dx.doi.org/10.18434/T4201B
.. _IMS: https://www-s.nist.gov/NCNR-IMS/login.do

.. toctree::
    :maxdepth: 2
    :numbered:
    :titlesonly:
    :glob:
    :hidden:

    server.rst
