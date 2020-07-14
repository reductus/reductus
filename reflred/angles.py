import numpy as np
from .resolution import divergence, divergence_simple

def apply_theta_offset(data, offset):
    data.sample.angle_x += offset
    data.detector.angle_x -= offset


def apply_absolute_angle(data):
    index = (data.sample.angle_x < 0)  # type: np.ndarray
    if np.any(index):
        data.sample.angle_x[index] *= -1.0
        data.detector.angle_x[index] *= -1.0


def apply_back_reflection(data):
    data.sample.angle_x *= -1.0
    data.detector.angle_x *= -1.0


def apply_divergence_simple(data, sample_width):
    # TODO: decide whether we should use Ti or sample.angle internally
    # The difference is that Ti has been shaped to match counts data
    # for a bank of detectors, but sample.angle_x is just the list of
    # sample angles in the scan.

    distance = abs(data.slit1.distance), abs(data.slit2.distance)
    # for slit scans, the sample size and angle are irrelevant and
    # need to be excluded from the calculation of divergence:
    use_sample = data.intent != "intensity"
    if sample_width is None:
        sample_width = data.sample.width

    slits = data.slit1.x, data.slit2.x
    #theta = data.Ti
    theta = data.sample.angle_x
    dtheta = divergence_simple(slits=slits, distance=distance, T=theta,
                               sample_width=sample_width, use_sample=use_sample)
    #print("divergence", theta.shape, dtheta.shape)
    data.angular_resolution = dtheta

def apply_sample_broadening(data, sample_broadening):
    r"""
    Modify angular divergence by a sample broadening (or focussing) amount.

    *sample_broadening* : float | |deg| 1-\ $\sigma$
            Additional divergence caused by sample. This can instead be
            included as a fitting parameter since it simply adds to the
            final $\Delta\theta$

    This makes no attempt to account for beam shadowing by a warped sample at
    really low angles, which will mostly show up as an effective attenuation.
    """
    data.angular_resolution = data.angular_resolution + sample_broadening

def apply_divergence_front_back(data, sample_width):
    """
    Use all four slits when computing divergence.
    """
    # TODO: separate sample_broadening from angular_resolution
    # TODO: decide whether we should use Ti or sample.angle internally
    # The difference is that Ti has been shaped to match counts data
    # for a bank of detectors, but sample.angle_x is just the list of
    # sample angles in the scan.

    slits = data.slit1, data.slit2, data.slit3, data.slit4
    distance = [s.distance for s in slits]
    width = [s.x for s in slits]

    # for slit scans, the sample size and angle are irrelevant and
    # need to be excluded from the calculation of divergence:
    use_sample = data.intent != "intensity"
    if sample_width is None:
        sample_width = data.sample.width

    # Assume Ti = Tf = Td/2
    theta = data.Td/2
    dtheta = divergence(slits=width, distance=distance, T=theta,
                        sample_width=sample_width, use_sample=use_sample)
    #print("divergence", theta.shape, dtheta.shape, dtheta.max())
    data.angular_resolution = dtheta
