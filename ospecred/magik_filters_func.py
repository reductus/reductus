from numpy import cos, pi, cumsum, arange, ndarray, ones, zeros, array, newaxis, linspace, empty, resize, sin, allclose, zeros_like, linalg, dot, arctan2, float64, histogram2d, sum, nansum, sqrt, loadtxt, searchsorted, NaN, logical_not, fliplr, flipud, indices, polyfit

import numpy
from numpy.ma import MaskedArray
import os, simplejson, datetime, sys, types
from copy import deepcopy

from FilterableMetaArray import FilterableMetaArray as MetaArray
from reflred import rebin as reb
from reflred.formats.nexusref import h5_open_zip

from posixpath import basename, join
import StringIO
import urllib2
import time
import pytz
from reflred.iso8601 import seconds_since_epoch

ALL_ACTIONS = []
DATA_SOURCES = {"ncnr": "http://ncnr.nist.gov/pub/"}
DEBUG = False

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
    
def fitPSDCalibration(calibration, minimum_peak_intensity=500.0):
    # takes a loaded psd calibration file, which 
    # is direct beam measurements at a variety of detector angles with tight slits
    #X = np.arange(data.size)
    #x = np.sum(X*data)/np.sum(data)
    #width = np.sqrt(np.abs(np.sum((X-x)**2*data)/np.sum(data)))
    counts = calibration['Measurements':'counts']
    twotheta = calibration.extrainfo['det_angle']
    cpixels = []
    tts = []
    widths = []
    for i in range(counts.shape[1]):
        data = counts[:,i].view(ndarray)
        tt  = twotheta[i]
        if sum(data) < minimum_peak_intensity:
            continue
        X = arange(data.size) + 0.5
        x = sum(X*data)/sum(data)
        width = sqrt(abs(sum((X-x)**2*data)/sum(data)))
        widths.append(width)
        cpixels.append(x)
        tts.append(tt)
    # now fitting to polynomial:
    fit = polyfit(tts, cpixels, 1)
    # returns [pixels_per_degree, qzero_pixel]
    return {"pixels_per_degree": -fit[0], "qzero_pixel": fit[1]}
   
@module
def coordinateOffset(data, offsets=None):
    """ 
    Apply an offset to one or both of the coordinate axes 
    To apply an offset to an axis, add it to the dict of offsets.
    e.g. if data is theta, twotheta, then
    to apply 0.01 offset to twotheta only make offsets = {'twotheta': 0.01}
    
    **Inputs**

    data (ospec2d) : data in

    offsets (offset_data) : to apply 0.01 offset to twotheta only make offsets = {'twotheta': 0.01}
    
    **Returns**

    output (ospec2d) : data with offsets applied

    2016-04-01 Brian Maranville
    """
    new_info = data.infoCopy()
    if offsets is None: offsets = {}
    for key in offsets.keys():
        if 1:
            axisnum = data._getAxis(key)
            new_info[axisnum]['values'] += offsets[key]
        #except:
        else:
            pass
    new_data = MetaArray(data.view(ndarray).copy(), info=new_info)
    return new_data
    
DETECTOR_ACTIVE = (320, 340)

def url_load(fileinfo):
    from dataflow.modules.load import url_get
    path, mtime, entries = fileinfo['path'], fileinfo['mtime'], fileinfo['entries']
    name = basename(path)
    fid = StringIO.StringIO(url_get(fileinfo))
    nx_entries = LoadMAGIKPSD.load_entries(name, fid, entries=entries)
    fid.close()
    return nx_entries

def url_load_list(files=None):
    if files is None: return []
    result = [entry for fileinfo in files for entry in url_load(fileinfo)]
    return result

def check_datasource(source):
    if not source in DATA_SOURCES:
        raise RuntimeError("Need to set reflred.steps.load.DATA_SOURCES['" + source + "'] first!")
        
def find_mtime(path, source="ncnr"):
    check_datasource(source)
    print DATA_SOURCES[source]
    try:
        url = urllib2.urlopen(DATA_SOURCES[source]+path)
        mtime = url.info().getdate('last-modified')
    except urllib2.HTTPError as exc:
        raise ValueError("Could not open %r\n%s"%(path, str(exc)))
    mtime_obj = datetime.datetime(*mtime[:7], tzinfo=pytz.utc)
    timestamp = seconds_since_epoch(mtime_obj)

    return { 'path': path, 'mtime': timestamp }


@module
def LoadMAGIKPSD(fileinfo=None, collapse_y=True, auto_PolState=False, PolState='', flip=True, transpose=True):
    """ 
    loads a data file into a MetaArray and returns that.
    Checks to see if data being loaded is 2D; if not, quits
    
    Need to rebin and regrid if the detector is moving...
    
    **Inputs**
    
    fileinfo (fileinfo): File to open.
    
    collapse_y {Collapse along y} (bool): sum over y-axis of detector
    
    auto_PolState {Automatic polarization identify} (bool): automatically determine the polarization state from entry name
    
    PolState (str): polarization state if not automatically detected
    
    flip (bool): flip the data up and down
    
    transpose (bool): transpose the data
    
    **Returns**
    
    output (ospec2d[]): all the entries loaded.
    
    2016-04-01 Brian Maranville    
    """
    lookup = {"DOWN_DOWN":"_down_down", "UP_DOWN":"_up_down", "DOWN_UP":"_down_up", "UP_UP":"_up_up", "entry": ""}
    from dataflow.modules.load import url_get
    path, mtime, entries = fileinfo['path'], fileinfo['mtime'], fileinfo['entries']
    name = basename(path)
    fid = StringIO.StringIO(url_get(fileinfo))
    file_obj = h5_open_zip(name, fid)
    #nx_entries = LoadMAGIKPSD.load_entries(name, fid, entries=entries)
    #fid.close()
    
    #if not (len(file_obj.detector.counts.shape) == 2):
        # not a 2D object!
    #    return
    for entryname, entry in file_obj.items():
        active_slice = slice(None, DETECTOR_ACTIVE[0], DETECTOR_ACTIVE[1])
        counts_value = entry['DAS_logs']['areaDetector']['counts'].value[:, 1:DETECTOR_ACTIVE[0]+1, :DETECTOR_ACTIVE[1]]
        dims = counts_value.shape
        print dims
        ndims = len(dims)
        if auto_PolState:
            PolState = lookup.get(entryname, "")
        # force PolState to a regularized version:
        if not PolState in lookup.values():
            PolState = ''
        #datalen = file_obj.detector.counts.shape[0]
        if ndims == 2:
            if DEBUG: print "2d"
            ypixels = dims[0]
            xpixels = dims[1]
        elif ndims >= 3:
            if DEBUG: print "3d"
            frames = dims[0]
            xpixels = dims[1]
            ypixels = dims[2]
        

        # doesn't really matter; changing so that each keyword (whether it took the default value
        # provided or not) will be defined
        #    if not PolState == '':
        #        creation_story += ", PolState='{0}'".format(PolState)
        # creation_story += ")" 
    
    
        if ndims == 2: # one of the dimensions has been collapsed.
            info = []     
            info.append({"name": "xpixel", "units": "pixels", "values": arange(xpixels) }) # reverse order
            info.append({"name": "theta", "units": "degrees", "values": entry['DAS_logs']['sampleAngle']['softPosition'].value })
            info.extend([
                    {"name": "Measurements", "cols": [
                            {"name": "counts"},
                            {"name": "pixels"},
                            {"name": "monitor"},
                            {"name": "count_time"}]},
                    {"PolState": PolState, "filename": filename, "start_datetime": entry['start_time'].value[0], "friendly_name": name,
                     "path":path, "det_angle":entry['DAS_logs']['detectorAngle']['softPosition'].value}]
                )
            data_array = zeros((xpixels, ypixels, 4))
            mon =  entry['DAS_logs']['counter']['liveMonitor'].value
            count_time = entry['DAS_logs']['counter']['liveTime'].value
            if ndims == 2:
                mon.shape = (1,) + mon.shape # broadcast the monitor over the other dimension
                count_time.shape = (1,) + count_time.shape
            counts = counts_value
            if transpose == True: counts = counts.swapaxes(0,1)
            if flip == True: counts = flipud(counts)
            data_array[..., 0] = counts
            #data_array[..., 0] = file_obj.detector.counts
            data_array[..., 1] = 1
            data_array[..., 2] = mon
            data_array[..., 3] = count_time
            # data_array[:,:,4]... I wish!!!  Have to do by hand.
            data = MetaArray(data_array, dtype='float', info=info)
            data.friendly_name = name # goes away on dumps/loads... just for initial object.
        
        elif ndims == 3: # then it's an unsummed collection of detector shots.  Should be one sample and detector angle per frame
            if collapse_y == True:
                info = []     
                info.append({"name": "xpixel", "units": "pixels", "values": arange(xpixels) }) # reverse order
                info.append({"name": "theta", "units": "degrees", "values": entry['DAS_logs']['sampleAngle']['softPosition'].value })
                info.extend([
                        {"name": "Measurements", "cols": [
                                {"name": "counts"},
                                {"name": "pixels"},
                                {"name": "monitor"},
                                {"name": "count_time"}]},
                        {"PolState": PolState, "start_datetime": entry['start_time'].value[0], "path":path, "det_angle":entry['DAS_logs']['detectorAngle']['softPosition'].value}]
                    )
                data_array = zeros((xpixels, frames, 4))
                mon =  entry['DAS_logs']['counter']['liveMonitor'].value
                count_time = entry['DAS_logs']['counter']['liveTime'].value
                if ndims == 3:
                    mon.shape = (1,) + mon.shape # broadcast the monitor over the other dimension
                    count_time.shape = (1,) + count_time.shape
                counts = numpy.sum(counts_value, axis=2)
                if transpose == True: counts = counts.swapaxes(0,1)
                if flip == True: counts = flipud(counts)
                data_array[..., 0] = counts
                #data_array[..., 0] = file_obj.detector.counts
                data_array[..., 1] = 1
                data_array[..., 2] = mon
                data_array[..., 3] = count_time
                # data_array[:,:,4]... I wish!!!  Have to do by hand.
                data = MetaArray(data_array, dtype='float', info=info)
                data.friendly_name = name # goes away on dumps/loads... just for initial object.
            else: # make separate frames           
                infos = []
                data = []
                samp_angle =  entry['DAS_logs']['sampleAngle']['softPosition'].value
                if samp_angle.shape[0] == 1:
                    samp_angle = numpy.ones((frames,)) * samp_angle
                det_angle = entry['DAS_logs']['detectorAngle']['softPosition'].value
                if det_angle.shape[0] == 1:
                    det_angle = numpy.ones((frames,)) * det_angle
                for i in range(frames):
                    samp_angle =  entry['DAS_logs']['sampleAngle']['softPosition'].value[i]
                    det_angle = entry['DAS_logs']['detectorAngle']['softPosition'].value[i]
                    info = []
                    info.append({"name": "xpixel", "units": "pixels", "values": range(xpixels) })
                    info.append({"name": "ypixel", "units": "pixels", "values": range(ypixels) })
                    info.extend([
                        {"name": "Measurements", "cols": [
                                {"name": "counts"},
                                {"name": "pixels"},
                                {"name": "monitor"},
                                {"name": "count_time"}]},
                        {"PolState": PolState, "start_datetime": entry['start_time'].value[0], "friendly_name": name,
                         "path":path, "samp_angle": samp_angle, "det_angle": det_angle}]
                    )
                    data_array = zeros((xpixels, ypixels, 4))
                    mon =  entry['DAS_logs']['counter']['liveMonitor'].value[i]
                    count_time = entry['DAS_logs']['counter']['liveTime'].value[i]
                    counts = counts_value[i]
                    if flip == True: counts = flipud(counts) 
                    data_array[..., 0] = counts
                    data_array[..., 1] = 1
                    data_array[..., 2] = mon
                    data_array[..., 3] = count_time
                    # data_array[:,:,4]... I wish!!!  Have to do by hand.
                    subdata = MetaArray(data_array, dtype='float', info=info)
                    subdata.friendly_name = name + ("_%d" % i) # goes away on dumps/loads... just for initial object.
                    data.append(subdata)
    return data
    
def test():
    from dataflow.modules import load
    load.DATA_SOURCES = {"ncnr": "http://ncnr.nist.gov/pub/"}
    fileinfo = {
        'mtime': 1457795231.0,
        'path': 'ncnrdata/cgd/201603/21237/data/wp10v132.nxz.cgd',
        'source': 'ncnr',
        'entries': ['entry']
    }
    return LoadMAGIKPSD(fileinfo)
     
