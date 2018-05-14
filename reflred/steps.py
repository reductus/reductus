# This program is public domain
import os
import numpy as np
from copy import copy

# TODO: maybe bring back formula to show the math of each step
# TODO: what about polarized data?

# Action names
__all__ = [] # type: List[str]

# Action methods
ALL_ACTIONS = [] # type: List[Callable[Any, Any]]

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
    __all__.append(action.__name__)

    # Sort modules alphabetically
    ALL_ACTIONS.sort(key=lambda action: action.__name__)
    __all__.sort()

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

@module
def ncnr_load(filelist=None):
    """
    Load a list of nexus files from the NCNR data server.

    **Inputs**

    filelist (fileinfo[]): List of files to open.

    **Returns**

    output (refldata[]): All entries of all files in the list.

    2016-06-29 Brian Maranville
    | 2017-08-21 Brian Maranville change to refldata, force cache invalidate
    """
    # NB: Fileinfo is a structure with
    #     { path: "location/on/server", mtime: timestamp }
    from .load import url_load_list
    auto_divergence = True

    datasets = []
    for data in url_load_list(filelist):
        if auto_divergence:
            data = divergence(data)
        datasets.append(data)
    return datasets

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
    #for k, d in enumerate(data):
    #    data.log("data %d:"%k)
    #    data.log(d.messages)
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
    elif dead_time is not None:
        data.log('monitor_dead_time(dead_time)')
        data.log_dependency('dead_time', dead_time)
        apply_monitor_dead_time(data, tau_NP=dead_time.tau_NP,
                                tau_P=dead_time.tau_P)
    elif data.monitor.deadtime is not None and np.isfinite(data.monitor.deadtime).all():
        try:
            tau_NP, tau_P = data.monitor.deadtime
        except Exception:
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

    2016-03-21 Paul Kienzle
    """
    from .deadtime import apply_detector_dead_time

    #data = copy(data)
    #data.detector = copy(data.detector)
    data.log('trying to do detector_dead_time()' + str(data.detector.deadtime))
    if nonparalyzing != 0.0 or paralyzing != 0.0:
        data.log('detector_dead_time(nonparalyzing=%.15g, paralyzing=%.15g)'
                 % (nonparalyzing, paralyzing))
        apply_detector_dead_time(data, tau_NP=nonparalyzing,
                                 tau_P=paralyzing)
    elif dead_time is not None:
        data.log('detector_dead_time(dead_time)')
        data.log_dependency('dead_time', dead_time)
        apply_detector_dead_time(data, tau_NP=dead_time.tau_NP,
                                 tau_P=dead_time.tau_P)
    elif data.detector.deadtime is not None and not np.all(np.isnan(data.detector.deadtime)):
        try:
            tau_NP, tau_P = data.detector.deadtime
        except Exception:
            tau_NP, tau_P = data.detector.deadtime, 0.0
        data.log('detector_dead_time(nonparalyzing=%.15g, paralyzing=%.15g)'
                 % (tau_NP, tau_P))
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
        #print("detector "+str(data.detector.__dict__))
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
def divergence(data, sample_width=None, sample_broadening=0):
    r"""
    Estimate divergence from slit openings.  Does nothing if divergence
    is already defined by the instrument.

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
    """
    from .angles import apply_divergence
    #data = copy(data)
    if data.angular_resolution is None:
        data.log('divergence()')
        apply_divergence(data, sample_width, sample_broadening)
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
    data.log('mask_specular()')
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

    2018-04-30 Brian Maranville
    """
    data = copy(data)
    data.log('mask_points(%r)' % mask_indices)
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
    #data = copy(data)
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

    xs {Cross-section} (opt:++\|--\|+-\|-+\|unpolarized): cross-section to extract

    **Returns**

    output (refldata[]): data matching just that cross-section

    2016-05-05 Brian Maranville
    """
    data = copy(data)
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

    scale (scale*) : amount to scale, one for each dataset

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

    group_by (str) : key by which the files are grouped prior to join

    tolerance(float?:1-sigma<0,inf>) : **deprecated** value for Qtol and dQtol;
    ignored if the value is None or not specified.

    **Returns**

    output (refldata[]) : joined data

    | 2017-02-09 Paul Kienzle: split tolerance into Qtol and dQtol
    | 2017-05-05 Paul Kienzle: consistent sort order for outputs
    | 2017-07-03 Brian Maranville: rearrange to group by Ti, Td before dT, dQ
    | 2018-05-14 Brian Maranville: group by Qx first for all rocking curves
    """
    from .joindata import sort_files, join_datasets
    from .util import group_by_key
    # No copy necessary; join is never in-place.

    if tolerance is not None:
        Q_tolerance = dQ_tolerance = tolerance
    datasets = [v for k, v in sorted(group_by_key(group_by, data).items())]
    output = []
    for group in datasets:
        group = sort_files(group, order)
        result = join_datasets(group, Q_tolerance, dQ_tolerance)

        result.log("join(*data)")
        for i, d in enumerate(group):
            result.log_dependency('data[%d]' % i, d)
        #print "join", result.name, result.v, result.dv
        output.append(result)
    return output

#@module
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
    #data = copy(data)
    # TODO: do we want to log the alignment chosen when alignment is auto?
    # Or do we log the fact that auto alignment was chosen?
    set_background_alignment(data, offset)
    data.log('align_background(%r)'%data.Qz_basis)
    return data


@module
def subtract_background(data, backp, backm, align="none"):
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

    align (opt:none|sample|detector|auto) : apply align_background to
    background inputs with offset='auto'

    **Returns**

    output (refldata) : background subtracted specular data

    2016-03-23 Paul Kienzle
    """
    from .background import apply_background_subtraction

    data = copy(data)
    data.log("background(%s,%s)"
             % ("backp" if backp is not None else "None",
                "backm" if backm is not None else "None"))
    if backp is not None:
        data.log_dependency("back+", backp)
        if align != "none":
            align_background(backp, offset=align)
    if backm is not None:
        data.log_dependency("back-", backm)
        if align != "none":
            align_background(backm, offset=align)
    #print "%s - (%s+%s)/2"%(data.name, (backp.name if backp else "none"), (backm.name if backm else "none"))
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
    if base is not None:
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
def abinitio_footprint(data, Io=1., width=None, offset=0.):
    """
    Apply an *ab initio* footprint correction to the data.

    Footprint is computed from the slits and the sample angle so those must
    be available in the data.  If the data has been stitched to common Q
    from different theta, lambda combinations, then footprint will no
    longer be available.

    **Inputs**

    data (refldata) : uncorrected measurement

    Io (float:): scale factorto account for vertical beam spill

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
    data.log("abinitio_footprint(Io=%s,width=%s,offset=%s)"
             % (str(Io), str(width), str(offset)))
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

    2016-04-29 Paul Kienzle
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
    data = copy(data)
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
    data.log("footprint(p=%s,dp=%s)"
             % (str(fitted_footprint.p), str(fitted_footprint.dp)))
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

    poldata.log("PolarizationData(beam, Imin=%.15g, Emin=%.15g%%, FRbal=%.15g%%, clip=%d)"
                % (Imin, Emin, FRbalance, 0+clip))
    #for xs in ('++','+-','-+','--'):
    #    poldata.log_dependency("beam"+xs, data[xs])
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
    #data.log("correct_polarization(polarization, splinflip=True)")
    #data.log_dependency("polarization", polarization)
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

    base {Normalize by} (opt:auto|monitor|time|power|none)
    : how to convert from counts to count rates

    **Returns**

    output (refldata[]): All entries of all files in the list.

    | 2017-01-13 Brian Maranville
    | 2017-02-15 Paul Kienzle: normalize by time if monitor is not present
    | 2017-08-21 Brian Maranville use fileName from trajectory
    | 2018-05-01 Brian Maranville import temperature metadata
    | 2018-05-07 Brian Maranville detector deadtime correction defaults to True
    | 2018-05-10 Brian Maranville export all columns if intent is scan
    | 2018-05-11 Brian Maranville detector deadtime correction defaults to False
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

    base {Normalize by} (opt:auto|monitor|time|power|none)
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
    mm = [d for d in data if d.polarization == '--'][0]
    pp = [d for d in data if d.polarization == '++'][0]
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
    from dataflow.modules import refl
    TIME_RESOLUTION = 1e-6 # 1 microsecond for NCNR timers.
    
    if base is not None:
        from .scale import calculate_number
        from dataflow.lib import err1d

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
