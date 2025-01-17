from io import BytesIO
#from cStringIO import StringIO as BytesIO

from numpy import ndarray, array, fromstring, float32, ones, empty, newaxis, savetxt, sqrt, mod, isnan, ma, hstack, log10
from reductus.dataflow.lib.exporters import exports_HDF5, exports_text

from .MetaArray import MetaArray

class FilterableMetaArray(MetaArray):
    def __new__(cls, *args, **kw):
        obj = MetaArray.__new__(cls, *args, **kw)
        #print("fma extra")
        obj.extrainfo = obj._info[-1]
        return obj

    def todict(self):
        output = { 'shape': self.shape, 'type': str(self.dtype), 'info': self.infoCopy()}
        output['data'] = self.tolist()
        return _toDictItem(output)

    def dumps(self):
        meta = { 'shape': self.shape, 'type': str(self.dtype), 'info': self.infoCopy()}
        assert isinstance(meta['info'], list)
        axstrs = []
        for ax in meta['info']:
            if 'values' in ax:
                axstrs.append(ax['values'].tostring())
                ax['values_len'] = len(axstrs[-1])
                ax['values_type'] = str(ax['values'].dtype)
                del ax['values']
        fd = BytesIO()
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
            if 'values' in ax:
                values = array(ax['values'])
                extrema[ax['name']] = [values.min(), values.max()]
        return extrema

    @classmethod
    def loads(cls, str):
        fd = BytesIO(str)
        meta = ''
        while True:
            line = fd.readline().strip()
            if line == '':
                break
            meta += line
        meta = eval(meta)

        ## read in axis values
        for ax in meta['info']:
            if 'values_len' in ax:
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

    def get_metadata(self):
        metadata = {}
        metadata.update(self.extrainfo)
        return metadata

    @exports_text(name="column")
    def to_column_text(self):
        name = self.extrainfo["friendly_name"]
        entry = self.extrainfo["entry"]
        suffix = ".ospec.dat"
        filename = "%s_%s%s" % (name, entry, suffix)
        return_value = {"name": name, "entry": entry, "file_suffix": suffix}
        if len(self.shape) == 3:
            # return gnuplottable format:
            """ export 2d data to gnuplot format """
            # grab the first counts col:
            data = self
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

            return_value["value"] =  result[0]

        elif len(self.shape) == 2:
            fid = BytesIO()
            cols = self._info[1]['cols']
            # put x axis in first:
            data_cols = [self._info[0]['name']]
            data_cols.extend([col['name'] for col in cols if not col['name'].startswith('error')])
            output_data = hstack((self._info[0]['values'][:,None], self))
            savetxt(fid, output_data, header="\t".join(data_cols))
            fid.seek(0)
            return_value["value"] = fid.read().decode()

        else:
            print("can only handle 1d or 2d data")
            return_value["value"] = ""

        return return_value

    def get_plottable(self, binary_fp=None):
        if len(self.shape) == 3:
            return self.get_plottable_2d(binary_fp)
        elif len(self.shape) == 2:
            return self.get_plottable_nd()
        else:
            print("can only handle 1d or 2d data")
            return

    def get_plottable_1d(self, binary_fp=None):
        colors = ['Blue', 'Red', 'Green', 'Yellow']
        cols = self._info[1]['cols']
        data_cols = [col['name'] for col in cols if not col['name'].startswith('error')]
        x = self._info[0]['values'].tolist()
        xlabel = self._info[0]['name']
        title = self._info[-1].get('friendly_name', "1d data")
        plottable_data = {
            'type': '1d',
            'entry': self.extrainfo.get('entry', 'entry'),
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

        return [plottable_data]

    def get_plottable_nd(self, binary_fp=None):
        colors = ['Blue', 'Red', 'Green', 'Yellow']
        cols = self._info[1]['cols']
        data_cols = [col['name'] for col in cols if not col['name'].startswith('error')]
        column_listing = dict([(d, {"label": d}) for d in data_cols])
        x = self._info[0]['values'].tolist()
        xlabel = self._info[0]['name']
        column_listing[xlabel] = {"label": xlabel}
        plottable_data = {
            'type': 'nd',
            'title': self.extrainfo['path'],
            'name': self._info[-1].get('filename', '1d data'),
            'entry': self._info[-1].get('entry', ''),
            'columns': column_listing,
            "options": {
                "series": [ 
                    {
                        'label': self._info[-1].get('friendly_name', '1d data'),
                        'color': 'Red',
                        'style': 'line',
                    }
                ],
                'xcol': xlabel,
                'ycol': cols[0]['name'],
                "errorbar_width": 0
            },
            'datas': {xlabel: {'values': x}},
            'clear_existing': False,
        }

        for i, col in enumerate(data_cols):
            y = self['Measurements':col].tolist()
            error_col = next((i for i in range(len(cols)) if cols[i]['name'] == ('error_'+col)), -1)
            series_y = {'values': y}
            if error_col > 0:
                series_y['errorbars'] = self['Measurements':'error_'+col].tolist()
            plottable_data['datas'][col] = series_y

        return plottable_data

    def get_plottable_2d(self, binary_fp=None):
        # grab the first counts col:
        cols = self._info[2]['cols']
        counts_col = next(iter([col['name'] for col in cols if col['name'].startswith('counts')]))
        mon_col = next(iter([col['name'] for col in cols if col['name'].startswith('monitor')]))
        array_out = self['Measurements':counts_col].view(ndarray) / self['Measurements':mon_col].view(ndarray) 

        dump = {'entry': self.extrainfo.get('entry', 'entry')}
        if binary_fp is not None:
            # use lookup to get binary value
            z = [[0,0]]
            dump['binary_fp'] = binary_fp + ":" + str(colnum)
        else: # use the old way
            af = array_out.ravel('C')
            z = [ma.masked_array(af, mask=isnan(af)).tolist(fill_value=None)]

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
            dims[axis[index] + 'min'] = float(arr[0])
            dims[axis[index] + 'max'] = float(arr[-1])
            dims[axis[index] + 'dim'] = len(arr)
        xlabel = self._info[0]['name']
        ylabel = self._info[1]['name']
        zlabel = counts_col
        #zlabel = self._info[2]['cols'][0]['name']
        title = 'MAGIK data' # That's creative enough, right?
        plot_type = '2d'
        transform = 'log' # this is nice by default
        dump.update( dict(type=plot_type, z=z, title=title, dims=dims,
                    xlabel=xlabel, ylabel=ylabel, zlabel=zlabel,
                    transform=transform) )
        return dump

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

            outstr = BytesIO()
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

            outstr = BytesIO()
            outstr.write('#' + '\t'.join(data_names) + '\n')
            savetxt(outstr, new_array, delimiter='\t')

            outstr.seek(0)
            return_val = outstr.read()
            outstr.close()
            return return_val

        else:
            print("can only handle 1d or 2d data")
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

import datetime
from collections import OrderedDict
import numpy as np

def _toDictItem(obj, convert_bytes=False):
    if isinstance(obj, np.integer):
        obj = int(obj)
    elif isinstance(obj, np.floating):
        obj = float(obj)
    elif isinstance(obj, np.ndarray):
        obj = obj.tolist()
    elif isinstance(obj, datetime.datetime):
        obj = [obj.year, obj.month, obj.day, obj.hour, obj.minute, obj.second]
    elif isinstance(obj, list):
        obj = [_toDictItem(a, convert_bytes=convert_bytes) for a in obj]
    elif isinstance(obj, dict):
        obj = OrderedDict([(k, _toDictItem(v, convert_bytes=convert_bytes)) for k, v in obj.items()])
    elif isinstance(obj, bytes) and convert_bytes == True:
        obj = obj.decode()
    return obj