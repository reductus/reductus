#!/usr/bin/env python
from warnings import warn
from copy import copy

import numpy as np

from reductus.dataflow.lib.exporters import exports_json

from .refldata import ReflData, Intent, Group, Detector, set_fields
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

# CRUFT: these will be in the datafile eventually
_EFFICIENCY = None
def detector_efficiency():
    from pathlib import Path
    global _EFFICIENCY
    if _EFFICIENCY is None:
        path = Path(__file__).parent / 'DetectorWavelengths.csv'
        eff = np.loadtxt(path, delimiter=',')[:, 3]
        eff = eff / np.mean(eff)
        _EFFICIENCY = np.vstack((eff, eff)).T
    return _EFFICIENCY

@set_fields
class Attenuator(Group):
    """
    Define built-in attenuators
    This is used by the attenuation correction.
    
    The wavelength-dependent transmission is defined by a fitted
    polynomial for each attenuator, along with a 
    covariance matrix for uncertainty propagation.

    transmission (n x m)
        transmission vs. wavelength
        length n is the number of defined attenuators, m is number of detectors
    transmission_err (n x m)
        1-sigma width of uncertainty distribution for transmission matrix
    target_value (npts)
        attenuator setting, for each data point (in [0, n])
    """
    transmission = None # n x m matrices
    transmission_err = None # m x m matrices
    target_value = None # attenuators in the beam; setting is per point, matching length of counts

class Candor(ReflData):
    """
    Candor data entry.

    See :class:`refldata.ReflData` for details.
    """
    format = "NeXus"
    probe = "neutrons"
    _groups = ReflData._groups + (("attenuator", Attenuator),)
    attenuator = None

    def __init__(self, entry, entryname, filename):
        super().__init__()
        self.attenuator = Attenuator()
        nexus_common(self, entry, entryname, filename)
        self.geometry = 'vertical'
        self.align_intensity = "slit1.x"

    def load(self, entry):
        #print(entry['instrument'].values())
        das = entry['DAS_logs']
        n = self.points
        raw_intent = str_data(das, 'trajectoryData/_scanType')
        if raw_intent in TRAJECTORY_INTENTS:
            self.intent = TRAJECTORY_INTENTS[raw_intent]

        # Figure out beam mode:
        #    Q.beamMode = WHITE_BEAM|SINGLE_BEAM
        #    convergingGuideMap.key = IN|OUT
        # For white beam with non-converging guide use the active bank to
        # determine which Q values to look at. For now look at both banks.
        #beam_mode = str_data(das, 'Q/beamMode', '')
        #if beam_mode != 'WHITE_BEAM':
        #    raise ValueError(f"candor reduction requires Q/beamMode=WHITE_BEAM in '{self.path}'")
        #active_bank = data_as(das, 'Q/angleIndex', 1) - 1
        #active_channel = data_as(das, 'Q/wavelenghtIndex', 1) - 1
        #is_converging = (str_data(das, 'convergingGuidesMap/key', 'OUT') == 'IN')

        # Polarizers
        self.polarization = (
            get_pol(das, 'frontPolarization')
            + get_pol(das, 'backPolarization')
        )

        # Counts
        # Load counts early so we can tell whether channels are axis 1 or 2
        counts = data_as(das, 'multiDetector/counts', '', dtype='d')
        if counts is None: # CRUFT: NICE Ticket #00113618 - Renamed detector from area to multi
            counts = data_as(das, 'areaDetector/counts', '', dtype='d')
        if counts is None or counts.size == 0:
            raise ValueError("Candor file '{self.path}' has no area detector data.".format(self=self))

        channels_at_end = (counts.shape[2] == NUM_CHANNELS)
        if channels_at_end:
            counts = np.swapaxes(counts, 1, 2)
        self.detector.counts = counts
        self.detector.counts_variance = counts.copy()
        self.detector.dims = counts.shape[1:]

        # Monochromator
        # Note: could test Q/beamMode == 'SINGLE_BEAM" for is_mono
        is_mono = (str_data(das, 'monoTrans/key', 'OUT') == 'IN')
        if is_mono:
            self.warn("monochromatic beams not yet supported for Candor reduction")
            self.monochromator.wavelength = data_as(entry, 'instrument/monochromator/wavelength', 'Ang', rep=n)
            # TODO: make sure wavelength_error is 1-sigma, not FWHM %
            self.monochromator.wavelength_resolution = data_as(entry, 'instrument/monochromator/wavelength_error', '', rep=n)
            # CRUFT: nexus config doesn't link in monochromator
            if self.monochromator.wavelength is None:
                self.monochromator.wavelength = data_as(das, 'mono/wavelength', 'Ang', rep=n)
            if self.monochromator.wavelength is None:
                self.warn("Wavelength is missing; using {MONO_WAVELENGTH} A".format(MONO_WAVELENGTH=MONO_WAVELENGTH))
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
        # There is one vertical slit, and it is defined by slit2AVertical
        # This is a virtual device which gives the center and opening, but
        # not the target center and opening. Instead, use the Top/Bottom motors
        # to get the desired and actual, and ignore slit2AVertical. This assumes
        # the slits are centered.
        self.slit2.y = (
            data_as(das, 'slit2AVerticalTop/softPosition', 'mm', rep=n)
            - data_as(das, 'slit2AVerticalBottom/softPosition', 'mm', rep=n))
        self.slit2.y_target = (
            data_as(das, 'slit2AVerticalTop/desiredSoftPosition', 'mm', rep=n)
            - data_as(das, 'slit2AVerticalBottom/desiredSoftPosition', 'mm', rep=n))
        # CRUFT: old files don't have the detector mask mapped
        # TODO: don't throw away datasets where the key is not defined:
        #       instead figure out an effective aperture size from motors or
        #       allow it to be overridden
        if self.slit4.x is None:
            mask_str = str_data(das, 'detectorMaskMap/key', '10')
            if not mask_str:
                mask_str = '10'
            try:
                mask = float(mask_str)
            except ValueError:
                raise ValueError("mask value {mask_str} cannot be converted to float".format(mask_str=mask_str))
            self.slit4.x_target = self.slit4.x = np.full(n, mask)

        # Detector
        wavelength = data_as(das, 'detectorTable/wavelengths', '')
        wavelength_spread = data_as(das, 'detectorTable/wavelengthSpreads', '')
        divergence = data_as(das, 'detectorTable/angularSpreads', '')
        efficiency = data_as(das, 'detectorTable/detectorEfficiencies', '')
        if divergence is None:
            divergence = np.repeat(0.01, wavelength.shape)
        if efficiency is None:
            efficiency = np.repeat(1.0, wavelength.shape)

        # PAK 2020-11-12: detectorTable now uses [54,2] rather than [108], so
        # reshape is no longer necessary. Check for [2,54] and transpose to
        # protect against future change. For older data, use reshape with
        # wavelengths in "channels_at_end" order (even though the detector
        # counts are in "banks_at_end" order).
        if all(dim != NUM_CHANNELS for dim in wavelength.shape):
            wavelength = wavelength.reshape(NUM_CHANNELS, -1)
            wavelength_spread = wavelength_spread.reshape(NUM_CHANNELS, -1)
            divergence = divergence.reshape(NUM_CHANNELS, -1)
            efficiency = efficiency.reshape(NUM_CHANNELS, -1)
        elif wavelength.shape[0] != NUM_CHANNELS:
            wavelength = wavelength.T
            wavelength_spread = wavelength_spread.T
            divergence = divergence.T
            efficiency = efficiency.T

        wavelength_resolution = wavelength_spread # FWHM2sigma(wavelength * wavelength_spread)
        if (efficiency == 1.0).all():
            efficiency = detector_efficiency()

        self.detector.wavelength = wavelength[None, :, :]
        self.detector.wavelength_resolution = wavelength_resolution[None, :, :]
        self.detector.efficiency = efficiency[None, :, :]
        #self.angular_resolution = divergence[None, :, :]
        # TODO: sample broadening?

        # Angles
        self.sample.angle_x = data_as(das, 'sampleAngle/softPosition', 'degree', rep=n)
        self.sample.angle_x_target = data_as(das, 'sampleAngle/desiredSoftPosition', 'degree', rep=n)
        # CRUFT: renamed sampleAngleMotor to sampleAngle
        if self.sample.angle_x is None:
            self.sample.angle_x = data_as(das, 'sampleAngleMotor/softPosition', 'degree', rep=n)
        if self.sample.angle_x_target is None:
            self.sample.angle_x_target = data_as(das, 'sampleAngleMotor/desiredSoftPosition', 'degree', rep=n)
        self.detector.angle_x = data_as(das, 'detectorArmAngle/softPosition', 'degree', rep=n)
        self.detector.angle_x_target = data_as(das, 'detectorArmAngle/desiredSoftPosition', 'degree', rep=n)
        # CRUFT: renamed detectorTableMotor to detectorArmAngle
        if self.detector.angle_x is None:
            self.detector.angle_x = data_as(das, 'detectorTableMotor/softPosition', 'degree', rep=n)
        if self.detector.angle_x_target is None:
            self.detector.angle_x_target = data_as(das, 'detectorTableMotor/desiredSoftPosition', 'degree', rep=n)
        # PAK 2020-11-11: detectorTable/rowAngularOffsets changed orientation; flatten so we don't care
        self.detector.angle_x_offset = data_as(das, 'detectorTable/rowAngularOffsets', 'degree').flatten()

        # Attenuators
        self.attenuator.transmission = data_as(entry, 'instrument/attenuator/transmission', '', dtype="float")
        self.attenuator.transmission_err = data_as(entry, 'instrument/attenuator/transmission_err', '', dtype="float")
        self.attenuator.target_value = data_as(das, 'counter/actualAttenuatorsDropped', '', rep=n)

        #print("shapes", self.detector.counts.shape, self.detector.wavelength.shape, self.detector.efficiency.shape)
        #print("shapes", self.sample.angle_x.shape, self.detector.angle_x.shape, self.detector.angle_x_offset.shape)


    @property
    def Ti(self):
        return self.sample.angle_x[:, None, None]

    @property
    def Ti_target(self):
        return self.sample.angle_x_target[:, None, None]

    @property
    def Td(self):
        angle, offset = self.detector.angle_x, self.detector.angle_x_offset
        return angle[:, None, None] + offset[None, None, :]

    @property
    def Td_target(self):
        angle, offset = self.detector.angle_x_target, self.detector.angle_x_offset
        return angle[:, None, None] + offset[None, None, :]

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
        #v = np.log10(self.v + (self.v == 0))
        # set noise floor to ignore 5% of the data above zero
        v = self.v.copy()
        vmin = np.sort(v[v > 0])[int((v > 0).size * 0.01)]
        v[v<vmin] = vmin
        v = np.log10(v)

        channel = np.arange(1, NUM_CHANNELS+1)

        if True: # Qz - channel OR S1 - channel
            if Intent.isslit(self.intent):
                x, xlabel = self.slit1.x, "Slit 1 opening (mm)"
                x = x[:, None, None]
                x = np.concatenate((x, x), axis=2)
            else:
                x, xlabel = self.Qz, "Qz (1/Ang)"
            y, ylabel = np.vstack((channel, channel)).T[None, :, :], "channel"
            #print("Qz-channel", x.shape, y.shape, v.shape)

            #plt.figure()
            plt.subplot(211)
            plt.pcolormesh(x[:, :, 0].T, y[:, :, 0].T, v[:, :, 0].T)
            plt.xlabel(xlabel)
            plt.ylabel("{ylabel} - bank 0".format(ylabel=ylabel))
            plt.colorbar()
            plt.subplot(212)
            plt.pcolormesh(x[:, :, 1].T, y[:, :, 1].T, v[:, :, 1].T)
            plt.xlabel(xlabel)
            plt.ylabel("{ylabel} - bank 1".format(ylabel=ylabel))
            plt.colorbar()
            plt.suptitle('detector counts for {self.name}'.format(self=self))

        if False: # lambda-theta
            x, xlabel = self.detector.wavelength, 'detector wavelength (Ang)'
            y, ylabel = self.sample.angle_x, 'sample angle (degree)'
            #print("lambda-theta", x.shape, y.shape, v.shape)

            plt.figure()
            plt.subplot(211)
            plt.pcolormesh(edges(x[0, :, 0]), edges(y), v[:, :, 0])
            plt.xlabel(xlabel)
            plt.ylabel("{ylabel} - bank 0".format(ylabel=ylabel))
            plt.colorbar()
            plt.subplot(212)
            plt.pcolormesh(edges(x[0, :, 1]), edges(y), v[:, :, 1])
            plt.xlabel(xlabel)
            plt.ylabel("{ylabel} - bank 1".format(ylabel=ylabel))
            plt.colorbar()
            plt.suptitle('detector counts for {self.name}'.format(self=self))

        if False: # detector efficiency
            eff = self.detector.efficiency[0]
            #print("detector efficiency", eff.shape)

            plt.figure()
            plt.plot(channel, eff[:, 0], label='bank 0')
            plt.plot(channel, eff[:, 1], label='bank 1')
            plt.xlabel('channel number')
            plt.ylabel('wavelength efficiency')
            plt.suptitle('detectorTable.detectorEfficiencies for {self.name}'.format(self=self))
            plt.legend()

        if False: # detector wavelength
            y, ylabel = self.detector.wavelength, 'detector wavelength (Ang)'
            dy = self.detector.wavelength_resolution
            #print("detector wavelength", y.shape)

            plt.figure()
            plt.errorbar(channel, y[0, :, 0], yerr=dy[0, :, 0], label='bank 0')
            plt.errorbar(channel, y[0, :, 1], yerr=dy[0, :, 1], label='bank 1')
            plt.xlabel('channel number')
            plt.ylabel(ylabel)
            plt.suptitle('detectorTable.wavelength for {self.name}'.format(self=self))
            plt.legend()

    def get_axes(self):
        x, xlabel = self.detector.wavelength, "Wavelength (Ang)"
        #print("intent", self.intent)
        #if Intent.isslit(self.intent):
        #    y, ylabel = self.slit1.x, "S1 (mm)"
        #elif Intent.isspec(self.intent):
        #    y, ylabel = self.sample.angle_x, "Detector Angle (degrees)"
        if self.detector.angle_x.max() - self.detector.angle_x.min() > 0.01:
            y, ylabel = self.detector.angle_x, "Detector Angle (degrees)"
        elif self.sample.angle_x.max() - self.sample.angle_x.min() > 0.01:
            y, ylabel = self.sample.angle_x, "Sample Angle (degrees)"
        elif self.slit1.x.max() - self.slit1.x.min() > 0.01:
            y, ylabel = self.slit1.x, "S1 (mm)"
        else:
            y, ylabel = np.arange(1, len(self.v)+1), "point"
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
        data = self.v
        ny, nx, nbanks = data.shape  # nangles, nwavelengths, nbanks
        (x, xlabel), (y, ylabel) = self.get_axes()
        x, nx = np.array([x.min(), x.min() + nbanks*(x.max() - x.min())]), nbanks*nx
        xmax, xmin = limits(x, nx) # reversed because wavelengths are reversed
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
        # One z per detector bank
        #z = [data[..., k].ravel('F').tolist() for k in range(data.shape[-1])]
        # One z with banks back-to-back
        z = [data.ravel('F').tolist()]
        #print("data", data.shape, dims, len(z))
        plottable = {
            'type': '2d_multi',
            'dims': {'zmin': zmin, 'zmax': zmax},
            'datasets': [{'dims': dims, 'data': z[0]}],
            'entry': entry,
            'title': "%s:%s" % (name, entry),
            'options': {},
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

class QData(ReflData):
    def __init__(self, data, q, dq, v, dv, ti=None, dt=None, ld=None, dl=None):
        super().__init__()
        self.probe = data.probe
        self.path = data.path
        self.uri = data.uri
        self.name = data.name
        self.entry = data.entry
        self.description = data.description
        self.polarization = data.polarization
        self.normbase = data.normbase
        self.v = v
        self.dv = dv
        self.intent = Intent.spec
        self.points = len(q)
        self.scan_value = []
        self.scan_units = []
        self.scan_label = []
        # Put angles and resolution in the appropriate places in the refldata
        # data structure.
        self.sample = copy(data.sample)
        self.sample.angle_x = ti
        self.sample.angle_x_target = ti
        self.angular_resolution = dt
        self.detector = Detector()
        self.detector.wavelength = ld
        self.detector.wavelength_resolution = dl
        self.detector.angle_x = 2*ti
        self.detector.angle_x_target = 2*ti
        # Since dq is not computed directly from dt and dl, we need to store
        # it specially. Need to override apply_mask to fix up dq.
        self._dq = dq

    @property
    def dQ(self):
        return self._dq

    def apply_mask(self, mask_indices):
        self._dq = np.delete(self._dq, mask_indices)
        ReflData.apply_mask(self, mask_indices)

def nobin(data):
    """
    Dump the raw data points into a single Q vector.
    """
    # Make all data have the same shape
    columns = (
        data.Qz, data.dQ, data.v, data.dv,
        data.Ti, data.angular_resolution, data.Ld, data.dL)
    columns = [np.broadcast_to(p, data.v.shape) for p in columns]

    # Process the detector banks into different data sets
    datasets = []
    for bank in range(data.v.shape[2]):
        columns_bank = [p[..., bank].flatten() for p in columns]
        index = np.argsort(columns_bank[0])
        columns_bank = [p[index] for p in columns_bank]
        Qx, dQ, v, dv, Ti, dT, L, dL = columns_bank
        datasets.append(QData(data, Qx, dQ, v, dv, Ti, dT, L, dL))

    # Only look at bank 0 for now
    return datasets[0]

def rebin(data, q, average="poisson"):
    if average not in ("poisson", "gauss"):
        raise ValueError("expected average to be 'poisson' or 'gauss'")
    if average == "poisson" and data.normbase not in ("monitor", "time", "none"):
        raise ValueError("expected norm to be time, monitor or none for poisson average")
    q_edges = edges(q, extended=True)
    datasets = []
    for bank in range(data.v.shape[2]):
        qz, dq, v, dv, Ti, dT, L, dL = _rebin_bank(data, bank, q_edges, average)
        #output = ReflData()
        #output.v, output.dv = v, dv
        #output.x, output.dx = q, dq
        datasets.append(QData(data, qz, dq, v, dv, Ti, dT, L, dL))

    # Only look at bank 0 for now
    return datasets[0]

def _rebin_bank(data, bank, q_edges, average):
    """
    Merge q points across channels and angles, returning q, dq, v, dv.

    Intensities (v, dv) are combined using poisson averaging.

    Q values (Q, dQ) for the combined measurements are weighted by intensity.
    This means that identical measurement conditions may give different
    (Q, dQ) depending on the specific values measured.

    The following are computed from the combined points::

        [q] = <q> = <4π/λ sin(θ)>
        [λ] = 1/<1/λ>
        [θ] = arcsin([q] [λ] / 4π)
        [Δq]² = <q √ {(Δλ/λ)² + (Δθ/tan θ)²}> + <q²> - <q>²
        [Δλ]² = <Δλ²> + <λ²> - <λ>²
        [Δθ]² = <Δθ²>
        [q'] = 4π/[λ] sin([θ] + δ)                     for θ-offset δ
        [Δq']² = [Δq]² + ([q]/tan[θ])² (2ω [Δθ] + ω²)  for sample broadening ω

    The result for [q'] and [Δq'] are with 1% over a wide range of angles
    and slits. Only small θ-offset values were checked since large errors
    in incident angle are readily visible in the data. The reflectivity curves
    will be clearly misaligned especially near the critical edge for θ-offset
    above about 0.1°. Large values of sample broadening are supported, with
    up to 2° tested. Negative sample broadening will lead to anomalies at low
    angles.

    The <q²> - <q>² term in [Δq] comes from the formula for variance in a
    mixture distribution, which averages the variances of the individual
    distributions and adds a spread term in case the means are not overlapping.
    See <https://en.wikipedia.org/wiki/Mixture_distribution#Moments>_.

    The sample broadening formula [Δq'] comes from substituting Δθ+ω for Δθ
    in [Δq] and expanding the square. By using [Δq]² to compute [Δq']², the
    spread term is automatically incorporated. This change may require updates
    to the fitting software, which compute [Δq'] from (θ,λ,Δθ,Δλ) directly.

    Since θ and λ are completely correlated based on the q value each bin
    has thin resolution function following the constant q curve on a θ-λ plot.
    The resulting Δq is smaller than would be expected from the full Δθ and Δλ
    within the bin.

    Since the distribution is not a simple gaussian, we are free to choose
    [θ], [λ], [Δθ] and [Δλ] in a way that is convenient for fitting.  Choosing
    wavelength based on the average of the inverse, and angle so that it
    matches the corresponding [q] works well for computing θ-offset.
    Using this [θ] and averaging the variance for [Δθ] works well for
    estimating the effects of sample broadening.

    The [Δλ] term is set from the second central moment from the mixture
    distribution. This gives some idea of the range of wavelengths included
    in each [q], but it is not not directly useful. To properly fit data in
    which reflectivity is wavelength dependent the correct wavelength
    distribution is needed, not just the first and second moment. Because
    points with different intensity are combined, even knowing that incident
    wavelength follows a truncated Maxwell-Boltzmann distribution with a
    given temperature is not enough to reconstruct the measured distribution.
    In these situations measure fewer angles for longer without binning the
    data so that you can ignore wavelength variation within each theory value.
    """
    # Make all data have the same shape
    columns = (
        data.Qz, data.dQ, data.v, data.dv,
        data.Ti, data.angular_resolution, data.Ld, data.dL)
    columns = [np.broadcast_to(p, data.v.shape) for p in columns]
    columns = [p[:, :, bank].flatten() for p in columns]
    q, dq, y, dy, T, dT, L, dL = columns

    # Sort q values into bins
    nbins = len(q_edges) - 1
    bin_index = np.searchsorted(q_edges, q) - 1

    # Some bins may not have any points contributing, such as those before
    # and after, or those in the middle if the q-step is too fine. These
    # will be excluded from the final result.
    points_per_bin = np.bincount(bin_index, minlength=nbins)
    # Note: we add empty_q to the divisor in a number of places to protect
    # against divide by zero in those bins. Since we are excluding these at
    # the end, this removes the spurious warnings without changing results.
    empty_q = (points_per_bin == 0)
    # The following is cribbed from util.poisson_average, replacing
    # np.sum with np.bincount.
    # TODO: update poisson average so it handles grouping
    norm = data.normbase
    if average == "gauss":
        dy = dy + (dy == 0) # protect against zero uncertainty
        Swx = np.bincount(bin_index, weights=y/dy**2, minlength=nbins)
        Sw = np.bincount(bin_index, weights=dy**-2, minlength=nbins)
        Sw += empty_q  # Protect against division by zero
        bar_y = Swx / Sw
        bar_dy = 1/np.sqrt(Sw)
    elif norm == "none":
        bar_y = np.bincount(bin_index, weights=y, minlength=nbins)
        bar_dy = np.sqrt(np.bincount(bin_index, weights=dy**2, minlength=nbins))
    else:
        # Counts must be positive for poisson averaging...
        y = y.copy()
        y[y < 0] = 0.
        dy = dy + (dy == 0) # protect against zero uncertainty
        monitors = y*(y+1)/dy**2 if norm == "monitor" else y/dy**2 # if "time"
        monitors[y == 0] = 1./dy[y == 0] # protect against zero counts
        counts = y*monitors
        combined_monitors = np.bincount(bin_index, weights=monitors, minlength=nbins)
        combined_counts = np.bincount(bin_index, weights=counts, minlength=nbins)
        combined_monitors += empty_q  # Protect against division by zero
        bar_y = combined_counts/combined_monitors
        if norm == "time":
            bar_dy = np.sqrt(bar_y / combined_monitors)
        else:
            bar_dy = 1./combined_monitors * np.sqrt(1. + 1./combined_monitors)
            idx = (bar_y != 0)
            bar_dy[idx] = bar_y[idx] * np.sqrt(1./combined_counts[idx]
                                               + 1./combined_monitors[idx])

    # Find Q center and resolution, weighting by intensity
    w = np.ones_like(y)  # Weights must be positive; use equal weights for now
    #w = y # use intensity weighting when finding q centers
    sum_w = np.bincount(bin_index, weights=w, minlength=nbins)
    #assert ((sum_w == 0) == empty_q).all()
    sum_w += empty_q  # protect against divide by zero
    sum_q = np.bincount(bin_index, weights=q*w, minlength=nbins)
    bar_q = sum_q / sum_w
    # Combined dq according to mixture distribution.
    sum_dqsq = np.bincount(bin_index, weights=w*(dq**2 + q**2), minlength=nbins)
    bar_dq = np.sqrt(sum_dqsq/sum_w - bar_q**2)
    ## Combined dq according average of variance.
    #bar_dq = np.sqrt(np.bincount(bin_index, weights=dq*w, minlength=nbins)/bar_w)
    # Set dq to 1% for now...
    #bar_dq = bar_q*0.01

    # Combine wavelengths
    sum_Linv = np.bincount(bin_index, weights=w/L, minlength=nbins)
    #assert ((sum_Linv == 0) == empty_q).all()
    sum_Linv += empty_q  # protect against divide by zero
    bar_Linv = sum_w/sum_Linv  # Not the first moment of L
    sum_L = np.bincount(bin_index, weights=w*L, minlength=nbins)
    sum_dLsq = np.bincount(bin_index, weights=w*(dL**2+L**2), minlength=nbins)
    bar_dL = np.sqrt(sum_dLsq/sum_w - (sum_L/sum_w)**2)

    # Combine angles
    bar_T = np.degrees(np.arcsin(bar_q*bar_Linv / 4 / np.pi))
    sum_dT = np.bincount(bin_index, weights=w*dT**2, minlength=nbins)
    bar_dT = np.sqrt(sum_dT/sum_w)

    # Need to drop catch-all bins before and after q edges.
    # Also need to drop q bins which don't contain any values.
    keep = ~empty_q
    keep[0] = keep[-1] = False
    columns = (bar_q, bar_dq, bar_y, bar_dy, bar_T, bar_dT, bar_Linv, bar_dL)
    return [p[keep] for p in columns]

def edges(c, extended=False):
    r"""
    Linear bin edges given centers.

    If *extended* then create before/after bins so coverage is $(-\infty, \infty)$.
    """
    midpoints = (c[:-1]+c[1:])/2
    left = 2*c[0] - midpoints[0]
    right = 2*c[-1] - midpoints[-1]
    if extended:
        return np.hstack((-np.inf, left, midpoints, right, np.inf))
    else:
        return np.hstack((left, midpoints, right))

if __name__ == "__main__":
    from .nexusref import demo
    demo(loader=load_entries)
