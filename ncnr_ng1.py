# This program is public domain
"""
Data file reader for NCNR NG-1 data.  
"""

import numpy,os
from numpy import inf
from . import refldata, icpformat, properties


# Instrument parameters
# As instrument parameters change add additional lines to this file
# indicating the new value and the date of the change.  The order of
# the entries does not matter.  The timestamp on the file will
# determine which value will be used.
# The format of the entries should be:
#      default.NAME = (VALUE, 'YYYY-MM-DD')  # value in effect after DD/MM/YYYY
#      default.NAME = (VALUE, '')          # value in effect at commissioning

# =====================================================================
# NG-1 defaults
ng1default = properties.DatedValues()
ng1default.wavelength = (4.76,'')  # in case ICP records the wrong value

# Detector saturates at 15000 counts/s.  The efficiency curve above 
# 15000 has not been measured.
ng1default.saturation = (numpy.array([[1,15000,0]]),'')
ng1default.psd_saturation = (numpy.array([[1,8000,0]]),'')

# NG-1 detector closer than slit 4?
ng1default.detector_distance = (36*25.4, '') # mm
ng1default.psd_width = (20, '') # mm; TODO: Is NG-1 PSD about 10 cm x 2 cm
ng1default.slit1_distance = (-75*25.4, '') # mm
ng1default.slit2_distance = (-14*25.4, '') # mm
ng1default.slit3_distance = (9*25.4, '') # mm
ng1default.slit4_distance = (42*25.4, '') # mm
ng1default.monitor_timestep = (60./100,'') # s ; ICP records 1/100ths of min 

# =====================================================================
# CG-1 defaults
cg1default = properties.DatedValues()
cg1default.wavelength = (5.0,'')  # in case ICP records the wrong value

# Detector saturates at 15000 counts/s.  The efficiency curve above 
# 15000 has not been measured.
cg1default.saturation = (numpy.array([[1,15000,0]]),'')
cg1default.psd_saturation = (numpy.array([[1,8000,0]]),'')

# NG-1 detector closer than slit 4?
cg1default.detector_distance = (1600., '') # mm
cg1default.psd_width = (211, '') # mm; TODO: Is NG-1 PSD about 10 cm x 2 cm
cg1default.slit1_distance = (-75*25.4, '') # mm
cg1default.slit2_distance = (-14*25.4, '') # mm
cg1default.slit3_distance = (9*25.4, '') # mm
cg1default.slit4_distance = (42*25.4, '') # mm
cg1default.monitor_timestep = (60./100,'') # s ; ICP records 1/100ths of min 
cg1default.psd_minbin = (1,'')
cg1default.psd_maxbin = (608,'')
cg1default.psd_width = (100,'')
cg1default.psd_pixels = (608,'')
cg1default.monitor_timestep = (60./100,'') # s ; ICP records 1/100ths of min 

# =====================================================================

def register_extensions(registry):
    for file in ['.na1', '.nb1', '.nc1', '.nd1', '.ng1']:
        registry[file] = readentries
        registry[file+'.gz'] = readentries

    for file in ['.ca1', '.cb1', '.cc1', '.cd1', '.cg1']:
        registry[file] = readentries
        registry[file+'.gz'] = readentries

def readentries(path):
    return [NG1Icp(path)]

class NG1Icp(refldata.ReflData):
    probe = "neutron"
    format = "NCNR ICP"

    # The following allows the user to override the wavelength 
    # all files in a dataset to compensate for an incorrectly
    # recorded wavelength in ICP.
    _wavelength_override = {}
    def _pencil_detector(self):
        """
        Pencil detector on NG-1.
        """
        self.detector.saturation = self.default.saturation
        # The following widths don't really matter for point detectors, but
        # for completeness we can put in the values.
        self.detector.width_x = 150 # mm   TODO: What is the precise value?
        self.detector.width_y = 20 # mm   TODO: What is the precise value?
        self.detector.center_x = 0 # mm
        self.detector.center_y = 0 # mm
        self.detector.rotation = 0 # degree

    def _psd(self):
        """
        PSD on NG-1.
        """
        # Detector saturates at 8000 counts/s.  Maybe could use efficiency
        # calibrations like on NG-7 to support higher count rates, though
        # in practice one risks damaging the detector by exposing it to too
        # strong a beam so there is little need.
        self.detector.efficiency = numpy.array([1,0,8000],'f')
        minbin = 1
        maxbin = 512
        width = 25.4*4 # mm
        self.detector.width_x = numpy.ones(512,'f')*(width/(maxbin-minbin))
        self.detector.center_x = 0
        self.detector.width_y = 20  # mm; TODO: Is NG-1 PSD about 10 cm x 2 cm

    def _psd2d(self):
        """
        2D PSD on NG-1.
        """
        # Detector saturates at 8000 counts/s.  Maybe could use efficiency
        # calibrations like on NG-7 to support higher count rates, though
        # in practice one risks damaging the detector by exposing it to too
        # strong a beam so there is little need.
        self.detector.efficiency = numpy.array([1,0,8000],'f')
        minbin = 1
        maxbin = 512
        width = 25.4*4 # mm
        self.detector.width_x = numpy.ones(256,'f')*(width/(maxbin-minbin))
        self.detector.center_x = 0
        self.detector.width_y = self.default.psd_width

    def __init__(self, path, *args, **kw):
        super(NG1Icp,self).__init__(*args, **kw)
        self.path = os.path.abspath(path)

        data = icpformat.summary(self.path)
        if data.scantype != 'I':
            raise TypeError, "Only I-Buffers supported for %s"%self.format

        self.date = data.date
        self.name = data.filename
        self.description = data.comment
        self.dataset = self.name[:5]

        # Lookup defaults
        ext = os.path.splitext(data.filename)[1].lower()
        if ext.startswith('c'):
            self.instrument = "NCNR AND/R"
            self.default = cg1default(str(data.date))
        else:
            self.instrument = "NCNR NG-1"
            self.default = ng1default(str(data.date))

        # Plug in instrument defaults
        self.detector.distance = self.default.detector_distance
        self.slit1.distance = self.default.slit1_distance
        self.slit2.distance = self.default.slit2_distance
        self.slit3.distance = self.default.slit3_distance
        self.slit4.distance = self.default.slit4_distance
        self.detector.rotation = 0 # degrees
        self.monitor.time_step = self.default.monitor_timestep

        if data.PSD:
            self.instrument += " PSD"
            self._psd()
        else:
            self._pencil_detector()
        self.display_monitor = data.monitor*data.prefactor

        # Callback for lazy data
        self.detector.loadcounts = self.loadcounts

    def loadcounts(self):
        data = icpformat.read(self.path)
        return data.counts

    def load(self):
        data = icpformat.read(self.path)

        self.detector.wavelength \
            = data.check_wavelength(self.default.wavelength, 
                                    NG1Icp._wavelength_override)

        # Slits are either stored in the file or available from the
        # motor information.  For non-reflectometry scans they may
        # not be available.
        if 'a1' in data: self.slit1.x = data.column.a1
        if 'a2' in data: self.slit2.x = data.column.a2
        if 'a5' in data: self.slit3.x = data.column.a5
        if 'a6' in data: self.slit4.x = data.column.a6

        # Angles are either stored in the file or can be calculated
        # from the motor details.  For non-reflectometry scans they
        # may not be available.
        if 'a3' in data: self.sample.angle_x = data.column.a3
        if 'a4' in data: self.detector.angle_x = data.column.a4

        # Polarization was extracted from the comment line
        self.polarization = data.polarization

        # Monitor counts may be recorded or may be inferred from header
        if 'monitor' in data:
            # Prefer the monitor column if it exists
            self.monitor.counts = data.column.monitor
        elif data.count_type == 'NEUT':
            # if count by neutron, the 'monitor' field stores counts
            self.monitor.counts \
                = data.monitor*data.prefactor*numpy.ones(data.points,'i')
        else:
            # Need monitor rate for normalization; the application
            # will have to provide the means of setting the rate
            # and computing the counts based on that rate.
            pass

        # Counting time may be recorded or may be inferred from header
        if data.count_type == 'TIME':
            # Prefer the target value to the time column when counting by
            # time because the time column is recorded in minutes rather
            # than seconds and is not precise enough.
            # if count by time, the 'monitor' field stores seconds
            self.monitor.count_time \
                = data.monitor*data.prefactor*numpy.ones(data.points,'f')
        elif 'time' in data:
            self.monitor.count_time = data.column.time*60
        else:
            # Need monitor rate for normalization; the application
            # will have to provide the means of setting the rate
            # and computing the time based on that rate.
            pass

        # TODO: if counts are huge we may want to make this lazy
        self.detector.counts = data.counts
