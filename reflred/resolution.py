r"""
Resolution calculations
"""

import numpy as np
from numpy import pi, sqrt, log, degrees, radians, cos, sin, tan
from numpy import arcsin as asin, ceil
from numpy import ones_like, arange, isscalar, asarray, hstack

from . import util


def QL2T(Q=None, L=None):
    r"""
    Compute angle from $Q$ (|1/Ang|) and wavelength (|Ang|).

    .. math::

        \theta = \sin^{-1}( |Q| \lambda / 4 \pi )

    Returns $\theta$\ |deg|.
    """
    Q, L = asarray(Q, 'd'), asarray(L, 'd')
    return degrees(asin(abs(Q) * L / (4*pi)))


def TL2Q(T=None, L=None):
    r"""
    Compute $Q$ from angle (|deg|) and wavelength $L$ (|Ang|).

    .. math::

        Q = 4 \pi \sin(\theta) / \lambda

    Returns $Q$ |1/Ang|
    """
    T, L = radians(asarray(T, 'd')), asarray(L, 'd')
    return 4 * pi * sin(T) / L


_FWHM_scale = 2*sqrt(2*log(2))
def FWHM2sigma(s):
    return s/_FWHM_scale


def sigma2FWHM(s):
    return s*_FWHM_scale


def calc_Qx(Ti, Td, Li, Ld):
    # type: (np.ndarray, np.ndarray, np.ndarray) -> (np.ndarray, np.ndarray)
    ki, kf = 2*pi/Li, 2*pi/Ld
    Qx = ki*cos(radians(Td - Ti)) - kf*cos(radians(-Ti))
    return Qx


def calc_Qz(Ti, Td, Li, Ld):
    ki, kf = 2*pi/Li, 2*pi/Ld
    Qz = ki*sin(radians(Td - Ti)) - kf*sin(radians(-Ti))
    return Qz


def TiTdL2Qxz(Ti, Td, L):
    # type: (np.ndarray, np.ndarray, np.ndarray) -> (np.ndarray, np.ndarray)
    Qx = 2*pi/L * (cos(radians(Td - Ti)) - cos(radians(Ti)))
    Qz = 2*pi/L * (sin(radians(Td - Ti)) + sin(radians(Ti)))
    return Qx, Qz


def dTdL2dQ(T=None, dT=None, L=None, dL=None):
    # type: (np.ndarray, np.ndarray, np.ndarray, np.ndarray) -> np.ndarray
    r"""
    Convert wavelength dispersion and angular divergence to $Q$ resolution.

    *T*, *dT*  (|deg|) angle and 1-\ $\sigma$ angular divergence
    *L*, *dL*  (|Ang|) wavelength and 1-\ $\sigma$ wavelength dispersion

    Returns 1-\ $\sigma$ $\Delta Q$

    Given $Q = 4 \pi sin(\theta)/\lambda$, this follows directly from
    gaussian error propagation using

    ..math::

        \Delta Q^2
            &= \left(\frac{\partial Q}{\partial \lambda}\right)^2\Delta\lambda^2
            + \left(\frac{\partial Q}{\partial \theta}\right)^2\Delta\theta^2

            &= Q^2 \left(\frac{\Delta \lambda}{\lambda}\right)^2
            + Q^2 \left(\frac{\Delta \theta}{\tan \theta}\right)^2

            &= Q^2 \left(\frac{\Delta \lambda}{\lambda}\right)^2
            + \left(\frac{4\pi\cos\theta\,\Delta\theta}{\lambda}\right)^2

    with the final form chosen to avoid cancellation at $Q=0$.
    """

    # Compute dQ from wavelength dispersion (dL) and angular divergence (dT)
    T, dT = radians(asarray(T, 'd')), radians(asarray(dT, 'd'))
    L, dL = asarray(L, 'd'), asarray(dL, 'd')
    #print T, dT, L, dL
    dQ = (4*pi/L) * sqrt((sin(T)*dL/L)**2 + (cos(T)*dT)**2)

    #sqrt((dL/L)**2+(radians(dT)/tan(radians(T)))**2)*probe.Q
    return dQ


def dQ_broadening(dQ, L, T, dT, width):
    r"""
    Broaden an existing dQ by the given divergence.

    *dQ* |1/Ang|, with 1-\ $\sigma$ $Q$ resolution
    *L* |Ang|
    *T*, *dT* |deg|, with 1-\ $\sigma$ angular divergence
    *width* |deg|, with 1-\ $\sigma$ increased angular divergence

    The calculation is derived by substituting
    $\Delta\theta' = \Delta\theta + \omega$ for sample broadening $\omega$.
    """
    T, dT = radians(asarray(T, 'd')), radians(asarray(dT, 'd'))
    width = radians(width)
    dQsq = dQ**2 + (4*pi/L*cos(T))**2*(2*width*dT + width**2)

    return sqrt(dQsq)


def dQdT2dLoL(Q, dQ, T, dT):
    r"""
    Convert a calculated Q resolution and angular divergence to a
    wavelength dispersion.

    *Q*, *dQ* |1/Ang|, with 1-\ $\sigma$ $Q$ resolution
    *T*, *dT* |deg|, with 1-\ $\sigma$ angular divergence

    Returns 1-\ $\sigma$ $\Delta\lambda/\lambda$
    """
    T, dT = radians(asarray(T, 'd')), radians(asarray(dT, 'd'))
    Q, dQ = asarray(Q, 'd'), asarray(dQ, 'd')
    return sqrt((dQ/Q)**2 - (dT/tan(T))**2)


def dQdL2dT(Q, dQ, L, dL):
    r"""
    Convert a calculated Q resolution and wavelength dispersion to
    angular divergence.

    *Q*, *dQ* |1/Ang|, with 1-\ $\sigma$ $Q$ resolution
    *L*, *dL* |deg|, with 1-\ $\sigma$ angular divergence

    Returns FWHM $\theta, \Delta\theta$
    """
    L, dL = asarray(L, 'd'), asarray(dL, 'd')
    Q, dQ = asarray(Q, 'd'), asarray(dQ, 'd')
    T = QL2T(Q, L)
    dT = degrees(sqrt((dQ/Q)**2 - (dL/L)**2) * tan(radians(T)))
    return dT


Plancks_constant = 6.62618e-27 # Planck constant (erg*sec)
neutron_mass = 1.67495e-24     # neutron mass (g)
def TOF2L(d_moderator, TOF):
    r"""
    Convert neutron time-of-flight to wavelength.

    .. math::

        \lambda = (t/d) (h/n_m)

    where:

        | $\lambda$ is wavelength in |Ang|
        | $t$ is time-of-flight in $u$\s
        | $h$ is Planck's constant in erg seconds
        | $n_m$ is the neutron mass in g
    """
    return TOF*(Plancks_constant/neutron_mass/d_moderator)


def bins(low, high, dLoL):
    r"""
    Return bin centers from low to high preserving a fixed resolution.

    *low*, *high* are the minimum and maximum wavelength.
    *dLoL* is the desired resolution FWHM $\Delta\lambda/\lambda$ for the bins.
    """

    step = 1 + dLoL
    n = ceil(log(high/low)/log(step))
    edges = low*step**arange(n+1)
    L = (edges[:-1]+edges[1:])/2
    return L

def binwidths(L):
    r"""
    Determine the wavelength dispersion from bin centers *L* for time-of-flight
    measurements.

    The wavelength dispersion $\Delta\lambda$ is just the difference
    between consecutive bin edges, so:

    .. math::

        \Delta L_i  = E_{i+1}-E_{i}
                    = (1+\omega) E_i - E_i
                    = \omega E_i
                    = \frac{2 \omega}{2+\omega} L_i

    where $E$ and $\omega$ are as defined in :func:`binedges`.
    """
    if L[1] > L[0]:
        dLoL = L[1]/L[0] - 1
    else:
        dLoL = L[0]/L[1] - 1
    dL = 2*dLoL/(2+dLoL)*L
    return dL

def binedges(L):
    # type: (np.ndarray) -> np.ndarray
    r"""
    Construct bin edges *E* from bin centers *L* for time-of-flight
    measurements.

    Assuming fixed $\omega = \Delta\lambda/\lambda$ in the bins, the
    edges will be spaced logarithmically at:

    .. math::

        E_0     &= \min \lambda \\
        E_{i+1} &= E_i + \omega E_i = E_i (1+\omega)

    with centers $L$ half way between the edges:

    .. math::

        L_i = (E_i+E_{i+1})/2
            = (E_i + E_i (1+\omega))/2
            = E_i (2 + \omega)/2

    Solving for $E_i$, we can recover the edges from the centers:

    .. math::

        E_i = L_i \frac{2}{2+\omega}

    The final edge, $E_{n+1}$, does not have a corresponding center
    $L_{n+1}$ so we must determine it from the previous edge $E_n$:

    .. math::

        E_{n+1} = L_n \frac{2}{2+\omega}(1+\omega)

    The fixed $\omega$ can be retrieved from the ratio of any pair
    of bin centers using:

    .. math::

        \frac{L_{i+1}}{L_i} = \frac{ (E_{i+2}+E_{i+1})/2 }{ (E_{i+1}+E_i)/2 }
                          = \frac{ (E_{i+1}(1+\omega)+E_{i+1} }
                                  { (E_i(1+\omega)+E_i }
                          = \frac{E_{i+1}}{E_i}
                          = \frac{E_i(1+\omega)}{E_i} = 1 + \omega
    """
    if L[1] > L[0]:
        dLoL = L[1]/L[0] - 1.
        last = (1.+dLoL)
    else:
        dLoL = L[0]/L[1] - 1.
        last = 1./(1.+dLoL)
    E = L*(2./(2.+dLoL))
    return hstack((E, E[-1]*last))

def divergence(slits=None, distance=None, T=None,
               sample_width=np.inf, use_sample=True):
    # type: (Sequence[Union[float, np.ndarray], ...], Sequence[float, ...], Optional[np.ndarray], float, bool) -> np.ndarray
    r"""
    Calculate divergence due to slit and sample geometry.

    :Parameters:
        *slits*     : float OR (float, ...) | mm
            s1,s2,s3,s4 slit openings for all available slits
        *distance*  : (float, ...) | mm
            d1,d2,d3,d4 distance to each slit
        *T*         : float OR [float] | |deg|
            incident angles
        *sample_width*      : float | mm
            w, width of the sample
        *use_sample* : bool
            True if sample footprint should be treated as a slit.  If False,
            then incident angle T and sample width are not used.

    :Returns:
        *dT*  : float OR [float] | |deg| 1-\ $\sigma$
            calculated angular divergence

    **Algorithm:**

    The divergence is based on the slit openings and the distance between
    the slits.  For very small samples, where the slit opening is larger
    than the width of the sample across the beam, the sample itself acts
    like the second slit.

    First find $p$, the projection of the beam on the sample:

    .. math::

        p &= w \sin\left(\frac{\pi}{180}\theta\right)

    Define this as slit s0 at distance d0=0.

    Given a set of slit openings $s_i$ with distance from sample $d_i$,
    the $\Delta\theta_d$ full width at half maximum (FWHM) in radians is
    computed as:

    .. math::

        \Delta\theta_d = \min_{i \ne j) \frac{1}{2}\frac{s_i+s_j}{|d_i-d_j|}

    In addition to the slit divergence, we need to add in any sample
    broadening $\Delta\theta_s$ returning the total divergence in degrees:

    .. math::

        \Delta\theta = \frac{180}{\pi} \Delta\theta_d + \Delta\theta_s

    Reversing this equation, the sample broadening contribution can
    be measured from the FWHM of the rocking curve, $B$, measured in
    degrees at a particular angle and slit opening:

    .. math::

        \Delta\theta_s = B - \frac{180}{\pi}\Delta\theta_d

    If any of the slits is not centered or the sample is offset from the
    center of rotation then this calculation will not be correct.

    Depending on the slit openings and distances, the angular distribution
    in the beam from a set of slits will vary from triangular
    ($\sigma^2 = w^2/24$) to uniform ($\sigma^2 = w^2/12) where $w$ is the
    width of the base, as determined by the minimum and maximum achievable
    angles through all the slits. Any slits that are not centered on the
    beam path can introduce a skew in this distribution.

    The algorithm computes the symmetric trapezoidal distribution
    for each pair of slits along the beam path and uses the minimum divergence
    as the divergence of the complete beam.  Monte Carlo simulations show that
    this method underestimates the divergence by up to 30% when slit 1 is
    much more open than slit 2, but handles the other conditions very well.
    Note that the sample itself can act like slit 2 at low angles, as
    can slit 3.

    **TODO**: fix S1 >> S2 condition

    **TODO**: sample footprint not used even when *use_sample* is True
    """
    # Extend all arrays to look like T (for use in candor data)
    slits = [util.extend(s, T) for s in slits]
    distance = [util.extend(d, T) for d in distance]

    # Add sample projection at distance zero
    if False and use_sample and np.isfinite(sample_width):
        sample_projection = sample_width * abs(sin(radians(T)))
        slits = slits + [sample_projection]
        distance = distance + [0.]

    # Compute pair-wise delta-theta
    def _divergence(i, j):
        # Note: divergence_simple below uses (s1 + s2)/|2d| for FWHM. Given
        # s1 = s2, this form returns arctan((s1 + s2)/|2d|)/sqrt(6) 1-sigma.
        # sqrt(6) ~ 2.45 whereas FWHM to 1-sigma conversion ~ 2.35. The arctan
        # makes the values closer still.
        s1, s2, d = slits[i], slits[j], distance[i] - distance[j]
        w, t = np.arctan(abs((s1 + s2)/2/d)), np.arctan(abs((s1 - s2)/2/d))
        return np.sqrt((w**2 + t**2)/6) # 1-sigma radians
    n = len(slits)
    sigma_rad = [_divergence(i, j) for i in range(n) for j in range(i+1, n)]
    ## With four slit pairs plus sample, show whether the sample footprint
    ## is the limiting factor in the divergence. The structure of the
    ## divergence list sigma is as follows:
    ##  [S1:S2 S1:S3 S1:S4 S1:foot S2:S3 S2:S4 S2:foot S3:S4 S3:foot S4:foot]
    #print(f"sample dT = {min(sigma_rad[k].min() for k in (3, 6, 8, 9))},"
    #      f" slit dT = {min(sigma_rad[k].min() for k in (0, 1, 2, 4, 5, 7))}")

    # Find the minimum delta-theta across all pairs
    # Sample slit is one per angle, so some divergence values will be vectors
    sigma_rad = np.asarray(np.broadcast_arrays(*sigma_rad))
    min_sigma_rad = np.min(sigma_rad, axis=0)

    # Convert to 1-sigma distribution in degrees
    return degrees(min_sigma_rad)

def divergence_simple(slits=None, distance=None, T=None,
                      sample_width=np.inf, use_sample=True):
    # TODO: check that the formula is correct for T=0 => dT = s1 / d1
    # TODO: add sample_offset and compute full footprint
    d1, d2 = distance
    try:
        s1, s2 = slits
    except TypeError:
        s1 = s2 = slits

    # Compute FWHM angular divergence dT from the slits in degrees
    dT_s1_s2 = 0.5*(s1+s2)/abs(d1-d2)
    # Sample can act as a slit according to the projection of its width
    if use_sample and np.isfinite(sample_width):
        sample = sample_width * abs(sin(radians(T)))
        dT_s1_sample = 0.5*(s1+sample)/abs(d1)
        dT_s2_sample = 0.5*(s2+sample)/abs(d2)
        dT = np.minimum(dT_s1_s2, np.minimum(dT_s1_sample, dT_s2_sample))
        return FWHM2sigma(degrees(dT))
    else:
        return FWHM2sigma(degrees(dT_s1_s2))


def slit_widths(T=None, slits_at_Tlo=None, Tlo=90, Thi=90,
                slits_below=None, slits_above=None):
    """
    Compute the slit widths for the standard scanning reflectometer
    fixed-opening-fixed geometry.

    :Parameters:
        *T* : [float] | |deg|
            Specular measurement angles.
        *Tlo*, *Thi* : float | |deg|
            Start and end of the opening region.  The default if *Tlo* is
            not specified is to use fixed slits at *slits_below* for all
            angles.
        *slits_below*, *slits_above* : float OR [float,float] | mm
            Slits outside opening region.  The default is to use the
            values of the slits at the ends of the opening region.
        *slits_at_Tlo* : float OR [float,float] | mm
            Slits at the start of the opening region.

    :Returns:
        *s1*, *s2* : [float] | mm
            Slit widths for each theta.

    Slits are assumed to be fixed below angle *Tlo* and above angle *Thi*,
    and opening at a constant dT/T between them.

    Slit openings are defined by a tuple (s1,s2) or constant s=s1=s2.
    With no *Tlo*, the slits are fixed with widths defined by *slits_below*,
    which defaults to *slits_at_Tlo*.  With no *Thi*, slits are continuously
    opening above *Tlo*.

    .. Note::
         This function works equally well if angles are measured in
         radians and/or slits are measured in inches.

    """

    # Slits at T<Tlo
    if slits_below is None:
        slits_below = slits_at_Tlo
    try:
        b1, b2 = slits_below
    except TypeError:
        b1 = b2 = slits_below
    s1 = ones_like(T) * b1
    s2 = ones_like(T) * b2

    # Slits at Tlo<=T<=Thi
    try:
        m1, m2 = slits_at_Tlo
    except TypeError:
        m1 = m2 = slits_at_Tlo
    idx = abs(T) >= Tlo
    s1[idx] = m1 * T[idx]/Tlo
    s2[idx] = m2 * T[idx]/Tlo

    # Slits at T > Thi
    if slits_above is None:
        slits_above = m1 * Thi/Tlo, m2 * Thi/Tlo
    try:
        t1, t2 = slits_above
    except TypeError:
        t1 = t2 = slits_above
    idx = abs(T) > Thi
    s1[idx] = t1
    s2[idx] = t2

    return s1, s2


'''
def resolution(Q=None,s=None,d=None,L=None,dLoL=None,Tlo=None,Thi=None,
               s_below=None, s_above=None,
               broadening=0, sample_width=1e10, sample_distance=0):
    """
    Compute the resolution for Q on scanning reflectometers.

    broadening is the sample warp contribution to angular divergence, as
    measured by a rocking curve.  The value should be w - (s1+s2)/(2*d)
    where w is the full-width at half maximum of the rocking curve.

    For itty-bitty samples, provide a sample width w and sample distance ds
    from slit 2 to the sample.  If s_sample = sin(T)*w is smaller than s2
    for some T, then that will be used for the calculation of dT instead.

    """
    T = QL2T(Q=Q,L=L)
    slits = slit_widths(T=T, s=s, Tlo=Tlo, Thi=Thi)
    dT = divergence(T=T, slits=slits, sample_width=sample_width,
                    sample_distance=sample_distance) + broadening
    Q,dQ = Qresolution(L, dLoL*L, T, dT)
    return FWHM2sigma(dQ)

def demo():
    import pylab
    from numpy import linspace, exp, real, conj, sin, radians
    # Values from volfrac example in garefl
    T = linspace(0,9,140)
    Q = 4*pi*sin(radians(T))/5.0042
    dQ = resolution(Q,s=0.21,Tlo=0.35,d=1890.,L=5.0042,dLoL=0.009)
    #pylab.plot(Q,dQ)

    # Fresnel reflectivity for silicon
    rho,sigma=2.07,5
    kz=Q/2
    f = sqrt(kz**2 - 4*pi*rho*1e-6 + 0j)
    r = (kz-f)/(kz+f)*exp(-2*sigma**2*kz*f)
    r[abs(kz)<1e-10] = -1
    R = real(r*conj(r))
    pylab.errorbar(Q,R,xerr=dQ,fmt=',r',capsize=0)
    pylab.grid(True)
    pylab.semilogy(Q,R,',b')

    pylab.show()

def demo2():
    import pylab
    Q,R,dR = pylab.loadtxt('ga128.refl.mce').T
    dQ = resolution(Q, s=0.154, Tlo=0.36, d=1500., L=4.75, dLoL=0.02)
    pylab.errorbar(Q,R,xerr=dQ,yerr=dR,fmt=',r',capsize=0)
    pylab.grid(True)
    pylab.semilogy(Q,R,',b')
    pylab.show()



if __name__ == "__main__":
    demo2()
'''
