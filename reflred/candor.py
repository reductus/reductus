#!/usr/bin/env python
from warnings import warn

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
        _EFFICIENCY = np.vstack((eff, eff)).T
    return _EFFICIENCY

class Candor(ReflData):
    """
    Candor data entry.

    See :class:`refldata.ReflData` for details.
    """
    format = "NeXus"
    probe = "neutron"

    def __init__(self, entry, entryname, filename):
        super().__init__()
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
            #y = 'vertSlitAperture%d/softPosition'%(k+1)
            #y_target = 'vertSlitAperture%d/desiredSoftPosition'%(k+1)
            #slit.y = data_as(das, y, 'mm', rep=n)
            #slit.y_target = data_as(das, y_target, 'mm', rep=n)
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

        # TODO: check the orientation on detectorTable nodes.
        # For now they appear to be in "channels_at_end" order even if the
        # detector counts are in "banks_at_end" order.
        wavelength = wavelength.reshape(NUM_CHANNELS, -1)
        wavelength_spread = wavelength_spread.reshape(NUM_CHANNELS, -1)
        divergence = divergence.reshape(NUM_CHANNELS, -1)
        efficiency = efficiency.reshape(NUM_CHANNELS, -1)

        wavelength_resolution = FWHM2sigma(wavelength * wavelength_spread)
        if (efficiency == 1.0).all():
            efficiency = detector_efficiency()

        self.detector.wavelength = wavelength[None, :, :]
        self.detector.wavelength_resolution = wavelength_resolution[None, :, :]
        self.detector.efficiency = efficiency[None, :, :]
        self.angular_resolution = divergence[None, :, :]
        # TODO: sample broadening?

        # Angles
        self.sample.angle_x = data_as(das, 'sampleAngleMotor/softPosition', 'degree', rep=n)
        self.sample.angle_x_target = data_as(das, 'sampleAngleMotor/desiredSoftPosition', 'degree', rep=n)
        self.detector.angle_x = data_as(das, 'detectorTableMotor/softPosition', 'degree', rep=n)
        self.detector.angle_x_target = data_as(das, 'detectorTableMotor/desiredSoftPosition', 'degree', rep=n)
        self.detector.angle_x_offset = data_as(das, 'detectorTable/rowAngularOffsets', '')[0]

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
        if self.sample.angle_x.max() - self.sample.angle_x.min() > 0.01:
            y, ylabel = self.sample.angle_x, "Detector Angle (degrees)"
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
        ny, nx, _ = data.shape  # nangles, nwavelengths, nbanks
        (x, xlabel), (y, ylabel) = self.get_axes()
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
    def __init__(self, data, q, dq, v, dv):
        super().__init__()
        self.sample = data.sample
        self.probe = data.probe
        self.path = data.path
        self.uri = data.uri
        self.name = data.name
        self.entry = data.entry
        self.description = data.description
        self.polarization = data.polarization
        self.normbase = data.normbase
        self._q = q
        self._dq = dq
        self.v = v
        self.dv = dv
        self.intent = Intent.spec
        self.points = len(q)
        # TODO: set something for dL and dT
        self.angular_resolution = 1.
        self.scan_value = []
        self.scan_units = []
        self.scan_label = []

    @property
    def Qz(self):
        return self._q

    @property
    def Qx(self):
        return np.zeros_like(self._q)

    @property
    def dQ(self):
        return self._dq

def rebin(data, q):
    if data.normbase not in ("monitor", "time", "none"):
        raise ValueError("expected norm to be time, monitor or none")
    q_edges = edges(q, extended=True)
    datasets = []
    for bank in range(data.v.shape[2]):
        qz, dq, v, dv = _rebin_bank(data, bank, q_edges)
        #output = ReflData()
        #output.v, output.dv = v, dv
        #output.x, output.dx = q, dq
        datasets.append(QData(data, qz, dq, v, dv))

    # Only look at bank 0 for now
    return datasets[0]

def _rebin_bank(data, bank, q_edges):
    """
    Merge q points across channels and angles, returning q, dq, v, dv.

    Intensities (v, dv) are combined using poisson averaging.

    Q values (Q, dQ) for the combined measurements are weighted by intensity.
    This means that identical measurement conditions may give different
    (Q, dQ) depending on the randomness in the measured value.

    There is a simple expression for the moments of a mixture of distributions:
        T = (sum wk . T) / (sum wk)
        dT^2 = (sum wk . (dTk^2 + Tk^2)) / (sum wk) - T^2
    See: https://en.wikipedia.org/wiki/Mixture_density#Moments

    When rebinning Candor values as a function of Q then apply this directly
    to (Q, dQ) since the resolution function is curved in theta-lambda space.
    Note that the fitting function will need a weighted wavelength distribution
    for rare earths and for strongly absorbing samples where the scattering is
    wavelength dependent. It may suffice to compute the joint dQ and dL then
    assign dT so that it is consistent: this will underestimate the true dT,
    but it should be good enough for fitting. Alternatively, measure fewer
    angles for longer and do not merge points so that you can ignore
    wavelength variation within each theory value.
    """
    norm = data.normbase
    y, dy, q, dq = (val[:, :, bank].flatten()
                    for val in (data.v, data.dv, data.Qz, data.dQ))
    nbins = len(q_edges) - 1
    bin_index = np.searchsorted(q_edges, q)

    # Some bins may not have any points contributing, such as those before
    # and after, or those in the middle if the q-step is too fine.
    empty_q = (np.bincount(bin_index, minlength=nbins) == 0)
    # The following is cribbed from util.poisson_average, replacing
    # np.sum with np.bincount.
    # TODO: update poisson average so it handles grouping
    if norm == "none":
        bar_y = np.bincount(bin_index, weights=y, minlength=nbins)
        bar_dy = np.bincount(bin_index, weights=dy**2, minlength=nbins)
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
        combined_monitors += empty_q  # protect against division by zero
        bar_y = combined_counts/combined_monitors
        if norm == "time":
            bar_dy = bar_y * np.sqrt(1./combined_monitors)
        else:
            bar_dy = 1./combined_monitors * np.sqrt(1. + 1./combined_monitors)
            idx = (bar_y != 0)
            bar_dy[idx] = bar_y[idx] * np.sqrt(1./combined_counts[idx]
                                            + 1./combined_monitors[idx])

    # Find Q center and resolution, weighting by intensity
    # TODO: use intensity weighting when finding q centers?
    #weights = y
    w = np.ones_like(y)  # Weights must be positivie; use equal weights for now
    bar_w = np.bincount(bin_index, weights=w, minlength=nbins)
    bar_w += (bar_w == 0)  # protect against divide by zero
    bar_q = np.bincount(bin_index, weights=q*w, minlength=nbins)/bar_w
    # TODO: proper dQ calculation
    # Combined dq according to mixture distribution.
    #qsq = np.bincount(bin_index, weights=q**2*w, minlength=nbins)
    #dqsq = np.bincount(bin_index, weights=dq**2*w, minlength=nbins)
    #bar_dq = np.sqrt((dqsq + qsq)/bar_w - bar_q**2)
    # Combined dq according average of variance.
    #bar_dq = np.sqrt(np.bincount(bin_index, weights=dq*w, minlength=nbins)/bar_w)
    # Set dq to 1% for now...
    bar_dq = bar_q*0.01

    # Need to drop catch-all bins before and after q edges.
    # Also need to drop q bins which don't contain any values.
    keep = ~empty_q
    keep[0] = keep[-1] = False
    return bar_q[keep], bar_dq[keep], bar_y[keep], bar_dy[keep]

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
