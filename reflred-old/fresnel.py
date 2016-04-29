# This code is public domain

"""
Pure python Fresnel reflectivity calculator.
"""

import numpy as np
from numpy import sqrt, exp, real, conj, pi, abs, choose

class Fresnel(object):
    """
    Function for computing the Fresnel reflectivity for a single interface.

    rho,Vrho
        scattering length density of substrate and vacuum
    irho,Virho
        imaginary SLD of substrate and vacuum (note that we do not correct
        for attenuation of the beam through the incident medium since we
        do not know the path length).
    sigma (angstrom)
        interfacial roughness
    """
    def __init__(self, rho=2.07, irho=0., sigma=0., Vrho=0., Virho=0.):
        self.rho,self.Vrho,self.irho,self.Virho,self.sigma \
            = rho,Vrho,irho,Virho,sigma

    def reflectivity(self, Q):
        # type: (np.ndarray) -> np.ndarray
        """
        Compute the Fresnel reflectivity at the given Q/wavelength.
        """
        # If Q < 0, then we are going from substrate into incident medium.
        # In that case we must negate the change in scattering length density
        # and ignore the absorption.
        contrast = self.rho-self.Vrho
        S = 4.*pi*choose(Q<0, (-contrast+1j*self.Virho, contrast+1j*self.irho))
        kz = abs(Q)/2.  # type: np.ndarray
        f = sqrt(kz**2 - S)  # fresnel coefficient

        # Compute reflectivity amplitude, with adjustment for roughness
        amp = (kz-f)/(kz+f) * exp(-2.*self.sigma**2*kz*f)
        # Note: we do not need to check for a divide by zero.
        # Qc^2 = 16 pi rho.  Since rho is non-zero then Qc is non-zero.
        # For mu = 0:
        # * If |Qz| < Qc then f has an imaginary component, so |Qz|+f != 0.
        # * If |Qz| > Qc then |Qz| > 0 and f > 0, so |Qz|+f != 0.
        # * If |Qz| = Qc then |Qz| != 0 and f = 0, so |Qz|+f != 0.
        # For mu != 0:
        # * f has an imaginary component, so |Q|+f != 0.

        R = real(amp*conj(amp))
        return R

    # Make the reflectivity method the default
    __call__ = reflectivity

def test():
    import warnings
    # TODO: hard-code target output rather than relying on refl1d on the path
    try:
        from refl1d.names import silicon, air, QProbe, Experiment
    except ImportError:
        warnings.warn("Not testing Fresnel since refl1d is not on path")
        return

    # Rough silicon with an anomolously large absorbtion
    fresnel = Fresnel(rho=2.07, irho=0, sigma=20)

    sample =  silicon(0,20) | air
    Q = np.linspace(0, 5, 11)
    probe = QProbe(Q, Q*0.02)
    m = Experiment(sample=sample, probe=probe)
    Rf = fresnel(Q)
    Rm = m.reflectivity()
    #print numpy.vstack((Q,Rf,Rm)).T

    # This is failing because reflectometry.model1d is failing; why that
    # is so has not yet been determined.
    relerr = np.linalg.norm((Rf-Rm)/Rm)
    assert relerr < 1e-10, "relative error is %g"%relerr

if __name__ == "__main__":
    test()
