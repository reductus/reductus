# This program is public domain
"""
Reflectometry reduction file formats.

=== File formats ===

Supported formats are:

     ICP on NCNR NG-1 and NG-7
     NeXus on SNS Liquids and Magnetic

The list of available formats can be found at runtime using
reflred.formats()

Sample data for some of these formats is available in examples.  In ipython
type the following:

    import reflred as red
    ls $red.examples

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

    data[0].load()

to load the data itself.  Again, loadmeta() returns a list of data
objects in case there are multiple datasets in the file.  Note that the
metadata can have the details wrong, for example when an NCNR ICP run is
aborted before all the measurements were complete.  data.load() will return
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

    red.formats.register(loader)

See the formats.register documentation for a description of the loader
function interface.

Currently available formats are returned from::

    red.formats.available()

"""
__all__ = ['loadmeta','load','examples']

from os.path import join as joinpath, dirname, abspath

from ..registry import ExtensionRegistry

examples = abspath(joinpath(dirname(__file__),'..','..','doc','examples'))


# Shared registry for all reflectometry formats
_registry = ExtensionRegistry()
def loadmeta(pattern, format=None):
    """
    Load the measurement description from the file but not the data.
    Use measurement.load() to load the data for each measurement.

    Returns a single measurement if there is only one measurement in
    the file, otherwise it returns a list of measurements.

    Use formats() to list available file formats.
    """
    if hasattr(pattern, 'read'):  # we have a file handle, not a path
        return _registry.load(pattern, format=format)
    else:
        return _flatten_one_level(_registry.load_pattern(pattern, format=format))

def _flatten_one_level(nested_list):
    """
    Remove one level of nesting from a list
    """
    return [k for nest in nested_list for k in nest]


def load(pattern, format=None):
    """
    Load the reflectometry measurement description and the data.


    Returns a single measurement if there is only one measurement in
    the file, otherwise it returns a list of measurements.

    Use formats() to list available file formats.
    """
    measurements = loadmeta(pattern, format)
    for data in measurements:  # Load the datasets
        data.load()
    return measurements


def available():
    """
    Return a list of available file formats.
    """
    return _registry.formats()


def register(ext,loader):
    """
    Register loader for a file extension.

    For each normal file extension for the format, call
        register('.ext',loader)
    You should also register the format name as
        register('name',loader)
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
    _registry[ext] = loader


# Delayed loading of file formats
def icp_ng7(filename):
    """NCNR NG-7 ICP file loader"""
    from .ncnr_ng7 import NG7Icp
    return [NG7Icp(filename)]


def icp_bt4(filename):
    from . import icpformat
    return [icpformat.data(filename)]

def icp_ng1(filename):
    """NCNR NG-7 ICP file loader"""
    from .ncnr_ng1 import NG1Icp
    return [NG1Icp(filename)]


def icp_ng1p(filename):
    """NCNR NG-7 ICP file loader"""
    from .ncnr_ng1 import NG1pIcp
    return [NG1pIcp(filename)]

def nexus(filename):
    """NeXus file loader"""
    from .nexusref import load_entries
    return load_entries(filename)


def _register_extensions():
    # Register extensions with file formats
    register('.ng7', icp_ng7)
    register('.ng7.gz', icp_ng7)
    register('NCNR NG-7',icp_ng7)

    register('.nxs', nexus)
    register('.nxs.magik', nexus)
    register('.nxz.cgd', nexus)
    register('.nxs.pbr', nexus)
    register('.nxz.pbr', nexus)
    register('.nxs.magik.zip', nexus)
    register('.nxs.pbr.zip', nexus)
    register('NeXus', nexus)
    register('NCNR NG-1', icp_ng1)

    for ext in ['.ngd', '.cgd', '.ng1', '.cg1']:
        register(ext, icp_ng1)
        register(ext+'.gz', icp_ng1)

    for ext in ['.nad', '.cad', '.na1', '.ca1']:
        for xs in 'abcd':
            register(ext.replace('a',xs), icp_ng1)

    register('.bt4', icp_bt4)
_register_extensions()

def test():
    # demostrate loading of NG-7 files; just check that the file
    # is found and loaded properlty, not that it
    ng7file = joinpath(examples,'ng7','jul04032.ng7')
    ng1file = joinpath(examples,'ng1','psih1001.ng1')
    cg1file = joinpath(examples,'cg1area','psdca022.cg1.gz')
    assert load(ng7file)[0].detector.wavelength == 4.76
    assert load(ng1file)[0].name == 'psih1001'
    assert loadmeta(cg1file)[0].name == 'psdca022'
    assert load(open(ng7file),format=".ng7")[0].detector.wavelength == 4.76
    print
    print load(open(ng1file),format='ng1')[0].name
    assert load(open(ng1file),format=".ng1")[0].name == 'gsip4007.ng1'
    assert available() == ['NCNR NG-1','NCNR NG-7','NeXus'],available()
    ng1pfile = joinpath(examples, 'ng1p', 'jd907_2706.n?d')
    pdata = load(ng1pfile)
    assert pdata[0].polarization == '--'
    assert pdata[1].polarization == '--'
    assert pdata[2].polarization == '--'
    assert pdata[3].polarization == '++'


if __name__ == "__main__":
    test()
