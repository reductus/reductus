from copy import copy

import numpy as np
from numpy import pi, sqrt, polyval, radians, tan, arctan, inf, sin

from reductus.dataflow.lib.wsolve import wpolyfit
from reductus.dataflow.lib.uncertainty import Uncertainty as U, interp
from .util import extend

class FootprintData(object):
    def __init__(self, p, dp):
        self.p = p
        self.dp = dp
    def get_metadata(self):
        #return {"p": self.p.tolist(), "dp": self.dp.tolist()}
        return {
            "slope": self.p[0],
            "intercept": self.p[1],
            # these next are intentionally different from the names of
            # the inputs fields in the footprint module, so that
            # they don't populate those fields when running manually.
            "slope_fit_error_": self.dp[0],
            "intercept_fit_error": self.dp[1]
        }
    def get_plottable(self):
        return {"params": self.get_metadata(), "type": "params"}

def fit_footprint(data, low, high, kind='line'):
    """
    Fit the footprint using data points over a range.

    Range should be a list of pairs of indices, one per data line that is
    to be simultaneously fitted.
    """
    # Join the ranges from the individual data sets
    x, y, dy = [], [], []
    for data_k in data:
        idx = np.ones_like(data_k.Qz, dtype='bool')
        if low is not None:
            idx = idx & (data_k.Qz >= low)
        if high is not None:
            idx = idx & (data_k.Qz <= high)
        x.append(data_k.Qz[idx])
        y.append(data_k.v[idx])
        dy.append(data_k.dv[idx])

    x = np.hstack(x)
    y = np.hstack(y)
    dy = np.hstack(dy)
    if len(x):
        p, dp = _fit_footprint_data(x, y, dy, kind)
        return FootprintData(p, dp)
    else:
        return None


def fit_footprint_shared_range(data, low, high, kind='line'):
    r"""
    Fit the footprint using data points over a range.

    The fit is restricted to *low <= x <= high*.  *kind* can be 'plateau' if
    the footprint is a constant scale factor, 'slope' if the footprint should
    go through the origin, or 'line' if the footprint is a slope that does
    not go through the origin.

    Note: this algorithm is provided for compatibility with the older reflpak
    program.  New datasets need to include support for overlapping points
    with different $\Delta Q$.
    """
    # Join all the datasets
    x, y, dy = [], [], []
    for d in data:
        x.append(d.Qz)
        y.append(d.v)
        dy.append(d.dv)
    x = np.hstack(x)
    y = np.hstack(y)
    dy = np.hstack(dy)


    if low > high:
        low, high = high, low
    idx = (x >= low) & (x <= high)
    x, y, dy = x[idx], y[idx], dy[idx]
    p, dp = _fit_footprint_data(x, y, dy, kind)
    return FootprintData(p, dp)


def apply_fitted_footprint(data, fitted_footprint, range):
    p, dp = fitted_footprint.p, fitted_footprint.dp
    Qmin, Qmax = range
    if Qmax is None:
        Qmax = data.Qz.max()
    if Qmin is None:
        Qmin = data.Qz.min()
    footprint = _generate_footprint_curve(p, dp, data.Qz, Qmin, Qmax)
    _apply_footprint(data, footprint)


def apply_measured_footprint(data, measured_footprint):
    x = measured_footprint.Qz
    y = U(measured_footprint.v, measured_footprint.dv**2)
    footprint = interp(data.Qz, x, y, left=U(1.0, 0.0), right=U(1.0, 0.0))
    _apply_footprint(data, footprint)


def apply_abinitio_footprint(data, Io, width, offset):
    slit1 = (data.slit1.distance, data.slit1.x, data.slit1.y)
    slit2 = (data.slit2.distance, data.slit2.x, data.slit2.y)
    theta = data.sample.angle_x
    if width is None:
        width = data.sample.width
    if offset is None:
        offset = 0.
    if Io is None:
        Io = 1.
    y = Io * _abinitio_footprint(slit1, slit2, theta, width, offset)
    footprint = U(y, 0.0*y)
    _apply_footprint(data, footprint)


def _apply_footprint(data, footprint):
    refl = U(data.v, data.dv**2)
    # Ignore footprint <= 0
    bad_correction = (footprint.x <= 0.)  # type: np.ndarray
    if bad_correction.any():
        footprint = copy(footprint)
        footprint.x = copy(footprint.x)
        footprint.x[bad_correction] = 1.0
        footprint.variance[bad_correction] = 0.0
    corrected_refl = refl/extend(footprint, refl)
    data.v, data.dv = corrected_refl.x, corrected_refl.dx


def _fit_footprint_data(x, y, dy, kind):
    """
    Fit the footprint from the measurement in *x*, *y*, *dy*.

    The fit is restricted to *low <= x <= high*.  *kind* can be 'plateau' if
    the footprint is a constant scale factor, 'slope' if the footprint should
    go through the origin, or 'line' if the footprint is a slope that does
    not go through the origin.
    """
    if len(x) < 2:
        p, dp = np.array([0., 1.]), np.array([0., 0.])
    elif kind == 'plateau':
        poly = wpolyfit(abs(x), y, dy, degree=0, origin=False)
        p, dp = poly.coeff, poly.std
        p, dp = np.hstack((0, p)), np.hstack((0, dp))
    elif kind == 'slope':
        poly = wpolyfit(abs(x), y, dy, degree=1, origin=True)
        p, dp = poly.coeff, poly.std
    elif kind == 'line':
        poly = wpolyfit(abs(x), y, dy, degree=1, origin=False)
        p, dp = poly.coeff, poly.std
    else:
        raise TypeError('unknown footprint type %r'%kind)
    return p, dp


def _generate_footprint_curve(p, dp, x, xmin, xmax):
    """
    Return the footprint correction for the fitted footprint *p*, *dp*.

    The footprint is calculated at the measured points *x*, and applied
    between *xmin* and *xmax*.
    """
    ## order min and max correctly
    xmin, xmax = abs(xmin), abs(xmax)
    if xmin > xmax:
        xmin, xmax = xmax, xmin

    ## linear between Qmin and Qmax
    y = polyval(p, abs(x))
    var_y = polyval(dp**2, x**2)

    ## ignore values below Qmin
    y[abs(x) < xmin] = 1.
    var_y[abs(x) < xmin] = 0.
    ## stretch Qmax to the end of the range
    y[abs(x) > xmax] = polyval(p, xmax)
    var_y[abs(x) > xmax] = polyval(dp**2, xmax**2)

    return U(y, var_y)


def apply(fp, R):
    """
    Scale refl by footprint, ignoring zeros
    """
    x, y, dy = R
    correction = fp.calc()
    correction += (correction == 0)  # avoid divide by zero errors
    corrected_y = y / correction
    corrected_dy = dy / correction
    return corrected_y, corrected_dy


def _abinitio_footprint(slit1, slit2, theta, width, offset=0.):
    """
    Ab-initio footprint calculation from slits, angles and sample size.

    *slit1*, *slit2* are *(d, x, y)* tuples for the distance between the
    slit and the sample, the width of the slit in the beam direction, and
    the width of the slit perpendicular to the beam. The center of slit 2
    must lie on the line between the center of slit 1 and the center of
    rotation of the sample.  All measurements are in mm, though any unit
    will work so long as all measurements are in the same unit.

    *theta* in degrees is the set of angles at which to compute the footprint.

    *width* is the width of the sample. *offset* is a shift in the center of
    rotation of the sample away from the beam center.  These are in the same
    units as the slits (mm).
    """
    # TODO: implement footprint for circular samples
    # TODO: implement vertical footprint if slit y is not inf

    d1, s1x, s1y = slit1
    d2, s2x, s2y = slit2

    # for some reason, distances are stored in nexus files with float32 precision,
    # causing roundoff errors in this calculation
    if hasattr(d1, 'astype'):
        d1 = d1.astype(np.float64)
    if hasattr(d2, 'astype'):
        d2 = d2.astype(np.float64)

    # use radians internally
    theta = radians(theta)

    #use_y = np.all(np.isfinite(s1y) & np.isfinite(s2y))

    # Projection of the sample to the center of rotation
    p_near = (-width / 2 + offset) * sin(theta)
    p_far = (+width / 2 + offset) * sin(theta)

    # beam profile is a trapezoid, 0 where a neutron entering at -s1/2 just
    # misses s2/2, and 1 where a neutron entering at s1/2 just misses s2/2.
    # With tiny front slits, the projection h2 may land on the other side
    # of the beam center.  In this case the overall instensity is lower, but
    # the trapezoid happens to have the same shape, with the flat region
    # extending from -abs(w2) to abs(w2).  Since we only care about intensity
    # relative to the beam for footprint correction, the scale factor cancels.
    w1 = abs(d1/(d1-d2))*(s1x + s2x) / 2 - s1x / 2
    w2 = abs(-abs(d1/(d1-d2)) * (s1x - s2x) / 2 + s1x / 2)
    w_intensity = w1 + w2
    #if use_y:
    #    h1 = abs(d1/(d1-d2))*(s1y+s2y)/2 - s1y/2
    #    h2 = abs(-abs(d1/(d1-d2))*(s1y-s2y)/2 + s1y/2)
    #    h_intensity = h1 + h2

    # Rectangular distribution
    # Three sections of the trapezoid.  Compute the portion of each section
    # that is to the right of p_near and to the right of p_far.  Total is
    # sum the near minus the sum of the far.
    fp = (_trapezoid_sum_right(p_near, w1, w2)
          - _trapezoid_sum_right(p_far, w1, w2))/w_intensity
    return fp

def _trapezoid_sum_right(p, w1, w2):
    """
    Find the integral from p to inf of the trapezoid defined by w1 and w2.
    """
    slope = 1.0/(w1-w2)
    a = np.maximum(p, -w1) + w1
    b = np.maximum(p, -w2) + w1
    A = 0.5*slope*(b**2-a**2)*(b > a)
    a = np.maximum(p, -w2) + w2
    b = np.maximum(p, w2) + w2
    A += (b-a)*(b > a)
    a = w1 - np.maximum(p, w1)
    b = w1 - np.maximum(p, w2)
    A += 0.5*slope*(b**2-a**2)*(b > a)
    return A


def spill(slit, Qz, wavelength, detector_distance, detector_width, thickness,
          A, B, Io, length, offset):
    """
    The primary beam on the detector is the beam reflected from the
    sample. Beam spill is the portion of the beam which is not
    intercepted by the sample but is still incident on the detector.
    This happens at low angles.  Above the sample this is fairly
    simple, being just that portion which is not reflected.  Below
    the sample there is the effect of the the thickness of the
    sample which shades the beam plus the fact that the detector is
    moving out of the path of the beam. At low angles there will also
    be some beam transmitted through the sample, but this is assumed
    to be orders of magnitude smaller than the direct beam so we can
    safely ignore it.  The final effect is the width of the back
    slits which cuts down the transmitted beam.
    """
    if True:
        raise NotImplementedError()

    # It is too difficult to compute beam spill for now.  Leave this
    # pseudo code around in case we decide to implement it later.
    L1 = length/2. + offset
    L2 = length/2. - offset
    wA = slit * A/2.
    wB = slit * B/2.

    # low: low edge of the sample
    # high: high edge of the sample
    # low2: low edge of the sample bottom
    # high2: max(sample,detector)
    # det: low edge of the detector
    # refl: area of intersection
    # spill_lo: area of spill below
    # spill_hi: area of spill above

    # Algorithm for converting Qx-Qz to alpha-beta:
    #   beta = 2 asin(wavelength/(2 pi) sqrt(Qx^2+Qz^2)/2) * 180/pi
    #        = asin(wavelength sqrt(Qx^2+Qz^2) /(4 pi)) / (pi/360)
    #   theta = atan2(Qx,Qz) * 180/pi
    #   alpha = theta + beta/2
    # Since we are in the specular condition, Qx = 0
    #   Qx = 0 => theta => 0 => alpha = beta/2
    #          => alpha = 2 asin(wavelength sqrt(Qz^2)/(4 pi)) / 2
    #          => alpha = asin (wavelength Qz / 4 pi) in radians
    # Length of intersection d = L sin (alpha)
    #          => d = L sin (asin (wavelength Qz / 4 pi))
    #          => d = L wavelength Qz/(4 pi)
    low = -L2*wavelength * Qz / (4 * pi)
    high = L1*wavelength * Qz / (4 * pi)
    area = integrate(wA, wB, low, high)

    # From trig, the bottom of the detector is located at
    #    d sin T - D/2 cos T
    # where d is the detector distance and D is the detector length.
    # Using cos(asin(x)) = sqrt(1-x^2), this is
    #    d wavelength Qz/4pi - D/2 sqrt(1-(wavelength Qz/4pi)^2)
    det = (detector_distance*wavelength*Qz/(4*pi)
           - detector_width/2 * sqrt(1 - (wavelength*Qz/(4*pi))**2))

    # From trig, the projection of thickness in the plane normal to
    # the beam is
    #    thickness/cos(theta) = thickness/sqrt(1-(wavelength Qz/4 pi)^2)
    # since cos(asin(x)) = sqrt(1-x^2).
    low2 = low - thickness / sqrt(1 - (wavelength*Qz/(4*pi))**2)
    high2 = det*(det >= high) + high*(det < high)
    spill_low = integrate(wA, wB, det, low2)
    spill_high = integrate(wA, wB, high2, wB)

    # Total area of intersection is the sum of the areas of the regions
    # Normalize that by the total area of the beam (A+B)/2
    abfoot_y = 2 * Io * (area + spill_low + spill_high) / (wA+wB)
    return abfoot_y
