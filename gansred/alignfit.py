r"""
Curve fitting operations for alignment
"""
from __future__ import division

import numpy as np
import scipy.optimize as so
from copy import copy

# BaseFitResult class returns results of background field fitting

class BaseFitResult:

    def get_metadata(self):
        return {}
    
    def get_plottable(self):
        return {"params": self.get_metadata(), "type": "params"}

class ErrorFitResult(BaseFitResult):

    def __init__(self, msg):
        self.msg = msg

    def get_metadata(self):
        return {'error message': self.msg}

# ===============

class GaussianBackgroundFitResult(BaseFitResult):

    def __init__(self, chisq, A, sigma, x0, bkg, dA, dsigma, dx0, dbkg):
        self.chisq = chisq
        self.A = A
        self.dA = dA
        self.sigma = sigma
        self.dsigma = dsigma
        self.x0 = x0
        self.dx0 = dx0
        self.bkg = bkg
        self.dbkg = dbkg

    def get_metadata(self):
        return {
            "fit_chi-squared": self.chisq,
            "amplitude": self.A,
            "amplitude error": self.dA,
            "sigma": self.sigma,
            "sigma error": self.dsigma,
            "FWHM": self.sigma * 2.355,
            "FWHM error": self.dsigma * 2.355,
            "center": self.x0,
            "center error": self.dx0,
            "background": self.bkg,
            "background error": self.dbkg
        }

def gaussian_background(x, A, sigma, x0, bkg):
    """
    Calculates Gaussian with background
    """

    with np.errstate(divide='ignore'):
        return A * np.exp(-(x - x0) ** 2 / (2 * sigma ** 2)) + bkg
    
def gaussian_background_jac(x, A, sigma, x0, bkg):

    with np.errstate(divide='ignore'):
        g = np.exp(-(x - x0) ** 2 / (2 * sigma ** 2))
        return np.array([g,
                         A * g * (x - x0) ** 2 / (sigma ** 3),
                         A * g * (x - x0) / (2 * sigma ** 2),
                         np.ones_like(g)])
    
def fit_gaussian_background(rock, A0, sigma0, x00, bkg0):
    v, dv = rock.v, rock.dv
    if rock.intent == 'rock sample':
        x = rock.sample.angle_x
    elif rock.intent == 'rock detector':
        x = rock.detector.angle_x
    elif rock.intent == 'rock chi':
        x = rock.sample.angle_y
    else:
        return ErrorFitResult(msg=f'intent must be either "rock sample" or "rock detector" or "rock chi", actually {rock.intent}'), None

    if A0 is None:
        A0 = max(v)
    
    if sigma0 is None:
        sigma0 = np.sqrt(np.trapezoid(v * x ** 2, x) / np.trapezoid(v, x) - np.trapezoid(v * x, x) ** 2 / np.trapezoid(v, x) ** 2)
    
    if x00 is None:
        x00 = x[np.where(v==max(v))[0][0]]
    
    if bkg0 is None:
        bkg0 = min(v)

    def minfunc(pars):
        res = gaussian_background(x, *pars)
        return (res - v)/dv

    def jacfunc(pars):
        J = gaussian_background_jac(x, *pars)
        return (J*np.tile(1/dv, (len(pars), 1))).T

    print(f'Starting gaussian fit with initial parameters A={A0}, sigma={sigma0}, x0={x00}, bkg={bkg0}')

    pout, pcov, _, msg, ier = so.leastsq(
            minfunc,
            np.array([A0, sigma0, x00, bkg0]),
            Dfun=jacfunc,
            full_output=True, ftol=1e-15, xtol=1e-15)
    
    if ier in [1, 2, 3, 4]:
        # fit successful
        lenpout = len(pout)

        perr, chisq = np.sqrt(np.diag(pcov)), np.sum(minfunc(pout)**2) / (len(x) - lenpout)

        # create fit result data

        rock2 = copy(rock)
        rock2.v = gaussian_background(x, *pout)
        rock2.dv = np.sqrt(np.array([j.T.dot(pcov.dot(j)) for j in jacfunc(pout)]))

        return GaussianBackgroundFitResult(chisq, *pout, *perr), rock2

    else:

        return ErrorFitResult(msg), None

# ===============

class LineXInterceptFitResult(BaseFitResult):

    def __init__(self, chisq, m, x0, dm, dx0):
        self.chisq = chisq
        self.m = m
        self.dm = dm
        self.x0 = x0
        self.dx0 = dx0

    def get_metadata(self):
        return {
            "fit_chi-squared": self.chisq,
            "slope": self.m,
            "slope error": self.dm,
            "xintercept": self.x0,
            "xintercept error": self.dx0
        }

def line_xintercept(x, m, x0):
    """
    Calculates line with x-intercept
    """

    return m * (x - x0)

def line_xintercept_jac(x, m, x0):

    return np.array([x - x0, -m * np.ones_like(x)])

def fit_line_xintercept(slit_align, m0, x00):
    v, dv = slit_align.v, slit_align.dv
    x = None
    if slit_align.intent in ['slit align', 'intensity']:
        for slit in [slit_align.slit1, slit_align.slit2, slit_align.slit3, slit_align.slit4]:
            if any(bool(d) for d in np.diff(v)!=0):
                x = slit.x
                break

        if x is None:
            return ErrorFitResult(msg=f'no slits appear to be scanned'), None
        
    else:
        return ErrorFitResult(msg=f'intent must be "slit align" or "intensity", actually {slit_align.intent}'), None

    if m0 is None:
        m0 = (v[-1] - v[0]) / (x[-1] - x[0])
    
    if x00 is None:
        x00 = x[np.where(abs(v) == min(abs(v)))[0][0]]
    
    def minfunc(pars):
        res = line_xintercept(x, *pars)
        return (res - v)/dv

    def jacfunc(pars):
        J = line_xintercept_jac(x, *pars)
        return (J*np.tile(1/dv, (len(pars), 1))).T

    print(f'Starting linear fit with initial parameters m={m0}, x0={x00}')

    pout, pcov, _, msg, ier = so.leastsq(
            minfunc,
            np.array([m0, x00]),
            Dfun=jacfunc,
            full_output=True, ftol=1e-15, xtol=1e-15)
    
    if ier in [1, 2, 3, 4]:
        # fit successful
        lenpout = len(pout)

        perr, chisq = np.sqrt(np.diag(pcov)), np.sum(minfunc(pout)**2) / (len(x) - lenpout)

        # create fit result data

        slit_align2 = copy(slit_align)
        slit_align2.v = line_xintercept(x, *pout)
        slit_align2.dv = np.sqrt(np.array([j.T.dot(pcov.dot(j)) for j in jacfunc(pout)]))

        return LineXInterceptFitResult(chisq, *pout, *perr), slit_align2

    else:

        return ErrorFitResult(msg), None
