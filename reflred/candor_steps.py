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
        dc_rate=0.,
        detector_correction=False,
        monitor_correction=False,
        spectral_correction=False,
        intent='auto',
        sample_width=None,
        base='none'):
    r"""
    Load a list of Candor files from the NCNR data server.

    **Inputs**

    filelist (fileinfo[]): List of files to open.

    dc_rate {Dark counts per minute} (float)
    : Number of dark counts to subtract from each detector channel per
    minute of counting time (see Dark Current).

    detector_correction {Apply detector deadtime correction} (bool)
    : If True, use deadtime constants in file to correct detector counts
    (see Detector Dead Time).

    monitor_correction {Apply monitor deadtime correction} (bool)
    : If True, use deadtime constants in file to correct monitor counts
    (see Monitor Dead Time).

    spectral_correction {Apply detector efficiency correction} (bool)
    : If True, scale counts by the detector efficiency calibration given
    in the file (see Spectral Efficiency).

    intent (opt:auto|specular|background+\|background-\|intensity|rock sample|rock detector|rock qx|scan)
    : Measurement intent (specular, background+, background-, slit, rock),
    auto or infer.  If intent is 'scan', then use the first scanned variable.

    sample_width {Sample width (mm)} (float?)
    : Width of the sample along the beam direction in mm, used for
    calculating the effective resolution when the sample is smaller
    than the beam.  Leave blank to use value from data file.

    base {Normalize by} (opt:auto|monitor|time|power|none)
    : How to convert from counts to count rates. Leave this as none if your
    template does normalization after integration (see Normalize).

    **Returns**

    output (candordata[]): All entries of all files in the list.

    | 2020-02-05 Paul Kienzle
    """
    from .load import url_load_list
    from .candor import load_entries

    # Note: candor automatically computes divergence.
    datasets = []
    for data in url_load_list(filelist, loader=load_entries):
        # TODO: drop data rows where fastShutter.openState is 0
        data.Qz_basis = 'target'
        if intent not in (None, 'none', 'auto'):
            data.intent = intent
        if dc_rate > 0.:
            data = dark_current(data, dc_rate)
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

    spectrum (float[]) : override spectrum from data file

    **Returns**

    output (candordata) : scaled data

    | 2020-03-03 Paul Kienzle
    """
    from .candor import NUM_CHANNELS
    # TODO: too many components operating directly on detector counts?
    # TODO: let the user paste their own spectral efficiency, overriding datafile
    # TODO: generalize to detector shapes beyond candor
    #print(data.v.shape, data.detector.efficiency.shape)
    if len(spectrum)%NUM_CHANNELS != 0:
        raise ValueError(f"Vector length {len(spectrum)} must be a multiple of {NUM_CHANNELS}")
    if spectrum:
        spectrum = np.reshape(spectrum, (NUM_CHANNELS, -1)).T[None, :, :]
    else:
        spectrum = data.detector.efficiency
    data = copy(data)
    data.detector = copy(data.detector)
    data.detector.counts = data.detector.counts / spectrum
    data.detector.counts_variance = data.detector.counts_variance / spectrum
    return data

@module("candor")
def dark_current(data, dc_rate=0.):
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

    **Returns**

    output (candordata): Dark current subtracted data.

    | 2020-03-04 Paul Kienzle
    """
    # TODO: no uncertainty propagation
    # TODO: generalize to detector shapes beyond candor
    # TODO: datatype hierarchy: accepts any kind of refldata
    if dc_rate > 0.:
        dc = data.monitor.count_time*(dc_rate/60.)
        data = copy(data)
        data.detector = copy(data.detector)
        data.detector.counts = data.detector.counts - dc[:, None, None]
    return data

@module("candor")
def stitch_intensity(data):
    r"""
    Join the intensity measurements into a single entry.

    **Inputs**

    data (candordata[]) : data to join

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
        if (not isclose(a.slit1.x[-1], b.slit1.x[0], abs_tol=0.001)
            or not isclose(a.slit2.x[-1], b.slit2.x[0], abs_tol=0.001)
            or not isclose(a.slit3.x[-1], b.slit3.x[0], abs_tol=0.001)):
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

    # Force intent to treat this as a slit scan.
    data[0].intent = Intent.slit

    # Use existing join algorithm.
    # TODO: expose join parameters to the user?
    data = join(data)
    return data


@module("candor")
def candor_rebin(data, qmin=None, qmax=None, qstep=0.003):
    r"""
    Join the intensity measurements into a single entry.

    **Inputs**

    data (candordata) : data to join

    qmin (float) : Start of q range, or empty to infer from data

    qmax (float) : End of q range, or empty to infer from data

    qstep (float) : q step size

    **Returns**

    output (refldata) : joined data

    | 2020-03-04 Paul Kienzle
    """
    from .candor import rebin

    if qmin is None:
        qmin = data.Qz.min()

    if qmax is None:
        qmax = data.Qz.max()

    q = np.arange(qmin, qmax, qstep)

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
