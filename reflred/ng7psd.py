#!/usr/bin/env python
import numpy as np

from .refldata import ReflData
from .nexusref import load_nexus_entries, nexus_common
from .nexusref import data_as, str_data
from .nexusref import TRAJECTORY_INTENTS
from .resolution import FWHM2sigma

def load_metadata(filename, file_obj=None):
    """
    Load the summary info for all entries in a NeXus file.
    """
    return load_nexus_entries(filename, file_obj=file_obj,
                              meta_only=True, entry_loader=Candor)

def load_entries(filename, file_obj=None, entries=None):
    #print("loading", filename, file_obj)
    return load_nexus_entries(filename, file_obj=file_obj, entries=entries,
                              meta_only=False, entry_loader=NG7PSD)

WAVELENGTH = 4.768
WAVELENGTH_DISPERSION = 0.025
DETECTOR_DISTANCE = 2006.
PIXEL_WIDTH = 100./256
PIXEL_OFFSET = np.linspace(0, 100, 257)[:-1] - 50 + 1/256

class NG7PSD(ReflData):
    """
    NeXus reflectometry entry.

    See :class:`refldata.ReflData` for details.
    """
    format = "NeXus"
    probe = "neutron"

    def __init__(self, entry, entryname, filename):
        super(NG7PSD, self).__init__()
        nexus_common(self, entry, entryname, filename)

    def load(self, entry):
        #print(entry['instrument'].values())
        das = entry['DAS_logs']
        n = self.points
        raw_intent = str_data(das, 'trajectoryData/_scanType')
        if raw_intent in TRAJECTORY_INTENTS:
            self.intent = TRAJECTORY_INTENTS[raw_intent]

        # Polarizers
        self.polarization = ''

        # Monochromator
        self.monochromator.wavelength = data_as(entry, 'instrument/monochromator/wavelength', 'Ang', rep=n, NA=None)
        self.monochromator.wavelength_resolution = data_as(entry, 'instrument/monochromator/wavelength_error', 'Ang', rep=n, NA=None)
        if self.monochromator.wavelength is None:
            self.warn("Wavelength is missing; using %.3f A"
                      % (WAVELENGTH,))
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
        for k, slit in enumerate((self.slit1, self.slit2, self.slit3)):
            x = 'slitAperture%d/softPosition'%(k+1)
            x_target = 'slitAperture%d/desiredSoftPosition'%(k+1)
            slit.x = data_as(das, x, 'mm', rep=n)
            slit.x_target = data_as(das, x_target, 'mm', rep=n)
            #y = 'vertSlitAperture%d/softPosition'%(k+1)
            #y_target = 'vertSlitAperture%d/desiredSoftPosition'%(k+1)
            #slit.y = data_as(das, y, 'mm', rep=n)
            #slit.y_target = data_as(das, y_target, 'mm', rep=n)

        # Detector
        self.detector.wavelength = self.monochromator.wavelength
        self.detector.wavelength_resolution = self.monochromator.wavelength_resolution
        self.detector.deadtime = data_as(entry, 'instrument/PSD/dead_time', 'us')
        self.detector.deadtime_error = data_as(entry, 'instrument/PSD/dead_time_error', 'us')
        self.detector.distance = data_as(entry, 'instrument/PSD/distance', 'mm')
        self.detector.rotation = data_as(entry, 'instrument/PSD/rotation', 'degree')
        if self.detector.distance is None:
            self.detector.distance = DETECTOR_DISTANCE
            self.warn("PSD distance is missing; using %.1f mm"
                      % (self.detector.distance,))
        # TODO: ignore detector distance increase with q (5mm over 2m at q=0.2)
        # ... and the corresponding 1/4 % decrease in divergence per pixel
        # If you really want to correct for it then use the following:
        #    d = x * sqrt(tan(theta)^2 + 1)
        #      = nominal_distance * sqrt(tan(radians(detector_angle))**2 + 1)
        # or per pixel in the Td_target code below:
        #    d = sqrt(x**2 + pixel_y**2)

        # TODO: ng7r/nexus/config.js needs to record info about the PSD

        # Counts ---  verify that we are pulling data from the PSD
        roi_device = str_data(das, 'counter/roiAgainst')
        if roi_device != "linearDetector":
            raise TypeError("expected roiAgainst to be linearDetector")
        self.detector.counts = np.asarray(data_as(das, roi_device + '/counts', ''), 'd')
        self.detector.counts_variance = self.detector.counts.copy()
        self.detector.dims = self.detector.counts.shape[1:]
        npixels = self.detector.dims[0]
        self.detector.width_x = data_as(entry, 'instrument/PSD/x_pixel_size', 'mm', rep=npixels)
        self.detector.offset_x = data_as(entry, 'instrument/PSD/x_pixel_offset', 'mm', rep=npixels)
        self.detector.mask = data_as(entry, 'instrument/PSD/pixel_mask', '')
        if self.detector.width_x is None:
            self.detector.width_x = np.full(npixels, PIXEL_WIDTH)
        if self.detector.offset_x is None:
            self.detector.offset_x = PIXEL_OFFSET
        if self.detector.mask is None:
            self.detector.mask = np.array([1] + [0]*(npixels-1))

        # Angles
        if 'q' not in das:
            raise ValueError("Unknown sample angle in file")
        # Ignore sampleTilt for now since it is arbitrary.  NG7 is not
        # using zeros for the sampleTilt motor in a predictable way.
        #tilt = data_as(das, 'sampleTilt/softPosition', 'degree', rep=n)
        tilt = 0.
        # TODO: is thetaIncident tied to sample elevation actual or target?
        # We could recompute theta from sample elevation softPosition and
        # desiredSoftPosition respectively if we care.
        theta = data_as(das, 'q/thetaIncident', 'degree', rep=n)
        self.sample.angle_x = theta + tilt
        self.detector.angle_x = 2*theta
        #tilt_target = data_as(das, 'sampleTilt/desiredSoftPosition', 'degree', rep=n)
        self.sample.angle_x_target = self.sample.angle_x
        self.detector.angle_x_target = self.detector.angle_x

    @property
    def Ti_target(self):
        return self.sample.angle_x[:, None] # [n, 1]

    @property
    def Td_target(self):
        # Assuming the detector is vertical at distance x from the
        # sample center at q=0.
        x = self.detector.distance  # [1]
        theta = np.radians(self.detector.angle_x) # [n]
        y = np.tan(theta)*x  # [n] * [1] = [n]
        center = self.detector.center[0]  # [1]
        offset = self.detector.offset_x # [p]
        pixel_y = y[:, None] + offset[None, :] + center # [n, p]
        pixel_theta = np.arctan2(pixel_y, x) # [n, p]
        return np.degrees(pixel_theta)

    @property
    def Ti(self):
        return self.Ti_target

    @property
    def Td(self):
        return self.Td_target

    @property
    def Li(self):
        return self.monochromator.wavelength[:, None]

    @property
    def Ld(self):
        return self.detector.wavelength[:, None]

if __name__ == "__main__":
    # Example:
    #   python -m reflred.ng7psd ncnr://ncnrdata/ng7/202001/27596/data/5ppm_NRW_0M33037.nxz.ng7
    from .nexusref import demo
    demo(loader=load_entries)
