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
==============================

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
from __future__ import print_function, division

import numpy as np

# reflred.uncertainty is fast but overestimates the error for the highly
# correlated polarization efficiency estimate.  The uncertainties package
# from pypi is slow, and does an excellent job of matching monte carlo
# estimates of polarization efficiency.

#from reductus.dataflow.lib.uncertainty import Uncertainty
#def U(x,dx): return Uncertainty(x,dx**2)
#def nominal_values(u): return u.x
#def std_devs(u): return u.dx
from uncertainties.unumpy import uarray as U, nominal_values, std_devs, ulinalg
from uncertainties import ufloat

from reductus.dataflow.lib.errutil import interp

from . import util

# A divergence difference of 5e-5 corresponds to 0.1 mm for 2 m slit separation
ACCEPTABLE_DIVERGENCE_DIFFERENCE = 5e-5

ALL_XS = '++', '+-', '-+', '--'
PM_XS = '++', '+-', '--'
MP_XS = '++', '-+', '--'
NSF_XS = '++', '--'

class PolarizationData:
    def __init__(self, intensity_data, Imin=0.0, Emin=0.0, FRbal=0.5, clip=True):
        self.beam = dict([(d.polarization, d) for d in intensity_data])
        self.FRbal = FRbal
        self.Emin = Emin
        self.Imin = Imin
        self.clip = clip

        self.warnings = []

    def apply(self, data, spinflip=True):
        correct(data, spinflip, self.beam,
                Imin=self.Imin, Emin=self.Emin, FRbal=self.FRbal,
                clip=self.clip)

    def plot(self):
        raise NotImplementedError("see polarization.py for plots we want to create")

    def get_metadata(self):
        eff = polarization_efficiency(self.beam, Imin=self.Imin, Emin=self.Emin,
                                      FRbal=self.FRbal, clip=self.clip)
        output = dict([(k, str(v)) for k, v in eff.items()])
        return output
        
    def get_plottable(self):
        return {"params": self.get_metadata(), "type": "params"}

def apply_polarization_correction(data, polarization, spinflip=True):
    polarization.apply(data, spinflip=spinflip)

def correct(data_in, spinflip, beam, Imin=0.0, Emin=0.0, FRbal=0.5, clip=False):
    dtheta = beam['++'].angular_resolution
    beta, fp, rp, x, y, mask \
        = _calc_efficiency(beam=beam, dtheta=dtheta,
                           Imin=Imin, Emin=Emin, FRbal=FRbal, clip=clip)

    data = dict([(d.polarization, d) for d in data_in])
    use_pm = spinflip and '+-' in data
    use_mp = spinflip and '-+' in data

    Hinv = _correction_matrix(beta, fp, rp, x, y, use_pm, use_mp)
    _apply_correction(data, dtheta, Hinv, use_pm, use_mp)

def _apply_correction(data, dtheta, Hinv, use_pm, use_mp):
    """Apply the efficiency correction in eff to the data."""

    # Identify active cross sections
    if use_pm and use_mp:
        parts = ALL_XS
    elif use_mp:
        parts = MP_XS
    elif use_pm:
        parts = PM_XS
    else:
        parts = NSF_XS

    # TODO: interpolation with mixed resolution
    # Interpolate data so that it aligns with ++.  If smoothing is
    # desired, apply the interpolated smoothing before calling polcor,
    # in which case the interpolation does nothing.
    assert parts[0] == '++'
    x = data['++'].Qz
    y = [U(data['++'].v, data['++'].dv)]
    for p in parts[1:]:
        px = data[p].Qz
        py = U(data[p].v, data[p].dv)
        y.append(interp(x, px, py, left=np.nan, right=np.nan))
    Y = np.vstack(y)
    Y = U(nominal_values(Y), std_devs(Y))

    # Look up correction matrix for each point using the ++ cross section
    correction_index = util.nearest(data['++'].angular_resolution, dtheta)

    # Apply the correction at each point
    X, dX = np.zeros(Y.shape), np.zeros(Y.shape)
    for point, polarization in enumerate(correction_index):
        x = Hinv[polarization] @ Y[:, point].T
        X[:, point], dX[:, point] = nominal_values(x).flat, std_devs(x).flat

    # Put the corrected intensities back into the datasets
    # interpolate back to the original Qz in that dataset:
    for k, xs in enumerate(parts):
        x = data[xs].Qz
        px = data['++'].Qz
        py = U(X[k, :], dX[k, :])
        y = interp(x, px, py, left=np.nan, right=np.nan)
        data[xs].v, data[xs].dv = nominal_values(y), std_devs(y)
        data[xs].vlabel = 'counts per incident count'
        data[xs].vunits = None


def _correction_matrix(beta, fp, rp, x, y, use_pm, use_mp):
    """
    Generate polarization correction matrices for each slit configuration *dT*.
    """
    Fp, Fm = 1+fp, 1-fp
    Rp, Rm = 1+rp, 1-rp
    Fp_x, Fm_x = 1+fp*x, 1-fp*x
    Rp_y, Rm_y = 1+rp*y, 1-rp*y

    # pylint: disable=bad-whitespace
    if use_pm and use_mp:
        H = np.array([
            [Fm_x*Rm_y, Fm_x*Rp_y, Fp_x*Rm_y, Fp_x*Rp_y],
            [Fm_x*Rm  , Fm_x*Rp  , Fp_x*Rm  , Fp_x*Rp  ],
            [Fm  *Rm_y, Fm  *Rp_y, Fp  *Rm_y, Fp  *Rp_y],
            [Fm  *Rm  , Fm  *Rp  , Fp  *Rm  , Fp  *Rp  ],
            ])
    elif use_pm:
        H = np.array([
            [Fm_x*Rm_y, (Fm_x*Rp_y + Fp_x*Rm_y), Fp_x*Rp_y],
            [Fm_x*Rm  , (Fm_x*Rp   + Fp_x*Rm  ), Fp_x*Rp  ],
            [Fm  *Rm  , (Fm  *Rp   + Fp  *Rm  ), Fp  *Rp  ],
        ])
    elif use_mp:
        H = np.array([
            [Fm_x*Rm_y, (Fm_x*Rp_y + Fp_x*Rm_y), Fp_x*Rp_y],
            [Fm  *Rm_y, (Fm  *Rp_y + Fp  *Rm_y), Fp  *Rp_y],
            [Fm  *Rm  , (Fm  *Rp   + Fp  *Rm  ), Fp  *Rp  ],
        ])
    else:
        H = np.array([
            [Fm_x*Rm_y, Fp_x*Rp_y  ],
            [Fm  *Rm  , Fp  *Rp    ],
            ])

    #print("H:", UM(H[:,:,0]), UM(H[:,:,0]).I)
    return [ulinalg.pinv(H[:, :, k]*Bk) for k, Bk in enumerate(beta)]

def plot_efficiency(beam, Imin=0.0, Emin=0.0, FRbal=0.5, clip=False):
    eff = polarization_efficiency(beam, Imin=Imin, Emin=Emin, FRbal=FRbal, clip=clip)
    from matplotlib import pyplot as plt
    ax1 = plt.subplot(211)
    for xs in ALL_XS:
        beam[xs].plot()
    _ploteff(eff, 'beta')
    plt.legend()
    plt.setp(ax1.get_xticklabels(), visible=False)
    plt.xlabel('')

    plt.subplot(212, sharex=ax1)
    for part in ('ff', 'rf', 'fp', 'rp'):
        _ploteff(eff, part)
    plt.grid(True)
    plt.legend()
    plt.ylabel("efficiency (%)")
    #plt.xlabel('angular resolution (degrees 1-sigma)')
    plt.xlabel('slit 1 opening (mm)')


EFF_LABELS = {'ff':'front flipper', 'rf':'rear flipper',
              'fp':'front polarizer', 'rp':'rear polarizer'}
EFF_SCALES = {'ff':100, 'rf':100, 'fp':100, 'rp':100}
EFF_COLORS = {'ff':'green', 'rf':'blue', 'fp':'cyan', 'rp':'purple'}
def _ploteff(eff, part):
    from matplotlib import pyplot as plt
    label = EFF_LABELS.get(part, part)
    scale = EFF_SCALES.get(part, 1.0)
    color = EFF_COLORS.get(part, 'black')
    x, mask = eff['slit1'], eff['mask']
    y, dy = scale*nominal_values(eff[part]), scale*std_devs(eff[part])
    plt.errorbar(x, y, dy, fmt='.', color=color, label=label, capsize=0, hold=True)
    #print "mask",mask
    #if np.any(mask):
        #plt.errorbar(x[mask], y[mask], dy[mask],
        #             fmt='.', color='red', label='_', capsize=0, hold=True)
        #plt.plot(x[mask], y[mask], '.', color='red', hold=True)
        #plt.vlines(x[mask], (y-dy)[mask], (y+dy)[mask], colors='red', hold=True)

def polarization_efficiency(beam, Imin=0.0, Emin=0.0, FRbal=0.5, clip=False):
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
    beta, fp, rp, x, y, mask = \
        _calc_efficiency(beam=beam, dtheta=dtheta, FRbal=FRbal,
                         Imin=Imin, Emin=Emin, clip=clip)
    ff, rf = (1-x)/2, (1-y)/2
    return dict(dtheta=dtheta, slit1=s1, beta=beta,
                ff=ff, rf=rf, fp=fp, rp=rp, mask=mask)

def _calc_efficiency(beam, dtheta, Imin, Emin, FRbal, clip):
    # Beam intensity.
    # NOTE: A:mm, B:pm, C:mp, D:mm
    #pp, pm, mp, mm = [_interp_intensity(dtheta, beam[xs]) for xs in ALL_XS]
    pp, pm, mp, mm = [_nearest_intensity(dtheta, beam[xs]) for xs in ALL_XS]

    Ic = ((mm*pp) - (pm*mp)) / ((mm+pp) - (pm+mp))
    reject = np.zeros_like(Ic, dtype='bool')  # Reject nothing initially
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

def _nearest_intensity(dT, data):
    index = util.nearest(dT, data.angular_resolution)
    if (abs(dT - data.angular_resolution[index]) > ACCEPTABLE_DIVERGENCE_DIFFERENCE).any():
        raise ValueError("polarization cross sections for direct beam are not aligned")
    return U(data.v, data.dv)[index]

def _interp_intensity(dT, data):
    return interp(dT, data.angular_resolution, U(data.v, data.dv))

# Different versions of clip depending on which uncertainty package is used.
def clip_no_error(field, low, high, nanval=0.):
    """
    Clip the values to the range, returning the indices of the values
    which were clipped.  Note that this modifies field in place. nan
    values are clipped to the nanval default.  *field* is a floating
    point array, with no uncertainty.
    """
    index = np.isnan(field)
    field[index] = nanval
    reject = index

    index = field < low
    field[index] = low
    reject |= index

    index = field > high
    field[index] = high
    reject |= index

    return reject


def clip_reflred_err1d(field, low, high, nanval=0.):
    """
    Clip the values to the range, returning the indices of the values
    which were clipped.  Note that this modifies field in place. nan
    values are clipped to the nanval default.

    *field* is dataflow.uncertainty array, whose values retain their
    variance even if they are forced within the bounds.  *low*, *high*
    and *nanval* are floats.
    """
    index = np.isnan(field.x)
    field[index] = U(nanval, field.variance[index])
    reject = index

    index = field.x < low
    field[index] = U(low, field.variance[index])
    reject |= index

    index = field.x > high
    field[index] = U(high, field.variance[index])
    reject |= index

    return reject


def clip_pypi_uncertainties(field, low, high, nanval=0.):
    """
    Clip the values to the range, returning the indices of the values
    which were clipped.  Note that this modifies field in place. nan
    values are clipped to the nanval default.

    *field* is an array from the uncertainties package, whose values retain
    their variance even if they are forced within the bounds.  Clipping is
    performed by subtracting from the uncertain value, which will help
    preserve correlations when performing further operations on the clipped
    values.

    *low*, *high* and *nanval* are floats.
    """
    # Move value to the limit without changing the correlated errors.
    # This is probably wrong, but it is less wrong than other straight forward
    # options, such setting x to the limit with zero uncertainty.  At least
    # the clipped points will be flagged.
    index = np.isnan(nominal_values(field))
    field[index] = [ufloat(nanval, 0.) for v in field[index]]
    reject = index

    index = field < low
    field[index] = [v+(low-v.n) for v in field[index]]
    reject |= index

    index = field > high
    field[index] = [v-(v.n-high) for v in field[index]]
    reject |= index

    return reject


if 'Uncertainty' in globals():
    _clip_data = clip_reflred_err1d
else:
    _clip_data = clip_pypi_uncertainties
