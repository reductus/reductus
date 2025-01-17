import os, sys, types
from copy import deepcopy
from posixpath import basename, join
import time
from io import BytesIO
from typing import List

import pytz
from numpy import (cos, pi, cumsum, arange, ndarray, ones, zeros, array,
                   newaxis, linspace, empty, resize, sin, allclose, zeros_like,
                   linalg, dot, arctan2, float64, histogram2d, sum, nansum,
                   sqrt, loadtxt, searchsorted, nan, logical_not, fliplr,
                   flipud, indices, polyfit, radians, argsort)

from numpy.ma import MaskedArray

from reductus.dataflow.lib.h5_open import h5_open_zip

from reductus.dataflow.core import Template
from reductus.dataflow.calc import process_template
from reductus.dataflow.fetch import url_get
from reductus.dataflow.lib import rebin as reb
from reductus.dataflow.lib.iso8601 import seconds_since_epoch

from reductus.dataflow.automod import cache, nocache, module

from .FilterableMetaArray import FilterableMetaArray as MetaArray

DEBUG = False

def get_index(t, x):
        if (x == "" or x == None):
            return None
        if float(x) > t.max():
            return None
        if float(x) < t.min():
            return None
        tord = argsort(t)
        return tord[searchsorted(t, float(x), sorter=tord)]

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
    from .dataflow import Parameters
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
    output_array = zeros( data.shape[:-1] + (len(counts_cols) + len(passthrough_cols),), dtype=float) * nan
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
        #print(mask)
        output_array[..., j][mask] = data["Measurements":col][mask] / data["Measurements":monitor_id][mask]
        #expression = "data1_counts%s / data1_%s" % (col_suffix, monitor_id)
        #error_expression = "sqrt(data1_counts%s) / data1_%s" % (col_suffix, monitor_id)
        #expressions.append({"name": "counts_norm%s" % (col_suffix,), "expression":expression})
        #expressions.append({"name": "error_counts_norm%s" % (col_suffix,), "expression":error_expression})
    #result = Algebra().apply(data, None, expressions, passthrough_cols)
    result = MetaArray(output_array, info=info)
    return result

@module
def cropData(data, cropbox=[None,None,None,None]):
    """
    crop 2d data along both axes and return smaller dataset

    **Inputs**

    data (ospec2d) : data in

    cropbox (range?:xy): region over which to mask (in data coordinates)

    **Returns**

    output (ospec2d) : data with normalization applied

    2018-04-10 Brian Maranville
    """
    if cropbox is None:
        cropbox = [None, None, None, None]
    xmin, xmax, ymin, ymax = cropbox
    new_info = data.infoCopy()
    x_axis = new_info[0]
    y_axis = new_info[1]
    col_info = new_info[2]
    extra_info = new_info[3]

    x_array = data._info[0]['values']
    y_array = data._info[1]['values']

    xslice = slice(get_index(x_array, xmin), get_index(x_array, xmax))
    yslice = slice(get_index(y_array, ymin), get_index(y_array, ymax))
    dataslice = (xslice, yslice)
    output_array = data.view(ndarray)[dataslice]
    new_info[0]['values'] = x_array[xslice]
    new_info[1]['values'] = y_array[yslice]
    result = MetaArray(output_array, info=new_info)
    return result

@module
def maskData(data, maskbox=[None,None,None,None], invert=False):
    """
    Set all data, normalization to zero within mask

    **Inputs**

    data (ospec2d) : data in
    
    maskbox (range?:xy): region over which to mask (in data coordinates)
    
    invert (bool): if True, mask everything not in the box

    **Returns**

    masked (ospec2d) : data out, with mask applied

    2018-04-01 Brian Maranville
    """
    
    if maskbox is None:
        maskbox = [None, None, None, None]
    xmin, xmax, ymin, ymax = maskbox
    new_info = data.infoCopy()
    x_axis = new_info[0]
    y_axis = new_info[1]
    col_info = new_info[2]
    extra_info = new_info[3]

    x_array = data._info[0]['values']
    y_array = data._info[1]['values']

    xslice = slice(get_index(x_array, xmin), get_index(x_array, xmax))
    yslice = slice(get_index(y_array, ymin), get_index(y_array, ymax))
    dataslice = (xslice, yslice)
    if invert:
        new_data = MetaArray(zeros_like(data.view(ndarray)), info=data.infoCopy())
        new_data.view(ndarray)[dataslice] = data.view(ndarray).copy()[dataslice]
    else:
        new_data = MetaArray(data.view(ndarray).copy(), info=data.infoCopy())
        new_data.view(ndarray)[dataslice] = 0

    return new_data

@module
def sliceData(data, slicebox=[None,None,None,None]):
    """
    Sum 2d data along both axes and return 1d datasets

    **Inputs**

    data (ospec2d) : data in
    
    slicebox (range?:xy): region over which to integrate (in data coordinates)

    **Returns**

    xout (ospecnd) : xslice

    yout (ospecnd) : yslice

    2016-04-01 Brian Maranville
    """
    
    if slicebox is None:
        slicebox = [None, None, None, None]
    xmin, xmax, ymin, ymax = slicebox
    new_info = data.infoCopy()
    x_axis = new_info[0]
    y_axis = new_info[1]
    col_info = new_info[2]
    extra_info = new_info[3]

    x_array = data._info[0]['values']
    y_array = data._info[1]['values']

    xslice = slice(get_index(x_array, xmin), get_index(x_array, xmax))
    yslice = slice(get_index(y_array, ymin), get_index(y_array, ymax))
    dataslice = (xslice, yslice)
    # print xmin, xmax, ymin, ymax
    x_out = nansum(data.view(ndarray)[dataslice], axis=1)
    y_out = nansum(data.view(ndarray)[dataslice], axis=0)
    x_axis['values'] = x_axis['values'][xslice]
    y_axis['values'] = y_axis['values'][yslice]

    x_data_obj = MetaArray( x_out, info=[x_axis, col_info, extra_info] )
    y_data_obj = MetaArray( y_out, info=[y_axis, col_info, extra_info] )

    return x_data_obj, y_data_obj

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

    if params is not None:
        if 'pixels_per_degree' in params: pixels_per_degree = params['pixels_per_degree']
        if 'qzero_pixel' in params: qzero_pixel = params['qzero_pixel']
    #kw = locals().keys()
    #print(kw, params)
    #for name in kw:
    #    if name in params:
    #        exec "print('%s', %s, params['%s']" % (name, name,name)) in locals()
    #        exec ("%s = params['%s']" % (name, name)) in locals()
    #        exec "print(name)" in locals()

    pixels_per_degree = float(pixels_per_degree) # coerce, in case it was an integer
    qzero_pixel = float(qzero_pixel)
    instr_resolution = float(instr_resolution)

    print(pixels_per_degree, qzero_pixel)

    new_info = data.infoCopy()
    det_angle = new_info[-1].get('det_angle', None)
    det_angle = array(det_angle)
    # det_angle should be a vector of the same length as the other axis (usually theta)
    # or else just a float, in which case the detector is not moving!
    ndim = len(new_info) - 2 # last two entries in info are for metadata
    pixel_axis = next((i for i in range(len(new_info)-2) if new_info[i]['name'] == ax_name), None)
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
                array_to_rebin = data_in[tuple(input_slice)]
                new_array = reb.rebin(input_twoth_bin_edges, array_to_rebin, output_twoth_bin_edges)
                new_data.view(ndarray)[tuple(input_slice)] = new_array

    return new_data

@module
def thetaTwothetaToQxQz(data, output_grid, wavelength=5.0, qxmin=-0.003, qxmax=0.003, qxbins=101, qzmin=0.0001, qzmax=0.1, qzbins=101):
    """ Figures out the Qx, Qz values of each datapoint
    and throws them in the correct bin.  If no grid is specified,
    one is created that covers the whole range of Q in the dataset

    If autofill_gaps is True, does reverse lookup to plug holes
    in the output (but pixel count is still zero for these bins)

    **Inputs**

    data (ospec2d): input data

    output_grid (ospec2d?): empty data object with axes defined (optional)

    wavelength (float): override wavelength in data file

    qxmin (float): lower bound of Qx range in rebinning

    qxmax (float): upper bound of Qx range in rebinning

    qxbins (int): number of bins to subdivide the range between qxmin and qxmax

    qzmin (float): lower bound of Qz range in rebinning

    qzmax (float): upper bound of Qz range in rebinning

    qzbins (int): number of bins to subdivide the range between qzmin and qzmax

    **Returns**

    output (ospec2d): output data rebinned into Qx, Qz

    2016-04-01 Brian Maranville
    """
    print("output grid: ", output_grid)
    if output_grid is None:
        info = [{"name": "qx", "units": "inv. Angstroms", "values": linspace(qxmin, qxmax, qxbins) },
            {"name": "qz", "units": "inv. Angstroms", "values": linspace(qzmin, qzmax, qzbins) },]
        old_info = data.infoCopy()
        info.append(old_info[2]) # column information!
        info.append(old_info[3]) # creation story!
        output_grid = MetaArray(zeros((qxbins, qzbins, data.shape[-1])), info=info)
    else:
        outgrid_info = deepcopy(output_grid._info) # take axes and creation story from emptyqxqz...
        outgrid_info[2] = deepcopy(data._info[2]) # take column number and names from dataset
        output_grid = MetaArray(zeros((output_grid.shape[0], output_grid.shape[1], data.shape[2])), info=outgrid_info)

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
    qxOut = 2.0 * qLength * sin((pi / 180.0) * (twotheta_array / 2.0)) * sin(pi * tilt_array / 180.0)
    qzOut = 2.0 * qLength * sin((pi / 180.0) * (twotheta_array / 2.0)) * cos(pi * tilt_array / 180.0)

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
        values_to_bin = data[:,:,col['name']].view(ndarray)[target_mask]
        outshape = (output_grid.shape[0], output_grid.shape[1])
        hist2d, xedges, yedges = histogram2d(target_qx_list,target_qz_list, \
            bins = (outshape[0],outshape[1]), range=((0,outshape[0]),(0,outshape[1])), weights=values_to_bin)
        output_grid[:,:,col['name']] += hist2d
        #framed_array[target_qz_list, target_qx_list, i] = data[:,:,col['name']][target_mask]

    cols = outgrid_info[2]['cols']
    data_cols = [col['name'] for col in cols if col['name'].startswith('counts')]
    monitor_cols = [col['name'] for col in cols if col['name'].startswith('monitor')]
    # just take the first one...
    if len(monitor_cols) > 0:
        monitor_col = monitor_cols[0]
        data_missing_mask = (output_grid[:,:,monitor_col] == 0)
        for dc in data_cols:
            output_grid[:,:,dc].view(ndarray)[data_missing_mask] = nan;

    #extra_info
    output_grid._info[-1] = data._info[-1].copy()
    print("output shape:", output_grid.shape)
    return output_grid

@module
def thetaTwothetaToAlphaIAlphaF(data):
    """ Figures out the angle in, angle out values of each datapoint
    and throws them in the correct bin.  If no grid is specified,
    one is created that covers the whole range of the dataset

    **Inputs**

    data (ospec2d): input data

    **Returns**

    output (ospec2d): output data rebinned into alpha_i, alpha_f

    2016-04-01 Brian Maranville
    """

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

    info = [{"name": "alpha_i", "units": "degrees", "values": th_array.copy() },
            {"name": "alpha_f", "units": "degrees", "values": alpha_f.copy() },]
    old_info = data.infoCopy()
    info.append(old_info[2]) # column information!
    info.append(old_info[3]) # creation story!
    output_grid = MetaArray(zeros((th_array.shape[0], alpha_f.shape[0], data.shape[-1])), info=info)

    if theta_axis < twotheta_axis: # then theta is first: add a dimension at the end
        alpha_i.shape = alpha_i.shape + (1,)
        ai_out = indices((th_array.shape[0], twotheta_array.shape[0]))[0]
        twotheta_array.shape = (1,) + twotheta_array.shape
    else:
        alpha_i.shape = (1,) + alpha_i.shape
        ai_out = indices((twotheta_array.shape[0], th_array.shape[0]))[1]
        twotheta_array.shape = twotheta_array.shape + (1,)

    af_out = twotheta_array - alpha_i

    # getting values from output grid:
    outgrid_info = output_grid.infoCopy()
    numcols = len(outgrid_info[2]['cols'])
    #target_ai = ((ai_out - th_array[0]) / theta_step).flatten().astype(int).tolist()
    target_ai = ai_out.flatten().astype(int).tolist()
    #return target_qx, qxOut
    target_af = ((af_out - af_min) / two_theta_step).flatten().astype(int).tolist()

    for i, col in enumerate(outgrid_info[2]['cols']):
        values_to_bin = data[:,:,col['name']].view(ndarray).flatten().tolist()
        print(len(target_ai), len(target_af), len(values_to_bin))
        outshape = (output_grid.shape[0], output_grid.shape[1])
        hist2d, xedges, yedges = histogram2d(target_ai, target_af, bins = (outshape[0],outshape[1]), range=((0,outshape[0]),(0,outshape[1])), weights=values_to_bin)
        output_grid[:,:,col['name']] += hist2d

    cols = outgrid_info[2]['cols']
    data_cols = [col['name'] for col in cols if col['name'].startswith('counts')]
    monitor_cols = [col['name'] for col in cols if col['name'].startswith('monitor')]
    # just take the first one...
    if len(monitor_cols) > 0:
        monitor_col = monitor_cols[0]
        data_missing_mask = (output_grid[:,:,monitor_col] == 0)
        for dc in data_cols:
            output_grid[:,:,dc].view(ndarray)[data_missing_mask] = nan

    #extra info changed
    output_grid._info[-1] = data._info[-1].copy()
    return output_grid

@module
def alphaFtoQz(data, wavelength=5.0):
    """ Figures out the Qz values of each datapoint
    and throws them in the correct bin.

    **Inputs**

    data (ospec2d): input data

    wavelength (float): override wavelength in data file

    **Returns**

    qzdata (ospec2d) : output data rebinned into Qz

    2016-04-03 Brian Maranville
    """

    new_info = data.infoCopy()
    # det_angle should be a vector of the same length as the other axis (usually theta)
    # or else just a float, in which case the detector is not moving!
    ndim = len(new_info) - 2 # last two entries in info are for metadata
    ax_name = "alpha_f"
    af_axis = next((i for i in range(len(new_info)-2) if new_info[i]['name'] == ax_name), None)
    if af_axis < 0:
        raise ValueError("error: no %s axis in this dataset" % (ax_name,))

    new_info[af_axis]['name'] = 'Qz'
    af = new_info[af_axis]['values']
    qz = 4.0*pi/wavelength * sin(radians(af))
    new_info[af_axis]['values'] = qz
    new_info[af_axis]['units'] = 'inv. Angstroms'
    new_array = (data.view(ndarray).copy())
    new_data = MetaArray(new_array, info=new_info)
    return new_data

@module
def autogrid(datasets, operation='union', extra_grid_point=True, min_step=1e-10):
    """
    take multiple datasets and create a grid which covers all of them
    - stepsize is smallest stepsize found in datasets
    returns an empty grid with units and labels

    if extra_grid_point is True, adds one point to the end of each axis
    so each dimension is incremented by one (makes edges for rebinning)

    **Inputs**

    datasets (ospec2d[]): input data

    operation (opt:union|intersection): make grid to cover all points (union) or only where overlapped (intersection)

    extra_grid_point (bool): if extra_grid_point is True, adds one point to the end of each axis so each dimension is incremented by one (makes edges for rebinning)

    min_step (float): smallest difference that is not rounded to zero

    **Returns**

    grid (ospec2d): output grid

    2017-05-01 Brian Maranville
    """

    num_datasets = len(datasets)
    dims = 2
    dim_min = zeros((dims, num_datasets))
    dim_max = zeros((dims, num_datasets))
    dim_len = zeros((dims, num_datasets))
    dim_step = zeros((dims, num_datasets))

    for i, data in enumerate(datasets):
        info = data.infoCopy()
        for dim in range(dims):
            av = data.axisValues(dim)
            dim_min[dim, i] = av.min()
            dim_max[dim, i] = av.max()
            dim_len[dim, i] = len(av)
            if dim_len[dim, i] > 1:
                dim_step[dim, i] = float(dim_max[dim, i] - dim_min[dim, i]) / (dim_len[dim, i] - 1)
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
            steps = int(round(float(absolute_max[dim] - absolute_min[dim]) / final_stepsizes[dim]))
        if extra_grid_point == True:
            steps += 1
        output_dims.append(steps)

    new_info = datasets[0].infoCopy() # take units etc from first dataset
     # then tack on the number of columns already there:
    output_dims.append(len(new_info[2]['cols']))
    for dim in range(dims):
        new_info[dim]["values"] = (arange(output_dims[dim], dtype='float') * final_stepsizes[dim]) + absolute_min[dim]
    output_grid = MetaArray(zeros(tuple(output_dims)), info=new_info)
    return output_grid


@module
def combine(datasets, grid, operation="union"):
    """
    Combine multiple datasets with or without overlap, adding
    all the values in the time, monitor and data columns, and populating
    the pixels column (number of pixels in each new bin)

    **Inputs**

    datasets (ospec2d[]): input data

    grid (ospec2d?): optional grid

    operation (opt:union|intersection): make grid to cover all points (union) or only where overlapped (intersection) for autogridding

    **Returns**

    combined (ospec2d) : datasets added together

    2017-05-01 Brian Maranville
    """

    if grid is None:
        grid = autogrid(datasets, operation=operation)
    for dataset in datasets:
        grid = add_to_grid(dataset, grid)
    # extra info changed
    # strip info that is meaningless in combined dataset: (filename, start_time, end_time)
    for key in ['filename', 'start_datetime', 'end_datetime']:
        if key in grid._info[-1]: grid._info[-1].pop(key)
    return grid

def subtract(minuend, subtrahend):
    """ 
    Takes two data objects and subtracts them.
    If no grid is provided, use Autogrid filter to generate one.

    **Inputs**

    minuend (ospec2d): input data

    subtrahend (ospec2d): 

    grid (ospec2d?): optional grid

    operation (opt:union|intersection): make grid to cover all points (union) or only where overlapped (intersection) for autogridding

    **Returns**

    combined (ospec2d) : datasets added together
    """
    #subtrahend = subtrahend[0] # can only subtract one thing... but from many.
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


def add_to_grid(dataset, grid, counts_multiplier=1.0):
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

    data_slice = tuple(data_slice)
    grid_slice = tuple(grid_slice)
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

#################
# Loader stuff
#################
DETECTOR_ACTIVE = (320, 340)

@module
def LoadMAGIKPSDMany(fileinfo=None, collapse=True, collapse_axis='y', auto_PolState=False, PolState='', flip=True, transpose=True):
    """
    loads a data file into a MetaArray and returns that.
    Checks to see if data being loaded is 2D; if not, quits

    Need to rebin and regrid if the detector is moving...

    **Inputs**

    fileinfo (fileinfo[]): Files to open.

    collapse {Collapse along one of the axes} (bool): sum over axis of detector

    collapse_axis {number index of axis to collapse along} (opt:x|y): axis to sum over

    auto_PolState {Automatic polarization identify} (bool): automatically determine the polarization state from entry name

    PolState (str): polarization state if not automatically detected

    flip (bool): flip the data up and down

    transpose (bool): transpose the data

    **Returns**

    output (ospec2d[]): all the entries loaded.

    2016-04-04 Brian Maranville
    """
    outputs = []
    kwconfig = {
        "collapse": collapse,
        "collapse_axis": collapse_axis,
        "auto_PolState": auto_PolState,
        "PolState": PolState,
        "flip": flip,
        "transpose": transpose
    }
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
        config["0"].update(kwconfig)
        nodenum = 0
        terminal_id = "output"

        retval = process_template(template, config, target=(nodenum, terminal_id))
        outputs.extend(retval.values)
    return outputs

@cache
@module
def LoadMAGIKPSD(fileinfo=None, collapse=True, collapse_axis='y', auto_PolState=False, PolState='', flip=True, transpose=True):
    """
    loads a data file into a MetaArray and returns that.
    Checks to see if data being loaded is 2D; if not, quits

    Need to rebin and regrid if the detector is moving...

    **Inputs**

    fileinfo (fileinfo): File to open.

    collapse {Collapse along one of the axes} (bool): sum over axis of detector

    collapse_axis {number index of axis to collapse along} (opt:x|y): axis to sum over

    auto_PolState {Automatic polarization identify} (bool): automatically determine the polarization state from entry name

    PolState (str): polarization state if not automatically detected

    flip (bool): flip the data up and down

    transpose (bool): transpose the data

    **Returns**

    output (ospec2d[]): all the entries loaded.

    2016-04-04 Brian Maranville
    """

    path, mtime, entries = fileinfo['path'], fileinfo['mtime'], fileinfo['entries']
    name = basename(path)
    fid = BytesIO(url_get(fileinfo))
    file_obj = h5_open_zip(name, fid)
    return loadMAGIKPSD_helper(file_obj, name, path, collapse=collapse, collapse_axis=collapse_axis, auto_PolState=auto_PolState, PolState=PolState, flip=flip, transpose=transpose)

def LoadMAGIKPSDFile(path, **kw):
    return loadMAGIKPSD_helper(h5_open_zip(path), path, path, **kw)

def loadMAGIKPSD_helper(file_obj, name, path, collapse=True, collapse_axis='y', auto_PolState=False, PolState='', flip=True, transpose=True) -> List[MetaArray]:
    lookup = {"DOWN_DOWN":"_down_down", "UP_DOWN":"_up_down", "DOWN_UP":"_down_up", "UP_UP":"_up_up", "entry": ""}
    #nx_entries = LoadMAGIKPSD.load_entries(name, fid, entries=entries)
    #fid.close()

    #if not (len(file_obj.detector.counts.shape) == 2):
        # not a 2D object!
    #    return
    for entryname, entry in file_obj.items():
        active_slice = slice(None, DETECTOR_ACTIVE[0], DETECTOR_ACTIVE[1])
        counts_value = entry['DAS_logs/areaDetector/counts'][:, 1:DETECTOR_ACTIVE[0]+1, :DETECTOR_ACTIVE[1]]
        dims = counts_value.shape
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


        # doesn't really matter; changing so that each keyword (whether it took the default value
        # provided or not) will be defined
        #    if not PolState == '':
        #        creation_story += ", PolState='{0}'".format(PolState)
        # creation_story += ")"


        if ndims == 2: # one of the dimensions has been collapsed.
            info = []
            info.append({"name": "xpixel", "units": "pixels", "values": arange(xpixels) }) # reverse order
            samp_angle = entry['DAS_logs/sampleAngle/softPosition'][()]
            det_angle = entry['DAS_logs/detectorAngle/softPosition'][()]
            if samp_angle.size > 1:
                yaxis = entry['DAS_logs/sampleAngle/softPosition']
                yaxisname = "theta"
            elif det_angle.size > 1:
                yaxis = entry['DAS_logs/detectorAngle/softPosition']
                yaxisname = "det_angle"
            else:
                # need to find the one that's moving...
                yaxis = entry['data/x']
                yaxisname = yaxis.path
            yaxisunits = yaxis.attrs['units']
            yaxisvalues = yaxis[()]
            info.append({"name": yaxisname, "units": yaxisunits, "values": yaxisvalues})
            info.extend([
                    {"name": "Measurements", "cols": [
                            {"name": "counts"},
                            {"name": "pixels"},
                            {"name": "monitor"},
                            {"name": "count_time"}]},
                    {"PolState": PolState, "filename": name, "start_datetime": entry['start_time'][0], "friendly_name": entry['DAS_logs/sample/name'][0],
                     "entry": entryname, "path":path, "det_angle":entry['DAS_logs/detectorAngle/softPosition'][()],
                     "theta": entry['DAS_logs/sampleAngle/softPosition'][()]}]
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
            data.friendly_name = name # goes away on dumps/loads... just for initial object.
            ouput = [data]

        elif ndims == 3: # then it's an unsummed collection of detector shots.  Should be one sample and detector angle per frame
            if collapse == True:
                info = []
                xaxis = "xpixel" if collapse_axis == 'y' else "ypixel"
                xdim = xpixels if collapse_axis == 'y' else ypixels
                xaxisvalues = arange(xdim)
                info.append({"name": xaxis, "units": "pixels", "values": xaxisvalues }) # reverse order
                samp_angle = entry['DAS_logs/sampleAngle/softPosition'][()]
                det_angle = entry['DAS_logs/detectorAngle/softPosition'][()]
                if samp_angle.size > 1:
                    yaxis = entry['DAS_logs/sampleAngle/softPosition']
                    yaxisname = "theta"
                elif det_angle.size > 1:
                    yaxis = entry['DAS_logs/detectorAngle/softPosition']
                    yaxisname = "det_angle"
                else:
                    # need to find the one that's moving...
                    yaxis = entry['data/x']
                    yaxisname = yaxis.path
                yaxisunits = yaxis.attrs['units']
                yaxisvalues = yaxis[()]
                info.append({"name": yaxisname, "units": yaxisunits, "values": yaxisvalues})
                info.extend([
                        {"name": "Measurements", "cols": [
                                {"name": "counts"},
                                {"name": "pixels"},
                                {"name": "monitor"},
                                {"name": "count_time"}]},
                        {"PolState": PolState, "start_datetime": entry['start_time'][0], "path":path,
                         "det_angle": det_angle.tolist(),
                         "theta": samp_angle.tolist(),
                         "filename": name,
                         "friendly_name": entry['DAS_logs/sample/name'][0], "entry": entryname}]
                    )
                data_array = zeros((xdim, frames, 4))
                mon =  entry['DAS_logs']['counter']['liveMonitor'][()]
                count_time = entry['DAS_logs']['counter']['liveTime'][()]
                if ndims == 3:
                    mon.shape = (1,) + mon.shape # broadcast the monitor over the other dimension
                    count_time.shape = (1,) + count_time.shape
                axis_to_sum = 2 if collapse_axis == 'y' else 1
                counts = sum(counts_value, axis=axis_to_sum)
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
                output = [data]
            else: # make separate frames
                infos = []
                data = []
                samp_angle =  entry['DAS_logs/sampleAngle/softPosition'][()].astype('float')
                if samp_angle.shape[0] == 1:
                    samp_angle = ones((frames,)) * samp_angle
                det_angle = entry['DAS_logs/detectorAngle/softPosition'][()].astype('float')
                if det_angle.shape[0] == 1:
                    det_angle = ones((frames,)) * det_angle
                count_time = entry['DAS_logs/counter/liveTime'][()]
                if count_time.shape[0] == 1:
                    count_time = ones((frames,)) * count_time
                mon =  entry['DAS_logs/counter/liveMonitor'][()]
                if mon.shape[0] == 1:
                    mon = ones((frames,)) * mon
                for i in range(frames):
                    info = []
                    info.append({"name": "xpixel", "units": "pixels", "values": list(range(xpixels)) })
                    info.append({"name": "ypixel", "units": "pixels", "values": list(range(ypixels)) })
                    info.extend([
                        {"name": "Measurements", "cols": [
                                {"name": "counts"},
                                {"name": "pixels"},
                                {"name": "monitor"},
                                {"name": "count_time"}]},
                        {"PolState": PolState, "filename": name, "start_datetime": entry['start_time'][0], "friendly_name": entry['DAS_logs/sample/name'][0],
                         "entry": entryname, "path":path, "samp_angle": samp_angle[i], "det_angle": det_angle[i]}]
                    )
                    data_array = zeros((xpixels, ypixels, 4))
                    counts = counts_value[i]
                    if flip == True: counts = flipud(counts)
                    data_array[..., 0] = counts
                    data_array[..., 1] = 1
                    data_array[..., 2] = mon[i]
                    data_array[..., 3] = count_time[i]
                    # data_array[:,:,4]... I wish!!!  Have to do by hand.
                    subdata = MetaArray(data_array, dtype='float', info=info)
                    subdata.friendly_name = name + ("_%d" % i) # goes away on dumps/loads... just for initial object.
                    data.append(subdata)
                    output = data
    return output

def demo():
    from reductus.dataflow import fetch
    fetch.DATA_SOURCES = [{"name": "ncnr", "url": "https://ncnr.nist.gov/pub/"}]
    fileinfo = {
        'mtime': 1457795231.0,
        'path': 'ncnrdata/cgd/201603/21237/data/wp10v132.nxz.cgd',
        'source': 'ncnr',
        'entries': ['entry']
    }
    return LoadMAGIKPSD(fileinfo)

def test():
    loaded_files = demo()
    assert len(loaded_files) == 1
    loaded_file = loaded_files[0]
    assert loaded_file.get_metadata()['filename'] == 'wp10v132.nxz.cgd'