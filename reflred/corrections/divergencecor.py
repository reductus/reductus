import numpy as np

from ..pipeline import Correction

class AngularResolution(Correction):
    """
    Calculate the angular resolution for each data point given the slit
    geometry.
    """
    # no parameters
    def apply(self, data):
        slits = data.slit1.x, data.slit2.x
        distance = abs(data.slit1.distance), abs(data.slit2.distance)
        theta = data.sample.angle_x
        sample_width = data.sample.width
        dtheta = divergence(theta=theta, slits=slits, distance=distance,
                            sample_width=sample_width)
        data.angular_resolution = dtheta


def divergence(theta=None, slits=None, distance=None, sample_width=1e10):
    r"""
    Calculate divergence due to slit and sample geometry.

    :Parameters:
        *theta*     : float OR [float] | degrees
            incident angles
        *slits*     : (float,float) | mm
            s1,s2 slit openings for slit 1 and slit 2
        *distance*  : (float,float) | mm
            d1,d2 distance from sample to slit 1 and slit 2
        *sample_width*      : float | mm
            w, width of the sample

    :Returns:
        *dtheta*  : float OR [float] | degrees FWHM
            calculated angular divergence

    **Algorithm:**

    The divergence is based on the slit openings and the distance between
    the slits.  For very small samples, where the slit opening is larger
    than the width of the sample across the beam, the sample itself acts
    like the second slit.

    First find $p$, the projection of the beam on the sample:

    .. math::

        p &= w \sin\left(\frac{\pi}{180}\theta\right)

    Depending on whether $p$ is larger than $s_2$, determine the slit
    divergence $\Delta\theta_d$ in radians:

    .. math::

        \Delta\theta_d &= \left\{
          \begin{array}{ll}
            \frac{1}{2}\frac{s_1+s_2}{d_1-d_2} & \mbox{if } p \geq s_2 \\
            \frac{1}{2}\frac{s_1+p}{d_1}       & \mbox{if } p < s_2
          \end{array}
        \right.

    In addition to the slit divergence, we need to add in any sample
    broadening $\Delta\theta_s$ returning the total divergence in degrees:

    .. math::

        \Delta\theta &= \frac{180}{\pi} \Delta\theta_d + \Delta\theta_s

    Reversing this equation, the sample broadening contribution can
    be measured from the full width at half maximum of the rocking
    curve, $B$, measured in degrees at a particular angle and slit
    opening:

    .. math::

        \Delta\theta_s = B - \frac{180}{\pi}\Delta\theta_d
    """
    # TODO: check that the formula is correct for theta=0 => dtheta = s1 / d1
    # TODO: add sample_offset and compute full footprint
    d1, d2 = distance
    s1, s2 = slits

    # Compute FWHM angular divergence dtheta from the slits in degrees
    dtheta = np.degrees(0.5*(s1+s2)/(d1-d2))

    # For small samples, use the sample projection instead.
    if np.isfinite(sample_width):
        sample_s = sample_width * np.sin(np.radians(theta))
        if np.isscalar(sample_s):
            if sample_s < s2:
                dtheta = np.degrees(0.5*(s1+sample_s)/d1)
        else:
            #print s1,s2,d1,d2,theta,dtheta,sample_s
            s1 = np.ones_like(sample_s)*s1
            dtheta = np.ones_like(sample_s)*dtheta
            idx = sample_s < s2
            dtheta[idx] = np.degrees(0.5*(s1[idx] + sample_s[idx])/d1)

    return dtheta