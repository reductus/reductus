# This program is public domain
# -*- coding: UTF-8 -*-
"""
Load a Bruker raw file into a reflectometry data structure.
"""
from __future__ import print_function

import os
import datetime
import time
import logging
import traceback
from io import BytesIO

import numpy as np

from reductus.dataflow.lib import unit
from reductus.dataflow.lib import iso8601

from . import bruker
from . import rigaku
from . import xrdml
from . import refldata
from .resolution import FWHM2sigma


def load_entries(filename, file_obj=None, entries=None):
    """
    Load the entries from an X-ray file.
    """
    #logging.info("loading X-ray file " + filename)
    if filename.endswith('.ras'):
        return load_rigaku_entries(filename, file_obj)
    elif filename.endswith('.xrdml'):
        return load_xrdml_entries(filename, file_obj)
    else:
        return load_bruker_entries(filename, file_obj)


def load_bruker_entries(filename, file_obj=None):
    """
    Load the entries from a Bruker file.
    """
    if file_obj is None:
        bruker_file = bruker.load(filename)
    else:
        bruker_file = bruker.loads(file_obj.read())

    entries = [BrukerRefl(bruker_file, entryid, filename)
               for entryid, _ in enumerate(bruker_file['data'])]
    return entries

def load_rigaku_entries(filename, file_obj=None):
    """
    Load the entries from a Rigaku file.
    """
    if file_obj is None:
        datasets = rigaku.load(filename)
    else:
        datasets = rigaku.loads(file_obj.read())
    joined_data = rigaku.join(datasets)

    entries = [RigakuRefl(joined_data, filename)]
    return entries

def load_xrdml_entries(filename, file_obj=None):
    """
    Load the entries from an XRDML file.
    """
    if file_obj is None:
        xrdml_file = xrdml.load(filename)
    else:
        xrdml_file = xrdml.load(file_obj)

    entries = [XRDMLRefl(entry, entryid, filename)
               for entryid, entry in enumerate(xrdml_file)]
    return entries


TRAJECTORY_INTENTS = {
    'locked coupled': 'specular',
    'unlocked coupled': 'specular',
    'detector scan': 'rock detector',
    'rocking curve': 'rock sample',
    'phi scan': 'rock sample'
}

class BrukerRefl(refldata.ReflData):
    """
    Bruker raw reflectometry file.

    See :class:`refldata.ReflData` for details.
    """
    format = "BrukerRaw"

    def __init__(self, bruker_file, entryid, filename):
        super(BrukerRefl, self).__init__()
        self.entry = "E"+str(entryid+1)  # 1-origin entry number for each entry
        self.path = os.path.abspath(filename)
        self.name = os.path.basename(filename).split('.')[0]
        self.filenumber = self.name # since we don't have a real filenumber
        #import pprint; pprint.pprint(entry)
        self._set_metadata(bruker_file)
        self._set_data(bruker_file['data'][entryid])

    def _set_metadata(self, entry):
        #print(entry['instrument'].values())
        self.probe = "x-rays"

        # parse date into datetime object
        month, day, year = [int(v) for v in entry['date'].split('/')]
        hour, minute, second = [int(v) for v in entry['time'].split(':')]
        self.date = datetime.datetime(year+2000, month, day, hour, minute, second)

        self.description = entry['comment']
        self.instrument = 'BrukerXray'
        # 1-sigma angular resolution (degrees) reported by Bruker.  Our own
        # measurements give a similar value (~ 0.033 degrees FWHM)
        nominal_resolution = 0.03
        self.angular_resolution = FWHM2sigma(nominal_resolution)
        self.slit1.distance = -275.5
        self.slit2.distance = -192.7
        self.slit3.distance = +175.0
        # Set the slit openings so that divergence calculation will yield
        # the nominal resolution for the given slit positions.
        # In practice the xray resolution is defined by optical elements
        # such as Goebel mirrors, and so the slit geometry should not be
        # used to compute resolution.  Slit openings could be used to estimate
        # beam footprint on the sample if we knew the true value...
        nominal_slits = (np.radians(nominal_resolution)
                         * abs(self.slit1.distance - self.slit2.distance))
        self.slit1.x = self.slit2.x = nominal_slits
        self.slit1.y = self.slit2.y = 20.0 # Note: back slits unused in reduction
        #self.slit4.distance = data_as(entry,'instrument/predetector_slit2/distance','mm')
        #self.detector.distance = data_as(entry,'instrument/detector/distance','mm')
        #self.detector.rotation = data_as(entry,'instrument/detector/rotation','degree')
        # Assume that Kalpha1 and Kalpha2 are both present in 2:1 ratio;
        # Normally we should check the value of fixed_inc_monochromator to
        # determine the wavelength and resolution, but the instrument at the
        # NCNR only has a Göbel mirror.
        self.detector.wavelength = entry['alpha_average']
        if self.detector.wavelength == 0.0:
            # this happens on some converted files...
            if 'alpha_1' in entry and 'alpha_2' in entry and 'alpha_21' in entry:
                self.detector.wavelength = (entry['alpha_1'] + entry['alpha_21'] * entry['alpha_2']) / (1.0 + entry['alpha_21'])
                
        self.detector.wavelength_resolution = np.std([
            entry['alpha_1'], entry['alpha_1'], entry['alpha_2']], ddof=1)
        #print("res:", self.angular_resolution, self.detector.wavelength_resolution, self.detector.wavelength)
        self.detector.deadtime = np.array([0.0]) # sorta true.
        self.detector.deadtime_error = np.array([0.0]) # also kinda true.

        self.sample.name = entry['samplename']
        self.sample.description = ""
        self.monitor.base = 'TIME'
        self.monitor.time_step = 0.001  # assume 1 ms accuracy on reported clock
        self.monitor.deadtime = 0.0
        self.polarization = "unpolarized"

    def _set_data(self, data):
        #for k,v in sorted(data.items()): print(k, v)
        raw_intent = bruker.SCAN_TYPE.get(data['scan_type'], "")
        attenuator_state = data['detslit_code'].strip().lower()
        self.intent = TRAJECTORY_INTENTS.get(raw_intent, refldata.Intent.none)
        self.detector.counts = data['values']['count']
        self.detector.counts_variance = self.detector.counts.copy()
        if attenuator_state == 'in':
            ATTENUATOR = 100.
            #self.v = self.detector.counts*ATTENUATOR
            #self.dv = np.sqrt(self.detector.counts_variance) * ATTENUATOR
            self.detector.counts *= ATTENUATOR
            self.detector.counts_variance *= ATTENUATOR**2
        self.detector.dims = self.detector.counts.shape
        n = self.detector.dims[0]
        self.points = n
        self.monitor.counts = np.zeros_like(self.detector.counts)
        self.monitor.counts_variance = np.zeros_like(self.detector.counts)
        self.monitor.count_time = np.ones_like(self.detector.counts) * data['step_time']
        if raw_intent in ["locked coupled", "unlocked coupled"]:
            self.sample.angle_x = data['theta_start'] + np.arange(n, dtype='float') * data['increment_1'] / 2.0
            self.detector.angle_x = data['two_theta_start'] + np.arange(n, dtype='float') * data['increment_1']
            self.sample.angle_x_target = self.sample.angle_x
            self.detector.angle_x_target = self.detector.angle_x
            self.scan_value = [self.sample.angle_x, self.detector.angle_x]
            self.scan_units = ['degrees', 'degrees']
            self.scan_label = ['theta', 'two_theta']
        elif raw_intent == 'detector scan':
            self.sample.angle_x = data['theta_start']
            self.detector.angle_x = data['two_theta_start'] + np.arange(n, dtype='float') * data['increment_1']
            self.sample.angle_x_target = self.sample.angle_x
            self.detector.angle_x_target = self.detector.angle_x
            self.scan_value = [self.detector.angle_x]
            self.scan_units = ['degrees']
            self.scan_label = ['two_theta']
        elif raw_intent in ['rocking curve', 'phi scan']:
            # this may not be right at all.  I can't understand what reflred/loadraw.tcl is doing here
            self.sample.angle_x = data['theta_start'] - np.arange(n, dtype='float') * data['increment_1']
            self.detector.angle_x = data['two_theta_start'] + np.arange(n, dtype='float') * data['increment_1']
            self.sample.angle_x_target = self.sample.angle_x
            self.detector.angle_x_target = self.detector.angle_x
            self.scan_value = [self.sample.angle_x, self.detector.angle_x]
            self.scan_units = ['degrees', 'degrees']
            self.scan_label = ['theta', 'two_theta']
        else:
            raise ValueError("Unknown sample angle in file")
        self.Qz_target = np.nan

class RigakuRefl(refldata.ReflData):
    """
    Bruker raw reflectometry file.

    See :class:`refldata.ReflData` for details.
    """
    format = "BrukerRaw"

    def __init__(self, dataset, filename):
        super(RigakuRefl, self).__init__()
        self.entry = "entry"
        self.path = os.path.abspath(filename)
        self.name = os.path.basename(filename).split('.')[0]
        self.filenumber = self.name # since we don't have a real filenumber
        #import pprint; pprint.pprint(entry)
        self._set_metadata(dataset)
        self._set_data(dataset)

    def _set_metadata(self, entry):
        #print(entry['instrument'].values())
        self.probe = "x-rays"

        # parse date into datetime object
        self.date = datetime.datetime.fromtimestamp(time.mktime(entry['start_time']))

        self.description = entry['comment']
        self.instrument = 'RigakuXray'
        self.detector.deadtime = np.array([0.0]) # sorta true.
        self.detector.deadtime_error = np.array([0.0]) # also kinda true.

        self.sample.name = entry['sample']
        self.sample.description = ""
        self.monitor.base = 'TIME'
        self.monitor.time_step = 0.001  # assume 1 ms accuracy on reported clock
        self.monitor.deadtime = 0.0
        self.polarization = "unpolarized"

    def _set_data(self, data):
        # Resolution info (returned as 1-sigma from rigaku reader)
        self.angular_resolution = data['angular_divergence']
        self.slit1.distance = data['slit1_distance']
        self.slit2.distance = data['slit2_distance']
        self.slit3.distance = data['slit3_distance']
        self.slit4.distance = data['slit4_distance']
        self.slit1.x = data['axis']['IncidentSlitBox'][2]
        self.slit2.x = data['axis']['IncidentAxdSlit'][2]
        self.slit3.x = data['axis']['ReceivingSlitBox1'][2]
        self.slit4.x = data['axis']['ReceivingSlitBox2'][2]

        self.detector.counts = data['y']
        self.detector.counts_variance = data['y_err']**2
        self.detector.dims = self.detector.counts.shape
        attenuation = data['axis']['Attenuator'][2]
        if attenuation != 0. and attenuation != 1.:
            self.detector.counts /= attenuation
            self.detector.counts_variance /= attenuation**2
        n = self.detector.dims[0]
        self.points = n
        self.detector.wavelength = np.ones(n) * data['wavelength']
        self.detector.wavelength_resolution = np.ones(n) * data['wavelength_resolution']
        self.monitor.counts = np.zeros(n)
        self.monitor.counts_variance = np.zeros(n)
        self.monitor.count_time = data['count_time']
        sample = data['axis']['Omega'][2]
        detector = data['axis']['TwoTheta'][2]
        offset = sample - detector/2
        scan_axis = data['scan_axis']
        if scan_axis in ["TwoThetaOmega", "TwoThetaTheta"]:
            self.sample.angle_x = data['x']/2 + offset
            self.detector.angle_x = data['x']
            self.scan_value = [self.sample.angle_x, self.detector.angle_x]
            self.scan_units = ['degrees', 'degrees']
            self.scan_label = ['theta', 'two_theta']
            if offset > 0:
                self.intent = refldata.Intent.backp
            elif offset < 0:
                self.intent = refldata.Intent.backm
            else:
                self.intent = refldata.Intent.spec
        elif scan_axis == 'Omega':
            self.sample.angle_x = data['x']
            self.detector.angle_x = np.ones(n) * detector
            self.scan_value = [self.sample.angle_x]
            self.scan_units = ['degrees']
            self.scan_label = ['theta']
            self.intent = refldata.Intent.rock3
        elif scan_axis == 'TwoTheta':
            self.sample.angle_x = np.ones(n) * sample
            self.detector.angle_x = data['x']
            self.scan_value = [self.sample.angle_x]
            self.scan_units = ['degrees']
            self.scan_label = ['theta']
            self.intent = refldata.Intent.rock4
        else:
            raise ValueError("Unknown scan type " + scan_axis)
        self.sample.angle_x_target = self.sample.angle_x
        self.detector.angle_x_target = self.detector.angle_x
        self.Qz_target = np.nan


class XRDMLRefl(refldata.ReflData):
    """
    Malvern Panalytical (.xrdml) raw reflectometry file.

    See :class:`refldata.ReflData` for details.
    """
    format = "XRDMLRaw"

    def __init__(self, xrdml_file, entryid, filename):
        super(XRDMLRefl, self).__init__()
        self.entry = "E"+str(entryid+1)  # 1-origin entry number for each entry
        self.path = os.path.abspath(filename)
        self.name = os.path.basename(filename).split('.')[0]
        self.filenumber = self.name # since we don't have a real filenumber
        #import pprint; pprint.pprint(entry)
        self._set_metadata(xrdml_file)
        self._set_data(xrdml_file)

    def _set_metadata(self, entry):
        #print(entry['instrument'].values())
        self.probe = "x-rays"

        # parse date into datetime object
        self.date = datetime.datetime.fromisoformat(entry["startTimeStamp"])

        self.description = entry['comment']
        self.instrument = 'Malvern Panalytical'
        # 1-sigma angular resolution (degrees) reported by Bruker.  Our own
        # measurements give a similar value (~ 0.033 degrees FWHM)
        #nominal_resolution = 0.03
        self.angular_resolution = None
        self.slit1.distance = -entry['incidentRadius']
        self.slit1.x = entry['sourceLineWidth']
        self.slit2.distance = -entry['divergenceSlitDistance']
        self.slit2.x = entry['divergenceSlitHeight']
        self.slit3.distance = entry['diffractedRadius']
        self.slit3.x = entry['receivingSlitHeight']

        self.slit1.y = self.slit2.y = 20.0 # Note: back slits unused in reduction

        ratio = entry['ratioKAlpha2KAlpha1']
        self.detector.wavelength = (entry['kAlpha1'] + ratio * entry['kAlpha2']) / (1.0 + ratio)
        # Var(Z)=p(1)σ_1^2+ p(2)σ_2^2+p(1)p(2)(μ1−μ2)2
        # from table II in https://journals.aps.org/pra/pdf/10.1103/PhysRevA.37.2404
        # width_kAlpha1 = FWHM2sigma(0.000461)
        # width_kAlpha2 = FWHM2sigma(0.00061)
        # probability of kAlpha2:
        p = ratio / (1 + ratio)
        # self.detector.wavelength_resolution = np.sqrt((1-p) * width_kAlpha1**2 + p * width_kAlpha2**2 + (1-p) * p * (entry['kAlpha1'] - entry['kAlpha2'])**2)
        # the width of the line seems to make no significant contribution...
        self.detector.wavelength_resolution = np.sqrt((1-p) * p * (entry['kAlpha1'] - entry['kAlpha2'])**2)

        #print("res:", self.angular_resolution, self.detector.wavelength_resolution, self.detector.wavelength)
        self.detector.deadtime = np.array([0.0]) # sorta true.
        self.detector.deadtime_error = np.array([0.0]) # also kinda true.

        self.sample.name = entry['sample_id']
        self.sample.description = entry['sample_name']
        self.monitor.base = 'TIME'
        self.monitor.time_step = 0.001  # assume 1 ms accuracy on reported clock
        self.monitor.deadtime = 0.0
        self.polarization = "unpolarized"

    def _set_data(self, data):
        #for k,v in sorted(data.items()): print(k, v)
        intents = {
            'Phi': 'rock sample',
            'Omega': 'rock sample',
            '2Theta': 'rock detector',
        }

        scanAxis = data['scanAxis']
        self.intent = intents.get(scanAxis, 'specular')

        attenuation = data['attenuation']
        counts = data['counts']
        self.detector.counts = counts * attenuation
        self.detector.counts_variance = counts * attenuation**2
        self.detector.dims = self.detector.counts.shape
        self.attenuation = attenuation
        n = self.detector.dims[0]
        self.points = n
        self.monitor.counts = np.zeros_like(self.detector.counts)
        self.monitor.counts_variance = np.zeros_like(self.detector.counts)
        self.monitor.count_time = np.ones_like(self.detector.counts) * data['count_time']
        if scanAxis == 'Phi':
            self.sample.angle_x = data['Phi']
            self.detector.angle_x = -data['Phi']
        else:
            self.sample.angle_x = data['Omega']
            self.detector.angle_x = data['2Theta']

        self.sample.angle_x_target = self.sample.angle_x
        self.detector.angle_x_target = self.detector.angle_x
        self.scan_value = [self.sample.angle_x, self.detector.angle_x]
        self.scan_units = ['degrees', 'degrees']
        self.scan_label = ['theta', 'two_theta']
        self.Qz_target = np.nan

def demo():
    import sys
    from .load import setup_fetch, fetch_uri
    from .scale import apply_norm
    from .steps import divergence
    if len(sys.argv) == 1:
        print("usage: python -m reflred.xrawref file...")
        sys.exit(1)
    setup_fetch()
    plotted_datasets = 0
    for uri in sys.argv[1:]:
        try:
            entries = fetch_uri(uri, loader=load_entries)
        except Exception as exc:
            print("Error while loading", uri, ':', str(exc))
            #traceback.print_exc(); raise
            continue

        # print the first entry
        #print(entries[0])

        # plot all the entries
        #pylab.figure()
        for entry in entries:
            entry = divergence(entry)
            apply_norm(entry, base='time')
            entry.plot()
            plotted_datasets += 1

    if plotted_datasets:
        import pylab
        pylab.legend()
        pylab.show()
    else:
        print("no data to plot")

if __name__ == "__main__":
    demo()
