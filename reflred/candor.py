#!/usr/bin/env python
import numpy as np

from .refldata import ReflData, Intent
from .nexusref import load_nexus_entries, nexus_common, get_pol
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
                              meta_only=False, entry_loader=Candor)

#: Number of detector channels per detector tube on CANDOR
NUM_CHANNELS = 54

class Candor(ReflData):
    """
    Candor data entry.

    See :class:`refldata.ReflData` for details.
    """
    format = "NeXus"
    probe = "neutron"

    def __init__(self, entry, entryname, filename):
        super(Candor, self).__init__()
        nexus_common(self, entry, entryname, filename)
        self.geometry = 'vertical'

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
        #if self.monochromator.wavelength is None:
        #    self.warn(f"Wavelength is missing; using {WAVELENGTH} A")
        #    self.monochromator.wavelength = WAVELENGTH
        #if self.monochromator.wavelength_resolution is None:
        #    self.warn("Wavelength resolution is missing; using %.1f%% dL/L FWHM"
        #              % (100*WAVELENGTH_DISPERSION,))
        #    self.monochromator.wavelength_resolution = \
        #        FWHM2sigma(WAVELENGTH_DISPERSION*self.monochromator.wavelength)

        # Slits
        self.slit1.distance = data_as(entry, 'instrument/presample_slit1/distance', 'mm')
        self.slit2.distance = data_as(entry, 'instrument/presample_slit2/distance', 'mm')
        self.slit3.distance = data_as(entry, 'instrument/predetector_slit1/distance', 'mm')
        self.slit4.distance = data_as(entry, 'instrument/detector_mask/distance', 'mm')

        for k, slit in enumerate((self.slit1, self.slit2, self.slit3)):
            x = 'slitAperture%d/softPosition'%(k+1)
            x_target = 'slitAperture%d/desiredSoftPosition'%(k+1)
            slit.x = data_as(das, x, 'mm', rep=n)
            slit.x_target = data_as(das, x_target, 'mm', rep=n)
            #y = 'vertSlitAperture%d/softPosition'%(k+1)
            #y_target = 'vertSlitAperture%d/desiredSoftPosition'%(k+1)
            #slit.y = data_as(das, y, 'mm', rep=n)
            #slit.y_target = data_as(das, y_target, 'mm', rep=n)
        # Slit 4 on CANDOR is a fixed mask rather than continuous motors.
        self.slit4.x = data_as(entry, 'instrument/detector_mask/width', 'mm', rep=n)
        self.slit4.x_target = self.slit4.x
        #self.slit4.y = data_as(entry, 'instrument/detector_mask/height', 'mm', rep=n)
        #self.slit4.y_target = self.slit4.y

        # Detector
        wavelength = data_as(das, 'detectorTable/wavelengths', '')
        wavelength_spread = data_as(das, 'detectorTable/wavelengthSpreads', '')
        wavelength = wavelength.reshape(NUM_CHANNELS, -1).T
        wavelength_spread = wavelength_spread.reshape(NUM_CHANNELS, -1).T
        self.detector.wavelength = wavelength
        self.detector.wavelength_resolution = FWHM2sigma(wavelength * wavelength_spread)

        divergence = data_as(das, 'detectorTable/angularSpreads', '')
        efficiency = data_as(das, 'detectorTable/detectorEfficiencies', '')
        if np.isscalar(divergence):
            if np.isnan(divergence):
                divergence = 0.01  # default divergence if missing
            divergence = np.ones(wavelength.shape) * divergence
        if np.isscalar(efficiency):
            if np.isnan(efficiency):
                efficiency = 1.0  # default efficiency if missing
            efficiency = np.ones(wavelength.shape) * efficiency
        divergence = divergence.reshape(NUM_CHANNELS, -1).T[None, :, :]
        efficiency = efficiency.reshape(NUM_CHANNELS, -1).T[None, :, :]
        self.detector.efficiency = efficiency
        # TODO: not using angular divergence?

        # If not monochromatic beam then assume elastic scattering
        if self.monochromator.wavelength is None:
            self.monochromator.wavelength = self.detector.wavelength
            self.monochromator.wavelength_resolution = self.detector.wavelength_resolution

        # Counts
        self.detector.counts = np.asarray(data_as(das, 'areaDetector/counts', ''), 'd')
        self.detector.counts_variance = self.detector.counts.copy()
        self.detector.dims = self.detector.counts.shape[1:]

        # Angles
        self.sample.angle_x = data_as(das, 'sampleAngleMotor/softPosition', 'degree', rep=n)
        self.sample.angle_x_target = data_as(das, 'sampleAngleMotor/desiredSoftPosition', 'degree', rep=n)
        self.detector.angle_x = data_as(das, 'detectorTableMotor/softPosition', 'degree', rep=n)
        self.detector.angle_x_target = data_as(das, 'detectorTableMotor/desiredSoftPosition', 'degree', rep=n)

        self.detector._bank_angle = data_as(das, 'detectorTable/rowAngularOffsets', '')[0]
        #bank_angle = np.arange(30)*0.1
        ## Add an extra dimension to sample angle

    @property
    def Ti(self):
        return self.sample.angle_x[:, None, None]

    def Ti_target(self):
        self.sample.angle_x_target = self.sample.angle_x[:, None, None]

    def Td(self):
        angle, offset = self.detector.angle_x, self.detector._bank_angle
        return angle[:, None, None] + offset[None, :, None]

    def Td_target(self):
        angle, offset = self.detector.angle_x_target, self.detector._bank_angle
        return angle[:, None, None] + offset[None, :, None]

    def Li(self):
        return self.monochromator.wavelength[None, :, None]

    def Ld(self):
        return self.detector.wavelength[None, :, :]

    def plot(self, label=None):
        if label is None:
            label = self.name+self.polarization

        from matplotlib import pyplot as plt
        xerr = self.dx if self.angular_resolution is not None else None
        #x, dx, xunits, xlabel = self.x, xerr, self.xunits, self.xlabel
        x, xunits, xlabel = self.detector.wavelength, 'Ang', 'detector wavelength'
        y, yunits, ylabel = self.sample.angle_x, 'degree', 'sample angle'
        v = self.v
        plt.subplot(211)
        plt.pcolormesh(edges(x[0, 0, :]), edges(y[:, 0, 0]), v[:, 0, :])
        plt.xlabel("%s (%s)"%(xlabel, xunits))
        plt.ylabel("%s (%s)"%(ylabel, yunits))
        plt.colorbar()
        plt.text(0, 0, ["bank 0"], ha='right', va='bottom', zorder=5)
        plt.subplot(212)
        plt.pcolormesh(edges(x[0, 1, :]), edges(y[:, 0, 0]), v[:, 1, :])
        plt.xlabel("%s (%s)"%(xlabel, xunits))
        plt.ylabel("%s (%s)"%(ylabel, yunits))
        plt.colorbar()
        plt.text(0, 0, ["bank 1"], ha='left', va='top', zorder=5)

    def get_axes(self):
        ny, nx = self.v.shape
        x, xlabel = np.arange(1, nx+1), "pixel"
        if Intent.isslit(self.intent):
            y, ylabel = self.slit1.x, "S1"
        elif Intent.isspec(self.intent):
            y, ylabel = self.Qz_target, "Qz"
        else:
            y, ylabel = np.arange(1, ny+1), "point"
        return (x, xlabel), (y, ylabel)

    def get_plottable(self):
        name = getattr(self, "name", "default_name")
        entry = getattr(self, "entry", "default_entry")
        def limits(v, n):
            low, high = v.min(), v.max()
            delta = (high - low) / max(n-1, 1)
            # TODO: move range cleanup to plotter
            if delta == 0.:
                delta = v[0]/10.
            return low - delta/2, high+delta/2
        data = self.v
        ny, nx = data.shape
        (x, xlabel), (y, ylabel) = self.get_axes()
        #print("data shape", nx, ny)
        xmin, xmax = limits(x, nx)
        ymin, ymax = limits(y, ny)
        # TODO: self.detector.mask
        zmin, zmax = data.min(), data.max()
        # TODO: move range cleanup to plotter
        if zmin <= 0.:
            if (data > 0).any():
                zmin = data[data > 0].min()
            else:
                data[:] = zmin = 1e-10
            if zmin >= zmax:
                zmax = 10*zmin
        dims = {
            "xmin": xmin, "xmax": xmax, "xdim": nx,
            "ymin": ymin, "ymax": ymax, "ydim": ny,
            "zmin": zmin, "zmax": zmax,
        }
        z = data.T.ravel('C').tolist()
        plottable = {
            #'type': '2d_multi',
            #'dims': {'zmin': zmin, 'zmax': zmax},
            #'datasets': [{'dims': dims, 'data': z}],
            'type': '2d',
            'dims': dims,
            'z': [z],
            'entry': entry,
            'title': "%s:%s" % (name, entry),
            'options': {
                'fixedAspect': {
                    'fixAspect': False,
                    'aspectRatio': 1.0,
                },
            },
            'xlabel': xlabel,
            'ylabel': ylabel,
            'zlabel': 'Intensity (I)',
            'ztransform': 'log',
        }
        #print(plottable)
        return plottable

    # TODO: Define export format for partly reduced PSD data.
    #@exports_text("column")
    def to_column_text(self):
        export_string = ""
        name = getattr(self, "name", "default_name")
        entry = getattr(self, "entry", "default_entry")
        return {
            "name": name,
            "entry": entry,
            "export_string": export_string,
            "file_suffix": ".dat",
            }

def edges(c):
    midpoints = (c[:-1]+c[1:])/2
    left = 2*c[0] - midpoints[0]
    right = 2*c[-1] - midpoints[-1]
    return np.hstack((left, midpoints, right))

if __name__ == "__main__":
    from .nexusref import demo
    demo(loader=load_entries)
