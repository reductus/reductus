#!/usr/bin/env python
import json

import numpy as np

from dataflow.lib.exporters import exports_text

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
S1_DISTANCE = -4335.86
S2_DISTANCE = -356.0
S3_DISTANCE = 356.0
DETECTOR_DISTANCE = 3496.0

_EFFICIENCY = None
def detector_efficiency():
    from pathlib import Path
    global _EFFICIENCY
    if _EFFICIENCY is None:
        path = Path(__file__).parent / 'DetectorWavelengths.csv'
        eff = np.loadtxt(path, delimiter=',')[:, 3]
        eff = eff / np.mean(eff)
        _EFFICIENCY = np.hstack((eff, eff))
        _EFFICIENCY = _EFFICIENCY.reshape(1, 2, NUM_CHANNELS)
    return _EFFICIENCY

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
        # Fill in missing distance data, if they aren't in the config file
        for slit, default in (
                (self.slit1, S1_DISTANCE),
                (self.slit2, S2_DISTANCE),
                (self.slit3, S3_DISTANCE),
                (self.slit4, DETECTOR_DISTANCE),
                ):
            if slit.distance is None:
                slit.distance = default

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
        # CRUFT: nexus should store efficiency
        if (efficiency == 1.0).all():
            efficiency = detector_efficiency()
        self.detector.efficiency = efficiency
        # TODO: sample broadening?
        self.angular_resolution = divergence

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

    @property
    def Ti_target(self):
        return self.sample.angle_x_target[:, None, None]

    @property
    def Td(self):
        angle, offset = self.detector.angle_x, self.detector._bank_angle
        return angle[:, None, None] + offset[None, :, None]

    @property
    def dT(self):
        self.detector._divergence

    @property
    def Td_target(self):
        angle, offset = self.detector.angle_x_target, self.detector._bank_angle
        return angle[:, None, None] + offset[None, :, None]

    @property
    def Li(self):
        return self.monochromator.wavelength[:, None, None]

    @property
    def Ld(self):
        return self.detector.wavelength[None, :, :]

    def plot(self, label=None):
        if label is None:
            label = self.name+self.polarization

        from matplotlib import pyplot as plt
        xerr = self.dx if self.angular_resolution is not None else None
        #x, dx, xlabel = self.x, xerr, f"{self.xlabel} ({self.xunits})"
        v = np.log10(self.v + (self.v == 0))
        channel = np.arange(1, NUM_CHANNELS+1)

        if True: # Qz - channel
            x, xlabel = self.Qz, 'Qz (1/Ang)'
            y, ylabel = np.vstack((channel, channel))[None, :, :], "channel"

            plt.subplot(211)
            plt.pcolormesh(x[:, 0, :].T, y[:, 0, :].T, v[:, 0, :].T)
            plt.xlabel(xlabel)
            plt.ylabel(f"{ylabel} - bank 0")
            plt.colorbar()
            plt.subplot(212)
            plt.pcolormesh(x[:, 1, :].T, y[:, 1, :].T, v[:, 1, :].T)
            plt.xlabel(xlabel)
            plt.ylabel(f"{ylabel} - bank 1")
            plt.colorbar()
            plt.suptitle(f'detector counts for {self.name}')

        if False: # lambda-theta
            x, xlabel = self.detector.wavelength, 'detector wavelength (Ang)'
            y, ylabel = self.sample.angle_x, 'sample angle (degree)'
            plt.subplot(211)
            plt.pcolormesh(edges(x[0]), edges(y), v[:, 0, :])
            plt.xlabel(xlabel)
            plt.ylabel(f"{ylabel} - bank 0")
            plt.colorbar()
            plt.subplot(212)
            plt.pcolormesh(edges(x[1]), edges(y), v[:, 1, :])
            plt.xlabel(xlabel)
            plt.ylabel(f"{ylabel} - bank 1")
            plt.colorbar()
            plt.suptitle(f'detector counts for {self.name}')

        if False: # detector efficiency
            plt.figure()
            eff = self.detector.efficiency[0]
            plt.plot(channel, eff[0], label='bank 0')
            plt.plot(channel, eff[1], label='bank 1')
            plt.xlabel('channel number')
            plt.ylabel('wavelength efficiency')
            plt.suptitle(f'detectorTable.detectorEfficiencies for {self.name}')
            plt.legend()

        if False: # detector wavelength
            plt.figure()
            y, ylabel = self.detector.wavelength, 'detector wavelength (Ang)'
            dy = self.detector.wavelength_resolution
            plt.errorbar(channel, y[0], yerr=dy[0], label='bank 0')
            plt.errorbar(channel, y[1], yerr=dy[1], label='bank 1')
            plt.xlabel('channel number')
            plt.ylabel(ylabel)
            plt.suptitle(f'detectorTable.wavelength for {self.name}')
            plt.legend()

    def get_axes(self):
        x, xlabel = self.detector.wavelength, "Wavelength (Ang)"
        y, ylabel = self.sample.angle_x, "Detector Angle (degrees)"
        return (x, xlabel), (y, ylabel)

    def get_plottable(self):
        name = getattr(self, "name", "default_name")
        entry = getattr(self, "entry", "default_entry")
        def limits(vec, n):
            low, high = vec.min(), vec.max()
            delta = (high - low) / max(n-1, 1)
            # TODO: move range cleanup to plotter
            if delta == 0.:
                delta = vec[0]/10.
            return low - delta/2, high+delta/2
        data = np.moveaxis(self.v, 1, 0)
        _, ny, nx = data.shape  # nbanks, nangles, nwavelengths
        (x, xlabel), (y, ylabel) = self.get_axes()
        #print("data shape", nx, ny, data.shape)
        # Paste frames back-to-back
        data = np.hstack((data[0], data[1]))[None, :, :]
        x, nx = np.hstack((x, x + (x.max()-x.min()))), 2*nx
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
        z = [frame.ravel('F').tolist() for frame in data]
        #print("data", data.shape, dims, len(z))
        plottable = {
            #'type': '2d_multi',
            #'dims': {'zmin': zmin, 'zmax': zmax},
            #'datasets': [{'dims': dims, 'data': z}],
            'type': '2d',
            'dims': dims,
            'z': z,
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
    @exports_text("json")
    def to_column_text(self):
        export_string = json.dumps(self._toDict())
        name = getattr(self, "name", "default_name")
        entry = getattr(self, "entry", "default_entry")
        return {
            "name": name,
            "entry": entry,
            "file_suffix": ".json",
            "value": export_string,
            }

def edges(c):
    midpoints = (c[:-1]+c[1:])/2
    left = 2*c[0] - midpoints[0]
    right = 2*c[-1] - midpoints[-1]
    return np.hstack((left, midpoints, right))

if __name__ == "__main__":
    from .nexusref import demo
    demo(loader=load_entries)
