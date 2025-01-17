r"""
Background field subtraction
"""
from __future__ import division

import numpy as np
import scipy.optimize as so
from copy import copy

#from reductus.dataflow.lib.uncertainty import Uncertainty as U, interp
#from .refldata import ReflData

# BackgroundFieldData class returns results of background field fitting

class BackgroundFieldData(object):
    def __init__(self, p, dp2, s, ds2, dsp, chisq):
        self.p = p
        self.dp2 = dp2
        self.s = s
        self.ds2 = ds2
        self.dsp = dsp
        self.chisq = chisq
    def get_metadata(self):
        return {
            "epsD": self.p,
            "epsD_var": self.dp2,
            "scale": self.s,
            "scale_var": self.ds2,
            "scale_epsD_covar": self.dsp,
            "fit_chi-squared": self.chisq
        }
    def get_plottable(self):
        return {"params": self.get_metadata(), "type": "params"}


def background_reservoir(ai, epsD, af, epssi, Fd, scale):
    """
    Calculates background from a reservoir surrounded by Si
    """
    with np.errstate(divide='ignore'):
        A = np.exp(-epsD * (1. / np.sin(ai) + 1. / np.sin(af)))
        res = (1 - A) / (1. + np.sin(ai) / np.sin(af))
        #si = epssi * (Fd * np.sin(af) / np.sin(ai + af)) * (0.5 + 0.5 * A)
        si = epssi * Fd / np.cos(ai) * (0.5 + 0.5 * A)

    # first term is the background value; the second contains intermediates used
    # in the Jacobian function and error calculation
    return scale*(res+si), (A, res, si)

def background_reservoir_jac(ai, epsD, af, epssi, Fd, scale):
    """
    Calculates Jacobian function for background_reservoir with
    parameters (scale, epsD)
    """
    A, res, si = background_reservoir(ai, epsD, af, epssi, Fd, scale)[1]

    with np.errstate(divide='ignore'):
        dA_depsD = -(1. / np.sin(ai) + 1. / np.sin(af)) * A
        dres_depsD = -dA_depsD / (1. + np.sin(ai) / np.sin(af))
        #dsi_depsD = epssi * (Fd * np.sin(af) / np.sin(ai + af)) * (0.5 * dA_depsD)
        dsi_depsD = epssi * Fd / np.cos(ai) * (0.5 * dA_depsD)

    J = np.array([res + si, scale*(dres_depsD + dsi_depsD)])

    return J

def background_reservoir_error(ai, epsD, af, epssi, Fd, scale, pcov):
    """
    Uses covariance matrix of fit result to propagate uncertainty
    """
    J = background_reservoir_jac(ai, epsD, af, epssi, Fd, scale)

    return np.sqrt(np.array([j.T.dot(pcov.dot(j)) for j in J.T]))

def fractional_solid_angle(s4, LS4, L4D, HD):
    """
    Calculates fractional solid angle subtended by a detector
    of height HD located a distance LS4 from the sample, fronted
    by a collimating slit a distance L4D away with width s4. Only
    works if the result is << 1.
    """

    dvert = np.arctan( HD / (LS4 + L4D) )
    dhorz = np.arctan( s4 / LS4 )
    return dvert * dhorz / (4 * np.pi)

def detector_footprint(af, s3, s4, LS3, L34):
    """
    Calculates effective footprint on sample viewed by the detector,
    based on post-sample slit values and the angle between the sample
    and the detector.
    """

    return s3 * LS3 / (L34 * np.sin(af)) * (s4 / s3 + 1. + L34 / LS3)

def fit_background_field(back, epsD0, epssi, fit_scale, scale_value=1.0, LS3=380, LS4=1269, LSD=1675, HD=150, Qcutoff=0.05, maxF=75):
    """
    Performs the fit to the background field.
    """

    ##type: (ReflData) -> (np.ndarray)
    #TODO: Better error handling if slit 4 doesn't exist (currently hardcoded detector size)
    #TODO: Include residuals for inspection (can currently pass both through a subtract module)

    # Initialize variables
    ai = list()
    af = list()
    s3 = list()
    s4 = list()
    v = list()
    dv = list()
    Qz_target = list()

    # Check for slit distances, otherwise use values from data file
    LS3 = back[0].slit3.distance if back[0].slit3.distance is not None else LS3
    LS4 = back[0].slit4.distance if back[0].slit4.distance is not None else LS4
    L4D = LSD - LS4

    # Extract relevant quantities from inputs
    for b in back:
        ai.append(b.sample.angle_x)
        Qz_target.append(b.Qz_target if not np.all(np.isnan(b.Qz_target))
                         else 4*np.pi/b.detector.wavelength*np.sin(np.radians(b.sample.angle_x)))
        af.append(b.detector.angle_x - b.sample.angle_x)
        s3.append(b.slit3.x)
        s4.append(b.slit4.x if not np.all(np.isinf(b.slit4.x)) else 25. * np.ones(b.v.shape))
        v.append(b.v)
        dv.append(b.dv)

    # Concatenate and filter results based on the Qcutoff parameter
    Qz_target = np.concatenate(Qz_target)
    ai = np.radians(np.concatenate(ai))
    af = np.radians(np.concatenate(af))
    crit = (Qz_target > Qcutoff) & (af > 0.)
    ai = ai[crit]
    af = af[crit]
    s3 = np.concatenate(s3)[crit]
    s4 = np.concatenate(s4)[crit]
    v = np.concatenate(v)[crit]
    dv = np.concatenate(dv)[crit]

    # Calculate the detector footprints and use maximum value relative to sample size maxF
    Fd = detector_footprint(af, s3, s4, LS3, LS4 - LS3)
    Fd = np.min((Fd, maxF*np.ones(Fd.shape)), axis=0)

    # Calculate the detector solid angle
    SA = fractional_solid_angle(s4, LS4, L4D, HD)

    # Define fit function and Jacobian
    def minfunc(pars):
        scale, epsD = pars
        res = background_reservoir(ai, epsD, af, epssi, Fd, scale)
        return (res[0] * SA - v)/dv

    def jacfunc(pars):
        scale, epsD = pars
        J = background_reservoir_jac(ai, epsD, af, epssi, Fd, scale)
        return (J*np.tile(SA/dv, (len(pars), 1))).T

    # Condition the fit if the scale factor is not included in the fit, then perform the fit
    if not fit_scale:
        pout, pcov = so.leastsq(
            lambda epsD: minfunc([scale_value, epsD]),
            epsD0,
            Dfun=lambda epsD: jacfunc([1.0, epsD])[:,1],
            full_output=True, ftol=1e-15, xtol=1e-15)[:2]
        lenpout = len(pout)
        pout = np.array([scale_value, pout[0]])
        pcov = np.array([[0.0, 0.0], [0.0, pcov[0][0]]])
    else:
        pout, pcov = so.leastsq(
            minfunc,
            np.array([scale_value, epsD0]),
            Dfun=jacfunc,
            full_output=True, ftol=1e-15, xtol=1e-15)[:2]
        lenpout = len(pout)

    # Calculate fitting error (not used) and chi-squared (only reported)
    perr, chisq = np.sqrt(np.diag(pcov)), np.sum(minfunc(pout)**2) / (len(v) - lenpout)

    # for testing purposes only
    if 0:
        import matplotlib.pyplot as plt
        plt.errorbar(np.arange(len(v)), v, dv, fmt='o')
        res = background_reservoir(ai, pout[1], af, epssi, Fd, pout[0])
        plt.plot(np.arange(len(v)), res[0] * SA)
        plt.show()

    # Create fit data structure
    bff = BackgroundFieldData(pout[1], pcov[1,1], pout[0], pcov[0,0], pcov[0,1], chisq)
    bff.epssi = epssi
    bff.LS3 = LS3
    bff.LS4 = LS4
    bff.L4D = L4D
    bff.HD = HD
    bff.maxF = maxF

    # Create calculated background data for comparison to input background data
    back2 = [copy(b) for b in back]

    for i, b in enumerate(back2):
        ai2 = np.radians(b.sample.angle_x)
        af2 = np.radians(b.detector.angle_x - b.sample.angle_x)
        s32 = b.slit3.x
        s42 = b.slit4.x if not np.all(np.isinf(b.slit4.x)) else 25. * np.ones(b.v.shape)

        # Uncomment following lines if output data should only include the data above Qcutoff
        # Currently all data are calculated

        #Qz_target = b.Qz_target if not np.all(np.isnan(b.Qz_target)) else 4 * np.pi / b.detector.wavelength * np.sin(
        #        np.radians(b.sample.angle_x))
        #crit = (Qz_target > Qcutoff) & (af > 0.)
        #ai2 = ai2[crit]
        #af2 = af2[crit]
        #s32 = s32[crit]
        #s42 = s42[crit]

        Fd2 = detector_footprint(af2, s32, s42, LS3, LS4 - LS3)
        Fd2 = np.min((Fd2, maxF * np.ones(Fd2.shape)), axis=0)
        SA2 = fractional_solid_angle(s42, LS4, L4D, HD)

        bestfit = background_reservoir(ai2, pout[1], af2, epssi, Fd2, pout[0])[0]
        bestfiterr = background_reservoir_error(ai2, pout[1], af2, epssi, Fd2, pout[0], pcov)

        back2[i].v = bestfit * SA2
        back2[i].dv = bestfiterr * SA2

    return bff, back2

def apply_background_field_subtraction(data, epsD, epssi, LS3, LS4, L4D, HD, maxF, scale, pcov):
    """
    Applies background field subtraction to specular data
    """
    for (i,d) in enumerate(data):
        I, varI = subtract_background_field(d, epsD, epssi, LS3, LS4, L4D, HD, maxF, scale, pcov)
        data[i].v, data[i].dv = I, np.sqrt(varI)

def subtract_background_field(d, epsD, epssi, LS3, LS4, L4D, HD, maxF, scale, pcov):
    """
    Subtracts background field from a single specular data set with error propagation
    """
    # TODO: Better error handling if slit 4 doesn't exist (currently hardcoded detector size)
    ai = np.radians(d.sample.angle_x)
    af = np.radians(d.detector.angle_x - d.sample.angle_x)
    s4 = d.slit4.x if not np.all(np.isinf(d.slit4.x)) else 25. * np.ones(d.v.shape)
    Fd = detector_footprint(af, d.slit3.x, s4, LS3, LS4 - LS3)
    Fd = np.min((Fd, maxF * np.ones(Fd.shape)), axis=0)
    SA = fractional_solid_angle(s4, LS4, L4D, HD)

    bkg = background_reservoir(ai, epsD, af, epssi, Fd, scale)[0]*SA
    bkg_err = background_reservoir_error(ai, epsD, af, epssi, Fd, scale, pcov)*SA

    return d.v - bkg, d.dv**2 + bkg_err**2
