# This program is public domain

"""
Load a Bruker raw file into a reflectometry data structure.
"""
import os
import datetime

import numpy as np

from .. import unit
from .. import iso8601
from . import bruker
from . import refldata


def load_from_string(filename, data, entries=None):
    """
    Load a nexus file from a string, e.g., as returned from url.read().
    """
    from StringIO import StringIO
    fd = StringIO(data)
    entries = load_entries(filename, fd, entries=entries)
    fd.close()
    return entries


def load_from_uri(uri, entries=None, url_cache="/tmp"):
    """
    Load a nexus file from disk or from http://, https:// or file://.

    Remote files are cached in *url_cache*.  Use None to fetch without caching.
    """
    import os

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
    for name,entry in file.items():
        if entry.attrs.get('NX_class', None) == 'NXentry':
            data = NCNRNeXusRefl(entry, name, filename)
            measurements.append(data)
    if file_obj is None:
        file.close()
    return measurements


def load_entries(filename, file_obj=None, entries=None):
    """
    Load the summary info for the entry in a Bruker file.
    """
    if file_obj is None:
        entry = bruker.load(filename)
    else:
        entry = bruker.loads(file_obj.read())
        
    data = BrukerRawRefl(entry, 'entry', filename)
    data.load(entry)
    return [data]


class BrukerRawRefl(refldata.ReflData):
    """
    Bruker raw reflectometry file.

    See :class:`refldata.ReflData` for details.
    """
    format = "BrukerRaw"
    trajectory_intents = {
        'locked coupled': 'specular',
        'unlocked coupled': 'specular',
        'detector scan': 'rock detector',
        'rocking curve': 'rock sample',
        'phi scan': 'rock sample'
    }

    def __init__(self, entry, entryname, filename):
        super(BrukerRawRefl,self).__init__()
        self.entry = 'entry'
        self.path = os.path.abspath(filename)
        self.name = os.path.basename(filename).split('.')[0]
        #import pprint; pprint.pprint(entry)
        self._set_metadata(entry)

    def _set_metadata(self, entry):
        #print(entry['instrument'].values())
        self.probe = 'xray'

        # parse date into datetime object
        month,day,year = [int(v) for v in entry['date'].split('/')]
        hour,minute,second = [int(v) for v in entry['time'].split(':')]
        self.date = datetime.datetime(year+2000,month,day,hour,minute,second)

        self.description = entry['comment']
        self.instrument = 'BrukerXray'
        self.slit1.distance = -275.5
        self.slit2.distance = -192.7
        self.slit3.distance = +175.0
        self.slit1.x = 0.03 # TODO: check
        self.slit2.x = 0.03 # TODO: check
        self.slit1.y = self.slit2.y = 20.0 # TODO: doesn't matter
        #self.slit4.distance = data_as(entry,'instrument/predetector_slit2/distance','mm')
        #self.detector.distance = data_as(entry,'instrument/detector/distance','mm')
        #self.detector.rotation = data_as(entry,'instrument/detector/rotation','degree')
        self.detector.wavelength = entry['alpha_average']
        self.detector.wavelength_resolution = 0.001*self.detector.wavelength
        self.detector.deadtime = 0.0 # sorta true.
        self.detector.deadtime_error = 0.0 # also kinda true.
        
        self.sample.name = entry['samplename']
        self.sample.description = ""
        raw_intent = bruker.SCAN_TYPE.get(entry['data'][0]['scan_type'], "")
        self._raw_intent = raw_intent
        if raw_intent in self.trajectory_intents:
            self.intent = self.trajectory_intents[raw_intent]
        self.monitor.base = 'TIME'
        self.monitor.time_step = 0.001  # assume 1 ms accuracy on reported clock
        self.monitor.deadtime = 0.0 
        self.polarization = "unpolarized"

    def load(self, entry):
        das = entry['data'][0]
        attenuator_state = das['detslit_code']
        self.detector.counts = das['values']['count']
        self.detector.counts_variance = self.detector.counts.copy()
        if attenuator_state.strip().lower() == 'in':
            ATTENUATOR = 100.
            #self.v = self.detector.counts*ATTENUATOR
            #self.dv = np.sqrt(self.detector.counts_variance) * ATTENUATOR
            self.detector.counts *= ATTENUATOR
            self.detector.counts_variance *= ATTENUATOR**2
        self.detector.dims = self.detector.counts.shape
        n = self.detector.dims[0]
        self.monitor.counts = np.ones_like(self.detector.counts)
        self.monitor.counts_variance = np.zeros_like(self.detector.counts)
        self.monitor.count_time = np.ones_like(self.detector.counts)*das['step_time']
        if self._raw_intent in ["locked coupled", "unlocked coupled"]:
            self.sample.angle_x = das['theta_start'] + np.arange(n, dtype='float') * das['increment_1']/2.0
            self.detector.angle_x = das['two_theta_start'] + np.arange(n, dtype='float') * das['increment_1']
            self.sample.angle_x_target = self.sample.angle_x
            self.detector.angle_x_target = self.detector.angle_x
        elif self._raw_intent == 'detector scan':
            self.sample.angle_x = das['theta_start']
            self.detector.angle_x = das['two_theta_start'] + np.arange(n, dtype='float') * das['increment_1']
            self.sample.angle_x_target = self.sample.angle_x
            self.detector.angle_x_target = self.detector.angle_x
        elif self._raw_intent in ['rocking curve', 'phi scan']:
            # this may not be right at all.  I can't understand what reflred/loadraw.tcl is doing here
            self.sample.angle_x = das['theta_start'] - np.arange(n, dtype='float') * das['increment_1']
            self.detector.angle_x = das['two_theta_start'] + np.arange(n, dtype='float') * das['increment_1']
            self.sample.angle_x_target = self.sample.angle_x
            self.detector.angle_x_target = self.detector.angle_x
        else:
            raise ValueError("Unknown sample angle in file")
        self.Qz_target = np.NaN
        
        self.scan_value = []
        self.scan_units = []
        self.scan_label= []

def demo():
    from .scale import apply_norm
    import sys
    if len(sys.argv) == 1:
        print("usage: python -m reflred.steps.xrawref file...")
        sys.exit(1)
    for filename in sys.argv[1:]:
        try:
            entries = load_from_uri(filename)
        except Exception as exc:
            print("**** "+str(exc)+" **** while reading "+filename)
            continue

        # print the first entry
        #print(entries[0])

        # plot all the entries
        import pylab
        #pylab.figure()
        for entry in entries:
            apply_norm(entry, base='time')
            entry.plot()
    pylab.legend()
    pylab.show()

if __name__ == "__main__":
    demo()
