# -*- coding: utf-8 -*-

u"""
Dead time correction algorithms
===============================

Introduction
------------

Detector dead time is the time below which two detector events cannot be
distinguished.  The simplest assumption is that any event occurring during
the dead time will be ignored, and so the effective counting time for the
detector will need to be reduced by the amount of time the detector is
unresponsive.  Under this model:

.. math:

    m = \frac{n}{1 + n \tau_{\text NP}}`

where $n$ is the incident rate, $m$ is the measured rate, and
$\tau_{\text NP}$ is the "non-paralyzed" dead time.

The reality is more complicated: each event produces some physical effect
in the detector, such as ionizing an excited gas.  The paralyzed dead
time corresponds to the recharge time of the gas, below which any new
event will not cause ionization.  Another type of detector may rely on
scintillation resulting from a particle travelling through it.  The
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


Available functions
-------------------

- :func:`attenuation_estimate` returns the estimated attenuation
    associated with the observed count rate.  Use this for the day-to-day
    dead time correction.

- :func:`deadtime_estimate` returns estimates for the dead time constants from a
    set of attenuated and unattenuated direct beam measurements.  This
    should be measured from time to time to make sure that the detector
    characteristics are stable, but needn't be done for each experiment.

- :func:`peak_rate' returns the incident an observed rates at the
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
    :func:`deadtime_estimate` to estimate the dead time constants,
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

- *DEADTIME_UNITS* are the units for time constants (default 'μs').  Sorry,
    no unicode used.

- *DEADTIME_SCALE* is the scale factor for time constant units (default 1e-6)


References
----------

.. [Lee] Lee, S. H.; Gardner, R. P. (2000).
    *A new G-M counter dead time model*,
    Applied Radiation and Isotopes, **53**, 731-737.

"""
from __future__ import division, print_function

__all__ = [
    "attenuation_estimate", "deadtime_estimate", "peak_rate",
    "expected_rate", "simulate_measurement", "run_sim",
    "masked_curve_fit", "zero_insert",
    "DEADTIME_UNITS", "DEADTIME_SCALE",
    ]

import numpy as np
from numpy import exp, sqrt, inf
from scipy.optimize import curve_fit, newton

from uncertainties.unumpy import uarray, exp as uexp
from uncertainties.unumpy import nominal_values as uval, std_devs as udev
from uncertainties import ufloat

DEADTIME_UNITS = u'μs'
DEADTIME_SCALE = 1e-6

def masked_curve_fit(f, x, y, p0=None, sigma=None, fixed=None, **kw):
    """
    Wrapper around *scipy.optimize.curve_fit* which allows fixed parameters.

    *fixed* is a list of integer parameter numbers that should be fixed
    during the fit.  The parameter values for the fixed parameters are
    given in *p0*.  The returned *popt* contains the fixed values of these
    parameters, and *pcov* contains rows/columns of zero for these parameters.

    Otherwise the interface is the same as *curve_fit*.
    """
    if fixed is not None:
        p = p0+0.
        fitted = (p==p)
        fitted[fixed] = False
        init = p[fitted]
        def cost(x, *args, **kw):
            p[fitted] = args
            return f(x, *p, **kw)
    else:
        cost = f
        init = p0

    popt, pcov = curve_fit(cost, x, y, p0=init, sigma=sigma, **kw)

    # The clean thing to do is just return the diagonals
    """
    if fixed is not None:
        dp = np.zeros_like(p)
        p[fitted] = popt
        dp[fitted] = np.sqrt(np.diag(pcov))
    else:
        p, dp = popt, np.sqrt(np.diag(pcov))

    return p, dp
    """

    # for compatibility with curve_fit, insert zeros for fixed parameter cov
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
    `stack overflow <http://stackoverflow.com/questions/26864619/inserting-rows-and-columns-into-a-numpy-array/26865792#26865792>`_.
    """
    n_b = A.shape[0] + len(index)
    not_index = np.array([k for k in range(n_b) if k not in index])
    B = np.zeros((n_b, n_b), dtype=A.dtype)
    B[not_index.reshape(-1, 1), not_index] = A
    return B


def attenuation_estimate(observed_rate, tau_NP, tau_P):
    """
    Return estimated dead-time attenuator factor for the given rate.

    *observed_rate* is a pair of vectors *(r, dr)*.  Gaussian uncertainty
    is sufficient since the rate measurements should be based on a large
    number of counts.

    *tau_NP* and *tau_P* can be estimated from pairs of rate measurements,
    one with and one without an attenuator.  See :func:`tau_fit` for details.

    Returns the attenuation factor *A* for each observed rate.
    """
    #r = np.asarray(observed_rate[0], 'd')
    #n, p = r*tau_P[0]*DEADTIME_SCALE, r*tau_NP[0]*DEADTIME_SCALE

    r = uarray(*observed_rate)
    n, p = r*ufloat(*tau_P)*DEADTIME_SCALE, r*ufloat(*tau_NP)*DEADTIME_SCALE

    # Some Newton steps to solve for incident rate given observed rate
    A = r*0.
    for _ in range(3):
        A = A - _f(A, n, p)/_df(A, n, p)

    # Newton steps with error propagation

    """
    # Newton's method to solve for incident rate given observed rate
    target = 0.1*dr/r
    A, n, p = np.zeros_like(r), r*tau_NP, r*tau_P
    step = 0
    while True:
        # Newton step
        #Ap = A - _f(A, n, p)/_df(A, n, p)
        # Halley step
        f, df, d2f = _f(A, n, p), _df(A, n, p), _d2f(A, n, p)
        Ap = A - 2*f*df / (2*df**2 - f*d2f)
        step += 1
        #print(step, Ap)
        print(step, Ap-A)
        if (abs(Ap - A) < target).all(): break
        if step>20: break
        A = Ap
    """

    # Newton's method
    #A = [newton(_f, 0, fprime=_df, args=(ri*tau_P, ri*tau_NP)) for ri in r]
    return A

def _f(A, n, p):
    return uexp(A*p)*(1 + A*n) - A

def _df(A, n, p):
    return uexp(A*p)*(A*n*p + n + p) - 1

def _d2f(A, n, p):
    return p*uexp(A*p)*(n*(A*p + 2) + p)


def deadtime_estimate(rate, rate_err, mode='mixed'):
    """
    Fit the dead time tau for the measured rate data.

    *rate* is a 2 x n array with the first column containing the unattenuated
    rates and the second column containing the attenuated rates.  *rate_err*
    is the same for the rate uncertainties.  Because we need to fit the
    incident rate and the attenuator scale factor in addition to the two
    time constants, at least four rate pairs must be measured in order to
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
    # initial values
    attenuator_estimate = rate[0,0] / rate[1,0]
    p0 = np.hstack((
        attenuator_estimate,            # attenuation_factor
        0, 0,                            # tau_NP and tau_P
        rate[1,:]*attenuator_estimate,  # incident rates
    ))

    # Set the fixed parameters
    if mode is None:
        mode = 'mixed'

    fixed = None
    if mode == 'NP':
        fixed = [1]
    elif mode == 'P':
        fixed = [2]
    elif mode == 'mixed':
        fixed = None
    elif mode is not None:
        raise ValueError("mode %r should be P, NP, or mixed"%mode)

    # perform the fit
    y = np.hstack((rate[0,:], rate[1,:]))
    dy = np.hstack((rate_err[0,:], rate_err[1,:]))
    #y, dy = rate[0,:], rate_err[0,:]
    x = np.arange(len(y))
    p, s = masked_curve_fit(_fit_tau_cost, y, y, p0, sigma=dy, fixed=fixed)
    dp = sqrt(np.diag(s))

    # extract the return values
    attenuator = (p[0], dp[0])
    tau_NP = (p[1], dp[1])
    tau_P = (p[2], dp[2])
    rates = (p[3:], dp[3:])
    return tau_NP, tau_P, attenuator, rates


def _fit_tau_cost(x, attenuator, tau_NP, tau_P, *rate):
    """
    Cost function for scipy optimize curve_fit.

    The x vector is ignored, other than to determine the total number of points.

    Used by :func:`deadtime_estimate` to fit the dead time constants.
    """

    direct_rate = rate
    attenuated_rate = np.array(rate)/attenuator
    incident = np.hstack((direct_rate, attenuated_rate))
    y = expected_rate(incident, tau_NP, tau_P)
    return y


def peak_rate(tau_NP=0., tau_P=0.):
    """
    Return incident and observed rates for the peak observed rate.

    If *tau_P* is zero, then there is no peak incident rate per se,
    but there is a peak observed rate.
    """
    if tau_P <= 0.:
        peak = inf
    elif tau_NP <= 0.:
        peak = 1/tau_P
    else:
        peak = 0.5*(sqrt(4*tau_NP/tau_P + 1) - 1)/tau_NP
    observed = expected_rate(peak, tau_NP=tau_NP, tau_P=tau_P) if tau_P>0 else 1/tau_NP

    return peak, observed


def expected_rate(rate, tau_NP=0., tau_P=0.):
    """
    Calculate the expected count rate given the observed count rate and the
    hybrid model dead time parameters
    """
    rate = np.asarray(rate, 'd')
    return rate * exp(-rate*tau_P*DEADTIME_SCALE) / (1. + rate*tau_NP*DEADTIME_SCALE)


def simulate_measurement(rate, target_counts, attenuator, tau_NP, tau_P,
                         cutoff_time=0.):
    """
    Return time and counts for each rate with and without attenuator.

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
    """
    rate = np.asarray(rate, 'd')
    attenuated_rate = expected_rate(rate/attenuator,
                                    tau_NP=tau_NP, tau_P=tau_P)
    unattenuated_rate = expected_rate(rate, tau_NP=tau_NP, tau_P=tau_P)
    theta = np.vstack((unattenuated_rate, attenuated_rate))
    #print("target", target)
    time = np.random.gamma(target_counts, 1/theta)
    counts = np.ones_like(time)*target_counts
    if cutoff_time > 0:
        index = time > cutoff_time
        counts[index] = np.random.poisson(cutoff_time*theta[index])
        time[index] = cutoff_time
    return time, counts


def run_sim(tau_NP=0, tau_P=0, attenuator=10, mode='mixed'):
    """
    Run a simulated dead time estimation measurement and dead time recovery.

    Print the simulated and recovered values.

    Plot the expected data in absolute and relative form.
    """

    #rate = [100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000]
    tmax = -np.log10(0.5*DEADTIME_SCALE*(tau_NP+tau_P))
    rate = np.logspace(tmax-3,tmax+0.5,10)
    rate[0], rate[-1] = rate[0]-1, rate[-1]+1
    target_counts = int(rate[-1]*0.2)
    # target_counts = 1e20  # force count by time
    # process time (in microseconds)
    time, counts = simulate_measurement(rate, target_counts, attenuator,
                                        tau_NP, tau_P,
                                        cutoff_time=5*60)
    res = deadtime_estimate(counts/time, np.sqrt(counts)/time, mode=mode)
    tau_NP_f, tau_P_f, attenuator_f, rate_f = res
    #print("counts",counts)
    #print("time",time)

    print("Total time to run experiment: %.2f hrs"%(np.sum(time)/3600))
    print("attenuator sim=%s, fit=%s"%(str(attenuator), str(ufloat(*attenuator_f))))
    print("tau_NP sim=%s, fit=%s"%(str(tau_NP), str(ufloat(*tau_NP_f))))
    print("tau_P  sim=%s, fit=%s"%(str(tau_P), str(ufloat(*tau_P_f))))
    #print("rate", rate_f[0])
    #print("drate/rate", rate_f[1]/rate_f[0])
    #print("rate residuals", (rate - rate_f[0])/rate_f[1])


    rate = np.asarray(rate, 'd')
    observed, err = counts/time, np.sqrt(counts)/time
    wo = (observed[0], err[0])  # without attenuator
    wt = (observed[1], err[1])  # with attenuator

    scale = attenuation_estimate( (observed[0], err[0]),
            tau_NP=tau_NP_f, tau_P=tau_P_f)
    ucor = scale*uarray(observed[0], err[0])
    scale = uval(scale)
    corrected, corrected_err = scale*observed[0], scale*err[0]
    print("scale", scale)
    print("correct error", (corrected - rate)/corrected_err)
    print("dcor simple", 100*corrected_err/corrected)
    print("dcor prop", 100*udev(ucor)/corrected)
    #return

    title = (
        r'Sim $\tau_{NP}=%g\,{\rm %s}$,  $\tau_{P}=%g\,{\rm %s}$,  ${\rm attenuator}=%g$'
        + '\n'
        + r'Fit $\tau_{NP}=%s$,  $\tau_P=%s$,  ${\rm attenuator}=%.2f$'
        )%(
        tau_NP, DEADTIME_UNITS, tau_P, DEADTIME_UNITS, attenuator,
        ("%.2f"%tau_NP_f[0] if tau_NP_f[1] > 0 else "-"),
        ("%.2f"%tau_P_f[0] if tau_P_f[1] > 0 else "-"),
        res[0][0],
        )

    import pylab
    pylab.subplot(211)
    #pylab.errorbar(rate, res[3][0], yerr=res[3][1], fmt='r.', label='fitted rate')
    #pylab.errorbar(rate, corrected, yerr=corrected_err, fmt='r.', label='corrected rate')
    pylab.errorbar(rate, uval(ucor), yerr=udev(ucor), fmt='r.', label='corrected rate')
    _show_rates(rate, wo, wt, attenuator)
    peak, observed = peak_rate(tau_NP=tau_NP, tau_P=tau_P)
    if rate[0] <= peak <= rate[-1]:
        pylab.axvline(x=peak, ls='--', c='b')
        pylab.text(x=peak, y=0.05, s=' %g'%peak,
                   ha='left', va='bottom',
                   transform=pylab.gca().get_xaxis_transform())
    if False:
        pylab.axhline(y=observed, ls='--', c='b')
        pylab.text(y=observed, x=0.05, s=' %g\n'%observed,
                   ha='left', va='bottom',
                   transform=pylab.gca().get_yaxis_transform())
    pylab.subplot(212); _show_droop(rate, wo, wt, attenuator)
    pylab.suptitle(title)
    pylab.show()

def _show_rates(rate, wo, wt, attenuator):
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

def _show_droop(rate, wo, wt, attenuator):
    import pylab

    #pylab.figure()
    pylab.errorbar(rate, wt[0]/(rate/attenuator), yerr=wt[1]/(rate/attenuator),
                   fmt='g.', label='attenuated')
    pylab.errorbar(rate, wo[0]/rate, yerr=wo[1]/rate,
                   fmt='b.', label='unattenuated', hold=True)

    pylab.xscale('log')
    pylab.xlabel('incident rate (counts/second)')
    pylab.ylabel('droop (observed rate/expected rate)')
    pylab.legend(loc='best')
    pylab.grid(True)

if __name__ == "__main__":
    #TAU_NP, TAU_P = 0.1, 30
    #TAU_NP, TAU_P = 0., 30
    #TAU_NP, TAU_P = 10, 10
    #TAU_NP, TAU_P = 30, 0.0
    #TAU_NP, TAU_P = 30, 0.1
    #TAU_NP, TAU_P = 5, 15
    #TAU_NP, TAU_P = 10, 20
    TAU_NP, TAU_P = 1, 2
    #TAU_NP, TAU_P = 3, 0
    #TAU_NP, TAU_P = 0, 3
    ## sub-microsecond dead times
    #TAU_NP, TAU_P = 0.050, 0.150
    #TAU_NP, TAU_P = 0.050, 0

    MODE='mixed'
    #MODE='P'
    #MODE='NP'

    #ATTENUATOR = 5
    ATTENUATOR = 10
    #ATTENUATOR = 20
    run_sim(tau_NP=TAU_NP, tau_P=TAU_P, attenuator=ATTENUATOR, mode=MODE)
