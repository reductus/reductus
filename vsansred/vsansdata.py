"""
SANS data format
================

Internal data representation for SANS data.
"""

import sys
import datetime
from copy import copy, deepcopy
from collections import OrderedDict
import json
from io import BytesIO

import numpy as np

from dataflow.lib.uncertainty import Uncertainty

IS_PY3 = sys.version_info[0] >= 3

IGNORE_CORNER_PIXELS = True

short_detectors = ["B", "MB", "MT", "ML", "MR", "FT", "FB", "FL", "FR"]

def _b(s):
    if IS_PY3:
        return s.encode('utf-8') if hasattr(s, 'encode') else s
    else:
        return s

def _s(b):
    if IS_PY3:
        return b.decode('utf-8') if hasattr(b, 'decode') else b
    else:
        return b

class RawVSANSData(object):
    suffix = ".vsans"
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
        return {"name": name, "entry": entry, "export_string": output, "file_suffix": self.suffix + ".metadata.json"}

class RawVSANSHe3Data(RawVSANSData):
    pass

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
        return self.__class__(deepcopy(self.metadata), deepcopy(self.detectors))

    def __copy__(self):
        return self.copy()

    #def __str__(self):
        #return self.data.x.__str__()
    #def __repr__(self):
        #return self.__str__()

    def get_plottable(self):
        datasets = []
        zmin = +np.inf
        zmax = -np.inf
        for sn in short_detectors:
            detname = 'detector_{short_name}'.format(short_name=sn)
            det = self.detectors.get(detname, None)
            if det is None:
                continue
            corrected = det['data'].x 
            dimX, dimY = corrected.shape
            xaxis = det[self.xaxisname]
            yaxis = det[self.yaxisname]
            xmax = xaxis.max()
            xmin = xaxis.min()
            ymax = yaxis.max()
            ymin = yaxis.min()
            zmax = np.max([corrected.max(), zmax])
            zmin = np.min([corrected.min(), zmin])

            datasets.append({
                "data": corrected.ravel('C'),
                "dims": {
                    "xmin": xmin,
                    "xmax": xmax,
                    "xdim": dimX,
                    "ymin": ymin,
                    "ymax": ymax,
                    "ydim": dimY,
                }
            })
        
        data_2d = {
            "dims": {
                "zmin": zmin,
                "zmax": zmax,
            },
            "type": "2d_multi",
            "title": _b(self.metadata["run.filename"]) + b":" + _b(self.metadata["sample.labl"]),
            #"z": [output_grid.T.tolist()],
            "datasets": datasets,
            "ztransform": "log",
            "xlabel": self.xaxisname,
            "ylabel": self.yaxisname,
            "zlabel": "intensity",
            "options": {
                "fixedAspect": {
                    "fixAspect": True,
                    "aspectRatio": 1.0
                }
            },
            "metadata": self.metadata.copy()
        }

        return _toDictItem(data_2d, convert_bytes=True)

        #return {"entry": "entry", "type": "metadata", "values": _toDictItem(self.metadata)}

    def get_metadata(self):
        metadata = {}
        metadata.update(_toDictItem(self.metadata, convert_bytes=True))
        return metadata


class VSansDataRealSpace(VSansData):
    def __init__(self, metadata=None, detectors=None):
        self.xaxisname = 'X'
        self.yaxisname = 'Y'
        VSansData.__init__(self, metadata=metadata, detectors=detectors)

class VSansDataAngleSpace(VSansData):
    def __init__(self, metadata=None, detectors=None):
        self.xaxisname = 'thetaX'
        self.yaxisname = 'thetaY'
        VSansData.__init__(self, metadata=metadata, detectors=detectors)

class VSansDataQSpace(VSansData):
    def __init__(self, metadata=None, detectors=None):
        self.xaxisname = 'Qx'
        self.yaxisname = 'Qy'
        VSansData.__init__(self, metadata=metadata, detectors=detectors)

    def export(self):
        # export to 6-column format compatible with SASVIEW
        # Data columns are Qx - Qy - I(Qx,Qy) - err(I) - Qz - SigmaQ_parall - SigmaQ_perp - fSubS(beam stop shadow)
        column_names = ["Qx", "Qy", "I", "dI", "Qz", "SigmaQ_para", "SigmaQ_perp", "ShadowFactor", "detector_id"]
        labels = ["Qx (1/A)", "Qy (1/A)", "I(Q) (1/cm)", "std. dev. I(Q) (1/cm)", "Qz (1/A)", "sigmaQ_para", "sigmaQ_perp", "ShadowFactor", "detector_id"]

        fid = BytesIO()
        fid.write(_b("# %s\n" % json.dumps(_toDictItem(self.metadata, convert_bytes=True)).strip("{}")))
        fid.write(_b('# detector_id: {"0":"B","1":"MB","2":"MT","3":"ML","4":"MR","5":"FT","6":"FB","7":"FL","8":FR"}\n'))
        fid.write(_b("# %s\n" % json.dumps({"columns": labels}).strip("{}")))
        for d_id, sn in enumerate(short_detectors):
            detname = 'detector_{short_name}'.format(short_name=sn)
            det = self.detectors.get(detname, None)
            if det is None:
                continue
            column_length = det['Qx'].size
            column_values = [
                det['Qx'].ravel('C'),
                det['Qy'].ravel('C'),
                (det['data']).x.ravel('C'),
                np.sqrt((det['data']).variance).ravel('C'),
                det['Qz'].ravel('C'),
                np.zeros(column_length, dtype='float'), # not yet calculated
                np.zeros(column_length, dtype='float'), # not yet calculated
                np.zeros(column_length, dtype='float'), # not yet calculated
                np.ones(column_length, dtype='float') * d_id
            ]
            np.savetxt(fid, np.vstack(column_values).T, fmt="%.10e")
        fid.seek(0)
        name = _s(self.metadata["run.filename"])
        entry = _s(self.metadata.get("entry", "default_entry"))
        return {"name": name, "entry": entry, "export_string": fid.read(), "file_suffix": ".vsans2d.dat"}        

class VSans1dData(object):
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
        label = self.metadata.get('title', "unknown"),
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
        return _toDictItem(self.metadata)

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
        return {"name": name, "entry": entry, "export_string": fid.read(), "file_suffix": ".vsans1d.dat"}

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

class Parameters(object):
    def __init__(self, params=None):
        self.params = params

    def get_metadata(self):
        return self.params

    def get_plottable(self):
        #return {"entry": "entry", "type": "params", "params": _toDictItem(self.metadata)}
        return {"entry": "entry", "type": "params", "params": _toDictItem(self.params)}

class Metadata(OrderedDict):
    def get_plottable(self):
        #return {"entry": "entry", "type": "params", "params": _toDictItem(self.metadata)}
        return {"entry": "entry", "type": "metadata", "values": _toDictItem(self)}

    def get_metadata(self):
        return _toDictItem(self)        

    def export(self):
        output = json.dumps(_toDictItem(self, convert_bytes=True))
        name = getattr(self, "name", "default_name")
        entry = getattr(self, "entry", "default_entry")
        return {"name": name, "entry": entry, "export_string": output, "file_suffix": ".vsans.metadata.json"}