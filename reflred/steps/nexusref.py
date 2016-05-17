# This program is public domain

"""
Load a NeXus file into a reflectometry data structure.
"""
import os
import tempfile
from zipfile import ZipFile, _EndRecData

import numpy as np
import h5py as h5

from .. import hzf_readonly_stripped as hzf
from .. import unit
from .. import iso8601
from . import refldata

def data_as(group, fieldname, units, rep=1):
    """
    Return value of field in the desired units.
    """
    if fieldname not in group:
        return np.NaN
    field = group[fieldname]
    converter = unit.Converter(field.attrs.get('units', ''))
    value = converter(field.value, units)
    if rep != 1:
        if value.shape[0] == 1:
            return np.repeat(value, rep, axis=0)
        elif value.shape[0] != rep:
            raise ValueError("field %r does not match counts in %r"
                             %(field.name,field.file.filename))
        else:
            return value
    else:
        return value

def nxfind(group, nxclass):
    """
    Iterate over the entries of type *nxclass* in the hdf5 *group*.
    """
    for entry in group.values():
        if nxclass == entry.attrs.get('NX_class', None):
            yield entry

def load_metadata(filename, file_obj=None):
    """
    Load the summary info for all entries in a NeXus file.
    """
    #file = h5.File(filename)
    file = h5_open_zip(filename, file_obj)
    measurements = []
    for name,entry in file.items():
        if entry.attrs.get('NX_class', None) == 'NXentry':
            data = NCNRNeXusRefl(entry, name, filename)
            measurements.append(data)
    if file_obj is None:
        file.close()
    return measurements

def load_entries(filename, file_obj=None, entries=None):
    """
    Load the summary info for all entries in a NeXus file.
    """
    #file = h5.File(filename)
    file = h5_open_zip(filename, file_obj)
    measurements = []
    for name,entry in file.items():
        if entries is not None and name not in entries:
            continue
        if entry.attrs.get('NX_class', None) == 'NXentry':
            data = NCNRNeXusRefl(entry, name, filename)
            data.load(entry)
            measurements.append(data)
    if file_obj is None:
        file.close()
    return measurements


def h5_open_zip(filename, file_obj=None, mode='r', **kw):
    """
    Open a NeXus file, even if it is in a zip file, 
    or if it is a NeXus-zip file.

    If the filename ends in '.zip', it will be unzipped to a temporary
    directory before opening and deleted on :func:`closezip`.  If opened
    for writing, then the file will be created in a temporary directory,
    then zipped and deleted on :func:`closezip`.
    
    If it is a zipfile but doesn't end in '.zip', it is assumed
    to be a NeXus-zip file and is opened with that library.

    Arguments are the same as for :func:`open`.
    """
    if file_obj is None:
        file_obj = open(filename, mode=mode)
    is_zip = _EndRecData(file_obj) # is_zipfile(file_obj) doens't work in py2.6
    if is_zip and not filename.endswith('.zip'):
        # then it's a nexus-zip file, rather than
        # a zipped hdf5 nexus file
        f = hzf.File(filename, file_obj)
        f.delete_on_close = False
        f.zip_on_close = False
    else:
        zip_on_close = None
        if is_zip:
            path = tempfile.gettempdir()
            if mode == 'r':
                zf = ZipFile(filename)
                members = zf.namelist()
                assert len(members) == 1
                zf.extract(members[0], path)
                filename = os.path.join(path, members[0])
            elif mode == 'w':
                zip_on_close = filename
                filename = os.path.join(path, os.path.basename(filename)[:-4])
            else:
                raise TypeError("zipped nexus files only support mode r and w")

        f = h5.File(filename, mode=mode, **kw)
        f.delete_on_close = is_zip
        f.zip_on_close = zip_on_close
    return f

def h5_close_zip(f):
    """
    Close a NeXus file opened by :func:`open_zip`.

    If the file was zipped and opened for reading, delete the temporary
    file that was created
    If opened for writing, create a zip file containing the file
    before closing.

    Delete the file after closing.
    """
    path = f.filename
    delete_on_close = getattr(f, 'delete_on_close', False)
    zip_on_close = getattr(f, 'zip_on_close', None)
    f.close()
    if zip_on_close is not None:
        with ZipFile(f.zip_on_close, 'w') as zf:
            zf.write(path, os.path.basename(path))
    if delete_on_close:
        os.unlink(path)


class NCNRNeXusRefl(refldata.ReflData):
    """
    NeXus reflectometry entry.

    See :class:`refldata.ReflData` for details.
    """
    format = "NeXus"
    trajectory_intents = {
        'SPEC': 'specular',
        'SLIT': 'slit',
        'BGP': 'background+',
        'BGM': 'background-',
        'ROCK': 'rock sample'
    }

    def __init__(self, entry, entryname, filename):
        super(NCNRNeXusRefl,self).__init__()
        self.entry = entryname
        self.filename = os.path.abspath(filename)
        self.name = os.path.basename(filename).split('.')[0]
        self._set_metadata(entry)

    def _set_metadata(self, entry):
        #print(entry['instrument'].values())
        das = entry['DAS_logs']
        self.probe = 'neutron'
        self.date = iso8601.parse_date(entry['start_time'][0])
        self.description = entry['experiment_description'][0]
        self.instrument = entry['instrument/name'][0]
        self.slit1.distance = data_as(entry,'instrument/presample_slit1/distance','mm')
        self.slit2.distance = data_as(entry,'instrument/presample_slit2/distance','mm')
        #self.slit3.distance = data_as(entry,'instrument/predetector_slit1/distance','mm')
        #self.slit4.distance = data_as(entry,'instrument/predetector_slit2/distance','mm')
        #self.detector.distance = data_as(entry,'instrument/detector/distance','mm')
        #self.detector.rotation = data_as(entry,'instrument/detector/rotation','degree')
        self.detector.wavelength = data_as(entry,'instrument/monochromator/wavelength','Ang')
        self.detector.wavelength_resolution = data_as(entry,'instrument/monochromator/wavelength_error','Ang')
        self.detector.deadtime = data_as(entry, 'instrument/single_detector/dead_time', 'us')
        self.detector.deadtime_error = data_as(entry, 'instrument/single_detector/dead_time_error', 'us')
        
        self.sample.name = entry['sample/name'][0] if 'name' in entry['sample'] else ""
        self.sample.description = entry['sample/description'][0] if 'description' in entry['sample'] else ""
        raw_intent = das['trajectoryData/_scanType'][0] if '_scanType' in das['trajectoryData'] else ""
        if raw_intent in self.trajectory_intents:
            self.intent = self.trajectory_intents[raw_intent]
        self.monitor.base = das['counter/countAgainst'][0]
        self.monitor.time_step = 0.001  # assume 1 ms accuracy on reported clock
        self.monitor.deadtime = data_as(entry,'control/dead_time','us')
        self.polarization = _get_pol(das, 'frontPolarization') \
                            + _get_pol(das, 'backPolarization')

        if np.isnan(self.slit1.distance):
            self.warn("Slit 1 distance is missing; using 2 m")
            self.slit1.distance = -2000
        if np.isnan(self.slit2.distance):
            self.warn("Slit 2 distance is missing; using 1 m")
            self.slit2.distance = -1000
        if np.isnan(self.detector.wavelength):
            self.warn("Wavelength is missing; using 4.75 A")
            self.detector.wavelength = 4.75
        if np.isnan(self.detector.wavelength_resolution):
            self.warn("Wavelength resolution is missing; using 2% dL/L FWHM")
            self.detector.wavelength_resolution = 0.02*self.detector.wavelength

    def load(self, entry):
        das = entry['DAS_logs']
        self.detector.counts = np.asarray(das['pointDetector/counts'][:,0], 'd')
        self.detector.dims = self.detector.counts.shape
        n = self.detector.dims[0]
        self.monitor.counts = np.asarray(data_as(das,'counter/liveMonitor','',rep=n), 'd')
        self.monitor.counts_variance = np.asarray(data_as(das,'counter/liveMonitor','',rep=n), 'd')
        self.monitor.count_time = data_as(das,'counter/liveTime','s',rep=n)
        self.slit1.x = data_as(das,'slitAperture1/softPosition','mm',rep=n)
        self.slit2.x = data_as(das,'slitAperture2/softPosition','mm',rep=n)
        self.slit3.x = data_as(das,'slitAperture3/softPosition','mm',rep=n)
        self.slit4.x = data_as(das,'slitAperture4/softPosition','mm',rep=n)
        self.sample.angle_x = data_as(das,'sampleAngle/softPosition','degree',rep=n)
        self.detector.angle_x = data_as(das,'detectorAngle/softPosition','degree',rep=n)
        self.Qz_target = data_as(das, 'trajectoryData/_q', 'invAng', rep=n)
        #TODO: temperature, field
        if '_theta_offset' in das['trajectoryData']:
            self.background_offset = 'theta'

    def _load_slits(self, instrument):
        """
        Slit names have not been standardized.  Instead sort the
        NXaperature components by distance and assign them according
        to serial order, negative aperatures first and positive second.
        """
        raise NotImplementedError("hardcode slit names for now")
        slits = list(nxfind(instrument, 'NXaperature'))
        # Note: only supports to aperatures before and after.
        # Assumes x and y aperatures are coupled in the same
        # component.  This will likely be wrong for some instruments,
        # but we won't deal with that until we have real NeXus files
        # to support.
        # Assume the file writer was sane and specified all slit
        # distances in the same units so that sorting is simple.
        # Currently only slit distance is recorded, not slit opening.
        slits.sort(lambda a,b: -1 if a.distance < b.distance else 1)
        index = 0
        for slit in slits:
            d = slit.distance.value('meters')
            if d <= 0:
                # process first two slits only
                if index == 0:
                    self.slit1.distance = d
                    index += 1
                elif index == 1:
                    self.slit2.distance = d
                    index += 1
            elif d > 0:
                # skip leading slits
                if index < 2: index = 2
                if index == 2:
                    self.slit3.distance = d
                    index += 1
                elif index == 3:
                    self.slit4.distance = d
                    index += 1

def _get_pol(das, pol):
    if pol in das:
        direction = das[pol+'/direction'][0]
        if direction == 'UP':
            result = '+'
        elif direction == 'DOWN':
            result = '-'
        elif direction == '' or direction == 'BEAM_OUT' or direction == 'UNPOLARIZED':
            result = ''
        else:
            raise ValueError("Don't understand DAS_logs/%s/direction=%r"%(pol,direction))
    else:
        result = ''
    return result



def demo():
    import sys
    import pylab
    if len(sys.argv) == 1:
        print("usage: python -m reflred.formats.nexusref file...")
        sys.exit(1)
    for f in sys.argv[1:]:
        entries = load_entries(f)
        for f in entries:
            f.load()
            print f
            f.plot()
    pylab.legend()
    pylab.show()

if __name__ == "__main__":
    demo()
