# This program is public domain
import os
from copy import copy
from warnings import warn

# TODO: maybe bring back formula
# TODO: what about polarized data?


def fit_dead_time(attenuated, unattenuated, source='detector', mode='auto'):
    from .deadtime import fit_dead_time

    data = fit_dead_time(attenuated, unattenuated, source=source, mode=mode)

    data.log("fit_dead_time(attenuated, unattenuated, source=%r, mode=%r)"
             % (source, mode))
    data.log("attenuated:")
    data.log(attenuated.messages)
    data.log("unattenuated:")
    data.log(unattenuated.messages)
    return data


def monitor_dead_time(data, dead_time):
    from .deadtime import apply_monitor_dead_time

    data = copy(data)
    data.monitor = copy(data.monitor)
    data.log('monitor_dead_time(dead_time)')
    data.log_dependency('dead_time', dead_time)
    apply_monitor_dead_time(data, dead_time)
    return data


def detector_dead_time(data, dead_time):
    from .deadtime import apply_detector_dead_time

    data = copy(data)
    data.detector = copy(data.detector)
    data.log('detector_dead_time(dead_time)')
    data.log_dependency('dead_time', dead_time)
    apply_detector_dead_time(data, dead_time)
    return data


def monitor_saturation(data):
    from .deadtime import apply_monitor_saturation
    if getattr(data.monitor, 'saturation', None) is not None:
        data = copy(data)
        data.monitor = copy(data.monitor)
        data.log('monitor_saturation()')
        apply_monitor_saturation(data)
    else:
        warn("no monitor saturation for %r"%data.name)

    return data


def detector_saturation(data):
    from .deadtime import apply_detector_saturation

    data = copy(data)
    data.detector = copy(data.detector)
    data.log('detector_saturation()')
    apply_detector_saturation(data)
    return data


def theta_offset(data, offset):
    from .angles import apply_theta_offset
    data = copy(data)
    data.sample = copy(data.sample)
    data.detector = copy(data.detector)
    data.sample.angle_x = copy(data.sample.angle_x)
    data.detector.angle_x = copy(data.detector.angle_x)
    data.log('theta_offset(%.15g)' % offset)
    apply_theta_offset(data, offset)
    return data


def back_reflection(data):
    """
    Reverse the sense of the reflection angles, making positive angles
    negative and vice versa
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


def absolute_angle(data):
    """
    Assume all reflection is off the top surface, reversing the sense
    of negative angles.
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


def divergence(data):
    from .angles import apply_divergence
    data = copy(data)
    data.log('divergence()')
    apply_divergence(data)
    return data


def mask_specular(data):
    """
    Identify and mask out specular points.

    This defines the *mask* attribute of *data* as including all points that
    are not specular or not previously masked.  The points are not actually
    removed from the data, since this operation is done by *join*.
    """
    from .background import apply_specular_mask
    data = copy(data)
    data.log('mask_specular()')
    apply_specular_mask(data)
    return data


def mark_intent(data, intent):
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
    """
    from .intent import apply_intent
    data = copy(data)
    data.log('mark_intent(%r)' % intent)
    apply_intent(data, intent)
    return data

def normalize(data, base='auto'):
    """
    Estimate the detector count rate.

    *base* can be monitor, time, power, or none for no normalization.
    For example, if base='monitor' then the count rate will be counts
    per monitor count.  Note that operations that combine datasets require
    the same normalization on the points.

    If *bases* is auto then the NORMALIZE_DEFAULT will be chosen.

    When viewing data, you sometimes want to scale it to a nice number
    such that the number of counts displayed for the first point is
    approximately the number of counts on the detector.
    """
    from .scale import apply_norm
    data = copy(data)
    data.log('normalize(base=%r)' % base)
    apply_norm(data, base)
    return data


def rescale(data, scale, dscale):
    from .scale import apply_rescale
    data = copy(data)
    data.log("scale(%.15g,%.15g)" % (scale, dscale))
    apply_rescale(data, scale, dscale)
    return data

def join(datasets, tolerance=0.05, order='file'):
    """
    Join operates on a list of datasets, returning a list with one dataset
    per intent/polarization.  When operating on a single dataset, it joins
    repeated points into single points.

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
    """
    from .joindata import sort_files, join_datasets
    # No copy necessary; join is never in-place.

    datasets = sort_files(datasets, order)
    data = join_datasets(datasets, tolerance)

    data.log("join(*data)")
    for i, d in enumerate(datasets):
        data.log_dependency('data[%d]' % i, d)
    return data

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


def subtract_background(data, backp=None, backm=None):
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


def divide_intensity(data, base):
    from .scale import apply_intensity_norm
    data = copy(data)
    data.log("divide(base)")
    data.log_dependency("base", base)
    apply_intensity_norm(data, base)
    return data


def smooth_slits(datasets, degree=1, span=2, dx=0.01):
    """
    Align slits with a moving window 1-D polynomial least squares filter.

    Updates *slit1.x*, *slit2.x* and *angular_resolution* attributes of the
    slit measurements so they all use a common set of points.

    *degree* is the polynomial degree.

    *span* is the number of consecutive points to use in the fit. Odd
    sized *span* is preferred.  *span* must be larger than *degree*.
    *degree=1* and *span=2* is equivalent to linear interpolation.

    *dx* is the size in mm within which slits can be merged.

    Updates divergence automatically after smoothing.
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


def estimate_polarization(beam, FRbalance=0.5, Emin=0., Imin=0., clip=False):
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

    *beam* direct beam measurement to determine polarization

    *FRbalance* front/rear balance of to use for efficiency loss

    *Emin* Minimum efficiency cutoff

    *Imin* Minimum intensity cutoff

    *spinflip* Correct spinflip data if available

    *clip* Clip efficiency between minimum and one
    """
    from .polarization import PolarizationData

    data = PolarizationData(beam=beam, FRbal=FRbalance,
                            Emin=Emin, Imin=Imin, clip=clip)

    data.log("PolarizationData(beam, Imin=%.15g, Emin=%.15g, FRbal=%.15g, clip=%d)"
             %(Imin, Emin, FRbalance, 0+clip))
    for xs in ('++','+-','-+','--'):
        data.log_dependency("beam"+xs, beam[xs])
    return data


def correct_polarization(data, polarization, spinflip=True):
    """
    *data* polarized data to be corrected

    *polarization* previously measured polarization efficiency
    """
    from .polarization import apply_polarization_correction
    data = copy(data)
    data.log("correct_polarization(polarization, splinflip=True)")
    data.log_dependency("polarization", polarization)
    apply_polarization_correction(data, polarization, spinflip)
    return data


def save(data, ext, path="."):
    filename = os.path.join(path, ".".join((data.name, ext)))
    data.save(filename)


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
        files = [cor.monitor_dead_time(d, monitor_dead_time) for d in files]
        files = [cor.detector_dead_time(d, detector_dead_time) for d in files]
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
