# -*- coding: UTF-8 -*-
import gzip
from collections import OrderedDict
import datetime
import numpy as np
import json
import io
import sys

IS_PY3 = sys.version_info[0] >= 3

def _b(s):
    if IS_PY3:
        return s.encode('utf-8')
    else:
        return s

from reductus.dataflow.lib import octave
from reductus.dataflow.lib.exporters import exports_HDF5, exports_text

class RawData(object):
    def __init__(self, name, data):
        histo_array = data.pop("histodata")
        self.histodata = histo_array
        #self.histodata = Uncertainty(histo_array, histo_array)
        self.metadata = {
            "name": name,
            "entry": "entry"
        }
        self.metadata.update(data)
        self.name = name

    def todict(self):
        return _toDictItem(self.metadata)

    def get_plottable(self):
        return {"entry": "entry", "type": "metadata", "values": _toDictItem(self.metadata)}

    def get_metadata(self):
        return _toDictItem(self.metadata)

class EfTwoThetaData(object):
    def __init__(self, name, data, ef=None, twotheta=None, metadata=None):
        self.metadata = metadata
        self.data = data
        self.ef = ef
        self.twotheta = twotheta
        self.name = name
        self.xaxis = {
            "label": u"Ef [meV]",
            "values": self.ef,
            "min": self.ef.min(),
            "max": self.ef.max(),
            "dim": self.ef.shape[0]
        }
        self.yaxis = {
            "label": "Detector Angle [degrees]",
            "values": self.twotheta,
            "min": self.twotheta.min(),
            "max": self.twotheta.max(),
            "dim": self.twotheta.shape[0]
        }

    def get_plottable(self):
        output = {
            "title": self.name,
            "dims": {
                "ymin": self.yaxis["min"],
                "ymax": self.yaxis["max"],
                "ydim": self.yaxis["dim"],
                "xmin": self.xaxis["min"],
                "xmax": self.xaxis["max"],
                "xdim": self.xaxis["dim"],
                "zmin": self.data.min(),
                "zmax": self.data.max()
            },
            "type": "2d",
            "xlabel": self.xaxis["label"],
            "ylabel": self.yaxis["label"],
            "z": [self.data.flatten().tolist()]
        }
        return output
    
    def get_metadata(self):
        return _toDictItem(self.metadata)

class EQData(object):
    def __init__(self, name, data, metadata):
        self.metadata = metadata
        self.data = data
        self.name = name
        self.xaxis = {
            "label": u"|Q| [A⁻¹]",
            "values": np.linspace(metadata["Q_min"], metadata["Q_max"], data.shape[0]),
            "min": metadata["Q_min"],
            "max": metadata["Q_max"],
            "dim": data.shape[0]
        }
        self.yaxis = {
            "label": "Ei-Ef [meV]",
            "values": np.linspace(-metadata["Ei"], metadata["Ei"], data.shape[1]),
            "min": -metadata["Ei"],
            "max": metadata["Ei"],
            "dim": data.shape[1]
        }

    def get_plottable(self):
        Ei = self.metadata['Ei']
        Q_max = self.metadata['Q_max']
        EQ_data = self.data
        output = {
            "title": self.name,
            "dims": {
                "ymin": self.yaxis["min"],
                "ymax": self.yaxis["max"],
                "ydim": self.yaxis["dim"],
                "xmin": self.xaxis["min"],
                "xmax": self.xaxis["max"],
                "xdim": self.xaxis["dim"],
                "zmin": self.data.min(),
                "zmax": self.data.max()
            },
            "type": "2d",
            "xlabel": self.xaxis["label"],
            "ylabel": self.yaxis["label"],
            "z": [self.data.flatten().tolist()]
        }
        return output

    def get_metadata(self):
        return _toDictItem(self.metadata) 

class DCS1dData(object):
    properties = ['x', 'v', 'dx', 'dv', 'xlabel', 'vlabel', 'xunits', 'vunits', 'metadata']

    def __init__(self, x, v, dx=0, dv=0, xlabel="", vlabel="", xunits="", vunits="", metadata=None):
        self.x = x
        self.v = v
        self.dx = dx
        self.dv = dv
        self.xlabel = xlabel
        self.vlabel = vlabel
        self.xunits = xunits
        self.vunits = vunits
        self.metadata = metadata if metadata is not None else {}

    def to_dict(self):
        props = dict([(p, getattr(self, p, None)) for p in self.properties])
        return _toDictItem(props)

    def get_plottable(self):
        label = "%s: %s" % (self.metadata['name'], self.metadata['entry'])
        xdata = self.x.tolist()
        ydata = self.v.tolist()
        yerr = self.dv.tolist()
        data = [[x, y, {"yupper": y+dy, "ylower": y-dy, "xupper": x, "xlower": x}] for x,y,dy in zip(xdata, ydata, yerr)]
        plottable = {
            "type": "1d",
            "title": self.metadata.get("name", "DCS 1d data"),
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

    @exports_text(name="column")
    def to_column_text(self):
        with io.BytesIO() as fid:
            #fid.write(_b("# %s\n" % json.dumps(_toDictItem(self.metadata)).strip("{}")))
            metadata = {"name": self.metadata["name"]}
            fid.write(_b("# %s\n" % json.dumps(metadata).strip("{}")))
            columns = {"columns": [self.xlabel, self.vlabel, "uncertainty", "resolution"]}
            units = {"units": [self.xunits, self.vunits, self.vunits, self.xunits]}
            fid.write(_b("# %s\n" % json.dumps(columns).strip("{}")))
            fid.write(_b("# %s\n" % json.dumps(units).strip("{}")))
            np.savetxt(fid, np.vstack([self.x, self.v, self.dv, self.dx]).T, fmt="%.10e")
            fid.seek(0)
            value = fid.read()

        return {
            "name": self.metadata.get("name", "default_name"),
            "entry": self.metadata.get("entry", "default_entry"),
            "file_suffix": ".dcs.dat",
            "value": value.decode(),
        }

class Parameters(dict):
    def get_metadata(self):
        return _toDictItem(self)

    def get_plottable(self):
        return {"entry": "entry", "type": "metadata", "values": _toDictItem(self)}

def readDCS(name, fid):
    gzf = gzip.GzipFile(fileobj=fid)
    data = octave.read_octave_binary(gzf)
    return RawData(name, data)

def _toDictItem(obj):
    if isinstance(obj, np.integer):
        obj = int(obj)
    elif isinstance(obj, np.floating):
        obj = float(obj)
    elif isinstance(obj, np.ndarray):
        obj = obj.tolist()
    elif isinstance(obj, datetime.datetime):
        obj = [obj.year, obj.month, obj.day, obj.hour, obj.minute, obj.second]
    elif isinstance(obj, list):
        obj = [_toDictItem(a) for a in obj]
    elif isinstance(obj, dict):
        obj = dict([(k, _toDictItem(v)) for k, v in obj.items()])
    return obj