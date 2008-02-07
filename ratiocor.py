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

from math import *
import reflectometry.model1d as reflfit
import reflectometry.reduction as reflred

class RatioCorrection(object):
    model = None
    name = None
    
    def __init__(self, model, name=None):
        if name: self.name = name
        self.model = model
        
    def __call__(self, data):
        intensity_ratio(data=data,model=self.model)
        return data
    
    def __str__(self):
        return self.name if name else "RatioCorrection"

def water_ratio(D2O=0,**kw):
    """
    Compute the incident intensity assuming that data measures a 
    reflection off water.
    
    D2O = percentage is the portion that is deuterated, from 0 to 100.

    Returns a correction object that can be applied to data.    
    """
    # SLDs calculated with NBCU.XLS from the NCNR website.
    if data.radiation == 'neutron':
        rho_H2O,mu_H2O = -0.560, 0.001
        rho_D2O,mu_D2O = 5.756, 0.00
    else:
        rho_H2O,mu_H2O = 9.466, 0.098
        rho_D2O,mu_D2O = 8.516, 0.089
    rho = ((100-D2O)*(rho_H2O) + D2O*rho_H2O)/100.
    mu = ((100-D2O)*(mu_H2O) + D2O*mu_H2O)/100.
    m = reflfit.Model()
    m.incident('Air')
    m.interface(sigma=3)
    m.substrate('water', rho=rho, mu=mu)
    name = "RatioCorrection(water,D2O=%d)"%D2O
    return RatioCorrection(m, name)
    
def intensity_ratio(data=data,model=model):
    """
    Compute the incident intensity assuming that data measures a 
    reflection off the given model.
    
    Returns a copy of the dataset that can be subsequently written
    to a data file for use in reflpak or other reduction software.
    """
    Q,dQ,L = data.Q,data.dQ,data.wavelength

    # Compute the convolved reflectivity.
    # Find the theory points necessary to compute an accurate estimate of
    # the convolved model without over- or under-sampling.
    Qi = model.resample_Q(Q,dQ)
    Ri = model.reflectivity(Qi,L)
    R = reflfit.convolve(Qi,Ri,Q,dQ)
    data.R, data.dR = data.R/R, data.dR/R
