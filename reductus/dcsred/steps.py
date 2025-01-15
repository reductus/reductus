import os
import json
from posixpath import basename, join
from copy import copy, deepcopy
from io import BytesIO
import numpy as np
from time import time,strftime

# Action names
__all__ = [] # type: List[str]

# Action methods
ALL_ACTIONS = [] # type: List[Callable[Any, Any]]

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
    __all__.append(action.__name__)

    # Sort modules alphabetically
    ALL_ACTIONS.sort(key=lambda action: action.__name__)
    __all__.sort()

    # This is a decorator, so return the original function
    return action

@module
def LoadDCS(filelist=None, check_timestamps=True):
    """
    loads a data file into a SansData obj and returns that.
    Checks to see if data being loaded is 2D; if not, quits

    **Inputs**

    filelist (fileinfo[]): Files to open.
    
    check_timestamps (bool): verify that timestamps on file match request

    **Returns**

    output (raw[]): all the entries loaded.

    2018-04-25 Brian Maranville
    """
    from reductus.dataflow.fetch import url_get
    from .dcsdata import readDCS
    if filelist is None:
        filelist = []
    data = []
    for fileinfo in filelist:
        path, mtime, entries = fileinfo['path'], fileinfo.get('mtime', None), fileinfo.get('entries', None)
        name = basename(path)
        fid = BytesIO(url_get(fileinfo, mtime_check=check_timestamps))
        entry = readDCS(name, fid)
        data.append(entry)

    return data

@module
def RawToEfTwoTheta(rawdata):
    """
    converts raw data to Q,E

    **Inputs**

    rawdata (raw): data in

    **Returns**

    output (ef2th): modified data

    2018-04-29 Daniel Pajerowski
    """
    from io import BytesIO
    from .dcsdata import EfTwoThetaData
    from .dcs_detector_info import detector_info_txt
    detInfo = np.genfromtxt(BytesIO(detector_info_txt.encode()), skip_header=1)#, skip_footer=17)
    detToTwoTheta = detInfo[:,9] # 10th column

    masterSpeed = rawdata.metadata['ch_ms']
    speedRatDenom = rawdata.metadata['ch_srdenom']
    t_SD_min = rawdata.metadata['tsdmin']
    t_channel = np.arange(rawdata.histodata.shape[0])
    ef = Ef_from_timechannel(t_channel, t_SD_min, speedRatDenom, masterSpeed)
    
    new_metadata = deepcopy(rawdata.metadata)
    new_ef2th = EfTwoThetaData(rawdata.name, rawdata.histodata, ef=ef, twotheta=detToTwoTheta, metadata=new_metadata)
    return new_ef2th

@module
def RawToEQ(rawdata):
    """
    converts raw data to Q,E

    **Inputs**

    rawdata (raw): data in

    **Returns**

    output (eq): modified data

    2018-04-28 Daniel Pajerowski
    """
    from io import BytesIO
    from .dcsdata import EQData
    from .dcs_detector_info import detector_info_txt
    detInfo = np.genfromtxt(BytesIO(detector_info_txt.encode()), skip_header=1)#, skip_footer=17)
    detToTwoTheta = detInfo[:,9] # 10th column

    ch_wl = rawdata.metadata['ch_wl']
    Ei = Elam(ch_wl)
    ki = kE(Ei)
    dE = abs(0.5*(-0.10395+0.05616 *Ei+0.00108 *Ei**2)) #take the putative resolution and halve it
    masterSpeed = rawdata.metadata['ch_ms']
    speedRatDenom = rawdata.metadata['ch_srdenom']
    t_SD_min = rawdata.metadata['tsdmin']

    #binning resolution
    Q_max = Qfunc(ki,ki,150)
    Q_min = 0
    E_bins = np.linspace(-Ei, Ei, int(int(2*Ei/dE)*0.5) )
    Q_bins = np.linspace(Q_min,Q_max,int(301*0.5))

    #for every point in {timechannel, detectorchannel} space, map into a bin of {E,Q} space
    #remember, data is organized as data[detectorchannel][timechannel]
    data = rawdata.histodata.T
    i,j = np.indices(data.shape)
    ef = Ef_from_timechannel(j, t_SD_min, speedRatDenom, masterSpeed)
    #print np.shape(data)
    #print np.shape(ki), np.shape(kE(ef)), np.shape(detToTwoTheta[:, None])
    #print detToTwoTheta

    Q_ = Qfunc(ki, kE(ef), detToTwoTheta[:, None])

    E_transfer = Ei-ef
    E_mask = (E_transfer > -Ei)

    EQ_dataarray, xedges, yedges = np.histogram2d(Q_[E_mask], E_transfer[E_mask], bins=(Q_bins, E_bins), range=([Q_min,Q_max], [-Ei, Ei]), weights=data[E_mask])
    # normalize to number of pixels in each histogram bin:
    norm_data = np.ones_like(data)
    EQ_norm, xedges, yedges = np.histogram2d(Q_[E_mask], E_transfer[E_mask], bins=(Q_bins, E_bins), range=([Q_min,Q_max], [-Ei, Ei]), weights=norm_data[E_mask])

    norm_mask = (EQ_norm != 0)
    EQ_normalized = np.copy(EQ_dataarray)
    EQ_normalized[norm_mask] = EQ_dataarray[norm_mask] / EQ_norm[norm_mask]
    
    new_metadata = deepcopy(rawdata.metadata)
    new_metadata['Ei'] = Ei
    new_metadata['Ef'] = ef
    new_metadata['Q_max'] = Q_max
    new_metadata['Q_min'] = Q_min
    new_eq = EQData(rawdata.name, EQ_normalized, new_metadata)
    return new_eq

@module
def sliceEQData(data, slicebox=[None,None,None,None]):
    """
    Sum 2d data along both axes and return 1d datasets

    **Inputs**

    data (eq) : data in
    
    slicebox (range?:xy): region over which to integrate (in data coordinates)

    **Returns**

    xout (eq1d) : xslice

    yout (eq1d) : yslice

    2018-04-22 Brian Maranville
    """

    from .dcsdata import DCS1dData

    if slicebox is None:
        slicebox = [None, None, None, None]
    xmin, xmax, ymin, ymax = slicebox
    
    # then use q-values
    xdata = data.xaxis['values']
    ydata = data.yaxis['values']

    xmin = data.xaxis["min"]
    xmax = data.xaxis["max"]
    x_in = data.xaxis["values"]
    y_in = data.yaxis["values"]
    
    xslice = slice(get_index(x_in, xmin), get_index(x_in, xmax))
    yslice = slice(get_index(y_in, ymin), get_index(y_in, ymax))
    x_out = x_in[xslice]
    y_out = y_in[yslice]
    dx = np.zeros_like(x_out)
    dy = np.zeros_like(y_out)
        
    dataslice = (xslice, yslice)
    x_sum = np.sum(data.data[dataslice], axis=1)
    y_sum = np.sum(data.data[dataslice], axis=0)
    
    x_output = DCS1dData(x_out, x_sum, dx=dx, dv=dx, xlabel=data.xaxis["label"], vlabel="I",
                    xunits="", vunits="neutrons", metadata=data.metadata)
    y_output = DCS1dData(y_out, y_sum, dx=dy, dv=dy, xlabel=data.yaxis["label"], vlabel="I",
                    xunits="", vunits="neutrons", metadata=data.metadata)

    return x_output, y_output

def Elam(lam):
    """
    convert wavelength in angstroms to energy in meV
    """
    return 81.81/lam**2

def Ek(k):
    """
    convert wave-vector in inver angstroms to energy in meV
    """
    return 2.072*k**2

def kE(E):
    return np.sqrt(E/2.072)

def Qfunc(ki, kf, theta):
    """
    evaluate the magnitude of Q from ki, kf, and theta
    theta is the angle between kf and ki, sometimes called 2 theta, units of degrees
    """
    return np.sqrt(  ki**2 + kf**2 - 2*ki*kf*np.cos(theta*np.pi/180)  )

def Ef_from_timechannel(timeChannel, t_SD_min, speedRatDenom, masterSpeed):
    """
    using the parameters
        t_SD_min = minimum sample to detector time
        speedRatDenom = to set FOL chopper speed
        masterSpeed = chopper speed (except for FOL chopper)
    using the variabl
        timeChannel, where I am numbering from 1 <be careful of this convention>
    """
    return 8.41e7 / (t_SD_min + (timeChannel+1)*    (6e4 *(speedRatDenom/masterSpeed))   )**2

def get_index(t, x):
    if (x == "" or x == None):
        return None
    if float(x) > t.max():
        return None
    if float(x) < t.min():
        return None
    tord = np.argsort(t)
    return tord[np.searchsorted(t, float(x), sorter=tord)]