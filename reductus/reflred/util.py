from __future__ import print_function

import numpy as np

from reductus.dataflow.lib import err1d

def extend(a, b):
    """
    Extend *a* to match the number of dimensions of *b*.

    This adds dimensions to the end of *a* rather than the beginning. It is
    equivalent to *a[..., None, None]* with the right number of None elements
    to make the number of dimensions match (or np.newaxis if you prefer).

    For example::

        from numpy.random import rand
        a, b = rand(3, 4), rand(3, 4, 2)
        a + b
        ==> ValueError: operands could not be broadcast together with shapes (3,4) (3,4,2)
        c = extend(a, b) + b
        c.shape
        ==> (3, 4, 2)

    Numpy broadcasting rules automatically extend arrays to the beginning,
    so the corresponding *lextend* function is not needed::

        c = rand(3, 4) + rand(2, 3, 4)
        c.shape
        ==> (2, 3, 4)
    """
    if np.isscalar(a):
        return a
    extra_dims = (np.newaxis,)*(b.ndim-a.ndim)
    return a[(..., *extra_dims)]

def indent(text, prefix="  "):
    """
    Add a prefix to every line in a string.
    """
    return "\n".join(prefix+line for line in text.splitlines())


def group_data(datasets):
    """
    Groups data files by intent and polarization cross section.

    Returns a dictionary with the groups, keyed by (intent,polarization).
    """
    # TODO: also need to group by temperature/field
    groups = {}
    for d in datasets:
        groups.setdefault((d.intent, d.polarization), []).append(d)
    return groups


def group_by_xs(datasets):
    """
    Return datasets grouped by polarization cross section.
    """
    cross_sections = {}
    for data in datasets:
        cross_sections.setdefault(data.polarization, []).append(data)

    #print("datasets", [":".join((d.name, d.entry, d.polarization, d.intent)) for d in datasets])
    #print("xs", cross_sections)
    return cross_sections

def group_by_key(key, datasets):
    """
    Return datasets grouped by a value that can be found in a refldata file.
    Handle dotted namespace through recursive lookup.
    Handle union with comma. (e.g. key = "polarization,sample.name" would
    create group where sample.name and polarization are the same for all)
    """
    groups = {}
    key_items = key.split(",")
    for data in datasets:
        groupkey = []
        for item in key_items:
            item = item.strip()
            value = data
            for k in item.split("."):
                value = getattr(value, k)
            groupkey.append(value)
        groupkey = tuple(sorted(groupkey))
        groups.setdefault(groupkey, []).append(data)
    return groups


def group_by_intent(datasets):
    """
    Return datasets grouped by intent.
    """
    intents = {}
    for data in datasets:
        intents.setdefault(data.intent, []).append(data)

    #print("datasets", [":".join((d.name, d.entry, d.polarization, d.intent)) for d in datasets])
    #print("xs", cross_sections)
    return intents


def nearest(x, xp, fp=None):
    """
    Return the *fp* value corresponding to the *xp* that is nearest to *x*.

    If *fp* is missing, return the index of the nearest value.
    """
    if len(xp) == 1:
        if np.isscalar(x):
            return fp[0] if fp is not None else 0
        else:
            return np.array(len(x)*(fp if fp is not None else [0]))

    # if fp is not provided, want to return f as an index into the array xp
    # for the target values x, so set it to integer indices.  if fp is
    # provided, make sure it is an array.
    fp = np.arange(len(xp)) if fp is None else np.asarray(fp)


    # make sure that the xp array is sorted
    xp = np.asarray(xp)
    if np.any(np.diff(xp) < 0.):
        index = np.argsort(xp)
        xp, fp = xp[index], fp[index]

    # find the midpoints of xp and use that as the index
    xp = 0.5*(xp[:-1] + xp[1:])
    return fp[np.searchsorted(xp, x)]


def plot_sa(data):
    """
    Plot spin asymmetry data.
    """
    from matplotlib import pyplot as plt
    from uncertainties.unumpy import uarray as U, nominal_values, std_devs
    from reductus.dataflow.lib.errutil import interp
    # TODO: interp doesn't test for matching resolution
    data = dict((d.polarization, d) for d in data)
    pp, mm = data['++'], data['--']
    v_pp = U(pp.v, pp.dv)
    v_mm = interp(pp.x, mm.x, U(mm.v, mm.dv))
    sa = (v_pp - v_mm) / (v_pp + v_mm)
    v, dv = nominal_values(sa), std_devs(sa)
    plt.errorbar(pp.x, v, yerr=dv, fmt='.', label=pp.name)
    plt.xlabel("%s (%s)"%(pp.xlabel, pp.xunits) if pp.xunits else pp.xlabel)
    plt.ylabel(r'$(R^{++} -\, R^{--}) / (R^{++} +\, R^{--})$')


def test_nearest():
    # length 1 arrays
    xp, fp = [1], [5]
    assert nearest(0, xp) == 0
    assert (nearest([0], xp) == [0]).all()
    assert (nearest([0, 1], xp) == [0, 0]).all()
    assert nearest(0, xp, fp) == fp[0]
    assert (nearest([0], xp, fp) == [fp[0]]).all()
    assert (nearest([0, 1], xp, fp) == [fp[0]]*2).all()

    # constants as arrays
    xp, fp = [1, 1, 1], [5, 5, 5]
    assert nearest(0, xp) == 0
    assert (nearest([0], xp) == [0]).all()
    assert (nearest([0, 1], xp) == [0, 0]).all()
    assert nearest(0, xp, fp) == fp[0]
    assert (nearest([0], xp, fp) == [fp[0]]).all()
    assert (nearest([0, 1], xp, fp) == [fp[0]]*2).all()

    # actual arrays
    xp, fp = [1, 2, 3], [4, 5, 6]
    assert nearest(0, xp) == 0
    assert (nearest([0], xp) == [0]).all()
    assert (nearest([0, 1, 1.1, 1.6, 2.1, 2.9, 3, 3.1], xp)
            == [0, 0, 0, 1, 1, 2, 2, 2]).all()
    assert nearest(0, xp, fp) == fp[0]
    assert (nearest([0], xp, fp) == [fp[0]]).all()
    assert (nearest([0, 1, 1.1, 1.6, 2.1, 2.9, 3, 3.1], xp, fp)
            == [fp[i] for i in [0, 0, 0, 1, 1, 2, 2, 2]]).all()

    # unsorted arrays
    xp, fp = [1, 3, 2], [4, 5, 6]
    assert nearest(0, xp) == 0
    assert (nearest([0], xp) == [0]).all()
    assert (nearest([0, 1, 1.1, 1.6, 2.1, 2.9, 3, 3.1], xp)
            == [0, 0, 0, 2, 2, 1, 1, 1]).all()
    assert nearest(0, xp, fp) == fp[0]
    assert (nearest([0], xp, fp) == [fp[0]]).all()
    assert (nearest([0, 1, 1.1, 1.6, 2.1, 2.9, 3, 3.1], xp, fp)
            == [fp[i] for i in [0, 0, 0, 2, 2, 1, 1, 1]]).all()


def poisson_average(y, dy, norm='monitor'):
    r"""
    Return the Poisson average of a rate vector *y +/- dy*.

    If y, dy is multidimensional then average the first dimension, returning
    an item of one fewer dimentsions.

    Use *norm='monitor'* When counting against monitor (the default) or
    *norm='time'* when counting against time.  Use *norm='none'* if *y, dy*
    is unnormalized, and the poisson sum should be returned. Use *norm='gauss'*
    for the simple weighted gaussian average.

    The count rate is expressed as the number of counts in an interval $N$
    divided by the interval $M$.  The rate for the combined interval should
    match the rate you would get if you counted for the entire interval,
    which is $\sum N_i / \sum M_i$.  We do this by inferring the counts
    and intervals from the rate and uncertainty, adding them together, and
    dividing to get the average rate over the entire interval.

    With counts $N$ and monitors $M$ both from Poisson distributions, the
    uncertainties are $\sqrt N$ and $\sqrt M$ respectively, and gaussian
    error propagation gives

    .. math::
       :nowrap:

        \begin{eqnarray}
        y &=& N/M \\
        \left(\frac{\Delta y}{y}\right)^2
            &=& \left(\frac{\Delta N}{N}\right)^2
              + \left(\frac{\Delta M}{M}\right)^2 \\
            &=& \left(\frac{1}{N}\right)
              + \left(\frac{1}{M}\right) \\
        \Delta y &=& y \sqrt{1/N + 1/M}
        \end{eqnarray}

    Inverting, we get

    .. math::
       :nowrap:

        \begin{eqnarray}
        M &=& y (y+1) / \Delta y^2 \\
        N &=& y M
        \end{eqnarray}

    When counts are zero, $y = 0$ and $M = 0$ according to the above formula.
    To correctly average intervals that may include zero counts, we need to
    be sure that the count uncertainty $\Delta N = 1$ when $N = 0$, which
    leads to a count rate of $0 \pm 1/M$, and the formula above needs to be
    adjusted accordingly, with $M = 1/ \Delta y$ when $N = 0$.

    To average a group of measurements $y_1, \ldots, y_n$ we first
    convert to counts and monitors, then set the rate to the sum of
    the counts over the sum of the monitors.  This gives

    .. math::
       :nowrap:

        \begin{eqnarray}
        M_i &=& y_i (y_i + 1) / \Delta y_i^2 \\
        N_i &=& y_i M_i \\
        \bar y &=& \sum N_i / \sum M_i \\
        \Delta \bar y &=& \bar y \sqrt{1/\sum_{N_i} + 1/\sum_{M_i}}
        \end{eqnarray}

    When counting against time the monitor uncertainty $\Delta M$ is
    effectively zero compared to uncertainty in the counts, and so
    the formulas are a little simpler:

    .. math::

        y &= N/M \\
        \Delta y &= y \sqrt{1/N} \\
        M &= y / \Delta y^2 \\
        N &= y M

    Again, zero counts leads to $M = 1 / \Delta y$.

    Averaging gives

    .. math::
       :nowrap:

        \begin{eqnarray}
        M_i &=& y_i / \Delta y_i^2 \\
        N_i &=& y_i M_i \\
        \bar y &=& \sum N_i / \sum M_i \\
        \Delta \bar y &=& \bar y \sqrt{1/\sum N_i}
        \end{eqnarray}

    This algorithm is robust against scale factors, such as detector
    efficiency, attenuators and dead-time correction. Assume the underlying
    rate $r$ for the averaged points is identical (otherwise why are you mixing
    them?) with an independent scale factor $C_i$ applied to each point. Then

    .. math::
        :nowrap:

        \begin{eqnarray}
        y_i' &=& C_i N_i/M_i \\
        \Delta y_i' &=& C_i \sqrt{N_i}/M_i \\
        M_i' &=& y_i' / \Delta y_i^2' = M_i/C_i \\
        N_i' &=& y_i' M_i' = N_i
        \end{equnarray}

    and

    .. math::
        :nowrap:

        \begin{eqnarray}
        r  &\approx& C_i N_i / M_i \Rightarrow M_i/C_i \approx N_i/r \\
        M^{+} &=& \sum M_i' \approx \sum N_i / r \\
        N^{+} &=& \sum N_i' = \sum N_i \\
        \bar y' &=& N^{+} / M^{+} \approx r \\
        \Delta \bar y' = \sqrt{\bar y' / M^{+}} = \sqrt{N^{+}} / M^{+} \approx r / \sqrt{\sum N_i}

    That is, $\bar y', \Delta \bar y'$ will be computed from the scaled data,
    again with uncertainty proportional to $\sqrt{N}$.

    Monte Carlo experiments confirm that this holds in practice, giving
    reasonable values for the signal when subtracting mixed background from
    mixed signal+background, even when signal rate and background rate vary
    amongst the points measured. This is not true for Gaussian averaging, which
    fails when the counts are approximately less than 100.
    """
    if norm not in ("monitor", "time", "gauss", "none"):
        raise ValueError("expected norm to be time, monitor or none")

    # Check whether we are combining rates or counts.  If it is counts,
    # then simply sum them, and sum the uncertainty in quadrature. This
    # gives the expected result for poisson statistics, with counts over
    # the combined interval having variance equal to the sum of the counts.
    # It even gives correct results for very low count rates with many of
    # the individual counts giving zero, so long as variance on zero counts
    # is set to zero rather than one.
    if norm == "none":
        bar_y = np.sum(y, axis=0)
        bar_dy = np.sqrt(np.sum(dy**2, axis=0))
        return bar_y, bar_dy

    dy = dy + (dy == 0)  # Protect against zero counts in division
    if norm == "gauss":
        Swx = np.sum(y/dy**2, axis=0)
        Sw = np.sum(dy**-2, axis=0)
        bar_y = Swx / Sw
        bar_dy = 1/np.sqrt(Sw)
        return bar_y, bar_dy

    # Recover monitor and counts
    monitors = y*(y+1)/dy**2 if norm == "monitor" else y/dy**2 # if "time"
    monitors[y == 0] = 1./dy[y == 0]  # Special handling for 0 counts
    counts = y*monitors

    # Compute average rate
    combined_monitors = np.sum(monitors, axis=0)
    combined_counts = np.sum(counts, axis=0)
    bar_y = combined_counts/combined_monitors
    if norm == "time":
        bar_dy = np.sqrt(bar_y/combined_monitors)
    elif np.isscalar(bar_y):
        if bar_y == 0:
            # When bar_y is zero then 1/N is undefined and so sqrt(1/N + 1/M) fails.
            # Instead use |dy| = 1/M*sqrt((dN)^2 + 1/M) with dN = 1.
            bar_dy = 1./combined_monitors * np.sqrt(1. + 1./combined_monitors)
        else:
            # When bar_y is not zero then use |dy| = N/M * sqrt(1/N + 1/M)
            bar_dy = bar_y * np.sqrt(1./combined_counts + 1./combined_monitors)
    else:
        # Following the scalar case above, first build bar_dy assuming
        # that y is zero since it works for all y, then fill in the values
        # for y not zero. Can't do this the other way since the expression
        # for y not zero will raise errors when y is zero.
        bar_dy = 1./combined_monitors * np.sqrt(1. + 1./combined_monitors)
        idx = (bar_y != 0)
        bar_dy[idx] = bar_y[idx] * np.sqrt(1./combined_counts[idx]
                                           + 1./combined_monitors[idx])

    #print("est. monitors:", monitors)
    #print("est. counts:", counts)
    #print("poisson avg", counts.shape, bar_y.shape, bar_dy.shape)
    return bar_y, bar_dy


def gaussian_average(y, dy, w, dw=0):
    bar_y, bar_y_var = err1d.average(y, dy**2, w, dw**2)
    return bar_y, np.sqrt(bar_y_var)

def demo_sub():
    """
    Check subtraction with mixed background and mixed scale.

    The assumption that $r$ is fixed does not hold when binning $Q$ for
    Candor. Both the signal (due to varying resolution) and the background
    due to measurement geometry, detector properties, etc. vary from point
    to point, and so the simplification that $M^{+} \approx \sum N_i / r$
    no longer holds.

    Instead we want the resulting signal to be the weighted average of the
    different signals when mixing signal+background and subtracting the
    mixed background.
    """
    from numpy import mean, std, sqrt
    from numpy.random import poisson

    NP = 5e-6  # 5 us non-paralyzing dead time
    def deadtime(r):
        return 1/(1 + r*NP)

    def _sim_one(spec, back, slit, spec_time, back_time):
        s = (spec+back)*slit
        b = back*slit
        S = poisson(s*deadtime(s)*spec_time)
        B = poisson(b*deadtime(b)*back_time)
        Sscale = spec_time*slit*deadtime(s)
        Bscale = back_time*slit*deadtime(b)
        # Be sure to account for uncertainty on zero counts.
        Sr, dSr = S/Sscale, np.sqrt(S+(S==0))/Sscale
        Br, dBr = B/Bscale, np.sqrt(B+(B==0))/Bscale
        Sm, dSm = poisson_average(Sr, dSr, norm='time')
        Bm, dBm = poisson_average(Br, dBr, norm='time')
        sub = Sm - Bm
        dsub = np.sqrt(dSm**2 + dBm**2)
        #print(s, S, Sscale, Sr, Sm)
        #print(b, B, Bscale, Br, Bm)
        #print(sub, dsub)
        return sub, dsub

    def _sim(spec, back, slit, t=100, n=10000):
        spec_time, back_time = np.full_like(spec, t), np.full_like(spec, t)
        target = np.sum(spec*slit)/np.sum(slit)
        out = [_sim_one(spec, back, slit, spec_time, back_time)
               for _ in range(n)]
        out = np.asarray(out)
        print("target %.4g r %.4g +/- %.2g, dr %.2g"
              % (target, mean(out[:, 0]), std(out[:, 0]), sqrt(mean(out[:, 1]**2))))

    k = 40
    spec = np.random.rand(k)*1e-7 + 1e-6
    back = np.random.rand(k)*1e-6
    slit = np.linspace(1e6, 4e6, k)

    if 0:
        spec = np.array([1e-6, 1.1e-6, 0.9e-6])  # a little variation due to resolution
        back = np.array([1e-8, 1e-6, 1e-7]) # high variation to see what happens
        slit = np.array([1e6, 2e6, 3e6]) # a lot of variation due to spectrum

    point_time = 3
    #print("for spec", spec, "back", back)
    _sim(spec, back, slit, n=1000, t=point_time)
    print("back /10")
    _sim(spec, back/100, slit, n=1000, t=point_time)
    print("back x100")
    _sim(spec, back*100, slit, n=1000, t=point_time)

def demo_error_prop(title, rate, monitors, attenuators=None,
                    norm='monitor'):
    """
    Compare point averaging algorithms on simulated data.

    *title* is the label for the comparison.

    *rate* is the underlying count rate.

    *monitors* is the set of counting intervals, or counting time if
    Plugging in some numbers combining two counts, one for 2000 monitors
    and one for 4000 monitors, we can compute the difference between
    measuring the values separately and measuring them together.  Using
    count rates which are low relative to the monitor yields a relative
    error on the order of 1/10^6:

        Na=7, Ma=2000, Nb=13, Mb=4000, Aa=Ab=1, dAa=dAb=0

    When count rates are high, such as with a direct beam measurement where
    the monitor rate 10% of the detector rate, the relative error is on
    the order of 0.02%::

        Na=20400, Ma=2000, Nb=39500, Mb=4000

    Monitor uncertainty is significant at high count rates.  In the above
    example, the rate uncertainty dr/r for Na/Ma is found to be 2.4% when
    monitor uncertainty is included, but only 0.7% if monitor uncertainty is
    not included in the calculation.  At high Q, where uncertainty count rates
    are much lower than the monitor rate, monitor uncertainty is much less
    important.

    The effect of Poisson versus gaussian averaging is marginal, even for
    regions with extremely low counts, so long as the gaussian average is
    weighted by monitor counts.
    """
    from uncertainties import ufloat
    from uncertainties.unumpy import uarray, nominal_values as uval, \
        std_devs as udev
    from numpy.random import poisson

    #norm='time'
    #norm='monitor'
    time_err = 0
    #time_err = 0.1

    use_attenuators = attenuators is not None
    monitors = np.array(monitors, 'd')
    if norm == 'monitor':
        umonitors = uarray(monitors, np.sqrt(monitors))
    else:
        umonitors = uarray(monitors, time_err)
    if use_attenuators:
        uattenuators = uarray(*list(zip(*attenuators)))
    else:
        uattenuators = uarray(monitors/monitors, 0.*monitors)
    expected = rate*monitors/uval(uattenuators)
    # TODO: simulation is not correct for count by monitor
    counts = poisson(expected)    # Simulated counts
    #counts = expected   # Non-simulated counts
    #ucounts = uarray(counts, np.sqrt(counts + (counts==0)))
    #ucounts = uarray(counts + (counts==0), np.sqrt(counts + (counts==0)))
    ucounts = uarray(counts, np.sqrt(counts))
    incident = ucounts*uattenuators

    print("="*10, title+", rate=%g,"%rate, \
          "median counts=%d"%np.median(counts), "="*10)

    # rate averaged across different counting intervals
    y = incident/umonitors
    y_ave = poisson_average(uval(y), udev(y), norm=norm)
    y_gm = np.sum(monitors*y)/np.sum(monitors)
    y_ave = ufloat(*y_ave)
    y_g = np.mean(y)

    # rate estimated from full counting time

    tin = (np.sum(incident) if use_attenuators
           else ufloat(np.sum(counts), np.sqrt(np.sum(counts))))
    if norm == 'monitor':
        tmon = ufloat(np.sum(monitors), np.sqrt(np.sum(monitors)))
    else:
        tmon = ufloat(np.sum(monitors), len(monitors)*time_err)
    direct = tin/tmon

    #print("monitors:", monitors)
    #print("counts:", counts)
    #print("incident:", incident)
    if use_attenuators:
        print("attenuators:", list(zip(*attenuators))[0])
    def show(label, r, tag=""):
        if r is direct:
            rel = ""
        else:
            rel = (" diff: (%.1f,%.1f)%% "
                   % (100*(r.n-direct.n)/direct.n, 100*(r.s-direct.s)/direct.s))
        print(label, "r:", r, " dr/r: %.2f%%"%(100*r.s/r.n), rel, tag)
    show("Combined", direct)
    show("Poisson ", y_ave)
    show("Gaussian", y_g)
    show("Gaussian", y_gm, "monitor weighted")

    # again without monitor uncertainty
    if 0:
        y2 = incident/monitors
        y2_ave = ufloat(*poisson_average(uval(y2), udev(y2)))
        y2_g = np.mean(y2)
        show("Separate", y2_ave, "no monitor uncertainty")
        show("Gaussian", y2_g, "no monitor uncertainty")

if __name__ == "__main__":
    if 0:
        demo_error_prop("mixed monitor", 10.0, [2000, 2000, 4000])
        demo_error_prop("mixed monitor", 1.0, [2000, 2000, 4000])
        demo_error_prop("mixed monitor", 0.035, [2000, 2000, 4000])
        demo_error_prop("mixed monitor", 0.0035, [2000, 2000, 4000])
        #demo_error_prop("mixed monitor", 0.00035, [2000, 2000, 4000])
        demo_error_prop("same monitor", 10.0, [2000]*700)
        demo_error_prop("same monitor", 1.0, [2000]*700)
        demo_error_prop("same monitor", 0.035, [2000]*700)
        demo_error_prop("same monitor", 0.0035, [2000]*700)
        demo_error_prop("same monitor", 0.00035, [2000]*700)
        demo_error_prop("attenuators", 10.0, [2000, 2000, 4000], [(1, 0), (12, 0.2), (12, 0.2)])
        demo_error_prop("attenuators", 10.0, [2000, 4000], [(12, 0.2), (122, 0.2)])
    else:
        demo_sub()
