# This program is public domain
import os
import numpy as np
from copy import copy

from reductus.dataflow.automod import cache, nocache, module

# TODO: maybe bring back formula to show the math of each step
# TODO: what about polarized data?

@module
def nop(data):
    """
    No operation.

    **Inputs**

    data (refldata[]): Input data

    **Returns**

    output (refldata[]): Unaltered data

    2015-12-31 Paul Kienzle
    """
    return data

@module
def ncnr_load(filelist=None, check_timestamps=True):
    """
    Load a list of nexus files from the NCNR data server.

    **Inputs**

    filelist (fileinfo[]): List of files to open.

    check_timestamps (bool): verify that timestamps on file match request

    **Returns**

    output (refldata[]): All entries of all files in the list.

    2016-06-29 Brian Maranville
    | 2017-08-21 Brian Maranville Change to refldata, force cache invalidate
    | 2018-06-18 Brian Maranville Change to nexusref to ignore areaDetector
    | 2018-12-10 Brian Maranville get_plottable routines moved to python data container from js
    | 2020-03-03 Paul Kienzle Just load.  Don't even compute divergence
    """
    # NB: used mainly to set metadata for processing, so keep it minimal
    # TODO: make a metadata loader that does not send all data to browser
    # NB: Fileinfo is a structure with
    #     { path: "location/on/server", mtime: timestamp }
    from .load import url_load_list

    datasets = []
    for data in url_load_list(filelist, check_timestamps=check_timestamps):
        datasets.append(data)
    return datasets

@module
def dark_current(data, poly_coeff=[0], poly_cov=None):
    r"""
    Correct for the dark current, which is the average number of
    spurious counts per minute of measurement on each detector channel.

    **Inputs**

    data (refldata[]) : data to scale

    poly_coeff {Polynomial coefficients of dark current vs slit1} (float[])
    : Polynomial coefficients (highest order to lowest) representing the dark current as a function of slit 1 opening. Units in counts/(minute . mm ^ N), for the coefficient of (slit1 ^ N). Default is [0].

    poly_cov {Polynomial covariance matrix} (float[])
    : Flattened covariance matrix for polynomial coefficients if error propagation is desired. For an order N polynomial, must have size N^2. If left blank, no error propagation will occur.

    **Returns**

    output (refldata[]): Dark current subtracted data.

    darkcurrent (refldata[]): Dark current that was subtracted (for plotting)

    | 2020-03-04 Paul Kienzle
    | 2020-03-12 Paul Kienzle Add slit 1 dependence for DC rate
    | 2021-06-11 David Hoogerheide generalize to refldata, prevent either adding counts or oversubtracting
    | 2021-06-13 David Hoogerheide add dark current output
    | 2021-06-14 David Hoogerheide change to polynomial input and add error propagation
    """

    # TODO: datatype hierarchy: accepts any kind of refldata

    from reductus.dataflow.lib.uncertainty import Uncertainty as U

    datasets = list()
    dcs = list()

    order = len(poly_coeff)

    for d in data:
        dcdata = copy(d)                    # hackish way to get dark current counts
        dcdata.detector = copy(d.detector)

        # calculate rate and Jacobian at each point
        rate = np.polyval(poly_coeff, dcdata.slit1.x)

        # error propagation
        rate_var = np.zeros_like(rate)
        if poly_cov is not None:
            poly_cov = np.array(poly_cov).reshape((order, order))
            for i, s1 in enumerate(dcdata.slit1.x):
                J = np.array([s1**float(i) for i in range(0, order)[::-1]])
                rate_var[i] = np.dot(J.T, np.dot(poly_cov, J))
        dc = dcdata.monitor.count_time*(rate/60.)
        dc[dc < 0] = 0.0                            # do not allow addition of dark counts from negative rates
        dc_var = rate_var * (dcdata.monitor.count_time/60.)**2

        # condition dark counts to the correct dimensionality
        ndetectordims = np.ndim(d.detector.counts)
        dc = np.expand_dims(dc, tuple(range(1, ndetectordims)))
        dc_var = np.expand_dims(dc_var, tuple(range(1, ndetectordims)))
        dcdata.detector.counts = np.ones_like(dcdata.detector.counts) * dc  # should preserve dimensionality correctly
        dcdata.detector.counts_variance = np.ones_like(dcdata.detector.counts_variance) * dc_var  # should preserve dimensionality correctly

        detcounts = U(d.detector.counts, d.detector.counts_variance)
        darkcounts = U(dcdata.detector.counts, dcdata.detector.counts_variance)

        detdarkdiff = detcounts - darkcounts

        d.detector.counts, d.detector.counts_variance = detdarkdiff.x, detdarkdiff.variance
        d.detector.counts[d.detector.counts < 0] = 0.0
        
        # only renormalize if apply_norm has already populated d.normbase, i.e. if it's a standalone module
        if d.normbase is not None:
            d = normalize(d, d.normbase)
            dcdata = normalize(dcdata, dcdata.normbase)

        # create outputs
        datasets.append(d)
        dcs.append(dcdata)

    return datasets, dcs

@module
def fit_dead_time(data, source='detector', mode='auto'):
    """
    Fit detector dead time constants (paralyzing and non-paralyzing) from
    measurement of attenuated and unattenuated data for a range of count rates.

    **Inputs**

    data (refldata[]): Data sets with different attenuation levels

    source (opt:detector|monitor): Tube that is being measured

    mode (opt:P|NP|mixed|auto): Dead-time mode

    **Returns**

    dead_time (deadtime): Dead time constants, attenuator estimate and beam rate

    2015-12-17 Paul Kienzle
    """
    from .deadtime import fit_dead_time

    dead_time = fit_dead_time(data, source=source, mode=mode)
    return dead_time



@module
def monitor_dead_time(data, dead_time, nonparalyzing=0.0, paralyzing=0.0):
    """
    Correct the monitor dead time from the fitted dead time.

    The deadtime constants are chosen as follows:

    #. If either *tau_NP* and *tau_P* are non-zero, then use them.
    #. If the dead time terminal is attached to a dead time fit, use it.
    #. If the dead time constants are given in the data file, then use them.
    #. Otherwise don't do any dead time correction.

    **Inputs**

    data (refldata) : Uncorrected data

    dead_time (deadtime?) : Output of dead time estimator

    nonparalyzing (float:us<0,inf>) : non-paralyzing dead time constant

    paralyzing (float:us<0,inf>) : paralyzing dead time constant

    **Returns**

    output (refldata): Dead-time corrected data

    2015-12-17 Paul Kienzle
    """
    from .deadtime import apply_monitor_dead_time

    data = copy(data)
    data.monitor = copy(data.monitor)
    if nonparalyzing != 0.0 or paralyzing != 0.0:
        apply_monitor_dead_time(data, tau_NP=nonparalyzing,
                                tau_P=paralyzing)
    elif dead_time is not None:
        apply_monitor_dead_time(data, tau_NP=dead_time.tau_NP,
                                tau_P=dead_time.tau_P)
    elif data.monitor.deadtime is not None and np.isfinite(data.monitor.deadtime).all():
        try:
            tau_NP, tau_P = data.monitor.deadtime
        except Exception:
            tau_NP, tau_P = data.monitor.deadtime, 0.0
        apply_monitor_dead_time(data, tau_NP=tau_NP, tau_P=tau_P)
    else:
        pass  # no deadtime correction parameters available.

    return data


@module
def detector_dead_time(data, dead_time, nonparalyzing=0.0, paralyzing=0.0):
    """
    Correct the detector dead time from the fitted dead time.

    If *tau_NP* and *tau_P* are non-zero, then use them.  If a dead_time
    fit result is supplied, then use it.  If the dead time constants are
    given in the data file, then use them.  Otherwise don't do any
    dead time correction.

    **Inputs**

    data (refldata) : Uncorrected data

    dead_time (deadtime?) : Output from dead time estimator

    nonparalyzing (float:us<0,inf>) : non-paralyzing dead time constant

    paralyzing (float:us<0,inf>) : paralyzing dead time constant

    **Returns**

    output (refldata): Dead-time corrected data

    2016-03-21 Paul Kienzle
    """
    from .deadtime import apply_detector_dead_time

    data = copy(data)
    if nonparalyzing != 0.0 or paralyzing != 0.0:
        data.detector = copy(data.detector)
        apply_detector_dead_time(data, tau_NP=nonparalyzing,
                                 tau_P=paralyzing)
    elif dead_time is not None:
        data.detector = copy(data.detector)
        apply_detector_dead_time(data, tau_NP=dead_time.tau_NP,
                                 tau_P=dead_time.tau_P)
    elif data.detector.deadtime is not None and not np.all(np.isnan(data.detector.deadtime)):
        try:
            tau_NP, tau_P = data.detector.deadtime
        except Exception:
            tau_NP, tau_P = data.detector.deadtime, 0.0
        data.detector = copy(data.detector)
        apply_detector_dead_time(data, tau_NP=tau_NP, tau_P=tau_P)
    else:
        raise ValueError("no valid deadtime provided in file or parameter")

    return data


@module
def monitor_saturation(data):
    """
    Correct the monitor dead time from stored saturation curve.

    **Inputs**

    data (refldata): Uncorrected data

    **Returns**

    output (refldata): Dead-time corrected data

    2017-02-22 Paul Kienzle
    """
    from .deadtime import apply_monitor_saturation
    data = copy(data)
    if getattr(data.monitor, 'saturation', None) is not None:
        data.monitor = copy(data.monitor)
        apply_monitor_saturation(data)
    else:
        data.warn("no monitor saturation for %r"%data.name)
    return data


@module
def detector_saturation(data):
    """
    Correct the detector dead time from stored saturation curve.

    **Inputs**

    data (refldata): Uncorrected data

    **Returns**

    output (refldata): Dead-time corrected data

    2015-12-17 Paul Kienzle
    """
    from .deadtime import apply_detector_saturation
    data = copy(data)
    if getattr(data.detector, 'saturation', None) is not None:
        #print("detector "+str(data.detector.__dict__))
        data.detector = copy(data.detector)
        apply_detector_saturation(data)
    else:
        data.warn("no detector saturation for %r"%data.name)
    return data


@module
def theta_offset(data, offset=0.0):
    """
    Correct the theta offset of the data for a misaligned sample, shifting
    sample and detector angle and updating $q_x$ and $q_z$.

    **Inputs**

    data (refldata) : Uncorrected data

    offset (float:degree) : amount of shift to add to sample angle and subtract
    from detector angle

    **Returns**

    output (refldata): Offset corrected data

    2015-12-17 Paul Kienzle
    """
    from .angles import apply_theta_offset
    data = copy(data)
    data.sample = copy(data.sample)
    data.detector = copy(data.detector)
    data.sample.angle_x = copy(data.sample.angle_x)
    data.detector.angle_x = copy(data.detector.angle_x)
    apply_theta_offset(data, offset)
    return data


@module
def back_reflection(data):
    """
    Reverse the sense of the reflection angles, making positive angles
    negative and vice versa.

    **Inputs**

    data (refldata): Uncorrected data

    **Returns**

    output (refldata): Angle corrected data

    2015-12-17 Paul Kienzle
    """
    from .angles import apply_back_reflection
    data = copy(data)
    data.sample = copy(data.sample)
    data.detector = copy(data.detector)
    data.sample.angle_x = copy(data.sample.angle_x)
    data.detector.angle_x = copy(data.detector.angle_x)
    apply_back_reflection(data)
    return data


@module
def absolute_angle(data):
    """
    Assume all reflection is off the top surface, reversing the sense
    of negative angles.

    **Inputs**

    data (refldata): Uncorrected data

    **Returns**

    output (refldata): Angle corrected data

    2015-12-17 Paul Kienzle
    """
    from .angles import apply_absolute_angle
    data = copy(data)
    data.sample = copy(data.sample)
    data.detector = copy(data.detector)
    data.sample.angle_x = copy(data.sample.angle_x)
    data.detector.angle_x = copy(data.detector.angle_x)
    apply_absolute_angle(data)
    return data

@module
def sample_broadening(data, width=0):
    r"""
    Increase (or decrease) nominal divergence due to the effects of sample
    broadening (or focussing) if this is not supported by the reflectivity
    analysis program.

    **Inputs**

    data (refldata): data without resolution estimate

    width (float) : amount of increased divergence in degrees, using
    1-\ $\sigma$ change in width.  This can be estimated from the FWHM of the
    rocking curve relative to the expected value with no broadening, divided
    by 2.35 to convert FWHM to 1-\ $\sigma$.

    **Returns**

    output (refldata): data with resolution estimate

    2020-05-05 Paul Kienzle
    """
    from .angles import apply_sample_broadening
    if width != 0:
        data = copy(data)
        apply_sample_broadening(data, width)
    return data

@module
def divergence_fb(data, sample_width=None):
    r"""
    Estimate divergence from slit openings.  Does nothing if divergence
    is already defined by the instrument.

    **Inputs**

    data (refldata): data without resolution estimate

    sample_width (float?:<0,inf>) : width of the sample in mm if it acts like a slit.
    By default, this uses the value in the file.

    **Returns**

    output (refldata): data with resolution estimate

    2020-05-05 Paul Kienzle
    """
    from .angles import apply_divergence_front_back
    if data.angular_resolution is None:
        data = copy(data)
        apply_divergence_front_back(data, sample_width)
    return data

@module
def divergence(data, sample_width=None, sample_broadening=0):
    r"""
    Estimate divergence from slit openings.  Does nothing if divergence
    is already defined by the instrument.

    **DEPRECATED** use divergence_fb instead

    **Inputs**

    data (refldata): data without resolution estimate

    sample_width (float?:<0,inf>) : width of the sample in mm if it acts like a slit.
    By default, this uses the value in the file.

    sample_broadening (float) : amount of increased divergence in degrees, using
    1-\ $\sigma$ change in width.  This can be estimated from the FWHM of the
    rocking curve relative to the expected value with no broadening, divided
    by 2.35 to convert FWHM to 1-\ $\sigma$.

    **Returns**

    output (refldata): data with resolution estimate

    2016-06-15 Paul Kienzle
    2020-05-05 Paul Kienzle
    """
    from .angles import apply_divergence_simple, apply_sample_broadening
    if data.angular_resolution is None:
        data = copy(data)
        apply_divergence_simple(data, sample_width)
        apply_sample_broadening(data, sample_broadening)
    return data


#@module
def mask_specular(data):
    """
    Identify and mask out specular points.

    This defines the *mask* attribute of *data* as including all points that
    are not specular or not previously masked.  The points are not actually
    removed from the data, since this operation is done by *join*.

    **Inputs**

    data (refldata) : background data which may contain specular point

    **Returns**

    output (refldata) : masked data

    2015-12-17 Paul Kienzle
    """
    from .background import apply_specular_mask
    data = copy(data)
    apply_specular_mask(data)
    return data

def mask_action(data=None, mask_indices=None, **kwargs):
    """
    Remove data at the indicated indices
    """
    if mask_indices:
        data = copy(data)
        data.apply_mask(mask_indices)
    return data

@module
def mask_points(data, mask_indices=None):
    """
    Identify and mask out user-specified points.

    This defines the *mask* attribute of *data* to include all data
    except those indicated in *mask_indices*.  Any previous mask is cleared.
    The masked data are not actually removed from the data, since this
    operation is done by *join*.

    **Inputs**

    data (refldata) : background data which may contain specular point

    mask_indices (index[]*) : 0-origin data point indices to mask. For example,
    *mask_indices=[1,4,6]* masks the 2nd, 5th and 7th point respectively. Each
    dataset should have its own mask.

    **Returns**

    output (refldata) : masked data

    | 2018-04-30 Brian Maranville
    | 2019-07-02 Brian Maranville: change self.points after mask
    """
    data = copy(data)
    output = mask_action(data=data, mask_indices=mask_indices)
    return output

@module
def mark_intent(data, intent='auto'):
    r"""
    Mark the file type based on the contents of the file, or override.

    *intent* can be 'infer', to guess the intent from the measurement geometry,
    'auto' to use the recorded value for the intent if present, otherwise
    infer it from the geometry, or the name of the intent.

    For inferred intent, it is 'specular' if incident angle matches detector
    angle within 0.1*angular divergence, 'background+' if incident angle is
    greater than detector angle, 'background-' if incident angle is less
    than detector angle, 'slit' if incident and detector angles are zero,
    'rock sample' if only the incident angle changes, 'rock detector' if
    only the detector angle changes, or 'rock qx' if only $Q_x$ is changing
    throughout the scan.

    **Inputs**

    data (refldata) : data file which may or may not have intent marked

    intent (opt:auto|infer|specular|background+\|background-\|slit
    \|rock sample|rock detector|rock qx) : intent to register with the
    datafile, or auto/infer to guess

    **Returns**

    output (refldata) : marked data

    2016-03-20 Paul Kienzle
    """
    from .intent import apply_intent
    data = copy(data)
    apply_intent(data, intent)
    return data

@module
def group_by_intent(data):
    """
    Split a bundle into multiple bundles using intent.

    **Inputs**

    data (refldata[]) : data files with intent marked

    **Returns**

    specular (refldata[]) : specular measurements

    backp {Background+} (refldata[]) : positive offset background measurements

    backm {Background-} (refldata[]) : negative offset background measurements

    intensity (refldata[]) : beam intensity measurements

    rock {Rocking curve} (refldata[]) : rocking curve measurements

    other (refldata[]) : everything else

    2016-07-20 Brian Maranville
    """
    map_intent = {
        'specular': 'specular',
        'intensity': 'intensity',
        'background+': 'backp',
        'background-': 'backm',
        'rock sample': 'rock',
        'rock detector': 'rock',
        'rock qx': 'rock',
        }
    groups = {}
    for intent in set(map_intent.values()):
        groups[intent] = []
    groups['other'] = []
    for d in data:
        #print("intent %s %s"%(d.intent, d.path))
        groups[map_intent.get(d.intent, 'other')].append(d)

    return [groups[intent]
            for intent in 'specular backp backm intensity rock other'.split()]

@module
def extract_xs(data, xs="++"):
    r"""
    Get a polarization cross-section from a bundle

    **Inputs**

    data (refldata[]): data files in of all cross sections

    xs {Cross-section} (opt:++\|--\|+-\|-+\|+\|-\|unpolarized): cross-section to extract

    **Returns**

    output (refldata[]): data matching just that cross-section

    | 2016-05-05 Brian Maranville
    | 2020-03-24 Brian Maranville: added half-pol cross-sections
    """
    # Note: no need to copy data since it is not being modified
    if xs == 'unpolarized':
        xs = ''
    output = [d for d in data if d.polarization == xs]
    return output

@module
def filter(data, key="", comparator="eq", value=None):
    r"""
    Get a subset of the datasets bundle based on the test

    **Inputs**

    data (refldata[]): data files in

    key (str): name to test in the dataset

    value (str?): value to compare

    comparator {Compare operator} (opt:eq|ne|lt|le|gt|ge): comparison operator

    **Returns**

    output (refldata[]): data matching the comparison

    2017-02-24 Brian Maranville
    """

    import operator
    compare_lookup = {
        "==": operator.eq,
        "!=": operator.ne,
        "<": operator.lt,
        "<=": operator.le,
        ">=": operator.ge,
        ">": operator.gt,
        "eq": operator.eq,
        "ne": operator.ne,
        "lt": operator.lt,
        "le": operator.le,
        "ge": operator.ge,
        "gt": operator.gt,

    }
    compare_op = compare_lookup[comparator]

    return [d for d in data if hasattr(d, key) and compare_op(getattr(d, key), value)]

@module
def normalize(data, base='auto'):
    """
    Estimate the detector count rate.

    *base* can be monitor, time, roi, power, or none for no normalization.
    For example, if base='monitor' then the count rate will be counts
    per monitor count.  Note that operations that combine datasets require
    the same normalization on the points.

    If *base* is auto then the default will be chosen, which is 'monitor'
    if the monitor exists, otherwise it is 'time'.  If neither exists
    (not sure that can happen) then the data will be unnormalized.

    The detector region of interest (*roi*) and reactor *power* have not been
    tested and should not be used. The detector efficient, the dead time
    corrections and attenuator scaling have not been applied to the roi
    measurement.  Since the measurement is only useful if a portion of the
    detector is exposed to the incident beam, this corrections will be
    especially important.  In the case where the monitor is unreliable and
    reactor power has been fluctuating, you may be able to estimate the
    incident intensity based on the integrated reactor power. This uses
    a simple average of the reactor power measurements multiplied by the
    measurement time.

    **Inputs**

    data (refldata) : data to normalize

    base {Normalize by} (opt:auto|monitor|time|roi|power|none)
    : how to convert from counts to count rates

    **Returns**

    output (refldata) : data with count rate rather than counts

    2015-12-17 Paul Kienzle
    2020-03-10 Paul Kienzle auto almost always equals monitor
    """
    # Note: reflpak supported visualization like "counts per 10000 monitor"
    # so that the displayed data looked roughly like the measured data, except
    # all scaled to a common monitor.  This is not available in reductus.

    # TODO: consistent use of data.detector.counts vs. data.v
    # see in particular the detector/monitor dead time, spectral efficiency,
    # dark current, etc.

    from .scale import apply_norm
    data = copy(data)
    apply_norm(data, base)
    return data


@module
def psd_center(data, center=128):
    """
    Set center pixel for the detector.

    **Inputs**

    data (psddata) : data to scale

    center (float) : beam center pixel (should be the same for all datasets)

    **Returns**

    output (psddata) : scaled data

    2020-02-04 Paul Kienzle
    """
    data = copy(data)
    data.detector = copy(data.detector)
    data.detector.center = (center, 0)
    return data

@module
def psd_integrate(
        data, spec_scale=1, spec_pixel=5.,
        left_scale=1., left_pixel=5., right_scale=1., right_pixel=5.,
        min_pixel=5., max_pixel=251., degree=1., mc_samples=1000,
        slices=None, #(0.01, 0.05, 0.10, 0.15),
        ):
    r"""
    Integrate specular and background from psd.

    Specular and background regions are computed from beam divergence and
    pixel width using the following:

        spec = spec scale * divergence + spec pixels
        left = left scale * divergence + left pixels
        right = right scale * divergence + right pixels

    The beam divergence used in the equations above is estimated from
    the slit openings. The specular signal is the sum over pixels
    in [-spec, +spec]. The background signal is determined by fitting
    a polynomial of degree n to the pixels in [-spec - left, -spec)
    and (spec, spec + right), then integrating that polynomial over
    the specular pixels.

    Specular uncertainty comes from simply integrating over the pixels.
    Background uncertainty comes from the uncertainty in the polynomial
    fitting parameters.  It can be estimated using Monte Carlo sampling,
    or by simple Gaussian propagation of uncertainty if mc samples is 0.
    MC estimates are stochastic, so rerunning with a different random
    number sequence will give a different result.  To make the reduction
    reproducible, the number of samples is used as the seed value for the
    random number generator.  To assess the variation in the background
    estimate, try slightly longer sequence lengths.  We have found 100
    samples gives a background estimate that is approximately stable
    (variation in estimate is well within uncertainty). A default value
    of 1000 was chosen because it is reasonably fast and reasonably stable.
    Test on your own data by comparing mc_samples to mc_samples+1

    The residual after subtracting the background estimate is also
    returned. Use this to verify that the integration ranges are
    chosen appropriately.  There is an additional output to show slices
    for selected frames---this will show the quality of background estimate.

    **Inputs**

    data (refldata) : data to integrate

    spec_scale {Spec scale}(float:<0,inf>) : Specular width as a divergence multiple, or zero for fixed width.

    spec_pixel {Spec offset}(float:pixel) : Fixed broadening in pixels (or narrowing if negative)

    left_scale {Back- scale}(float:<0,inf>) : Left background width as a divergence multiple, or zero for fixed width.

    left_pixel {Back- offset}(float:pixel) : Left background shift in pixels.

    right_scale {Back+ scale}(float:<0,inf>) : Right background width as a divergence multiple, or zero for fixed width.

    right_pixel {Back+ offset}(float:pixel) : Right background shift in pixels.

    min_pixel {Left edge}(float:pixel<1,256>) : Left background cutoff pixel.

    max_pixel {Right edge}(float:pixel<1,256>) : Right background cutoff pixel.

    degree {Polynomial degree}(int:<0,9>) : Background polynomial degree.

    mc_samples {MC samples}(int:<0,inf>) : Number of MC samples for uncertainty analysis, or zero for simple gaussian.

    slices {Slice value}(float) : Display data cross-sections at the given values.

    **Returns**

    specular (refldata) : integrated specular

    background (refldata) : integrated background

    residual (psddata) : background subtracted psd data

    sliceplot (plot) : slices plot

    | 2020-02-03 Paul Kienzle
    """
    from .ng7psd import apply_integration
    from reductus.dataflow.data import Plottable

    mc_seed = mc_samples if mc_samples > 0 else None
    #print("slices", slices)
    spec, back, resid, sliceplot = apply_integration(
        data, spec=(spec_scale, spec_pixel),
        left=(left_scale, left_pixel), right=(right_scale, right_pixel),
        pixel_range=(min_pixel, max_pixel),
        degree=degree, mc_samples=mc_samples, seed=mc_seed,
        slices=[slices] if slices is not None else [],
    )

    return spec, back, resid, Plottable(sliceplot)

@module
def rescale(data, scale=1.0, dscale=0.0):
    """
    Rescale the count rate by some scale and uncertainty.

    **Inputs**

    data (refldata) : data to scale

    scale (scale*) : amount to scale, one for each dataset

    dscale {Scale err} (float*:<0,inf>) : scale uncertainty for gaussian error propagation

    **Returns**

    output (refldata) : scaled data

    2015-12-17 Paul Kienzle
    """
    from .scale import apply_rescale
    data = copy(data)
    apply_rescale(data, scale, dscale)
    return data

#@nocache
@module
def join(data, Q_tolerance=0.5, dQ_tolerance=0.002, order='file',
         group_by="polarization", tolerance=None):
    r"""
    Join operates on a list of datasets, returning a list with one dataset,
    or one dataset per polarization state.  When operating on a single
    dataset, it joins repeated points into single points.

    *Qtol* and *dQtol* are scale factors on $\Delta \theta$ used to
    determine whether two angles are equivalent.  For a given tolerance
    $\epsilon_Q, \epsilon_{\Delta Q}$, a point at incident angle
    $\theta_1$ can be joined with one with incident angle $\theta_2$ when
    $|\theta_1 - \theta_2| < \epsilon_Q \cdot \Delta\theta$ and
    $|\Delta\theta_1 - \Delta\theta_2| < \epsilon_{\Delta Q} \cdot \Delta\theta$.
    Values of $\epsilon_Q=0.5$ and $\epsilon_{\Delta Q}=0.002$ work well in
    practice. If the tolerances are both 0 then join is performed against
    the desired positions rather than the actual positions; this more
    closely corresponds with user intent.

    The join algorithm is greedy, so if you have a sequence of points with
    individual separation less than $\epsilon\cdot\Delta\theta$ but total
    spread greater than $\epsilon\cdot\Delta\theta$, they will be joined
    into multiple points with the final with the final point having worse
    statistics than the prior points.  Join operates on one dimension at
    a time, first grouping points with common $\Delta\theta$, then joining
    points within each $\Delta\theta$ by common $\theta_\text{incident}$,
    then by common $\theta_\text{detector}$.  This algorithm should work
    well enough on the common reflectometry scans, but it may fail for example
    if applied to a set of $Q_x$ scans with different $Q_z$ values.

    *order* is the sort order of the files that are joined.  The first
    file in the sorted list determines the metadata such as the base
    file name for the joined file.

    The joined datasets will be sorted as appropriate for the the
    measurement intent.  Masked points will be removed.

    Data must be normalized before join.

    **Inputs**

    data (refldata[]) : data to join

    Q_tolerance (float:1-sigma<0,inf>) : allowed separation between points
    while still joining them to a single point; this is relative to the angular
    resolution and wavelength dispersion of each point

    dQ_tolerance (float:1-sigma<0,inf>) : allowed difference in resolution
    between combined points; this is relative to the angular resolution and
    wavelength dispersion of each point

    order (opt:file|time|theta|slit|none) : order determines which file is the
    base file, supplying the metadata for the joined set

    group_by (opt:polarization|probe|entry|filenumber|instrument|intent|sample.name|sample.description) : key by which the files are grouped prior to join

    tolerance(float?:1-sigma<0,inf>) : **deprecated** value for Qtol and dQtol;
    ignored if the value is None or not specified.

    **Returns**

    output (refldata[]) : joined data

    | 2017-02-09 Paul Kienzle: split tolerance into Qtol and dQtol
    | 2017-05-05 Paul Kienzle: consistent sort order for outputs
    | 2017-07-03 Brian Maranville: rearrange to group by Ti, Td before dT, dQ
    | 2018-05-14 Brian Maranville: group by Qx first for all rocking curves
    | 2020-10-14 Paul Kienzle fixed uncertainty for time normalized data
    | 2020-12-15 Brian Maranville added roi_counts and source_power to columns
    """
    from .joindata import sort_files, join_datasets
    from .util import group_by_key
    # No copy necessary; join is never in-place.

    # TODO: parse **deprecated** in automod and hide deprecated inputs on ui
    if tolerance is not None:
        Q_tolerance = dQ_tolerance = tolerance
    datasets = [v for k, v in sorted(group_by_key(group_by, data).items())]
    output = []
    for group in datasets:
        group = sort_files(group, order)
        result = join_datasets(group, Q_tolerance, dQ_tolerance)
        output.append(result)
    return output

@module
def mix_cross_sections(data, mix_sf=False, mix_nsf=False):
    """
    Mix (combine) cross-sections, usually to improve statistics when cross-sections
    are expected to be indistinguishable in the model (e.g. spin-flip when no chirality)
    Typically this is done after load and before "join"

    All inputs are passed to the output, and in addition:

    When *mix_sf* is enabled, all input datasets with polarization "-+" will be copied and
    added to the output with polarization = "+-", and vice-versa for "+-" inputs.

    When *mix_nsf* is enabled, all input datasets with polarization "++" will be copied and
    added to the output with polarization = "--", and similarly "--" inputs sent to "++"

    **Inputs**

    data (refldata[]) : datasets in

    mix_sf {Mix Spin-Flip?} (bool) : Perform mixing on spin-flip cross-sections,
    i.e. "+-" and "-+"

    mix_nsf {Mix Non-Spin-Flip?} (bool) : Perform mixing on spin-flip cross-sections,
    i.e. "++" and "--" or "+" and "-"

    **Returns**

    output (refldata[]) : relabeled and copied datasets (around twice as many as in the input)

    2021-11-17 Brian Maranville
    """
    output = copy(data)
    mappings = {
        "sf": {
            "+-": "-+",
            "-+": "+-"
        },
        "nsf": {
            "++": "--",
            "--": "++",
            "+": "-",
            "-": "+"
        }
    }
    def duplicate_and_remap_items(xs_type):
        mapping = mappings[xs_type]
        items = [d for d in data if d.polarization in mapping]
        for item in items:
            new_item = copy(item)
            new_item.polarization = mapping[item.polarization]
            output.append(new_item)

    if mix_sf:
        duplicate_and_remap_items("sf")

    if mix_nsf:
        duplicate_and_remap_items("nsf")

    return output

#@module
def align_background(data, align='auto'):
    """
    Determine the Qz value associated with the background measurement.

    The *align* flag determines which background points are matched
    to the sample points.  It can be 'sample' if background is
    measured using an offset from the sample angle, or 'detector'
    if it is offset from detector angle.   If *align* is 'auto', then
    use 'Qz_target' to align the background scan.

    For 'auto' alignment without Qz_target set, we can only distinguish
    relative and constant offsets, and cannot determine which of sample
    and detector is offset from the specular condition, so we must rely
    on convention. If the offset is constant for each angle, then it is
    assumed to be a sample offset. If the the offset is proportional to
    the angle (and therefore offset divided by angle is constant), then
    it is assumed to be a detector offset. If neither condition is met,
    it is assumed to be a sample offset.

    The 'auto' test is robust: 90% of the points should be within 5% of the
    median value of the vector for the offset to be considered a constant.

    **Inputs**

    data (refldata) : background data with unknown $q$

    align (opt:auto|sample|detector) : angle which determines $q_z$

    **Returns**

    output (refldata) : background with known $q$

    2015-12-17 Paul Kienzle
    2020-10-16 Paul Kienzle rename 'offset' to 'align'
    """
    from .background import set_background_alignment
    data = copy(data)
    set_background_alignment(data, align)
    return data


@module
def subtract_background(data, backp, backm, align="none"):
    """
    Subtract the background datasets from the specular dataset.

    The specular, background+ and background- signals should already be
    joined into single datasets. For each, the background is interpolated
    onto the specular Q values, extending above and below with the final
    background measurement. If there are no backgrounds, then data is
    sent through unchanged.

    Background subtraction is applied independently to the different
    polarization cross sections.

    The *align* flag determines which background points are matched
    to the sample points. It can be 'sample' if background is
    measured using an offset from the sample angle, or 'detector'
    if it is offset from detector angle. If it is 'none' then use
    the 'Qz_basis' value set in the loader. The 'auto' option uses
    'Qz_target' if it exists, or tries to guess from the measured angles.

    **Inputs**

    data (refldata) : specular data

    backp {Background+} (refldata?) : plus-offset background data

    backm {Background-} (refldata?) : minus-offset background data

    align (opt:none|sample|detector|auto) : apply align_background to
    background inputs with offset='auto'

    **Returns**

    output (refldata) : background subtracted specular data

    2016-03-23 Paul Kienzle
    """
    from .background import apply_background_subtraction

    # Note: This changes backp and backm, so copy first.
    if align != "none":
        if backp is not None:
            backp = copy(backp)
            align_background(backp, align=align)
        if backm is not None:
            backm = copy(backm)
            align_background(backm, align=align)

    #print "%s - (%s+%s)/2"%(data.name, (backp.name if backp else "none"), (backm.name if backm else "none"))
    data = copy(data)
    apply_background_subtraction(data, backp, backm)
    return data

@module
def interpolate_background(data, backp, backm, align='auto'):
    """
    Interpolate background data onto specular angles.

    The *align* flag determines which background points are matched
    to the specular points. The 'auto' option uses the Qz_basis set
    in the file loader, otherwise align the sample angle or the detector
    angle. This sets Qz_basis to align so that a subsequent subtraction
    operation will use the same interpolation.

    Masking of background or specular should occur before interpolation
    or after subtraction.

    **Inputs**

    data (refldata) : specular data

    backp {Background+} (refldata?) : plus-offset background data

    backm {Background-} (refldata?) : minus-offset background data

    align (opt:auto|sample|detector|sample_target|detector_target)
    : angle which determines $q_z$

    **Returns**

    output (refldata) : unchanged specular

    outp (refldata) : interpolated plus-offset background data

    outm (refldata) : interpolated minus-offset background data

    2020-11-20 Paul Kienzle new module
    """
    from .background import apply_interpolation

    if backp is not None:
        backp = copy(backp)
        backp.sample = copy(backp.sample)
        backp.detector = copy(backp.detector)
        apply_interpolation(data=backp, base=data, align=align)
    if backm is not None:
        backm = copy(backp)
        backm.sample = copy(backp.sample)
        backm.detector = copy(backp.detector)
        apply_interpolation(data=backm, base=data, align=align)
    return data, backp, backm

@module
def fit_background_field(back, fit_scale=True, scale=1.0, epsD0=0.01, epssi=1.109e-4, LS3=380, LS4=1269, LSD=1675, HD=150, maxF=76.2, Qcutoff=0.05):
    """
    Fit the background field from a thin liquid reservoir to background
    datasets. Background datasets:

     o Can be any at any (non-specular) condition

     o Should already be normalized by incident intensity

     o Can involve any number of scans

    The background datasets are fit using a Levenberg-Marquardt algorithm to a model
    involving a two parameters: epsD, the product of the incoherent attenuation coefficient
    of the reservoir (eps) and the reservoir thickness D, and a scale factor that accounts for
    uncertainty in the instrument geometry, i.e. the post-sample slit distances and/or the
    solid angle subtended by the detector.

    The uncertainty in the optimized parameters are estimated from the covariance matrix,
    and the chi-squared value of the fit (typically 1.5 or less) is also calculated and available
    in the parameter output. Note that the covariance matrix itself is passed to subract_background_field
    because the parameters are correlated.

    If the scale factor is not included in the fit, the accuracy of the calculation depends critically on
    correct values for the instrument geometry. The geometry is inferred from the data files;
    if it is missing, certain values can be overridden using the data entry boxes. These include the
    slit4-detector distance (0 for instruments with no slit4) and the detector height (for horizontal
    reflectometers, the width).

    The calculation assumes a geometry like that of the NIST liquid flow cell, in which the liquid reservoir
    is encased in silicon. For a different cell material (e.g. sapphire), the appropriate incoherent
    extinction coefficient for the material should replace the default Si value.

    **Inputs**

    back (refldata[]) : group of background datasets

    epsD0 {Reservoir extinction coefficient guess (mm^-1)} (float:mm^-1) : initial guess
    for product of incoherent extinction coefficient of reservoir and reservoir thickness

    epssi {Extinction coefficient of Si (mm^-1)} (float:mm^-1) : incoherent
    extinction coefficient of Si or cell materials

    fit_scale {Include scale factor in fit?} (bool) : True if scale factor on detector solid angle
    should be included in fit (use if uncertain of the instrument geometry)

    scale {Scale factor value} (float) : Value of scale factor. Initial guess if scale
    factor is included in fit; otherwise fixed scale factor value.

    Qcutoff {Target Qz cutoff (Ang^-1)} (float:Ang^-1) : Cutoff target Q_z value below which background data
    are excluded from background fit

    LS3 {sample-slit3 distance (mm)} (float:mm) : Distance from sample to slit3

    LS4 {sample-slit4 distance (mm)} (float:mm) : Distance from sample to slit4

    LSD {sample-detector distance (mm)} (float:mm) : Distance from sample to detector

    HD {detector height (mm)} (float:mm) : Height of detector

    maxF {maximum beam footprint (mm)} (float:mm) : Sample dimension in beam direction

    **Returns**

    fitparams (ncnr.refl.backgroundfield.params) : fit parameters, covariances, and chi-squared

    fit (refldata[]) : ReflData structure containing fit outputs (for plotting against
    background inputs to inspect background field fit)

    2018-06-12 David P. Hoogerheide; last updated 2018-10-12
    """

    from .backgroundfield import fit_background_field

    bff, outfitdata = fit_background_field(back, epsD0, epssi, fit_scale, scale, LS3, LS4, LSD, HD, Qcutoff, maxF)

    return bff, outfitdata


@module
def subtract_background_field(data, bfparams, epsD=None, epsD_var=None, scale=None, scale_var=None, scale_epsD_covar=None):
    """
    Subtract the background field from a thin liquid reservoir from
    a specular dataset, which should already be normalized by the incident intensity.
    Applies the background field fit with the "Fit Background Field" module. See that
    module's description for more details.

    **Inputs**

    data (refldata[]) : specular data

    bfparams (ncnr.refl.backgroundfield.params) : background field parameters

    epsD {epsD} (float) : p

    epsD_var {epsD variance} (float) : dp2

    scale {scale} (float) : s

    scale_var {scale factor variance} : ds2

    scale_epsD_covar {covariance of scale factor and epsD} : dsp

    **Returns**

    output (refldata[]) : background subtracted specular data

    2018-06-12 David P. Hoogerheide; last updated 2018-10-12
    """

    from .backgroundfield import apply_background_field_subtraction

    data = [copy(d) for d in data]

    if epsD is None: epsD = bfparams.p
    if epsD_var is None: epsD_var = bfparams.dp2
    if scale is None: scale = bfparams.s
    if scale_var is None: scale_var = bfparams.ds2
    if scale_epsD_covar is None: scale_epsD_covar = bfparams.dsp

    pcov = np.array([[scale_var, scale_epsD_covar],
                     [scale_epsD_covar, epsD_var]])

    apply_background_field_subtraction(data, epsD, bfparams.epssi, bfparams.LS3, bfparams.LS4, bfparams.L4D, bfparams.HD, bfparams.maxF, scale, pcov)

    return data

@module
def divide_intensity(data, base):
    """
    Scale data by incident intensity.

    Data is matched to the incident scan according to the measurement type:
    By default it is aligned by the angular resolution of both scans,
    assuming all data with the same angular resolution was subject to the
    same incident intensity.

    For Candor data it is aligned by the slit 1 opening (slit.x),
    and for MAGIK horizontal mode it is aligned by the incident angle (sample.angle_x)

    **Inputs**

    data (refldata) : specular, background or subtracted data

    base (refldata) : intensity data

    **Returns**

    output (refldata) : reflected intensity

    | 2015-12-17 Paul Kienzle
    | 2020-07-23 Brian Maranville add align_intensity flag to data to match incident and reflected points

    """
    if base is not None:
        from .scale import apply_intensity_norm
        data = copy(data)
        apply_intensity_norm(data, base)
    return data


@module
def smooth_slits(datasets, degree=1, span=2, dx=0.01):
    """
    Align slits with a moving window 1-D polynomial least squares filter.

    Updates *slit1.x*, *slit2.x* and *angular_resolution* attributes of the
    slit measurements so they all use a common set of points.

    Updates divergence automatically after smoothing.

    **Inputs**

    datasets (refldata[]) : slits to align and smooth

    degree (int) : polynomial degree on smoothing filter

    span (int) : number of consecutive points to use in the fit. Odd
    sized *span* is preferred.  *span* must be larger than *degree*.
    *degree=1* and *span=2* is equivalent to linear interpolation.

    dx (float:mm<0,>) :  size within which slits can be merged.

    **Returns**

    outputs (refldata[]) : aligned and smoothed slits.

    2015-12-17 Paul Kienzle
    """
    from .smoothslits import apply_smoothing
    datasets = [copy(d) for d in datasets]
    for d in datasets:
        d.slit1, d.slit2 = copy(d.slit1), copy(d.slit2)

    apply_smoothing(datasets, dx=dx, degree=degree, span=span)
    return datasets


@module
def abinitio_footprint(data, Io=1., width=None, offset=0.):
    """
    Apply an *ab initio* footprint correction to the data.

    Footprint is computed from the slits and the sample angle so those must
    be available in the data.  If the data has been stitched to common Q
    from different theta, lambda combinations, then footprint will no
    longer be available.

    Footprint is computed using sample angle. If background is measured using
    sample angle offset, then footprint should be applied before background
    subtraction. For detector angle offset the correction is the same for
    specular and background, so it can be applied before or after subtraction.

    **Inputs**

    data (refldata) : uncorrected measurement

    Io (float:): scale factor to account for vertical beam spill.

    width (float:mm) : sample width along the beam.  If not provided, use the
    value stored in the file.

    offset (float:mm) : offset of the center of rotation of the sample in
    the direction of the beam, toward the detector.

    **Returns**

    outputs (refldata): footprint-corrected data

    2016-09-02 Paul Kienzle
    """
    from .footprint import apply_abinitio_footprint

    data = copy(data)
    apply_abinitio_footprint(data, Io, width, offset)
    return data

@module
def fit_footprint(data, fit_range=[None, None], origin=False):
    """
    Fit a footprint using a range of data below the critical edge.

    If a range is not provided, then no footprint is fitted and instead the
    footprint slope and intercept from the *correct_footprint* component are
    used.

    **Inputs**

    data (refldata[]) : uncorrected measurement

    fit_range (range?:x): x-region over which to fit

    origin (bool) : True if data should go through the origin

    **Returns**

    fitted_footprint (ncnr.refl.footprint.params?) : slope and intercept

    2016-04-30 Paul Kienzle
    """
    from .footprint import fit_footprint
    if fit_range is None:
        fit_range = [None, None]
    footprint = fit_footprint(data, fit_range[0], fit_range[1], kind='slope' if origin else 'line')
    return footprint

@module
def correct_footprint(data, fitted_footprint, correction_range=[None, None],
                      slope=None, slope_error=0.0, intercept=None,
                      intercept_error=0.0):
    """
    Apply fitted footprint correction to each data set.

    If not footprint is fitted, then values must be entered for *slope* and
    *intercept*.

    **Inputs**

    data (refldata) : uncorrected measurement

    fitted_footprint (ncnr.refl.footprint.params?) : fitted footprint

    correction_range {Correction Application Range} (range?:x) : Lower bound of region to apply footprint correction

    slope (float) : footprint slope

    slope_error {Error on slope} (float): and uncertainty

    intercept (float) : footprint intercept

    intercept_error {Error on intercept} (float): and uncertainty

    **Returns**

    outputs (refldata): footprint-corrected data

    2017-06-29 Paul Kienzle
    """
    from .footprint import apply_fitted_footprint, FootprintData
    if correction_range is None:
        correction_range = [None, None]
    # always use manually-provided error on slope and intercept (not fitted)
    dp = np.array([slope_error, intercept_error])
    if fitted_footprint is None:
        # make empty footprint data object
        p = np.array([None, None])
        fitted_footprint = FootprintData(p, None)
    if slope is not None:
        fitted_footprint.p[0] = slope
    if intercept is not None:
        fitted_footprint.p[1] = intercept
    # in all cases, overwrite the error in fitted_footprint with specified
    # values:
    fitted_footprint.dp = dp
    data = copy(data)
    apply_fitted_footprint(data, fitted_footprint, correction_range)
    return data

@nocache
@module
def estimate_polarization(data, FRbalance=50.0, Emin=0.0, Imin=0.0, clip=False):
    """
    Compute polarizer and flipper efficiencies from the intensity data.

    If clip is true, reject points above or below particular efficiencies.
    The minimum intensity is 1e-10.  The minimum efficiency is 0.9.

    The computed values are systematically related to the efficiencies:

      beta: intensity/2
      fp: front polarizer efficiency is F
      rp: rear polarizer efficiency is R
      ff: front flipper efficiency is (1-x)/2
      rf: rear flipper efficiency is (1-y)/2

    reject is the indices of points which are clipped because they
    are below the minimum efficiency or intensity.

    See PolarizationEfficiency.pdf for details on the calculation.

    **Inputs**

    data (refldata[]) : direct beam measurement to determine polarization

    FRbalance (float:%<0,100>) : front/rear balance of to use for efficiency loss

    Emin (float:%<0,100>) : minimum efficiency cutoff

    Imin (float:counts/s<0,>) : minimum intensity cutoff

    clip {Clip efficiency} (bool) : clip efficiency between Emin and one

    **Returns**

    polarization (poldata) : estimated polarization correction factors

    2015-12-18 Paul Kienzle
    """
    from .polarization import PolarizationData

    poldata = PolarizationData(data, FRbal=0.01*FRbalance,
                               Emin=0.01*Emin, Imin=Imin, clip=clip)
    return poldata


@nocache
@module
def correct_polarization(data, polarization, spinflip=True):
    """
    Correct data for polarizer and flipper efficiencies.

    **Inputs**

    data (refldata[]) : polarized data to be corrected

    polarization (poldata) : estimated polarization efficiency

    spinflip {Correct spinflip data} (bool) : correct spinflip data if available

    **Returns**

    output (refldata[]) : polarization corrected data

    2015-12-18 Paul Kienzle
    | 2017-08-22 Brian Maranville interpolate back to Qz-basis for that cross-section
    """
    from .polarization import apply_polarization_correction
    data = copy(data)
    apply_polarization_correction(data, polarization, spinflip)
    return data


@module
def save(data, name='auto', ext='auto', path='auto'):
    """
    Save data to a particular file

    **Inputs**

    data (refldata) : data to save

    name (opt:auto|...) : name of the file, or 'auto' to use the basename

    ext {Extension} (opt:auto|...) : file extension, or 'auto' to use the
    id of the last step

    path (opt:auto|...) : data path, or 'auto' to use the current directory

    2015-12-17 Paul Kienzle
    """
    if path == 'auto':
        path = '.'
    if ext == 'auto':
        ext = '.dat'
    elif not ext.startswith('.'):
        ext = '.' + ext
    if name == 'auto':
        name = data.name
    filename = os.path.join(path, name+ext)
    data.save(filename)


@cache
@module
def ng7_psd(
        filelist=None,
        detector_correction=False,
        monitor_correction=False,
        center=None,
        intent='auto',
        sample_width=None,
        base='none'):
    r"""
    Load a list of NG7 PSD files from the NCNR data server.

    **Inputs**

    filelist (fileinfo[]): List of files to open.

    detector_correction {Apply detector deadtime correction} (bool)
    : If True, use deadtime constants in file to correct detector counts.

    monitor_correction {Apply monitor saturation correction} (bool)
    : If True, use the measured saturation curve in file to correct
    : the monitor counts.

    center {Beam center} (int)
    : Detector pixel containing the beam center.  This is needed for
    : plotting Qx-Qz, etc., and for setting the specular integration region.

    intent (opt:auto|specular|intensity|scan)
    : Measurement intent (specular, slit, or some other scan), auto or infer.
    : If intent is 'scan', then use the first scanned variable.

    sample_width {Sample width (mm)} (float?)
    : Width of the sample along the beam direction in mm, used for
    calculating the effective resolution when the sample is smaller
    than the beam.  Leave blank to use value from data file.

    base {Normalize by} (opt:auto|monitor|time|roi|power|none)
    : How to convert from counts to count rates.
    : Leave this as none if your template does normalization after integration.

    **Returns**

    output (refldata[]): All entries of all files in the list.

    | 2020-02-05 Paul Kienzle
    | 2020-02-11 Paul Kienzle include divergence estimate in startup
    """
    from .load import url_load_list
    from .ng7psd import load_entries

    # Note: divergence is required for join, so always calculate it.  If you
    # really want it optional then use:
    #
    #  auto_divergence {Calculate dQ} (bool)
    #    : Automatically calculate the angular divergence of the beam.
    #
    auto_divergence = True

    datasets = []
    for data in url_load_list(filelist, loader=load_entries):
        data.Qz_basis = 'target'
        if intent not in [None, 'auto']:
            data.intent = intent
        if center is not None:
            data = psd_center(data, center)
        if auto_divergence:
            data = divergence(data, sample_width)
        if detector_correction:
            data = detector_dead_time(data, None)
        if monitor_correction:
            data = monitor_saturation(data)
        data = normalize(data, base=base)
        #print "data loaded and normalized"
        datasets.append(data)

    return datasets

@cache
@module
def super_load(filelist=None,
               detector_correction=False,
               monitor_correction=False,
               intent='auto',
               Qz_basis='actual',
               sample_width=None,
               base='auto'):
    r"""
    Load a list of nexus files from the NCNR data server.

    *Qz_basis* uses one of the following values:

        **actual**
            calculates Qx and Qz as (x,z)-components of
            $(\vec k_{\text{out}} - \vec k_\text{in})$ in sample coordinates,
        **detector**
            ignores the sample angle and calculates Qz
            as $(4\pi/\lambda \sin(\theta_\text{detector}/2))$,
        **sample**
            ignores the detector angle and calculates Qz
            as $(4\pi/\lambda \sin(\theta_\text{sample}))$
        **target**
            uses the user-supplied Qz_target values

    **Inputs**

    filelist (fileinfo[]): List of files to open.

    detector_correction {Apply detector deadtime correction} (bool)
    : Which deadtime constant to use for detector deadtime.

    monitor_correction {Apply monitor deadtime correction} (bool)
    : Which deadtime constant to use for monitor deadtime.

    intent (opt:auto|specular|background+\|background-\|intensity|rock sample|rock detector|rock qx|scan)
    : Measurement intent (specular, background+, background-, slit, rock),
    auto or infer.  If intent is 'scan', then use the first scanned variable.

    Qz_basis (opt:actual|detector|sample|target)
    : How to calculate Qz from instrument angles.

    sample_width {Sample width (mm)} (float?)
    : Width of the sample along the beam direction in mm, used for
    calculating the effective resolution when the sample is smaller
    than the beam.  Leave blank to use value from data file.

    base {Normalize by} (opt:auto|monitor|time|roi|power|none)
    : how to convert from counts to count rates

    **Returns**

    output (refldata[]): All entries of all files in the list.

    | 2017-01-13 Brian Maranville
    | 2017-02-15 Paul Kienzle normalize by time if monitor is not present
    | 2017-08-21 Brian Maranville use fileName from trajectory
    | 2018-05-01 Brian Maranville import temperature metadata
    | 2018-05-07 Brian Maranville detector deadtime correction defaults to True
    | 2018-05-10 Brian Maranville export all columns if intent is scan
    | 2018-05-11 Brian Maranville detector deadtime correction defaults to False
    | 2018-06-18 Brian Maranville change to nexusref to ignore areaDetector
    | 2018-06-20 Brian Maranville promote detector.wavelength to column (and resolution)
    | 2018-08-29 Paul Kienzle ignore sampleTilt field for NG7
    | 2018-12-10 Brian Maranville get_plottable routines moved to python data container from js
    | 2020-01-21 Brian Maranville updated loader to handle hdf-nexus
    | 2020-12-18 Brian Maranville adding source_power column to monitor
    | 2022-04-27 Brian Maranville fix count time for Rigaku in sweep mode
    """
    from .load import url_load_list
    #from .intent import apply_intent
    #from .angles import apply_divergence
    # Note: Fileinfo is a structure with
    #     { path: "location/on/server", mtime: timestamp }

    # Note: divergence is required for join, so always calculate it.  If you
    # really want it optional then use:
    #
    #  auto_divergence {Calculate dQ} (bool)
    #    : Automatically calculate the angular divergence of the beam.
    #
    auto_divergence = True

    # TODO: sample_width is ignored if datafile defines angular_divergence

    datasets = []
    for data in url_load_list(filelist):
        data.Qz_basis = Qz_basis
        if intent not in [None, 'auto']:
            data.intent = intent
        if auto_divergence:
            data = divergence(data, sample_width)
        if detector_correction:
            data = detector_dead_time(data, None)
        if monitor_correction:
            data = monitor_dead_time(data, None)
        data = normalize(data, base=base)
        #print "data loaded and normalized"
        datasets.append(data)

    return datasets

@cache
@module
def magik_horizontal(filelist=None,
                    detector_correction=False,
                    monitor_correction=False,
                    intent='auto',
                    Qz_basis='actual',
                    sample_width=None,
                    base='auto'):
    r"""
    Load a list of nexus files from the NCNR data server.

    *Qz_basis* uses one of the following values:

        **actual**
            calculates Qx and Qz as (x,z)-components of
            $(\vec k_{\text{out}} - \vec k_\text{in})$ in sample coordinates,
        **detector**
            ignores the sample angle and calculates Qz
            as $(4\pi/\lambda \sin(\theta_\text{detector}/2))$,
        **sample**
            ignores the detector angle and calculates Qz
            as $(4\pi/\lambda \sin(\theta_\text{sample}))$
        **target**
            uses the user-supplied Qz_target values

    **Inputs**

    filelist (fileinfo[]): List of files to open.

    detector_correction {Apply detector deadtime correction} (bool)
    : Which deadtime constant to use for detector deadtime.

    monitor_correction {Apply monitor deadtime correction} (bool)
    : Which deadtime constant to use for monitor deadtime.

    intent (opt:auto|specular|background+\|background-\|intensity|rock sample|rock detector|rock qx|scan)
    : Measurement intent (specular, background+, background-, slit, rock),
    auto or infer.  If intent is 'scan', then use the first scanned variable.

    Qz_basis (opt:actual|detector|sample|target)
    : How to calculate Qz from instrument angles.

    sample_width {Sample width (mm)} (float?)
    : Width of the sample along the beam direction in mm, used for
    calculating the effective resolution when the sample is smaller
    than the beam.  Leave blank to use value from data file.

    base {Normalize by} (opt:auto|monitor|time|roi|power|none)
    : how to convert from counts to count rates

    **Returns**

    output (refldata[]): All entries of all files in the list.

    | 2020-07-21 Brian Maranville
    | 2020-07-23 Brian Maranville Added a flag to the loader, to control divide_intensity align_by
    | 2020-09-03 Brian Maranville Vertical slit readout changed
    | 2021-09-20 Brian Maranville use horizontalGeom.angle for sample.angle_x (ignore tilt except in ROCK)
    """
    from .load import url_load_list
    from .magik_horizontal import load_entries
    
    # Note: Fileinfo is a structure with
    #     { path: "location/on/server", mtime: timestamp }

    # Note: divergence is required for join, so always calculate it.  If you
    # really want it optional then use:
    #
    #  auto_divergence {Calculate dQ} (bool)
    #    : Automatically calculate the angular divergence of the beam.
    #
    auto_divergence = True

    # TODO: sample_width is ignored if datafile defines angular_divergence

    datasets = []
    for data in url_load_list(filelist, loader=load_entries):
        data.Qz_basis = Qz_basis
        if intent not in [None, 'auto']:
            data.intent = intent
        if auto_divergence:
            data = divergence(data, sample_width)
        if detector_correction:
            data = detector_dead_time(data, None)
        if monitor_correction:
            data = monitor_dead_time(data, None)
        data = normalize(data, base=base)
        #print "data loaded and normalized"
        datasets.append(data)

    return datasets

@cache
@module
def super_load_sorted(filelist=None,
                      detector_correction=False,
                      monitor_correction=False,
                      sample_width=None,
                      base='auto'):
    """
    Load a list of nexus files from the NCNR data server, to be sorted by
    the intent stored in the file.  If intent does not match
    'specular', 'background+', 'background-' or 'intensity', it is not returned.

    **Inputs**

    filelist (fileinfo[]): List of files to open.

    detector_correction {Apply detector deadtime correction} (bool)
    : Which deadtime constant to use for detector deadtime.

    monitor_correction {Apply monitor deadtime correction} (bool)
    : Which deadtime constant to use for monitor deadtime.

    sample_width {Sample width (mm)} (float): Width of the sample along the
    beam direction in mm, used for calculating the effective resolution when
    the sample is smaller than the beam.  Leave blank to use value from data file.

    base {Normalize by} (opt:auto|monitor|time|roi|power|none)
    : how to convert from counts to count rates

    **Returns**

    spec (refldata[]): All entries of all spec files in the list.

    bgp (refldata[]): All entries of all bg+ files in the list.

    bgm (refldata[]): All entries of all bg- files in the list.

    slit (refldata[]): All entries of all slit files in the list.

    2016-06-30 Brian Maranville
    """
    from .load import url_load_list
    auto_divergence = True
    sorting_key = "intent"
    sort_values = ["specular", "background+", "background-", "intensity"]
    outputs = dict([(key, []) for key in sort_values])

    for data in url_load_list(filelist):
        if auto_divergence:
            data = divergence(data, sample_width)
        if detector_correction:
            data = detector_dead_time(data, None)
        if monitor_correction:
            data = monitor_dead_time(data, None)
        data = normalize(data, base=base)
        intent = getattr(data, sorting_key, None)
        if intent in outputs:
            outputs[intent].append(data)

    return tuple([outputs[k] for k in sort_values])

@module
def spin_asymmetry(data):
    """
    Do the calculation (up-up - down-down) / (up-up + down-down) and
    return a single dataset.

    **Inputs**

    data (refldata[]): input data; must contain up-up and down-down polarizations

    **Returns**

    output (refldata): calculated spin asymmetry.

    2016-04-04 Brian Maranville
    """
    mm = [d for d in data if d.polarization in ('-', '--')][0]
    pp = [d for d in data if d.polarization in ('+', '++')][0]
    output = copy(mm)
    output.vscale = "linear"
    output.vlabel = "Spin asymmetry (pp-mm)/(pp+mm) "
    output.vunits = "unitless"
    shortest = min(mm.v.shape[0], pp.v.shape[0])
    mmv = mm.v[:shortest]
    mmdv = mm.dv[:shortest]
    ppv = pp.v[:shortest]
    ppdv = pp.dv[:shortest]
    denom = (mmv + ppv)
    output.v = (ppv - mmv) / denom
    # d(sa)/d(x) = 2*x/(x+y)**2, d(sa)/d(y) = -2*y/(x+y)**2
    output.dv = np.sqrt(((2.0*mmv*mmdv)/(denom**2))**2 + ((2.0*ppv*ppdv)/(denom**2))**2)
    return output

@module
def average_flux(data, base, beam_height=25):
    """
    Calculate time-averaged flux on the sample

    Data is matched according to angular resolution, assuming all data with
    the same angular resolution was subject to the same incident intensity.
    Does not work on polarized beam data with multiple slit scans

    Beam area is taken to be beam_height * slit2 aperture (from file)

    **Inputs**

    data (refldata[]) : specular, background or subtracted data

    base (refldata) : intensity data

    beam_height (float:mm): height of the beam at the sample position

    **Returns**

    flux (ncnr.refl.flux.params?) : integrated flux data

    2018-03-01 Brian Maranville
    """
    from reductus.dataflow.modules import refl
    TIME_RESOLUTION = 1e-6 # 1 microsecond for NCNR timers.

    if base is not None:
        from .scale import calculate_number
        from reductus.dataflow.lib import err1d

        fluxes = []
        total_number = 0.0
        total_number_variance = 0.0
        total_time = 0.0
        total_time_variance = 0.0
        sum_weighted_flux = 0.0
        sum_weighted_flux_variance = 0.0

        for datum in data:
            datum = copy(datum)
            beam_area = datum.slit2.x * beam_height / 100.0 # both in mm, convert to cm
            N, varN = calculate_number(datum, base, time_uncertainty=TIME_RESOLUTION)
            S, varS = err1d.sum(N, varN)
            P, varP = err1d.div(N, varN, beam_area, 0.0)
            A, varA = err1d.sum(P, varP) # time-weighted average of Flux/Area
            T, varT = err1d.sum(datum.monitor.count_time, TIME_RESOLUTION**2)
            F, varF = err1d.div(A, varA, T, varT) # average Flux/(Area * Time)
            fluxes.append({
                "name": datum.name,
                "number_incident": S,
                "number_incident_error": np.sqrt(varS),
                "number_incident_units": "neutrons",
                "average_flux": F,
                "average_flux_error": np.sqrt(varF),
                "average_flux_units": "neutrons/(second * cm^2)",
                "total_time": float(T),
                "total_time_error": float(np.sqrt(varT))
            })
            total_number += S
            total_number_variance += varS
            total_time += T
            total_time_variance += varT
            sum_weighted_flux += A
            sum_weighted_flux_variance += varA
        aggregated_flux, aggregated_flux_variance = err1d.div(sum_weighted_flux, sum_weighted_flux_variance, total_time, total_time_variance)
        output = refl.FluxData(fluxes, {
            "aggregated_average_flux": aggregated_flux,
            "aggregated_average_flux_error": np.sqrt(aggregated_flux_variance),
            "aggregated_time": total_time,
            "aggregated_time_error": np.sqrt(total_time_variance)
        })
    else:
        output = refl.FluxData([], None)
    return output
