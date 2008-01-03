# This program is public domain
"""
Default settings for the NCNR NG-1 reflectometer.

These may change periodically, so be sure to check for updates.
"""

import numpy
from numpy import inf
import reflectometry.reduction.icpformat as icp

def register_extensions(registry):
    for file in ['.na1', '.nb1', '.nc1', '.nd1', '.ng1']:
        registry[file] = NG1Icp
        registry[file+'.gz'] = NG1Icp

    for file in ['.ca1', '.cb1', '.cc1', '.cd1', '.cg1']:
        registry[file] = NG1Icp
        registry[file+'.gz'] = NG1Icp


class NG1Icp(refldata.ReflData):
    radiation = "neutron"
    format = "NCNR ICP"

    # The following allows the user to override the wavelength 
    # all files in a dataset to compensate for an incorrectly
    # recorded wavelength in ICP.
    _wavelength_override = {}
    def _pencil_detector(self):
        """
        Pencil detector on NG-1.
        """
        # Detector saturates at 15000 counts/s.  The efficiency curve above 
        # 15000 has not been measured.
        self.detector.efficiency = numpy.array([1,0,15000],'f')
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
        maxbin = 256
        width = 25.4*4 # mm
        self.detector.width_x = numpy.ones(256,'f')*(width/(maxbin-minbin))
        self.detector.center_x = 0
        self.detector.width_y = 20  # mm; TODO: Is NG-1 PSD about 10 cm x 2 cm
    
    def __init__(self, fields):
        super(ReflIcp,self).__init__(args, kw)
        self.filename = os.path.abspath(filename)

        self.detector.distance = 36*25.4/1000.  # NG-1 detector closer than slit 4?
        self.slit1.distance = -75*25.4 # mm
        self.slit2.distance = -14*25.4 # mm
        self.slit3.distance = 9*25.4 # mm
        self.slit4.distance = 42*25.4 # mm
        self.detector.rotation = 0 # degrees
        
        fields = icpformat.summary(self.filename)
        if fields['scantype'] != 'I':
            raise TypeError, "Only I-Buffers supported for NG-7"

        self.date = fields['date']
        self.name = fields['filename']
        self.description = fields['comment']
        self.dataset = self.name[:5]

        if fields['scantype'] != 'I':
            raise TypeError, "Only I-Buffers supported for NG-1"
        
        if fields['PSD']:
            self.instrument = 'NCNR NG-1 PSD'
            self._psd()
        else:
            self.instrument = 'NCNR NG-1'
            self._pencil_detector()
        self.display_monitor = fields['monitor']*fields['prefactor']

    def load(self):
        fields = icp.read(self.filename)
        
        self.detector.wavelength \
            = icp.check_wavelength(fields, 4.75, NG1Icp._wavelength_override)

        # Slits are either stored in the file or available from the
        # motor information.  For non-reflectometry scans they may
        # not be available.
        if 'A1' in fields['columns']:
            self.slit1.x = fields['columns']['A1']
        if 'A2' in fields['columns']:
            self.slit2.x = fields['columns']['A2']
        if 'A5' in fields['columns']:
            self.slit3.x = fields['columns']['A5']
        if 'A6' in fields['columns']:
            self.slit4.x = fields['columns']['A6']

        # Angles are either stored in the file or can be calculated
        # from the motor details.  For non-reflectometry scans they
        # may not be available.
        if 'A3' in fields['columns']:
            self.sample.angle_x = fields['columns']['A3']
        if 'A4' in fields['columns']:
            self.detector.angle_x = fields['columns']['A4']

        # Polarization was extracted from the comment line
        self.polarization = fields['polarization']

        # Monitor counts may be recorded or may be inferred from header
        if 'monitor' in fields['columns']:
            # Prefer the monitor column if it exists
            self.monitor.counts = fields['columns']['monitors']
        elif fields['count_type'] == 'NEUT':
            # if count by neutron, the 'monitor' field stores counts
            self.monitor.counts \
                = fields['monitor']*fields['prefactor']*numpy.ones(pts,'i')
        else:
            # Need monitor rate for normalization; the application
            # will have to provide the means of setting the rate
            # and computing the counts based on that rate.
            pass

        # Counting time may be recorded or may be inferred from header
        if fields['count_type'] == 'TIME':
            # if count by time, the 'monitor' field stores seconds
            self.monitor.count_time = fields['monitor']*numpy.ones(pts,'f')
        elif 'time' in fields['columns']:
            self.monitor.count_time = files['columns']['time']
        else:
            # Need monitor rate for normalization; the application
            # will have to provide the means of setting the rate
            # and computing the time based on that rate.
            pass

        """  This does not belong in self.qx/self.qz
        # Figure out Qx-Qz for sample angle/detector center
        if self.sample.angle_x != None and self.detector.angle_x != None:
            A,B = self.sample.angle_x, self.detector.angle_x
            Qx,Qz = refldata.AB_to_QxQz(A,B,self.detector.wavelength)
            self.qx,self.qz = Qx,Qz
        """
