# This program is public domain
"""
Rescale dataset.
"""
import numpy as np

from ..pipeline import Correction
from ..refldata import Intent
from ..uncertainty import Uncertainty as U, interp

AUTO_OFFSET = 'auto'
SAMPLE_OFFSET = 'sample angle'
DETECTOR_OFFSET = 'detector angle'

class Background(Correction):
    """
    Adjust Q if there is reason to believe either the detector
    or the sample is rotated.
    """
    properties = ["align_with"]
    """One of %r, %r or %r"""%(SAMPLE_OFFSET, DETECTOR_OFFSET, AUTO_OFFSET)

    def __init__(self, align_with=AUTO_OFFSET):
        self.align_with = align_with

    def apply_list(self, datasets):
        cross_sections = group_by_xs(datasets)
        for _, measurements in cross_sections.items():
            subtract_background(measurements, self.align_with)
        #print cross_sections
        return [data
                for xs in cross_sections.values()
                for _,data in sorted((d.intent,d) for d in xs.values())
               ]

    def __str__(self):
        return "Background(%s)"%(self.align_with)


def group_by_xs(datasets):
    """
    Return datasets grouped by polarization cross section, and by intent within
    each polarization cross section.
    """
    cross_sections = {}
    for data in datasets:
        xs = cross_sections.setdefault(data.polarization,{})
        if data.intent in xs:
            raise ValueError("More than one %r in reduction"%data.intent)
        xs[data.intent] = data

    #print "datasets",[":".join((d.name,d.entry,d.polarization,d.intent)) for d in datasets]
    #print "xs",cross_sections
    return cross_sections


def subtract_background(measurements, align_with):
    """
    Subtract back+ and back- from spec.

    back+ and back- are removed from the list of measurements.

    if spec is not present, do nothing.

    Returns updated specular.
    """
    # remove back+, and back- from the set of measurements
    backp = measurements.pop(Intent.backp, None)
    backm = measurements.pop(Intent.backm, None)
    spec = measurements.get(Intent.spec, None)

    if not spec or not (backp or backm):
        # Nothing to do if no spec or no background
        return spec

    spec_v = U(spec.v, spec.dv**2)
    backp_v = U(backp.v, backp.dv**2) if backp else None
    backm_v = U(backm.v, backm.dv**2) if backm else None

    if align_with == AUTO_OFFSET:
        align_with = guess_alignment(backp) if backp else guess_alignment(backm)
        #print "align with",align_with

    if align_with == SAMPLE_OFFSET:
        x = spec.sample.angle_x
        backp_v = interp(x, backp.sample.angle_x, backp_v) if backp else None
        backm_v = interp(x, backm.sample.angle_x, backm_v) if backm else None
    elif align_with == DETECTOR_OFFSET:
        x = spec.detector.angle_x
        backp_v = interp(x, backp.detector.angle_x, backp_v) if backp else None
        backm_v = interp(x, backm.detector.angle_x, backm_v) if backm else None
    else:
        raise ValueError("Unknown alignment %r in background subtraction"%align_with)

    #print "+",backp
    #print "-",backm
    if backp and backm:
        spec_v -= (backp_v + backm_v)/2
    elif backp:
        spec_v -= backp_v
    else:
        spec_v -= backm_v

    spec.v = spec_v.x
    spec.dv = spec_v.dx
    return spec


def guess_alignment(back):
    a3 = back.sample.angle_x
    a4 = back.detector.angle_x
    a3_from_a4 = a4/2
    a4_from_a3 = 2*a3
    dT = 0.1*back.angular_resolution
    if _check_mostly_constant(a3 - a3_from_a4, dT):
        # A3 absolute offset
        return SAMPLE_OFFSET
    elif _check_mostly_constant(a3 - a3_from_a4, dT*a3_from_a4):
        # A3 relative offset
        return SAMPLE_OFFSET
    elif _check_mostly_constant(a4 - a4_from_a3, dT):
        # A4 absolute offset
        return DETECTOR_OFFSET
    elif _check_mostly_constant(a4 - a4_from_a3, dT*a4_from_a3):
        # A4 relative offset
        return DETECTOR_OFFSET
    else:
        return SAMPLE_OFFSET


def _check_mostly_constant(v, dv):
    # normalize
    v = v/dv
    # find median; don't want mean since it is not robust
    med = np.median(v)
    # exclude points too far away from central value
    outliers = np.sum((v<med-1)|(v>med+1))
    # if too many points excluded, then reject the "mostly constant" assumption
    return outliers <= len(v)//10



def demo():
    import pylab
    from os.path import join as joinpath
    from ..examples import get_data_path
    from .. import formats
    from .. import corrections as cor
    path = get_data_path('ng1p')
    base = "jd901_2"
    files = [joinpath(path, "%s%03d.n%sd"%(base,seq,xs))
             for seq in (706,707,708,709,710,711)
             for xs in 'abcd']#'abcd']
    datasets = [formats.load(name)[0] for name in files]
    #for d in datasets: print d.name,d.entry,d.intent
    #print datasets[0]; return
    #print datasets[0].detector.counts
    datasets = datasets | cor.join()
    subtracted = datasets | cor.background()

    #for data in datasets: print data.intent
    pylab.hold(True)
    pylab.subplot(211)
    for data in datasets: data.plot()
    pylab.legend()

    #for data in subtracted: print data.intent
    pylab.subplot(212)
    for data in subtracted: data.plot()
    pylab.legend()
    pylab.show()

if __name__ == "__main__":
    demo()
