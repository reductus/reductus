#!/usr/bin/env python
# -*- coding: utf-8 -*-

r"""
Introduction
------------

Detector dead time is the time below which two detector events cannot be
distinguished.  The simplest assumption is that any event occurring during
the dead time will be ignored, and so the effective counting time for the
detector will need to be reduced by the amount of time the detector is
unresponsive.  Under this model:

.. math:

    m = \frac{n}{1 + n \tau_{\text NP}}

where $n$ is the incident rate, $m$ is the measured rate, and
$\tau_{\text NP}$ is the "non-paralyzed" dead time.

The reality is more complicated: each event produces some physical effect
in the detector, such as ionizing an excited gas.  The paralyzing dead
time corresponds to the recharge time of the gas, below which any new
event will not cause ionization.  Another type of detector may rely on
scintillation resulting from a particle traveling through it.  The
photon counter will register voltage spikes each time the particle causes
a new cascade of photons to be emitted. The detector must wait until the
scintillation ends before being sure that the particle has finished traversing
the detector.  If a new particle enters during this time, then the
scintillation will continue until all particles are gone.  In effect,
each new event resets the dead time clock.  This model leads to:

.. math:

    m = n \exp(-n \tau_{\text P})

where $\tau_{\text P}$ is the "paralyzed" dead time.

A hybrid model[Lee]_ combines both effects:

.. math:

    m = \frac{n \exp(-n \tau_{\text P})}{1 + n \tau_{\text NP}}

Detector dead time constants can be estimated from a set of intensity
measurements.  For a beam line detector, measure a series of slit openings
with and without an attenuator.  The narrow slits should be measured for
a long time to give a good estimate of the attenuator scale factor at
low count rates, where the dead time has a minimal effect on the
estimated rate.  The wider slits are used to estimate the dead time, with
the attenuated rate scaled by the attenuator factor to give the true
rate.  From these measurements we can estimate the incident beam rate
and the attenuator factor, $\tau_{\text NP}$, and possibly $\tau_{\text P}$
if we need to use the hybrid model.

Note that a non-zero *tau_NP* will lead to total detector lockout for
high enough count rates.  When the probability of an event occurring
during the paralyzing time constant approaches unity, the detector
never has enough time to recover so that a new event can be triggered.
This will lead to a decrease in the number of counts beyond the incident
and observed peak rates returned by :func:`peak_rate`.  Clearly, if this
is the case then observed rate to peak rate is not unique.  The function
:func:`attenuation_estimate` assumes that the incident rate is below the
peak rate.

In principle, one could tag each observed rate as non-saturated
while you are exposing the detector to increasing amounts of beam, then
assume it is saturated when the inferred rate passes the peak, but this
is beyond the scope of the current project.  Instead, users should
exclude any measurements which they believe to be from a saturated detector.

Note that the fit has a strong preference for including a paralyzing
time constant even for simulations with 10 hours of counts.  In practice
it won't matter, so long as the working range of the detector is within
the calibration range. You can force a pure non-paralyzing model by
setting mode to *NP*, but this is not advised. The effect of the paralyzing
time constant is minimal in the beginning, but once pile-up starts the
attenuation can be dramatic, so the assumption that it is purely
non-paralyzing is difficult to support by observations below the
rate $1/\tau_{\text P}$.

Available functions
-------------------

- :func:`attenuation_estimate` returns the estimated attenuation
    associated with the observed count rate.  Use this for the day-to-day
    dead time correction.

- :func:`deadtime_estimate` returns estimates for the dead time constants from a
    set of attenuated and unattenuated direct beam measurements.  This
    should be measured from time to time to make sure that the detector
    characteristics are stable, but needn't be done for each experiment.

- :func:`deadtime_from_counts` is an interface to the dead time estimate
    using counts and counting times rather than rate and rate uncertainty.

- :func:`peak_rate` returns the incident an observed rates at the
    peak observed rates for the detector.  You should keep all incident
    intensity below the incident rate at the peak in order to avoid
    confusion between saturated and unsaturated detector counts.

- :func:`expected_rate` returns the expected observed rate for a given
    incident rate on the detector.  The inverse function, which estimates
    the incident rate for a given observed rate, can be calculated from
    :func:`attenuation_estimate`.

- :func:`simulate_measurement` returns a simulated set of counts for
    the dead time characterization measurement.

- :func:`run_sim` runs a detector calibration simulation, using
    :func:`simulate_measurement` to generate the calibration data,
    :func:`deadtime_from_counts` to estimate the dead time constants,
    :func:`attenuation_estimate` to recover the incident intensity
    and plots the results.  The :func:`peak_rate` value is shown
    on the graphs.

- :func:`masked_curve_fit` is a wrapper for *scipy.optimize.curve_fit*
    which allows you to fix some parameters in the model.  This is used
    by :func:`deadtime_estimate`, but is general enough that it could
    be used elsewhere.

- :func:`zero_insert` is a function to insert zero columns and rows into
    a matrix, corresponding to the covariance of the parameters which are
    fixed during the fit.  This is used by :func:`masked_curve_fit`, and
    left visible in case it is useful elsewhere.

- *DEADTIME_UNITS* are the units for time constants (default 'μs').

- *DEADTIME_SCALE* is the scale factor for time constant units (default 1e-6)


References
----------

.. [Lee]
    Lee, S. H.; Gardner, R. P. (2000).
    *A new G-M counter dead time model*,
    Applied Radiation and Isotopes, **53**, 731-737.

.. [Lebigot]
    Lebigot, Eric O. (2015).
    *Uncertainties: a Python package for calculations with uncertainties*,
    `https://pythonhosted.org/uncertainties/ <https://pythonhosted.org/uncertainties/>`_.

"""
from __future__ import division, print_function

__all__ = [
    "estimate_attenuation", "estimate_deadtime", "peak_rate",
    "expected_rate", "simulate_measurement", "run_sim",
    "masked_curve_fit", "zero_insert",
    "DEADTIME_UNITS", "DEADTIME_SCALE",
    ]

import numpy as np
from numpy import exp, sqrt, inf

from uncertainties.unumpy import nominal_values as uval, std_devs as udev
from uncertainties.unumpy import uarray
from uncertainties import ufloat

DEADTIME_UNITS = u'μs'
DEADTIME_SCALE = 1e-6

#import numdifftools as nd
def masked_curve_fit(f, x, y, p0=None, sigma=None, fixed=None, method='lm', **kw):
    """
    Wrapper around *scipy.optimize.curve_fit* which allows fixed parameters.

    *fixed* is a list of integer parameter numbers that should be fixed
    during the fit.  The parameter values for the fixed parameters are
    given in *p0*.  The returned *popt* contains the fixed values of these
    parameters, and *pcov* contains rows/columns of zero for these parameters.

    Otherwise the interface is the same as *curve_fit*.
    """
    from scipy.optimize import curve_fit
    # Hide fixed parameters
    if fixed is not None:
        p = p0+0.
        fitted = (p == p)
        fitted[fixed] = False
        init = p[fitted]
        def cost(x, *args, **kw):
            p[fitted] = args
            return f(x, *p, **kw)
    else:
        cost = f
        init = p0

    # Perform fit
    if method == 'lm':
        popt, pcov = curve_fit(cost, x, y, p0=init, sigma=sigma, **kw)
    else:
        if sigma is None:
            sigma = 1
        def chisq(p):
            resid = (cost(x, *p, **kw) - y)/sigma
            v = np.sum(resid**2)/(len(x)-len(p))
            return v
        from scipy.optimize import minimize
        res = minimize(chisq, init, method=method, options={'maxiter':1000})
        popt = res.x
        #from scipy.optimize import fmin
        #popt = fmin(chisq, init, maxiter=10)
        try:
            import numdifftools as nd
            H = nd.Hessian(chisq)(popt)
            L = np.linalg.cholesky(H)
            Linv = np.linalg.inv(L)
            pcov = np.dot(Linv.T.conj(), Linv)
        except Exception as exc:
            print(exc)
            pcov = np.zeros((len(p0), len(p0)))

    # Restore fixed parameters
    if fixed is not None:
        p[fitted] = popt
        pcov = zero_insert(pcov, fixed)
    else:
        p = popt

    return p, pcov


def zero_insert(A, index):
    """
    Insert zero rows/columns into matrix A at each index.

    Solution by Warren Weckesser, on
    `stack overflow <https://stackoverflow.com/questions/26864619/inserting-rows-and-columns-into-a-numpy-array/26865792#26865792>`_.
    """
    n_b = A.shape[0] + len(index)
    not_index = np.array([k for k in range(n_b) if k not in index])
    B = np.zeros((n_b, n_b), dtype=A.dtype)
    B[not_index.reshape(-1, 1), not_index] = A
    return B


def estimate_incident(observed_rate, tau_NP, tau_P, above=False):
    """
    Estimate incident rate given observed rate.

    *observed_rate* is a pair of vectors *(r, dr)*.  Gaussian uncertainty
    is sufficient since the rate measurements should be based on a large
    number of counts.

    *tau_NP* and *tau_P* can be estimated from pairs of rate measurements,
    one with and one without an attenuator.  See :func:`tau_fit` for details.
    Each time constant is a pair *(T, dT)* scaled by *DEADTIME_SCALE*. The
    uncertainty *dT* is ignored for now, since the time constant estimates
    can be highly correlated, particularly if the measurement range is low.

    If *above* is True, then return the rate estimate assuming that the
    rate is higher than the peak rate.

    Returns (I,dI), the estimated incident rate and its uncertainty.

    Note: the uncertainty analysis for paralyzing models is dodgy, as it
    simply scales the uncertainty in the observed counts, suggesting the
    model is perfectly known.  This is fine for most points, but for high
    saturation where the observed rate flattens, a large change in incident
    rate only causes a small change in observed rate.
    """

    # Nonparalyzing dead time only
    if tau_P[0] == 0.:
        # Use direct calculation for pure non-paralyzing models
        R = uarray(*observed_rate)
        tau_NP = ufloat(*tau_NP)
        I = R/(1-R*tau_NP*DEADTIME_SCALE)
        # May accidentally exceed the peak rate; in that case, limit
        # the damage to the lowest rate consistent with the uncertainty
        # in the observed rate.  Basically, look at the denominator in
        # the above equation, and if it is within error of zero, use the
        # relative uncertainty as the scale factor.
        #idx = (R*tau_NP[0]*DEADTIME_SCALE > (1-dR/R))
        #I[idx] = R[idx]**2/dR[idx]
        return uval(I), udev(I)

    # Paralyzing and mixed dead time
    R, dR = observed_rate
    Ipeak, Rpeak = peak_rate(tau_NP[0], tau_P[0])
    if above:
        # Use bisection for intensity above Ipeak.  This was stable enough
        # for the problems tried.  We haven't put effort into improving
        # performance this capability isn't likely to be used in production.
        n, p = tau_NP[0]*DEADTIME_SCALE, tau_P[0]*DEADTIME_SCALE
        I = [_invert_above(Ipeak, Rpeak, rk, n, p) for rk in R]
        # We can probably get Newton-Raphson iteration to work if we start
        # it in the right place.  The first try with Io = Ipeak*Rpeak/r
        # gave numerical problems, presumably because it was starting too
        # far out in I.  If this capability becomes important this problem
        # can be solved for reasonable values of r.
        I = np.array(I)
    else:
        # Use solver for P and mixed P-NP problems.
        n, p = tau_NP[0]*DEADTIME_SCALE, tau_P[0]*DEADTIME_SCALE
        r = np.asarray(observed_rate[0], 'd')
        # Use Newton-Raphson iteration starting from the observed rate.
        # It converges quickly and stably away from Rpeak.  Near Rpeak
        # it may give numerical problems, but these points are handled
        # elsewhere, so the errors and warnings are suppressed.
        with np.errstate(all='ignore'):
            I = r.copy()
            I -= _forward(I, n, p, r) / _dforward(I, n, p)
            I -= _forward(I, n, p, r) / _dforward(I, n, p)
            I -= _forward(I, n, p, r) / _dforward(I, n, p)
        # Use bisection near Rpeak since the slope approaches zero and
        # Newton-Raphson may fail.  These should be rare.
        index = (r > 0.9*Rpeak)
        I[index] = [_invert_below(Ipeak, Rpeak, rk, n, p) for rk in r[index]]

    return I, (I/R)*dR

def estimate_attenuation(observed_rate, tau_NP, tau_P, above=False):
    """
    Estimated dead-time scale factor for the given rate.

    Note: the uncertainty analysis is dodgy, as it only propagates the
    uncertainty in the observed counts, not the fitted model.  This is
    fine for most points, where the correction is stable, but it may
    be underestimating the uncertainty in the corrected rate for high
    precision rate measurements.
    """
    I, dI = estimate_incident(observed_rate, tau_NP, tau_P, above=above)
    A = I/uarray(*observed_rate)
    return A

def _invert_below(Ipeak, Rpeak, r, n, p):
    from scipy.optimize import bisect
    return bisect(_forward, r, Ipeak, args=(n, p, r)) if r < Rpeak else Ipeak

def _invert_above(Ipeak, Rpeak, r, n, p):
    from scipy.optimize import bisect
    return bisect(_forward, Ipeak, 1e6*Ipeak, args=(n, p, r)) if r < Rpeak else Ipeak

def _forward(I, n, p, r):
    return I*exp(-I*p)/(I*n + 1.) - r

def _dforward(I, n, p):
    return -exp(-I*p)/(I*n + 1.)*(I*p - 1./(I*n + 1.))

def deadtime_from_counts(counts, mode='mixed'):
    """
    Convert from counts to rates and estimate detector dead times.

    *counts* are pairs of vectors containing (counts, time).  These are
    converted to rate and uncertainty using Poisson statistics.

    *mode* is described in :func:`estimate_deadtime`.
    """
    # assumes data is aligned and sorted by slit opening
    rates = [(c/t, np.sqrt(c)/t) for c, t in counts]

    return estimate_deadtime(rates, mode=mode)


def estimate_deadtime(datasets, mode='auto'):
    """
    Fit the dead time tau for the measured rate data.

    *attenuated* and *unattenuated* are pairs of vectors containing
    (count rate, rate uncertainty).  Because we fit the incident rate
    and the attenuator scale factor in addition to the two time constants,
    at least four incident intensities must be measured in order to
    recover all the fitted parameters.

    *mode* is 'P' a for purely paralyzing dead time model, 'NP' for a
    purely non-paralyzing dead time model, or 'mixed' for hybrid model with
    paralyzing and non-paralyzing time constants.  If the detector does
    not show significant saturation, then there will not be enough information
    to fit both paralyzing and non-paralyzing time constants.  In that case,
    either model should work well enough; with few pile-up events in low
    event rate data, the distinction between paralyzing and non-paralyzing
    dead time is minimal.  Through simulation, you can observe that the
    incorrect model will yield incorrect values for the time constant,
    with the paralyzing time constant being somewhat smaller for
    an equivalent dead time attenuation.

    Don't try to apply the correction significantly beyond the range for
    which it was characterized.

    Returns a list of pairs (p, dp) containing *tau_NP*, *tau_P*,
    *attenuator* and *incident_rate*.  The incident rate is a pair of
    vectors *(r, dr)*.
    """
    # guess attenuator from first point and dead time from highest point
    # use these guesses as the initial values
    num_atten = len(datasets) - 1
    unattenuated = datasets[-1]
    A = [(a[0][0] / unattenuated[0][0]) for a in datasets[:-1]]
    idx = np.argmax(unattenuated[0])
    R1, R2 = unattenuated[0][idx], datasets[0][0][idx]
    T = (1/R1 - (R1+R2)/(R1*R2*(1/A[0] - 1)))/DEADTIME_SCALE
    #print("A",1/A,"NP",T)
    p0 = np.hstack((
        T, 0,             # tau_NP and tau_P
        #1, 2,            # tau_NP and tau_P
        A,                # attenuation factor(s)
        datasets[0][0]/A[0],  # incident rates
    ))

    # Set the fixed parameters
    if mode is None:
        mode = 'mixed'

    fixed = None
    if mode == 'NP':
        fixed = [1]
    elif mode == 'P':
        fixed = [0]
    elif mode == 'mixed' or mode == 'auto':
        fixed = None
    elif mode is not None:
        raise ValueError("mode %r should be P, NP, mixed or auto"%mode)

    # perform the fit
    y = np.hstack([a[0] for a in datasets])
    dy = np.hstack([a[1] for a in datasets])
    #y, dy = rate[0,:], rate_err[0,:]
    x = np.arange(len(y))

    def prediction(x, *p):
        if any(v < 0 for v in p):
            return 1000*y
        return _rate_estimate(p[0], p[1], p[2:2+num_atten], p[2+num_atten:])

    p, s = masked_curve_fit(prediction, x, y, p0, sigma=dy, fixed=fixed)
    if mode == 'auto':
        # Pick the better fit from pure np, pure p or both
        # Note: spurious P components can appear, even in truncated ranges
        pn, sn = masked_curve_fit(prediction, x, y, p0, sigma=dy, fixed=[1])
        p0[0], p0[1] = 0., T
        pp, sp = masked_curve_fit(prediction, x, y, p0, sigma=dy, fixed=[0])

        chisq_np = _chisq(pn, prediction, x, y, dy)
        chisq_p = _chisq(pp, prediction, x, y, dy)
        if chisq_np <= chisq_p:
            chisq_one, p1, s1 = (chisq_np, pn, sn)
        else:
            chisq_one, p1, s1 = (chisq_p, pp, sp)

        # Compare the single fit to the fit to both p and np
        chisq_both = _chisq(p, prediction, x, y, dy)
        dof = len(y) - len(p0)
        F = (chisq_one - chisq_both)/(chisq_both/dof)
        from scipy import stats
        pF = stats.f.cdf(F, 1, dof)
        #print("  chisq np=%.2f  p=%.2f  both=%.2f  p(F-stat)=%.3f"
        #      %(chisq_np, chisq_p, chisq_both, pF))

        # Pick single vs combined fit subject to reduction in chisq being
        # enough to justify the additional parameter
        if pF < 0.05:
            p, s = p1, s1


    dp = sqrt(np.diag(s))

    # extract the return values
    tau_NP = (p[0], dp[0])
    tau_P = (p[1], dp[1])
    attenuators = (p[2:2+num_atten], dp[2:2+num_atten])
    rates = (p[2+num_atten:], dp[2+num_atten:])
    return tau_NP, tau_P, attenuators, rates

def _chisq(p, f, x, y, dy):
    resid = (f(x, *p) - y)/dy
    return np.sum(resid**2)

def _rate_estimate(tau_NP, tau_P, attenuators, rates):
    """
    Given time constants *tau_NP* and *tau_P*, a list of *attenuators*
    [A1, A2, ...] and true incident *rates* [r1, r2, ...], return the
    estimated observed rates for [A1r1 A1r2 ... A2r1 A2r2 ... r1 r2 ...].
    """
    direct_rate = np.asarray(rates, 'd')
    rates = [direct_rate*attenuation for attenuation in attenuators]
    rates.append(direct_rate)
    incident = np.hstack(rates)
    y = expected_rate(incident, tau_NP, tau_P)
    return y

def _fit_resid_jacobian(p, x, y, f, w):
    """
    Analytic jacobian of the _fit_resid function.
    """
    tau_NP, tau_P = p[:2]
    raise RuntimeError("not updated for multiple attenuators")
    direct_rate = np.asarray(p[3:], 'd')
    attenuated_rate = direct_rate*attenuation
    rate = np.hstack((attenuated_rate, direct_rate))
    # f = (A*R * exp(-A*R*tau_P*DEADTIME_SCALE) / (1. + A*R*tau_NP*DEADTIME_SCALE))
    fx = expected_rate(rate, tau_NP, tau_P)
    num_rates = len(direct_rate)
    den = 1. + rate * tau_NP*DEADTIME_SCALE
    common = (tau_P*DEADTIME_SCALE*rate - 1./den)
    dfdA = fx * (-common/attenuation)
    dfdP = fx * (-rate*DEADTIME_SCALE)
    dfdN = fx * (-rate/den*DEADTIME_SCALE)
    dfdR = fx * (-common/rate)
    dfdR[:num_rates] *= attenuation
    dfdA[num_rates:] = 0.
    dfdR = np.vstack((np.diag(dfdR[:num_rates]), np.diag(dfdR[num_rates:])))
    J = np.hstack((dfdA[:, None], dfdN[:, None], dfdP[:, None], dfdR))
    #print(J)
    wJ = w[:, None]*J

    ## Cross check against the numerical derivative using numdifftools
    #print("calc numeric J")
    #import numdifftools as nd
    #wJnum = nd.Jacobian(lambda p: _fit_resid(p, x, y, f, w))(p)
    #print((wJ-wJnum).max())
    #print("A",wJ[:num_rates,0])
    #print("A",wJnum[:num_rates,0])
    #print("A",D[:num_rates,0]/wJ[:num_rates,0])

    #print("NP",wJ[:,1])
    #print("NP",wJnum[:,1])
    #print("NP",D[:,1]/wJ[:,1])

    #print("N",wJ[:,2])
    #print("N",wJnum[:,2])
    #print("N",D[:,2]/wJ[:,2])

    #print("RA",np.diag(wJ[:num_rates,3:]))
    #print("RA",np.diag(wJnum[:num_rates,3:]))
    #print("RA",np.diag(D[:num_rates,3:]))

    #print("RN",np.diag(wJ[num_rates:,3:]))
    #print("RN",np.diag(wJnum[num_rates:,3:]))
    #print("RN",np.diag(D[num_rates:,3:]/np.diag(wJ[num_rates:,3:])))
    return wJ


def peak_rate(tau_NP=0., tau_P=0.):
    """
    Return incident and observed rates for the peak observed rate.

    If *tau_P* is zero, then there is no peak incident rate per se,
    but there is a peak observed rate.
    """
    if tau_P <= 0.:
        Ipeak = inf
    elif tau_NP <= 0.:
        Ipeak = 1.0/tau_P/DEADTIME_SCALE
    else:
        Ipeak = 0.5*(sqrt(4*tau_NP/tau_P + 1) - 1)/tau_NP/DEADTIME_SCALE
    Rpeak = (expected_rate(Ipeak, tau_NP=tau_NP, tau_P=tau_P)
             if tau_P > 0 else 1/tau_NP/DEADTIME_SCALE)

    return Ipeak, Rpeak


def expected_rate(rate, tau_NP=0., tau_P=0.):
    """
    Calculate the expected count rate given the true count rate and the
    hybrid model dead time parameters
    """
    rate = np.asarray(rate, 'd')
    return (rate * exp(-rate*tau_P*DEADTIME_SCALE)
            / (1. + rate*tau_NP*DEADTIME_SCALE))


def simulate_measurement(rate, target_counts, attenuator, tau_NP, tau_P,
                         cutoff_time=0.):
    r"""
    Simulate time and counts for each rate with and without attenuator.

    *rate* is a vector of incident beam rates representing different
    slit configurations.

    *target_counts* is the total number of counts desired at each rate.  The
    counting time with attenuator is clearly going to be longer than the
    counting time without to achieve the same statistics.  Counting time
    for a given number of counts *k* follows an Erlang distribution, which
    is a gamma distribution with discrete *k* and *\theta=\lambda*.

    *attenuator* is a scale on the rate incident on the detector.

    *tau_NP* is the non-paralyzed dead time, representing the minimum time
    to process a neutron count.  This will be the dominant effect at lower
    rates.

    *tau_P* is the paralyzed dead time, representing the minimum time for
    the activation level to get low enough after pile-up for the next neutron
    to be seen.  At higher rates this effect will dominate, eventually
    leading to zero observed counts when the detector is not given enough
    time to reset.

    *cutoff_time* is the maximum time in seconds for each measurement. If
    the simulated measurement time for the *target_counts* exceeds
    *cutoff_time*, then time is fixed to the cutoff and the number of
    counts in that time is simulated instead.

    Returns (counts, time) pairs for attenuated and unattenuated values.
    """
    rate = np.asarray(rate, 'd')
    attenuated_rate = expected_rate(rate/attenuator,
                                    tau_NP=tau_NP, tau_P=tau_P)
    unattenuated_rate = expected_rate(rate, tau_NP=tau_NP, tau_P=tau_P)
    theta = np.vstack((attenuated_rate, unattenuated_rate))
    #print("target", target_counts, attenuator)
    #print("theta", theta)
    time = np.random.gamma(target_counts, 1/theta)
    counts = np.ones_like(time)*target_counts
    #print("theta",theta)
    #print("time",time)
    #print("counts",counts)
    if cutoff_time > 0:
        index = time > cutoff_time
        counts[index] = np.random.poisson(cutoff_time*theta[index])
        time[index] = cutoff_time
    return (counts[0], time[0]), (counts[1], time[1])


def run_sim(tau_NP=0, tau_P=0, attenuator=10, mode='mixed', plot=True, tmax=None):
    """
    Run a simulated dead time estimation measurement and dead time recovery.

    Print the simulated and recovered values.

    Plot the expected data in absolute and relative form.
    """

    # set rate, target counts and cutoff time
    if tmax is None:
        tmax = np.ceil(-np.log10(DEADTIME_SCALE*(tau_NP+tau_P)/2)+0.49)
    else:
        tmax = np.log10(tmax)
    tmin = tmax-4
    #tmin, tmax = np.log10(5000.), np.log10(35000.)
    rate = np.logspace(tmin, tmax, 9)
    rate_index = slice(0, None, 2)  # since 2 per decade
    rates_printed = rate[rate_index]+0
    rate[0], rate[-1] = rate[0]-1, rate[-1]+1

    target_counts, cutoff_time = int(rate[-1]*0.2), 5*60
    #target_counts, cutoff_time = int(rate[-1]*0.5), 15*60
    #target_counts, cutoff_time = 1e20, 30*60
    # target_counts = 1e20  # force count by time

    # simulate data
    attenuated, unattenuated = simulate_measurement(rate, target_counts,
                attenuator, tau_NP, tau_P, cutoff_time=cutoff_time)

    # estimate dead time
    try:
        res = deadtime_from_counts([attenuated, unattenuated], mode=mode)
        #print(*res)
    except Exception as exc:
        res = (tau_NP, 0), (tau_P, 0), (1./attenuator, 0), (rate, 0*rate)
        print(exc)
    tau_NP_f, tau_P_f, attenuation_f, rate_f = res

    Ipeak, Rpeak = peak_rate(tau_NP=tau_NP_f[0], tau_P=tau_P_f[0])
    #print("counts",counts)
    #print("time",time)

    # redo simulation for test
    attenuated, unattenuated = simulate_measurement(rate, target_counts,
                attenuator, tau_NP, tau_P, cutoff_time=cutoff_time)
    # correct the unattenuated data
    wt = (attenuated[0]/attenuated[1], sqrt(attenuated[0])/attenuated[1])
    wo = (unattenuated[0]/unattenuated[1], sqrt(unattenuated[0])/unattenuated[1])
    scale = estimate_attenuation((wo[0], wo[1]), tau_NP=tau_NP_f, tau_P=tau_P_f,
        #above=True
    )
    corrected = scale*uarray(wo[0], wo[1])
    #print("correction",ufloat(wo[0][-1],wo[1][-1]),"*",scale[-1],"=",corrected[-1])

    # Print results
    total_time = np.sum(attenuated[1] + unattenuated[1])
    print("  Total time to run experiment: %.2f hrs"%(total_time/3600))
    def _compare(name, target, fitted):
        err = (fitted.n-target)/(target if target > 0 else 1.)
        sbad = "*" if abs(err) > 0.5 else " "
        sval = str(target)
        sfit = str(fitted) if np.isfinite(fitted.s) else "%g"%fitted.n
        serr = "%.2f%%"%(err*100)
        print(" %s%s sim=%s, fit=%s, err=%s"%(sbad, name, sval, sfit, serr))
    _compare("tau_NP", tau_NP, ufloat(*tau_NP_f))
    _compare("tau_P", tau_P, ufloat(*tau_P_f))
    _compare("atten", attenuator, 1./ufloat(*attenuation_f))
    print("  peak observed rate %d at %d incident"
          %(int(Ipeak if np.isfinite(Ipeak) else 3*Rpeak), int(Rpeak)))
    #print(" rate", rate_f[0])
    #print("  drate/rate", rate_f[1]/rate_f[0])
    #print("  rate residuals", (rate - rate_f[0])/rate_f[1])
    #print("  scale", " ".join('{:S}'.format(v) for v in scale))
    pairs = zip(rates_printed, scale[rate_index])
    print("  effect", " ".join('%d=%.1f%%'%(int(r), 100*(v.n-1)) for r, v in pairs))
    print("  scale", " ".join('%.2f'%v.n for v in scale))
    rel_err = (rate-uval(corrected))/rate
    print("  error (r-r')/r:",
          " ".join("%.2f%%"%v for v in 100*rel_err[rate <= Ipeak]))
    print("  corrected  (r-r')/dr':",
          " ".join("% .2f"%v for v in
                   (rate-uval(corrected))/udev(corrected)))
    print("  uncorrected (r-r')/dr:",
          " ".join("% .2f"%v for v in (rate-wo[0])/wo[1]))
    target = (tau_NP, tau_P, attenuator, rate)
    fitted = (tau_NP_f, tau_P_f, attenuation_f, rate_f)
    if plot:
        _show_plots(target, fitted, wt, wo, corrected)


def _show_plots(target, fitted, wt, wo, corrected):
    tau_NP, tau_P, attenuator, rate = target
    tau_NP_f, tau_P_f, attenuation_f, rate_f = fitted

    # Plot the results
    sim_pars = (r'Sim $\tau_{NP}=%g\,{\rm %s}$,  $\tau_{P}=%g\,{\rm %s}$,  ${\rm attenuator}=%g$'
               )%(tau_NP, DEADTIME_UNITS, tau_P, DEADTIME_UNITS, attenuator)
    fit_pars = (r'Fit $\tau_{NP}=%s$,  $\tau_P=%s$,  ${\rm attenuator}=%.2f$'
               )%(
                   ("%.2f"%tau_NP_f[0] if np.inf > tau_NP_f[1] > 0 else "-"),
                   ("%.2f"%tau_P_f[0] if np.inf > tau_P_f[1] > 0 else "-"),
                   1./attenuation_f[0],
               )
    title = '\n'.join((sim_pars, fit_pars))
    import pylab
    pylab.subplot(211)
    #pylab.errorbar(rate, rate_f[0], yerr=rate_f[1], fmt='c.', label='fitted rate')
    #mincident = np.linspace(rate[0], rate[-1], 400)
    #munattenuated = expected_rate(mincident, tau_NP_f[0], tau_P_f[0])
    #mattenuated = expected_rate(mincident/attenuator, tau_NP_f[0], tau_P_f[0])
    #minc = np.hstack((mincident, 0., mincident))
    #mobs = np.hstack((munattenuated, np.NaN, mattenuated))
    #pylab.plot(minc, mobs, 'c-', label='expected rate')
    pylab.errorbar(rate, uval(corrected), yerr=udev(corrected), fmt='r.', label='corrected rate')
    _show_rates(rate, wo, wt, attenuator, tau_NP_f[0], tau_P_f[0])
    pylab.subplot(212)
    _show_droop(rate, wo, wt, attenuator)
    pylab.suptitle(title)

    #pylab.figure(); _show_inversion(wo, tau_P_f, tau_NP_f)
    pylab.show()

def _show_rates(rate, wo, wt, attenuator, tau_NP, tau_P):
    import pylab

    #pylab.figure()
    pylab.errorbar(rate, wt[0], yerr=wt[1], fmt='g.', label='attenuated')
    pylab.errorbar(rate, wo[0], yerr=wo[1], fmt='b.', label='unattenuated')

    pylab.xscale('log')
    pylab.yscale('log')
    pylab.xlabel('incident rate (counts/second)')
    pylab.ylabel('observed rate (counts/second)')
    pylab.legend(loc='best')
    pylab.grid(True)
    pylab.plot(rate, rate/attenuator, 'g-', label='target')
    pylab.plot(rate, rate, 'b-', label='target')

    Ipeak, Rpeak = peak_rate(tau_NP=tau_NP, tau_P=tau_P)
    if rate[0] <= Ipeak <= rate[-1]:
        pylab.axvline(x=Ipeak, ls='--', c='b')
        pylab.text(x=Ipeak, y=0.05, s=' %g'%Ipeak,
                   ha='left', va='bottom',
                   transform=pylab.gca().get_xaxis_transform())
    if False:
        pylab.axhline(y=Rpeak, ls='--', c='b')
        pylab.text(y=Rpeak, x=0.05, s=' %g\n'%Rpeak,
                   ha='left', va='bottom',
                   transform=pylab.gca().get_yaxis_transform())

def _show_droop(rate, wo, wt, attenuator):
    import pylab

    #pylab.figure()
    pylab.errorbar(rate, wt[0]/(rate/attenuator), yerr=wt[1]/(rate/attenuator),
                   fmt='g.', label='attenuated')
    pylab.errorbar(rate, wo[0]/rate, yerr=wo[1]/rate,
                   fmt='b.', label='unattenuated')

    pylab.xscale('log')
    pylab.xlabel('incident rate (counts/second)')
    pylab.ylabel('droop (observed rate/expected rate)')
    pylab.legend(loc='best')
    pylab.grid(True)

def _show_inversion(wo, tau_P_f, tau_NP_f):
    import pylab

    #Ipeak, Rpeak = peak_rate(tau_NP_f[0], tau_P_f[0])
    idx = np.argmax(wo[0])-1
    print("index", idx)
    Rmax, dRmax = wo[0][idx], wo[1][idx]
    A = np.linspace(0, 5, 400)
    r = 0.  # _forward computes f(x) - r, so set r to 0. to recover f(x)
    fA = lambda R: _forward(A, R*tau_NP_f[0]*DEADTIME_SCALE, R*tau_P_f[0]*DEADTIME_SCALE, r)
    Ao = lambda R, dR: estimate_attenuation(([R], [dR]), tau_NP_f, tau_P_f)[0].n
    pylab.plot(A, fA(Rmax), '-', label="Rmax")
    pylab.axvline(x=Ao(Rmax, dRmax))
    pylab.plot(A, fA(wo[0][idx-2]), '-', label="-2")
    pylab.plot(A, fA(wo[0][idx-1]), '-', label="-1")
    if idx+1 < len(wo[0]):
        pylab.plot(A, fA(wo[0][idx+1]), '-', label="+1")
    if idx+2 < len(wo[0]):
        pylab.plot(A, fA(wo[0][idx+2]), '-', label="+2")
    pylab.legend()
    pylab.grid(True)


if __name__ == "__main__":
    #TAU_NP, TAU_P = 0.001, 30
    #TAU_NP, TAU_P = 0., 30
    #TAU_NP, TAU_P = 10, 10
    #TAU_NP, TAU_P = 10, 0
    #TAU_NP, TAU_P = 30, 0.0
    #TAU_NP, TAU_P = 30, 0.1
    #TAU_NP, TAU_P = 5, 15
    #TAU_NP, TAU_P = 10, 20
    #TAU_NP, TAU_P = 1, 2
    #TAU_NP, TAU_P = 3, 0
    #TAU_NP, TAU_P = 0, 3
    ## sub-microsecond dead times
    #TAU_NP, TAU_P = 0.050, 0.150
    #TAU_NP, TAU_P = 0.050, 0

    MODE = 'auto'
    #MODE = 'mixed'
    #MODE = 'P'
    #MODE = 'NP'

    #ATTENUATOR = 5
    ATTENUATOR = 10
    #ATTENUATOR = 20

    ## Random models
    TAU_NP, TAU_P = np.random.exponential((1, 1))
    #TAU_NP, TAU_P = np.random.exponential((0.1,0.0002))
    #TAU_NP, TAU_P = np.random.exponential((0.01,1))
    #TAU_NP, TAU_P = np.random.exponential((1,0.01))
    #ATTENUATOR = np.random.uniform(5,100)

    PLOT = True
    #PLOT=False
    run_sim(tau_NP=TAU_NP, tau_P=TAU_P,
            attenuator=ATTENUATOR, mode=MODE, plot=PLOT)
