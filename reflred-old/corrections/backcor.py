# This program is public domain
"""
Rescale dataset.
"""
from __future__ import division

import numpy as np

from ..pipeline import Correction
from ..refldata import Intent
from ..uncertainty import Uncertainty as U, interp
from .util import group_by_xs

AUTO_OFFSET = 'auto'
SAMPLE_OFFSET = 'sample angle'
DETECTOR_OFFSET = 'detector angle'

class Background(Correction):
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

    The *align_with* flag determines which background points are matched
    to the sample points.  It can be 'sample angle' if background is
    measured using an offset from the sample angle, or 'detector angle'
    if it is offset from detector angle.   If *align_with* is 'auto', then
    we guess whether it is a offset from sample or detector.

    For 'auto' alignment, we can only distinguish relative and constant offsets,
    not  whether it is offset from sample or detector, so we must rely on
    convention. If the offset is constant for each angle, then it is assumed
    to be a sample offset.  If the offset is proportional to the angle (and
    therefore offset/angle is constant), then it is assumed to be a detector
    offset. If neither condition is met, it is  assumed to be a sample offset.

    The 'auto' test is robust: 90% of the points should be within 5% of the
    median value of the vector for the offset to be considered a constant.
    """
    parameters = [
        ["align_with", AUTO_OFFSET, "",
         "One of %r, %r or %r"%(SAMPLE_OFFSET, DETECTOR_OFFSET, AUTO_OFFSET)],
    ]

    def apply_list(self, datasets):
        cross_sections = group_by_xs(datasets)
        for _, measurements in cross_sections.items():
            subtract_background(measurements, self.align_with)
        #print cross_sections
        return [data
                for xs in cross_sections.values()
                for _,data in sorted((d.intent,d) for d in xs.values())
               ]


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
        spec.formula = "(%s - <%s,%s>)"%(spec.formula, backp.formula, backm.formula)
    elif backp:
        spec_v -= backp_v
        spec.formula = "(%s - %s)"%(spec.formula, backp.formula,)
    else:
        spec_v -= backm_v
        spec.formula = "(%s - %s)"%(spec.formula, backm.formula,)

    spec.v = spec_v.x
    spec.dv = spec_v.dx
    return spec


def guess_alignment(back):
    """
    Guess whether background is offset from sample angle or from detector angle.
    """
    if back.background_offset:
        return back.background_offset
    a3 = back.sample.angle_x
    a4 = back.detector.angle_x
    a3_from_a4 = a4/2
    a4_from_a3 = a3*2
    #print "a3",a3
    #print "a3 - a3 from a4",a3 - a3_from_a4
    #print "a4 - a4 from a3",a4 - a4_from_a3
    #print "a4",a4
    #print "(a4 - a4_from_a3)/a4_from_a3",(a4 - a4_from_a3)/a4_from_a3
    if _check_mostly_constant(a3 - a3_from_a4):
        # A3 absolute offset
        return SAMPLE_OFFSET
    #elif _check_mostly_constant((a3 - a3_from_a4)/a3_from_a4):
    #    # A3 relative offset
    #    return SAMPLE_OFFSET
    #elif _check_mostly_constant(a4 - a4_from_a3):
    #    # A4 absolute offset
    #    return DETECTOR_OFFSET
    elif _check_mostly_constant((a4 - a4_from_a3)/a4_from_a3):
        # A4 relative offset
        return DETECTOR_OFFSET
    else:
        return SAMPLE_OFFSET


def _check_mostly_constant(v):
    # normalize
    # find median; don't want mean since it is not robust
    med = np.median(v)
    delta = abs(med)*0.05
    # exclude points too far away from central value
    #print med,delta,v
    outliers = np.sum((v<med-delta)|(v>med+delta))
    #print "outliers",outliers
    # if too many points excluded, then reject the "mostly constant" assumption
    return outliers <= len(v)//10


def test_alignment_guess():
    from ..refldata import ReflData
    back = ReflData()
    #a3 = np.arange(0.005,3,0.005)
    a3 = np.arange(0.5,3,0.5)
    a4 = 2*a3
    a3err = np.random.uniform(-0.0001,0.0001, size=a3.size)
    a4err = np.random.uniform(-0.0001,0.0001, size=a3.size)

    # detector offset
    back.sample.angle_x = a3 + a3err
    back.detector.angle_x = a4 + 0.3 + a4err
    assert guess_alignment(back) == SAMPLE_OFFSET, "detector absolute +"
    back.detector.angle_x = a4 - 0.3 + a4err
    assert guess_alignment(back) == SAMPLE_OFFSET, "detector absolute -"
    back.detector.angle_x = a4*(1+0.4) + a4err
    assert guess_alignment(back) == DETECTOR_OFFSET, "detector relative +"
    back.detector.angle_x = a4*(1-0.4) + a4err
    assert guess_alignment(back) == DETECTOR_OFFSET, "detector relative -"

    # sample offset
    back.detector.angle_x = a4 + a4err
    back.sample.angle_x = a3 + 0.3 + a3err
    assert guess_alignment(back) == SAMPLE_OFFSET, "sample absolute +"
    back.sample.angle_x = a3 - 0.3 + a3err
    assert guess_alignment(back) == SAMPLE_OFFSET, "sample absolute -"
    back.sample.angle_x = a3*(1+0.4) + a3err
    assert guess_alignment(back) == DETECTOR_OFFSET, "sample relative +"
    back.sample.angle_x = a3*(1-0.4) + a3err
    assert guess_alignment(back) == DETECTOR_OFFSET, "sample relative -"

def demo():
    import pylab
    from ..examples import ng1p as group
    from .. import corrections as cor
    datasets = group.spec()+group.back()
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
    for data in subtracted: print data.formula+data.polarization
    pylab.legend()
    pylab.show()

if __name__ == "__main__":
    demo()
