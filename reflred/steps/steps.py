# This program is public domain
import os
from copy import copy
from warnings import warn

# TODO: maybe bring back formula to show the math of each step
# TODO: what about polarized data?

ALL_ACTIONS = []
def cache(action):
    """
    Decorator which adds the *cached* attribute to the function.

    Use *@cache* to force caching to always occur (for example, when
    the function references remote resources, vastly reduces memory, or is
    expensive to compute.  Use *@nocache* when debugging a function
    so that it will be recomputed each time regardless of whether or not it
    is seen again.
    """
    action.cached = True
    return action

def nocache(action):
    """
    Decorator which adds the *cached* attribute to the function.

    Use *@cache* to force caching to always occur (for example, when
    the function references remote resources, vastly reduces memory, or is
    expensive to compute.  Use *@nocache* when debugging a function
    so that it will be recomputed each time regardless of whether or not it
    is seen again.
    """
    action.cached = False
    return action

def module(action):
    """
    Decorator which records the action in *ALL_ACTIONS*.

    This just collects the action, it does not otherwise modify it.
    """
    ALL_ACTIONS.append(action)

    # This is a decorator, so return the original function
    return action

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

@cache
@module
def ncnr_load(filelist=None):
    """
    Load a list of nexus files from the NCNR data server.

    **Inputs**

    filelist (fileinfo[]): List of files to open.

    **Returns**

    output (refldata[]): All entries of all files in the list.

    2015-12-17 Brian Maranville
    """
    # NB: Fileinfo is a structure with
    #     { path: "location/on/server", mtime: timestamp }
    from .load import url_load_list
    return url_load_list(filelist)

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

    data = fit_dead_time(data, source=source, mode=mode)

    data.log("fit_dead_time(attenuated, unattenuated, source=%r, mode=%r)"
             % (source, mode))
    for k, d in enumerate(data):
        data.log("data %d:"%k)
        data.log(d.messages)
    return data



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
        data.log('monitor_dead_time(nonparalyzing=%.15g, paralyzing=%.15g)'
                 % (nonparalyzing, paralyzing))
        apply_monitor_dead_time(data, tau_NP=nonparalyzing,
                                tau_P=paralyzing)
    elif dead_time != None:
        data.log('monitor_dead_time(dead_time)')
        data.log_dependency('dead_time', dead_time)
        apply_monitor_dead_time(data, tau_NP=dead_time.tau_NP,
                                tau_P=dead_time.tau_P)
    elif data.monitor.deadtime is not None:
        try:
            tau_NP, tau_P = data.monitor.deadtime
        except:
            tau_NP, tau_P = data.monitor.deadtime, 0.0
        data.log('monitor_dead_time()')
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

    2015-12-17 Paul Kienzle
    """
    from .deadtime import apply_detector_dead_time

    data = copy(data)
    data.detector = copy(data.detector)
    if nonparalyzing != 0.0 or paralyzing != 0.0:
        data.log('detector_dead_time(nonparalyzing=%.15g, paralyzing=%.15g)'
                 % (nonparalyzing, paralyzing))
        apply_detector_dead_time(data, tau_NP=nonparalyzing,
                                tau_P=paralyzing)
    elif dead_time != None:
        data.log('detector_dead_time(dead_time)')
        data.log_dependency('dead_time', dead_time)
        apply_detector_dead_time(data, tau_NP=dead_time.tau_NP,
                                tau_P=dead_time.tau_P)
    elif data.detector.deadtime is not None:
        try:
            tau_NP, tau_P = data.detector.deadtime
        except:
            tau_NP, tau_P = data.detector.deadtime, 0.0
        data.log('detector_dead_time()')
        apply_detector_dead_time(data, tau_NP=tau_NP, tau_P=tau_P)
    else:
        pass  # no deadtime correction parameters available.

    return data


@module
def monitor_saturation(data):
    """
    Correct the monitor dead time from stored saturation curve.

    **Inputs**

    data (refldata): Uncorrected data

    **Returns**

    output (refldata): Dead-time corrected data

    2015-12-17 Paul Kienzle
    """
    from .deadtime import apply_monitor_saturation
    data = copy(data)
    if getattr(data.monitor, 'saturation', None) is not None:
        data.monitor = copy(data.monitor)
        data.log('monitor_saturation()')
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
        print "detector",data.detector.__dict__
        data.detector = copy(data.detector)
        data.log('detector_saturation()')
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
    data.log('theta_offset(%.15g)' % offset)
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
    data.log("back_reflection()")
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
    data.log("absolute_angle()")
    apply_absolute_angle(data)
    return data


@module
def divergence(data):
    """
    Estimate divergence from slit openings.

    **Inputs**

    data (refldata): data without resolution estimate

    **Returns**

    output (refldata): data with resolution estimate

    2015-12-17 Paul Kienzle
    """
    from .angles import apply_divergence
    data = copy(data)
    data.log('divergence()')
    apply_divergence(data)
    return data


@module
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
    data.log('mask_specular()')
    apply_specular_mask(data)
    return data

def mask_action(data=None, mask_indices=None, **kwargs):
    """
    Set the data mask to the list of points, e.g. [0, 4, 5]
    """
    import numpy
    if mask_indices:
        data.mask = numpy.ones(data.detector.counts.shape, dtype="bool")
        data.mask[mask_indices] = False
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

    2016-02-08 Brian Maranville
    """
    data = copy(data)
    data.log('mask_points(%r)' % mask_indices)
    output = mask_action(data=data, mask_indices=mask_indices)
    return output

@module
def mark_intent(data, intent='auto'):
    """
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

    intent (opt*:auto|infer|specular|background+|background-|slit
    |rock sample|rock detector|rock qx) : intent to register with the
    datafile, or auto/infer to guess

    **Returns**

    output (refldata) : marked data

    2015-12-17 Paul Kienzle
    """
    from .intent import apply_intent
    data = copy(data)
    data.log('mark_intent(%r)' % intent)
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
        print "intent",d.intent, d.path
        groups[map_intent.get(d.intent, 'other')].append(d)

    return [groups[intent]
            for intent in 'specular backp backm intensity rock other'.split()]

@module
def normalize(data, base='auto'):
    """
    Estimate the detector count rate.

    *base* can be monitor, time, power, or none for no normalization.
    For example, if base='monitor' then the count rate will be counts
    per monitor count.  Note that operations that combine datasets require
    the same normalization on the points.

    If *base* is auto then the default will be chosen, which is 'monitor'
    if the monitor exists, otherwise it is 'time'.

    When viewing data, you sometimes want to scale it to a nice number
    such that the number of counts displayed for the first point is
    approximately the number of counts on the detector.

    **Inputs**

    data (refldata) : data to normalize

    base {Normalize by} (opt:auto|monitor|time|power|none)
    : how to convert from counts to count rates

    **Returns**

    output (refldata) : data with count rate rather than counts

    2015-12-17 Paul Kienzle
    """
    from .scale import apply_norm
    data = copy(data)
    data.log('normalize(base=%r)' % base)
    apply_norm(data, base)
    return data


@module
def rescale(data, scale=1.0, dscale=0.0):
    """
    Rescale the count rate by some scale and uncertainty.

    **Inputs**

    data (refldata) : data to scale

    scale (float*:<0,inf>) : amount to scale, one for each dataset

    dscale {Scale err} (float*:<0,inf>) : scale uncertainty for gaussian error propagation

    **Returns**

    output (refldata) : scaled data

    2015-12-17 Paul Kienzle
    """
    from .scale import apply_rescale
    data = copy(data)
    data.log("scale(%.15g,%.15g)" % (scale, dscale))
    apply_rescale(data, scale, dscale)
    return data

@module
def join(data, tolerance=0.05, order='file'):
    """
    Join operates on a list of datasets, returning a list with one dataset,
    or one dataset per polarization state.  When operating on a single
    dataset, it joins repeated points into single points.

    *tolerance* (default=0.05) is a scale factor on $\Delta \theta$ used to
    determine whether two angles are equivalent.  For a given tolerance
    $\epsilon$, a point at incident angle $\theta_1$ can be joined
    with one with incident angle $\theta_2$ when
    $|\theta_1 - \theta_2| < \epsilon \cdot \Delta\theta$.

    The join algorithm is greedy, so if you have a sequence of points with
    individual separation less than $\epsilon\cdot\Delta\theta$ but total
    spread greater than $\epsilon\cdot\Delta\theta$, they will be joined
    into multiple points with the final with the final point having worse
    statistics than the prior points.

    *order* is the sort order of the files that are joined.  The first
    file in the sorted list determines the metadata such as the base
    file name for the joined file.

    The joined datasets will be sorted as appropriate for the the
    measurement intent.  Masked points will be removed.

    Data must be normalized before join.

    **Inputs**

    data (refldata[]) : data to join

    tolerance (float:<0,inf>) : allowed separation between points while
    still joining them to a single point; this is relative to the angular
    resolution of the each point

    order (opt:file|time|theta|slit|none) : order determines which file is the
    base file, supplying the metadata for the joined set

    **Returns**

    output (refldata[]) : joined data

    2016-03-02 Paul Kienzle
    """
    from .joindata import sort_files, join_datasets
    from .util import group_by_xs
    # No copy necessary; join is never in-place.

    datasets = group_by_xs(data).values()
    output = []
    for group in datasets:
        group = sort_files(group, order)
        result = join_datasets(group, tolerance)

        result.log("join(*data)")
        for i, d in enumerate(group):
            result.log_dependency('data[%d]' % i, d)
        output.append(result)
    return output

@module
def align_background(data, offset='auto'):
    """
    Determine the Qz value associated with the background measurement.

    The *offset* flag determines which background points are matched
    to the sample points.  It can be 'sample' if background is
    measured using an offset from the sample angle, or 'detector'
    if it is offset from detector angle.   If *offset* is 'auto', then
    we guess whether it is a offset from sample or detector.

    For 'auto' alignment, we can only distinguish relative and constant offsets,
    not  whether it is offset from sample or detector, so we must rely on
    convention. If the offset is constant for each angle, then it is assumed
    to be a sample offset.  If the offset is proportional to the angle (and
    therefore offset/angle is constant), then it is assumed to be a detector
    offset. If neither condition is met, it is assumed to be a sample offset.

    The 'auto' test is robust: 90% of the points should be within 5% of the
    median value of the vector for the offset to be considered a constant.

    **Inputs**

    data (refldata) : background data with unknown $q$

    offset (opt:auto|sample|detector) : angle which determines $q_z$

    **Returns**

    output (refldata) : background with known $q$

    2015-12-17 Paul Kienzle
    """
    if offset is None:
        offset = 'auto'
    from .background import set_background_alignment
    data = copy(data)
    # TODO: do we want to log the alignment chosen when alignment is auto?
    # Or do we log the fact that auto alignment was chosen?
    set_background_alignment(data, offset)
    data.log('align_background(%r)'%data.Qz_basis)
    return data


@module
def subtract_background(data, backp, backm):
    """
    Subtract the background datasets from the specular dataset.

    The background+ and background- signals are removed from the list of
    data sets, averaged, interpolated, and subtracted from the specular.
    If there is no specular, then the backgrounds are simply removed and
    there is no further action.  If there are no backgrounds, then the
    specular is sent through unchanged.  Slit scans and rocking curves
    are not affected.

    This correction only operates on a list of datasets.  A single dataset
    which contains both specular and background, such as a PSD measurement,
    must first be filtered through a correction to separate the specular
    and background into a pair of datasets.

    Background subtraction is applied independently to the different
    polarization cross sections.

    **Inputs**

    data (refldata) : specular data

    backp {Background+} (refldata?) : plus-offset background data

    backm {Background-} (refldata?) : minus-offset background data

    **Returns**

    output (refldata) : background subtracted specular data

    2015-12-17 Paul Kienzle
    """
    from .background import apply_background_subtraction

    data = copy(data)
    data.log("background(%s,%s)"
             % ("backp" if backp is not None else "None",
                "backm" if backm is not None else "None"))
    if backp is not None:
        data.log_dependency("back+", backp)
    if backm is not None:
        data.log_dependency("back-", backm)
    apply_background_subtraction(data, backp, backm)
    return data


@module
def divide_intensity(data, base):
    """
    Scale data by incident intensity.

    Data is matched according to angular resolution, assuming all data with
    the same angular resolution was subject to the same incident intensity.

    **Inputs**

    data (refldata) : specular, background or subtracted data

    base (refldata) : intensity data

    **Returns**

    output (refldata) : reflected intensity

    2015-12-17 Paul Kienzle
    """
    from .scale import apply_intensity_norm
    data = copy(data)
    data.log("divide(base)")
    data.log_dependency("base", base)
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
        # TODO: not reproducible from log
        # no info in log about which datasets were smoothed together
        d.log("smooth_slits(degree=%d, span=%d, dx=%g)" % (degree, span, dx))

    apply_smoothing(datasets, dx=dx, degree=degree, span=span)
    return datasets


@module
def estimate_polarization(data, FRbalance=0.5, Emin=0.0, Imin=0.0, clip=False):
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

    2015-12-17 Paul Kienzle
    """
    from .polarization import PolarizationData

    poldata = PolarizationData(beam=data, FRbal=0.01*FRbalance,
                               Emin=0.01*Emin, Imin=Imin, clip=clip)

    poldata.log("PolarizationData(beam, Imin=%.15g, Emin=%.15g%%, FRbal=%.15g%%, clip=%d)"
             %(Imin, Emin, FRbalance, 0+clip))
    for xs in ('++','+-','-+','--'):
        poldata.log_dependency("beam"+xs, poldata[xs])
    return poldata


@module
def correct_polarization(data, polarization, spinflip=True):
    """
    Correct data for polarizer and flipper efficiencies.

    **Inputs**

    data (refldata) : polarized data to be corrected

    polarization (poldata) : estimated polarization efficiency

    spinflip {Correct spinflip data} (bool) : correct spinflip data if available

    **Returns**

    output (refldata) : polarization corrected data

    2015-12-17 Paul Kienzle
    """
    from .polarization import apply_polarization_correction
    data = copy(data)
    data.log("correct_polarization(polarization, splinflip=True)")
    data.log_dependency("polarization", polarization)
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
        # TODO: look in the log to guess an extension
        ext = '.dat'
    elif not ext.startswith('.'):
        ext = '.' + ext
    if name == 'auto':
        name = data.name
    filename = os.path.join(path, name+ext)
    data.save(filename)

@cache
@module
def super_load(filelist=None,
               detector_correction=False,
               monitor_correction=False,
               intent='auto'):
    """
    Load a list of nexus files from the NCNR data server.

    **Inputs**

    filelist (fileinfo[]): List of files to open.

    detector_correction {Apply detector deadtime correction} (bool)
    : Which deadtime constant to use for detector deadtime.

    monitor_correction {Apply monitor deadtime correction} (bool)
    : Which deadtime constant to use for monitor deadtime.

    intent (str) : Measurement intent (specular, background+, background-,
    slit, rock), auto or infer.

    **Returns**

    output (refldata[]): All entries of all files in the list.

    2016-03-03 Brian Maranville
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

    datasets = []
    for data in url_load_list(filelist):
        if auto_divergence:
            data = divergence(data)
        if detector_correction:
            data = detector_dead_time(data)
        if monitor_correction:
            data = monitor_dead_time(data, None)
        data = mark_intent(data, intent)
        data = normalize(data)
        #print "data loaded and normalized"
        datasets.append(data)

    return datasets

# ==================

def demo():
    from reflred.examples import ng1 as group
    from reflred.steps import steps as cor
    from reflred.refldata import Intent

    print "="*20

    spec, back, slits = group.spec(), group.back(), group.slits()

    files = spec+back+slits
    files = [f for group in files for f in group]

    if False:
        detector_attenuated = load('detector_attenuated')
        detector_unattenuated = load('detector_unattenuated')
        monitor_attenuated = load('monitor_attenuated')
        monitor_unattenuated = load('monitor_unattenuated')
        monitor_dead_time = cor.fit_dead_time(monitor_attenuated,
                                              monitor_unattenuated)
        detector_dead_time = cor.fit_dead_time(detector_attenuated,
                                               detector_unattenuated)
        files = [cor.monitor_dead_time(d, tau_NP=monitor_dead_time.tau_NP, tau_P=monitor_dead_time.tau_P) for d in files]
        files = [cor.detector_dead_time(d, tau_NP=detector_dead_time.tau_NP, tau_P=detector_dead_time.tau_P) for d in files]
    else:
        files = [cor.monitor_saturation(d) for d in files]
        files = [cor.detector_saturation(d) for d in files]
        pass

    files = [cor.divergence(d) for d in files]
    files = [cor.normalize(d, 'auto') for d in files]
    files = [cor.mark_intent(d, 'auto') for d in files]

    #for d in files: print d.name, d.intent

    raw_spec = [d for d in files if d.intent == Intent.spec]
    raw_backp = [d for d in files if d.intent == Intent.backp]
    raw_backm = [d for d in files if d.intent == Intent.backm]
    raw_slits = [d for d in files if d.intent == Intent.slit]

    # Maybe separate alignment from join
    """
    alignment_fields = [
        'sample.theta', 'detector.theta', 'slit1.x', 'slit2.x',
        ]
    alignment = CommonValues(data=alignment.output, fields=alignment_fields)
    spec = join(datasets=spec, alignment=alignment.theta,
                fields=alignment_fields)
    back = Join(data=back.output, alignment=alignment.theta,
                fields=alignment_fields)
    slits = Join(data=slits.output, alignment=alignment.theta,
                 fields=['slit1.x', 'slit2.x'])
    """

    raw_backp, raw_backm = [[align_background(mask_specular(data=d),
                                              'auto')
                                              #refldata.SAMPLE_OFFSET)
                             for d in v]
                            for v in (raw_backp, raw_backm)]

    scaled_slits = [cor.rescale(d, I, 0.)
                    for d, I in zip(raw_slits, [1, 1, 20, 20, 20, 115])]

    #for d in spec: d.plot()

    spec = cor.join(raw_spec)
    backp = cor.join(raw_backp)
    backm = cor.join(raw_backm)
    slits = cor.join(scaled_slits, tolerance=0.0001)
    if False:
        cor.save(spec, 'spec')
        cor.save(backp, 'bp')
        cor.save(backm, 'bm')
        cor.save(slits, 'res')

    diff = cor.subtract_background(data=spec, backp=backp, backm=backm)

    # slit normalization
    refl = cor.divide_intensity(data=diff, base=slits)

    # or load footprint or ab-initio footprint or no footprint
    #no_footprint = One(data=refl.output)
    #fit_footprint = FitFootprint(data=refl.output)
    #calc_footprint = CalcFootprint(data=refl.output)
    #measured_footprint = MeasuredFootprint(data=refl.output)
    #footprint = Select(fit_footprint, calc_footprint,
    #                   measured_footprint, no_footprint)
    #refl = divide(data=refl, base=footprint)

    #cor.save(refl, 'refl')

    import matplotlib.pyplot as plt
    plt.subplot(211)
    plt.hold(True)
    #spec = cor.rescale(spec, 2, 0)
    spec.plot('spec')
    #for d in raw_backp+raw_backm: d.plot()
    backp.plot('backp')
    backm.plot('backm')
    diff.plot('diff')
    refl.plot('refl')
    plt.legend()

    plt.subplot(212)
    for d in raw_slits: d.plot()
    slits.plot()
    plt.legend()
    plt.show()

if __name__ == "__main__":
    demo()
