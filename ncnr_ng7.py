# This program is public domain
"""
Data file reader for NCNR NG-7 data.  

"""

import os, numpy
from . import icpformat
from . import refldata
from . import properties


# Instrument parameters
# As instrument parameters change add additional lines to this file
# indicating the new value and the date of the change.  The order of
# the entries does not matter.  The timestamp on the file will
# determine which value will be used.
# The format of the entries should be:
#      default.NAME = (VALUE, 'YYYY-MM-DD')  # value in effect after DD/MM/YYYY
#      default.NAME = (VALUE, '')          # value in effect at commissioning
default = properties.DatedValues()
default.wavelength = (4.76,'')  # in case ICP records the wrong value

# Detector saturates at 15000 counts/s.  The efficiency curve above 
# 15000 has not been measured.
default.saturation = (numpy.array([[1,15000,0]]),'')


# NG-1 detector closer than slit 4?
default.detector_distance = (2000., '') # mm
default.psd_width = (100, '') # mm
default.slit1_distance = (-75*25.4, '') # mm
default.slit2_distance = (-14*25.4, '') # mm
default.slit3_distance = (9*25.4, '') # mm
default.slit4_distance = (42*25.4, '') # mm

#    rate     correction factor
saturation = """
     304     1.0   ;
    1788     1.0074;
    6812     1.0672;
   13536     1.1399;
   19426     1.2151;
   24022     1.2944;
   27771     1.370 ;
   31174     1.429
"""
C = numpy.matrix(saturation).A
C[1,:] = 1/C[1,:] # Use efficiency rather than attenuation
default.pencil_saturation = (C, '')
# The following widths don't really matter for point detectors, but
# for completeness we can put in the values.
default.pencil_length = (25.4*6,'') # mm TODO: Is NG-7 pencil det. 6" long
default.pencil_width = (25.4*1,'') # mm TODO: Is NG-7 pencil det. 1" wide?

# TODO: NG-7 PSD saturates at 8000 counts/s?
default.psd_saturation = (numpy.array([1,8000],'f'),'')
default.psd_minbin = (9,'')
default.psd_maxbin = (246,'')
default.psd_width = (100,'')
default.psd_pixels = (256,'')
default.monitor_timestep = (60./100,'') # s ; ICP records 1/100ths of min 

# ===================================================================

def register_extensions(registry):
    for file in ['.ng7']:
        registry[file] = readentries
        registry[file+'.gz'] = readentries

def readentries(path):
    # ICP files have one entry per file
    return [NG7Icp(path)]

class NG7Icp(refldata.ReflData):
    # Instrument description
    probe = "neutron"
    format = "NCNR ICP"
    instrument = "NCNR NG-7"

    # The following allows the user to override the wavelength 
    # all files in a dataset to compensate for an incorrectly
    # recorded wavelength in ICP.
    _wavelength_override = {}
    def __init__(self, path, *args, **kw):
        super(NG7Icp,self).__init__(*args, **kw)
        self.path = os.path.abspath(path)


        data = icpformat.summary(path)
        if data.scantype != 'R':
            raise TypeError, "Only R-Buffers supported for NG-7"

        self.date = data.date
        self.name = data.filename
        self.description = data.comment
        self.dataset = self.name[:5]

        self.default = default(str(data.date))
        self.detector.distance = self.default.detector_distance
        self.slit1.distance = self.default.slit1_distance
        self.slit2.distance = self.default.slit2_distance
        self.slit3.distance = self.default.slit3_distance
        self.slit4.distance = self.default.slit4_distance
        self.detector.rotation = 0 # degrees
        self.monitor.time_step = self.default.monitor_timestep

        if data.count_type=='TIME':
            # Override the default monitor base of 'counts'
            self.monitor.base='time'

        if data.PSD:
            self.instrument = 'NCNR NG-7 PSD'
            self._psd()
        else:
            self.instrument = 'NCNR NG-7'
            self._pencil_detector()
        self.display_monitor = 1

        # Callback for lazy data
        self.detector.loadcounts = self.loadcounts


    def _pencil_detector(self):
        """
        Pencil detector on NG-7.
        """
        self.detector.saturation = self.default.pencil_saturation
        self.detector.width_x = self.default.pencil_length
        self.detector.width_y = self.default.pencil_width
        self.detector.center_x = 0
        self.detector.center_y = 0
        self.detector.rotation = 0

    def _psd(self):
        """
        PSD on NG-7.
        """
        self.detector.saturation = self.default.psd_saturation
        width = self.default.psd_width
        minbin,maxbin = self.default.psd_minbin,self.default.psd_maxbin
        pixels = self.default.psd_pixels
        self.detector.width_x = numpy.ones(pixels,'f')*(width/(maxbin-minbin))
        self.detector.center_x = 0
        self.detector.width_y = self.default.psd_height

    def loadcounts(self):
        data = icpformat.read(self.path)
        return data.counts

    def load(self):
        data = icpformat.read(self.path)
        self.detector.wavelength \
            = data.check_wavelength(self.default.wavelength, 
                                    NG7Icp._wavelength_override)
        if 'monitor' in data:
            self.monitor.counts = data.column.monitor
        if 'time' in data:
            self.monitor.count_time = data.column.time*60
        elif 'qz' in data:
            # NG7 automatically increases count times as Qz increases
            monitor, prefactor = data.monitor,data.prefactor
            Mon1, Exp = data.Mon1,data.Exp
            Qz = data.column.qz
            self.monitor.counts = prefactor*(monitor + Mon1 * abs(Qz)**Exp)

        if 's1' in data: self.slit1.x = data.column.s1
        if 's2' in data: self.slit2.x = data.column.s2
        if 's3' in data: self.slit3.x = data.column.s3
        if 's4' in data: self.slit4.x = data.column.s4
        if 'qz' in data:
            Qx = data.column.qx if 'qx' in data else 0
            Qz = data.column.qz
            A,B = refldata.QxQzL_to_AB(Qx,Qz,self.detector.wavelength)
            self.sample.angle_x,self.detector.angle_x = A,B

        # TODO: if the dataset is large, set up a weak reference instead
        self.detector.counts = data.counts
