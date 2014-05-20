from MetaArray import MetaArray
from numpy import ndarray, amin, amax, alen, array, fromstring, float, float64, float32, ones, empty, newaxis, savetxt, sqrt, mod
import copy, simplejson, datetime
#from ...dataflow.core import Data
from cStringIO import StringIO

class FilterableMetaArray(MetaArray):
    def __new__(*args, **kwargs):
        subarr = MetaArray.__new__(*args, **kwargs)
        subarr.extrainfo = subarr._info[-1]
        return subarr
    
    def filter(self, filtername, *args, **kwargs):
        import filters
        return filters.__getattribute__(filtername)().apply(self, *args, **kwargs)

    
    def __deepcopy__(self, memo):
        return FilterableMetaArray(self.view(ndarray).copy(), info=self.infoCopy())

    def dumps(self):
        meta = { 'shape': self.shape, 'type': str(self.dtype), 'info': self.infoCopy()}
        assert isinstance(meta['info'], list)
        axstrs = []
        for ax in meta['info']:
            if ax.has_key('values'):
                axstrs.append(ax['values'].tostring())
                ax['values_len'] = len(axstrs[-1])
                ax['values_type'] = str(ax['values'].dtype)
                del ax['values']
        fd = StringIO()
        fd.write(str(meta) + '\n\n')
        for ax in axstrs:
            fd.write(ax)
        fd.write(self.tostring())
        ans = fd.getvalue()
        fd.close()
        return ans
    
    def get_extrema(self):
        extrema = {}
        for ax in self._info:
            if ax.has_key('values'):
                values = array(ax['values'])
                extrema[ax['name']] = [values.min(), values.max()]
        return extrema
    
    @classmethod
    def loads(cls, str):
        fd = StringIO(str)
        meta = ''
        while True:
            line = fd.readline().strip()
            if line == '':
                break
            meta += line
        meta = eval(meta)
        
        ## read in axis values
        for ax in meta['info']:
            if ax.has_key('values_len'):
                ax['values'] = fromstring(fd.read(ax['values_len']), dtype=ax['values_type'])
                del ax['values_len']
                del ax['values_type']
        
        subarr = fromstring(fd.read(), dtype=meta['type'])
        subarr = subarr.view(FilterableMetaArray)
        subarr.shape = meta['shape']
        subarr._info = meta['info']
        return subarr

    def use_binary(self):
        if len(self.shape) == 3:
            return True
        elif len(self.shape) == 2:
            return False
        else:
            return False

    def get_plottable(self, binary_fp=None):
        if len(self.shape) == 3:
            return self.get_plottable_2d(binary_fp)
        elif len(self.shape) == 2:
            return self.get_plottable_nd()
        else:
            print "can only handle 1d or 2d data"
            return 
            
    def get_plottable_1d(self, binary_fp=None):
        colors = ['Blue', 'Red', 'Green', 'Yellow']
        cols = self._info[1]['cols']
        data_cols = [col['name'] for col in cols if not col['name'].startswith('error')]
        print data_cols
        x = self._info[0]['values'].tolist()
        xlabel = self._info[0]['name']
        title = self._info[-1].get('friendly_name', "1d data")
        plottable_data = {
            'type': '1d',
            'title': title,
            'options': {'series': []},
            'clear_existing': False,
            'data': []
        }
        
        for i, col in enumerate(data_cols):
            y = self['Measurements':col].tolist()
            #error_col = next((i for i in xrange(len(cols)) if cols[i]['name'] == ('error_'+col)), -1)
            #if error_col > 0:
            #    yerror = self['Measurements':'error_'+col].tolist()
            #else:
            #    yerror = sqrt(abs(self['Measurements':col])).tolist()
            series_data = [[xx,yy] for xx, yy in zip(x,y)]
            plottable_data['data'].append(series_data)
            plottable_data['options']['series'].append({'label': col})
            
        return simplejson.dumps(plottable_data,sort_keys=True, indent=2)
        
    def get_plottable_nd(self, binary_fp=None):
        colors = ['Blue', 'Red', 'Green', 'Yellow']
        cols = self._info[1]['cols']
        data_cols = [col['name'] for col in cols if not col['name'].startswith('error')]
        print data_cols
        x = self._info[0]['values'].tolist()
        xlabel = self._info[0]['name']
        plottable_data = {
            'type': 'nd',
            'title': '1d summed Data',

            'clear_existing': False,
            'orderx': [{'key': xlabel, 'label': xlabel }],
            'ordery': [],
            'series': [ {'label': self._info[-1].get('friendly_name', '1d data'),
                        'color': 'Red',
                        'style': 'line',
                        'data': { xlabel: {
                                    'values': x,
                                    'errors': [0,] * len(x),
                                     },
                                },
                         },],
        }
        
        for i, col in enumerate(data_cols):
            y = self['Measurements':col].tolist()
            error_col = next((i for i in xrange(len(cols)) if cols[i]['name'] == ('error_'+col)), -1)
            if error_col > 0:
                yerror = self['Measurements':'error_'+col].tolist()
            else:
                yerror = sqrt(abs(self['Measurements':col])).tolist()
            ordery = {'key': col, 'label': col}
            series_y = {
                'values': y,
                'errors': yerror,
            }
            plottable_data['ordery'].append(ordery)
            plottable_data['series'][0]['data'][col] = series_y
            
        return simplejson.dumps(plottable_data,sort_keys=True, indent=2)
            
    def get_plottable_2d(self, binary_fp=None):
        # grab the first counts col:
        cols = self._info[2]['cols']
        data_cols = [col['name'] for col in cols if col['name'].startswith('counts')]
        
        result = []
        for colnum, col in enumerate(data_cols):      
            array_out = self['Measurements':col].view(ndarray)
            
            dump = {}
            if binary_fp is not None:
                # use lookup to get binary value
                z = [[0,0]]
                dump['binary_fp'] = binary_fp + ":" + str(colnum)
            else: # use the old way
                z = [array_out.T.tolist()]
                
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
            axis = ['x', 'y']
            for index, label in enumerate(axis):
                arr = self._info[index]['values']
                dims[axis[index] + 'min'] = float(arr.min())
                dims[axis[index] + 'max'] = float(arr.max())
                dims[axis[index] + 'dim'] = len(arr)
            xlabel = self._info[0]['name']
            ylabel = self._info[1]['name']
            zlabel = col
            #zlabel = self._info[2]['cols'][0]['name']
            title = 'AND/R data' # That's creative enough, right?
            plot_type = '2d'
            transform = 'lin' # this is nice by default
            dump.update( dict(type=plot_type, z=z, title=title, dims=dims, 
                        xlabel=xlabel, ylabel=ylabel, zlabel=zlabel, 
                        transform=transform) )
            result.append(simplejson.dumps(dump, sort_keys=True))
        return ",".join(result)
    
    def get_plottable_binary(self):
        cols = self._info[2]['cols']
        data_cols = [col['name'] for col in cols if col['name'].startswith('counts')]
        
        result = []
        for col in data_cols:
            # output in column-major order, since first index is "x",
            # and we want to traverse that axis first.       
            array_out = self['Measurements':col].view(ndarray)
            array_out = array_out.ravel('F')
            result.append(array_out.astype(float32).tostring())
        
        return result
     
    def get_csv(self):
        if len(self.shape) == 3:
            num_cols = self.shape[2]
            new_array = empty((self.shape[0] * self.shape[1], num_cols + 2))
            new_array[:,0] = (self._info[0]['values'][:,newaxis] * ones((self.shape[0], self.shape[1]))).ravel()
            new_array[:,1] = (self._info[1]['values'][newaxis,:] * ones((self.shape[0], self.shape[1]))).ravel()
            data_names = []
            data_names.append(self._info[0]['name']) # xlabel
            data_names.append(self._info[1]['name']) # ylabel
            
            for i in range(num_cols):
                new_array[:,i+2] = self[:,:,i].view(ndarray).ravel()
                data_names.append(self._info[2]['cols'][i]['name'])
            
            outstr = StringIO()
            outstr.write('#' + '\t'.join(data_names) + '\n')
            savetxt(outstr, new_array, delimiter='\t', newline='\n')
            
            outstr.seek(0)
            return_val = outstr.read()
            outstr.close()
            
            return return_val

        elif len(self.shape) == 2:
            num_cols = self.shape[1]
            new_array = empty((self.shape[0], num_cols + 1))
            new_array[:,0] = (self._info[0]['values'])
            data_names = []
            data_names.append(self._info[0]['name']) # xlabel
            
            for i in range(num_cols):
                new_array[:,i+1] = self[:,i].view(ndarray)
                data_names.append(self._info[1]['cols'][i]['name'])
            
            outstr = StringIO()
            outstr.write('#' + '\t'.join(data_names) + '\n')
            savetxt(outstr, new_array, delimiter='\t')
            
            outstr.seek(0)
            return_val = outstr.read()
            outstr.close()
            return return_val
            
        else:
            print "can only handle 1d or 2d data"
            return     
        
        
#    def get_plottable_new(self):
#        array_out = self['Measurements':'counts']
#        z = {'png': base64.b64encode(array_to_png(array_out, colormap='jet')), 
#             'data': array_out.tolist()}
#        dims = {}
#        dims['zmin'] = array_out.min()
#        dims['zmax'] = array_out.max()
#        axis = ['x', 'y']
#        for index, label in enumerate(axis):
#            arr = self._info[index]['values']
#            dims[axis[index] + 'min'] = amin(arr)
#            dims[axis[index] + 'max'] = amax(arr)
#            dims[axis[index] + 'dim'] = alen(arr)
#            dims['d' + axis[index]] = arr[1] - arr[0]
#        xlabel = self._info[0]['name']
#        ylabel = self._info[1]['name']
#        zlabel = self._info[2]['cols'][0]['name']
#        title = 'AND/R data' # That's creative enough, right?
#        type = '2d_image'
#        dump = dict(type=type, z=z, title=title, dims=dims, xlabel=xlabel, ylabel=ylabel, zlabel=zlabel)
#        res = simplejson.dumps(dump, sort_keys=True)
#        return res
