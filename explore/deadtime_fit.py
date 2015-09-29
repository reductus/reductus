"""
Explore algorithms for recovering dead time constants from slit scans.


"""
from __future__ import division, print_function
import numpy as np
from scipy.optimize import curve_fit


def expected_rate(rate, tau_NP=0., tau_P=0.):
    """
    Calculate the expected count rate given the observed count rate and the
    hybrid model dead time parameters

    .. [Lee] Lee, S. H.; Gardner, R. P. (2000).
        *A new G-M counter dead time model*,
        Applied Radiation and Isotopes, **53**, 731-737.

    """
    rate = np.asarray(rate, 'd')
    return rate * np.exp(-rate * tau_P) / (1. + rate * tau_NP)

def simulate_measurement(rate, target, attenuator_factor, tau_NP, tau_P,
                         cutoff=0.):
    """
    Return time and counts for each rate with and without attenuator.

    *rate* is a vector of incident beam rates representing different
    slit configurations.

    *target* is the total number of counts desired at each rate.  The
    counting time with attenuator is clearly going to be longer than the
    counting time without to achieve the same statistics.  Counting time
    for a given number of counts *k* follows an Erlang distribution, which
    is a gamma distribution with discrete *k* and *\theta=\lambda*.

    *attenuator_factor* is a scale on the rate incident on the detector.

    *tau_NP* is the non-paralyzed dead time, representing the minimum time
    to process a neutron count.  This will be the dominant effect at lower
    rates.

    *tau_P* is the paralyzed dead time, representing the minimum time for
    the activation level to get low enough after pile-up for the next neutron
    to be seen.  At higher rates this effect will dominate, eventually
    leading to zero observed counts when the detector is not given enough
    time to reset.

    *cutoff* is the maximum time in seconds for each measurement.  Instead
    of ending at a specific number of counts, it ends at a specific time.
    """
    rate = np.asarray(rate, 'd')
    attenuated_rate = expected_rate(rate/attenuator_factor,
                                    tau_NP=tau_NP, tau_P=tau_P)
    unattenuated_rate = expected_rate(rate, tau_NP=tau_NP, tau_P=tau_P)
    theta = np.vstack((unattenuated_rate, attenuated_rate))
    print("target", target)
    time = np.random.gamma(target, 1/theta)
    counts = np.ones_like(time)*target
    if cutoff > 0:
        index = time > cutoff
        counts[index] = np.random.poisson(cutoff*theta[index])
        time[index] = cutoff
    return time, counts

TAU_UNITS = 1e-6
#TAU_NP, TAU_P = 0.1, 30
#TAU_NP, TAU_P = 30, 0.1
#TAU_NP, TAU_P = 10, 10
TAU_NP, TAU_P = 5, 15
#TAU_NP, TAU_P = .5, 1.5
#TAU_NP, TAU_P, TAU_UNITS = 50, 150, 1e-9
#TAU_NP, TAU_P, TAU_UNITS = 50, 0, 1e-9
#ATTENUATOR = 5
ATTENUATOR = 10
#ATTENUATOR = 20

def cost(x,
         attenuation_factor,
         tau_NP,
         tau_P,
         *rate):
    """
    Cost function for scipy optimize curve_fit.

    The x vector is ignored, other than to determine the total number of points.

    The rate vector fits the unknown incident rate.  Given that we have the
    attenuated and unattenuated rate for each unknown incident, this seems
    to be enough to reconstruct the incident, while also fitting the
    attenuator and tau.  We probably do not need the attenuated and
    unattenuated points to be aligned, if for some reason we do not want
    to drive the attenuator too high.
    """

    # Can't toggle fitted/non-fitted, so need to comment out the parameters
    # as needed, then uncomment the default values inside the function.
#    attenuation_factor=ATTENUATOR
#    tau_NP = TAU_NP
#    tau_P = TAU_P

    direct_rate = rate
    attenuated_rate = np.array(rate)/attenuation_factor
    incident = np.hstack((direct_rate, attenuated_rate))
    y = expected_rate(incident, tau_NP*TAU_UNITS, tau_P*TAU_UNITS)
    return y

def fit_tau(rate, rate_err):
    """
    Fit the dead time tau for the measured rate data.

    *rate* is a 2 x n array with the first column containing the unattenuated
    rates and the second column containing the attenuated rates.  *rate_err*
    is the same for the rate uncertainties.

    Returns the attenation factor, tau_NP, tau_P and incident rates as a
    list of pairs (p, dp).
    """
    # initial values
    attenuator_factor = rate[0,0] / rate[1,0]
    tau_P, tau_NP = 0, 1
    #tau_P, tau_NP = TAU_P, TAU_NP
    incident_rates = rate[1,:]*attenuator_factor

    # You can play with the fixed/fitted values by commenting them out
    # in p0, down below in the returned values, and up above in both
    # the cost function parameters and the cost function initial
    # values.  Kind of a pain...
    p0 = np.hstack((
        attenuator_factor,
        tau_NP,
        tau_P,
        incident_rates))

    # fit
    y = np.hstack((rate[0,:], rate[1,:]))
    dy = np.hstack((rate_err[0,:], rate_err[1,:]))
    #y, dy = rate[0,:], rate_err[0,:]
    x = np.arange(len(y))
    p, s = curve_fit(cost, y, y, p0, sigma=dy)
    dp = np.sqrt(np.diag(s))

    # fixed values
    attenuation_factor = (ATTENUATOR, 0)
    tau_P = (TAU_P, 0)
    tau_NP = (TAU_NP, 0)

    # returned values
    i=0
    attenuation_factor = (p[i], dp[i]); i+=1
    tau_NP = (p[i], dp[i]); i+=1
    tau_P = (p[i], dp[i]); i+=1
    rates = (p[i:], dp[i:])
    return attenuation_factor, tau_NP, tau_P, rates

def run_sim():
    """
    Run a simulated dead time estimation measurement and dead time recovery.

    Print the simulated and recovered values.

    Plot the expected data in absolute and relative form.
    """
    #rate = [100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000]
    tmax = -np.log10(0.5*TAU_UNITS*(TAU_NP+TAU_P))
    rate = np.logspace(tmax-3,tmax+0.5,10)
    rate[0], rate[-1] = rate[0]-1, rate[-1]+1
    target = rate[-1]*0.2 #*10
    target = int(target)
    target = 1e20
    atten = ATTENUATOR
    # process time (in microseconds)
    tau_NP, tau_P = TAU_NP, TAU_P
    time, counts = simulate_measurement(rate, target, atten,
                                        tau_NP*TAU_UNITS, tau_P*TAU_UNITS,
                                        cutoff=5*60)
    print("counts",counts)
    print("time",time)

    res = fit_tau(counts/time, np.sqrt(counts)/time)
    print("Total time to run experiment: %.2f hrs"%(np.sum(time)/3600))
    print("atten", atten, res[0])
    print("tau_NP", tau_NP, res[1])
    print("tau_P", tau_P, res[2])
    print("rate", res[3][0])
    print("drate/rate", res[3][1]/res[3][0])
    print("rate residuals", (rate - res[3][0])/res[3][1])


    rate = np.asarray(rate, 'd')
    observed, err = counts/time, np.sqrt(counts)/time
    wo = (observed[0], err[0])  # without attenuator
    wt = (observed[1], err[1])  # with attenuator
    title = (r'$\tau_{NP}=%g\,{\rm us}$,  $\tau_{P}=%g\,{\rm us}$,  ${\rm atten}=%g$'
             %(tau_NP*TAU_UNITS*1e6, tau_P*TAU_UNITS*1e6, atten))
    #return
    import pylab
    pylab.subplot(211);
    pylab.errorbar(rate, res[3][0], yerr=res[3][1], fmt='r.', label='fitted rate')
    _show_rates(rate, wo, wt, atten, title)
    pylab.subplot(212); _show_droop(rate, wo, wt, atten, title)
    import pylab; pylab.show()

def _show_rates(rate, wo, wt, atten, title):
    import pylab

    #pylab.figure()
    pylab.errorbar(rate, wt[0], yerr=wt[1], fmt='g.', label='attenuated')
    pylab.errorbar(rate, wo[0], yerr=wo[1], fmt='b.', label='unattenuated')

    pylab.xscale('log')
    pylab.yscale('log')
    pylab.xlabel('incident rate (counts/second)')
    pylab.ylabel('observed rate (counts/second)')
    pylab.legend(loc='best')
    pylab.title(title)
    pylab.grid(True)
    pylab.plot(rate, rate/atten, 'g-', label='target')
    pylab.plot(rate, rate, 'b-', label='target')

def _show_droop(rate, wo, wt, atten, title):
    import pylab

    #pylab.figure()
    pylab.errorbar(rate, wt[0]/(rate/atten), yerr=wt[1]/(rate/atten),
                   fmt='g.', label='attenuated')
    pylab.errorbar(rate, wo[0]/rate, yerr=wo[1]/rate,
                   fmt='b.', label='unattenuated', hold=True)

    pylab.xscale('log')
    pylab.xlabel('incident rate (counts/second)')
    pylab.ylabel('droop (observed rate/expected rate)')
    pylab.legend(loc='best')
    pylab.title(title)
    pylab.grid(True)

if __name__ == "__main__":
    run_sim()
