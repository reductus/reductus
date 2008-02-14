# This code is public domain

"""
Pure python Fresnel reflectivity calculator.
"""

from numpy import sqrt, exp, real, conj, pi, log, abs, choose

class Fresnel:
    """
    Function for computing the Fresnel reflectivity for a single interface.
    """
    def __init__(self, rho=1e-6, Vrho=0, mu=0, sigma=0):
        self.rho,self.Vrho,self.mu,self.sigma = rho,Vrho,mu,sigma

    def reflectivity(self, Q, L=1):
        """
        Compute the Fresnel reflectivity at the given Q/wavelength.
        """
        rho_s = self.rho    # substrate density
        rho_v = self.Vrho   # incident medium density
        mu_s = self.mu      # absorption
        sigma = self.sigma  # roughness
        # If Q < 0, then we are going from substrate into incident medium.
        # In that case we must negate the change in scattering length density
        # and ignore the absorption.
        S = 16*pi*(rho_s-rho_v)*choose(Q<0,(-1,1)) \
            + 8j*pi*mu_s/L*choose(Q<0,(0,1))
        Q = abs(Q)
        f = sqrt(Q**2 - S)  # fresnel coefficient
        
        # Compute reflectivity amplitude, with adjustment for roughness
        amp = (Q-f)/(Q+f) * exp(-0.5*self.sigma**2*Q*f)
        # Note: we do not need to check for a divide by zero.
        # Let Qc^2 = 16 pi rho.  Since rho is non-zero then Qc is non-zero.
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
    # Rough silicon with an anomolously large absorbtion
    f = Fresnel(rho=2.07e-6, mu=1e-6, sigma=20)

    import numpy
    import reflectometry.model1d as reflfit
    m = reflfit.Model()
    m.incident('Air',rho=0,mu=0)
    m.interface(sigma=f.sigma)
    m.substrate('Si',rho=f.rho*1e6,mu=f.mu*1e6)

    L = 4.75 # Angstrom
    Q = numpy.linspace(0,0.1,11,'d')
    Rf = f(Q,L)
    Rm = m.reflectivity(Q,L,dz=0.01)
    #print numpy.vstack((Q,Rf,Rm)).T

    # This is failing because reflectometry.model1d is failing; why that
    # is so has not yet been determined.
    relerr = numpy.linalg.norm((Rf-Rm)/Rm)
    assert relerr < 1e-10, "relative error is %g"%relerr

if __name__ == "__main__": test()