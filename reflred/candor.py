#!/usr/bin/env python
import json

import numpy as np

from dataflow.lib.exporters import exports_json

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

# CRUFT: these will be in the nexus/config.js eventually
S1_DISTANCE = -4335.86
S2_DISTANCE = -356.0
S3_DISTANCE = 356.0
DETECTOR_DISTANCE = 3496.0
MONO_WAVELENGTH = 4.75
MONO_WAVELENGTH_DISPERSION = 0.01

# CRUFT: these will be in the
_EFFICIENCY = None
def detector_efficiency():
    from pathlib import Path
    global _EFFICIENCY
    if _EFFICIENCY is None:
        path = Path(__file__).parent / 'DetectorWavelengths.csv'
        eff = np.loadtxt(path, delimiter=',')[:, 3]
        eff = eff / np.mean(eff)
        _EFFICIENCY = np.hstack((eff, eff))
        _EFFICIENCY = _EFFICIENCY.reshape(2, NUM_CHANNELS)
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

        # Counts
        # Load counts early so we can tell whether channels are axis 1 or 2
        counts = np.asarray(data_as(das, 'areaDetector/counts', ''), 'd')
        channels_at_end = (counts.shape[2] == NUM_CHANNELS)
        if not channels_at_end:
            counts = np.swapaxes(counts, 1, 2)
        self.detector.counts = counts
        self.detector.counts_variance = counts.copy()
        self.detector.dims = counts.shape[1:]


        # Monochromator
        ismono = (str_data(das, 'monoTrans/key', 'OUT') == 'IN')
        if ismono:
            self.warn("monochromatic beams not yet supported for Candor reduction")
            self.monochromator.wavelength = data_as(entry, 'instrument/monochromator/wavelength', 'Ang', rep=n)
            # TODO: make sure wavelength_error is 1-sigma, not FWHM %
            self.monochromator.wavelength_resolution = data_as(entry, 'instrument/monochromator/wavelength_error', '', rep=n)
            # CRUFT: nexus config doesn't link in monochromator
            if self.monochromator.wavelength is None:
                self.monochromator.wavelength = data_as(das, 'mono/wavelength', 'Ang', rep=n)
            if self.monochromator.wavelength is None:
                self.warn(f"Wavelength is missing; using {MONO_WAVELENGTH} A")
                self.monochromator.wavelength = MONO_WAVELENGTH
            # TODO: generate wavelength_error directly with the nexus writer
            if self.monochromator.wavelength_resolution is None:
                dispersion = data_as(das, 'mono/wavelengthSpread', '', rep=n)
                if dispersion is not None:
                    self.monochromator.wavelength_resolution = \
                        FWHM2sigma(dispersion*self.monochromator.wavelength)
            if self.monochromator.wavelength_resolution is None:
                self.warn("Wavelength resolution is missing; using %.1f%% dL/L FWHM"
                        % (100*MONO_WAVELENGTH_DISPERSION,))
                self.monochromator.wavelength_resolution = \
                    FWHM2sigma(MONO_WAVELENGTH_DISPERSION*self.monochromator.wavelength)
            self.monochromator.wavelength = self.monochromator.wavelength[:, None, None]
            self.monochromator.wavelength_resolution = self.monochromator.wavelength_resolution[:, None, None]
        else:
            self.monochromator.wavelength = None
            self.monochromator.wavelength_resolution = None

        # Slit distances
        self.slit1.distance = data_as(entry, 'instrument/presample_slit1/distance', 'mm')
        self.slit2.distance = data_as(entry, 'instrument/presample_slit2/distance', 'mm')
        self.slit3.distance = data_as(entry, 'instrument/predetector_slit1/distance', 'mm')
        self.slit4.distance = data_as(entry, 'instrument/predetector_slit2/distance', 'mm')
        # CRUFT: old candor files don't populate instrument slits
        for slit, default in (
                (self.slit1, S1_DISTANCE),
                (self.slit2, S2_DISTANCE),
                (self.slit3, S3_DISTANCE),
                (self.slit4, DETECTOR_DISTANCE),
                ):
            if slit.distance is None:
                slit.distance = default

        # Slit openings
        # Note: Candor does not have slit4, but we translate the detector
        # mask value into a slit4 opening positioned right at the detector.
        # TODO: get values from instrument group instead of DAS_logs.
        for k, slit in enumerate((self.slit1, self.slit2, self.slit3, self.slit4)):
            x = 'slitAperture%d/softPosition'%(k+1)
            x_target = 'slitAperture%d/desiredSoftPosition'%(k+1)
            slit.x = data_as(das, x, 'mm', rep=n)
            slit.x_target = data_as(das, x_target, 'mm', rep=n)
            #y = 'vertSlitAperture%d/softPosition'%(k+1)
            #y_target = 'vertSlitAperture%d/desiredSoftPosition'%(k+1)
            #slit.y = data_as(das, y, 'mm', rep=n)
            #slit.y_target = data_as(das, y_target, 'mm', rep=n)
        # CRUFT: old files don't have the detector mask mapped
        if self.slit4.x is None:
            mask_str = str_data(das, 'detectorMaskMap/key', '10')
            if not mask_str:
                mask_str = '10'
            try:
                mask = float(mask_str)
            except ValueError:
                raise ValueError(f"mask value {mask_str} cannot be converted to float")
            self.slit4.x_target = self.slit4.x = np.full(n, mask)

        # Detector
        wavelength = data_as(das, 'detectorTable/wavelengths', '')
        wavelength_spread = data_as(das, 'detectorTable/wavelengthSpreads', '')
        if channels_at_end:
            wavelength = wavelength.reshape(NUM_CHANNELS, -1).T
            wavelength_spread = wavelength_spread.reshape(NUM_CHANNELS, -1).T
        else:
            wavelength = wavelength.reshape(-1, NUM_CHANNELS)
            wavelength_spread = wavelength_spread.reshape(-1, NUM_CHANNELS)
        self.detector.wavelength = wavelength[None, :, :]
        self.detector.wavelength_resolution = FWHM2sigma(wavelength * wavelength_spread)[None, :, :]

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
        if channels_at_end:
            divergence = divergence.reshape(NUM_CHANNELS, -1).T
            efficiency = efficiency.reshape(NUM_CHANNELS, -1).T
        else:
            divergence = divergence.reshape(-1, NUM_CHANNELS)
            efficiency = efficiency.reshape(-1, NUM_CHANNELS)
        # CRUFT: old files have efficiency set to 1
        if (efficiency == 1.0).all():
            efficiency = detector_efficiency()
        self.detector.efficiency = efficiency[None, :, :]
        # TODO: sample broadening?
        self.angular_resolution = divergence[None, :, :]

        # Angles
        self.sample.angle_x = data_as(das, 'sampleAngleMotor/softPosition', 'degree', rep=n)
        self.sample.angle_x_target = data_as(das, 'sampleAngleMotor/desiredSoftPosition', 'degree', rep=n)
        self.detector.angle_x = data_as(das, 'detectorTableMotor/softPosition', 'degree', rep=n)
        self.detector.angle_x_target = data_as(das, 'detectorTableMotor/desiredSoftPosition', 'degree', rep=n)

        self.detector.angle_x_offset = data_as(das, 'detectorTable/rowAngularOffsets', '')[0]
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
        angle, offset = self.detector.angle_x, self.detector.angle_x_offset
        return angle[:, None, None] + offset[None, :, None]

    @property
    def Td_target(self):
        angle, offset = self.detector.angle_x_target, self.detector.angle_x_offset
        return angle[:, None, None] + offset[None, :, None]

    @property
    def Li(self):
        # Assume incident = reflected wavelength if no monochromator
        return (self.Ld if self.monochromator.wavelength is None
                else self.monochromator.wavelength)

    @property
    def Ld(self):
        return self.detector.wavelength  # Candor always has detector wavelength
        #return (self.Li if self.detector.wavelength is None
        #        else self.detector.wavelength)

    def plot(self, label=None):
        if label is None:
            label = self.name+self.polarization

        from matplotlib import pyplot as plt
        v = np.log10(self.v + (self.v == 0))
        channel = np.arange(1, NUM_CHANNELS+1)

        if True: # Qz/S1 - channel
            if Intent.isslit(self.intent):
                x, xlabel = self.slit1.x, "Slit 1 opening (mm)"
                x = np.vstack((x, x)).T[:,:,None]
            else:
                x, xlabel = self.Qz, "Qz (1/Ang)"
            y, ylabel = np.vstack((channel, channel))[None, :, :], "channel"
            #print("Qz-channel", x.shape, y.shape, v.shape)

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
        ny, _, nx = self.v.shape
        x, xlabel = self.detector.wavelength, "Wavelength (Ang)"
        if Intent.isslit(self.intent):
            y, ylabel = self.slit1.x, "S1"
        elif Intent.isspec(self.intent):
            y, ylabel = self.sample.angle_x, "Detector Angle (degrees)"
        else:
            y, ylabel = np.arange(1, ny+1), "point"
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
    @exports_json("json")
    def to_json_text(self):
        name = getattr(self, "name", "default_name")
        entry = getattr(self, "entry", "default_entry")
        return {
            "name": name,
            "entry": entry,
            "file_suffix": ".json",
            "value": self._toDict(),
            }

    # Kill column writer
    def to_column_text(self):
        pass

def edges(c):
    midpoints = (c[:-1]+c[1:])/2
    left = 2*c[0] - midpoints[0]
    right = 2*c[-1] - midpoints[-1]
    return np.hstack((left, midpoints, right))

if __name__ == "__main__":
    from .nexusref import demo
    demo(loader=load_entries)
