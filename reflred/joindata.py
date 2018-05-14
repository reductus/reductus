# This program is in the public domain
"""
Join reflectivity datasets with matching intent/cross section.
"""
from __future__ import print_function

from copy import copy

import numpy as np

from dataflow.lib import unit
from .refldata import Intent, ReflData, Environment
from .util import poisson_average
from .resolution import divergence, dTdL2dQ, TiTdL2Qxz

try:
    #from typing import List, Dict, Union, Sequence
    #Columns = Dict[str, List[np.ndarray]]
    #StackedColumns = Dict[str, np.ndarray]
    #IndexSet = List[int]
    pass
except ImportError:
    pass

def sort_files(datasets, key):
    # type: (List[ReflData], str) -> List[ReflData]
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


def join_datasets(group, Qtol, dQtol, by_Q=False):
    # type: (List[ReflData], float, float) -> ReflData
    """
    Create a new dataset which joins the results of all datasets in the group.

    This is a multistep operation with the various parts broken into separate
    functions.
    """
    #print "joining files in",group[0].path,group[0].name,group[0].entry
    # Make sure all datasets are normalized by the same factor.
    normbase = group[0].normbase
    assert all(data.normbase == normbase for data in group), "can't mix time and monitor normalized data"

    # Gather the columns
    fields = get_fields(group)
    env = get_env(group)
    fields.update(env)
    columns = stack_columns(group, fields)
    columns = apply_mask(group, columns)
    columns = set_QdQ(columns)

    # Group points together, either by target angles, by actual angles or by Q
    # TODO: maybe include target Q
    # TODO: check background subtraction based on trajectoryData._q
    # ----- it can't be right since Qz_target is not properly propagated
    # ----- through the join...
    if Qtol == 0. and dQtol == 0.:
        targets = get_target_values(group)
        targets = stack_columns(group, targets)
        targets = apply_mask(group, targets)
        groups = group_by_target_angles(targets)
    elif by_Q:
        groups = group_by_Q(columns, Qtol=Qtol, dQtol=dQtol)
    else:
        groups = group_by_actual_angles(columns, Qtol=Qtol, dQtol=dQtol)

    # Join the data points in the individual columns
    columns = merge_points(groups, columns, normbase)

    # Sort so that points are in display order
    # Column keys are:
    #    Qx, Qz, dQ: Q and resolution
    #    Td: detector theta
    #    Ti: incident (sample) theta
    #    dT: angular divergence
    #    L : wavelength
    #    dL: wavelength dispersion
    isslit = Intent.isslit(group[0].intent)
    isrock = Intent.isrock(group[0].intent)
    if isrock:
        # Sort detector rocking curves so that small deviations in sample
        # angle don't throw off the order in detector angle.
        keys = ('Qx', 'Qz', 'dQ')
        #keys = ('Td', 'Ti', 'L', 'dT', 'dL')
    elif isslit:
        keys = ('dT', 'L', 'dL')
    else:
        keys = ('Qz', 'dQ', 'Qx')
        #keys = ('Ti', 'Td', 'L', 'dT', 'dL')
    columns = sort_columns(columns, keys)

    data = build_dataset(group, columns)
    #print "joined",data.intent
    return data


def build_dataset(group, columns):
    # type: (List[ReflData], StackedColumns) -> ReflData
    """
    Build a new dataset from a set of columns.

    Metadata is set from the first dataset in the group.

    If there are any sample environment columns they will be added to
    data.sample.environment.
    """
    head = group[0]

    # Copy details of first file as metadata for the returned dataset, and
    # populate it with the result vectors.  Note that this is copy by reference;
    # if an array in head gets updated later, then this modification will
    # also appear in the returned data.  Not sure if this is problem...
    data = ReflData()
    for p in data._fields:
        setattr(data, p, getattr(head, p))
    for group_name, _ in data._groups:
        head_group, data_group = getattr(head, group_name), getattr(data, group_name)
        for p in data_group._fields:
            setattr(data_group, p, getattr(head_group, p))

    # Clear the fields that are no longer defined
    data.sample.angle_x_target = None
    data.sample.angle_y = None
    data.sample.rotation = None
    data.detector.angle_x_target = None
    data.detector.angle_y = None
    data.detector.rotation = None
    data.detector.counts = None
    data.detector.counts_variance = None
    data.monitor.counts_variance = None
    for k in range(1, 5):
        slit = getattr(data, 'slit%d'%k)
        slit.x = slit.y = slit.x_target = slit.y_target = None

    # summary data derived from group, or copied from head if commented
    #data.instrument
    #data.geometry
    #data.probe
    data.path = None  # no longer refers to head file
    data.uri = None  # TODO: does a reduction have a DOI?
    data.points = len(columns['v'])
    #data.channels  # unused
    #data.scale = 1.0  # unused
    #data.name
    #data.entry
    #data.description
    data.date = min(d.date for d in group)  # set date to earliest date
    data.duration = sum(d.duration for d in group)  # cumulative duration
    data.polarization = (head.polarization
                         if all(d.polarization == head.polarization for d in group)
                         else '')
    #data.normbase
    data.warnings = []  # initialize per-file history
    data.messages = []  # initialize per-file history
    #data.vlabel
    #data.vunits
    #data.vscale
    #data.xlabel
    #data.xunits
    #data.xscale
    data.mask = None  # all points are active after join
    #data.angular_resolution # averaged
    data.Qz_basis = head.Qz_basis
    data.scan_value = []  # TODO: may want Td, Ti as alternate scan axes
    data.scan_label = []
    data.scan_units = []
    data.intent = head.intent  # preserve intent
    #data.x  # read-only
    #data.dx # read-only
    #data.v  # averaged
    #data.dv # averaged
    #data.Qz # read-only  # TODO: if join by Q then Qx,Qz,dQ need to be set
    #data.Qx # read-only
    #data.dQ # read-only

    # Fill in the fields we have averaged
    data.v = columns['v']
    data.dv = columns['dv']
    data.angular_resolution = columns['dT']
    data.sample.angle_x = columns['Ti']
    data.detector.angle_x = columns['Td']
    data.slit1.x = columns['s1']
    data.slit2.x = columns['s2']
    data.detector.wavelength = columns['L']
    data.detector.wavelength_resolution = columns['dL']
    data.monitor.count_time = columns['time']
    data.monitor.counts = columns['monitor']
    data.Qz_target = columns['Qz_target']
    #data.Qz_target = None

    # Add in any sample environment fields
    data.sample.environment = {}
    for k, v in head.sample.environment.items():
        if k in columns:
            env = Environment()
            env.units = v.units
            env.average = columns[k]
            data.sample.enviroment[k] = env
            # TODO: could maybe join the environment logs
            # ----- this would require setting them all to a common start time

    return data


def get_fields(group):
    # type: (List[ReflData]) -> Columns
    """
    Extract geometry and counts from all files in group into separate fields.

    Returns a map of columns: list of vectors, with one vector for each
    dataset in the group.
    """
    columns = dict(
        s1=[data.slit1.x for data in group],
        s2=[data.slit2.x for data in group],
        dT=[data.angular_resolution for data in group],
        Ti=[data.sample.angle_x for data in group],
        Td=[data.detector.angle_x for data in group],
        L=[data.detector.wavelength for data in group],
        dL=[data.detector.wavelength_resolution for data in group],
        monitor=[data.monitor.counts for data in group],
        time=[data.monitor.count_time for data in group],
        Qz_target=[data.Qz_target for data in group],
        # using v,dv since poisson average wants rates
        v=[data.v for data in group],
        dv=[data.dv for data in group],
    )
    return columns


def get_env(group):
    # type: (List[ReflData]) -> Columns
    """
    Extract sample environment from all fields in group into separate fields.
    """
    head = group[0]
    # Gather environment variables such as temperature and field.
    # Make sure they are all in the same units.
    columns = dict((e.name, []) for e in head.sample.environment)
    converter = dict((e.name, unit.Converter(e.units)) for e in head.sample.environment)
    for data in group:
        for env_name, env_list in columns.items():
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


def stack_columns(group, columns):
    # type: (List[ReflData], Columns) -> StackedColumns
    """
    Join individual datasets into only long vector for each field in columns.
    """
    columns = dict((field, [_scalar_to_vector(part, data, field)
                            for part, data in zip(values, group)])
                   for field, values in columns.items())

    # Turn the data into arrays, masking out the points we are ignoring
    columns = dict((k, np.hstack(v)) for k, v in columns.items())
    return columns


def _scalar_to_vector(value, data, field):
    # type: (Union[np.ndarray, float], ReflData, str) -> np.ndarray
    """
    Make v a vector of length n if v is a scalar, or leave it alone.
    """
    n = len(data.v)
    if np.isscalar(value):
        return np.ones(n)*value
    elif len(value) == 1:
        return np.ones(n)*value[0]
    elif len(value) == n:
        return value
    else:
        raise ValueError("%s length does not match data length in %s%s"
                         % (field, data.name, data.polarization))


def apply_mask(group, columns):
    # type: (List[ReflData], StackedColumns) -> StackedColumns
    """
    Mask out selected points from the joined dataset.

    Note: could instead return the non-masked points as the initial index set.
    """
    masks = [data.mask for data in group]
    if any(mask is not None for mask in masks):
        masks = [(data.mask&np.isfinite(data.v) if data.mask is not None else np.isfinite(data.v))
                 for data in group]
        idx = np.hstack(masks)
        columns = dict((k, v[idx]) for k, v in columns.items())
    return columns


def set_QdQ(columns):
    # type: (StackedColumns) -> StackedColumns
    """
    Generate Q and dQ fields from angles and geometry
    """
    Ti, Td, dT = columns['Ti'], columns['Td'], columns['dT']
    L, dL = columns['L'], columns['dL']
    Qx, Qz = TiTdL2Qxz(Ti, Td, L)
    # TODO: is dQx == dQz ?
    dQ = dTdL2dQ(Td-Ti, dT, L, dL)
    columns['Qx'], columns['Qz'], columns['dQ'] = Qx, Qz, dQ
    return columns


def get_target_values(group):
    # type: (List[ReflData]) -> Columns
    """
    Get the target values for the instrument geometry.
    """
    columns = dict(
        Ti=[data.sample.angle_x_target for data in group],
        Td=[data.detector.angle_x_target for data in group],
        dT=[_target_dT(data) for data in group],
        L=[data.detector.wavelength for data in group],
        dL=[data.detector.wavelength_resolution for data in group],
    )
    return columns


def _target_dT(data):
    # type: (ReflData) -> np.ndarray
    """
    Idealized resolution based on the resolution of the target slits.
    """
    distance = abs(data.slit1.distance), abs(data.slit2.distance)
    slits = data.slit1.x_target, data.slit2.x_target
    return divergence(slits=slits, distance=distance, use_sample=False)


def group_by_target_angles(columns):
    # type: (StackedColumns) -> List[IndexSet]
    """
    Given columns of target values, group together exactly matching points.
    """
    Ti, Td, dT = columns['Ti'], columns['Td'], columns['dT']
    L, dL = columns['L'], columns['dL']
    points = {}
    for index, point in enumerate(zip(Ti, Td, dT, L, dL)):
        points.setdefault(point, []).append(index)
    return list(points.values())


def group_by_actual_angles(columns, Qtol, dQtol):
    # type: (StackedColumns, float, float) -> List[IndexSet]
    """
    Given instrument geometry columns group points by angles and wavelength.
    """
    Ti, Td, dT = columns['Ti'], columns['Td'], columns['dT']
    L, dL = columns['L'], columns['dL']
    #print "joining", Qtol, dQtol, Ti, Td, dT
    groups = [list(range(len(Ti)))]
    groups = _group_by_dim(groups, Td, Qtol*dT)
    #print("Td groups", groups)
    groups = _group_by_dim(groups, Ti, Qtol*dT)
    #print("Ti groups", groups)
    groups = _group_by_dim(groups, L, Qtol*dL)
    #print("L groups", groups)
    groups = _group_by_dim(groups, dT, dQtol*dT)
    #print("dT groups", groups)
    groups = _group_by_dim(groups, dL, dQtol*dL)
    #print("dL groups", groups)
    return groups


def group_by_Q(columns, Qtol, dQtol):
    # type: (StackedColumns, float, float) -> List[IndexSet]
    """
    Given instrument geometry columns group points by Q and resolution.
    """
    Qx, Qz, dQ = columns['Qx'], columns['Qz'], columns['dQ']
    groups = [list(range(len(Qz)))]
    groups = _group_by_dim(groups, dQ, dQtol*dQ)
    groups = _group_by_dim(groups, Qz, Qtol*dQ)
    groups = _group_by_dim(groups, Qx, Qtol*dQ)
    return groups


def _group_by_dim(index_sets, data, width):
    # type: (List[IndexSet], np.ndarray, np.ndarray) -> List[IndexSet]
    """
    Given a list of index groups, split each subgroup according to the
    dimension given in data, making sure points in the group lie within
    width of each other.

    Note that the resolution dimensions must be split before the angle
    and wavelength dimensions, otherwise there can be weirdness. When points
    with widely different resolution are joined, there will be a new output
    group triggered every time a point with tight resolution is encountered,
    splitting up a series of points with loose resolution that would otherwise
    be joined.
    """
    refinement = []
    for subgroup in index_sets:
        refinement.extend(_split_subgroup(subgroup, data, width))
    return refinement


def _split_subgroup(indices, data, width):
    # type: (IndexSet, np.ndarray, np.ndarray) -> List[IndexSet]
    """
    Split an index group according to data, returning a list of subgroups.
    """

    # If there is only one point then there is nothing to split
    if len(indices) <= 1:
        return [indices]

    # Grab the data/width subset according to indices
    data = data[indices]
    width = width[indices]
    order = np.argsort(data)  # type: Sequence[int]

    # Initialize the returned group list and the current group; set start
    # and end points so that a new group is triggered on the first point
    groups = []  # type: List[IndexSet]
    current_group = []  # type: IndexSet
    start_point = end_point = -np.inf
    for k in order:
        # Check if next point falls out of bounds, either because it is
        # beyond the range of existing points (data[k] > end_point), or
        # because the first point is outside of the range the next
        # point (data[k]-width[k] > start_point).
        if data[k] > end_point or data[k] - width[k] > start_point:
            # next point is outside the range; close the current group and
            # start a new one.  The first time through the loop the current
            # group will be empty but still a new group will be triggered.
            if current_group:
                groups.append(current_group)
            current_group = [indices[k]]
            start_point = data[k]
            end_point = data[k] + width[k]
        else:
            # next point is in the range; add it to the current group and
            # limit the end point of the group to its range
            current_group.append(indices[k])
            end_point = min(end_point, data[k]+width[k])
    groups.append(current_group)
    return groups


def merge_points(index_sets, columns, normbase):
    # type: (List[IndexSet], StackedColumns, str) -> StackedColumns
    """
    Join points together according to groups.

    Points are weighted according to normbase, which could be 'monitor'
    or 'time'.

    Note: we do not yet increase divergence when points with slightly
    different incident angles are mixed.
    """
    # Weight each point in the average by monitor.
    weight = columns[normbase]

    # build a structure to hold the results
    results = dict((k, []) for k in columns.keys())

    #for k,v in columns.items(): print k, len(v), v
    for group in index_sets:
        if len(group) == 1:
            index = group[0]
            for key, value in columns.items():
                results[key].append(value[index])
        else:
            v, dv = poisson_average(columns['v'][group], columns['dv'][group])
            results['v'].append(v)
            results['dv'].append(dv)
            results['time'].append(np.sum(columns['time'][group]))
            results['monitor'].append(np.sum(columns['monitor'][group]))
            # TODO: dQ should increase when points are mixed
            w = weight[group]
            for key, value in columns.items():
                if key not in ['v', 'dv', 'time', 'monitor']:
                    results[key].append(np.average(value[group], weights=w))

    # Turn lists into arrays
    results = dict((k, np.array(v)) for k, v in results.items())
    return results


def sort_columns(columns, keys):
    # type: (StackedColumns, Sequence[str]) -> StackedColumns
    """
    Returns the set of columns by a ordered by a list of keys.

    *columns* is a dictionary of vectors of the same length.

    *keys* is the list of columns in the order they should be sorted.
    """
    A = [columns[name] for name in reversed(keys)]
    A = np.array(A)
    index = np.lexsort(A)

    return dict((k, v[index]) for k, v in columns.items())


def demo():
    import sys
    import pylab
    import numpy; numpy.set_printoptions(linewidth=10000)
    from . import steps
    from . import nexusref
    from .util import group_by_key
    from .refldata import Intent
    if len(sys.argv) == 1:
        print("usage: python -m reflred.steps.joindata file...")
        sys.exit(1)
    pylab.hold(True)
    data = []
    for filename in sys.argv[1:]:
        try:
            entries = nexusref.load_from_uri(filename)
        except Exception as exc:
            print(str(exc) + " while loading " + filename)
            continue
        for entry in entries:
            entry = steps.mark_intent(steps.normalize(steps.divergence(entry)))
            if not Intent.isspec(entry.intent):
                continue
            #entry.plot()
            data.append(entry)
    groups = group_by_key('polarization', data).values()
    output = []
    for group in groups:
        group = sort_files(group, 'file')
        result = join_datasets(group, Qtol=0.5, dQtol=0.002)
        result.plot()
        output.append(result)
    pylab.legend()
    pylab.show()

if __name__ == "__main__":
    demo()
