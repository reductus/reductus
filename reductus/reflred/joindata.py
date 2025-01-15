# This program is in the public domain
"""
Join reflectivity datasets with matching intent/cross section.
"""
from __future__ import print_function

from copy import deepcopy

import numpy as np

from reductus.dataflow.lib import unit
from .refldata import Intent, ReflData, Environment
from .util import poisson_average, extend
from .resolution import divergence_simple, dTdL2dQ, TiTdL2Qxz

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
    # type: (List[ReflData], float, float, bool) -> ReflData
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
    #    Li: monochromator wavelength
    #    Ld: detector wavelength
    #    dL: wavelength dispersion
    isslit = Intent.isslit(group[0].intent)
    isrock = Intent.isrock(group[0].intent)
    if isrock:
        # Sort detector rocking curves so that small deviations in sample
        # angle don't throw off the order in detector angle.
        keys = ('Qx', 'Qz', 'dQ')
        #keys = ('Td', 'Ti', 'Ld', 'dT', 'dL')
    elif isslit:
        keys = ('dT', 'Ld', 'dL')
    else:
        keys = ('Qz', 'dQ', 'Qx')
        #keys = ('Ti', 'Td', 'Ld', 'dT', 'dL')
    columns = sort_columns(columns, keys)

    data = build_dataset(group, columns, normbase)
    #print "joined",data.intent
    return data


def build_dataset(group, columns, norm):
    # type: (List[ReflData], StackedColumns, str) -> ReflData
    """
    Build a new dataset from a set of columns.

    Metadata is set from the first dataset in the group.

    If there are any sample environment columns they will be added to
    data.sample.environment.
    """
    head = group[0]

    # Copy details of first file as metadata for the returned dataset.
    # Note: using deepcopy since this is going to update subgroup
    # data such as data.slit1.x.
    data = deepcopy(group[0])
    ## Could instead do a semi-deep copy using info from the group:
    #data = copy(group[0])
    #for group_name, _ in data._groups:
    #    setattr(data, group_name, copy(getattr(data, group_name)))

    # Clear the fields that are no longer defined
    data.sample.angle_y = None
    data.sample.rotation = None
    data.detector.angle_y = None
    data.detector.rotation = None
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

    # Fill in rates and monitors.
    # Note: we are not tracking monitor variance, so assume it is equal
    # to monitor counts (dm^2 = m).  This does not account for monitor
    # scaling due to dead time correction, etc.  In practice it doesn't
    # matter since we've already normalized the counts to a count rate
    # and we don't need detector counts or variance.
    v, dv, m, t = columns['v'], columns['dv'], columns['monitor'], columns['time']
    dmsq = m
    data.v = v
    data.dv = dv
    data.monitor.count_time = t
    data.monitor.counts = m
    data.monitor.counts_variance = dmsq
    data.monitor.roi_counts = columns['roi']
    data.monitor.roi_variance = columns['roi']
    data.monitor.source_power = columns['source_power']
    data.monitor.source_power_variance = columns['source_power_variance']


    # Assign a value to detector counts. We need this if we norm after join.
    if norm == "none":
        # v = counts, dv = dcounts
        data.detector.counts = v
        data.detector.counts_variance = dv**2
    elif norm == "time":
        # v = counts/time, dv = dcounts/time
        data.detector.counts = v * extend(t, v)
        data.detector.counts_variance = (dv * extend(t, dv))**2
    elif norm == "monitor":
        # v = counts/monitor, (dv/v)^2 = (dcounts/counts)^2+(dmonitor/monitor)^2
        # => dc^2 = (m dv)^2 - (v dm)^2
        data.detector.counts = v * extend(m, v)
        data.detector.counts_variance = (extend(m, dv)*dv)**2 - v**2*extend(dmsq,v)

    # Fill in the fields we have averaged
    data.sample.angle_x = columns['Ti']
    data.detector.angle_x = columns['Td']
    data.sample.angle_x_target = columns['Ti_target']
    data.detector.angle_x_target = columns['Td_target']
    data.slit1.x = columns['s1']
    data.slit2.x = columns['s2']
    data.slit3.x = columns['s3']
    data.slit4.x = columns['s4']
    # TODO: cleaner handling of candor data
    # Angular resolution may be stored separately from dT in the joined set
    # if it is multidimensional or dT is set to something else for grouping.
    res = 'angular_resolution' if 'angular_resolution' in columns else 'dT'
    data.angular_resolution = columns[res]
    # Some fields may not have been in the original data
    if data.Qz_target is not None:
        data.Qz_target = columns['Qz_target']
    if data.monochromator.wavelength is not None:
        data.monochromator.wavelength = columns['Li']
    if data.detector.wavelength is not None:
        # On candor data.detector.wavelength has shape [1, 2, 54] since it is
        # constant for all measurement points. Since Ld and dL need to be
        # scalars for grouping it is inconvenient to maintain the
        # full wavelength for each frame, so we instead assume that any time
        # the wavelength is multidimensional then it is constant. Further,
        # we assume that the constant is included in the group[0] metadata
        # we use as the basis of our return value.
        if getattr(data.detector.wavelength, 'ndim', 0) < 2:
            data.detector.wavelength = columns['Ld']
            data.detector.wavelength_resolution = columns['dL']

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
        s3=[data.slit3.x for data in group],
        s4=[data.slit4.x for data in group],
        Ti=[data.sample.angle_x for data in group],
        Td=[data.detector.angle_x for data in group],
        dT=[data.angular_resolution for data in group],
        Li=[data.monochromator.wavelength for data in group],
        Ld=[data.detector.wavelength for data in group],
        dL=[data.detector.wavelength_resolution for data in group],
        monitor=[data.monitor.counts for data in group],
        roi=[data.monitor.roi_counts for data in group],
        source_power=[data.monitor.source_power for data in group],
        source_power_variance=[data.monitor.source_power_variance for data in group],
        time=[data.monitor.count_time for data in group],
        Ti_target=[data.sample.angle_x_target for data in group],
        Td_target=[data.detector.angle_x_target for data in group],
        Qz_target=[data.Qz_target for data in group],
        # using v,dv since poisson average wants rates
        v=[data.v for data in group],
        dv=[data.dv for data in group],
    )
    # TODO: cleaner way of handling multi-channel detectors
    if columns['v'][0].ndim > 1:
        # For candor analysis (and anything else with an nD detector), pick
        # a particular detector channel to use as the basis for merging
        # detector frames. This has only been tested on Candor so far, and
        # may need to change if we want to handle overlapping frames in a
        # traditional detector with a psd.

        # Save the angular divergence since it may be multidimensional, and
        # we will want to paste it in to the joined dataset. We will replace
        # dT with a scalar for the purposes of grouping frames.
        columns['angular_resolution'] = columns['dT']

        # Make dT a scalar. Use S1 rather than dT since candor does not yet
        # compute divergence properly.  Otherwise use the first channel of dT.
        columns['dT'] = columns['s1']
        #columns['dT'] = [v.flat[0] for v in columns['dT']]

        # Pick the first channel of L, dL.  Not picking a column since they are
        # constant across all frames, and since the column stacker automatically
        # extends a scalar to a vector with one entry per frame.
        columns['Ld'] = [v.flat[0] for v in columns['Ld']]
        columns['dL'] = [v.flat[0] for v in columns['dL']]

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

    # Turn the data into arrays.
    #for k, v in columns.items(): print(f"{k}:", [vk.shape for vk in v])
    columns = dict((k, np.concatenate(v, axis=0)) for k, v in columns.items())
    return columns


def _scalar_to_vector(value, data, field):
    # type: (Union[np.ndarray, float], ReflData, str) -> np.ndarray
    """
    Make v a vector of length n if v is a scalar, or leave it alone.
    """
    n = len(data.v)
    if value is None:  # Convert missing data to NaN
        value = np.nan
    if np.isscalar(value) or len(value) == 1:
        return np.repeat(value, n, axis=0)
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
    Ld, dL = columns['Ld'], columns['dL']
    #print("set_QdQ", [v.shape for v in (Ti, Td, dT, Ld, dL)])
    Qx, Qz = TiTdL2Qxz(Ti, Td, Ld)
    # TODO: is dQx == dQz ?
    dQ = dTdL2dQ(Td-Ti, dT, Ld, dL)
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
        Ld=[data.detector.wavelength for data in group],
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
    return divergence_simple(slits=slits, distance=distance, use_sample=False)


def group_by_target_angles(columns):
    # type: (StackedColumns) -> List[IndexSet]
    """
    Given columns of target values, group together exactly matching points.
    """
    Ti, Td, dT = columns['Ti'], columns['Td'], columns['dT']
    Ld, dL = columns['Ld'], columns['dL']
    points = {}
    for index, point in enumerate(zip(Ti, Td, dT, Ld, dL)):
        points.setdefault(point, []).append(index)
    return list(points.values())


def group_by_actual_angles(columns, Qtol, dQtol):
    # type: (StackedColumns, float, float) -> List[IndexSet]
    """
    Given instrument geometry columns group points by angles and wavelength.
    """
    Ti, Td, dT = columns['Ti'], columns['Td'], columns['dT']
    Ld, dL = columns['Ld'], columns['dL']
    #print "joining", Qtol, dQtol, Ti, Td, dT
    groups = [list(range(len(Ti)))]
    groups = _group_by_dim(groups, Td, Qtol*dT)
    #print("Td groups", groups)
    groups = _group_by_dim(groups, Ti, Qtol*dT)
    #print("Ti groups", groups)
    groups = _group_by_dim(groups, Ld, Qtol*dL)
    #print("Ld groups", groups)
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
    # Weight each point by monitor/time/counts
    if normbase == "none":
        # if weighting by counts then use the counts across the entire
        # detector as the weight.  This is a just a proxy for time/monitor
        # weighting but using the measured data, assuming the same conditions
        # give the same count rate.
        counts = columns['v']
        ndim = counts[0].ndim
        if ndim == 1:
            weight = counts
        else:
            axis = tuple(range(1, ndim))
            weight = [np.sum(v, axis=axis) for v in counts]
    else:
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
            v, dv = poisson_average(
                columns['v'][group], columns['dv'][group], norm=normbase)
            results['v'].append(v)
            results['dv'].append(dv)
            results['time'].append(np.sum(columns['time'][group]))
            results['monitor'].append(np.sum(columns['monitor'][group]))
            # TODO: dQ should increase when points are mixed (see MERGE below)
            w = weight[group]
            for key, value in columns.items():
                if key not in ['v', 'dv', 'time', 'monitor']:
                    results[key].append(np.average(value[group], weights=w, axis=0))

    # Turn lists into arrays
    results = dict((k, np.array(v)) for k, v in results.items())
    return results

# MERGE variance
#
# There is a simple expression for the moments of a mixture of distributions:
#     T = (sum wk . T) / (sum wk)
#     dT^2 = (sum wk . (dTk^2 + Tk^2)) / (sum wk) - T^2
# See: https://en.wikipedia.org/wiki/Mixture_density#Moments
#
# This formula should be applied to angular distribution since that is
# the quantity being mixed when combining measurements at slightly
# different angles.

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
    import matplotlib.pyplot as plt
    from . import steps
    from .load import setup_fetch, fetch_uri
    from .util import group_by_key
    if len(sys.argv) == 1:
        print("usage: python -m reflred.joindata file...")
        sys.exit(1)
    np.set_printoptions(linewidth=10000)
    setup_fetch()
    data = []
    for uri in sys.argv[1:]:
        try:
            entries = fetch_uri(uri)
        except Exception as exc:
            print(str(exc) + " while loading " + uri)
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
    plt.legend()
    plt.show()

if __name__ == "__main__":
    demo()
