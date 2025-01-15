from posixpath import basename, join
from copy import copy, deepcopy
from io import BytesIO
import numpy as np

ALL_ACTIONS = []

def cache(action):
    """
    Decorator which adds the *cached* attribute to the function.

    Use *@cache* to force caching to always occur (for example, when
    the function references remote resources, vastly reduces memory, or is
    expensive to compute.  Use *@nocache* when debugging a function
    so that it will be recomputed each time regardless of whether or not it
    is seen again.
    """
    action.cached = True
    return action

def nocache(action):
    """
    Decorator which adds the *cached* attribute to the function.

    Use *@cache* to force caching to always occur (for example, when
    the function references remote resources, vastly reduces memory, or is
    expensive to compute.  Use *@nocache* when debugging a function
    so that it will be recomputed each time regardless of whether or not it
    is seen again.
    """
    action.cached = False
    return action

def module(action):
    """
    Decorator which records the action in *ALL_ACTIONS*.

    This just collects the action, it does not otherwise modify it.
    """
    ALL_ACTIONS.append(action)

    # This is a decorator, so return the original function
    return action

#################
# Loader stuff
#################

def findPeak(qvals, counts, min_height=10, sample_width=10):
    # using first moment to get center and height
    # IGOR command: FindPeak/P/Q/M=10/R=[(temp-10),(temp+10)]
    # where 
    # /M=minLevel Defines minimum level of a peak 
    # /R=[startP,endP] Specifies point range and direction for search
    peak_index = np.argmax(counts)
    peak_q = qvals[peak_index]
    peak_val = counts[peak_index]
    if peak_val < min_height:
        return None,None
    
    central_slice = slice(peak_index-sample_width, peak_index+sample_width+1)
    central_counts = counts[central_slice]
    central_qvals = qvals[central_slice]
    peak_center = np.sum(central_qvals*central_counts)/np.sum(central_counts) 
    return {"peak_center": peak_center, "peak_value": peak_val}

@cache
@module
def LoadRawUSANS(filelist=None, check_timestamps=True, det_deadtime=7e-6, trans_deadtime=1.26e-5):
    """
    loads a data file into a RawSansData obj and returns that.

    **Inputs**

    filelist (fileinfo[]): Files to open.
    
    check_timestamps (bool): verify that timestamps on file match request

    det_deadtime {main deadtime (s)} (float): main detector deadtime, in seconds

    trans_deadtime {trans deadtime (s)} (float): transmission detector deadtime, in seconds 

    **Returns**

    output (data[]): all the entries loaded.

    2020-01-29 Brian Maranville
    """
    from reductus.dataflow.fetch import url_get
    from .loader import readUSANSNexus
    from .usansdata import USansData
    if filelist is None:
        filelist = []
    data = []
    for fileinfo in filelist:
        path, mtime, entries = fileinfo['path'], fileinfo.get('mtime', None), fileinfo.get('entries', None)
        name = basename(path)
        fid = BytesIO(url_get(fileinfo, mtime_check=check_timestamps))
        entries = readUSANSNexus(name, fid, det_deadtime=det_deadtime, trans_deadtime=trans_deadtime)
        
        data.extend(entries)

    return data

@cache
@module
def convert_to_countrate(unnormalized, do_mon_norm=True, mon0=1e6):
    """"
    Given a USansData object, normalize the data to time and the provided monitor

    **Inputs**

    unnormalized (data): data in

    do_mon_norm {normalize to mon0} (bool) : normalized detCnt to specified mon0 (otherwise just time)

    mon0 (float): provided monitor

    **Returns**

    output (data): corrected for dead time

    2020-01-28 Brian Maranville
    """

    time = unnormalized.countTime
    monitor = unnormalized.monCts

    if do_mon_norm:
        unnormalized.detCts *= mon0/monitor
    else:
        unnormalized.detCts /= time
    
    unnormalized.monCts /= time
    unnormalized.transCts /= time
        
    return unnormalized

def _findTWideCts(data, q_threshold=1e-4):
    mask = (data.Q > q_threshold)
    missing_data_warn = False

    if mask.sum() == 0:
        mask = np.zeros_like(data.Q, dtype='bool')
        mask[-4:] = True
        missing_data_warn = True

    mean_cts = data.transCts[mask].mean()
    mean_mon = data.monCts[mask].mean()

    twide = mean_cts/mean_mon

    return twide, missing_data_warn

@module
def findTWideCts(data, q_threshold=1e-4):
    """"
    Given a USansData object, find the TWide parameters.
    If no data is available above the Q threshold, uses the last 4 points and returns
    a warning in the parameters.

    **Inputs**

    data (data): data in

    q_threshold (float): use Q values larger than this to do the calculation

    **Returns**

    twide (params): corrected for dead time

    2020-01-28 Brian Maranville
    """
    from reductus.sansred.sansdata import Parameters

    twide, missing_data_warn = _findTWideCts(data, q_threshold)

    output = {"fileNumber": data.metadata["run.instFileNum"], "TWIDE": twide.x, "TWIDE_ERR": np.sqrt(twide.variance)}
    if missing_data_warn:
        output["WARNING"] = "You don't have data past 1e-4 A-1 (~2 degrees) - so Twide may not be reliable"
    
    return Parameters(params=output)

@cache
@module
def setPeakCenter(data, peak_params, peak_center=None):
    """"
    Given a USansData object and a new peak center, adjusts Q values to match the new center
    If a peak_center is specified directly, it will always be used
    Otherwise the value from the input peak_params (coming from the fit) will be used
    
    **Inputs**

    data (data): data in

    peak_params (params?): send output from findPeak to here, and the 'peak_center' will be used unless overridden

    peak_center (float*): override the value from the peak_params['peak_center']

    **Returns**

    adjusted_data (data): corrected for new peak center

    2020-01-28 Brian Maranville
    """
    peak_center = peak_center if peak_center is not None else peak_params.params['peak_center']

    data.Q -= peak_center
    data.Q_offset = peak_center

    return data

@cache
@module
def getPeakParams(data):
    """"
    Given a USansData object peak parameters (center and height) will be calculated
    
    **Inputs**

    data (data): data in

    **Returns**

    peak_params (params): peak data

    2020-01-29 Brian Maranville
    """
    from reductus.sansred.sansdata import Parameters

    peak_params = {"fileNumber": data.metadata["run.instFileNum"], "intent": data.metadata["analysis.intent"]}
    peak_params.update(findPeak(data.Q, data.detCts.x))

    return Parameters(params=peak_params)

@cache
@module
def correctData(sample, empty, bkg_level=0.0, emp_level=0.0, thick=1.0, dOmega=7.1e-7):
    """"
    Do the final data reduction.  Requires a data and empty, normalized.
    
    **Inputs**

    sample (data): data in

    empty (data): empty in

    bkg_level (float): background level

    emp_level (float): empty background level

    thick (float): thickness of sample, in cm

    dOmega (float): solid angle of detector (steradians)

    **Returns**

    corrected (data): corrected output

    corrected_info (params): correction info

    2020-01-29 Brian Maranville
    """
    from reductus.dataflow.lib.uncertainty import Uncertainty
    from .usansdata import USansCorData
    from reductus.sansred.sansdata import Parameters
    # find q-range of empty:
    empty_qmax = empty.Q.max()
    empty_qmin = empty.Q.min()
    empty_mask = np.logical_and(sample.Q >= empty_qmin, sample.Q <= empty_qmax)
    interpolated_empty = np.interp(sample.Q, empty.Q, empty.detCts.x, left=emp_level, right=emp_level)
    interpolated_empty_err = np.interp(sample.Q, empty.Q, empty.detCts.variance, left=0, right=0)
    tempI = Uncertainty(interpolated_empty, interpolated_empty_err)

    Twide_sam, _ = _findTWideCts(sample)
    Twide_emp, _ = _findTWideCts(empty)

    pkHtEMP = empty.detCts.x.max()
    pkHtSAM = sample.detCts.x.max()

    Trock = pkHtSAM / pkHtEMP
    Twide = Twide_sam / Twide_emp

    ratio = Trock / Twide

    iqCOR = sample.detCts - Trock*tempI - (1-Trock)*bkg_level

    scale = 1/(Twide*thick*dOmega*pkHtEMP)

    iqCOR *= scale

    info = {
        "Sample file": sample.metadata["run.filename"],
        "Empty file": empty.metadata["run.filename"],
        "Trock/Twide": ratio.x,
        "Thickness": thick,
        "Twide": Twide.x,
        "Trock": Trock,
        "Sample Peak Angle": getattr(sample, 'Q_offset', 0.0),
        "Empty Peak Angle": getattr(empty, 'Q_offset', 0.0),
        "Empty level": emp_level,
        "Bkg level": bkg_level,
        "dQv": sample.metadata["dQv"],
        "Start time": sample.metadata["start_time"],
        "Entry": sample.metadata["entry"],
    }

    corrected = USansCorData(metadata=info,iqCOR=iqCOR, Q=sample.Q)
    
    return corrected, Parameters(info)

@cache
@module
def correctJoinData(sample, empty, q_tol=0.01, bkg_level=0.0, emp_level=0.0, thick=1.0, dOmega=7.1e-7):
    """"
    Do the final data reduction.  Requires sample and empty datasets, normalized.
    Multiple inputs in either will be joined into one dataset before processing.
    
    **Inputs**

    sample (data[]): data in

    empty (data): empty in

    q_tol (float): values closer together than this tolerance in Q will be joined into a single point

    bkg_level (float): background level

    emp_level (float): empty background level

    thick (float): thickness of sample, in cm

    dOmega (float): solid angle of detector (steradians)

    **Returns**

    corrected (cor): corrected output

    corrected_info (params[]): correction info

    2020-01-29 Brian Maranville
    """

    from reductus.dataflow.lib.uncertainty import Uncertainty
    from .usansdata import USansCorData
    from reductus.sansred.sansdata import Parameters


    data_groups = make_groups([s.Q for s in sample])

    reduced_pairs = [correctData(s, empty, bkg_level=bkg_level, emp_level=emp_level, thick=thick, dOmega=dOmega) for s in sample]

    reduced_values = [r[0] for r in reduced_pairs]
    reduced_infos = [r[1].params for r in reduced_pairs]

    Qvals = []
    iqCOR_x = []
    iqCOR_variance = []
    for g in data_groups:
        qmean = np.array([x for x,i,j in g]).mean()
        iq = [reduced_values[i].iqCOR[j] for x,i,j in g]
        iqmean = sum(iq) / len(iq)
        Qvals.append(qmean)
        iqCOR_x.append(iqmean.x)
        iqCOR_variance.append(iqmean.variance)
    
    iqCOR = Uncertainty(iqCOR_x, iqCOR_variance)
    Qvals = np.array(Qvals)

    corrected = USansCorData(metadata=reduced_infos,iqCOR=iqCOR, Q=Qvals)
    
    return corrected, [Parameters(info) for info in reduced_infos]

@module
def crop_corrected(data, start_stop=[None, None]):
    """
    Crop USANS corrected data

    **Inputs**

    data (cor): USANS corrected input

    start_stop {Crop start and stop} (range?:x) : Select which part of the data (along x-axis) to keep

    **Returns**

    cropped (cor): cropped data

    | 2020-05-04 Brian Maranville
    """

    if start_stop is None:
        start_stop = [None, None]
    
    cropped = copy(data)
    start, stop = start_stop
    left_index = None if start is None else np.searchsorted(data.Q, start, side='left')
    right_index = None if stop is None else np.searchsorted(data.Q, stop, side='right')
    new_slice = slice(left_index, right_index)
    cropped.Q = data.Q[new_slice]
    cropped.iqCOR = data.iqCOR[new_slice]
    return cropped
    

def make_groups(xvals_list, xtol=0):
    # xvals_list is list of xvals arrays
    groups = []
    for i, xvals in enumerate(xvals_list):
        for j, x in enumerate(xvals):
            matched = False
            for g in groups:
                d = [(x-gp[0]) <= (xtol * x) for gp in g]
                if all([(x-gp[0]) <= (xtol * x) for gp in g]):
                    g.append((x,i,j))
                    matched = True
                    break
            if not matched:
                groups.append([(x,i,j)])
    return groups


            

