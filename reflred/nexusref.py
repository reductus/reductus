# This program is public domain

"""
Load a NeXus file into a reflectometry data structure.
"""
import os
import tempfile
from zipfile import ZipFile, _EndRecData
from io import BytesIO

import numpy as np
import h5py as h5

from dataflow.lib import hzf_readonly_stripped as hzf
from dataflow.lib import unit
from dataflow.lib import iso8601

from . import refldata
from .util import fetch_url

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
                             %(field.name, field.file.filename))
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


def load_from_string(filename, data, entries=None):
    """
    Load a nexus file from a string, e.g., as returned from url.read().
    """
    fd = BytesIO(data)
    entries = load_entries(filename, fd, entries=entries)
    fd.close()
    return entries


def load_from_uri(uri, entries=None, url_cache="/tmp"):
    """
    Load a nexus file from disk or from http://, https:// or file://.

    Remote files are cached in *url_cache*.  Use None to fetch without caching.
    """
    if uri.startswith('file://'):
        return load_entries(uri[7:], entries=entries)
    elif uri.startswith('http://') or uri.startswith('https://'):
        filename = os.path.basename(uri)
        data = fetch_url(uri, url_cache=url_cache)
        return load_from_string(filename, data, entries=entries)
    else:
        return load_entries(uri, entries=entries)


def load_metadata(filename, file_obj=None):
    """
    Load the summary info for all entries in a NeXus file.
    """
    #file = h5.File(filename)
    file = h5_open_zip(filename, file_obj)
    measurements = []
    for name, entry in file.items():
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
    for name, entry in file.items():
        if entries is not None and name not in entries:
            continue
        if entry.attrs.get('NX_class', None) == 'NXentry':
            data = NCNRNeXusRefl(entry, name, filename)
            data.load(entry)
            measurements.append(data)
    if file_obj is None:
        file.close()
    return measurements

def h5_open_zip(filename, file_obj=None, mode='rb', **kw):
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
        file_obj = open(filename, mode=mode, buffering=-1)
    is_zip = _EndRecData(file_obj) # is_zipfile(file_obj) doens't work in py2.6
    if is_zip and '.attrs' in ZipFile(file_obj).namelist():
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
        'SLIT': 'intensity',
        'BGP': 'background+',
        'BGM': 'background-',
        'ROCK': 'rock sample'
    }

    def __init__(self, entry, entryname, filename):
        super(NCNRNeXusRefl, self).__init__()
        self.entry = entryname
        self.path = os.path.abspath(filename)
        self._set_metadata(entry)

    def _set_metadata(self, entry):
        #print(entry['instrument'].values())
        das = entry['DAS_logs']
        self.probe = 'neutron'
        self.name = das['trajectoryData/fileName'][0] if 'trajectoryData/fileName' in das else 'unknown'
        if 'trajectoryData/fileNum' in das:
            self.filenumber = das['trajectoryData/fileNum'][0]
        else:
            # fall back to randomly generated filenum
            from random import randint
            self.filenumber = -randint(10**9, (10**10) - 1)
        
        #self.date = iso8601.parse_date(entry['start_time'][0].decode('utf-8'))
        self.date = iso8601.parse_date(entry['start_time'][0])
        self.description = entry['experiment_description'][0]
        self.instrument = entry['instrument/name'][0]
        self.slit1.distance = data_as(entry, 'instrument/presample_slit1/distance', 'mm')
        self.slit2.distance = data_as(entry, 'instrument/presample_slit2/distance', 'mm')
        #self.slit3.distance = data_as(entry, 'instrument/predetector_slit1/distance','mm')
        #self.slit4.distance = data_as(entry, 'instrument/predetector_slit2/distance','mm')
        #self.detector.distance = data_as(entry, 'instrument/detector/distance','mm')
        #self.detector.rotation = data_as(entry, 'instrument/detector/rotation','degree')
        self.detector.wavelength = data_as(entry, 'instrument/monochromator/wavelength','Ang')
        self.detector.wavelength_resolution = data_as(entry, 'instrument/monochromator/wavelength_error','Ang')
        self.detector.deadtime = data_as(entry, 'instrument/single_detector/dead_time', 'us')
        self.detector.deadtime_error = data_as(entry, 'instrument/single_detector/dead_time_error', 'us')
        monitor_device = entry.get('control/monitor', {})
        self.monitor.deadtime = data_as(monitor_device, 'dead_time','us')
        self.monitor.deadtime_error = data_as(monitor_device, 'dead_time_error', 'us')

        self.sample.name = entry['sample/name'][0] if 'name' in entry['sample'] else ""
        self.sample.description = entry['sample/description'][0] if 'description' in entry['sample'] else ""
        raw_intent = das['trajectoryData/_scanType'][0] if 'trajectoryData/_scanType' in das else ""
        if raw_intent in self.trajectory_intents:
            self.intent = self.trajectory_intents[raw_intent]
        self.monitor.base = das['counter/countAgainst'][0]
        self.monitor.time_step = 0.001  # assume 1 ms accuracy on reported clock
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
            self.warn("Wavelength resolution is missing; using 1.5% dL/L FWHM")
            self.detector.wavelength_resolution = 0.015/2.35*self.detector.wavelength

        # TODO: stop trying to guess DOI
        if 'DOI' in entry:
            URI = entry['DOI']
        else:
            # See: dataflow.modules.doi_resolve for helpers.
            #NCNR_DOI = "10.18434/T4201B"
            NCNR_DOI = "https://ncnr.nist.gov/pub/ncnrdata"
            LOCATION = {'pbr':'ngd', 'magik':'cgd', 'ng7r':'ng7'}
            nice_instrument = str(das['experiment/instrument'].value[0]).lower()
            instrument = LOCATION.get(nice_instrument, nice_instrument)
            year, month = self.date.year, self.date.month
            cycle = "%4d%02d"%(year, month)
            experiment = str(entry['experiment_identifier'].value[0])
            filename = os.path.basename(self.path)
            URI = "/".join((NCNR_DOI, instrument, cycle, experiment, "data", filename))
        self.uri = URI

    def load(self, entry):
        das = entry['DAS_logs']
        self.detector.counts = np.asarray(data_as(das, 'counter/liveROI', ''), 'd')
        self.detector.counts_variance = self.detector.counts.copy()
        self.detector.dims = self.detector.counts.shape
        n = self.detector.dims[0]
        self.points = n
        self.monitor.counts = np.asarray(data_as(das, 'counter/liveMonitor', '', rep=n), 'd')
        self.monitor.counts_variance = self.monitor.counts.copy()
        self.monitor.count_time = data_as(das, 'counter/liveTime', 's', rep=n)
        for k, s in enumerate([self.slit1, self.slit2, self.slit3, self.slit4]):
            x = 'slitAperture%d/softPosition'%(k+1)
            y = 'vertSlitAperture%d/softPosition'%(k+1)
            x_target = 'slitAperture%d/desiredSoftPosition'%(k+1)
            y_target = 'vertSlitAperture%d/desiredSoftPosition'%(k+1)
            if x in das:
                s.x = data_as(das, x, 'mm', rep=n)
            if y in das:
                s.y = data_as(das, y, 'mm', rep=n)
            s.x_target = data_as(das, x_target, 'mm', rep=n)
            s.y_target = data_as(das, y_target, 'mm', rep=n)
        if 'sampleAngle' in das:
            # selects MAGIK or PBR, which have sample and detector angle
            self.sample.angle_x = data_as(das, 'sampleAngle/softPosition', 'degree', rep=n)
            self.detector.angle_x = data_as(das, 'detectorAngle/softPosition', 'degree', rep=n)
            self.sample.angle_x_target = data_as(das, 'sampleAngle/desiredSoftPosition', 'degree', rep=n)
            self.detector.angle_x_target = data_as(das, 'detectorAngle/desiredSoftPosition', 'degree', rep=n)
        elif 'q' in das:
            # selects NG7R which has only q device (qz) and sampleTilt
            tilt = data_as(das, 'sampleTilt/softPosition', 'degree', rep=n)
            theta = data_as(das, 'q/thetaIncident', 'degree', rep=n)
            self.sample.angle_x = theta + tilt
            self.detector.angle_x = 2*theta
            # NaN if not defined
            tilt_target = data_as(das, 'sampleTilt/desiredSoftPosition', 'degree', rep=n)
            theta_target = data_as(das, 'q/desiredThetaInident', 'degree', rep=n)
            self.sample.angle_x_target = theta_target + tilt_target
            self.detector.angle_x_target = 2*theta_target
        else:
            raise ValueError("Unknown sample angle in file")
        self.Qz_target = data_as(das, 'trajectoryData/_q', '', rep=n)
        if 'trajectoryData/_theta_offset' in das:
            self.background_offset = 'theta'
        self.scan_value = []
        self.scan_units = []
        self.scan_label = []
        SCANNED_VARIABLES = 'trajectory/scannedVariables'
        if SCANNED_VARIABLES in das:
            scanned_variables = das[SCANNED_VARIABLES].value
            # Just in case the scanned variables is a string with
            # elements separated by new lines...
            if len(scanned_variables) == 1:
                scanned_variables = str(scanned_variables[0]).split('\n')
            for node_id in scanned_variables:
                path = node_id.replace('.', '/')
                try:
                    field = das[path]
                except KeyError:
                    print(">>> could not read scanned %s for %s"
                          % (node_id, os.path.basename(self.path)))
                    continue
                try:
                    scan_value = data_as(das, path, '', rep=n)
                    scan_units = field.attrs.get('units', '')
                    scan_label = field.attrs.get('label', node_id)
                except Exception:
                    print(">>> unexpected error reading %s for %s"
                          % (node_id, os.path.basename(self.path)))
                    continue
                # check if numeric:
                if scan_value.dtype.kind in ["f", "u", "i"]:
                    self.scan_value.append(scan_value)
                    self.scan_units.append(scan_units)
                    self.scan_label.append(scan_label)
        # TODO: field
        if 'temp' in das:
            if 'temp/primaryControlLoop' in das:
                temp_primaryControlLoop = das['temp/primaryControlLoop'].value
                self.sample.temp_setpoint = data_as(das, 'temp/setpoint_%d' % (temp_primaryControlLoop), 'K')[0]
            temp_values = data_as(das, 'temp/primaryNode/value', 'K')
            temp_shape = temp_values.shape[0] if temp_values.shape[0] else 1.0;
            # only include one significant figure for temperatures.
            self.sample.temp_avg = round(np.sum(temp_values)/temp_shape, 1)

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
    if len(sys.argv) == 1:
        print("usage: python -m reflred.steps.nexusref file...")
        sys.exit(1)
    for filename in sys.argv[1:]:
        try:
            entries = load_from_uri(filename)
        except Exception as exc:
            print("**** "+str(exc)+" **** while reading "+filename)
            continue

        # print the first entry
        print(entries[0])

        # plot all the entries
        import pylab
        pylab.figure()
        for entry in entries:
            entry.plot()
        pylab.legend()
        pylab.show()

if __name__ == "__main__":
    demo()
