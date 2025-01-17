from functools import wraps

from .FilterableMetaArray import FilterableMetaArray as MetaArray
from .magik_filters import Filter2D, Algebra, updateCreationStory, autoApplyToList

class AsterixPixelsToTwotheta(Filter2D):
    """ input array has pixels axis, convert to
    two-theta based on distance from sample to detector and
    center pixel when two-theta motor is set to zero """

    @autoApplyToList
    @updateCreationStory
    def apply(self, data, qzero_pixel = 145., twotheta_offset=0.0, pw_over_d=0.0003411385649):
        """ pw_over_d is pixel width divided by distance (sample to detector) """
        new_info = data.infoCopy()
        # find pixels axis, and replace with two-theta
        # assuming there are only 2 dimensions of data, looking only at indices 0, 1
        xpixel_axis = next((i for i in range(len(new_info)) if new_info[i]['name'] == 'xpixel'), None)
        if xpixel_axis < 0:
            print("error: no xpixel axis in this dataset")
            return

        new_info[xpixel_axis]['name'] = 'twotheta'
        twotheta_motor = 0.0
        if data._info[-1].has_key('state'):
            twotheta_motor = float(data._info[-1]['state']['A[0]'])
        pixels = data.axisValues('xpixel')
        twotheta = arctan2((pixels - qzero_pixel) * pw_over_d, 1.0) * 180./pi + twotheta_offset + twotheta_motor
        new_info[xpixel_axis]['values'] = twotheta
        new_data = MetaArray(data.view(ndarray).copy(), info=new_info)

        return new_data

class AsterixTOFToWavelength(Filter2D):
    """ input array has TOF axis, convert to wavelength
    based on calibration (depends on distance from source to detector) """

    @autoApplyToList
    @updateCreationStory
    def apply(self, data, wl_over_tof=1.9050372144288577e-5):
        """ wl_over_tof is wavelength divided by time-of-flight """
        new_info = data.infoCopy()
        # find pixels axis, and replace with two-theta
        # assuming there are only 2 dimensions of data, looking only at indices 0, 1
        tof_axis = next((i for i in range(len(new_info)) if new_info[i]['name'] == 'tof'), None)
        if tof_axis < 0:
            print("error: no tof axis in this dataset")
            return

        new_info[tof_axis]['name'] = 'wavelength'
        tof = data.axisValues('tof')
        wavelength = (tof * wl_over_tof)
        # shift by half-bin width to align to center of tof bins!
        wavelength += (tof[1] - tof[0])/2.0 * wl_over_tof
        # (bins appear to be centered)
        new_info[tof_axis]['values'] = wavelength
        new_data = MetaArray(data.view(ndarray).copy(), info=new_info)

        return new_data

class AsterixShiftData(Filter2D):

    @autoApplyToList
    @updateCreationStory
    def apply(self, data, edge_bin = 180, axis=0):
        """ Shift 2D dataset along axis 0, also shifting the axisValues
        along that edge (assuming linear behaviour)
        This is useful for time-of-flight data where the low-t data is empty due
        to spectrum shape, and can be interpreted as the high-t data from the
        previous pulse."""
        #axis = 0
        axis = int(axis)
        if axis > 1:
            axis = 1
        if axis < 0:
            axis = 0
        new_info = data.infoCopy()
        old_axis_values = new_info[axis]['values']
        src_data = data.view(ndarray).copy()

        shifted_data = empty(src_data.shape)

        #start with empty slices over first two axes
        output_slice = [slice(None, None)] * len(src_data.shape)
        input_slice = [slice(None, None)] * len(src_data.shape)

        # move data from edge_bin to end to beginning:
        input_slice[axis] = slice(edge_bin, None)
        output_slice[axis] = slice(None, -edge_bin)
        shifted_data[output_slice] = src_data[input_slice]
        # move data from beginning to edge bin to the end of the new dataset
        input_slice[axis] = slice(None, edge_bin)
        output_slice[axis] = slice(-edge_bin, None)
        shifted_data[output_slice] = src_data[input_slice]

        shifted_axis = zeros(src_data.shape[axis])
        dx = old_axis_values[1] - old_axis_values[0]
        shifted_axis[:-edge_bin] = old_axis_values[edge_bin:]
        shifted_axis[-edge_bin:] = old_axis_values[:edge_bin] + (old_axis_values[-1] - old_axis_values[0]) + dx

        new_info[axis]['values'] = shifted_axis
        new_data = MetaArray(shifted_data, info=new_info)
        return new_data

class AsterixCorrectSpectrum(Filter2D):

    def apply(self, data, spectrum):
        ##polarizations = ["down_down", "down_up", "up_down", "up_up"]
        # inherit polarizations list from Filter2D:
        passthrough_cols = ["counts_%s" % (pol,) for pol in self.polarizations]
        passthrough_cols.extend(["pixels", "count_time"])
        #expressions = [{"name":col, "expression":"data1_%s" % (col,)} for col in passthrough_cols]
        expressions = []
        spectrum_cols = [col['name'] for col in spectrum._info[-2]['cols']]
        for pol in self.polarizations:
            if ("spectrum_%s" % (pol,) in spectrum_cols):
                spec_id = "data2_spectrum_%s" % (pol,)
            else:
                spec_id = "data2_spectrum"
            expressions.append({"name":"monitor_%s" % (pol,), "expression":"data1_monitor_%s * %s[:,newaxis]" % (pol,spec_id)})
        result = Algebra().apply(data, spectrum, expressions, passthrough_cols)
        return result

class TwothetaLambdaToQxQz(Filter2D):
    """ Figures out the Qx, Qz values of each datapoint
    and throws them in the correct bin.  If no grid is specified,
    one is created that covers the whole range of Q in the dataset

    If autofill_gaps is True, does reverse lookup to plug holes
    in the output (but pixel count is still zero for these bins)
    """

    default_qxqz_gridvals = (-0.003, 0.003, 201, 0, 0.1, 201)

    def getQxQz (self, theta, twotheta, wavelength = 5.0):
        qLength = 2.0 * pi / wavelength
        tilt = theta - ( twotheta / 2.0 )
        dq = 2.0 * qLength * sin( ( pi / 180.0 ) * ( twotheta / 2.0 ) )
        qxOut = dq * sin( pi * tilt / 180.0 )
        qzOut = dq * cos( pi * tilt / 180.0 )
        return [qxOut, qzOut]

    @autoApplyToList
    #@updateCreationStory
    def apply(self, data, theta=None, qxmin=None, qxmax=None, qxbins=None, qzmin=None, qzmax=None, qzbins=None):
        info = [{"name": "qx", "units": "inv. Angstroms", "values": linspace(qxmin, qxmax, qxbins) },
                {"name": "qz", "units": "inv. Angstroms", "values": linspace(qzmin, qzmax, qzbins) },]
        old_info = data.infoCopy()
        info.append(old_info[2]) # column information!
        info.append(old_info[3]) # creation story!
        output_grid = MetaArray(zeros((qxbins, qzbins, data.shape[-1])), info=info)


        #if output_grid == None:
        #    output_grid = EmptyQxQzGrid(*self.default_qxqz_gridvals)
        #else:
        #    output_grid = deepcopy(output_grid)

        if (theta == "") or (theta == None):
            if 'state' in data._info[-1]:
                theta = float(data._info[-1]['state']['A[1]'])
                print('theta:', theta)
            else:
                print("can't run without theta!")
                return

        wl_array = data.axisValues('wavelength').copy()
        wl_array.shape = wl_array.shape + (1,)
        twotheta_array = data.axisValues('twotheta').copy()
        twotheta_array.shape = (1,) + twotheta_array.shape
        qxOut, qzOut = self.getQxQz(theta, twotheta_array, wl_array)

        # getting values from output grid:
        outgrid_info = output_grid.infoCopy()
        numcols = len(outgrid_info[2]['cols'])
        qx_array = output_grid.axisValues('qx')
        dqx = qx_array[1] - qx_array[0]
        qz_array = output_grid.axisValues('qz')
        dqz = qz_array[1] - qz_array[0]
        framed_array = zeros((qz_array.shape[0]+2, qx_array.shape[0]+2, numcols))
        target_qx = ((qxOut - qx_array[0])/dqx + 1).astype(int)
        #return target_qx, qxOut
        target_qz = ((qzOut - qz_array[0])/dqz + 1).astype(int)
        target_mask = (target_qx >= 0) * (target_qx < qx_array.shape[0])
        target_mask *= (target_qz >= 0) * (target_qz < qz_array.shape[0])
        target_qx_list = target_qx[target_mask]
        target_qz_list = target_qz[target_mask]
        #target_qx = target_qx.clip(0, qx_array.shape[0]+1)
        #target_qz = target_qz.clip(0, qz_array.shape[0]+1)

        for i, col in enumerate(outgrid_info[2]['cols']):
            values_to_bin = data[:,:,col['name']][target_mask]
            outshape = (output_grid.shape[0], output_grid.shape[1])
            hist2d, xedges, yedges = histogram2d(target_qx_list,target_qz_list, bins = (outshape[0],outshape[1]), range=((0,outshape[0]),(0,outshape[1])), weights=values_to_bin)
            output_grid[:,:,col['name']] += hist2d
            #framed_array[target_qz_list, target_qx_list, i] = data[:,:,col['name']][target_mask]

        #trimmed_array = framed_array[1:-1, 1:-1]
        #output_grid[:,:] = trimmed_array

        creation_story = data._info[-1]['CreationStory']
        new_creation_story = creation_story + ".filter('{0}', {1})".format(self.__class__.__name__, output_grid._info[-1]['CreationStory'])
        #print(new_creation_story)
        output_grid._info[-1] = data._info[-1].copy()
        output_grid._info[-1]['CreationStory'] = new_creation_story
        return output_grid
