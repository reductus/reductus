# This program is public domain
"""
RatioIntensity estimates an intensity scan based on the measured
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

Example::

    # Compute the intensity scan assuming that data measures
    # the specular reflection off 85% water, 15% deuterated water.
    data.apply(WaterIntensity(D2O=15))

"""
from __future__ import with_statement

from ..pipeline import Correction
from ..fresnel import Fresnel

__all__ = ['RatioIntensity', 'WaterIntensity']

class RatioIntensity(Correction):
    """
    Compute the incident intensity assuming that data measures a
    reflection off known sample.

    model is a refl1d model

    Returns a correction object that can be applied to data.
    """
    parameters = [
        ['model', None, '', 'Refl1D model to normalize by'],
    ]

    def apply(self, data):
        intensity_ratio(data=data,model=self.model)

class WaterIntensity(Correction):
    """
    Compute the incident intensity assuming that data measures a
    reflection off water substrate.

    D2O_percent = percentage is the portion that is deuterated, from 0 to 100.

    Returns a correction object that can be applied to data.
    """

    parameters = [
        ['D2O_percent', 0, '%', 'D2O/H2O ratio in solvent, from 0 to 100'],
        ['interface', 3, 'Ang', 'Interfacial rougnhess on the water surface'],
    ]

    # TODO: allow background, intensity
    # TODO: allow different substrate
    def _water_rho(self, probe):
        # SLDs calculated with NBCU.XLS from the NCNR website.
        if probe == 'neutron':
            rho_H2O,irho_H2O = -0.560, 0.001
            rho_D2O,irho_D2O = 5.756, 0.00
        elif probe == 'xray': # 1.54 A
            rho_H2O,irho_H2O = 9.466, 0.098
            rho_D2O,irho_D2O = 8.516, 0.089
        else:
            raise ValueError, "water_ratio needs probe 'neutron' or 'xray'"
        p = 0.01*self.D2O_percent
        rho = 1e-6*((1-p)*rho_H2O + p*rho_D2O)
        irho = 1e-6*((1-p)*irho_H2O + p*irho_D2O)
        return rho, irho

    def apply(self,data):
        rho,irho = self._water_rho(data.probe)
        model = Fresnel(rho=rho, irho=irho, sigma=self.interface)
        intensity_ratio(data=data,model=model)

def intensity_ratio(data=None,model=None):
    """
    Compute the incident intensity assuming that data measures a
    reflection off the given model.

    Returns a copy of the dataset that can be subsequently written
    to a data file for use in reflpak or other reduction software.
    """

    # computing the data/theory ratio
    # TODO: use resolution info in water ratio
    if True:
        R = model.reflectivity(data.Qz, data.detector.wavelength)
    else:
        from refl1d.reflectivity import convolve
        Qi = model.fitQ(data.Qz, data.dQ)
        Ri = model.reflectivity(Qi, data.detector.wavelength)
        R = convolve(Qi, Ri, data.Qz, data.dQ)

    data.R, data.dR = data.R/R, data.dR/R
    data.intent = 'intensity'
    return

def demo():
    import pylab
    from . import normalize
    from ..examples import ng7 as dataset
    spec = dataset.spec()[0] | normalize()
    water = WaterIntensity(D2O_percent=20)
    theory = water.model(spec.Qz,spec.detector.wavelength)

    pylab.subplot(211)
    pylab.title('Data normalized to water scattering (%g%% D2O)'%water.D2O)
    pylab.xlabel('Qz (inv Ang)')
    pylab.ylabel('Reflectivity')
    pylab.semilogy(spec.Qz,theory,'-',label='expected')
    scale = theory[0]/spec.R[0]
    pylab.errorbar(spec.Qz,scale*spec.R,scale*spec.dR,fmt='.',label='measured')

    spec |= water
    pylab.subplot(212)
    #pylab.title('Intensity correction factor')
    pylab.xlabel('Slit 1 opening (mm)')
    pylab.ylabel('Incident intensity')
    pylab.yscale('log')
    pylab.errorbar(spec.slit1.x,spec.R,spec.dR,fmt='.',label='correction')

    pylab.show()

if __name__ == "__main__":
    demo()
