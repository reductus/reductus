"""
Polarized data corrections

Polarized neutron measurements select a particular neutron spin state
for the incident and reflected neutrons.  Experiments which probe the
interaction between spin state and sample must first determine the
efficiency with which each spin state can be selected and apply that
effect to the data before presenting it to the user.

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
beam data under different polarization conditions:

    pp spin up incident, spin up reflected
    pm spin up incident, spin down measured
    mp spin down incident, spin up measured
    mm spin down incident, spin down measured

These data are passed into the correction using a PolarizedData container:

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

Use alignment or smoothing corrections to make your data regular:

    I.apply(align)    # use linear interpolation to regrid the data
    I.apply(smooth)   # a weighted irregular Savitsky-Golay filter


2. Compute polarization efficiencies
====================================

The polarization efficiency correction is controlled by the
PolarizationEfficiency class:

    eff = PolarizationEfficiency(I)

Once the class is constructed and the resulting efficiency attributes
are available:

    eff.fp front polarizer efficiency
    eff.ff front flipper efficiency
    eff.rp rear polarizer efficiency
    eff.rf rear flipper efficiency
    eff.Ic overall beam intensity

The formalism from Majkrzak, et al. (see attached PDF) defines the
following, which are attributes to the efficiency object:

    eff.F = fp
    eff.R = rp
    eff.x = 1 - 2*ff
    eff.y = 1 - 2*rf
    eff.beta = Ic/2

There are a few attributes of the class that will change how the
efficiencies are calculated:

    eff.min_intensity = 1e-2
    eff.min_efficiency = 0.7
    eff.FRbalance = 0.5

FRbalance determines the relative front-back weighting of the
polarization efficiency.  From the data we can only estimate the
product FR of the front and rear polarization efficiencies, and
the user must decide how to distribute the remainder.
The FRbalance should vary between 0 (front polarizer is 100% efficient)
through 0.5 (distribute inefficiency equally) to 1 (rear polarizer
is 100% efficient).  The particular formula used is:

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


"""

import numpy as N
from reflectometry.reduction.data import PolarizedData
from reflectometry.reduction.wsolve import wsolve


class PolarizationEfficiency(object):
    """
    Polarization efficiency correction object.  Create a correction object
    from a polarized direct beam measurement and apply it to measured data.

    E.g.,
        eff = PolarizationEfficiency(beam)
        data.apply(eff)

    """

    properties = ['FRbalance','min_efficiency','min_intensity']
    min_efficiency = 0.7
    min_intensity = 1e-2
    _beam = PolarizedData()
    _FRbalance = 0.5


    # Define the correction parameters
    def _getbeam(self): return self._beam
    def _setbeam(self, beam):
        if not beam.isaligned():
            raise ValueError, "polarization efficiency correction needs aligned intensity measurements"
        self._beam = beam
        self._compute_efficiency()
    beam = property(_getbeam,_setbeam,
                    doc="measured beam intensity")

    def _getFRbalance(self): return self._FRbalance
    def _setFRbalance(self,val):
        if val > 1: val = 1
        elif val < 0: val = 0
        self._FRbalance = val
        self._compute_efficiency()
    FRbalance = property(_getFRbalance,_setFRbalance,
                         doc="relative balance of front to back efficiency")

    @property
    def x(self): return (1-2*self.ff)
    @property
    def y(self): return (1-2*self.rf)
    @property
    def F(self): return self.fp
    @property
    def R(self): return self.rp
    @property
    def beta(self): return 0.5*self.Ic

    def __init__(self, **kw):
        """Define the polarization efficiency correction for the beam
        beam: measured beam intensity for all four cross sections
        FRbalance: portion of efficiency to assign to front versus rear
        """
        for k,v in kw.iteritems():
            assert hasattr(self,k), "No %s in %s"%(k,self.__class__.__name__)
            setattr(self,k,v)

    def __call__(self, data):
        """Apply the correction to the data"""
        assert data.ispolarized(), "need polarized data"
        assert data.isaligned(), "need aligned data"

        X,dX = correct_efficiency(self, data)
        data.pp.v, data.pp.dv = X[0,:], dX[0,:]
        data.pm.v, data.pm.dv = X[1,:], dX[1,:]
        data.mp.v, data.mp.dv = X[2,:], dX[2,:]
        data.mm.v, data.mm.dv = X[3,:], dX[3,:]
        data.log(str(self))
        return data

    def __str__(self):
        return "PolarizationEfficiency('%s')"%self.beam.name

    def _compute_efficiency(self):
        """
        Compute polarizer and flipper efficiencies from the intensity data.

        If clip is true, reject points above or below particular efficiencies.
        The minimum intensity is 1e-10.  The minimum efficiency is 0.9.

        The returned values are systematically related to the efficiencies:
          Ic: intensity is 2*beta
          fp: front polarizer efficiency is F
          rp: rear polarizer efficiency is R
          ff: front flipper efficiency is (1-x)/2
          rf: rear flipper efficiency is (1-y)/2
        reject is the indices of points which are clipped because they
        are below the minimum efficiency or intensity.

        See PolarizationEfficiency.pdf for details on the calculation.
        """

        # Beam intensity normalization.
        beam = self._beam
        assert beam.isaligned(), "need aligned data"
        pp,pm,mp,mm = beam.pp.v,beam.pm.v,beam.mp.v,beam.mm.v
        Ic = (pp*mm-pm*mp) / (pp+mm-pm-mp)
        Ireject = clip(Ic, self.min_intensity, N.inf)

        # F and R are the front and rear polarizer efficiencies.  Each
        # is limited below by min_efficiency and above by 1 (since they
        # are not neutron sources).  Keep a list of points that are
        # rejected because they are outside this range.
        FR = pp/Ic - 1
        FRreject = clip(FR, self.min_efficiency**2, 1)
        fp = FR ** self.FRbalance
        rp = FR / fp

        # f and r are the front and rear flipper efficiencies.  Each
        # is again limited below by min_efficiency and above by 1.
        # We don't compute f and r directly, but instead x, y, Fx and Fy:
        #    x = 1-2f => f=(1-x)/2
        #    y = 1-2r => r=(1-y)/2
        # Clip the values which are out of range
        x = (pm/Ic - 1)/FR
        y = (mp/Ic - 1)/FR
        ff = (1-x)/2
        rf = (1-y)/2

        ffreject = clip(ff, self.min_efficiency, 1)
        rfreject = clip(rf, self.min_efficiency, 1)

        reject = N.unique(N.hstack([FRreject, Ireject, ffreject, rfreject]))

        self.Ic, self.fp, self.ff, self.rp, self.rf = Ic,fp,ff,rp,rf
        self.reject = reject



def clip(field,lo,hi,nanval=0.):
    """clip the values to the range, returning the indices of the values
    which were clipped.  Note that this modifies field in place. NaN
    values are clipped to the nanval default.
    """
    reject = N.where(N.isnan(field) | (field<lo) | (field>hi))
    field[N.isnan(field)] = nanval
    field[field<lo] = lo
    field[field>hi] = hi
    return reject

def correct_efficiency(eff, data):
    """Apply the efficiency correction in eff to the data."""

    F = eff.F
    R = eff.R
    Fx = eff.F*eff.x
    Ry = eff.R*eff.y
    beta = eff.beta

    Y = N.array([ data.pp.v, data.pm.v, data.mp.v, data.mm.v ]) / beta
    dY = N.array([ data.pp.dv, data.pm.dv, data.mp.dv, data.mm.dv ]) / beta

    # Note:  John's code has an extra factor of four here,
    # which roughly corresponds to the elements of sqrt(diag(inv(Y'Y))),
    # the latter giving values in the order of 3.9 for one example
    # dataset.  Is there an analytic reason it should be four?
    H = N.array([
                 (1+F)*(1+R), (1+Fx)*(1+R), (1+F)*(1+Ry), (1+Fx)*(1+Ry),
                 (1-F)*(1+R), (1-Fx)*(1+R), (1-F)*(1+Ry), (1-Fx)*(1+Ry),
                 (1+F)*(1-R), (1+Fx)*(1-R), (1+F)*(1-Ry), (1+Fx)*(1-Ry),
                 (1-F)*(1-R), (1-Fx)*(1-R), (1-F)*(1-Ry), (1-Fx)*(1-Ry),
                 ])

    X = N.zeros(Y.shape)
    dX = N.zeros(dY.shape)
    reject = []
    for i in xrange(H.shape[1]):
        # Extract and solve each set of equations
        # Note: it may be faster to compute the pseudo-inverses as a
        # a preprocessing step so that the code below is simply a matrix
        # multiply.  This will only be true if the same intensity scan
        # is used for multiple slit scans.
        A = N.reshape(H[:,i],(4,4))
        y = Y[:,i].T
        dy = dY[:,i].T
        try:
            s = wsolve(A,y,dy)
        except ValueError:
            x,dx = y,dy
            reject.append(i)
        else:
            x,dx = N.ravel(s.x),N.ravel(s.std)
        X[:,i] = x
        dX[:,i] = dx

    return X, dX

def demo():
    from examples import e3a12 as dataset
    eff = PolarizationEfficiency(beam=dataset.slits())
    for attr in ["Ic","fp","rp","ff","rf"]:
        print attr,getattr(eff,attr)
    data = dataset.spec()
    #data.appy(eff)

if __name__ == "__main__": demo()
