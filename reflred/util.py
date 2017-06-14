from __future__ import print_function

import numpy as np

from dataflow.lib import err1d

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
    from dataflow.lib.errutil import interp
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
    Return the Poisson average of a rate vector y +/- dy.

    Use *norm='monitor'* When counting against monitor (the default) or
    *norm='time'* when counting against time.

    The count rate is expressed as the number of counts in an interval $N$
    divided by the interval $M$.  The rate for the combined interval should
    match the rate you would get if you counted the entire interval at once,
    which is $\sum N_i / \sum M_i$.  We do this by inferring the counts
    and intervals from the rate and uncertainty, adding them together, and
    dividing to get the average rate over the entire interval.

    With counts and monitors both from Poisson distribution, the uncertainties
    are $\sqrt N$ and $\sqrt M$ respectively.  With error propagation, we get

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
        \Delta \bar y &=& \bar y \sqrt{1/\sum_{N_i}}
        \end{eqnarray}

    Our expression does not account for detector efficiency, attenuators
    and dead-time correction. In practice we have an additional scaling
    value $A \pm \Delta A$ for each point, giving

    .. math::
       :nowrap:

        \begin{eqnarray}
        y &=& A N/M \\
        \left(\frac{\Delta y}{y}\right)^2
            &=& \left(\frac{\Delta A}{A}\right)^2
              + \left(\frac{\Delta N}{N}\right)^2
              + \left(\frac{\Delta M}{M}\right)^2
        \end{eqnarray}

    Clearly with two inputs $y$, $\Delta y$ we cannot uniquely recover
    the four parameters $A$, $\Delta A$, $M$, $N$, and Poisson averaging
    will not work properly.  In these cases, a monitor weighted average
    is better for error propagation.  Monitor weighted averaging
    works well for everything except data with many zero counts.
    """
    dy = dy + (dy == 0)  # Protect against zero counts in division

    # Recover monitor and counts
    if norm == "monitor":
        monitors = y*(y+1)/dy**2
    else:
        monitors = y/dy**2
    monitors[y == 0] = 1./dy[y == 0]  # Special handling for 0 counts
    counts = y*monitors

    # Compute average rate
    combined_monitors, combined_counts = np.sum(monitors), np.sum(counts)
    bar_y = combined_counts/combined_monitors
    if norm == "monitor":
        if bar_y == 0:
            # then the simplification: sqrt(1/N + 1/M) is invalid,
            # use |dy| = 1/M*sqrt((dN)^2 + 1/M)
            # but dN in this case is 1.
            bar_dy = 1./combined_monitors * np.sqrt(1. + 1./combined_monitors)
        else:
            # the simplification will work in this case, sort of
            bar_dy = bar_y * np.sqrt(1./combined_counts + 1./combined_monitors)
    else:
        bar_dy = bar_y * np.sqrt(1./combined_monitors)

    #print("est. monitors:", monitors)
    #print("est. counts:", counts)
    return bar_y, bar_dy


def gaussian_average(y, dy, w, dw=0):
    bar_y, bar_y_var = err1d.average(y, dy**2, w, dw**2)
    return bar_y, np.sqrt(bar_y_var)


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


def _fetch_url_uncached(url):
    # type: (str) -> str
    import urllib2
    try:
        fd = urllib2.urlopen(url)
        ret = fd.read()
    finally:
        fd.close()
    return ret


def fetch_url(url, url_cache="/tmp"):
    """
    Fetch a file from a url.

    The content of the file will be cached in */tmp/_path_to_file.ext* for
    the url *http://path/to/file.ext*.  If *url_cache* is None, then no caching
    is performed.  Set *url_cache* to the private cache directory if you don't
    want the files cleaned by the tmp reaper.
    """
    from urlparse import urlparse
    import os

    if url_cache is None:
        return _fetch_url_uncached(url)

    cached_path = os.path.join(url_cache, urlparse(url).path.replace('/', '_'))
    if os.path.exists(cached_path):
        with open(cached_path) as fd:
            ret = fd.read()
    else:
        ret = _fetch_url_uncached(url)
        with open(cached_path, 'wb') as fd:
            fd.write(ret)
    return ret


if __name__ == "__main__":
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
