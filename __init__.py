# This code is in the public domain
"""
The DANSE Reflectometry data reduction library will use a data flow
architecture consisting of file readers, various corrections, 
plotters and file writers.  Many operations work on sets of files,
so we also provide tools for displaying and selecting files.

Further details available at:

    http://www.reflectometry.org/danse

=== Installation ===

The reflectometry reduction library is not presently released, but is
available by directly accessing the reflectometry svn repository.  Make
sure your machine has gcc, gfortran, svn, python, numpy, matplotlib,
ipython and scipy installed.  Instructions should be available at the
[[http://danse.us|DANSE site]], along with resources for learning Python.

Retrieve the danse repository:

   $ svn co svn://danse.us/reflectometry/trunk reflectometry

Change into the reflectometry directory and type:

   $ python setup.py
   
Run python and load the library:

   $ ipython -pylab
   import reflectometry.reduction as red
   data = red.load(red.datadir+'/ng7/jul04039.ng7')
   print red.summary(data)

Frequent users will want to modify the ipython startup file to execute
the import statement automatically at startup.

File readers for the various instrument formats load the data into a
standard reflectometry data object.

=== Getting Started ===

Once you have the reduction library installed you will need to do
a little bit of reading to see what is available.  The following
is a good order to proceed.

# Reflectometry data format
   help red.refldata
# Loading data and saving results
   help red.formats
# Data transformations
   help red.corrections
# Plotting data
   help red.plots

=== Acknowledgements ===

This work was primarily supported by the NIST Center for Neutron Research,
with minor support from National Science Foundation DMR-0520547.

Contributing developers:
    Paul Kienzle
"""

# Make module headers available to the help system
from reflectometry.reduction \
    import formats, corrections, refldata
from reflectometry.reduction.formats import *
from reflectometry.reduction.corrections import *
from reflectometry.reduction.refldata import *
