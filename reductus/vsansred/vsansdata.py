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

from reductus.dataflow.lib.uncertainty import Uncertainty
from reductus.dataflow.lib.exporters import exports_HDF5, exports_text
from reductus.vsansred.export_vsans import (
    exports_vsans_1d_nxcansas, export_1d_to_nxcansas, export_2d_to_nxcansas, export_2d_to_ascii)

IS_PY3 = sys.version_info[0] >= 3

IGNORE_CORNER_PIXELS = True

short_detectors = ["B", "MB", "MT", "ML", "MR", "FT", "FB", "FL", "FR"]

def _b(s):
    if IS_PY3:
        return s.encode('utf-8') if hasattr(s, 'encode') else s
    else:
        return s

class RawVSANSData(object):
    suffix = ".vsans"
    def __init__(self, metadata, detectors=None):
        self.metadata = metadata
        self.metadata['name'] = metadata['run.filename']
        self.detectors = detectors

    def copy(self):
        return self.__class__(deepcopy(self.metadata), deepcopy(self.detectors))

    def __copy__(self):
        return self.copy()

    def todict(self):
        return _toDictItem(self.metadata)

    def get_plottable(self):
        #return {"entry": "entry", "type": "params", "params": _toDictItem(self.metadata)}
        to_exclude = ["fileinfo"]
        metadata = self.metadata.copy()
        for key in to_exclude:
            metadata.pop(key, None)
        return {"entry": "entry", "type": "metadata", "values": _toDictItem(metadata, convert_bytes=True)}

    def get_metadata(self):
        return _toDictItem(self.metadata, convert_bytes=True)

    @exports_text(name="metadata")
    def to_column_text(self):
        output = json.dumps(_toDictItem(self.metadata, convert_bytes=True))
        return {
            "name": self.metadata.get("name", "default_name"),
            "entry": self.metadata.get("entry", "default_entry"),
            "file_suffix": self.suffix + "metadata.json",
            "value": output,
        }

class RawVSANSHe3Data(RawVSANSData):
    pass

def _toDictItem(obj, convert_bytes=False):
    if isinstance(obj, np.integer):
        obj = int(obj)
    elif isinstance(obj, np.floating):
        obj = float(obj)
    elif isinstance(obj, np.ndarray):
        obj = obj.tolist()
    elif isinstance(obj, Uncertainty):
        obj = _toDictItem({'x': obj.x, 'variance': obj.variance})
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
    properties = ['metadata', 'detectors']

    def __init__(self, metadata=None, detectors=None):
        self.metadata = metadata if metadata is not None else {}
        self.detectors = detectors if detectors is not None else {}
    
    def copy(self):
        return self.__class__(deepcopy(self.metadata), deepcopy(self.detectors))

    def __copy__(self):
        return self.copy()

    def __sub__(self, other):

        result = self.copy()

        for sn in short_detectors:
            detname = "detector_{short_name}".format(short_name=sn)
            if detname in result.detectors and detname in other.detectors:
                result.detectors[detname]["data"] = (
                        result.detectors[detname]["data"]
                        - other.detectors[detname]["data"]
                )

        return result

    def __mul__(self, other):
        result = self.copy()

        if hasattr(other, "x"):
            val = float(other.x)
            var = float(getattr(other, "variance", 0.0))
        elif hasattr(other, "value"):
            val = float(other.value)
            var = float(getattr(other, "variance", 0.0))
        elif isinstance(other, (int, float)):
            val = float(other)
            var = 0.0
        else:
            return NotImplemented

        for detname, det in result.detectors.items():
            if "data" in det:
                data_old = det["data"]
                det["data"] = data_old * val

                if "err" in det:
                    err_old = det["err"]
                    det["err"] = np.sqrt((val * err_old) ** 2 + (data_old ** 2) * var)
                elif "variance" in det:
                    var_old = det["variance"]
                    det["variance"] = (val ** 2) * var_old + (data_old ** 2) * var

        return result

    def __rmul__(self, other):
        return self.__mul__(other)

    #def __str__(self):
        #return self.data.x.__str__()
    #def __repr__(self):
        #return self.__str__()

    def get_plottable(self):
        datasets = []
        zmin = +np.inf
        zmax = -np.inf
        series = []
        series_color = "red"
        for sn in short_detectors:
            detname = 'detector_{short_name}'.format(short_name=sn)
            det = self.detectors.get(detname, None)
            if det is None:
                continue
            series.append({"label": sn, "color": series_color})
            corrected = det['data'].x
            dimX, dimY = corrected.shape
            xaxis = det[self.xaxisname]
            yaxis = det[self.yaxisname]
            xmax = xaxis.max()
            xmin = xaxis.min()
            xstep = (xmax - xmin) / (max(dimX-1, 1))
            ymax = yaxis.max()
            ymin = yaxis.min()
            ystep = (ymax - ymin) / (max(dimY-1, 1))
            zmax = np.max([corrected.max(), zmax])
            zmin = np.min([corrected.min(), zmin])

            new_dataset = {
                "data": corrected.ravel('C'),
                "dims": {
                    "xmin": xmin - xstep/2.0,
                    "xmax": xmax + xstep/2.0,
                    "xdim": dimX,
                    "ymin": ymin - ystep/2.0,
                    "ymax": ymax + ystep/2.0,
                    "ydim": dimY,
                }
            }
            if 'shadow_mask' in det:
                new_dataset['mask'] = det['shadow_mask'].astype(float).ravel('C')
            datasets.append(new_dataset)
        
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
                },
                "legend": {"show": True},
                "mask": {
                    "show": True,
                    "method": "overlay",
                    "overlay_color": "lightGreen",
                    "overlay_opacity": 0.8
                },
                "series": series
            },
            "metadata": self.metadata.copy()
        }

        return _toDictItem(data_2d, convert_bytes=True)

        #return {"entry": "entry", "type": "metadata", "values": _toDictItem(self.metadata)}

    def get_metadata(self):
        metadata = {}
        metadata.update(_toDictItem(self.metadata, convert_bytes=True))
        return metadata

    def todict(self):
        props = dict([(p, getattr(self, p, None)) for p in self.properties])
        return _toDictItem(props)


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

    @exports_text(name="column")
    def to_column_text(self):
        # All panels gridded onto one QxQy matrix in the NIST 2D ASCII format read by SasView
        return export_2d_to_ascii(self)

    @exports_HDF5(name="NXcanSAS")
    def to_NXcanSAS(self):
        # One SASentry with a SASdata group per detector panel
        return export_2d_to_nxcansas(self)

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

    def todict(self):
        props = dict([(p, getattr(self, p, None)) for p in self.properties])
        return _toDictItem(props)

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

    @exports_text(name="column")
    def to_column_text(self):
        with BytesIO() as fid:
            fid.write(_b("# %s\n" % json.dumps(_toDictItem(self.metadata, convert_bytes=True)).strip("{}")))
            columns = {"columns": [self.xlabel, self.vlabel, "uncertainty", "resolution"]}
            units = {"units": [self.xunits, self.vunits, self.vunits, self.xunits]}
            fid.write(_b("# %s\n" % json.dumps(columns).strip("{}")))
            fid.write(_b("# %s\n" % json.dumps(units).strip("{}")))
            np.savetxt(fid, np.vstack([self.x, self.v, self.dv, self.dx]).T, fmt="%.10e")
            fid.seek(0)
            value = fid.read()

        return {
            "name": getattr(self, "name", "default_name"),
            "entry": getattr(self.metadata, "entry", "default_entry"),
            "file_suffix": ".vsans1d.dat",
            "value": value.decode('utf-8'),
        }

    @exports_vsans_1d_nxcansas(name="NXcanSAS")
    def to_NXcanSAS(self):
        # Panels from the same measurement are merged into one SASdata group by the exporter
        return export_1d_to_nxcansas(self)

    def _copy_with(self, new_v, new_dv):
        return VSans1dData(
            x=self.x,
            v=new_v,
            dx=self.dx,
            dv=new_dv,
            xlabel=self.xlabel,
            vlabel=self.vlabel,
            xunits=self.xunits,
            vunits=self.vunits,
            xscale=self.xscale,
            vscale=self.vscale,
            metadata=self.metadata,
            fit_function=self.fit_function
        )

    def __add__(self, other):
        if isinstance(other, VSans1dData):
            return self._copy_with(self.v + other.v, np.sqrt(self.dv ** 2 + other.dv ** 2))
        return self._copy_with(self.v + other, self.dv)

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, VSans1dData):
            return self._copy_with(self.v - other.v, np.sqrt(self.dv ** 2 + other.dv ** 2))
        return self._copy_with(self.v - other, self.dv)

    def __rsub__(self, other):
        return self._copy_with(other - self.v, self.dv)

    def __mul__(self, other):
        if isinstance(other, VSans1dData):
            new_v = self.v * other.v
            rel_err_self = np.where(self.v != 0, self.dv / self.v, 0.0)
            rel_err_other = np.where(other.v != 0, other.dv / other.v, 0.0)
            new_dv = np.abs(new_v) * np.sqrt(rel_err_self ** 2 + rel_err_other ** 2)
            return self._copy_with(new_v, new_dv)
        return self._copy_with(self.v * other, self.dv * abs(other))

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, VSans1dData):
            with np.errstate(divide='ignore', invalid='ignore'):
                new_v = np.nan_to_num(self.v / other.v, nan=0.0, posinf=0.0, neginf=0.0)
                rel_err = np.sqrt((self.dv / self.v) ** 2 + (other.dv / other.v) ** 2)
                new_dv = np.nan_to_num(np.abs(new_v) * rel_err, nan=0.0, posinf=0.0, neginf=0.0)
            return self._copy_with(new_v, new_dv)
        return self._copy_with(self.v / other, self.dv / abs(other))

    def __rtruediv__(self, other):
        with np.errstate(divide='ignore', invalid='ignore'):
            new_v = np.nan_to_num(other / self.v, nan=0.0, posinf=0.0, neginf=0.0)
            new_dv = np.nan_to_num(np.abs(new_v) * (self.dv / self.v), nan=0.0, posinf=0.0, neginf=0.0)
        return self._copy_with(new_v, new_dv)

    def __pow__(self, power):
        new_v = self.v ** power
        new_dv = np.abs(power * (self.v ** (power - 1)) * self.dv)
        new_dv = np.nan_to_num(new_dv, nan=0.0, posinf=0.0, neginf=0.0)
        return self._copy_with(new_v, new_dv)

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

    def todict(self):
        props = dict([(p, getattr(self, p, None)) for p in self.properties])
        return _toDictItem(props)

    def get_plottable(self):
        label = "%s: %s" % (self.metadata['run.instFileNum'], self.metadata['sample.labl'])
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

    @exports_text(name="column")
    def export(self):
        with BytesIO() as fid:
            fid.write(_b("# %s\n" % json.dumps(_toDictItem(self.metadata)).strip("{}")))
            columns = {"columns": [self.xlabel, self.vlabel, "uncertainty", "resolution"]}
            units = {"units": [self.xunits, self.vunits, self.vunits, self.xunits]}
            fid.write(_b("# %s\n" % json.dumps(columns).strip("{}")))
            fid.write(_b("# %s\n" % json.dumps(units).strip("{}")))
            np.savetxt(fid, np.vstack([self.x, self.v, self.dv, self.dx]).T, fmt="%.10e")
            fid.seek(0)
            value = fid.read()

        return {
            "name": getattr(self, "name", "default_name"),
            "entry": getattr(self.metadata, "entry", "default_entry"),
            "file_suffix": ".sans1d.dat",
            "value": value.decode(),
        }

class Parameters(object):
    def __init__(self, params=None):
        self.params = params

    def get_metadata(self):
        return self.params

    def todict(self):
        return _toDictItem(self.params)

    def get_plottable(self):
        #return {"entry": "entry", "type": "params", "params": _toDictItem(self.metadata)}
        return {"entry": "entry", "type": "params", "params": _toDictItem(self.params)}

class Metadata(OrderedDict):
    def get_plottable(self):
        #return {"entry": "entry", "type": "params", "params": _toDictItem(self.metadata)}
        return {"entry": "entry", "type": "metadata", "values": _toDictItem(self)}

    def get_metadata(self):
        return _toDictItem(self)

    @exports_text(name="json")
    def export(self):
        value = json.dumps(_toDictItem(self, convert_bytes=True))
        return {
            "name": getattr(self, "name", "default_name"),
            "entry": getattr(self, "entry", "default_entry"),
            "file_suffix": ".vsans.metadata.json",
            "value": value,
        }
