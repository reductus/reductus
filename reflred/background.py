# This program is public domain
"""
Background subtraction
"""
from __future__ import division

import numpy as np

from dataflow.lib.uncertainty import Uncertainty as U, interp

from .refldata import ReflData

def apply_specular_mask(data):
    theta_i = data.sample.angle_x
    theta_f = 0.5*data.detector.angle_x
    dtheta = 0.1*data.angular_resolution
    not_spec = (abs(theta_f - theta_i) >= dtheta)
    data.mask = not_spec | (True if data.mask is None else data.mask)


def apply_background_subtraction(data, backp, backm):
    assert all((bkg is None or data.normbase == bkg.normbase)
               for bkg in (backp, backm)), "can't mix time and monitor normalized data"
    I, varI = subtract_background(data, backp, backm)
    data.v, data.dv = I, np.sqrt(varI)


def set_background_alignment(back, offset):
    """
    Guess whether background is offset from sample angle or from detector angle.
    """
    if offset is None or offset == 'auto':
        # for auto, if Qz_target is set by the trajectory then use it
        if back.Qz_target is not None and not np.isnan(back.Qz_target).any():
            back.Qz_basis = 'target'
            return
        offset = guess_background_offset(back)

    #A, B, L = back.sample.angle_x, back.detector.angle_x, back.detector.wavelength
    #if offset == 'sample':
        #back.Qz_target = 4*np.pi/L * np.sin(np.radians(A))
    #elif offset == 'detector':
        #back.Qz_target = 4*np.pi/L * np.sin(np.radians(B)/2)
    #else:
        #raise KeyError('unknown offset: must be sample|detector')
    back.Qz_basis = offset


# TODO: should only subtract items with the same angular resolution
def subtract_background(spec, backp, backm):
    # type: (ReflData, ReflData, ReflData) -> (np.ndarray, np.ndarray)
    """
    Subtract back+ and back- from spec.

    if *offset* is 'auto', guess alignment.

    Interpolates background measurements to align with the specular.  If a
    different interpolation is required, then do so before subtract_background
    so that interp does nothing herein.

    Returns I, varI
    """
    #print "%s - (%s+%s)/2"%(spec.name, (backp.name if backp else "none"), (backm.name if backm else "none"))
    spec_v = U(spec.v, spec.dv**2)
    backp_v = U(backp.v, backp.dv**2) if backp else None
    backm_v = U(backm.v, backm.dv**2) if backm else None

    #print "spec",spec_v,spec.v,spec.dv
    #if backp: print "back+",backp_v,backp.v,backp.dv
    #if backm: print "back-",backm_v,backm.v,backm.dv

    backp_v = interp(_ordinate(spec), _ordinate(backp), backp_v) if backp else None
    backm_v = interp(_ordinate(spec), _ordinate(backm), backm_v) if backm else None

    if backp and backm:
        spec_v -= (backp_v + backm_v)/2
    elif backp:
        spec_v -= backp_v
    elif backm:
        spec_v -= backm_v
    else:
        pass  # no background to subtract

    return spec_v.x, spec_v.variance

def _ordinate(data):
    """
    Determine interpolation ordinate for the dataset.  This is Qz for 1-D data
    but theta for n-D data (since Q varies across the detector).
    """
    if data.Qz.ndim == 1:
        return data.Qz
    # This is similar to code in Refldata.Qz ...
    if data.Qz_basis == 'actual':
        return data.sample.angle_x
    if data.Qz_basis == 'target':
        return data.sample.angle_x_target
    if data.Qz_basis == 'detector':
        return data.detector.angle_x/2
    if data.Qz_basis == 'sample':
        return data.sample.angle_x
    raise KeyError("Qz basis must be one of [actual, detector, sample, target]")


def guess_background_offset(back):
    """
    Guess whether background is offset from sample or from detector.

    Note that we can only distinguish relative and constant offsets,
    not  whether it is offset from sample or detector, so we must rely on
    convention. If the offset is constant for each angle, then it is assumed
    to be a sample offset.  If the offset is proportional to the angle (and
    therefore offset/angle is constant), then it is assumed to be a detector
    offset. If neither condition is met, it is assumed to be a sample offset.
    """
    a3 = back.sample.angle_x
    a4 = back.detector.angle_x
    a3_from_a4 = a4/2.
    a4_from_a3 = a3*2.
    a4_from_a3[a4_from_a3 == 0.] = 1e-5  # large number, but not many
    #print "a3",a3
    #print "a3 - a3 from a4",a3 - a3_from_a4
    #print "a4 - a4 from a3",a4 - a4_from_a3
    #print "a4",a4
    #print "a4 from a3",a4_from_a3
    #print "(a4 - a4_from_a3)/a4_from_a3",(a4 - a4_from_a3)/a4_from_a3
    if _check_mostly_constant(a3 - a3_from_a4):
        # A3 absolute offset
        return 'sample'
    #elif _check_mostly_constant((a3 - a3_from_a4)/a3_from_a4):
    #    # A3 relative offset
    #    return 'sample'
    #elif _check_mostly_constant(a4 - a4_from_a3):
    #    # A4 absolute offset
    #    return 'detector'
    elif _check_mostly_constant((a4 - a4_from_a3)/a4_from_a3):
        # A4 relative offset
        return 'detector'
    else:
        return 'sample'


def _check_mostly_constant(v):
    # normalize
    # find median; don't want mean since it is not robust
    med = np.median(v)
    delta = abs(med)*0.05
    # exclude points too far away from central value
    #print med,delta,v
    outliers = np.sum((v < med-delta) | (v > med+delta))
    #print "outliers",outliers
    # if too many points excluded, then reject the "mostly constant" assumption
    return outliers <= len(v)//10


def test_alignment_guess():
    back = ReflData()
    #a3 = np.arange(0.005,3,0.005)
    #a3 = np.arange(0.5,3,0.5)
    a3 = np.arange(-0.5, 6, 0.5)
    a3[1] = 0.
    a4 = 2*a3
    a3err = np.random.uniform(-0.0001, 0.0001, size=a3.size)
    a4err = np.random.uniform(-0.0001, 0.0001, size=a3.size)

    # detector offset
    back.sample.angle_x = a3 + a3err
    back.detector.angle_x = a4 + 0.3 + a4err
    assert guess_background_offset(back) == 'sample', "detector absolute +"
    back.detector.angle_x = a4 - 0.3 + a4err
    assert guess_background_offset(back) == 'sample', "detector absolute -"
    back.detector.angle_x = a4*(1+0.4) + a4err
    assert guess_background_offset(back) == 'detector', "detector relative +"
    back.detector.angle_x = a4*(1-0.4) + a4err
    assert guess_background_offset(back) == 'detector', "detector relative -"

    # sample offset
    back.detector.angle_x = a4 + a4err
    back.sample.angle_x = a3 + 0.3 + a3err
    assert guess_background_offset(back) == 'sample', "sample absolute +"
    back.sample.angle_x = a3 - 0.3 + a3err
    assert guess_background_offset(back) == 'sample', "sample absolute -"
    back.sample.angle_x = a3*(1+0.4) + a3err
    assert guess_background_offset(back) == 'detector', "sample relative +"
    back.sample.angle_x = a3*(1-0.4) + a3err
    assert guess_background_offset(back) == 'detector', "sample relative -"
