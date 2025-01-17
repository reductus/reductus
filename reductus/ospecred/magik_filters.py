# -*- coding: latin-1 -*-
# pylint: disable=line-too-long
from __future__ import print_function, division

import datetime
import types
from copy import deepcopy
from functools import wraps

from numpy import (cos, pi, cumsum, arange, ndarray, ones, zeros, array,
                   newaxis, linspace, empty, resize, sin, allclose, zeros_like,
                   linalg, dot, arctan2, float64, histogram2d, sum, nansum,
                   sqrt, loadtxt, searchsorted, nan, logical_not, fliplr,
                   flipud, indices, polyfit)
import numpy
from numpy.ma import MaskedArray

from reductus.dataflow.lib import rebin as reb

from .FilterableMetaArray import FilterableMetaArray as MetaArray
from .he3analyzer import He3AnalyzerCollection

DEBUG = False

class Supervisor():
    """class to hold rebinned_data objects and increment their reference count"""
    def __init__(self):
        self.rb_count = 0
        self.rebinned_data_objects = []
        self.plottable_count = 0
        self.plottable_2d_data_objects = []
        self.plots2d_count = 0
        self.plots2d_data_objects = []
        self.plots2d_names = []

    def AddRebinnedData(self, new_object, name='', base_data_obj=None):
        self.rebinned_data_objects.append(new_object)
        new_object.number = self.rb_count
        self.rb_count += 1

    def AddPlottable2dData(self, new_object, parent=None, name='', base_data_obj=None):
        self.plottable_2d_data_objects.append(new_object)
        self.plottable_count += 1

    def AddPlot2d(self, new_object, parent=None, name=''):
        self.plots2d_data_objects.append(new_object)
        self.plots2d_names.append(name)
        self.plots2d_count += 1

    def __iadd__(self, new_object):
        if isinstance(new_object, rebinned_data):
            self.AddRebinnedData(new_object)
        elif isinstance(new_object, plottable_2d_data):
            self.AddPlottable2dData(new_object)
        return self

def th_2th_single_dataobj():
    info = [{"name": "Theta", "units": "degrees", "values": th_list},
            {"name": "TwoTheta", "units": "degrees", "values": twoth_list},
            {"name": "Measurements", "cols": [
                {"name": "counts"},
                {"name": "pixels"},
                {"name": "monitor"},
                {"name": "count_time"}]},
            {"PolState": '++'}]
    data = MetaArray((th_len, twoth_len, 5), info=info)
    return data

def th_2th_polarized_dataobj():
    info = [{"name": "Theta", "units": "degrees", "values": th_list},
            {"name": "TwoTheta", "units": "degrees", "values": twoth_list},
            {"name": "PolState", "values": "++"},
            {"name": "Measurements", "cols": [
                {"name": "counts"},
                {"name": "pixels"},
                {"name": "monitor"},
                {"name": "count_time"}]},
            {"PolState": '++'}]
    data = MetaArray((th_len, twoth_len, 1, 5), info=info)
    return data

def qx_qz_single_dataobj(qxmin, qxmax, qxbins, qzmin, qzmax, qzbins):
    info = [{"name": "qz", "units": "inv. Angstroms", "values":
             linspace(qzmin, qzmax, qzbins)},
            {"name": "qx", "units": "inv. Angstroms", "values":
             linspace(qxmin, qxmax, qxbins)},
            {"name": "Measurements", "cols": [
                {"name": "counts"},
                {"name": "pixels"},
                {"name": "monitor"},
                {"name": "count_time"}]},
            {"PolState": '++'}]
    data = MetaArray((qzbins, qxbins, 4), info=info)
    return data

def default_qx_qz_grid():
    return EmptyQxQzGrid(-0.003, 0.003, 201, 0, 0.14, 201)

class EmptyQxQzGrid(MetaArray):
    def __new__(subtype, qxmin, qxmax, qxbins, qzmin, qzmax, qzbins):
        creation_story = subtype.__name__
        creation_story += "({0}, {1}, {2}, {3}, {4}, {5})".format(qxmin, qxmax, qxbins, qzmin, qzmax, qzbins)
        info = [
            {"name": "qx", "units": "inv. Angstroms", "values":
             linspace(qxmin, qxmax, qxbins)},
            {"name": "qz", "units": "inv. Angstroms", "values":
             linspace(qzmin, qzmax, qzbins)},
            {"name": "Measurements", "cols": [
                {"name": "counts"},
                {"name": "pixels"},
                {"name": "monitor"},
                {"name": "count_time"}]},
            {'CreationStory': creation_story}]
        data = MetaArray(zeros((qxbins, qzbins, 4)), info=info)
        return data

class EmptyQxQzGridPolarized(MetaArray):
    def __new__(subtype, qxmin, qxmax, qxbins, qzmin, qzmax, qzbins):
        creation_story = subtype.__name__
        creation_story += "({0}, {1}, {2}, {3}, {4}, {5})".format(qxmin, qxmax, qxbins, qzmin, qzmax, qzbins)
        info = [
            {"name": "qx", "units": "inv. frakking Angstroms", "values":
             linspace(qxmin, qxmax, qxbins)},
            {"name": "qz", "units": "inv. Angstroms", "values":
             linspace(qzmin, qzmax, qzbins)},
            {"name": "Measurements", "cols": [
                {"name": "counts_down_down"},
                {"name": "counts_down_up"},
                {"name": "counts_up_down"},
                {"name": "counts_up_up"},
                {"name": "monitor_down_down"},
                {"name": "monitor_down_up"},
                {"name": "monitor_up_down"},
                {"name": "monitor_up_up"},
                {"name": "pixels"},
                {"name": "count_time"}]},
            {'CreationStory': creation_story}]
        data = MetaArray(zeros((qxbins, qzbins, 10)), info=info)
        return data

def th_2th_combined_dataobj():
    info = [{"name": "Theta", "units": "degrees", "values": th_list},
            {"name": "TwoTheta", "units": "degrees", "values": twoth_list},
            {"name": "PolState", "values": ['++', '+-', '-+', '--']},
            {"name": "Measurements", "cols": [
                {"name": "counts"},
                {"name": "pixels"},
                {"name": "monitor"},
                {"name": "count_time"}]}]
    data = MetaArray((th_len, twoth_len, 4, 5), dtype='float', info=info)
    return data

def reflbinned_pixel_single_dataobj(datalen, xpixels):
    info = [{"name": "datapoints", "units": None, "values": range(datalen)},
            {"name": "xpixel", "units": "pixels", "values": range(xpixels)},
            {"name": "Measurements", "cols": [
                {"name": "counts"},
                {"name": "pixels"},
                {"name": "monitor"},
                {"name": "count_time"}]},
            {"PolState": '++'}]
    data = MetaArray(ones((datalen, xpixels, 5)), dtype='float', info=info)
    return data

def reflbinned_pixel_combined_dataobj(datalen, xpixels):
    info = [{"name": "datapoints", "units": None, "values": range(datalen)},
            {"name": "xpixel", "units": "pixels", "values": range(xpixels)},
            {"name": "PolState", "values": ['++', '+-', '-+', '--']},
            {"name": "Measurements", "cols": [
                {"name": "counts"},
                {"name": "pixels"},
                {"name": "monitor"},
                {"name": "count_time"}]}]
    data = MetaArray((datalen, xpixels, 4, 5), info=info)
    return data

class Filter2D:
    """ takes MetaArray with 2 dims (2 cols) as input
    and outputs the same thing """
    default_path = None
    polarizations = ["down_down", "down_up", "up_down", "up_up"]

    def __init__(self, *args, **kwargs):
        self.valid_column_labels = [['', '']]

    def check_labels(self, data):
        validated = True
        labelsets = self.valid_column_labels
        info = data.infoCopy()
        for labelset in labelsets:
            for col, label in zip(info, labelset):
                if not col["name"] == label:
                    validated = False
        return validated

    def validate(self, data):
        validated = True
        if not isinstance(data, MetaArray):
            print("not MetaArray")
            return False #short-circuit
        if not len(data.shape) == 3:
            print("# coordinate dims not equal 2")
            return False
        return self.check_labels(data)

    def apply(self, data):
        if not self.validate(data):
            print("error in data type")
            return
        return data

def updateCreationStory(apply):
    """
    decorator for 'apply' method - it updates the Creation Story
    for each filter application.
    """
    @wraps(apply)
    def newfunc(self, data, *args, **kwargs):
        name = self.__class__.__name__
        new_args = "".join([', {arg}'.format(arg=arg) for arg in args])
        new_kwargs = "".join(', {key}={value}'.format(key=key, value=kwargs[key])
                             for key in kwargs)
        new_creation_story = ".filter('{fname}'{args}{kwargs})".format(fname=name, args=new_args, kwargs=new_kwargs)
        result = apply(self, data, *args, **kwargs)

        # Try update in place data._info instead!
        result._info[-1]["CreationStory"] += new_creation_story
        # if the above didn't work, uncomment this below:
        #new_info = result.infoCopy()
        #new_dtype = result.dtype
        #new_data_array = result.view(ndarray)
        #new_info[-1]["CreationStory"] += new_creation_story
        #new_data = MetaArray(new_data_array, dtype=new_dtype, info=new_info)
        #return new_data
        return result
    return newfunc


def autoApplyToList(apply):
    """
    decorator for 'apply' method - if a list of data objects is given
    as the first argument, applies the filter to each item one at a time.
    """

    @wraps(apply)
    def newfunc(self, data, *args, **kwargs):
        if isinstance(data, list):
            result = []
            for datum in data:
                result.append(apply(self, datum, *args, **kwargs))
            return result
        else:
            return apply(self, data, *args, **kwargs)
    return newfunc

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
        data = counts[:, i].view(ndarray)
        tt = twotheta[i]
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

def matplot2d(data, transform='log', aspect='auto'):
    """ plot 2d data using matplotlib/pylab """
    from pylab import figure, show, imshow, colorbar, title, xlabel, ylabel
    from numpy import log10
    # grab the first counts col:
    cols = data._info[2]['cols']
    data_cols = [col['name'] for col in cols if col['name'].startswith('counts')]

    result = []
    for colnum, col in enumerate(data_cols):
        array_out = data['Measurements':col].view(ndarray)

        dump = {}


        #zbin_base64 = base64.b64encode(array_out.tostring())
        #z = [arr[:, 0].tolist() for arr in self]
        dims = {}
        # can't display zeros effectively in log... set zmin to smallest non-zero

        lowest = 1e-10
        non_zeros = array_out[array_out > lowest]
        if len(non_zeros) > 0:
            dims['zmin'] = float(non_zeros.min())
            dims['zmax'] = float(non_zeros.max())
        else:
            dims['zmin'] = float(lowest)
            dims['zmax'] = float(lowest)

        #dims['zmin'] = array_out.min()
        #dims['zmax'] = array_out.max()
        extent = [
            data._info[0]['values'].min(),
            data._info[0]['values'].max(),
            data._info[1]['values'].min(),
            data._info[1]['values'].max()
        ]

        fig = figure()
        title(data.extrainfo['filename'])
        xlabel(data._info[0]['name'])
        ylabel(data._info[1]['name'])
        #zlabel = self._info[2]['cols'][0]['name']
        toPlot = log10(array_out.T + lowest) if transform == 'log' else array_out.T
        imshow(toPlot, extent=extent, aspect=aspect, origin='lower')
        colorbar()

def gnuplot2d(data, transform='log'):
    """ plot 2d data using matplotlib/pylab """
    from numpy import log10
    # grab the first counts col:
    cols = data._info[2]['cols']
    data_cols = [col['name'] for col in cols if col['name'].startswith('counts')]

    result = []
    for colnum, col in enumerate(data_cols):
        array_out = data['Measurements':col].view(ndarray)

        dump = ""
        xlist = data._info[0]['values'].tolist()
        ylist = data._info[1]['values'].tolist()
        for ix, x in enumerate(xlist):
            dump += "\n"
            for iy, y in enumerate(ylist):
                dump += "%g\t%g\t%g\n" % (x, y, array_out[ix, iy])
        result.append(dump)

    return result

class CoordinateOffset(Filter2D):
    """ apply an offset to one or both of the coordinate axes """

    @autoApplyToList
    @updateCreationStory
    def apply(self, data, offsets=None):
        """ to apply an offset to an axis, add it to the dict of offsets.
        e.g. if data is theta, twotheta, then
        to apply 0.01 offset to twotheta only make offsets = {'twotheta': 0.01}
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

class MaskData(Filter2D):
    """ set all data, normalization to zero within mask """

    @autoApplyToList
    @updateCreationStory
    def apply(self, data, xmin=None, xmax=None, ymin=None, ymax=None, invert_mask=False):
        def sanitize (item):
            return int(item) if item != "" else None
        mask = zeros(data.shape, dtype=bool) # array of False
        # convert to data coordinates
        x_array = data._info[0]['values']
        y_array = data._info[1]['values']

        def get_index(t, x):
            if x == "" or x is None:
                return None
            if float(x) > t.max():
                return None
            if float(x) < t.min():
                return None
            return searchsorted(t, float(x))

        dataslice = (slice(get_index(x_array, xmin), get_index(x_array, xmax)),
                     slice(get_index(y_array, ymin), get_index(y_array, ymax)))
        #print("indexing:", get_index(x_array, xmin), get_index(x_array, xmax, get_index(y_array, ymin), get_index(y_array, ymax))
        print(dataslice)
        mask[dataslice] = True # set the masked portions to False
        if invert_mask:
            mask = logical_not(mask)
        new_data = MetaArray(data.view(ndarray).copy(), info=data.infoCopy())
        new_data.view(ndarray)[mask] = 0
        return new_data

#class MaskData(Filter2D):
#    """ set all data, normalization to zero within mask """
#
#    @autoApplyToList
#    @updateCreationStory
#    def apply(self, data, xmin=None, xmax=None, ymin=None, ymax=None):
#        def sanitize (item):
#            return int(item) if item != "" else None
#        dataslice = (slice(sanitize(xmin), sanitize(xmax)), slice(sanitize(ymin), sanitize(ymax)))
#        new_data = MetaArray(data.view(ndarray).copy(), info=data.infoCopy())
#        new_data[dataslice] = 0
#        return new_data

class SliceNormData(Filter2D):
    """ Sum 2d data along both axes and return 1d datasets,
    normalized to col named in normalization param """

    @autoApplyToList
    def apply(self, data, normalization='monitor'):
        new_info = data.infoCopy()
        x_axis = new_info[0]
        y_axis = new_info[1]

        counts_array = data['Measurements':'counts'].view(ndarray)
        norm_array = data['Measurements':normalization].view(ndarray)
        y_out = zeros((data.shape[1], 2))
        x_out = zeros((data.shape[0], 2))

        norm_y = sum(norm_array, axis=0)
        sum_y = sum(counts_array, axis=0)
        mask_y = (norm_y != 0)
        y_out[:, 0][mask_y] += sum_y[mask_y] / norm_y[mask_y]
        y_out[:, 1][mask_y] += sqrt(sum_y)[mask_y] / norm_y[mask_y]

        norm_x = sum(norm_array, axis=1)
        sum_x = sum(counts_array, axis=1)
        mask_x = (norm_x != 0)
        x_out[:, 0][mask_x] += sum_x[mask_x] / norm_x[mask_x]
        x_out[:, 1][mask_x] += sqrt(sum_x)[mask_x] / norm_x[mask_x]

        col_info = {"name": "Measurements", "cols": [
            {"name": "counts"},
            {"name": "error"}]}

        x_data_obj = MetaArray(x_out, info=[x_axis, col_info, new_info[-1]])
        y_data_obj = MetaArray(y_out, info=[y_axis, col_info, new_info[-1]])

        return [x_data_obj, y_data_obj]

class CollapseData(Filter2D):
    """ Sum 2d data along both axes and return 1d datasets """

    @autoApplyToList
    def apply(self, data):
        new_info = data.infoCopy()
        x_axis = new_info[0]
        y_axis = new_info[1]
        col_info = new_info[2]
        extra_info = new_info[3]

        x_out = sum(data.view(ndarray), axis=1)
        y_out = sum(data.view(ndarray), axis=0)

        x_data_obj = MetaArray(x_out, info=[x_axis, col_info, extra_info])
        y_data_obj = MetaArray(y_out, info=[y_axis, col_info, extra_info])

        return [x_data_obj, y_data_obj]

class SliceData(Filter2D):
    """ Sum 2d data along both axes and return 1d datasets """

    @autoApplyToList
    def apply(self, data, xmin=None, xmax=None, ymin=None, ymax=None):
        new_info = data.infoCopy()
        x_axis = new_info[0]
        y_axis = new_info[1]
        col_info = new_info[2]
        extra_info = new_info[3]

        x_array = data._info[0]['values']
        y_array = data._info[1]['values']

        print(xmin, xmax, ymin, ymax)

        def get_index(t, x):
            if x == "" or x is None:
                return None
            if float(x) > t.max():
                return None
            if float(x) < t.min():
                return None
            return searchsorted(t, float(x))

        xslice = slice(get_index(x_array, xmin), get_index(x_array, xmax))
        yslice = slice(get_index(y_array, ymin), get_index(y_array, ymax))
        dataslice = (xslice, yslice)

        x_out = nansum(data.view(ndarray)[dataslice], axis=1)
        y_out = nansum(data.view(ndarray)[dataslice], axis=0)
        x_axis['values'] = x_axis['values'][xslice]
        y_axis['values'] = y_axis['values'][yslice]

        x_data_obj = MetaArray(x_out, info=[x_axis, col_info, extra_info])
        y_data_obj = MetaArray(y_out, info=[y_axis, col_info, extra_info])

        return [x_data_obj, y_data_obj]

class FootprintCorrection(Filter2D):
    """ correct the incident intensity (monitor) by a geometric factor that depends
    on the distances between the slits 1 and 2, and the sample.  See thesis of Hua
    for details. """

    @autoApplyToList
    def apply(self, data, w1=None, w2=None, L1=None, L2=None, LSample=None):
        new_info = data.infoCopy()
        output_data = data.view(ndarray).copy()
        cols = [col['name'] for col in data._info[-2]['cols']]
        monitor_cols = [col for col in cols if col.startswith('monitor')]

        axis_names = [new_info[0]['name'], new_info[1]['name']]
        axes = set([1, 0])
        if "theta" in axis_names:
            th_axis_num = axis_names.index("theta")
            th_axis = "theta"
        elif "alpha_i" in axis_names:
            th_axis_num = axis_names.index("alpha_i")
            th_axis = "alpha_i"
        axes.remove(th_axis_num)
        other_axis = None
        new_data = MetaArray(output_data, info=new_info)
        return new_data

class WiggleCorrection(Filter2D):
    """
    Remove the oscillatory artifact from the Brookhaven 2D detector data
    This filter properly works on data in pixel coordinates, so it belongs
    right at the beginning of most filter chains, before data is converted to
    angle (and then Q...)

    The artifact is defined as being a sinusoidal variation in the effective width
    of the pixel --- this results in two effects:
    1. an apparent oscillation in sensitivity
    2. an oscillatory shift in the effective location of the pixel with
        respect to an ordered grid of pixels.
    """

    def __init__(self, amp=0.140, **kwargs):
        Filter2D.__init__(self, **kwargs)
        self.wiggleAmplitude = amp
        self.valid_column_labels = [["theta", "xpixel"]]


    def correctionFromPixel(self, xpixel, wiggleAmplitude):
        xpixel = xpixel.astype('float')
        #wiggleAmplitude = self.wiggleAmplitude
        #pixelCorrection = ( (32.0 / (2.0 * pi) ) * wiggleAmplitude * sin( 2.0 * pi * xpixel / 32.0 ) )
        widthCorrection = (wiggleAmplitude * cos(2.0 * pi * xpixel / 32.0))
        pixelCorrection = cumsum(widthCorrection) - widthCorrection[0]
        return [widthCorrection, pixelCorrection]

    @autoApplyToList
    @updateCreationStory
    def apply(self, data, amp=0.14):
        """ Data is MetaArray (for now) with axis values + labels
        Output is the same """
        if not self.validate(data):
            print("error in data type")
            return

        num_xpixels = len(data.axisValues('xpixel'))
        if not num_xpixels == 608:
            print("this correction is only defined for Brookhaven detector!")
        xpixel = data.axisValues('xpixel')
        #arange(num_xpixels + 1, 'float')
        widthCorrection, pixelCorrection = self.correctionFromPixel(xpixel, amp)
        corrected_pixel = xpixel + pixelCorrection
        intens = data['Measurements': 'counts']
        corrected_I = intens / (1.0 + widthCorrection)
        new_info = data.infoCopy()
        new_info[1]["values"] = corrected_pixel
        new_data = MetaArray(data.view(ndarray).copy(), info=new_info)
        new_data['Measurements': 'counts'] = corrected_I

        return new_data

class SmoothData(Filter2D):
    """ takes the input and smooths it according to
    the specified window type and width, along the given axis """


    @autoApplyToList
    @updateCreationStory
    def apply(self, data, window="flat", width=5, axis=0):
        """smooth the data using a window with requested size.

        ****************************************************************
        *** Adapted from https://www.scipy.org/Cookbook/SignalSmooth ***
        ****************************************************************

        This method is based on the convolution of a scaled window with the signal.
        The signal is prepared by introducing reflected copies of the signal
        (with the window size) in both ends so that transient parts are minimized
        in the begining and end part of the output signal.

        input:
            data: the input signal
            width: the dimension of the smoothing window; should be an odd integer
            window: the type of window from 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'
                flat window will produce a moving average smoothing.
            axis: the axis to which the smoothing is applied

        output:
            the smoothed signal

        example:

        t=linspace(-2,2,0.1)
        x=sin(t)+randn(len(t))*0.1
        y=smooth(x)

        see also:

        numpy.hanning, numpy.hamming, numpy.bartlett, numpy.blackman, numpy.convolve
        scipy.signal.lfilter

        TODO: the window parameter could be the window itself if an array instead of a string
        """
        # on demand loading
        from scipy import signal
        axis = int(axis)
        width = int(width)
        src_data = data.view(ndarray)

        if src_data.shape[axis] < width:
            raise ValueError("Input vector " + str(src_data.shape)
                             + " needs to be bigger than window size: " + str(width))

        if width < 3:
            return data

        if window not in ['flat', 'hanning', 'hamming', 'bartlett', 'blackman']:
            raise ValueError("Window is not one of 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'")

        if window == 'flat': #moving average
            kernel = ones(width, 'd')
        else:
            #w=eval('numpy.'+window+'(window_len)')
            kernel = getattr(numpy, window)(width)

        ia_size = list(src_data.shape) # intermediate array initialization
        ia_size[axis] += 2*(width-1)
        ia = empty(ia_size)

        #start with empty slices over first two axes
        output_slice = [slice(None, None)] * len(ia.shape)
        input_slice = [slice(None, None)] * len(src_data.shape)
        first_element_slice = [slice(None, None)] * len(src_data.shape)
        first_element_slice[axis] = slice(0, 1)
        last_element_slice = [slice(None, None)] * len(src_data.shape)
        last_element_slice[axis] = slice(-1, None)

        # mirror data around left edge (element zero):
        input_slice[axis] = slice(width, 1, -1)
        output_slice[axis] = slice(None, width-1, 1)
        ia[output_slice] = 2*src_data[first_element_slice] - src_data[input_slice]
        # mirror data around right edge (last element, -1):
        input_slice[axis] = slice(-1, -width, -1)
        output_slice[axis] = slice(-(width-1), None)
        ia[output_slice] = 2*src_data[last_element_slice] - src_data[input_slice]
        # fill the center of the expanded array with the original array
        output_slice[axis] = slice(width-1, -(width-1), 1)
        ia[output_slice] = src_data[:]

        kernel_shape = [1,] * len(src_data.shape)
        kernel_shape[axis] = width
        kernel.shape = tuple(kernel_shape)

        # modes include same, valid, full
        sm_ia = signal.convolve(ia, kernel, mode='same')
        output_slice[axis] = slice(width-1, -(width-1), 1)

        new_info = data.infoCopy()
        smoothed_data = sm_ia[output_slice]
        output_data = src_data.copy()

        # now go through and replace counts cols
        for colnum, col in enumerate(new_info[-2]['cols']):
            if col['name'].startswith('counts'):
                output_data[..., colnum] = smoothed_data[..., colnum]

        new_data = MetaArray(output_data, info=new_info)

        return new_data

        #y=numpy.convolve(w/w.sum(),s,mode='same')
        #return y[window_len-1:-window_len+1]

class NormalizeToMonitor(Filter2D):
    """ divide all the counts columns by monitor and output as normcounts, with stat. error """

    @autoApplyToList
    def apply(self, data):
        cols = [col['name'] for col in data._info[-2]['cols']]
        passthrough_cols = [col for col in cols if not col.startswith('counts')] # and not col.startswith('monitor'))]
        counts_cols = [col for col in cols if col.startswith('counts')]
        monitor_cols = [col for col in cols if col.startswith('monitor')]
        info = data.infoCopy()
        info[-2]['cols'] = []
        output_array = zeros(data.shape[:-1] + (len(counts_cols) + len(passthrough_cols),),
                             dtype=float) * nan
        expressions = []
        for i, col in enumerate(passthrough_cols):
            info[-2]['cols'].append({"name":col})
            output_array[..., i] = data["Measurements":col]

        for i, col in enumerate(counts_cols):
            j = i + len(passthrough_cols)
            col_suffix = col[len('counts'):]
            monitor_id = 'monitor'
            if 'monitor'+col_suffix in monitor_cols:
                monitor_id += col_suffix
            info[-2]['cols'].append({"name":"counts_norm%s" % (col_suffix,)})
            mask = data["Measurements":monitor_id].nonzero()
            #print(mask)
            output_array[..., j][mask] \
                = data["Measurements":col][mask] / data["Measurements":monitor_id][mask]
            #expression = "data1_counts%s / data1_%s" % (col_suffix, monitor_id)
            #error_expression = "sqrt(data1_counts%s) / data1_%s" % (col_suffix, monitor_id)
            #expressions.append({"name": "counts_norm%s" % (col_suffix,), "expression":expression})
            #expressions.append({"name": "error_counts_norm%s" % (col_suffix,), "expression":error_expression})
        #result = Algebra().apply(data, None, expressions, passthrough_cols)
        result = MetaArray(output_array, info=info)
        return result

class PixelsToTwotheta(Filter2D):
    """ input array has axes theta and pixels:
    output array has axes theta and twotheta.

    Pixel-to-angle conversion is arithmetic (pixels-per-degree=constant)
    output is rebinned to fit in a rectangular array if detector angle
    is not fixed. """

    @autoApplyToList
    @updateCreationStory
    def apply(self, data, pixels_per_degree=50.0, qzero_pixel=149.0, instr_resolution=1e-6, ax_name='xpixel'):
        """\
            input array has axes theta and pixels:
            output array has axes theta and twotheta.

            Pixel-to-angle conversion is arithmetic (pixels-per-degree=constant)
            output is rebinned to fit in a rectangular array if detector angle
            is not fixed. """
        print(" inside PixelsToTwoTheta ")
        pixels_per_degree = float(pixels_per_degree) # coerce, in case it was an integer
        qzero_pixel = float(qzero_pixel)
        instr_resolution = float(instr_resolution)

        new_info = data.infoCopy()
        det_angle = new_info[-1].get('det_angle', None)
        # det_angle should be a vector of the same length as the other axis (usually theta)
        # or else just a float, in which case the detector is not moving!
        ndim = len(new_info) - 2 # last two entries in info are for metadata
        pixel_axis = next((i for i in xrange(len(new_info)-2) if new_info[i]['name'] == ax_name),
                          None)
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
            print("doing the simple switch of axis values...")

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
            output_shape = [0, 0, 0]
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
                    new_array = reb.rebin(input_twoth_bin_edges,
                                          array_to_rebin,
                                          output_twoth_bin_edges)
                    new_data.view(ndarray)[input_slice] = new_array

        return new_data

class Autogrid(Filter2D):
    """ take multiple datasets and create a grid which covers all of them
    - stepsize is smallest stepsize found in datasets
    returns an empty grid with units and labels

    if extra_grid_point is True, adds one point to the end of each axis
    so each dimension is incremented by one (makes edges for rebinning) """

    def apply(self, list_of_datasets, operation='union', extra_grid_point=True, min_step=1e-10):
        num_datasets = len(list_of_datasets)
        dims = 2
        dim_min = zeros((dims, num_datasets))
        dim_max = zeros((dims, num_datasets))
        dim_len = zeros((dims, num_datasets))
        dim_step = zeros((dims, num_datasets))

        for i, data in enumerate(list_of_datasets):
            info = data.infoCopy()
            for dim in range(dims):
                av = data.axisValues(dim)
                dim_min[dim, i] = av.min()
                dim_max[dim, i] = av.max()
                dim_len[dim, i] = len(av)
                if dim_len[dim, i] > 1:
                    dim_step[dim, i] = (float(dim_max[dim, i] - dim_min[dim, i])
                                        / (dim_len[dim, i] - 1))
                    # dim0_max[i] += th_step[i] # add back on the last step
                else:
                    dim_step[dim, i] = min_step

        final_stepsizes = []
        absolute_max = []
        absolute_min = []
        for dim in range(dims):
            dim_stepsize = dim_step[dim].min()
            if dim_stepsize < min_step:
                dim_stepsize = min_step
            final_stepsizes.append(dim_stepsize)

            if operation == 'union':
                absolute_max.append(dim_max[dim].max())
                absolute_min.append(dim_min[dim].min())
            elif operation == 'intersection':
                absolute_max.append(dim_max[dim].min())
                absolute_min.append(dim_min[dim].max())
            else:
                raise ValueError('operation must be one of "union" or "intersection"')

        # now calculate number of steps:
        output_dims = []
        for dim in range(dims):
            if (dim_len[dim].max() == 1) or (absolute_max[dim] == absolute_min[dim]):
                steps = 1
            else:
                steps = int(round(float(absolute_max[dim] - absolute_min[dim])
                                  / final_stepsizes[dim]))
            if extra_grid_point == True:
                steps += 1
            output_dims.append(steps)

        new_info = list_of_datasets[0].infoCopy() # take units etc from first dataset
         # then tack on the number of columns already there:
        output_dims.append(len(new_info[2]['cols']))
        for dim in range(dims):
            new_info[dim]["values"] = (arange(output_dims[dim], dtype='float')
                                       * final_stepsizes[dim]) + absolute_min[dim]
        output_grid = MetaArray(zeros(tuple(output_dims)), info=new_info)
        return output_grid




class InsertTimestamps(Filter2D):
    """ This is a hack.
    Get the timestamps from the source file directory listing
    and interpolate between the start time and the end time.
    """

    @autoApplyToList
    @updateCreationStory
    def apply(self, data, timestamps, override_existing=False, filename=None):
        # first of all, if there is already a timestamp, skip!
        #extra info changed
        if data._info[-1].has_key('end_datetime') and not override_existing:
            return data
        # now figure out which file was the source:
        new_info = data.infoCopy()
        source_filename = filename[1:] or new_info[-1]['filename'][1:] # strip off leading 'I'
        try:
            end_timestamp = timestamps[source_filename]
        except KeyError:
            print("source file 'last modified time' (mtime) not found")
            return
        end_datetime = datetime.datetime.fromtimestamp(end_timestamp)
        new_info[-1]['end_datetime'] = end_datetime
        new_data_array = data.view(ndarray).copy()
        new_data = MetaArray(new_data_array, info=new_info)
        return new_data


class AppendPolarizationMatrix(Filter2D):
    """
    Takes a dataset with a defined polarization state (not None) and
    calculates the row of the NT matrix that corresponds to each datapoint
    (This is more straightforward for raw pixel data where the
    timestamp is the same for all pixels in a single measurement 'point')
    """

    @autoApplyToList
    @updateCreationStory
    def apply(self, data, he3cell=None):
        """ can use He3AnalyzerCollection in place of He3Analyzer...
        then calls to getNTRow(t) get automatically routed to the correct cell object
        """
        #cell = self.supervisor.He3_cells[str(inData.cell_id)] # link to the cell object
        if he3cell == None:
            print("where is the He cell?")
            # extra info changed
            he3cell = He3AnalyzerCollection(path=data._info[-1]['path'])
        new_info = data.infoCopy()
        if not new_info[-1]['PolState'] in  ["_down_down", "_up_down", "_down_up", "_up_up"]:
            print("polarization state not defined: can't get correction matrix")
            return
        start_datetime = new_info[-1]['start_datetime']
        #start_time_offset = start_datetime - he3cell.start_datetime
        #offset_seconds = start_time_offset.days * 86400. + start_time_offset.seconds
        # weird implementation of datetime difference measures in days, seconds, microseconds
        end_datetime = new_info[-1]['end_datetime']
        elapsed = end_datetime - start_datetime
        datalen = data.shape[0]
        delta_t = elapsed / datalen
        #el_seconds = el.days * 86400. + el.seconds # datetime timedelta is an odd duck


        time_list = [start_datetime + delta_t * i for i in range(datalen)]
        #time_array += offset_seconds # get total time from cell T0
        #time_array.shape += (1,)

        data_array = data.view(ndarray).copy()
        new_data_array = zeros(data_array.shape[:-1] + (data_array.shape[-1] + 4,))
        new_data_array[:, :, 0:-4] = data_array[:]
        PolState = new_info[-1]['PolState']
        #flipper_on = (PolState[0] == '-') # check for flipper on in incoming polarization state
        flipper_on = PolState.startswith("_down") # check for flipper on in incoming polarization state
        #He3_up = (PolState[1] == '+')
        He3_up = PolState.endswith("up")
        for i in range(datalen):
            t = start_datetime + delta_t * i
            #print('t: ', t)
            pol_corr = he3cell.getNTRow(t, flipper_on=flipper_on, He3_up=He3_up)
            monitor_row = data['Measurements':'monitor'][i].view(ndarray).copy()
            # NT is multiplied by I_0, or monitor in this case:
            new_data_array[i, :, -4:] = pol_corr[newaxis, :] * monitor_row[:, newaxis]


        #pol_corr_list = [he3cell.getNTRow(t, flipper_on = flipper_on, He3_up = He3_up) for t in time_list]
        #pol_corr_array = array(pol_corr_list)

        #fill the first four columns with existing data:

        #1new_data_array[:,:,0:4] = data_array[:,:,0:4]

        # now append the polarization matrix elements!
        # from He3Analyzer:
        # """creates matrix elements for the polarization-correction
        #    this assumes the order of elements is Rup-up, Rup-down, Rdown-down, Rdown-up
        #    and for I: Iup-up, Iup-down, Idown-up, Idown-down   """

        #1new_data_array[:,:,4:8] = pol_corr_array[newaxis, newaxis, :]

        # the order of columns here is determined by the order coming out of He3Analyer NTRow:
        # (++, +-, --, -+)
        pol_columns = [
            {"name": 'NT_up_up'},
            {"name": 'NT_up_down'},
            {"name": 'NT_down_down'},
            {"name": 'NT_down_up'}]
        new_info[2]["cols"] = new_info[2]["cols"][:4] + pol_columns
        new_data = MetaArray(new_data_array, info=new_info)

        return new_data



class Combine(Filter2D):
    """ combine multiple datasets with or without overlap, adding
    all the values in the time, monitor and data columns, and populating
    the pixels column (number of pixels in each new bin)

    If no grid is provided, use Autogrid filter to generate one.
    """
    #@updateCreationStory
    def apply(self, list_of_datasets, grid=None):
        if grid == None:
            grid = Autogrid().apply(list_of_datasets)
        for dataset in list_of_datasets:
            grid = self.add_to_grid(dataset, grid)

        # extra info changed
        old_creation_stories = "[" + "".join([data._info[-1]['CreationStory'] + ", " for data in list_of_datasets]) + "]"
        name = self.__class__.__name__
        new_creation_story = "{fname}().apply({oldcs})".format(fname=name, oldcs=old_creation_stories)
        grid._info[-1]['CreationStory'] = new_creation_story
        # strip info that is meaningless in combined dataset: (filename, start_time, end_time)
        for key in ['filename', 'start_datetime', 'end_datetime']:
            if grid._info[-1].has_key(key): grid._info[-1].pop(key)
        return grid

    def add_to_grid(self, dataset, grid):
        dims = 2
        grid_slice = [slice(None, None, 1),] * dims
        bin_edges = []
        for dim in range(dims):
            av = grid.axisValues(dim).copy()
            dspacing = (av[-1] - av[0]) / (len(av) - 1)
            edges = resize(av, len(av) + 1)
            edges[-1] = av[-1] + dspacing
            if dspacing < 0:
                edges = edges[::-1] # reverse
                grid_slice[dim] = slice(None, None, -1)
            bin_edges.append(edges)

        data_edges = []
        data_slice = [slice(None, None, 1),] * dims
        for dim in range(dims):
            av = dataset.axisValues(dim).copy()
            dspacing = (av[-1] - av[0]) / (len(av) - 1)
            edges = resize(av, len(av) + 1)
            edges[-1] = av[-1] + dspacing
            if dspacing < 0:
                edges = edges[::-1] # reverse
                data_slice[dim] = slice(None, None, -1)
            data_edges.append(edges)

        #cols_to_add = ['counts', 'pixels', 'monitor', 'count_time'] # standard data columns
        #cols_to_add += ['NT++', 'NT+-', 'NT-+', 'NT--'] # add in all the polarization correction matrices too!

        new_info = dataset.infoCopy()
        for i, col in enumerate(new_info[2]['cols']):
            #if col['name'] in cols_to_add:
            array_to_rebin = dataset[:, :, col['name']].view(ndarray)
            #print(data_edges, bin_edges)
            new_array = reb.rebin2d(data_edges[0], data_edges[1],
                                    array_to_rebin[data_slice],
                                    bin_edges[0], bin_edges[1])
            grid[:, :, col['name']] += new_array[grid_slice]

        return grid

class CombinePolarized(Filter2D):
    """
    Combines on a per-polarization state basis.
    Master output grid is calculated that will cover ALL the inputs,
    without regard for polarization state, but then separate
    copies of this grid are filled with data from each
    PolState separately.
    """

    def sortByPolarization(self, list_of_datasets):
        """ takes an unsorted list of datasets, peeks at the PolState inside,
        and groups them into a labeled list of lists (dictionary!)"""
        pol_datasets = {}
        for dataset in list_of_datasets:
            # extra info changed
            PolState = dataset._info[-1].get('PolState', '')
            if not PolState in pol_datasets.keys():
                pol_datasets[PolState] = []
            pol_datasets[PolState].append(dataset)
        return pol_datasets

    def getListOfDatasets(self, pol_datasets):
        """ inverse of sortByPolarization: take a dictionary of PolState-grouped
        data and return a flat list of every dataset inside """
        list_of_datasets = []
        for PolState in pol_datasets:
            list_of_datasets += pol_datasets[PolState]
        return list_of_datasets


    def apply(self, pol_datasets, grid=None):
        if isinstance(pol_datasets, list):
            # then we got an unordered list of polarized datasets.
            # that's ok - we can label and group them together!
            list_of_datasets = pol_datasets
            pol_datasets = self.sortByPolarization(pol_datasets)
        else:
            list_of_datasets = self.getListOfDatasets(pol_datasets)

        if grid == None:
            grid = Autogrid().apply(list_of_datasets)
        # grid covering all polstates is now made:  now create
        # sublists for each polarization state

        combined_datasets = []
        for PolState in pol_datasets:
            # combined single polarization:
            csingle = Combine().apply(pol_datasets[PolState], deepcopy(grid))
            #print(type(pol_datasets[PolState]))
            #extra info changed
            csingle._info[-1]['PolState'] = PolState
            combined_datasets.append(csingle)
        # we end up with a dictionary set of datasets (e.g. {"++": data1, "--": data2} )

        return   d_datasets



class TwothetaToQ(Filter2D):
    """ Figures out the Q values of an axis.
    """

    @autoApplyToList
    @updateCreationStory
    def apply(self, data, wavelength=5.0, ax_name='twotheta'):
        print(" inside TwoThetaToQ ")
        wavelength = float(wavelength)

        new_info = data.infoCopy()
        ndim = len(new_info) - 2 # last two entries in info are for metadata
        twotheta_axis = next((i for i in xrange(len(new_info)-2) if new_info[i]['name'] == ax_name),
                             None)
        if twotheta_axis < 0:
            raise ValueError("error: no %s axis in this dataset" % (ax_name,))

        print("doing the simple switch of axis values...")

        if ax_name == 'twotheta':
            new_info[twotheta_axis]['name'] = 'qx'
        else:
            new_info[twotheta_axis]['name'] = 'qy'

        twotheta = new_info[twotheta_axis]['values']
        q = 4.0*pi/wavelength * sin((twotheta/2.0) * pi/180.0)
        #new_info[pixel_axis]['values'] = twoth[::-1] # reverse: twotheta increases as pixels decrease
        new_info[twotheta_axis]['values'] = q
        new_info[twotheta_axis]['units'] = 'inv. Angstroms'
        #new_array = (data.view(ndarray).copy())[data_slices]
        new_array = (data.view(ndarray).copy())
        new_data = MetaArray(new_array, info=new_info)

        return new_data


class ThetaTwothetaToQxQz(Filter2D):
    """ Figures out the Qx, Qz values of each datapoint
    and throws them in the correct bin.  If no grid is specified,
    one is created that covers the whole range of Q in the dataset

    If autofill_gaps is True, does reverse lookup to plug holes
    in the output (but pixel count is still zero for these bins)
    """

    default_qxqz_gridvals = (-0.003, 0.003, 201, 0, 0.1, 201)

    @autoApplyToList
    #@updateCreationStory
    def apply(self, data, output_grid=None, wavelength=5.0, qxmin=None,
              qxmax=None, qxbins=None, qzmin=None, qzmax=None, qzbins=None):
    #def apply(self, data, output_grid=None, wavelength=5.0):
        if output_grid == None:
            info = [{"name": "qx", "units": "inv. Angstroms", "values": linspace(qxmin, qxmax, qxbins)},
                    {"name": "qz", "units": "inv. Angstroms", "values": linspace(qzmin, qzmax, qzbins)}]
            old_info = data.infoCopy()
            info.append(old_info[2]) # column information!
            info.append(old_info[3]) # creation story!
            output_grid = MetaArray(zeros((qxbins, qzbins, data.shape[-1])), info=info)
            #output_grid = EmptyQxQzGrid(*self.default_qxqz_gridvals)
        else:
            #outgrid_info = data._info.copy()
            #outgrid_info[0] = {"name": "qx", "units": "inv. frakking Angstroms", "values": linspace(qxmin, qxmax, qxbins) }
            #outgrid_info[1] = {"name": "qz", "units": "inv. Angstroms", "values": linspace(qzmin, qzmax, qzbins) }
            outgrid_info = deepcopy(output_grid._info) # take axes and creation story from emptyqxqz...
            outgrid_info[2] = deepcopy(data._info[2]) # take column number and names from dataset
            output_grid = MetaArray(zeros((output_grid.shape[0], output_grid.shape[1], data.shape[2])),
                                    info=outgrid_info)

        theta_axis = data._getAxis('theta')
        twotheta_axis = data._getAxis('twotheta')

        qLength = 2.0 * pi / wavelength
        th_array = data.axisValues('theta').copy()
        twotheta_array = data.axisValues('twotheta').copy()

        if theta_axis < twotheta_axis: # then theta is first: add a dimension at the end
            th_array.shape = th_array.shape + (1,)
            twotheta_array.shape = (1,) + twotheta_array.shape
        else:
            twotheta_array.shape = twotheta_array.shape + (1,)
            th_array.shape = (1,) + th_array.shape

        tilt_array = th_array - (twotheta_array / 2.0)
        qxOut = 2.0 * qLength * sin((pi/180.0) * (twotheta_array/2.0)) * sin(pi*tilt_array/180.0)
        qzOut = 2.0 * qLength * sin((pi/180.0) * (twotheta_array/2.0)) * cos(pi*tilt_array/180.0)

        # getting values from output grid:
        outgrid_info = output_grid.infoCopy()
        numcols = len(outgrid_info[2]['cols'])
        qx_array = output_grid.axisValues('qx')
        dqx = qx_array[1] - qx_array[0]
        qz_array = output_grid.axisValues('qz')
        dqz = qz_array[1] - qz_array[0]
        #framed_array = zeros((qz_array.shape[0] + 2, qx_array.shape[0] + 2, numcols))
        target_qx = ((qxOut - qx_array[0]) / dqx).astype(int)
        #return target_qx, qxOut
        target_qz = ((qzOut - qz_array[0]) / dqz).astype(int)

        target_mask = (target_qx >= 0) * (target_qx < qx_array.shape[0])
        target_mask *= (target_qz >= 0) * (target_qz < qz_array.shape[0])
        target_qx_list = target_qx[target_mask]
        target_qz_list = target_qz[target_mask]

        for i, col in enumerate(outgrid_info[2]['cols']):
            values_to_bin = data[:, :, col['name']].view(ndarray)[target_mask]
            outshape = (output_grid.shape[0], output_grid.shape[1])
            hist2d, xedges, yedges = histogram2d(target_qx_list,target_qz_list,
                                                 bins=(outshape[0], outshape[1]),
                                                 range=((0, outshape[0]),(0, outshape[1])),
                                                 weights=values_to_bin)
            output_grid[:, :, col['name']] += hist2d
            #framed_array[target_qz_list, target_qx_list, i] = data[:,:,col['name']][target_mask]

        cols = outgrid_info[2]['cols']
        data_cols = [col['name'] for col in cols if col['name'].startswith('counts')]
        monitor_cols = [col['name'] for col in cols if col['name'].startswith('monitor')]
        # just take the first one...
        if len(monitor_cols) > 0:
            monitor_col = monitor_cols[0]
            data_missing_mask = (output_grid[:, :, monitor_col] == 0)
            for dc in data_cols:
                output_grid[:, :, dc].view(ndarray)[data_missing_mask] = nan


        #extra info changed
        creation_story = data._info[-1]['CreationStory']
        new_creation_story = creation_story + ".filter('{0}', {1})".format(self.__class__.__name__, output_grid._info[-1]['CreationStory'])
        #print(new_creation_story)
        output_grid._info[-1] = data._info[-1].copy()
        output_grid._info[-1]['CreationStory'] = new_creation_story
        return output_grid

class ThetaTwothetaToAlphaIAlphaF(Filter2D):
    """ Figures out the angle in, angle out values of each datapoint
    and throws them in the correct bin.  If no grid is specified,
    one is created that covers the whole range of the dataset

    If autofill_gaps is True, does reverse lookup to plug holes
    in the output (but pixel count is still zero for these bins)
    """

    @autoApplyToList
    #@updateCreationStory
    def apply(self, data):
        theta_axis = data._getAxis('theta')
        twotheta_axis = data._getAxis('twotheta')

        th_array = data.axisValues('theta').copy()
        twotheta_array = data.axisValues('twotheta').copy()

        two_theta_step = twotheta_array[1] - twotheta_array[0]
        theta_step = th_array[1] - th_array[0]

        af_max = (twotheta_array.max() - th_array.min())
        af_min = (twotheta_array.min() - th_array.max())
        alpha_i = th_array.copy()
        alpha_f = arange(af_min, af_max, two_theta_step)

        info = [{"name": "alpha_i", "units": "degrees", "values": th_array.copy()},
                {"name": "alpha_f", "units": "degrees", "values": alpha_f.copy()}]
        old_info = data.infoCopy()
        info.append(old_info[2]) # column information!
        info.append(old_info[3]) # creation story!
        output_grid = MetaArray(zeros((th_array.shape[0], alpha_f.shape[0], data.shape[-1])),
                                info=info)

        if theta_axis < twotheta_axis: # then theta is first: add a dimension at the end
            alpha_i.shape = alpha_i.shape + (1,)
            ai_out = indices((th_array.shape[0], twotheta_array.shape[0]))[0]
            twotheta_array.shape = (1,) + twotheta_array.shape
        else:
            alpha_i.shape = (1,) + alpha_i.shape
            ai_out = indices((twotheta_array.shape[0], th_array.shape[0]))[1]
            twotheta_array.shape = twotheta_array.shape + (1,)

        print("ai_out:", ai_out.shape)
        af_out = twotheta_array - alpha_i

        # getting values from output grid:
        outgrid_info = output_grid.infoCopy()
        numcols = len(outgrid_info[2]['cols'])
        #target_ai = ((ai_out - th_array[0]) / theta_step).flatten().astype(int).tolist()
        target_ai = ai_out.flatten().astype(int).tolist()
        #return target_qx, qxOut
        target_af = ((af_out - af_min) / two_theta_step).flatten().astype(int).tolist()

        for i, col in enumerate(outgrid_info[2]['cols']):
            values_to_bin = data[:, :, col['name']].view(ndarray).flatten().tolist()
            print(len(target_ai), len(target_af), len(values_to_bin))
            outshape = (output_grid.shape[0], output_grid.shape[1])
            hist2d, xedges, yedges = histogram2d(target_ai, target_af,
                                                 bins=(outshape[0], outshape[1]),
                                                 range=((0, outshape[0]), (0, outshape[1])),
                                                 weights=values_to_bin)
            output_grid[:, :, col['name']] += hist2d

        cols = outgrid_info[2]['cols']
        data_cols = [col['name'] for col in cols if col['name'].startswith('counts')]
        monitor_cols = [col['name'] for col in cols if col['name'].startswith('monitor')]
        # just take the first one...
        if len(monitor_cols) > 0:
            monitor_col = monitor_cols[0]
            data_missing_mask = (output_grid[:, :, monitor_col] == 0)
            for dc in data_cols:
                output_grid[:, :, dc].view(ndarray)[data_missing_mask] = nan

        #extra info changed
        creation_story = data._info[-1]['CreationStory']
        new_creation_story = creation_story + ".filter('{0}', {1})".format(self.__class__.__name__, output_grid._info[-1]['CreationStory'])
        #print(new_creation_story)
        output_grid._info[-1] = data._info[-1].copy()
        output_grid._info[-1]['CreationStory'] = new_creation_story
        return output_grid

class PolarizationCorrect(Filter2D):
    """
    Takes 2 to 4 input datasets with appended Polarization Matrix,
    inverts the polarization matrix and applies to the data.
    Outputs fully polarization-corrected intensities.

    # 0: "no assumptions (use all I++, I+-, I-+, I--)",
    # 1: "R+- assumed equal to R-+ (use I++, I-+ and I--)",
    # 2: "R-+ assumed equal to R+- (use I++, I+- and I--)",
    # 3: "R-+ and R+- equal zero (use I++, I--)"

    Requires that Polarization state is defined for each dataset ("PolState")
    and that at least "++" and "--" PolStates are present.
    """

    polstate_order = {'_up_up':0, '_up_down':1, '_down_up':2, '_down_down':3}

    def progress_update(self, percent_done):
        print('{0}% done'.format(percent_done))

    def check_grids(self, datasets):
        """ Combined data will be dictionary of labeled datasets:
        e.g. {"++": datapp, "+-": datapm} etc."""
        compatible = True
        firstdata = datasets[0]
        for dataset in datasets[1:]:
            # allclose is the next best thing to "==" for a floating point array
            compatible &= allclose(dataset.axisValues(0), firstdata.axisValues(0))
            compatible &= allclose(dataset.axisValues(1), firstdata.axisValues(1))
        return compatible

    def guess_assumptions(self, datasets):
        assumptions = None
        polstates = [datum._info[-1]['PolState'] for datum in datasets]
        if set(polstates) == set(['_up_up', '_up_down', '_down_up', '_down_down']):
            assumptions = 0
        elif set(polstates) == set(['_up_up', '_down_up', '_down_down']):
            assumptions = 1
        elif set(polstates) == set(['_up_up', '_up_down', '_down_down']):
            assumptions = 2
        elif set(polstates) == set(['_up_up', '_down_down']):
            assumptions = 3
        return assumptions

    def apply(self, combined_data, assumptions=0, auto_assumptions=True):
        # do I apply assumptions here, or in separate subclasses?
        if auto_assumptions:
            assumptions = self.guess_assumptions(combined_data)
            print("assumptions: ", assumptions)

        if not self.check_grids(combined_data):
            # binning on datasets in combined data is not the same!  quit.
            return

        data_shape = combined_data[0].shape
        polstates = [datum._info[-1]['PolState'] for datum in combined_data]

        NT = empty(data_shape[:2] + (4, 4))
        alldata = empty(data_shape[:2] + (len(polstates), 4))
        # recall order of I, R is different for the way we've set up NT matrix (not diagonal)
        # [Iuu, Iud, Idu, Idd] but [Ruu, Rud, Rdd, Rdu]
        #['NT++','NT+-','NT--','NT-+']
        for dataset in combined_data:
            PolState = dataset._info[-1]['PolState']
            NT[:, :, self.polstate_order[PolState]] = dataset[:, :, ['NT_up_up', 'NT_up_down', 'NT_down_up', 'NT_down_down']]
            alldata[:, :, self.polstate_order[PolState]] = dataset[:, :, ['counts', 'pixels', 'monitor', 'count_time']]
            #alldata[:,:,self.polstate_order[PolState]] = combined_data[PolState][:,:,['counts','pixels','monitor','count_time']]
        # should result in:
        #NT[:,:,0] = combined_data['++'][:,:,['NT++','NT+-','NT-+','NT--']]
        #NT[:,:,1] = combined_data['+-'][:,:,['NT++','NT+-','NT-+','NT--']]
        #NT[:,:,2] = combined_data['-+'][:,:,['NT++','NT+-','NT-+','NT--']]
        #NT[:,:,3] = combined_data['--'][:,:,['NT++','NT+-','NT-+','NT--']]
        #alldata[:,:,0] = combined_data['++'][:,:,['counts','pixels','monitor','count_time']]
        #alldata[:,:,1] = combined_data['+-'][:,:,['counts','pixels','monitor','count_time']]
        #alldata[:,:,2] = combined_data['-+'][:,:,['counts','pixels','monitor','count_time']]
        #alldata[:,:,3] = combined_data['--'][:,:,['counts','pixels','monitor','count_time']]
        # by arranging this new NT matrix as above, I'm undoing the weird arrangement in
        # the He3Analyzer module.  now the order is:
        # [Iuu, Iud, Idu, Idd] AND [Ruu, Rud, Rdu, Rdd] !!!
        output_columns = self.polstate_order #{'++':0, '+-':1, '-+':2, '_down_down':3}

        if assumptions == 1:
            NT = NT[:, :, [0, 2, 3], :] #remove +- (second) row
            NT[:, :, :, 1] += NT[:, :, :, 2] # add -+(column 3) to +- (column 2), (cols. 1 and 2 in zero-indexed)
            NT = NT[:, :, :, [0, 1, 4]] # drop column 3 (2 in zero-indexing)
            # should now be (th_len, 2th_len, 3, 3) matrix
            output_columns = {'_up_up':0, '_down_up':1, '_down_down':2}

        elif assumptions == 2:
            NT = NT[:, :, [0, 1, 3], :] #remove -+ (third) row
            NT[:, :, :, 1] += NT[:, :, :, 2] # add -+ column 3 to +- column 2 (zero-indexed)
            NT = NT[:, :, :, [0, 1, 4]] # drop column 3 (2 in zero-indexing)
            # should now be (th_len, 2th_len, 3, 3) matrix
            output_columns = {'_up_up':0, '_up_down':1, '_down_down':2}

        elif assumptions == 3:
            NT = NT[:, :, [0, 3], :] #remove both middle rows
            NT = NT[:, :, :, [0, 3]] # remove both middle columns (1,2 in zero-indexing)
            # should now be (th_len, 2th_len, 2, 2) matrix
            output_columns = {'_up_up':0, '_down_down':1}

        R = deepcopy(alldata)
        # output will have the same shape as input... just with different values!

        invNT = zeros_like(NT)
        normNT = zeros(data_shape[:2])

        n = 0
        percent_done = -1
        nmax = NT.shape[0] * NT.shape[1]
        #return NT

        for i in range(NT.shape[0]):
            for j in range(NT.shape[1]):
                try:
                    invNT[i, j] = linalg.inv(NT[i, j])
                    normNT[i, j] = linalg.norm(invNT[i, j])
                    R[i, j, :, 0] = dot(invNT[i, j], alldata[i, j, :, 0]) # counts
                    R[i, j, :, 1] = dot(invNT[i, j], alldata[i, j, :, 1]) / normNT[i, j] # pixels (need unitary transform)
                    R[i, j, :, 2] = 1.0 # monitor is set to one.  Not sure about this one
                    R[i, j, :, 3] = 1.0 # count time is set to one also.
                except:
                    import sys
                    print(sys.exc_info())
                    sys.exit()
                    R[i, j, :, 0] = 0.0 # counts
                    R[i, j, :, 1] = 0.0 # pixels (need unitary transform)
                    R[i, j, :, 2] = 1.0 # monitor is set to one.  Not sure about this one
                    R[i, j, :, 3] = 1.0 # count time is set to one also.
                    # this leaves zeros where the inversion fails
                    # not sure what else to do!
                n += 1
                new_percent_done = (100 * n) / nmax
                if new_percent_done > percent_done:
                    self.progress_update(new_percent_done)
                    percent_done = new_percent_done

        combined_R = []
        for index, PolState in enumerate(polstates):
            combined_R.append(MetaArray(R[:, :, output_columns[PolState]], info=combined_data[index].infoCopy()))
        return combined_R

    def add_to_grid(self, dataset, grid):
        dims = 2
        bin_edges = []
        for dim in range(dims):
            av = grid.axisValues(dim).copy()
            dspacing = (av.max() - av.min()) / (len(av) - 1)
            edges = resize(av, len(av) + 1)
            edges[-1] = av[-1] + dspacing
            bin_edges.append(edges)

        data_edges = []
        for dim in range(dims):
            av = dataset.axisValues(dim).copy()
            dspacing = (av.max() - av.min()) / (len(av) - 1)
            edges = resize(av, len(av) + 1)
            edges[-1] = av[-1] + dspacing
            data_edges.append(edges)

        cols_to_add = ['counts', 'pixels', 'monitor', 'count_time'] # standard data columns
        cols_to_add += ['NT_up_up', 'NT_up_down', 'NT_down_up', 'NT_down_down'] # add in all the polarization correction matrices too!

        new_info = dataset.infoCopy()
        for i, col in enumerate(new_info[2]['cols']):
            if col['name'] in cols_to_add:
                array_to_rebin = dataset[:, :, col['name']].view(ndarray)
                new_array = reb.rebin2d(data_edges[0], data_edges[1], array_to_rebin, bin_edges[0], bin_edges[1])
                grid[:, :, col['name']] += new_array

        return grid

class wxPolarizationCorrect(PolarizationCorrect):
    def apply(self, *args, **kwargs):
        import wx
        self.progress_meter = wx.ProgressDialog("Progress", "% done", parent=None, style=wx.PD_AUTO_HIDE | wx.PD_APP_MODAL)
        return PolarizationCorrect.apply(self, *args, **kwargs)

    def progress_update(self, percent_done):
        self.progress_meter.Update(int(percent_done), "Polarization Correction Progress:\n{0}% done".format(percent_done))

class Subtract(Filter2D):
    """ takes two data objects and subtracts them.
    If no grid is provided, use Autogrid filter to generate one.
    """
    #@updateCreationStory
    #@autoApplyToList
    def apply(self, minuend, subtrahend):
        #subtrahend = subtrahend[0] # can only subtract one thing... but from many.
        print(len(minuend), len(subtrahend))
        if len(minuend) == len(subtrahend): pass # go with it.
        elif len(subtrahend) == 1: subtrahend = [subtrahend[0] for m in minuend] # broadcast
        else: raise Exception("I don't know what to do with unmatched argument lengths")
        results = []
        for m, s in zip(minuend, subtrahend):
            dim_m = len(m.shape) - 1
            dim_s = len(s.shape) - 1
            if dim_m == 2 and dim_s == 1:
                print("subtract vector from matrix (broadcast subtrahend)")
                s_units = s._info[0]['units']
                m1_units = m._info[0]['units']
                m2_units = m._info[1]['units']
                if s_units == m1_units: active_axis = 0
                elif s_units == m2_units: active_axis = 1
                else: raise Exception("no matching units to subtract from") # bail out!

                new_axisvals = [m._info[0]['values'].copy(), m._info[1]['values'].copy()]
                update_axisvals = new_axisvals[active_axis]
                s_axisvals = s._info[0]['values']
                overlap = slice(get_index(update_axisvals, s_axisvals[0]), get_index(update_axisvals, s_axisvals[-1]))
                print(overlap)
                new_axisvals[active_axis] = update_axisvals[overlap]
                full_overlap = [slice(None, None), slice(None, None)]
                full_overlap[active_axis] = overlap
                full_overlap = tuple(full_overlap)

                output_array = []

                dims = 2
                data_edges = []
                for dim in range(dims):
                    av = new_axisvals[dim].copy()
                    dspacing = (av.max() - av.min()) / (len(av) - 1)
                    edges = resize(av, len(av) + 1)
                    edges[-1] = av[-1] + dspacing
                    data_edges.append(edges)



                #bin_edges = [[data_edges[0][0], data_edges[0][-1]],[data_edges[1][0], data_edges[1][-1]]]
                av = s_axisvals #give the same treatment to the subtrahend asixvals
                dspacing = (av.max() - av.min()) / (len(av) - 1)
                edges = resize(av, len(av) + 1)
                edges[-1] = av[-1] + dspacing
                #bin_edges[active_axis] = edges

                #new_s = reb.rebin(edges, s['Measurements':col], data_edges[active_axis])

                #new_sshape = [1,1]
                #new_sshape[active_axis] = len(new_saxisvals)
                #new_saxisvals.shape = tuple(new_sshape)

                #new_array = reb.rebin2d(data_edges[0], data_edges[1], array_to_rebin, bin_edges[0], bin_edges[1])

                print(m._info[0]['units'], m._info[1]['units'], s._info[0]['units'])
                data_array = m.view(ndarray).copy()[full_overlap]
                new_info = m.infoCopy()
                new_info[0]['values'] = new_axisvals[0]
                new_info[1]['values'] = new_axisvals[1]
                print(data_array.shape, new_axisvals[0].shape, new_axisvals[1].shape)
                new_data = MetaArray(data_array, info=new_info)
                subtractable_columns = [c['name'] for c in s._info[1]['cols'] if c['name'].startswith('counts')]
                #subtractable_columns = dict(subtractable_columns)
                print("subtractable columns:", subtractable_columns)
                for i, col in enumerate(new_info[2]['cols']):
                    if col['name'].startswith('counts') and col['name'] in subtractable_columns:
                        new_s = reb.rebin(edges, s['Measurements':col['name']], data_edges[active_axis])
                        new_sshape = [1, 1]
                        new_sshape[active_axis] = len(new_s)
                        new_s.shape = tuple(new_sshape)
                        new_data['Measurements':col['name']] -= new_s
                results.append(new_data)
            elif dim_m == 2 and dim_s == 2:
                print("subtract matrix from matrix (in overlap)")
                grid = Autogrid().apply([m, s], operation='intersection')
                grid = self.add_to_grid(m, grid, counts_multiplier=1.0)
                grid = self.add_to_grid(s, grid, counts_multiplier=-1.0)
                print(grid._info[0]['units'], m._info[1]['units'], s._info[0]['units'], s._info[1]['units'])
                results.append(grid)
            elif dim_m == 1 and dim_s == 2:
                print("can't do this.")
                print(m._info[0]['units'], s._info[0]['units'], s._info[1]['units'])
                results.append(m)
            elif dim_m == 1 and dim_s == 1:
                print("subtract vector from vector (in overlap)")
                print(m._info[0]['units'], s._info[0]['units'])
                results.append(m)

        return results

    def add_to_grid(self, dataset, grid, counts_multiplier=1.0):
        dims = 2
        grid_slice = [slice(None, None, 1),] * dims
        bin_edges = []
        for dim in range(dims):
            av = grid.axisValues(dim).copy()
            dspacing = (av[-1] - av[0]) / (len(av) - 1)
            edges = resize(av, len(av) + 1)
            edges[-1] = av[-1] + dspacing
            if dspacing < 0:
                edges = edges[::-1] # reverse
                grid_slice[dim] = slice(None, None, -1)
            bin_edges.append(edges)

        data_edges = []
        data_slice = [slice(None, None, 1),] * dims
        for dim in range(dims):
            av = dataset.axisValues(dim).copy()
            dspacing = (av[-1] - av[0]) / (len(av) - 1)
            edges = resize(av, len(av) + 1)
            edges[-1] = av[-1] + dspacing
            if dspacing < 0:
                edges = edges[::-1] # reverse
                data_slice[dim] = slice(None, None, -1)
            data_edges.append(edges)

        #cols_to_add = ['counts', 'pixels', 'monitor', 'count_time'] # standard data columns
        #cols_to_add += ['NT++', 'NT+-', 'NT-+', 'NT--'] # add in all the polarization correction matrices too!

        new_info = dataset.infoCopy()
        for i, col in enumerate(new_info[2]['cols']):
            #if col['name'] in cols_to_add:
            if 'counts' in col['name']:
                multiplier = counts_multiplier
            else:
                multiplier = 1.0  # add monitor counts and time always
            array_to_rebin = dataset[:, :, col['name']].view(ndarray)
            #print(data_edges, bin_edges)
            new_array = reb.rebin2d(data_edges[0], data_edges[1], array_to_rebin[data_slice], bin_edges[0], bin_edges[1])
            grid[:, :, col['name']] += (multiplier * new_array[grid_slice])

        return grid
        # extra info changed
#        old_creation_stories = "[" + "".join([data._info[-1]['CreationStory'] + ", " for data in list_of_datasets]) + "]"
#        name = self.__class__.__name__
#        new_creation_story = "{fname}().apply({oldcs})".format(fname=name, oldcs=old_creation_stories)
#        grid._info[-1]['CreationStory'] = new_creation_story
#        # strip info that is meaningless in combined dataset: (filename, start_time, end_time)
#        for key in ['filename', 'start_datetime', 'end_datetime']:
#            if grid._info[-1].has_key(key): grid._info[-1].pop(key)
#        return grid


class Algebra(Filter2D):
    """ generic algebraic manipulations """
    def get_safe_operations_namespace(self):
        #make a list of safe functions
        safe_list = [
            'math', 'acos', 'asin', 'atan', 'atan2', 'ceil', 'cos', 'cosh',
            'degrees', 'e', 'exp', 'fabs', 'floor', 'fmod', 'frexp', 'hypot',
            'ldexp', 'log', 'log10', 'modf', 'pi', 'pow', 'radians', 'sin',
            'sinh', 'sqrt', 'tan', 'tanh', 'newaxis']
        #use the list to filter the local namespace
        safe_dict = dict([(k, numpy.__dict__.get(k, None)) for k in safe_list])
        return safe_dict

    def add_to_namespace(self, data, prefix, namespace, automask=True):
        cols = data._info[-2]['cols']
        #if automask and ("pixels" in cols):
        #    mask = ( data["Measurements":"pixels"] > 0 )
        #else:
        #    mask = ones(data.shape[:2], dtype=bool)
        for col in cols:
            new_name = str(prefix) + col['name']
            data_view = data['Measurements':col['name']].view(ndarray)
            if automask and ("pixels" in cols):
                data_view = MaskedArray(data_view)
                data_view.mask = (data["Measurements":"pixels"] > 0)
            #namespace[new_name] = data['Measurements':col['name']].view(ndarray)[mask]
            namespace[new_name] = data_view

    @autoApplyToList
    def apply(self, data1=None, data2=None, output_cols=[], passthrough_cols=[], automask=True):
        """ can operate on columns within data1 if needed
        output_cols is in form
        [{"name":"output_col_name", "expression":"data1_counts + data2_counts"},...]

        automask=True means operations are only applied to places where pixels column is > 0.
        """
        local_namespace = self.get_safe_operations_namespace()
        safe_globals = {"__builtins__":None}
        data_shape = data1.shape
        output_info = data1.infoCopy()
        output_colinfo = []
        self.add_to_namespace(data1, "data1_", local_namespace, automask)
        if data2 is not None:
#            if len(data2.shape) > len(data_shape):
#                data_shape = data2.shape
            self.add_to_namespace(data2, "data2_", local_namespace, automask)
        output_array = zeros(data_shape[:-1] + (len(output_cols) + len(passthrough_cols),), dtype=float)
        for i, o in enumerate(output_cols):
            print(o['expression'], data1.shape, output_array[..., i].shape)
            output_array[..., i] = eval(o['expression'], safe_globals, local_namespace)
            output_colinfo.append({'name':o['name']})

        for i, p in enumerate(passthrough_cols):
            output_array[..., i+len(output_cols)] = data1["Measurements":p]
            output_colinfo.append({'name':p})

        output_info[-2]['cols'] = output_colinfo
        output_obj = MetaArray(output_array, info=output_info)
        return output_obj


class CombinePolcorrect(Filter2D):
    """ combine and polarization-correct """
    def apply(self, list_of_datasets, grid=None):
        pass

def get_index(t, x):
    if (x == "" or x is None):
        return None
    if float(x) > t.max():
        return None
    if float(x) < t.min():
        return None
    return searchsorted(t, float(x))

# rowan tests
if __name__ == '__main__':
    data1 = LoadICPData('Isabc2003.cg1', '/home/brendan/dataflow/sampledata/ANDR/sabc/')
    data2 = LoadICPData('Isabc2004.cg1', '/home/brendan/dataflow/sampledata/ANDR/sabc/')
    data = [data1, data2]
    data = Combine().apply(data)
    data = data.filter('CoordinateOffset', offsets={'theta': 0.1})
    data = data.filter('WiggleCorrection')
    print(data)
    #print(data._info[-1]["CreationStory"])
    #print(eval(data._info[-1]["CreationStory"]))
    #print(data)
    assert data.all() == eval(data._info[-1]["CreationStory"]).all()
