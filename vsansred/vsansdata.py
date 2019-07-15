"""
SANS data format
================

Internal data representation for SANS data.
"""

import sys
import datetime
from copy import copy, deepcopy
import json
from io import BytesIO

import numpy as np

from dataflow.lib.uncertainty import Uncertainty

IS_PY3 = sys.version_info[0] >= 3

IGNORE_CORNER_PIXELS = True

def _b(s):
    if IS_PY3:
        return s.encode('utf-8')
    else:
        return s

def _s(b):
    if IS_PY3:
        return b.decode('utf-8') if hasattr(b, 'decode') else b
    else:
        return b

class RawVSANSData(object):
    def __init__(self, metadata, detectors=None):
        self.metadata = metadata
        self.metadata['name'] = metadata['run.filename']
        self.detectors = detectors

    def todict(self):
        return _toDictItem(self.metadata)

    def get_plottable(self):
        #return {"entry": "entry", "type": "params", "params": _toDictItem(self.metadata)}
        return {"entry": "entry", "type": "metadata", "values": _toDictItem(self.metadata)}

    def get_metadata(self):
        return _toDictItem(self.metadata)        

    def export(self):
        output = json.dumps(_toDictItem(self.metadata, convert_bytes=True))
        name = getattr(self.metadata, "name", "default_name")
        entry = getattr(self.metadata, "entry", "default_entry")
        return {"name": name, "entry": entry, "export_string": output, "file_suffix": ".vsans.metadata.json"}

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
        obj = dict([(k, _toDictItem(v, convert_bytes=convert_bytes)) for k, v in obj.items()])
    elif isinstance(obj, bytes) and convert_bytes == True:
        obj = obj.decode()
    return obj

class VSansData(object):
    """VSansData object used for storing values from a sample file (not div/mask).
       Stores the array of data as a Uncertainty object (detailed in uncertainty.py)
       Stores all metadata
       q, qx, qy, theta all get updated with values throughout the reduction process
       Tsam and Temp are just used for storage across modules (in wireit)
    """
    def __init__(self, metadata=None, detectors=None):
        self.metadata = metadata if metadata is not None else {}
        self.detectors = detectors if detectors is not None else {}
    
    def copy(self):
        return VSansData(deepcopy(self.metadata), deepcopy(self.detectors))

    def __copy__(self):
        return self.copy()

    #def __str__(self):
        #return self.data.x.__str__()
    #def __repr__(self):
        #return self.__str__()

    def get_plottable(self):
        #return {"entry": "entry", "type": "params", "params": _toDictItem(self.metadata)}
        return {"entry": "entry", "type": "metadata", "values": _toDictItem(self.metadata)}

    def get_plottable_old(self):
        data = self.data.x.astype("float")
        xdim = data.shape[0]
        ydim = data.shape[1]
        if not (np.abs(data) > 1e-10).any():
            zmin = 0.0
            zmax = 1.0
        else:
            zmin = data[data > 1e-10].min()
            if IGNORE_CORNER_PIXELS:
                mask = np.ones(data.shape, dtype='bool')
                mask[0, 0] = mask[-1, 0] = mask[-1, -1] = mask[0, -1] = 0.0
                zmax = data[mask].max()
            else:
                zmax = data.max()
        if self.qx is None or self.qy is None:
            xmin = 0.5
            xmax = 128.5
            ymin = 0.5
            ymax = 128.5
        else:
            xmin = self.qx_min if self.qx_min is not None else self.qx.min()
            xmax = self.qx_max if self.qx_max is not None else self.qx.max()
            ymin = self.qy_min if self.qy_min is not None else self.qy.min()
            ymax = self.qy_max if self.qy_max is not None else self.qy.max()
        plottable_data = {
            'entry': self.metadata['entry'],
            'type': '2d',
            'z':  [data.flatten().tolist()],
            'title': _s(self.metadata['run.filename'])+': ' + _s(self.metadata['sample.labl']),
            #'metadata': self.metadata,
            'options': {
                'fixedAspect': {
                    #'fixAspect': True,
                    #'aspectRatio': 1.0
                }
            },
            'dims': {
                'xmax': xmax,
                'xmin': xmin,
                'ymin': ymin,
                'ymax': ymax,
                'xdim': xdim,
                'ydim': ydim,
                'zmin': zmin,
                'zmax': zmax,
            },
            'xlabel': self.xlabel,
            'ylabel': self.ylabel,
            'zlabel': 'Intensity (I)',
        }
        if self.aspect_ratio is not None:
            plottable_data['options']['fixedAspect'] = {
                'fixAspect': True,
                'aspectRatio': self.aspect_ratio
            }
        return plottable_data

    def get_metadata(self):
        metadata = {}
        metadata.update(pythonize(self.metadata))
        return metadata

def pythonize(obj):
    output = {}
    for a in obj:
        attr = obj.get(a, None)
        if isinstance(attr, np.integer):
            attr = int(attr)
        elif isinstance(attr, np.floating):
            attr = float(attr)
        elif isinstance(attr, np.ndarray):
            attr = attr.tolist()
        elif isinstance(attr, datetime.datetime):
            attr = [attr.year, attr.month, attr.day,
                    attr.hour, attr.minute, attr.second]
        elif isinstance(attr, dict):
            attr = pythonize(attr)
        output[a] = attr
    return output

class Sans1dData(object):
    properties = ['x', 'v', 'dx', 'dv', 'xlabel', 'vlabel', 'xunits', 'vunits', 'xscale', 'vscale', 'metadata', 'fit_function']

    def __init__(self, x, v, dx=0, dv=0, xlabel="", vlabel="", xunits="", vunits="", xscale="linear", vscale="linear", metadata=None, fit_function=None):
        self.x = x
        self.v = v
        self.dx = dx
        self.dv = dv
        self.xlabel = xlabel
        self.vlabel = vlabel
        self.xunits = xunits
        self.vunits = vunits
        self.xscale = xscale
        self.vscale = vscale
        self.metadata = metadata if metadata is not None else {}
        self.fit_function = fit_function

    def to_dict(self):
        props = dict([(p, getattr(self, p, None)) for p in self.properties])
        return pythonize(props)

    def get_plottable(self):
        label = "%s: %s" % (self.metadata['run.experimentScanID'], self.metadata['sample.labl'])
        xdata = self.x.tolist()
        ydata = self.v.tolist()
        yerr = self.dv.tolist()
        data = [[x, y, {"yupper": y+dy, "ylower": y-dy, "xupper": x, "xlower": x}] for x,y,dy in zip(xdata, ydata, yerr)]
        plottable = {
            "type": "1d",
            "options": {
                "axes": {
                    "xaxis": {"label": self.xlabel},
                    "yaxis": {"label": self.vlabel}
                },
                "series": [{"label": label}]
            },
            "data": [data]
        }
        return plottable

    def get_metadata(self):
        return self.to_dict()

    def export(self):
        fid = BytesIO()
        fid.write(_b("# %s\n" % json.dumps(pythonize(self.metadata)).strip("{}")))
        columns = {"columns": [self.xlabel, self.vlabel, "uncertainty", "resolution"]}
        units = {"units": [self.xunits, self.vunits, self.vunits, self.xunits]}
        fid.write(_b("# %s\n" % json.dumps(columns).strip("{}")))
        fid.write(_b("# %s\n" % json.dumps(units).strip("{}")))
        np.savetxt(fid, np.vstack([self.x, self.v, self.dv, self.dx]).T, fmt="%.10e")
        fid.seek(0)
        name = getattr(self, "name", "default_name")
        entry = getattr(self.metadata, "entry", "default_entry")
        return {"name": name, "entry": entry, "export_string": fid.read(), "file_suffix": ".sans1d.dat"}

class Parameters(dict):
    def get_metadata(self):
        return self

    def get_plottable(self):
        return self
