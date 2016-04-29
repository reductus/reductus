import numpy as np

def indent(text, prefix="  "):
    """
    Add a prefix to every line in a string.
    """
    return "\n".join(prefix+line for line in text.splitlines())


def group_data(datasets):
    """
    Groups data files by intent and polarization.

    Returns a dictionary with the groups, keyed by (intent,polarization).
    """
    # TODO: also need to group by temperature/field
    groups = {}
    for d in datasets:
        groups.setdefault((d.intent,d.polarization),[]).append(d)
    return groups


def group_by_xs(datasets):
    """
    Return datasets grouped by polarization cross section, and by intent within
    each polarization cross section.
    """
    cross_sections = {}
    for data in datasets:
        group = cross_sections.setdefault(data.polarization,{})
        if data.intent in group:
            raise ValueError("More than one %r in reduction"%data.intent)
        group[data.intent] = data

    #print "datasets",[":".join((d.name,d.entry,d.polarization,d.intent)) for d in datasets]
    #print "xs",cross_sections
    return cross_sections


def group_by_intent(datasets):
    """
    Return datasets grouped by polarization cross section, and by intent within
    each polarization cross section.
    """
    intents = {}
    for data in datasets:
        group = intents.setdefault(data.intent,{})
        if data.polarization in group:
            raise ValueError("More than one %r in reduction"%data.polarization)
        group[data.polarization] = data

    #print "datasets",[":".join((d.name,d.entry,d.polarization,d.intent)) for d in datasets]
    #print "xs",cross_sections
    return intents


def interp(x,xp,fp,left=None,right=None):
    """
    1-D interpolation of *x* into *(xp,fp)*.

    *xp* must be an increasing vector.  *x* can be scalar or vector.

    If *x* is beyond the range of *xp*, returns *left/right*, or the value of
    *fp* at the end points if *left/right* is not defined.

    Implemented in pure python so *fp* can be an extended numeric type such
    as complex or value+uncertainty.
    """
    is_scalar_x = np.isscalar(x)
    if len(xp) == 1:
        f = fp[np.zeros_like(x, dtype='i')]
    else:
        xp = np.asarray(xp)
        if np.any(np.diff(xp)<=0.):
            raise ValueError("interp needs a sorted list")
        if not is_scalar_x:
            x = np.asarray(x)
        idx = np.searchsorted(xp[1:-1], x)
        # Support repeated values in Xp, which will lead to 0/0 errors if the
        # interpolated point is one of the repeated values.
        p = (xp[idx+1]-x)/(xp[idx+1]-xp[idx])
        f = p*fp[idx] + (1-p)*fp[idx+1]

    if is_scalar_x:
        if x < xp[0]:
            return left if left is not None else fp[0]
        elif x > xp[-1]:
            return right if right is not None else fp[-1]
        else:
            return f
    else:
        f[x<xp[0]] = left if left is not None else fp[0]
        f[x>xp[-1]] = right if right is not None else fp[-1]
        return f


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
    if np.any(np.diff(xp)<0.):
        idx = np.argsort(xp)
        xp, fp = xp[idx], fp[idx]

    # find the midpoints of xp and use that as the index
    xp = 0.5*(xp[:-1] + xp[1:])
    return fp[np.searchsorted(xp, x)]


def plot_sa(data):
    """
    Plot spin asymmetry data.
    """
    from matplotlib import pyplot as plt
    from uncertainties.unumpy import uarray as U, nominal_values, std_devs
    from ..refldata import Intent
    # TODO: interp doesn't test for matching resolution
    data = dict((d.polarization,d) for d in data)
    pp, mm = data['++'], data['--']
    v_pp = U(pp.v, pp.dv)
    v_mm = interp(pp.x, mm.x, U(mm.v, mm.dv))
    sa = (v_pp - v_mm) / (v_pp + v_mm)
    v,dv = nominal_values(sa), std_devs(sa)
    plt.errorbar(pp.x, v, yerr=dv, fmt='.', label=pp.name)
    plt.xlabel("%s (%s)"%(pp.xlabel, pp.xunits) if pp.xunits else pp.xlabel)
    plt.ylabel(r'$(R^{++} -\, R^{--}) / (R^{++} +\, R^{--})$')

def test_nearest():
    # length 1 arrays
    xp, fp = [1], [5]
    assert (nearest(0, xp) == 0)
    assert (nearest([0], xp) == [0]).all()
    assert (nearest([0, 1], xp) == [0, 0]).all()
    assert (nearest(0, xp, fp) == fp[0])
    assert (nearest([0], xp, fp) == [fp[0]]).all()
    assert (nearest([0, 1], xp, fp) == [fp[0]]*2).all()

    # constants as arrays
    xp, fp = [1, 1, 1], [5, 5, 5]
    assert (nearest(0, xp) == 0)
    assert (nearest([0], xp) == [0]).all()
    assert (nearest([0, 1], xp) == [0, 0]).all()
    assert (nearest(0, xp, fp) == fp[0])
    assert (nearest([0], xp, fp) == [fp[0]]).all()
    assert (nearest([0, 1], xp, fp) == [fp[0]]*2).all()

    # actual arrays
    xp, fp = [1, 2, 3], [4, 5, 6]
    assert (nearest(0, xp) == 0)
    assert (nearest([0], xp) == [0]).all()
    assert (nearest([0,1,1.1,1.6,2.1,2.9,3,3.1], xp) == [0,0,0,1,1,2,2,2]).all()
    assert (nearest(0, xp, fp) == fp[0])
    assert (nearest([0], xp, fp) == [fp[0]]).all()
    assert (nearest([0,1,1.1,1.6,2.1,2.9,3,3.1], xp, fp)
            == [fp[i] for i in [0,0,0,1,1,2,2,2]]).all()

    # unsorted arrays
    xp, fp = [1, 3, 2], [4, 5, 6]
    assert (nearest(0, xp) == 0)
    assert (nearest([0], xp) == [0]).all()
    assert (nearest([0,1,1.1,1.6,2.1,2.9,3,3.1], xp) == [0,0,0,2,2,1,1,1]).all()
    assert (nearest(0, xp, fp) == fp[0])
    assert (nearest([0], xp, fp) == [fp[0]]).all()
    assert (nearest([0,1,1.1,1.6,2.1,2.9,3,3.1], xp, fp)
            == [fp[i] for i in [0,0,0,2,2,1,1,1]]).all()

