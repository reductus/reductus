# This program is public domain
"""
Reflectometry reduction file formats.

    loadmeta('path/to/file.ext')
        Load the metadata for all measurements in the file but not the data.
        Use measurement.load() to load the data for each measurement.
    load('path/to/file.ext')
        Load the data and metadata for all measurements in the file.  This
        is a convenience function which returns a single measurement if
        there is only one measurement in the file, otherwise it returns
        a list of measurements.
    register_format('.ext',loader)
        Register your own file format.

Supported formats are:

     ICP on NCNR NG-1 and NG-7
     NeXus on SNS Liquids and Magnetic

The loader should return a list of ReflData objects, with a method for
load() to load the data.  See reflectometry.reduction.refldata for details.

Loaders are tried in the reverse order that they are registered.

Whatever exception is raised by the loader will be forwarded to
the application.
"""

from reflectometry.reduction.registry import ExtensionRegistry
__all__ = ['loadmeta','load','register_format']

# Shared registry for all reflectometry formats
registry = ExtensionRegistry()
def loadmeta(file):
    """Load reflectometry measurement descriptions only."""
    return registry.load(file)

def load(file):
    """
    Load reflectometry measurement description and data.  If there are
    multiple measurements in the file, return a list of measurements.
    """
    measurements = registry.load(file)
    for data in measurements:
        data.load() # Load the dataset
        data.resetQ() # Set Qz
    return measurements[0] if len(measurements)==1 else measurements

def register_format(ext,loader):
    """Register loader for a file extension"""
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
register_format('.nxs', nexus)

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
    assert loadmeta(cg1file)[0].name == 'psdca022.cg1'

if __name__ == "__main__": test()
