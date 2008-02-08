# This program is public domain
"""
Data file reader for NCNR NG-7 data.  

"""

import os, numpy
from . import icpformat
from . import refldata

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
    format = "NCNR ICP (NG-7)"

    # The following allows the user to override the wavelength 
    # all files in a dataset to compensate for an incorrectly
    # recorded wavelength in ICP.
    _wavelength_override = {}
    def __init__(self, path, *args, **kw):
        super(NG7Icp,self).__init__(*args, **kw)
        self.path = os.path.abspath(path)

        # Note: these constants likely depend on the date that the file 
        # was created.
        # Why is NG-1 detector closer than slit 4?
        self.detector.distance = 36*25.4 # mm 
        self.slit1.distance = -75*25.4 # mm
        self.slit2.distance = -14*25.4 # mm
        self.slit3.distance = 9*25.4 # mm
        self.slit4.distance = 42*25.4 # mm
        self.detector.rotation = 0 # degrees

        data = icpformat.summary(path)
        if data.scantype != 'R':
            raise TypeError, "Only R-Buffers supported for NG-7"

        self.date = data.date
        self.name = data.filename
        self.description = data.comment
        self.dataset = self.name[:5]

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
        #    rate     correction factor
        calibration = """
              304     1.0   ;
             1788     1.0074;
             6812     1.0672;
            13536     1.1399;
            19426     1.2151;
            24022     1.2944;
            27771     1.370 ;
            31174     1.429
        """
        C = numpy.matrix(calibration).A
        C[1,:] = 1/C[1,:] # Use efficiency rather than attenuation
        self.detector.saturation = C
        # The following widths don't really matter for point detectors, but
        # for completeness we can put in the values.
        self.detector.width_x = 25.4*6 # mm TODO: Is NG-1 pencil det. 6" long?
        self.detector.width_y = 25.4*1 # mm TODO: Is NG-1 pencil det. 1" wide?
        self.detector.center_x = 0
        self.detector.center_y = 0
        self.detector.rotation = 0

    def _psd(self):
        """
        PSD on NG-7.
        """
        # TODO: NG-7 PSD saturates at 8000 counts/s?
        self.detector.efficiency = numpy.array([1,8000,0],'f')
        minbin = 9
        maxbin = 246
        width = 100
        self.detector.width_x = numpy.ones(256,'f')*(width/(maxbin-minbin))
        self.detector.center_x = 0
        self.detector.width_y = 100 # TODO: Is NG-7 PSD width 10 cm?

    def loadcounts(self):
        data = icpformat.read(self.path)
        return data.counts

    def load(self):
        data = icpformat.read(self.path)
        self.detector.wavelength \
            = data.check_wavelength(4.76, NG7Icp._wavelength_override)
        if 'monitor' in data:
            self.monitor.counts = data.column.monitor
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
            qx = data.column.qx if 'qx' in data else 0
            qz = data.column.qz
            A,B = refldata.QxQz_to_AB(qx,qz,self.detector.wavelength)
            self.sample.angle_x,self.detector.angle_x = A,B

        # TODO: if the dataset is large, set up a weak reference instead
        self.detector.counts = data.counts
