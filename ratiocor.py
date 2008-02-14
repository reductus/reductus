# This program is public domain
"""
RatioCorrection estimates an intensity scan based on the measured 
intensity from a known scatterer.

You need to perform this type of scan on reflectometers whose beam 
profile changes as a function of angle, thus making it impossible
to measure the beam intensity directly.

Even with the ratio scan the reduction may need a scaling
step to recover the absolute intensity.

Note that we will assume that slit opening as a function of
angle is identical for the measured intensity and the measured
reflection.

We will also assume that the intensity scan and the measured
reflection are performed on blanks with identical geometery
so the footprint is the same on both.  No footprint correction 
will be required.

Example:

  # Compute the intensity scan assuming that data measures
  # the specular reflection off 85% water, 15% deuterated water.
  data.apply(ratiocor.water_ratio(D2O=15))

"""
# Boilerplate to allow relative imports for apps.
if __name__ == '__main__':
    import os; __path__=[os.path.dirname(os.path.realpath(__file__))]; del os

from math import *
import reflectometry.model1d as reflfit
from .fresnel import Fresnel
import numpy

class RatioCorrection(object):
    model = None
    
    def __init__(self, model):
        self.model = model

    def __call__(self, data):
        intensity_ratio(data=data,model=self.model)
        data.log(str(self))
        return data

    def __str__(self):
        return "RatioCorrection(%s)"%str(model)

class WaterRatio(object):
    """
    Compute the incident intensity assuming that data measures a 
    reflection off water.
    
    D2O = percentage is the portion that is deuterated, from 0 to 100.
    probe = 'neutron' or 'xray'

    Returns a correction object that can be applied to data.    
    """
    def _set_fresnel_coefficients(self):
        # SLDs calculated with NBCU.XLS from the NCNR website.
        if self.probe == 'neutron':
            rho_H2O,mu_H2O = -0.560, 0.001
            rho_D2O,mu_D2O = 5.756, 0.00
        elif self.probe == 'xray':
            rho_H2O,mu_H2O = 9.466, 0.098
            rho_D2O,mu_D2O = 8.516, 0.089
        else:
            raise ValueError, "water_ratio needs probe 'neutron' or 'xray'"
        D2O = self._D2O
        self.model.rho = ((100-D2O)*(rho_H2O) + D2O*rho_H2O)/100.
        self.model.mu = ((100-D2O)*(mu_H2O) + D2O*mu_H2O)/100.
        
    def _setD2O(self, D2O):
        self._D2O = D2O
        self._set_fresnel_coefficients
    def _getD2O(self):
        return self._D2O
    def _setprobe(self,probe):
        self._probe = probe
        self._set_fresnel_coefficients
    def _getprobe(self):
        return self._probe
    D2O = property(_getD2O,_setD2O)
    probe = property(_getprobe,_setprobe)

    def __init__(self,D2O=0,probe=None):
        self.model = Fresnel(sigma=3)
        self._probe = probe
        self._D2O = D2O
        self._set_fresnel_coefficients()

    def __call__(self,data):
        intensity_ratio(data=data,model=self.model)
        data.log(str(self))
        return data

    def __str__(self):
        return "WaterRatio(D2O=%d,probe=%s)"%(self._D2O,self._probe)

def intensity_ratio(data=None,model=None):
    """
    Compute the incident intensity assuming that data measures a 
    reflection off the given model.

    Returns a copy of the dataset that can be subsequently written
    to a data file for use in reflpak or other reduction software.
    """

    # TODO for now we are not using resolution information when
    # computing the data/theory ratio
    Q,L = data.Qz,data.detector.wavelength
    R = model.reflectivity(Q,L)
    data.R, data.dR = data.R/R, data.dR/R
    data.intent = 'intensity'
    return

    # Compute the convolved reflectivity.
    # Find the theory points necessary to compute an accurate estimate of
    # the convolved model without over- or under-sampling.
    Q,dQ,L = data.Qz,data.dQ,data.wavelength
    Qi = model.fitQ(Q,dQ)
    Ri = model.reflectivity(Qi,L)
    R = reflfit.convolve(Qi,Ri,Q,dQ)
    data.R, data.dR = data.R/R, data.dR/R

def demo():
    from .examples import ng7 as dataset
    from .normalize import Normalize
    spec = dataset.spec()[0]
    spec.apply(Normalize())
    spec.apply(WaterRatio(D2O=20,probe=spec.probe))
    print spec

if __name__ == "__main__": demo()
