# This program is in the public domain
"""
Join reflectivity datasets with matching intent/cross section.
"""
from copy import copy

import numpy as np

from .. import unit
from ..pipeline import Correction
from ..refldata import Intent, ReflData, Environment
from .util import indent, group_data


class Join(Correction):
    """
    Join operates on a list of datasets, returning a list with one dataset
    per intent/polarization.  When operating on a single dataset, it joins
    repeated points into single points.

    *tolerance* (default=0.1) is a scale factor on $\Delta \theta$ used to
    determine whether two angles are equivalent.  For a given tolerance
    $\epsilon$, a point at incident angle $\theta_1$ can be joined
    with one with incident angle $\theta_2$ when
    $|\theta_1 - \theta_2| < \epsilon \cdot \Delta\theta$.

    The join algorithm is greedy, so if you have a sequence of points with
    individual separation less than $\epsilon\cdot\Delta\theta$ but total
    spread greater than $\epsilon\cdot\Delta\theta$, they will be joined
    into multiple points with the final with the final point having worse
    statistics than the prior points.

    *order* is the sort order of the files that are joined.  The first
    file in the sorted list determines the metadata such as the base
    file name for the joined file.

    The joined datasets will be sorted as appropriate for the the
    measurement intent.  Masked points will be removed.
    """
    parameters = [
        ["tolerance", 0.05, "",
         "scale on dtheta used to determine whether angles are equivalent"],
        ["order", "file", "file|time|theta|slit|none",
         "sort order for joined files, which determines the name of the result"],
    ]
    def apply(self, data):
        return self.apply_list([data])[0]

    def apply_list(self, datasets):
        groups = group_data(sort_files(datasets, self.order))
        return [join_datasets(data, self.tolerance)
                for _,data in sorted(groups.items())]


def sort_files(datasets, key):
    """
    Order files by key.

    key can be one of: file, time, theta, or slit
    """
    if key == 'file':
        keyfn = lambda data: data.name
    elif key == 'time':
        import datetime
        keyfn = lambda data: data.date + datetime.timedelta(seconds=data.monitor.start_time[0])
    elif key == "theta":
        keyfn = lambda data: (data.sample.angle_x[0],data.detector.angle_x[0])
    elif key == "slit":
        keyfn = lambda data: (data.slit1.x,data.slit2.x)
    elif key == "none":
        return datasets
    else:
        raise ValueError("Unknown sort key %r: use file, time, theta or slit"%key)
    datasets = datasets[:]
    datasets.sort(key=keyfn)
    return datasets


def join_datasets(group, tolerance):
    """
    Create a new dataset which joins the results of all datasets in the group.

    This is a multistep operation with the various parts broken into separate
    functions.
    """
    # Make sure all datasets are normalized by monitor.
    assert all(data.normbase == 'monitor' for data in group)

    # Gather the columns
    columns = get_columns(group)
    env_columns = get_env(group)
    columns.update(env_columns)
    columns = vectorize_columns(group, columns)
    columns = apply_mask(group, columns)

    # Sort the columns so that nearly identical points are together
    if group[0].intent == Intent.rock4:
        # Sort detector rocking curves so that small deviations in sample
        # angle don't throw off the order in detector angle.
        keys = ('a4', 'a3', 'dT', 'L')
    elif Intent.isslit(group[0].intent):
        keys = ('dT','L','a3','a4')
    else:
        keys = ('a3', 'a4', 'dT', 'L')
    columns = sort_columns(columns, keys)
    #for k,v in sorted(columns.items()): print k,v

    # Join the data points in the individual columns
    columns = join_columns(columns, tolerance)
    #print "==after join=="
    #for k,v in sorted(columns.items()): print k,v

    data = build_dataset(group, columns)
    #print "joined",data.intent
    return data

def build_dataset(group, columns):
    """
    Build a new dataset from a set of columns.

    Metadata is set from the first dataset in the group.

    If there are any sample environment columns they will be added to
    data.sample.environment.
    """
    head = group[0]

    # Copy details of first file as metadata for the returned dataset, and
    # populate it with the result vectors.
    data = ReflData()
    for p in data.properties:
        setattr(data, p, getattr(head, p))
    data.formula = build_join_formula(group)
    data.v = columns['v']
    data.dv = columns['dv']
    data.angular_resolution = columns['dT']
    data.sample = copy(head.sample)
    data.sample.angle_x = columns['a3']
    data.sample.environment = {}
    data.slit1 = copy(head.slit1)
    data.slit1.x = columns['s1']
    data.slit2 = copy(head.slit2)
    data.slit2.x = columns['s2']
    # not copying detector or monitor
    data.detector.counts = []
    data.detector.wavelength = columns['L']
    data.detector.wavelength_resolution = columns['dL']
    data.detector.angle_x = columns['a4']
    data.monitor.count_time = columns['time']
    data.monitor.counts = columns['monitor']
    data.monitor.start_time = None
    # record per-file history
    data.warnings = []
    data.messages = []
    if len(group) > 1:
        for d in group:
            if d.warnings:
                data.warnings.append(d.name)
                data.warnings.extend(indent(msg,"| ") for msg in d.warnings)
            if d.messages:
                data.messages.append('Dataset(%s)'%d.name)
                data.messages.extend(indent(msg,"|") for msg in d.messages)
    else:
        data.warnings = group[0].warnings
        data.messages = group[0].messages

    # Add in any sample environment fields
    for k,v in head.sample.environment.items():
        if k in columns:
            env = Environment()
            env.units = v.units
            env.average = columns[k]
            data.sample.enviroment[k] = env

    return data

def build_join_formula(group):
    head = group[0].formula
    prefix = 0
    if len(group) > 1:
        try:
            while all(d.formula[prefix]==head[prefix] for d in group[1:]):
                prefix = prefix + 1
        except IndexError:
            pass
    if prefix <= 2:
        prefix = 0
    return head[:prefix]+"<"+",".join(d.formula[prefix:] for d in group)+">"

def get_columns(group):
    """
    Extract the data we care about into separate columns.

    Returns a map of columns: list of vectors, with one vector for each
    dataset in the group.
    """
    columns = dict(
        # only need to force one value to double
        s1 = [data.slit1.x.astype('d') for data in group],
        s2 = [data.slit2.x for data in group],
        dT = [data.angular_resolution for data in group],
        a3 = [data.sample.angle_x for data in group],
        a4 = [data.detector.angle_x for data in group],
        L = [data.detector.wavelength for data in group],
        dL = [data.detector.wavelength_resolution for data in group],
        monitor = [data.monitor.counts for data in group],
        time = [data.monitor.count_time for data in group],
        # using v,dv since poisson average wants rates
        v = [data.v for data in group],
        dv = [data.dv for data in group],
        )
    return columns

def get_env(group):
    """
    Extract the sample environment columns.
    """
    head = group[0]
    # Gather environment variables such as temperature and field.
    # Make sure they are all in the same units.
    columns = dict((e.name,[]) for e in head.sample.environment)
    converter = dict((e.name,unit.converter(e.units)) for e in head.sample.environment)
    for data in group:
        for env_name,env_list in columns.items():
            env = data.sample.environment.get(env_name, None)
            if env is not None:
                values = converter[env_name](env.average, units=env.units)
            else:
                values = None
            env_list.append(values)

    # Drop environment variables that are not defined in every file
    columns = dict((env_name,env_list)
                   for env_name,env_list in columns.items()
                   if not any(v is None for v in env_list))
    return columns

def vectorize_columns(group, columns):
    """
    Convert the data columns into
    Make sure we are working with vectors, not scalars
    """
    columns = dict((k,[_vectorize(part,data,k)
                       for part,data in zip(v,group)])
                   for k,v in columns.items())

    # Turn the data into arrays, masking out the points we are ignoring
    columns = dict((k,np.hstack(v)) for k,v in columns.items())
    return columns


def _vectorize(v, data, field):
    """
    Make v a vector of length n if v is a scalar, or leave it alone.
    """
    n = len(data.v)
    if np.isscalar(v):
        return [v]*n
    elif len(v) == n:
        return v
    else:
        raise ValueError("%s length does not match data length in %s%s"
                         % (field, data.name, data.polarization))

def apply_mask(group, columns):
    """
    Mask out selected points from the joined dataset.
    """
    masks = [data.mask for data in group]
    if any(mask is not None for mask in masks):
        masks = [(data.mask if data.mask is not None else np.isfinite(data.v))
                 for data in group]
        idx = np.hstack(masks)
        columns = dict((k,v[idx]) for k,v in columns.items())
    return columns




def sort_columns(columns, names):
    """
    Returns the set of columns by a ordered by a list of keys.

    *columns* is a dictionary of vectors of the same length.

    *names* is the list of keys that the columns should be sorted by.
    """
    #print "order",names
    #print "before sort",columns['dT']
    index = np.arange(len(columns[names[0]]), dtype='i')
    for k in reversed(names):
        # TODO: L,dL wrong length
        if k == 'L': continue
        order = np.argsort(columns[k][index], kind='heapsort')
        index = index[order]
    #print "after sort",columns['dT'][index]
    return dict((k,v[index]) for k,v in columns.items())


def join_columns(columns, tolerance):
    # Weight each point in the average by monitor.
    weight = columns['monitor']


    # build a structure to hold the results
    results = dict((k,[]) for k in columns.keys())

    # Merge points with nearly identical geometry by looping over the sorted
    # list, joining those within epsilon*delta of each other. The loop goes
    # one beyond the end so that the last group gets accumulated.
    current,maximum = 0,len(columns['a3'])
    for i in range(1,maximum+1):
        T_width = tolerance*columns['dT'][current]
        L_width = tolerance*columns['dL'][current]
        # use <= in condition so that identical points are combined when
        # tolerance is zero
        if (i < maximum
            and abs(columns['dT'][i] - columns['dT'][current]) <= T_width
            and abs(columns['a3'][i] - columns['a3'][current]) <= T_width
            and abs(columns['a4'][i] - columns['a4'][current]) <= T_width
            and abs(columns['dL'][i] - columns['dL'][current]) <= L_width
            and abs(columns['L'][i] - columns['L'][current]) <= L_width):
            continue
        if i == current+1:
            for k,v in columns.items():
                results[k].append(v[current])
        else:
            v,dv = poisson_average(columns['v'][current:i],columns['dv'][current:i])
            results['v'].append(v)
            results['dv'].append(dv)
            results['time'].append(np.sum(columns['time'][current:i]))
            results['monitor'].append(np.sum(columns['monitor'][current:i]))
            w = weight[current:i]
            #print "join",current,i,w,tolerance
            for k,v in columns.items():
                if k not in set(('v','dv','time','monitor')):
                    #print "averaging",k,current,i
                    #print columns[k][current:i]
                    #print "weights",w
                    results[k].append(np.average(columns[k][current:i],weights=w))
        current = i

    # Turn lists into arrays
    results = dict((k,np.array(v)) for k,v in results.items())
    return results


def poisson_average(y, dy):
    """
    Return the Poisson average of a rate vector y +/- dy

    To average y1, ..., yn, use::

        w = sum( y/dy^2 )
        y = sum( (y/dy)^2 )/w
        dy = sqrt ( y/w )

    For pure rate measurements using poisson statistics, this formula
    guarantees that rate from counting over an interval matches the
    average of counting over subintervals::

        avg(y1,...,yn) == avg(y1, avg(y2, ..., avg(yn-1,yn)...))

    Looking in detail at two counts with detector values Na, Nb and
    monitor values Ma, Mb::

        ya, dya = Na/Ma, sqrt(Na)/Ma
        yb, dyb = Nb/Mb, sqrt(Nb)/Mb
        w = ya/dya^2 + yb/dyb^2 = Ma + Mb = M
        y = ((ya/dya)^2 + (yb/dyb)^2)/w = (Na + Nb)/(Ma + Mb) = N/M
        dy = sqrt(y/w) = sqrt((N/M)/M) = sqrt(N/M^2) = sqrt(N)/M

    We are actually using a more complicated expression for rate which
    includes attenuators and for rate uncertainty which includes attenuator
    and monitor uncertainty propagated using gaussian statistics, so in
    practice it will be::

        r = A*N/M
        dr = sqrt( A^2*(1+N/M)*N/M^2 + (dA*N/M)^2 )

    Comparing the separately measured versus the combined values yeilds
    relative error on the order of 1/10^6 for high Q points::

        Na=7, Ma=2000, Nb=13, Mb=4000, Aa=Ab=1, dAa=dAb=0

    Below the critical edge, with the monitor rate 10% of the detector rate,
    the relative error is on the order of 0.02%::

        Na=20400, Ma=2000, Nb=39500, Mb=4000

    Monitor uncertainty is significant at high count rates.  In the above
    example, the rate Na/Ma relative error is found to be 2.4% when monitor
    uncertainty is included, but only 0.7% if monitor uncertainty is not
    included in the calculation.  At high Q, where uncertainty count rates
    are much lower than the monitor rate, monitor uncertainty is much less
    important.

    The effect of Poisson versus gaussian averaging is marginal, even for
    regions with extremely low counts, so long as the gaussian average is
    weighted by monitor counts.
    """
    w = np.sum(y/(dy+(dy==0))**2)
    y = np.sum( (y/(dy+(dy==0)))**2 )/w
    dy = np.sqrt(y/w)
    return y, dy


def demo():
    import pylab
    from ..examples import ng1p as group
    from .. import corrections as cor
    datasets = group.spec()+group.back()
    #for d in datasets: print d.name,d.polarization,d.intent
    #print datasets[0]; return
    #print datasets[0].detector.counts
    datasets = datasets | cor.join()
    for data in datasets: print data.intent, data.formula+data.polarization
    for data in datasets:
        data.plot()
    pylab.legend()
    pylab.show()

if __name__ == "__main__":
    demo()
