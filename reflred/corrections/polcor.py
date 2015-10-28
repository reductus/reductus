"""
Polarized data corrections

Polarized neutron measurements select a particular neutron spin state
for the incident and reflected neutrons.  Experiments which probe the
interaction between spin state and sample must first determine the
efficiency with which each spin state can be selected and apply that
effect to the data before presenting it to the user.[1]

The way that spin states are selected will vary between instruments.
Some instruments will have a polarizing supermirror+flipper
arrangement, with the mirror either transmitting or reflecting
a particular polarization state, and a magnetic field tuned to
flip the polarization state when a current is applied or otherwise
leave it in the selected state.  TOF sources will require a
time-varying field to adjust for the different transit times
for different wavelengths through the flipper field.  He3 polarizers
can select spin up or spin down for transmission and so do not
require a flipper.  In any case, the efficiency will vary with
Q, either due to increased divergence or wavelength dependence.


1.  Prepare the intensity data
===============================

To perform a polarization data reduction you must first have measured
beam data under different polarization conditions::

    pp spin up incident, spin up reflected
    pm spin up incident, spin down measured
    mp spin down incident, spin up measured
    mm spin down incident, spin down measured

These data are passed into the correction using a PolarizedData container::

    I = PolarizedData()
    I.xlabel, P.xunits = 'Slit 1', 'mm'   # On TOF, maybe 'wavelength','nm'
    I.ylabel, P.yunits = 'Intensity', 'counts'
    I.pp.set(x=Spp, y=Ipp, variance=Ipp)
    I.pm.set(x=Spm, y=Ipm, variance=Ipm)
    I.mp.set(x=Smp, y=Imp, variance=Imp)
    I.mm.set(x=Smm, y=Imm, variance=Imm)

The intensities given should be 1-dimensional.  For 1D and 2D detectors, the
integrated beam image should be used.  Time-of-flight data will be
organized by time channel while monochromatic data is organized by slit
opening.  Any ordering will do so long as the intensity is well behaved
between points.

We will assume the correction is uniform across the detector since it
is impractical to measure the efficiency as a function of position.
In fact the slightly different path lengths for the various positions
on the detector will lead to a decrease in efficiency as you move away
from the center of the beam, and so it may have a subtle influence on
off-specular polarized reflectometry.

The different cross sections must have corresponding ordinate axes.  On TOF
machines this will usually not be a problem since all time channels are
measured simultaneously.  On scanning instruments, there are a variety
of factors which may result in points that don't correspond well, such
as user error, or undersampling in the spin-flip cross sections.

Even if the data are already aligned across the four cross sections,
it is still desirable to smooth the polarized data prior to estimating
because the efficiency estimate is unstable.

Use alignment or smoothing corrections to make your data regular::

    I.apply(align)    # use linear interpolation to regrid the data
    I.apply(smooth)   # a weighted irregular Savitsky-Golay filter


2. Compute polarization efficiencies
====================================

The polarization efficiency correction is controlled by the
PolarizationEfficiency class::

    eff = PolarizationEfficiency(I)

Once the class is constructed and the resulting efficiency attributes
are available::

    eff.fp front polarizer efficiency
    eff.ff front flipper efficiency
    eff.rp rear polarizer efficiency
    eff.rf rear flipper efficiency
    eff.Ic overall beam intensity

The formalism from Majkrzak, et al. (see attached PDF) defines the
following, which are attributes to the efficiency object::

    eff.F = fp
    eff.R = rp
    eff.x = 1 - 2*ff
    eff.y = 1 - 2*rf
    eff.beta = Ic/2

There are a few attributes of the class that will change how the
efficiencies are calculated::

    eff.min_intensity = 1e-2
    eff.min_efficiency = 0.7
    eff.FRbalance = 0.5

FRbalance determines the relative front-back weighting of the
polarization efficiency.  From the data we can only estimate the
product FR of the front and rear polarization efficiencies, and
the user must decide how to distribute the remainder.
The FRbalance should vary between 0 (front polarizer is 100% efficient)
through 0.5 (distribute inefficiency equally) to 1 (rear polarizer
is 100% efficient).  The particular formula used is::

     F = (F*R)^FRbalance
     R = (F*R)/F

The min_intensity and min_efficiency numbers are used to bound
the range of the correction.  Normally you won't need to set
them.  These are class attributes, so you can set them globally
in PolarizationEfficiency instead of eff, but still override
them for particular instances by setting them in eff.


3. Apply the correction to the data
===================================

You must first prepare your data for the polarization correction by
placing it in a PolarizedData container, and possibly subtracting
the background measurements (the polarization correction is linear so it
doesn't matter mathematically if background subtraction happens before
or after the polarization correction, but the polarization correction
is slow enough that it should probably only be done once).

Once again the measurements need to be aligned, but in this case
smoothing should not be used.  The data will need to be normalized
to the same monitor as the intensity measurement before adding them
to the container.

For scanning instruments, the data will need to retain the slit
settings used for the measurement so that the correct intensity
measurement can be used for the correction.


TODO: create a complete data reduction doc including footprint, etc.
TODO: use array masks to identify interpolated data.
TODO: incorporate time for He3 polarizer
TODO: extend to 1D and 2D detectors
TODO: cross check results against Asterix algorithm
TODO: implement alignment and smoothing
TODO: consider applying the efficiency correction to the theory rather than
the data --- if the inversion is unstable, this may be more reliable.
TODO: with both spin up and spin down neutrons in sample simultaneously
in some proportion, do the cross sections need to be coherently to account
for the theory?

[1] C.F. Majkrzak (1996). Physica B 221, 342-356.
"""

import numpy as np

# reflred.uncertainty is fast but overestimates the error for the highly
# correlated polarization efficiency estimate.  The uncertainties package
# from pypi is slow, and does an excellent job of matching monte carlo
# estimates of polarization efficiency.

#from ..uncertainty import Uncertainty
#def U(x,dx): return Uncertainty(x,dx**2)
#def nominal_values(u): return u.x
#def std_devs(u): return u.dx
from uncertainties.unumpy import uarray as U, matrix as UM, nominal_values, std_devs

from ..pipeline import Correction
from ..wsolve import wsolve
from ..refldata import Intent

from . import util

class PolarizationCorrection(Correction):
    """
    Compute polarizer and flipper efficiencies from the intensity data.

    If clip is true, reject points above or below particular efficiencies.
    The minimum intensity is 1e-10.  The minimum efficiency is 0.9.

    The computed values are systematically related to the efficiencies:
      beta: intensity/2
      fp: front polarizer efficiency is F
      rp: rear polarizer efficiency is R
      ff: front flipper efficiency is (1-x)/2
      rf: rear flipper efficiency is (1-y)/2
    reject is the indices of points which are clipped because they
    are below the minimum efficiency or intensity.

    See PolarizationEfficiency.pdf for details on the calculation.
    """
    parameters = [
        ["FRbalance", 0.5, "",
         "front/rear balance of to use for efficiency loss."],
        ["min_efficiency", 0, "",
         "Minimum efficiency cutoff"],
        ["min_intensity", 0, "",
         "Minimum intensity cutoff"],
        ["spinflip", True, "",
         "Correct spinflip data if available"],
        ["clip", False, "",
         "Clip efficiency between minimum and one"],
    ]
    def apply_list(self, datasets):
        """Apply the correction to the data"""
        groups = util.group_by_intent(datasets)
        beam = groups.pop(Intent.slit,None)
        if beam is None:
            # return datasets
            raise ValueError("Need beam intensity measurements to perform polarization correction")

        datasets = []
        for intent,data in groups.items():
            if any(test(intent) for test in (Intent.isspec,Intent.isrock,Intent.isback)):
                correct(beam, data, Emin=self.min_efficiency,
                        Imin = self.min_intensity, FRbal=self.FRbalance,
                        spinflip=self.spinflip, clip=self.clip)
            datasets.extend(v for _,v in sorted(data.items()))

        return datasets

ALL_XS = '++','+-','-+','--'
NSF_XS = '++','--'

def correct(beam, data, Emin=0, Imin=0, FRbal=0.5, spinflip=True, clip=False):
    spinflip = spinflip and '+-' in data and '-+' in data
    dtheta = data['++'].angular_resolution
    beta,fp,rp,x,y,mask =  _calc_efficiency(beam=beam, dtheta=dtheta, FRbal=FRbal,
                                      Imin=Imin, Emin=Emin, clip=clip)

    Hinv = _correction_matrix(beta, fp, rp, x, y, spinflip)
    _apply_correction(dtheta, Hinv, data, spinflip)

def _apply_correction(dtheta, Hinv, data, spinflip=True):
    """Apply the efficiency correction in eff to the data."""

    # Get the intensities from the datasets
    # TODO: need to interpolate data so that it aligns with ++
    # If smoothing is desired, apply the smoothing before calling polcor
    parts = (ALL_XS if spinflip else NSF_XS)
    Y = np.vstack([U(data[xs].v, data[xs].dv) for xs in parts])

    # Look up correction matrix for each point using the ++ cross section
    index = util.nearest(data['++'].angular_resolution, dtheta)

    # Apply the correction at each point
    X, dX = np.zeros(Y.shape), np.zeros(Y.shape)
    for i,idx in enumerate(index):
        x = Hinv[idx] * UM(Y[:,i]).T
        X[:,i], dX[:,i] = nominal_values(x).flat, std_devs(x).flat

    # Put the corrected intensities back into the datasets
    for i, xs in enumerate(parts):
        data[xs].v, data[xs].dv = X[i,:], dX[i,:]
        data[xs].vlabel = 'Reflectivity'
        data[xs].vunits = None


def _correction_matrix(beta, fp, rp, x, y, spinflip):
    """
    Generate polarization correction matrices for each slit configuration *dT*.
    """
    Fp,Fm = 1+fp, 1-fp
    Rp,Rm = 1+rp, 1-rp
    Fp_x,Fm_x = 1+fp*x, 1-fp*x
    Rp_y,Rm_y = 1+rp*y, 1-rp*y

    if spinflip:
        H = np.array([
            [Fp * Rp, Fp_x * Rp, Fp * Rp_y, Fp_x * Rp_y],
            [Fm * Rp, Fm_x * Rp, Fm * Rp_y, Fm_x * Rp_y],
            [Fp * Rm, Fp_x * Rm, Fp * Rm_y, Fp_x * Rm_y],
            [Fm * Rm, Fm_x * Rm, Fm * Rm_y, Fm_x * Rm_y],
            ])
    else:
        H = np.array([
            [Fp * Rp, Fp_x*Rp_y],
            [Fm * Rm, Fm_x*Rm_y],
            ])
    return [UM(H[:,:,k]*Bk).I for k,Bk in enumerate(beta)]

def plot_efficiency(beam, Imin=0, Emin=0, FRbal=0.5, clip=False):
    from ..corrections import normalize
    eff = polarization_efficiency(beam, Imin=Imin, Emin=Emin, FRbal=FRbal, clip=clip)
    from matplotlib import pyplot as plt
    ax1 = plt.subplot(211)
    for xs in ALL_XS: beam[xs].plot()
    _ploteff(eff, 'beta')
    plt.legend()
    plt.setp(ax1.get_xticklabels(), visible=False)
    plt.xlabel('')

    ax2 = plt.subplot(212, sharex=ax1)
    for part in ('ff', 'rf', 'fp', 'rp'):
        _ploteff(eff, part)
    plt.grid(True)
    plt.legend()
    plt.ylabel("efficiency (%)")
    #plt.xlabel('angular resolution (degrees FWHM)')
    plt.xlabel('slit 1 opening (mm)')


EFF_LABELS = {'ff':'front flipper','rf':'rear flipper',
              'fp':'front polarizer','rp':'rear polarizer'}
EFF_SCALES = {'ff':100, 'rf':100, 'fp':100, 'rp':100}
EFF_COLORS = {'ff':'green', 'rf':'blue', 'fp':'cyan', 'rp':'purple'}
def _ploteff(eff, part):
    from matplotlib import pyplot as plt
    label = EFF_LABELS.get(part, part)
    scale = EFF_SCALES.get(part, 1.0)
    color = EFF_COLORS.get(part, 'black')
    x,mask = eff['slit1'], eff['mask']
    y, dy = scale*nominal_values(eff[part]), scale*std_devs(eff[part])
    plt.errorbar(x, y, dy, fmt='.', color=color, label=label, capsize=0, hold=True)
    #print "mask",mask
    #if np.any(mask):
        #plt.errorbar(x[mask], y[mask], dy[mask],
        #             fmt='.', color='red', label='_', capsize=0, hold=True)
        #plt.plot(x[mask], y[mask], '.', color='red', hold=True)
        #plt.vlines(x[mask], (y-dy)[mask], (y+dy)[mask], colors='red', hold=True)



def polarization_efficiency(beam, Imin=0, Emin=0, FRbal=0.5, clip=False):
    """
    Compute polarization and flipper efficiencies from the intensity data.

    *beam* is the measured beam intensity as a dict with entries for
    ++, +-, -+, and --.

    *FRbalance* is the  portion of efficiency assigned to front versus rear

    *clip* [True|False] force efficiencies below 100%

    If clip is true, constrain points between the minimum efficiency and one,
    and intensity above minimum intensity.

    The computed values are systematically related to the efficiencies:

    Ic: intensity is 2*beta
    fp: front polarizer efficiency is F
    rp: rear polarizer efficiency is R
    ff: front flipper efficiency is (1-x)/2
    rf: rear flipper efficiency is (1-y)/2
    mask: true if point was clipped.

    See PolarizationEfficiency.pdf for details on the calculation.
    """
    # Assume the '++' cross section exists and completely covers the
    # resolution range
    dtheta = beam['++'].angular_resolution
    s1 = beam['++'].slit1.x
    beta,fp,rp,x,y,mask = \
        _calc_efficiency(beam=beam, dtheta=dtheta, FRbal=FRbal, Imin=Imin, Emin=Emin, clip=clip)
    ff,rf = (1-x)/2, (1-y)/2
    return dict(dtheta=dtheta,slit1=s1,beta=beta,ff=ff,rf=rf,fp=fp,rp=rp,mask=mask)

def _calc_efficiency(beam, dtheta, FRbal, Imin, Emin, clip):
    # Beam intensity.
    # NOTE: A:mm, B:pm, C:mp, D:mm
    pp,pm,mp,mm = [_interp_intensity(dtheta, beam[xs]) for xs in ALL_XS]

    Ic = ((mm*pp) - (pm*mp)) / ((mm+pp) - (pm+mp))
    reject = (Ic!=Ic)  # Reject nothing initially
    if clip:
        reject |= _clip_data(Ic, Imin, np.inf)
    beta = Ic/2


    # F and R are the front and rear polarizer efficiencies.  Each
    # is limited below by min_efficiency and above by 1 (since they
    # are not neutron sources).  Keep a list of points that are
    # rejected because they are outside this range.
    FR = mm/Ic - 1
    if clip:
        reject |= _clip_data(FR, Emin**2, 1)
    fp = FR ** FRbal
    rp = FR / fp

    # f and r are the front and rear flipper efficiencies.  Each
    # is again limited below by min_efficiency and above by 1.
    # We don't compute f and r directly, but instead x, y, Fx and Fy:
    #    x = 1-2f => f=(1-x)/2
    #    y = 1-2r => r=(1-y)/2
    x = (pm/Ic - 1)/FR
    y = (mp/Ic - 1)/FR

    # Clip the f,r flipper efficiencies to [min. efficiency, 1] by clipping
    # x,y to [-1, 1-2*min. efficiency]
    if clip:
        reject |= _clip_data(x, -1, 1-2*Emin)
        reject |= _clip_data(y, -1, 1-2*Emin)

    return beta, fp, rp, x, y, reject

def _interp_intensity(dT, data):
    #return util.nearest(dT, data.angular_resolution, U(data.v, data.dv))
    return util.interp(dT, data.angular_resolution, U(data.v, data.dv))

# Different versions of clip depending on which uncertainty package is used.
def clip_no_error(field,low,high,nanval=0.):
    idx = np.isnan(field); field[idx] = nanval; reject = idx
    idx = field<low;       field[idx] = low;    reject |= idx
    idx = field>high;      field[idx] = high;   reject |= idx
    return reject

def clip_reflred_err1d(field,low,high,nanval=0.):
    idx = np.isnan(field.x); field[idx] = U(nanval,field.variance[idx]); reject = idx
    idx = field.x<low;  field[idx] = U(low,field.variance[idx]);  reject |= idx
    idx = field.x>high; field[idx] = U(high,field.variance[idx]); reject |= idx
    return reject

def clip_pypi_uncertainties(field,low,high,nanval=0.):
    # Move value to the limit without changing the correlated errors.
    # This is probably wrong, but it is less wrong than other straight forward
    # options, such setting x to the limit with zero uncertainty.  At least
    # the clipped points will be flagged.
    from uncertainties import unumpy as unp
    idx=np.isnan(nominal_values(field)); field[idx]=[v+(nanval-v.n) for v in field[idx]]; reject=idx
    idx=field<low;  field[idx]=[v+(low-v.n)  for v in field[idx]]; reject |= idx
    idx=field>high; field[idx]=[v-(v.n-high) for v in field[idx]]; reject |= idx
    return reject


if 'Uncertainty' in globals():
    _clip_data = clip_reflred_err1d
else:
    _clip_data = clip_pypi_uncertainties
_clip_data.__doc__ =  """
    Clip the values to the range, returning the indices of the values
    which were clipped.  Note that this modifies field in place. NaN
    values are clipped to the nanval default.
    """

def demo():
    import pylab
    from ..examples import ng1p as group
    #from ..examples import ng1pnxs as group
    from ..corrections import join, smooth_slits
    from .util import plot_sa

    raw_slit,spec,back = [d|join(tolerance=0.01)
                          for d in group.slit(), group.spec(), group.back()]
    slit = raw_slit | smooth_slits(degree=2,span=45,dx=0.001)
    corrected = (spec+slit) | PolarizationCorrection()

    #pylab.subplot(211); [d.plot() for d in raw_slit]
    #pylab.subplot(212); [d.plot() for d in slit]
    #pylab.suptitle('slit intensities')

    pylab.figure()
    plot_efficiency(dict((d.polarization,d) for d in raw_slit),clip=False)
    pylab.suptitle("raw polarization correction")


    pylab.figure()
    plot_efficiency(dict((d.polarization,d) for d in slit),clip=False)
    pylab.suptitle("smoothed polarization correction")

    pylab.figure()
    pylab.subplot(211)
    for d in spec: d.plot()
    #plot_sa(spec)
    pylab.legend()
    pylab.title("Before polarization correction")
    pylab.subplot(212)
    for d in corrected: d.plot()
    #plot_sa(data)
    pylab.legend()
    pylab.title("After polarization correction")
    pylab.show()


if __name__ == "__main__":
    demo()
