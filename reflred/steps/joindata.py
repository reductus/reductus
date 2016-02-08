# This program is in the public domain
"""
Join reflectivity datasets with matching intent/cross section.
"""
from copy import copy

import numpy as np

from .. import unit
from ..refldata import Intent, ReflData, Environment
from .util import poisson_average

def sort_files(datasets, key):
    """
    Order files by key.

    key can be one of: file, time, theta, or slit
    """
    if key == 'file':
        keyfn = lambda data: data.name
    elif key == 'time':
        import datetime
        keyfn = lambda data: (data.date + datetime.timedelta(seconds=data.monitor.start_time[0]))
    elif key == "theta":
        keyfn = lambda data: (data.sample.angle_x[0], data.detector.angle_x[0])
    elif key == "slit":
        keyfn = lambda data: (data.slit1.x, data.slit2.x)
    elif key == "none":
        return datasets
    else:
        raise ValueError("Unknown sort key %r: use file, time, theta or slit"
                         % key)
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
        keys = ('Td', 'Ti', 'dT', 'L')
    elif Intent.isslit(group[0].intent):
        keys = ('dT', 'L', 'Ti', 'Td')
    else:
        keys = ('Ti', 'Td', 'dT', 'L')
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
    #data.formula = build_join_formula(group)
    data.name = head.name
    data.v = columns['v']
    data.dv = columns['dv']
    data.angular_resolution = columns['dT']
    data.sample = copy(head.sample)
    data.sample.angle_x = columns['Ti']
    data.sample.environment = {}
    data.slit1 = copy(head.slit1)
    data.slit1.x = columns['s1']
    data.slit2 = copy(head.slit2)
    data.slit2.x = columns['s2']
    # not copying detector or monitor
    data.detector.counts = []
    data.detector.wavelength = columns['L']
    data.detector.wavelength_resolution = columns['dL']
    data.detector.angle_x = columns['Td']
    data.monitor.count_time = columns['time']
    data.monitor.counts = columns['monitor']
    data.monitor.start_time = None
    # record per-file history
    data.warnings = []
    data.messages = []

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
        s1=[data.slit1.x.astype('d') for data in group],
        s2=[data.slit2.x for data in group],
        dT=[data.angular_resolution for data in group],
        Ti=[data.sample.angle_x for data in group],
        Td=[data.detector.angle_x for data in group],
        L=[data.detector.wavelength for data in group],
        dL=[data.detector.wavelength_resolution for data in group],
        monitor=[data.monitor.counts for data in group],
        time=[data.monitor.count_time for data in group],
        # using v,dv since poisson average wants rates
        v=[data.v for data in group],
        dv=[data.dv for data in group],
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
    converter = dict((e.name,unit.Converter(e.units)) for e in head.sample.environment)
    for data in group:
        for env_name,env_list in columns.items():
            env = data.sample.environment.get(env_name, None)
            if env is not None:
                values = converter[env_name](env.average, units=env.units)
            else:
                values = None
            env_list.append(values)

    # Drop environment variables that are not defined in every file
    columns = dict((env_name, env_list)
                   for env_name, env_list in columns.items()
                   if not any(v is None for v in env_list))
    return columns


def vectorize_columns(group, columns):
    """
    Make sure we are working with vectors, not scalars
    """
    columns = dict((k, [_vectorize(part, data, k)
                       for part, data in zip(v, group)])
                   for k, v in columns.items())

    # Turn the data into arrays, masking out the points we are ignoring
    columns = dict((k, np.hstack(v)) for k, v in columns.items())
    return columns


def _vectorize(v, data, field):
    """
    Make v a vector of length n if v is a scalar, or leave it alone.
    """
    n = len(data.v)
    if np.isscalar(v):
        return [v]*n
    elif len(v) == 1:
        return [v[0]]*n
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
        columns = dict((k, v[idx]) for k, v in columns.items())
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
        if k == 'L':
            continue
        order = np.argsort(columns[k][index], kind='heapsort')
        index = index[order]
    #print "after sort",columns['dT'][index]
    return dict((k, v[index]) for k, v in columns.items())


def join_columns(columns, tolerance):
    # Weight each point in the average by monitor.
    weight = columns['monitor']

    # build a structure to hold the results
    results = dict((k, []) for k in columns.keys())

    # Merge points with nearly identical geometry by looping over the sorted
    # list, joining those within epsilon*delta of each other. The loop goes
    # one beyond the end so that the last group gets accumulated.
    current, maximum = 0, len(columns['Ti'])
    for i in range(1, maximum+1):
        T_width = tolerance*columns['dT'][current]
        L_width = tolerance*columns['dL'][current]
        # use <= in condition so that identical points are combined when
        # tolerance is zero
        if (i < maximum
                and abs(columns['dT'][i] - columns['dT'][current]) <= T_width
                and abs(columns['Ti'][i] - columns['Ti'][current]) <= T_width
                and abs(columns['Td'][i] - columns['Td'][current]) <= T_width
                and abs(columns['dL'][i] - columns['dL'][current]) <= L_width
                and abs(columns['L'][i] - columns['L'][current]) <= L_width):
            continue
        if i == current+1:
            for k, v in columns.items():
                results[k].append(v[current])
        else:
            v, dv = poisson_average(columns['v'][current:i],
                                    columns['dv'][current:i])
            results['v'].append(v)
            results['dv'].append(dv)
            results['time'].append(np.sum(columns['time'][current:i]))
            results['monitor'].append(np.sum(columns['monitor'][current:i]))
            w = weight[current:i]
            #print "join", current, i, w, tolerance
            for k, v in columns.items():
                if k not in {'v', 'dv', 'time', 'monitor'}:
                    #print "averaging", k, current, i
                    #print columns[k][current:i]
                    #print "weights", w
                    results[k].append(np.average(columns[k][current:i],
                                                 weights=w))
        current = i

    # Turn lists into arrays
    results = dict((k, np.array(v)) for k, v in results.items())
    return results


