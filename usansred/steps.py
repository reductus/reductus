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

    2020-01-28 Brian Maranville
    """
    from dataflow.fetch import url_get
    from .loader import readUSANSNexus
    from .usansdata import USansData
    if filelist is None:
        filelist = []
    data = []
    for fileinfo in filelist:
        path, mtime, entries = fileinfo['path'], fileinfo.get('mtime', None), fileinfo.get('entries', None)
        name = basename(path)
        fid = BytesIO(url_get(fileinfo, mtime_check=check_timestamps))
        entries = readUSANSNexus(name, fid)
        
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
    from sansred.sansdata import Parameters

    mask = (data.Q > q_threshold)
    missing_data_warn = False

    if mask.sum() == 0:
        mask = np.zeros_like(data.Q, dtype='bool')
        mask[-4:] = True
        missing_data_warn = True

    mean_cts = data.transCts[mask].mean()
    mean_mon = data.monCts[mask].mean()

    cts = mean_cts/mean_mon

    output = {"fileNumber": data.metadata["run.instFileNum"], "TWIDE": cts.x, "TWIDE_ERR": np.sqrt(cts.variance)}
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
    from sansred.sansdata import Parameters

    peak_params = {"fileNumber": data.metadata["run.instFileNum"], "intent": data.metadata["analysis.intent"]}
    peak_params.update(findPeak(data.Q, data.detCts.x))

    return Parameters(params=peak_params)
    
