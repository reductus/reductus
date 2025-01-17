# This program is public domain
"""
Load a NeXus file into a reflectometry data structure.
"""
import os

import numpy as np

from reductus.dataflow.lib import unit
from reductus.dataflow.lib import iso8601
from reductus.dataflow.lib import h5_open
from reductus.dataflow.lib.strings import _s, _b

from .refldata import ReflData
from .resolution import FWHM2sigma

TRAJECTORY_INTENTS = {
    'SPEC': 'specular',
    'SLIT': 'intensity',
    'BGP': 'background+',
    'BGM': 'background-',
    'ROCK': 'rock sample',
}

WAVELENGTH = 4.
WAVELENGTH_DISPERSION = 0.015

def data_as(group, fieldname, units, rep=None, NA=None, dtype=None):
    """
    Return value of field in the desired units.
    """
    if fieldname not in group:
        return NA
    field = group[fieldname]
    units_in = _s(field.attrs.get('units', ''))
    converter = unit.Converter(units_in)
    value = converter(field[()], units)
    if dtype is not None:
        value = np.asarray(value, dtype=dtype)
    if rep is not None:
        if np.isscalar(value) or len(value) == 1:
            return np.repeat(value, rep, axis=0)
        elif len(value) == rep:
            return value
        else:
            raise ValueError("field %r does not match counts in %r"
                             %(field.name, field.file.filename))
    else:
        return value


def str_data(group, field, default=''):
    """
    Retrieve value of field as a string, with default if field is missing.
    """
    if field in group:
        data = group[field][0]
        if data.ndim > 0:
            value = [_s(v) for v in data]
        else:
            value = _s(data)
        return value
    else:
        return default


def list_data(group, field):
    """
    Retrieve value of field as a list of strings, or []
    """
    if field in group:
        return [_s(s) for s in group[field]]
    else:
        return []


def nxfind(group, nxclass):
    """
    Iterate over the entries of type *nxclass* in the hdf5 *group*.
    """
    for entry in group.values():
        if nxclass == _s(entry.attrs.get('NX_class', None)):
            yield entry


def load_metadata(filename, file_obj=None):
    """
    Load the summary info for all entries in a NeXus file.
    """
    return load_nexus_entries(filename, file_obj=file_obj,
                              meta_only=True, entry_loader=NCNRNeXusRefl)


def load_entries(filename, file_obj=None, entries=None):
    return load_nexus_entries(filename, file_obj=file_obj, entries=entries,
                              meta_only=False, entry_loader=NCNRNeXusRefl)


def load_nexus_entries(filename, file_obj=None, entries=None,
                       meta_only=False, entry_loader=None):
    """
    Load the summary info for all entries in a NeXus file.
    """
    handle = h5_open.h5_open_zip(filename, file_obj)
    measurements = []
    for name, entry in handle.items():
        if entries is not None and name not in entries:
            continue
        if _s(entry.attrs.get('NX_class', None)) == 'NXentry':
            data = entry_loader(entry, name, filename)
            if not meta_only:
                data.load(entry)
            measurements.append(data)
    if file_obj is None:
        handle.close()
    return measurements


def nexus_common(self, entry, entryname, filename):
    #print(entry['instrument'].values())
    das = entry['DAS_logs']
    self.entry = entryname
    self.path = os.path.abspath(filename)
    self.name = str_data(das, 'trajectoryData/fileName', 'unknown')
    if 'trajectoryData/fileNum' in das:
        self.filenumber = das['trajectoryData/fileNum'][0]
    else:
        # fall back to randomly generated filenum
        from random import randint
        self.filenumber = -randint(10**9, (10**10) - 1)

    #self.date = iso8601.parse_date(entry['start_time'][0].decode('utf-8'))
    self.date = iso8601.parse_date(str_data(entry, 'start_time'))
    self.description = str_data(entry, 'experiment_description')
    self.instrument = str_data(entry, 'instrument/name')

    # Determine the number of points in the scan.
    # TODO: Reliable way to determine scan length.
    if 'trajectory/liveScanLength' in entry:
        # New files should have num points in trajectory/liveScanLength ...
        n = entry['trajectory/liveScanLength'][()]
    else:
        # Guess length by looking at the counter fields
        # Prefer to not load the entire counter at this point, especially since
        # we don't know where it is.
        n = das['counter/liveROI'].shape[0]
        if n == 1:
            n = das['counter/liveMonitor'].shape[0]
        if n == 1:
            n = das['counter/liveTime'].shape[0]
    self.points = n

    monitor_device = entry.get('control/monitor', {})
    self.monitor.deadtime = data_as(monitor_device, 'dead_time', 'us')
    self.monitor.deadtime_error = data_as(monitor_device, 'dead_time_error', 'us')
    base = str_data(das, 'counter/countAgainst').lower()
    # NICE stores TIME, MONITOR, ROI, TIME_MONITOR, TIME_ROI, etc.
    if "monitor" in base:
        base = "monitor"
    elif "time" in base:
        base = "time"
    elif "roi" in base:
        base = "roi"
    else:
        base = "none"

    self.monitor.time_step = 0.001  # assume 1 ms accuracy on reported clock
    self.monitor.counts = data_as(das, 'counter/liveMonitor', '', rep=n, dtype='d')
    self.monitor.counts_variance = self.monitor.counts.copy()
    self.monitor.count_time = data_as(das, 'counter/liveTime', 's', rep=n)
    self.monitor.roi_counts = data_as(das, 'counter/liveROI', '', rep=n, dtype='d')
    self.monitor.roi_variance = self.monitor.roi_counts.copy()
    self.monitor.roi_variance = self.monitor.roi_counts.copy()
    self.monitor.source_power = data_as(das,
        'reactorPower/reactorPowerThermal/average_value', 'MW', rep=n, dtype='d')
    self.monitor.source_power_variance = data_as(das, 
        'reactorPower/reactorPowerThermal/average_value_error', 'MW', rep=n, dtype='d')
    self.monitor.source_power_units = "MW"

    # NG7 monitor saturation is stored in control/countrate_correction
    saturation_device = entry.get('control/countrate_correction', None)
    if saturation_device is not None:
        rate = data_as(saturation_device, 'measured_rate', '')
        correction = data_as(saturation_device, 'correction', '')
        self.monitor.saturation = np.vstack((rate, 1./correction))

    # CRUFT: old candor files don't define NXsample
    self.sample.name = str_data(entry, 'sample/name', default=None)
    self.sample.description = str_data(entry, 'sample/description')
    if self.sample.name is None:
        self.sample.name = str_data(entry, 'DAS_logs/sample/name')
        self.sample.description = str_data(entry, 'DAS_logs/sample/description')

    # TODO: stop trying to guess DOI
    if 'DOI' in entry:
        URI = _s(entry['DOI'])
    else:
        # See: dataflow.modules.doi_resolve for helpers.
        #NCNR_DOI = "10.18434/T4201B"
        NCNR_DOI = "https://ncnr.nist.gov/pub/ncnrdata"
        LOCATION = {'pbr':'ngd', 'magik':'cgd', 'ng7r':'ng7', 'candor':'cdr'}
        nice_instrument = str_data(das, 'experiment/instrument').lower()
        instrument = LOCATION.get(nice_instrument, nice_instrument)
        year, month = self.date.year, self.date.month
        cycle = "%4d%02d"%(year, month)
        experiment = str_data(entry, 'experiment_identifier')
        filename = os.path.basename(self.path)
        URI = "/".join((NCNR_DOI, instrument, cycle, experiment, "data", filename))
    self.uri = URI

    self.scan_value = []
    self.scan_units = []
    self.scan_label = []
    if 'trajectory/scannedVariables' in das:
        scanned_variables = list_data(das, 'trajectory/scannedVariables')
        # Just in case the scanned variables is a string with
        # elements separated by new lines...
        if len(scanned_variables) == 1:
            scanned_variables = scanned_variables[0].split('\n')
        # TODO: exclude count fields from scanned variables
        #scanned_variables = [s for s in scanned_variables
        #                     if not s.startswith("areaDetector")]
        for node_id in scanned_variables:
            path = node_id.replace('.', '/')
            try:
                field = das[path]
            except KeyError:
                # Note: Suppressing this message because it makes the
                # regression tests noisy.  Older versions of the SelectFields
                # filter on the datawriter were not stripping the fields from
                # control/scanned variables lists, but newer ones are.
                # TODO: reenable test for missing scan fields
                #print(">>> could not read scanned %s for %s"
                #      % (node_id, os.path.basename(self.path)))
                continue
            try:
                scan_value = data_as(das, path, '', rep=n)
                scan_units = _s(field.attrs.get('units', ''))
                scan_label = _s(field.attrs.get('label', node_id))
            except Exception as exc:
                print(">>> unexpected error %s reading %s for %s"
                      % (str(exc), node_id, os.path.basename(self.path)))
                continue
            # check if numeric:
            if scan_value.dtype.kind in ["f", "u", "i"]:
                self.scan_value.append(scan_value)
                self.scan_units.append(scan_units)
                self.scan_label.append(scan_label)

    # TODO: magnetic field
    if 'temp' in das:
        if 'temp/primaryControlLoop' in das:
            temp_controller = das['temp/primaryControlLoop'][0]
            setpoint_field = 'temp/setpoint_%d' % (temp_controller,)
            self.sample.temp_setpoint = data_as(das, setpoint_field, 'K')[0]
        temp_values = data_as(das, 'temp/primaryNode/value', 'K')
        temp_shape = temp_values.shape[0] if temp_values.shape[0] else 1.0
        # only include one significant figure for temperatures.
        self.sample.temp_avg = round(np.sum(temp_values)/temp_shape, 1)


def get_pol(das, pol):
    if pol in das:
        direction = str_data(das, pol+'/direction')
        if direction == 'UP':
            result = '+'
        elif direction == 'DOWN':
            result = '-'
        elif direction in ('', 'BEAM_OUT', 'UNPOLARIZED'):
            result = ''
        else:
            raise ValueError("Don't understand DAS_logs/%s/direction=%r"
                             %(pol, direction))
    else:
        result = ''
    return result


class NCNRNeXusRefl(ReflData):
    """
    NeXus reflectometry entry.

    See :class:`ReflData` for details.
    """
    format = "NeXus"
    probe = "neutrons"

    def __init__(self, entry, entryname, filename):
        super(NCNRNeXusRefl, self).__init__()
        nexus_common(self, entry, entryname, filename)

    def load(self, entry):
        #print(entry['instrument'].values())
        das = entry['DAS_logs']
        n = self.points
        raw_intent = str_data(das, 'trajectoryData/_scanType')
        if raw_intent in TRAJECTORY_INTENTS:
            self.intent = TRAJECTORY_INTENTS[raw_intent]

        # Polarizers
        self.polarization = (
            get_pol(das, 'frontPolarization')
            + get_pol(das, 'backPolarization')
        )

        # Monochromator
        self.monochromator.wavelength = data_as(entry, 'instrument/monochromator/wavelength', 'Ang', rep=n)
        self.monochromator.wavelength_resolution = data_as(entry, 'instrument/monochromator/wavelength_error', 'Ang', rep=n)
        if self.monochromator.wavelength is None:
            # for old NG7 data, wavelength is in DAS_logs
            self.monochromator.wavelength = data_as(das, 'wavelength/wavelength', 'Ang', rep=n)
        if self.monochromator.wavelength is None:
            self.warn("Wavelength is missing; using {WAVELENGTH} A".format(WAVELENGTH=WAVELENGTH))
            self.monochromator.wavelength = WAVELENGTH
        if self.monochromator.wavelength_resolution is None:
            self.warn("Wavelength resolution is missing; using %.1f%% dL/L FWHM"
                      % (100*WAVELENGTH_DISPERSION,))
            self.monochromator.wavelength_resolution = \
                FWHM2sigma(WAVELENGTH_DISPERSION*self.monochromator.wavelength)

        # Slits
        self.slit1.distance = data_as(entry, 'instrument/presample_slit1/distance', 'mm')
        self.slit2.distance = data_as(entry, 'instrument/presample_slit2/distance', 'mm')
        self.slit3.distance = data_as(entry, 'instrument/predetector_slit1/distance', 'mm')
        self.slit4.distance = data_as(entry, 'instrument/predetector_slit2/distance', 'mm')
        if self.slit1.distance is None:
            self.warn("Slit 1 distance is missing; using 2 m")
            self.slit1.distance = -2000
        if self.slit2.distance is None:
            self.warn("Slit 2 distance is missing; using 1 m")
            self.slit2.distance = -1000

        for k, slit in enumerate([self.slit1, self.slit2, self.slit3, self.slit4]):
            x = 'slitAperture%d/softPosition'%(k+1)
            x_target = 'slitAperture%d/desiredSoftPosition'%(k+1)
            slit.x = data_as(das, x, 'mm', rep=n, dtype='d')
            slit.x_target = data_as(das, x_target, 'mm', rep=n, dtype='d')
            y = 'vertSlitAperture%d/softPosition'%(k+1)
            y_target = 'vertSlitAperture%d/desiredSoftPosition'%(k+1)
            slit.y = data_as(das, y, 'mm', rep=n, dtype='d')
            slit.y_target = data_as(das, y_target, 'mm', rep=n, dtype='d')

        # Detector
        self.detector.wavelength = self.monochromator.wavelength
        self.detector.wavelength_resolution = self.monochromator.wavelength_resolution
        self.detector.deadtime = data_as(entry, 'instrument/single_detector/dead_time', 'us')
        self.detector.deadtime_error = data_as(entry, 'instrument/single_detector/dead_time_error', 'us')
        self.detector.distance = data_as(entry, 'instrument/detector/distance', 'mm')
        self.detector.rotation = data_as(entry, 'instrument/detector/rotation', 'degree')

        # Counts
        self.detector.counts = data_as(das, 'counter/liveROI', '', dtype='d')
        self.detector.counts_variance = self.detector.counts.copy()
        self.detector.dims = self.detector.counts.shape[1:]

        # Angles
        if 'sampleAngle' in das:
            # selects MAGIK or PBR, which have sample and detector angle
            self.sample.angle_x = data_as(das, 'sampleAngle/softPosition', 'degree', rep=n)
            self.detector.angle_x = data_as(das, 'detectorAngle/softPosition', 'degree', rep=n)
            self.sample.angle_x_target = data_as(das, 'sampleAngle/desiredSoftPosition', 'degree', rep=n)
            self.detector.angle_x_target = data_as(das, 'detectorAngle/desiredSoftPosition', 'degree', rep=n)
        elif 'q' in das:
            # selects NG7R which has only q device (qz) and sampleTilt
            # Ignore sampleTilt for now since it is arbitrary.  NG7 is not
            # using zeros for the sampleTilt motor in a predictable way.
            tilt = 0.
            #tilt = data_as(das, 'sampleTilt/softPosition', 'degree', rep=n)
            theta = data_as(das, 'q/thetaIncident', 'degree', rep=n)
            if theta is not None:
                self.sample.angle_x = theta + tilt
                self.detector.angle_x = 2*theta
            # NaN if not defined
            tilt_target = 0.
            #tilt_target = data_as(das, 'sampleTilt/desiredSoftPosition', 'degree', rep=n)
            # Note: q/desiredThetaIncident is not available on any instruments
            # so the following always returns None.
            theta_target = data_as(das, 'q/desiredThetaIncident', 'degree', rep=n)
            if theta_target is not None:
                self.sample.angle_x_target = theta_target + tilt_target
                self.detector.angle_x_target = 2*theta_target
        else:
            raise ValueError("Unknown sample angle in file")
        self.Qz_target = data_as(das, 'q/z', '', rep=n)
        if self.Qz_target is None:
            self.Qz_target = data_as(das, 'trajectoryData/_q', '', rep=n)
        # TODO: use background_offset if it is defined
        #if 'trajectoryData/_theta_offset' in das:
        #    self.background_offset = 'theta'

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


def demo(loader=load_entries):
    import sys
    from .load import setup_fetch, fetch_uri
    if len(sys.argv) == 1:
        print("usage: python -m reflred.nexusref file...")
        sys.exit(1)
    setup_fetch()
    for uri in sys.argv[1:]:
        try:
            entries = fetch_uri(uri, loader=loader)
        except Exception as exc:
            print("**** "+str(exc)+" **** while reading "+uri)
            raise
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
