import os
import icpformat as icp
import refldata

def register_extensions(registry):
    for file in ['.ng7']:
        registry[file] = readentries
        registry[file+'.gz'] = readentries

def readentries(filename):
    # ICP files have one entry per filename
    return [NG7Icp(filename)]

class NG7Icp(refldata.ReflData):
    probe = "neutron"
    format = "NCNR ICP (NG-7)"

    def __init__(self, filename):
        super(ReflIcp,self).__init__(args, kw)
        self.filename = os.path.abspath(filename)

        self.detector.distance = 36*25.4/1000.  # NG-1 detector closer than slit 4?
        self.slit1.distance = -75*25.4 # mm
        self.slit2.distance = -14*25.4 # mm
        self.slit3.distance = 9*25.4 # mm
        self.slit4.distance = 42*25.4 # mm
        self.detector.rotation = 0 # degrees

        fields = icp.summary(filename)
        if fields['scantype'] != 'I':
            raise TypeError, "Only I-Buffers supported for NG-7"

        self.date = fields['date']
        self.name = fields['filename']
        self.description = fields['comment']
        self.dataset = self.name[:5]

        if fields['count_type']=='TIME':
            # Override the default monitor base of 'counts'
            self.monitor.base='time'

        if fields['PSD']:
            self.instrument = 'NCNR NG-7 PSD'
            self._psd()
        else:
            self.instrument = 'NCNR NG-7'
            self._pencil_detector()
        self.display_monitor = 1

    def _pencil_detector(self):
        """
        Pencil detector on NG-7.
        """
        #    rate     correction factor
        NG7monitor_calibration = """
              304     1.0   ;
             1788     1.0074;
             6812     1.0672;
            13536     1.1399;
            19426     1.2151;
            24022     1.2944;
            27771     1.370 ;
            31174     1.429 ;
        """
        C = numpy.matrix(Ng7monitor_calibration)
        self.detector.saturation = numpy.array(C[0,:],100./C[1,:])
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
        self.detector.efficiency = numpy.array([1,0,8000],'f')
        minbin = 9
        maxbin = 246
        width = 100
        self.detector.width_x = numpy.ones(256,'f')*(width/(maxbin-minbin))
        self.detector.center_x = 0
        self.detector.width_y = 100 # TODO: Is NG-7 PSD width 10 cm?

    def load(self):
        fields = icp.read(self.filename)
        self.detector.wavelength \
            = icp.check_wavelength(fields, 4.76, NG7Icp._wavelength_override)
        if 'monitor' in fields['columns']:
            self.monitor.counts = fields['columns']['monitor']
        elif 'qz' in fields['columns']:
            # NG7 automatically increases count times as Qz increases
            monitor, prefactor = fields['monitor'],fields['prefactor']
            Mon1, Exp = fields['Mon1'],fields['Exp']
            Qz = fields['columns']['qz']
            self.monitor.counts = prefactor*(monitor + Mon1 * abs(Qz)**Exp)

        if 'S1' in fields['columns']:
            self.slit1.x = fields['columns']['S1']
        if 'S2' in fields['columns']:
            self.slit2.x = fields['columns']['S2']
        if 'S3' in fields['columns']:
            self.slit3.x = fields['columns']['S3']
        if 'S4' in fields['columns']:
            self.slit4.x = fields['columns']['S4']
        if 'qz' in fields['columns']:
            qx = fields['columns'] if 'qx' in fields['columns'] else 0
            qz = fields['columns']['qz']
            A,B = refldata.QxQz_to_AB(qx,qz,self.detector.wavelength)
            self.sample.angle_x,self.detector.angle_x = A,B
