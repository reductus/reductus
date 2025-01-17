#!/usr/bin/env python
from copy import copy

import numpy as np

from .refldata import ReflData, PSDData
from .nexusref import load_nexus_entries, nexus_common
from .nexusref import data_as, str_data
from .nexusref import TRAJECTORY_INTENTS
from .resolution import FWHM2sigma

def load_metadata(filename, file_obj=None):
    """
    Load the summary info for all entries in a NeXus file.
    """
    return load_nexus_entries(filename, file_obj=file_obj,
                              meta_only=True, entry_loader=NG7PSD)

def load_entries(filename, file_obj=None, entries=None):
    #print("loading", filename, file_obj)
    return load_nexus_entries(filename, file_obj=file_obj, entries=entries,
                              meta_only=False, entry_loader=NG7PSD)

WAVELENGTH = 4.768
WAVELENGTH_DISPERSION = 0.025
S1_DISTANCE = -1722.25
S2_DISTANCE = -222.25
S3_DISTANCE = 229.0
DETECTOR_DISTANCE = 2006.
PIXEL_WIDTH = 100./256
PIXEL_OFFSET = np.linspace(0, 100, 257)[:-1] - 50 + 1/256

class NG7PSD(PSDData):
    """
    NG7PSD entry.

    See :class:`refldata.ReflData` for details.
    """
    format = "NeXus"
    probe = "neutrons"

    def __init__(self, entry, entryname, filename):
        super(NG7PSD, self).__init__()
        nexus_common(self, entry, entryname, filename)
        self.geometry = 'horizontal'

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
            self.warn("Wavelength is missing for %r; using %.3f A"
                      % (self.name, WAVELENGTH))
            self.monochromator.wavelength = WAVELENGTH
        if self.monochromator.wavelength_resolution is None:
            self.warn("Wavelength resolution is missing for %r; using %.1f%% dL/L FWHM"
                      % (self.name, 100*WAVELENGTH_DISPERSION))
            self.monochromator.wavelength_resolution = \
                FWHM2sigma(WAVELENGTH_DISPERSION*self.monochromator.wavelength)

        # Slits
        # Read slit opening from the data file
        for k, slit in enumerate((self.slit1, self.slit2, self.slit3)):
            x = 'slitAperture%d/softPosition'%(k+1)
            x_target = 'slitAperture%d/desiredSoftPosition'%(k+1)
            slit.x = data_as(das, x, 'mm', rep=n)
            slit.x_target = data_as(das, x_target, 'mm', rep=n)
            #y = 'vertSlitAperture%d/softPosition'%(k+1)
            #y_target = 'vertSlitAperture%d/desiredSoftPosition'%(k+1)
            #slit.y = data_as(das, y, 'mm', rep=n)
            #slit.y_target = data_as(das, y_target, 'mm', rep=n)
        # There is no slit 4: use detector pixel width instead.
        self.slit4.x = data_as(entry, 'instrument/PSD/x_pixel_size', 'mm')
        if self.slit4.x is None:
            self.slit4.x = 0.390625  # 10 cm / 256 pixels
        self.slit4.x_target = self.slit4.x
        # Get slit distances as set by nexus config.js
        self.slit1.distance = data_as(entry, 'instrument/presample_slit1/distance', 'mm')
        self.slit2.distance = data_as(entry, 'instrument/presample_slit2/distance', 'mm')
        self.slit3.distance = data_as(entry, 'instrument/predetector_slit1/distance', 'mm')
        self.slit4.distance = data_as(entry, 'instrument/predetector_slit2/distance', 'mm')
        # Fill in missing distance data, if they aren't in the config file
        for slit, default in (
                (self.slit1, S1_DISTANCE),
                (self.slit2, S2_DISTANCE),
                (self.slit3, S3_DISTANCE),
                (self.slit4, DETECTOR_DISTANCE),
                ):
            if slit.distance is None:
                slit.distance = default
        # TODO: Correct for distance increase with q (5mm over 2m at q=0.2)
        # ... and the corresponding 1/4 % decrease in divergence per pixel
        # As the sample drops the slits pull away from the sample according
        # to the following:
        #    d = x * sqrt(tan(theta)^2 + 1)  # distance to detector center
        #      = nominal_distance * sqrt(tan(radians(detector_angle))**2 + 1)
        #    delta = d - nominal_distance
        # so S1, S2, S3 and detector distance all need to increase by this much.
        # Note: This calculation is used when computing the property Td_target,
        # the pixel angle for each point on the detector.

        # Detector
        self.detector.wavelength = self.monochromator.wavelength
        self.detector.wavelength_resolution = self.monochromator.wavelength_resolution
        self.detector.deadtime = data_as(entry, 'instrument/PSD/dead_time', 'us')
        self.detector.deadtime_error = data_as(entry, 'instrument/PSD/dead_time_error', 'us')
        self.detector.distance = data_as(entry, 'instrument/PSD/distance', 'mm')
        self.detector.rotation = data_as(entry, 'instrument/PSD/rotation', 'degree')
        if self.detector.distance is None:
            self.detector.distance = DETECTOR_DISTANCE
            self.warn("PSD distance is missing for %r; using %.1f mm"
                      % (self.name, self.detector.distance))

        # TODO: ng7r/nexus/config.js needs to record info about the PSD

        # Load data from linear detector.  Note that counts/liveROI may not
        # match if counts/roiAgainst is against a different detector.
        self.detector.counts = data_as(das, 'linearDetector/counts', '', dtype='d')
        #print("detector shape", self.detector.counts.shape)
        self.detector.counts_variance = self.detector.counts.copy()
        self.detector.dims = self.detector.counts.shape[1:]
        npixels = self.detector.dims[0]
        # TODO: is detector center in the data file?
        self.detector.center = [128, 0]
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
            raise ValueError("Unknown sample angle in file %r" % self.name)
        self.Qz_target = data_as(das, 'q/z', '', rep=n)
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

        # TODO: what does angular resolution mean before integration?
        from .angles import divergence_simple as divergence
        # Use slit2 and pixel width for the collimation geometry. The values
        # for pixel width and distances are stored as slit 4.
        slits = (self.slit4.x, self.slit2.x)
        distance = (self.slit4.distance, self.slit2.distance)
        theta = self.sample.angle_x
        self.angular_resolution = divergence(
            slits=slits, distance=distance, T=theta,
            sample_width=np.inf,
            use_sample=False,
        )

    @property
    def Ti_target(self):
        return self.sample.angle_x[:, None] # [n, 1]

    @property
    def Td_target(self):
        # Assuming the detector tilts with angle as the sampleElevator drops,
        # increasing the length of the arm slightly at the sample center.
        # Note: using a fixed distance would give 2% error on angle at q=0.5
        x = self.detector.distance  # [1]
        theta = np.radians(self.detector.angle_x) # [n]
        distance = x * np.sqrt(np.tan(theta)**2 + 1)  # [n] * [1] = [n]
        center = self.detector.center[0]  # [1]
        offset = self.detector.offset_x # [p]
        pixel_y = offset + center # [p]
        pixel_theta = np.arctan2(pixel_y[None, :], distance[:, None]) # [n, p]
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

def apply_integration(
        data, spec=(1, 0), left=(1, 0), right=(1, 0), pixel_range=(1, 256),
        degree=0, mc_samples=0, seed=None, slices=[],
    ):
    """
    Apply integration to *data* returning specular, backgroundm, residual
    after background subtraction and slices.

    *data* is a dataset containing psd data in *data.v*.

    *spec*, *left* and *right* are (scale, offset) for the boundaries of the
    specular, left background and right background respectively.  The scale
    applies to the divergence estimated from slit 1 and the offset is the
    number of pixels to add or subtract from that width.

    *pixel_range* refers to the outer edges of the valid detector pixels.

    *degree* is the polynomial degree fitted to the background.

    *mc_samples* are the number of Monte Carlo samples to use when estimating
    background value and uncertainty under the signal.  Use 0 for an estimate
    directly from the uncertainty in the fitting parameters
    (**mc_samples==0 is broken** as of this writing).  Set *seed* to a fixed
    value for reproducible results.

    *slices* is a list of coordinates at which to display cross sections of
    the background fit.
    """
    from reductus.dataflow.lib.seed import push_seed

    # Make sure Monte Carlo simulations are reproducible by using the
    # same seed every time.
    with push_seed(seed):
        Is, Ib, residual, slice_plot = integrate(
            data, spec, left, right, pixel_range,
            degree, mc_samples, slices,
        )

    spec_data, back_data = _build_1d(data, Is), _build_1d(data, Ib)

    resid_data = copy(data)
    resid_data.v = residual

    return spec_data, back_data, resid_data, slice_plot

def _build_1d(head, intensity):
    # Initialize new from existing data
    data = ReflData()
    for field_name in data._fields:
        setattr(data, field_name, getattr(head, field_name, None))
    for group_name, _ in data._groups:
        data_group, head_group = getattr(data, group_name), getattr(head, group_name)
        for field_name in data_group._fields:
            setattr(data_group, field_name, getattr(head_group, field_name, None))

    # Kill fields we don't want anymore
    v, dv = intensity
    data.detector.counts = v
    data.detector.counts_variance = dv**2
    data.detector.dims = [1]
    data.detector.center = [0, 0]
    data.detector.width_x = np.sum(data.detector.width_x)
    data.detector.offset_x = 0.
    data.detector.mask = None
    data.warnings = []  # initialize per-file history
    data.intent = head.intent
    return data

def integrate(data, spec, left, right, pixel_range,
              degree, mc_samples, slices):
    from reductus.dataflow.lib import err1d
    from reductus.dataflow.lib.wsolve import wpolyfit

    nframes, npixels = data.v.shape

    # Determine the boundaries of each frame
    slit_width, pixel_width = data.slit1.x, data.slit4.x
    divergence = slit_width / pixel_width
    spec_width = spec[0]*divergence + spec[1]
    back_left = spec_width + np.maximum(left[0]*divergence + left[1], 0)
    back_right = spec_width + np.maximum(right[0]*divergence + right[1], 0)
    #print("integrate", spec, slit_width, pixel_width, spec_width, back_left, back_right)

    # Pixels are numbered from 1 to npixels, including the center pixel.
    # Normalize the pixels so the polynomial fitter uses smaller x.
    # Could also normalize by resolution width, but that makes it harder
    # to identify where the integration region is bad.
    center = data.detector.center[0]
    min_pixel, max_pixel = pixel_range
    p1 = np.maximum(min_pixel-center, -back_left)
    p2 = np.maximum(min_pixel-center, -spec_width)
    p3 = np.minimum(max_pixel-center, +spec_width)
    p4 = np.minimum(max_pixel-center, +back_right)
    pixel = np.arange(1, npixels+1) - center

    # TODO: maybe estimate divergence from specular peak width?
    # The following does not work:
    #    # Assume signal width is chosen to span +/- 2 sigma, or 95%.
    #    sigma = (p3 - p2)/4 * pixel_width
    #    divergence = np.degrees(np.arctan(sigma / data.detector.distance))

    # Find slices we want to plot by looking up the selected slice values
    # in the list of y values for the frames.
    (_, _), (yaxis, _) = data.get_axes() # get the data axes
    index = np.searchsorted(yaxis, slices)
    # TODO: search y-axis as bin edges rather than centers
    index = index[(index > 0)&(index < nframes)] - 1 # can't do last slice
    index = set(index) # duplicates and order don't matter for sets

    # Prepare plottable for slices
    series = [] # [{"label": str}, ...]
    lines = [] # [{c: {"values": [], "errorbars": []} for c in (pixel, intensity, error)}
    columns = {
        "pixel": {"label": "Pixel", "units": ""}, # no errorbars
        "intensity": {"label": "Intensity", "units": "counts", "errorbars": "error"}
    }
    plottable = {
        "type": "1d",
        "title": data.name + ":" + data.entry,
        "entry": data.entry,
        "columns": columns,
        "options": {
            "series": series,
            "axes": {
                "xaxis": {"label": "Pixel"},
                "yaxis": {"label": "Intensity (counts)"},
            },
            "xcol": "pixel",
            "ycol": "intensity",
            "errorbar_width": 0,
        },
        "data": lines,
    }
    def addline(label, x, y, dy=None):
        #print("line", label, x, y, dy)
        if dy is not None:
            line = [[xk, yk, {"yupper":yk+dyk, "ylower": yk-dyk}]
                    for xk, yk, dyk in zip(x, y, dy)]
        else:
            line = [[xk, yk] for xk, yk in zip(x, y)]
        series.append(label)
        lines.append(line)

    # Cycle through detector frames gathering signal and background for each.
    results = []
    for k in range(nframes):
        # Get data for frame.
        y, dy = data.v[k], data.dv[k]
        spec_idx = (pixel >= p2[k]) & (pixel <= p3[k])
        full_idx = (pixel >= p1[k]) & (pixel <= p4[k])
        back_idx = full_idx & ~spec_idx
        spec_x, spec_y, spec_dy = pixel[spec_idx], y[spec_idx], dy[spec_idx]
        back_x, back_y, back_dy = pixel[back_idx], y[back_idx], dy[back_idx]

        if not len(spec_x) or not len(back_x):
            results.append((np.nan, np.nan, np.nan, np.nan, np.zeros_like(y)))
            continue

        # Integrate frame data.
        # TODO: Could do sub-pixel interpolation at the boundary?
        Is, dIs = poisson_sum(spec_y, spec_dy)
        fit = wpolyfit(back_x, back_y, back_dy, degree=degree)
        # Uh, oh! Correlated errors on poly coefficients! How do we integrate?
        if mc_samples > 0: # using monte-carlo sampling
            # Generate a random set of polynomials from the fit
            coeffs = fit.rand(size=mc_samples)
            # Use Horner's method to evaluate all p_k over all x points
            px = np.zeros((len(spec_x), mc_samples))
            for c in coeffs.T:
                px *= spec_x[:, None]
                px += c[None, :]
            # Integrate p(x) over x
            integral = np.sum(px, axis=0)
            #print("integral", px.shape, mc_samples, coeffs.shape, integral.shape)
            # Find mean and variance of the integrated values
            Ib, dIb = np.mean(integral), np.std(integral)
        else: # using simple sum ignoring correlation in uncertainties
            est_y = fit(spec_x)
            est_dy = fit.ci(spec_x)
            Ib, dIb = err1d.sum(est_y, est_dy)

        # TODO: consider fitting gaussian to peak or finding FWHM of spec-back
        #signal = spec_y - fit(spec_x)
        #halfmax = signal.max() / 2
        #top_half = spec_x[signal > halfmax]
        #FWHM = top_half[-1] - top_half[0]
        #sigma = FWHM/(2*sqrt(2*log(2)))

        # add slices if the index is in the set of selected indices
        if k in index:
            valstr = str(yaxis[k])
            addline('data:'+valstr, pixel, y, dy)
            addline('spec:'+valstr, spec_x, fit(spec_x))
            addline('back:'+valstr, back_x, fit(back_x))

        # Show background residuals
        residual = y - fit(pixel)
        residual[~full_idx] = np.nan #0.
        #residual[spec_idx] += signal_jump

        results.append((Is, dIs, Ib, dIb, residual))

    Is, dIs, Ib, dIb, residual = (np.asarray(v) for v in zip(*results))

    return (Is, dIs), (Ib, dIb), residual, plottable

def poisson_sum(v, dv):
    """
    Sum data with poisson uncertainties.

    This happens to be the same as the sum of gaussian distributed
    uncertainties, with V = sum(v) and dV = sqrt(sum(dv^2)), preserving
    the relationship that variance of the sum matches its expected value.
    This even works if all elements of the sum have been scaled, for example
    by a shared deadtime factor.  In that case, Guassian propagation causes
    dv to be scaled by C, so variance is scaled by C^2, which becomes
    C dV after the square root.

    When integrating background, be sure the variance uses sqrt(counts)
    even when counts are zero for a bin, otherwise the uncertainty on the
    integrated counts will be overestimated.

    There is an important case where poisson integration will produce a
    different result from strict gaussian error propagation. That is for
    detectors where events give rise to a signal that is assigned to one
    pixel or its neighbour based on properties of the signal.  Inhomogeneities
    will lead to differing pixel widths across the detector, which shows
    up as different count rates per pixel in a flood-field measurement.
    In this case, it is better to sum the raw counts across the pixel region
    and scale by the average width of the contributing pixels rather than
    normalizing counts by pixel width then summing.

    For independent detectors with separate detection efficiency the
    situation is a little different.  In that case it is better to sum
    the efficiency corrected data using gaussian error propagation on
    the values, at least when the number of counts is large.  Not sure
    how to properly normalize across different detector efficiencies when
    counts are mostly zero, though gaussian approximation to the error
    is probably going to be good enough.

    When computing count rate, you should integrate peaks and backgrounds
    before normalizing by time or monitor counts. The normalization factor
    only drops out in the integration equations when you are using
    variance equal to number of counts.  However, when you are computing
    count rates, you will probably set the uncertainty for zero counts
    to 1/t rather than 0/t.  If you don't you will not be able to fit
    the data since the weighted residual will be infinite when you have
    zero uncertainty on a measurement.
    """
    return np.sum(v), np.sqrt(np.sum(dv**2))


if __name__ == "__main__":
    # Example:
    #   python -m reflred.ng7psd ncnr://ncnrdata/ng7/202001/27596/data/5ppm_NRW_0M33037.nxz.ng7
    from .nexusref import demo
    demo(loader=load_entries)
