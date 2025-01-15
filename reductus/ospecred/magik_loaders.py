import os, datetime, sys, types
from copy import deepcopy
import dateutil.parser

from numpy import cos, pi, cumsum, arange, ndarray, ones, zeros, array, newaxis, linspace, empty, resize, sin, allclose, zeros_like, linalg, dot, arctan2, float64, histogram2d, sum, sqrt, loadtxt, searchsorted, nan, logical_not, fliplr, flipud
import numpy
from numpy.ma import MaskedArray
import h5py

from reductus.dataflow.lib import hzf_readonly_stripped as hzf

from .FilterableMetaArray import FilterableMetaArray as MetaArray
from .he3analyzer import He3AnalyzerCollection

DEBUG=False

def hdf_to_dict(hdf_obj, convert_i1_tostr=True):
    out_dict = {}
    for key in hdf_obj:
        val = hdf_obj[key]
        if type(val) == h5py.highlevel.Dataset:
            if (val[()].dtype == 'int8') and (convert_i1_tostr == True):
                value = val[()].tostring()
            else:
                value = val[()]
            out_dict[key] = value
        else:
            out_dict[key] = hdf_to_dict(val)
    return out_dict

def LoadText(filename, friendly_name="", path=None, first_as_x=True):
    if path == None:
        path = os.getcwd()
    creation_story = "LoadText('{fn}')".format(fn=filename)
    data_in = loadtxt(os.path.join(path, filename))
    info = []
    first_y_col = 0
    if first_as_x:
        info.append({"name":"xaxis", "units":"unknown", "values": data_in[:,0]})
        first_y_col = 1
    else:
        info.append({"name":"rownumber", "units":"index", "values": range(data_in.shape[1])})

    info.append({"name":"Measurements", "cols":[]})
    for col in range(first_y_col, data_in.shape[1]):
        info[1]["cols"].append({"name": "column%d" % (col,)})

    info.append({"filename": filename, "start_datetime": None,
             "CreationStory":creation_story, "path":path})
    output_obj = MetaArray(data_in[:,first_y_col:], dtype='float', info=info[:])
    return output_obj


def LoadICPMany(filedescriptors):
    result = []
    for fd in filedescriptors:
        new_data = LoadICPData(fd.pop('filename'), **fd)
        if isinstance(new_data, list):
            result.extend(new_data)
        else:
            result.append(new_data)
    return result

DETECTOR_ACTIVE = (320, 340)

def LoadMAGIKPSD(filename, path="", friendly_name="", collapse_y=True, auto_PolState=False, PolState='', flip=True, transpose=True, **kw):
    """
    loads a data file into a MetaArray and returns that.
    Checks to see if data being loaded is 2D; if not, quits

    Need to rebin and regrid if the detector is moving...
    """
    lookup = {"DOWN_DOWN":"_down_down", "UP_DOWN":"_up_down", "DOWN_UP":"_down_up", "UP_UP":"_up_up", "entry": ""}
    if '.nxz' in filename:
        file_obj = hzf.File(filename)
    else:
        # nexus
        file_obj = h5py.File(os.path.join(path, filename))

    #if not (len(file_obj.detector.counts.shape) == 2):
        # not a 2D object!
    #    return
    for entryname, entry in file_obj.items():
        active_slice = slice(None, DETECTOR_ACTIVE[0], DETECTOR_ACTIVE[1])
        counts_value = entry['DAS_logs']['areaDetector']['counts'][:, 1:DETECTOR_ACTIVE[0]+1, :DETECTOR_ACTIVE[1]]
        dims = counts_value.shape
        print(dims)
        ndims = len(dims)
        if auto_PolState:
            PolState = lookup.get(entryname, "")
        # force PolState to a regularized version:
        if not PolState in lookup.values():
            PolState = ''
        #datalen = file_obj.detector.counts.shape[0]
        if ndims == 2:
            if DEBUG: print("2d")
            ypixels = dims[0]
            xpixels = dims[1]
        elif ndims >= 3:
            if DEBUG: print("3d")
            frames = dims[0]
            xpixels = dims[1]
            ypixels = dims[2]

        creation_story = "LoadMAGIKPSD('{fn}', path='{p}')".format(fn=filename, p=path, aPS=auto_PolState, PS=PolState)

        # doesn't really matter; changing so that each keyword (whether it took the default value
        # provided or not) will be defined
        #    if not PolState == '':
        #        creation_story += ", PolState='{0}'".format(PolState)
        # creation_story += ")"


        if ndims == 2: # one of the dimensions has been collapsed.
            info = []
            info.append({"name": "xpixel", "units": "pixels", "values": arange(xpixels) }) # reverse order
            info.append({"name": "theta", "units": "degrees", "values": entry['DAS_logs']['sampleAngle']['softPosition'][()] })
            info.extend([
                    {"name": "Measurements", "cols": [
                            {"name": "counts"},
                            {"name": "pixels"},
                            {"name": "monitor"},
                            {"name": "count_time"}]},
                    {"PolState": PolState, "filename": filename, "start_datetime": dateutil.parser.parse(file_obj.attrs.get('file_time')), "friendly_name": friendly_name,
                     "CreationStory":creation_story, "path":path, "det_angle":entry['DAS_logs']['detectorAngle']['softPosition'][()]}]
                )
            data_array = zeros((xpixels, ypixels, 4))
            mon =  entry['DAS_logs']['counter']['liveMonitor'][()]
            count_time = entry['DAS_logs']['counter']['liveTime'][()]
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
            data.friendly_name = friendly_name # goes away on dumps/loads... just for initial object.

        elif ndims == 3: # then it's an unsummed collection of detector shots.  Should be one sample and detector angle per frame
            if collapse_y == True:
                info = []
                info.append({"name": "xpixel", "units": "pixels", "values": arange(xpixels) }) # reverse order
                info.append({"name": "theta", "units": "degrees", "values": entry['DAS_logs']['sampleAngle']['softPosition'][()] })
                info.extend([
                        {"name": "Measurements", "cols": [
                                {"name": "counts"},
                                {"name": "pixels"},
                                {"name": "monitor"},
                                {"name": "count_time"}]},
                        {"PolState": PolState, "filename": filename, "start_datetime": dateutil.parser.parse(file_obj.attrs.get('file_time')), "friendly_name": friendly_name,
                         "CreationStory":creation_story, "path":path, "det_angle":entry['DAS_logs']['detectorAngle']['softPosition'][()]}]
                    )
                data_array = zeros((xpixels, frames, 4))
                mon =  entry['DAS_logs']['counter']['liveMonitor'][()]
                count_time = entry['DAS_logs']['counter']['liveTime'][()]
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
                data.friendly_name = friendly_name # goes away on dumps/loads... just for initial object.
            else: # make separate frames
                infos = []
                data = []
                samp_angle =  entry['DAS_logs']['sampleAngle']['softPosition'][()]
                if samp_angle.shape[0] == 1:
                    samp_angle = numpy.ones((frames,)) * samp_angle
                det_angle = entry['DAS_logs']['detectorAngle']['softPosition'][()]
                if det_angle.shape[0] == 1:
                    det_angle = numpy.ones((frames,)) * det_angle
                for i in range(frames):
                    samp_angle =  entry['DAS_logs']['sampleAngle']['softPosition'][i]
                    det_angle = entry['DAS_logs']['detectorAngle']['softPosition'][i]
                    info = []
                    info.append({"name": "xpixel", "units": "pixels", "values": range(xpixels) })
                    info.append({"name": "ypixel", "units": "pixels", "values": range(ypixels) })
                    info.extend([
                        {"name": "Measurements", "cols": [
                                {"name": "counts"},
                                {"name": "pixels"},
                                {"name": "monitor"},
                                {"name": "count_time"}]},
                        {"PolState": PolState, "filename": filename, "start_datetime": entry['start_time'][()], "friendly_name": friendly_name,
                         "CreationStory":creation_story, "path":path, "samp_angle": samp_angle, "det_angle": det_angle}]
                    )
                    data_array = zeros((xpixels, ypixels, 4))
                    mon =  entry['DAS_logs']['counter']['liveMonitor'][i]
                    count_time = entry['DAS_logs']['counter']['liveTime'][i]
                    counts = counts_value[i]
                    if flip == True: counts = flipud(counts)
                    data_array[..., 0] = counts
                    data_array[..., 1] = 1
                    data_array[..., 2] = mon
                    data_array[..., 3] = count_time
                    # data_array[:,:,4]... I wish!!!  Have to do by hand.
                    subdata = MetaArray(data_array, dtype='float', info=info)
                    subdata.friendly_name = friendly_name + ("_%d" % i) # goes away on dumps/loads... just for initial object.
                    data.append(subdata)
    return data

def LoadICPData(filename, path="", friendly_name="", auto_PolState=False, PolState='', flip=True, transpose=True, **kw):
    """
    loads a data file into a MetaArray and returns that.
    Checks to see if data being loaded is 2D; if not, quits

    Need to rebin and regrid if the detector is moving...
    """
    lookup = {"a":"_down_down", "b":"_up_down", "c":"_down_up", "d":"_up_up", "g": ""}
    file_obj = load(os.path.join(path, filename), format='NCNR NG-1')
    dims = file_obj.detector.counts.shape
    ndims = len(dims)
    #if not (len(file_obj.detector.counts.shape) == 2):
        # not a 2D object!
    #    return
    if auto_PolState:
        key = friendly_name[-2:-1] # na1, ca1 etc. are --, nc1, cc1 are -+...
        PolState = lookup.get(key, "")
    # force PolState to a regularized version:
    if not PolState in lookup.values():
        PolState = ''
    #datalen = file_obj.detector.counts.shape[0]
    if ndims == 2:
        if DEBUG: print("2d")
        ypixels = file_obj.detector.counts.shape[0]
        xpixels = file_obj.detector.counts.shape[1]
    elif ndims >= 3:
        if DEBUG: print("3d")
        frames = file_obj.detector.counts.shape[0]
        ypixels = file_obj.detector.counts.shape[1]
        xpixels = file_obj.detector.counts.shape[2]

    creation_story = "LoadICPData('{fn}', path='{p}', auto_PolState={aPS}, PolState='{PS}')".format(fn=filename, p=path, aPS=auto_PolState, PS=PolState)

    # doesn't really matter; changing so that each keyword (whether it took the default value
    # provided or not) will be defined
    #    if not PolState == '':
    #        creation_story += ", PolState='{0}'".format(PolState)
    # creation_story += ")"


    if ndims == 2: # one of the dimensions has been collapsed.
        info = []
        info.append({"name": "xpixel", "units": "pixels", "values": arange(xpixels) }) # reverse order
        info.append({"name": "theta", "units": "degrees", "values": file_obj.sample.angle_x })
        info.extend([
                {"name": "Measurements", "cols": [
                        {"name": "counts"},
                        {"name": "pixels"},
                        {"name": "monitor"},
                        {"name": "count_time"}]},
                {"PolState": PolState, "filename": filename, "start_datetime": file_obj.date, "friendly_name": friendly_name,
                 "CreationStory":creation_story, "path":path, "det_angle":file_obj.detector.angle_x}]
            )
        data_array = zeros((xpixels, ypixels, 4))
        mon = file_obj.monitor.counts
        count_time = file_obj.monitor.count_time
        if ndims == 2:
            mon.shape = (1,) + mon.shape # broadcast the monitor over the other dimension
            count_time.shape = (1,) + count_time.shape
        counts = file_obj.detector.counts
        if transpose == True: counts = counts.swapaxes(0,1)
        if flip == True: counts = flipud(counts)
        data_array[..., 0] = counts
        #data_array[..., 0] = file_obj.detector.counts
        data_array[..., 1] = 1
        data_array[..., 2] = mon
        data_array[..., 3] = count_time
        # data_array[:,:,4]... I wish!!!  Have to do by hand.
        data = MetaArray(data_array, dtype='float', info=info)
        data.friendly_name = friendly_name # goes away on dumps/loads... just for initial object.

    elif ndims == 3: # then it's an unsummed collection of detector shots.  Should be one sample and detector angle per frame
        infos = []
        data = []
        for i in range(frames):
            samp_angle = file_obj.sample.angle_x[i]
            det_angle = file_obj.detector.angle_x[i]
            info = []
            info.append({"name": "xpixel", "units": "pixels", "values": range(xpixels) })
            info.append({"name": "ypixel", "units": "pixels", "values": range(ypixels) })
            info.extend([
                {"name": "Measurements", "cols": [
                        {"name": "counts"},
                        {"name": "pixels"},
                        {"name": "monitor"},
                        {"name": "count_time"}]},
                {"PolState": PolState, "filename": filename, "start_datetime": file_obj.date, "friendly_name": friendly_name,
                 "CreationStory":creation_story, "path":path, "samp_angle": samp_angle, "det_angle": det_angle}]
            )
            data_array = zeros((xpixels, ypixels, 4))
            mon = file_obj.monitor.counts[i]
            count_time = file_obj.monitor.count_time[i]
            counts = file_obj.detector.counts[i]
            if flip == True: counts = flipud(counts)
            data_array[..., 0] = counts
            data_array[..., 1] = 1
            data_array[..., 2] = mon
            data_array[..., 3] = count_time
            # data_array[:,:,4]... I wish!!!  Have to do by hand.
            subdata = MetaArray(data_array, dtype='float', info=info)
            subdata.friendly_name = friendly_name + ("_%d" % i) # goes away on dumps/loads... just for initial object.
            data.append(subdata)
    return data

