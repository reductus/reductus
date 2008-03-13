# This program is public domain
"""
Reflectometry reduction file formats.

=== File formats ===
Supported formats are:

     ICP on NCNR NG-1 and NG-7
     NeXus on SNS Liquids and Magnetic

Sample data for some of these formats is available in datadir.  In ipython
type the following:

    import reflectometry.reduction as red
    ls $red.datadir

=== Loading files ===

Data files are loaded using:
 
    data = red.load('path/to/file')
    
This creates a reflectometry data object in memory whose fields can be
accessed directly (see below).  Note that some data formats can store
multiple measurements in the file, so the returned value may be a list
of data objects.

Once loaded, data fields can be accessed using data.field for general
data, or data.component.field for specific components such as detectors
or slits.  Within ipython, type data.<Tab> to see the fields available.
See help(refldata) for a complete description of all the fields.

Some datasets are huge and can take substantial time to load.  Instead 
of loading the entire dataset, you can use:

    data = red.loadmeta('path/to/file')

to load just the metadata, and later use:

    data.load()

to load the data itself.  Again, loadmeta() returns a list of data
objects if there are multiple datasets in the file.  Note that the
metadata can be wrong if for example an NCNR ICP run was aborted
before all the measurements were complete.  data.load() will return
the points which were actually measured.

=== Saving files ===  [Not implemented]

Saving files is the inverse of loading:

    red.save(data, 'filename.ext')
    red.save(data, 'filename')  # .ext defaults to .dat
    red.save(data, 'arbitraryfilename', format='.ext')  #

This saves the contents of data into the file of type '.ext'.  Alternatively,
the data can be saved to an arbitrary filename if the format='.ext' 
keyword is given.  If the extension is missing, '.dat' is used.  

If no filename is given, then 

The save function can be used to convert from one file format to
another.  This is can be useful for comparing the results of reduction
from different reduction programs.

After normalizing by monitor, the data may be in various states of reduction:

* refl - specular reflectivity, Q dQ R dR wavelength
* spec - specular intensity, not yet corrected by slits
* back - background estimate 
* slit - intensity measurement for slit corrections
* rock - slice through the Qx-Qz plane
* qxqz - 2-D data

It is up to the individual formats to determine how they will store this
information.

With no file extension, an ascii format is used with a .dat extension.
This is a multicolumn formation with a header defined by:

    # field value
    # field value
    ...
    # columns Q dQ R dR wavelength
    0.001   0.000121  0.98596  0.00212  4.75
    ...
    0.02    0.00215  1.2356e-7  2.195e-8  4.75

The columns included will be different for the different states of
reduction, in particular, enough information needs to be preserved
so that intensity scans can be aligned with the corresponding specular
intensity.

With no filename, the file is saved to a file of the same name as the
original, but with an extension of e.g., .refl.dat if it is reflectivity
data.

Other common output formats include .xml for an xml version of the
multicolumn ascii format, following the standards for reduced SANS
data, and .nxs for an NeXus/HDF5 versions of the same information.

Note that the reduction process combines many files into one.  Storing
details such as the sample description from all these files is impractical,
and so only one 'head' file will be chosen.  This will be the file on 
which all the corrections have been applied, or the file with the lowest
sequence number if multiple files have been combined.  When saving to
the NeXus format, all the metadata from the head file will be preserved.

=== Registering new formats ===

New formats can be created and register using

    red.register_format(loader)

See the register_format documentation for a description of the loader
function interface.

"""

import os.path
#from reflectometry.reduction.
from registry import ExtensionRegistry
__all__ = ['loadmeta','load','formats','register_format','datadir']

datadir = os.path.join(os.path.dirname(__file__),'examples')


# Shared registry for all reflectometry formats
registry = ExtensionRegistry()
def loadmeta(file, format=None):
    """
    Load the measurement description from the file but not the data.
    Use measurement.load() to load the data for each measurement.

    Returns a single measurement if there is only one measurement in 
    the file, otherwise it returns a list of measurements.
    
    Use formats() to list available file formats.
    """
    measurements = registry.load(file, format=format)
    return measurements[0] if len(measurements)==1 else measurements

def load(file, format=None):
    """
    Load the reflectometry measurement description and the data.  
    

    Returns a single measurement if there is only one measurement in 
    the file, otherwise it returns a list of measurements.
    
    Use formats() to list available file formats.
    """
    measurements = registry.load(file, format=format)
    for data in measurements: data.load() # Load the dataset
    return measurements[0] if len(measurements)==1 else measurements

def formats():
    return registry.formats()

def register_format(ext,loader):
    """
    Register loader for a file extension.

    For each normal file extension for the format, call
        register_format('.ext',loader)
    You should also register the format name as
        register_format('name',loader)
    This allows the user to recover the specific loader using:
        load('path',format='name')

    The loader has the following signature:
    
        [data1, data2, ...] = loader('path/to/file.ext')

    The loader should raise an exception if file is not of the correct
    format.  When encountering an exception, load will try another loader
    in reverse order in which the they were registered.  If all loaders
    fail, the exception raised by the first loader will be forwarded to
    the application.
    
    The returned objects should support the ReflData interface and
    include enough metadata so that guess_intent() can guess the 
    kind and extent of the measurement it contains.  The metadata need
    not be correct, if for example the length and the actual values of
    the motors are not known until the file is completely read in.
    
    After initialization, the application will make a call to data.load()
    to read in the complete metadata.  In order to support large datasets,
    data.detector.counts can use weak references.  In that case the
    file format should set data.detector.loadcounts to a method which
    can load the counts from the file.  If load() has already loaded
    the counts in it can set data.detector.counts = weakref.ref(counts)
    for the weak reference behaviour, or simply data.detector.counts = counts
    if the data is small.

    Both loader() and data.load() should call the self.resetQ() before
    returning in order to set the Qx-Qz values from the instrument geometry.
    
    File formats should provide a save() class method.  This method
    will take a ReflData object plus a filename and save it to the file.

    See source in refldata.py for a description of the ReflData format.
    
    See source in ncnr_ng1.py for a complete example.

    """
    registry[ext] = loader

# Delayed loading of file formats
def icp_ng7(file):
    """NCNR NG-7 ICP file loader"""
    from reflectometry.reduction.ncnr_ng7 import NG7Icp
    return [NG7Icp(file)]

def icp_ng1(file):
    """NCNR NG-7 ICP file loader"""
    from reflectometry.reduction.ncnr_ng1 import NG1Icp
    return [NG1Icp(file)]

def nexus(file):
    """NeXus file loader"""
    from reflectometry.reduction import nexusref, nexus
    tree = nexus.read(file)
    measurements = []
    for name,entry in tree.nodes():
        if entry.nxclass == 'NXentry':
            measurements.append(nexusref.NeXusRefl(entry,file))
    return measurements

# Register extensions with file formats
register_format('.ng7', icp_ng7)
register_format('.ng7.gz', icp_ng7)
register_format('NCNR ng7',icp_ng7)

register_format('.nxs', nexus)
register_format('NeXus', nexus)

register_format('NCNR ng1', icp_ng1)
for ext in ['.na1', '.nb1', '.nc1', '.nd1', '.ng1']:
        register_format(ext, icp_ng1)
        register_format(ext+'.gz', icp_ng1)

for ext in ['.ca1', '.cb1', '.cc1', '.cd1', '.cg1']:
        register_format(ext, icp_ng1)
        register_format(ext+'.gz', icp_ng1)

def test():
    # demostrate loading of NG-7 files; just check that the file
    # is found and loaded properlty, not that it
    import os.path
    root = os.path.dirname(__file__)
    ng7file = os.path.join(root,'examples','ng7','jul04032.ng7')
    ng1file = os.path.join(root,'examples','ng1','psih1001.ng1')
    cg1file = os.path.join(root,'examples','cg1area','psdca022.cg1.gz')
    assert load(ng7file).detector.wavelength == 4.76
    assert load(ng1file).name == 'gsip4007.ng1'
    assert loadmeta(cg1file).name == 'psdca022.cg1'

if __name__ == "__main__": test()
