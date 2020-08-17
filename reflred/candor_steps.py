# This program is public domain
from copy import copy

import numpy as np

from dataflow.automod import cache, nocache, module, copy_module
# Note: do not load symbols from .steps directly into the file scope
# or they will be defined twice as reduction modules.
from . import steps

@cache
@module("candor")
def candor(
        filelist=None,
        bank_select=None,
        channel_select=None,
        dc_rate=0.,
        dc_slope=0.,
        detector_correction=False,
        monitor_correction=False,
        spectral_correction=False,
        Qz_basis='target',
        intent='auto',
        sample_width=None,
        base='auto'):
    r"""
    Load a list of Candor files from the NCNR data server.

    **Inputs**

    filelist (fileinfo[]): List of files to open.

    bank_select {Select bank} (int) : Choose bank to output (default is all)

    channel_select {Select channel(s)} (int[]*) : Choose channels to output from bank (default is all)

    dc_rate {Dark counts per minute} (float)
    : Number of dark counts to subtract from each detector channel per
    minute of counting time (see Dark Current).

    dc_slope {DC vs. slit 1} (float)
    : Dark counts per mm of slit 1 opening per minute.

    detector_correction {Apply detector deadtime correction} (bool)
    : If True, use deadtime constants in file to correct detector counts
    (see Detector Dead Time).

    monitor_correction {Apply monitor deadtime correction} (bool)
    : If True, use deadtime constants in file to correct monitor counts
    (see Monitor Dead Time).

    spectral_correction {Apply detector efficiency correction} (bool)
    : If True, scale counts by the detector efficiency calibration given
    in the file (see Spectral Efficiency).

    Qz_basis (opt:target|sample|detector|actual)
    : How to calculate Qz from instrument angles.

    intent (opt:auto|specular|background+\|background-\|intensity|rock sample|rock detector|rock qx|scan)
    : Measurement intent (specular, background+, background-, slit, rock),
    auto or infer.  If intent is 'scan', then use the first scanned variable.

    sample_width {Sample width (mm)} (float?)
    : Width of the sample along the beam direction in mm, used for
    calculating the effective resolution when the sample is smaller
    than the beam.  Leave blank to use value from data file.

    base {Normalize by} (opt:auto|monitor|time|roi|power|none)
    : How to convert from counts to count rates. Leave this as none if your
    template does normalization after integration (see Normalize).

    **Returns**

    output (candordata[]): All entries of all files in the list.

    | 2020-02-05 Paul Kienzle
    | 2020-03-12 Paul Kienzle Add slit 1 dependence for DC rate
    """
    from .load import url_load_list
    from .candor import load_entries
    auto_divergence = True

    # Note: candor automatically computes divergence.
    datasets = []
    for data in url_load_list(filelist, loader=load_entries):
        # TODO: drop data rows where fastShutter.openState is 0
        data.Qz_basis = Qz_basis
        if intent not in (None, 'none', 'auto'):
            data.intent = intent
        if bank_select is not None:
            data = select_bank(data, bank_select)
        if channel_select is not None:
            data = select_channel(data, channel_select)
        if auto_divergence:
            data = steps.divergence_fb(data, sample_width)
        if dc_rate != 0. or dc_slope != 0.:
            data = dark_current(data, dc_rate, dc_slope)
        if detector_correction:
            data = steps.detector_dead_time(data, None)
        if monitor_correction:
            data = steps.monitor_dead_time(data, None)
        if spectral_correction:
            data = spectral_efficiency(data)
        data = steps.normalize(data, base=base)
        datasets.append(data)

    return datasets

@module("candor")
def select_bank(data, bank_select=None):
    r"""
    Remove banks from Candor data.

    **Inputs**

    data (candordata): Input data with 1 or more banks

    bank_select {Select bank} (int) : Choose banks to output (default is all)

    **Returns**

    output (candordata): Data with indices not listed in bank_select removed.

    | 2020-07-07 Brian Maranville 
    """

    if bank_select is not None:
        data = copy(data)
        data.detector.counts = data.detector.counts[:,:,[bank_select]]
        data.detector.counts_variance = data.detector.counts.copy()
        data.detector.dims = data.detector.counts.shape

        data.detector.efficiency = data.detector.efficiency[:,:,[bank_select]]
        data.detector.angle_x_offset = data.detector.angle_x_offset[[bank_select]]
        data.detector.wavelength = data.detector.wavelength[:,:,[bank_select]]
        data.detector.wavelength_resolution = data.detector.wavelength_resolution[:,:,[bank_select]]
    
    return data

@module("candor")
def select_channel(data, channel_select=None):
    r"""
    Select channels from bank of Candor data.

    **Inputs**

    data (candordata): Input data with 1 or more banks

    channel_select {Select channel(s)} (int[]*) : Choose channels to output (default is all)

    **Returns**

    output (candordata): Data with indices not listed in channel_select removed.

    | 2020-07-12 Brian Maranville 
    """

    if channel_select is not None:
        data = copy(data)
        data.detector = copy(data.detector)										   
        data.detector.counts = data.detector.counts[:,channel_select,:]
        data.detector.counts_variance = data.detector.counts_variance[:,channel_select,:]
        data.detector.dims = data.detector.counts.shape

        data.detector.efficiency = data.detector.efficiency[:,channel_select,:]
        data.detector.wavelength = data.detector.wavelength[:,channel_select,:]
        data.detector.wavelength_resolution = data.detector.wavelength_resolution[:,channel_select,:]
        if data._v is not None:
            data._v = data._v[:,channel_select,:]
        if data._dv is not None:
            data._dv = data._dv[:,channel_select,:]
    return data

@module("candor")
def select_points(data, point_select=None):
    r"""
    Select data points from scan of Candor.

    **Inputs**

    data (candordata): Input data with 1 or more banks

    point_select {Select points(s)} (int[]*) : Choose points to output (default is all)

    **Returns**

    output (candordata): Data with point indices not listed in point_select removed.

    | 2020-07-03 Brian Maranville 
    """

    if point_select is not None:
        data = copy(data)
        data.detector.counts = data.detector.counts[point_select]
        data.detector.counts_variance = data.detector.counts_variance[point_select]
        data.detector.dims = data.detector.counts.shape
        monitor = data.monitor
        monitor.counts = monitor.counts[point_select]
        monitor.counts_variance = monitor.counts_variance[point_select]
        monitor.count_time = monitor.count_time[point_select]
        monitor.roi_counts = monitor.roi_counts[point_select]
        monitor.roi_variance = monitor.roi_variance[point_select]
        monitor.source_power = monitor.source_power[point_select]
        monitor.source_power_variance = monitor.source_power_variance[point_select]

        if data._v is not None:
            data.v = data.v[point_select]
        if data._dv is not None:
            data.dv = data.dv[point_select]
        if data.angular_resolution is not None:
            data.angular_resolution = data.angular_resolution[point_select]

        for slit in (data.slit1, data.slit2, data.slit3, data.slit4):
            slit.x = slit.x[point_select]
            slit.x_target = slit.x_target[point_select]

        data.sample.angle_x = data.sample.angle_x[point_select]
        data.sample.angle_x_target = data.sample.angle_x_target[point_select]
        data.detector.angle_x = data.detector.angle_x[point_select]
        data.detector.angle_x_target = data.detector.angle_x_target[point_select]
    
    return data


@module("candor")
def spectral_efficiency(data, spectrum=()):
    r"""
    Correct for the relative intensity in the different detector channels
    across the detector banks.  This correction depends on a number of
    factors including the distribution of wavelenths from the source,
    any wavelength selection filters in the path, the relative angles
    of the analyzer leaves, and the efficiency of the detector in each
    channel.

    **Inputs**

    data (candordata) : data to scale

    spectrum (float[]?) : override spectrum from data file

    **Returns**

    output (candordata) : scaled data

    | 2020-03-03 Paul Kienzle
    """
    #from .candor import NUM_CHANNELS
    # TODO: too many components operating directly on detector counts?
    # TODO: let the user paste their own spectral efficiency, overriding datafile
    # TODO: generalize to detector shapes beyond candor
    #print(data.v.shape, data.detector.efficiency.shape)
    #if len(spectrum)%NUM_CHANNELS != 0:
    #    raise ValueError("Vector length {s_len} must be a multiple of {NUM_CHANNELS}".format(s_len=len(spectrum), NUM_CHANNELS=NUM_CHANNELS))
    if spectrum:
        #spectrum = np.reshape(spectrum, (NUM_CHANNELS, -1)).T[None, :, :]
        spectrum = np.reshape(spectrum, data.detector.efficiency.shape)
    else:
        spectrum = data.detector.efficiency
    data = copy(data)
    data.detector = copy(data.detector)
    data.detector.counts = data.detector.counts / spectrum
    data.detector.counts_variance = data.detector.counts_variance / spectrum
    return data


@module("candor")
def recalibrate_wavelength(data, wavelengths=(), wavelength_resolutions=()):
    r"""
    Use different wavelength calibration from that already in the data file.

    **Inputs**

    data (candordata) : data to scale

    wavelengths (float[]?) : override wavelengths from data file
    
    wavelength_resolutions (float[]?) : override wavelength spreads (sigma) from data file

    **Returns**

    output (candordata) : scaled data

    | 2020-08-14 David Hoogerheide
    """
    # TODO: too many components operating directly on detector counts?
    # TODO: let the user paste their own spectral efficiency, overriding datafile
    # TODO: generalize to detector shapes beyond candor
    if wavelengths:
        wavelengths = np.reshape(wavelengths, data.detector.wavelength.shape)
    else:
        wavelengths = data.detector.wavelength
    if wavelength_resolutions:
        wavelength_resolutions = np.reshape(wavelength_resolutions, data.detector.wavelength_resolution.shape)
    else:
        wavelength_resolutions = data.detector.wavelength_resolution
    data = copy(data)
    data.detector = copy(data.detector)
    data.detector.wavelength = wavelengths
    data.detector.wavelength_resolution = wavelength_resolutions
    return data

@module("candor")
def dark_current(data, dc_rate=0., s1_slope=0.):
    r"""
    Correct for the dark current, which is the average number of
    spurious counts per minute of measurement on each detector channel.

    Note: could instead use this module to estimate the dark current and
    output a background signal which can then be plotted or fed into a
    background subtraction tool.  Or maybe just produce a dark current
    plottable as an extra output.

    **Inputs**

    data (candordata) : data to scale

    dc_rate {Dark counts per minute} (float)
    : Number of dark counts to subtract from each detector channel per
    minute of counting time.

    s1_slope {DC vs. slit 1 in counts/(minute . mm)} (float)
    : Dark current may increase with slit 1 opening as "dc_rate + s1_slope*S1"

    **Returns**

    output (candordata): Dark current subtracted data.

    | 2020-03-04 Paul Kienzle
    | 2020-03-12 Paul Kienzle Add slit 1 dependence for DC rate
    """
    # TODO: no uncertainty propagation
    # TODO: generalize to detector shapes beyond candor
    # TODO: datatype hierarchy: accepts any kind of refldata
    if dc_rate != 0. or s1_slope != 0.:
        rate = dc_rate + s1_slope*data.slit1.x
        dc = data.monitor.count_time*(rate/60.)
        data = copy(data)
        data.detector = copy(data.detector)
        data.detector.counts = data.detector.counts - dc[:, None, None]
    return data

@module("candor")
def stitch_intensity(data, tol=0.001):
    r"""
    Join the intensity measurements into a single entry.

    **Inputs**

    data (candordata[]) : data to join

    tol {Tolerance (mm)} (float)
    : Tolerance for "overlapping" slit opening on slits 1, 2, and 3

    **Returns**

    output (candordata[]) : joined data

    | 2020-03-04 Paul Kienzle
    """
    from math import isclose
    from .refldata import Intent
    from .steps import join

    # sort the segments and make sure there is one and only one overlap
    data = [copy(v) for v in data]
    data.sort(key=lambda d: (d.slit1.x[0], d.slit2.x[0]))
    #print([(d.slit1.x[0],d.slit1.x[-1]) for d in data])
    for a, b in zip(data[:-1], data[1:]):
        # Verify overlap
        if (not isclose(a.slit1.x[-1], b.slit1.x[0], abs_tol=tol)
            or not isclose(a.slit2.x[-1], b.slit2.x[0], abs_tol=tol)
            or not isclose(a.slit3.x[-1], b.slit3.x[0], abs_tol=tol)):
            raise ValueError("need one point of overlap between segments")
        # Scale the *next* segment to the current segment rather than scaling
        # the current segment.  This does two things: (1) the first segment
        # doesn't need to be scaled since it has the narrowest slits, hence
        # the smallest attenuators are needed, and (2) the attenuation
        # computed at the next cycle automatically includes the cumulative
        # attenuation up to the current cycle.
        # TODO: propagate uncertainties
        # TODO: maybe update counts (unnormalized) rather than v (normalized)
        atten = a.v[-1] / b.v[0]
        b.v *= atten[None, ...]

        # Better scale estimation:
        # * user provides an overlap fitting radius
        # * order segments
        # * for each pair of segments
        # ** find midpoint between end of first segment and beginning of next segment
        # ** this midpoint may lie between the two segments (no overlap),
        #    exactly at the endpoints (single overlap) or somewhere
        #    before the end of the first and the beginning of the next
        # ** find all points within that overlap region
        #       low=[(s1_low, rate_low), ...], high=[(s1_high, rate_high), ...]
        #    where s1 is the slit 1 opening and rate is the normalized count rate.
        # ** define f(c) as chisq from fit a quadratic to the points
        #       [(s1_low, rate_low), ... , (s1_high, c*rate_high), ...]
        # ** minimize f(a, c, k) = a s1^2 + c - k y
        # This can be solved using a linear system:
        #      [a c k] = I
        # where
        #      a = [s1_low^2 s1_high^2]/sigma
        #      c = [1 ... 1  1 ... 1]/sigma
        #      k = [0 ... 0  y_high]/sigma
        #      I  = [y_low    0 ... 0]/sigma
        # With 1 point overlap and identical s1 can estimate k
        # With 2 point overlap can estimate a line bx + c
        # With 3 point overlap can estimate the quadratic as above
        # A quick simulation with 4 points overlap, a=5000, k=10
        # s1_low=[1,2,3,4], s1_high=[3,4,5,6] gave k to 0.5%
        # Note that the quadratic is centered at zero.  Without this condition
        # the quadratic can have a minimum over the range which is non-physical.
        # In practice the data is probably linear-quadratic-linear over the
        # range of the entire slit scan, but each overlap should be small
        # enough that it is either linear or quadratic.  With the right value
        # for "c" the curve can be made as flat as necessary over the range.
        # The attenuation "k" is not same across the detector bank since the
        # absorption coefficient is wavelength dependent and attenuation
        # is exponential with thickness of the attenuator.
        # However... we are going to have fixed attenuators on motor controls,
        # so its better to calibrate them once with high statistics and store
        # the attenuation values in the NeXus file.

    # Force intent to treat this as a slit scan.
    data[0].intent = Intent.slit

    # Use existing join algorithm.
    # TODO: expose join parameters to the user?
    data = join(data)
    return data


@module("candor")
def candor_rebin(data, qmin=None, qmax=None, qstep=0.003, qstep_max=None):
    r"""
    Join the intensity measurements into a single entry.

    **Inputs**

    data (candordata) : data to join

    qmin (float) : Start of q range, or empty to infer from data

    qmax (float) : End of q range, or empty to infer from data

    qstep (float) : q step size at qmin, or 0 for no rebinning

    qstep_max (float) : maximum q step size at qmax, or empty to use qstep over entire q range

    **Returns**

    output (refldata) : joined data

    | 2020-03-04 Paul Kienzle
    | 2020-08-03 David Hoogerheide adding progressive q step coarsening
    """
    from .candor import rebin, nobin

    if qstep == 0.0:
        data = nobin(data)
    else:
        if qmin is None:
            qmin = data.Qz.min()
        if qmax is None:
            qmax = data.Qz.max()
        if qstep_max is None:
            q = np.arange(qmin, qmax, qstep)
        else:
            dq = np.linspace(qstep,qstep_max, int(np.ceil(2*(qmax-qmin)/(qstep_max+qstep))))
            q = (qmin-qstep) + np.cumsum(dq) 
        data = rebin(data, q)

    return data

candor_join = copy_module(
    steps.join, "candor_join",
    "refldata", "candordata", tag="candor")

candor_rescale = copy_module(
    steps.rescale, "candor_rescale",
    "refldata", "candordata", tag="candor")

candor_normalize = copy_module(
    steps.normalize, "candor_normalize",
    "refldata", "candordata", tag="candor")

candor_background = copy_module(
    steps.subtract_background, "candor_background",
    "refldata", "candordata", tag="candor")

candor_divide = copy_module(
    steps.divide_intensity, "candor_divide",
    "refldata", "candordata", tag="candor")

candor_divergence_fb = copy_module(
    steps.divergence_fb, "candor_divergence",
    "refldata", "candordata", tag="candor")

candor_sample_broadening = copy_module(
    steps.sample_broadening, "candor_sample_broadening",
    "refldata", "candordata", tag="candor")
