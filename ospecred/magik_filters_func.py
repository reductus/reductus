from numpy import cos, pi, cumsum, arange, ndarray, ones, zeros, array, newaxis, linspace, empty, resize, sin, allclose, zeros_like, linalg, dot, arctan2, float64, histogram2d, sum, nansum, sqrt, loadtxt, searchsorted, NaN, logical_not, fliplr, flipud, indices, polyfit

import numpy
from numpy.ma import MaskedArray
import os, sys, types
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

from dataflow.core import Template
from dataflow.calc import process_template

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

@module    
def fitPSDCalibration(calibration, minimum_peak_intensity=500.0):
    """
    Takes a loaded psd calibration file, which 
    is direct beam measurements at a variety of detector angles with tight slits
    X = np.arange(data.size)
    x = np.sum(X*data)/np.sum(data)
    width = np.sqrt(np.abs(np.sum((X-x)**2*data)/np.sum(data))) 
    
    **Inputs**

    calibration (ospec2d) : data in
    
    minimum_peak_intensity (float): don't fit peaks with integrated intensity smaller than this
    
    **Returns**

    output (params) : fit results

    2016-04-01 Brian Maranville
    """
    from dataflow.modules.ospec import Parameters
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
    return Parameters({"pixels_per_degree": -fit[0], "qzero_pixel": fit[1]})
   
@module
def coordinateOffset(data, axis=None, offset=0):
    """ 
    Apply an offset to one or both of the coordinate axes 
    To apply an offset to an axis, add it to the dict of offsets.
    e.g. if data is theta, twotheta, then
    to apply 0.01 offset to twotheta only make offsets = {'twotheta': 0.01}
    
    **Inputs**

    data (ospec2d) : data in

    axis (str): axis to apply the offset to
    
    offset (float): amount of offset
    
    **Returns**

    output (ospec2d) : data with offsets applied

    2016-04-01 Brian Maranville
    """
    if axis is None: return data
    new_info = data.infoCopy()
    axisnum = data._getAxis(axis)
    new_info[axisnum]['values'] += offset
    new_data = MetaArray(data.view(ndarray).copy(), info=new_info)
    return new_data

@module
def normalizeToMonitor(data):
    """ 
    divide all the counts columns by monitor and output as normcounts, with stat. error 
    
    **Inputs**

    data (ospec2d) : data in
    
    **Returns**

    output (ospec2d) : data with normalization applied

    2016-04-01 Brian Maranville
    """
    cols = [col['name'] for col in data._info[-2]['cols']]
    passthrough_cols = [col for col in cols if (not col.startswith('counts'))] # and not col.startswith('monitor'))]
    counts_cols = [col for col in cols if col.startswith('counts')]
    monitor_cols = [col for col in cols if col.startswith('monitor')]
    info = data.infoCopy()
    info[-2]['cols'] = []
    output_array = zeros( data.shape[:-1] + (len(counts_cols) + len(passthrough_cols),), dtype=float) * NaN
    expressions = []
    for i, col in enumerate(passthrough_cols):
        info[-2]['cols'].append({"name":col})
        output_array[..., i] = data["Measurements":col]
        
    for i, col in enumerate(counts_cols):
        j = i + len(passthrough_cols)
        col_suffix = col[len('counts'):]
        monitor_id = 'monitor'
        if ('monitor'+col_suffix) in monitor_cols:
            monitor_id += col_suffix
        info[-2]['cols'].append({"name":"counts_norm%s" % (col_suffix,)})
        mask = data["Measurements":monitor_id].nonzero()
        #print mask
        output_array[..., j][mask] = data["Measurements":col][mask] / data["Measurements":monitor_id][mask]
        #expression = "data1_counts%s / data1_%s" % (col_suffix, monitor_id)
        #error_expression = "sqrt(data1_counts%s) / data1_%s" % (col_suffix, monitor_id)
        #expressions.append({"name": "counts_norm%s" % (col_suffix,), "expression":expression})
        #expressions.append({"name": "error_counts_norm%s" % (col_suffix,), "expression":error_expression})
    #result = Algebra().apply(data, None, expressions, passthrough_cols)
    result = MetaArray(output_array, info=info)
    return result

@module
def pixelsToTwotheta(data, params, pixels_per_degree=50.0, qzero_pixel=149.0, instr_resolution=1e-6, ax_name='xpixel'):
    """ input array has axes theta and pixels:
    output array has axes theta and twotheta.
    
    Pixel-to-angle conversion is arithmetic (pixels-per-degree=constant)
    output is rebinned to fit in a rectangular array if detector angle 
    is not fixed. 
    
    **Inputs**

    data (ospec2d) : data in
    
    params (params): parameters override the field values
    
    pixels_per_degree {Pixels per degree} (float): slope of equation relating pixel to angle
    
    qzero_pixel {Q-zero pixel} (float): pixel value for Q=0
    
    instr_resolution {Resolution} (float): steps in angle smaller than this will be ignored/combined
    
    ax_name {Axis name} (str): name of the axis containing pixel data 
    
    **Returns**

    output (ospec2d) : data with pixel axis converted to angle

    2016-04-01 Brian Maranville
    """
   
    if 'pixels_per_degree' in params: pixels_per_degree = params['pixels_per_degree']
    if 'qzero_pixel' in params: qzero_pixel = params['qzero_pixel']
    #kw = locals().keys()
    #print kw, params
    #for name in kw:
    #    if name in params:
    #        exec "print '%s', %s, params['%s']" % (name, name,name) in locals()
    #        exec ("%s = params['%s']" % (name, name)) in locals()
    #        exec "print %s" % (name,) in locals()
    
    pixels_per_degree = float(pixels_per_degree) # coerce, in case it was an integer
    qzero_pixel = float(qzero_pixel) 
    instr_resolution = float(instr_resolution)
    
    print pixels_per_degree, qzero_pixel
    
    new_info = data.infoCopy()
    det_angle = new_info[-1].get('det_angle', None)
    det_angle = array(det_angle)
    # det_angle should be a vector of the same length as the other axis (usually theta)
    # or else just a float, in which case the detector is not moving!
    ndim = len(new_info) - 2 # last two entries in info are for metadata
    pixel_axis = next((i for i in xrange(len(new_info)-2) if new_info[i]['name'] == ax_name), None)
    if pixel_axis < 0:
        raise ValueError("error: no %s axis in this dataset" % (ax_name,))
        
    if hasattr(det_angle, 'max'):
        det_angle_max = det_angle.max()
        det_angle_min = det_angle.min()
    else: # we have a number
        det_angle_max = det_angle_min = det_angle
        
    if ((det_angle_max - det_angle_min) < instr_resolution) or ndim == 1 or ax_name != 'xpixel':
        #then the detector is fixed and we just change the values in 'xpixel' axis vector to twotheta
        # or the axis to be converted is y, which doesn't move in angle.
        print "doing the simple switch of axis values..."
        
        #data_slices = [slice(None, None, 1), slice(None, None, 1)]
        #data_slices[pixel_axis] = slice(None, None, -1)
        
        if ax_name == 'xpixel':
            twotheta_motor = det_angle_min
            new_info[pixel_axis]['name'] = 'twotheta'
        else:
            twotheta_motor = 0.0 # we don't have a y-motor!
            new_info[pixel_axis]['name'] = 'twotheta_y'
            
        pixels = new_info[pixel_axis]['values']
        twoth = (pixels - qzero_pixel) / pixels_per_degree + twotheta_motor
        #new_info[pixel_axis]['values'] = twoth[::-1] # reverse: twotheta increases as pixels decrease
        new_info[pixel_axis]['values'] = twoth
        new_info[pixel_axis]['units'] = 'degrees'
        #new_array = (data.view(ndarray).copy())[data_slices]
        new_array = (data.view(ndarray).copy())
        new_data = MetaArray(new_array, info=new_info)
    
    else:
        # the detector is moving - have to rebin the dataset to contain all values of twoth
        # this is silly but have to set other axis!
        other_axis = (1 if pixel_axis == 0 else 0)
        #other_vector = new_info[other_axis]['values']
        #other_spacing = other_vector[1] - other_vector[0]
        pixels = new_info[pixel_axis]['values']
        twoth = (pixels - qzero_pixel) / pixels_per_degree
        #twoth = twoth[::-1] # reverse
        twoth_min = det_angle_min + twoth.min()
        twoth_max = det_angle_max + twoth.max()
        twoth_max_edge = twoth_max + 1.0 / pixels_per_degree
        dpp = 1.0 / pixels_per_degree
        #output_twoth_bin_edges = arange(twoth_max + dpp, twoth_min - dpp, -dpp)
        output_twoth_bin_edges = arange(twoth_min - dpp, twoth_max + dpp, dpp)
        output_twoth = output_twoth_bin_edges[:-1]
        #other_bin_edges = linspace(other_vector[0], other_vector[-1] + other_spacing, len(other_vector) + 1)
        new_info[pixel_axis]['name'] = 'twotheta' # getting rid of pixel units: substitute twoth
        new_info[pixel_axis]['values'] = output_twoth
        new_info[pixel_axis]['units'] = 'degrees'
        output_shape = [0,0,0]
        output_shape[pixel_axis] = len(output_twoth)
        output_shape[other_axis] = data.shape[other_axis] # len(other_vector)
        output_shape[2] = data.shape[2] # number of columns is unchanged!
        new_data = MetaArray(tuple(output_shape), info=new_info) # create the output data object!
        
        tth_min = twoth.min()
        tth_max = twoth.max()
        data_in = data.view(ndarray).copy()
        for i, da in enumerate(det_angle):
            twoth_min = da + tth_min
            twoth_max = da + tth_max
            input_twoth_bin_edges = empty(len(pixels) + 1)
            input_twoth_bin_edges[-1] = twoth_max + 1.0 / pixels_per_degree
            input_twoth_bin_edges[:-1] = twoth + da         
            #data_cols = ['counts', 'pixels', 'monitor', 'count_time']
            cols = new_info[-2]['cols']
            
            for col in range(len(cols)):
                input_slice = [slice(None, None), slice(None, None), col]
                #input_slice[pixel_axis] = slice(i, i+1)
                input_slice[other_axis] = i
                array_to_rebin = data_in[input_slice]
                new_array = reb.rebin(input_twoth_bin_edges, array_to_rebin, output_twoth_bin_edges)
                new_data.view(ndarray)[input_slice] = new_array
            
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
def LoadMAGIKPSDMany(fileinfo=None, collapse_y=True, auto_PolState=False, PolState='', flip=True, transpose=True):
    """ 
    loads a data file into a MetaArray and returns that.
    Checks to see if data being loaded is 2D; if not, quits
    
    Need to rebin and regrid if the detector is moving...
    
    **Inputs**
    
    fileinfo (fileinfo[]): Files to open.
    
    collapse_y {Collapse along y} (bool): sum over y-axis of detector
    
    auto_PolState {Automatic polarization identify} (bool): automatically determine the polarization state from entry name
    
    PolState (str): polarization state if not automatically detected
    
    flip (bool): flip the data up and down
    
    transpose (bool): transpose the data
    
    **Returns**
    
    output (ospec2d[]): all the entries loaded.
    
    2016-04-01 Brian Maranville  
    """
    outputs = []
    for fi in fileinfo:        
        template_def = {
          "name": "loader_template",
          "description": "Offspecular remote loader",
          "modules": [
            {"module": "ncnr.ospec.LoadMAGIKPSD", "version": "0.1", "config": {}}
          ],
          "wires": [],
          "instrument": "ncnr.magik",
          "version": "0.0"
        }
        template = Template(**template_def)
        config = {"0": {"fileinfo": {"path": fi['path'], "source": fi['source'], "mtime": fi['mtime']}}}
        nodenum = 0
        terminal_id = "output"
        
        retval = process_template(template, config, target=(nodenum, terminal_id))
        outputs.extend(retval.values)
    return outputs
    
@cache
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
        counts_value = entry['DAS_logs/areaDetector/counts'].value[:, 1:DETECTOR_ACTIVE[0]+1, :DETECTOR_ACTIVE[1]]
        dims = counts_value.shape
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
            info.append({"name": "theta", "units": "degrees", "values": entry['DAS_logs/sampleAngle/softPosition'].value })
            info.extend([
                    {"name": "Measurements", "cols": [
                            {"name": "counts"},
                            {"name": "pixels"},
                            {"name": "monitor"},
                            {"name": "count_time"}]},
                    {"PolState": PolState, "filename": filename, "start_datetime": entry['start_time'].value[0], "friendly_name": entry['DAS_logs/sample/name'].value[0],
                     "entry": entryname, "path":path, "det_angle":entry['DAS_logs/detectorAngle/softPosition'].value}]
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
                info.append({"name": "theta", "units": "degrees", "values": entry['DAS_logs/sampleAngle/softPosition'].value })
                info.extend([
                        {"name": "Measurements", "cols": [
                                {"name": "counts"},
                                {"name": "pixels"},
                                {"name": "monitor"},
                                {"name": "count_time"}]},
                        {"PolState": PolState, "start_datetime": entry['start_time'].value[0], "path":path, 
                         "det_angle":entry['DAS_logs/detectorAngle/softPosition'].value.tolist(), 
                         "friendly_name": entry['DAS_logs/sample/name'].value[0], "entry": entryname}]
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
                        {"PolState": PolState, "start_datetime": entry['start_time'].value[0], "friendly_name": entry['DAS_logs/sample/name'].value[0],
                         "entry": entryname, "path":path, "samp_angle": samp_angle, "det_angle": det_angle}]
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
    return [data]
    
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
     
