# This code is in the public domain
"""
The reflectometry data reduction library will use a data flow
architecture consisting of file readers, various corrections,
plotters and file writers.  Many operations work on sets of files,
so we also provide tools for displaying and selecting files.

Further details available at:

    http://www.reflectometry.org/danse


=== Getting Started ===

Once you have the reduction library installed you will need to do
a little bit of reading to see what is available.  The following
is a good order to proceed::

   import reflred as red
   # Reflectometry data format
   help(red.refldata)
   # Loading data and saving results
   help(red.formats)
   # Data transformations
   help(red.corrections)

=== Acknowledgements ===

This work was developed by the NIST Center for Neutron Research,
with some support from National Science Foundation DMR-0520547.

Contributing developers:
    Paul Kienzle
"""

__version__ = "0.4"

from reflred.refldata import *
from .formats import *
from .corrections import *