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
            "name": _s(self.metadata.get("name", "default_name")),
            "entry": _s(self.metadata.get("entry", "default_entry")),
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
        # export to 6-column format compatible with SASVIEW
        # Data columns are Qx - Qy - I(Qx,Qy) - err(I) - Qz - SigmaQ_parall - SigmaQ_perp - fSubS(beam stop shadow)
        column_names = ["Qx", "Qy", "I", "dI", "Qz", "SigmaQ_para", "SigmaQ_perp", "ShadowFactor", "detector_id"]
        labels = ["Qx (1/A)", "Qy (1/A)", "I(Q) (1/cm)", "std. dev. I(Q) (1/cm)", "Qz (1/A)", "sigmaQ_para", "sigmaQ_perp", "ShadowFactor", "detector_id"]

        with BytesIO() as fid:
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
            value = fid.read()

        return {
            "name": _s(self.metadata["run.filename"]),
            "entry": _s(self.metadata.get("entry", "default_entry")),
            "file_suffix": ".vsans2d.dat",
            "value": value.decode(),
        }

    @exports_HDF5(name="NXcanSAS")
    def to_NXcanSAS(self):
        import h5py

        # TODO: Avoid returning open handles to caller.
        # Check whether closing h5_item frees fid, or whether it is kept
        # around indefinitely leading to a memory leak.
        fid = BytesIO()
        h5_item = h5py.File(fid, 'w')

        entry_name = self.metadata.get("entry", "entry")
        nxentry = h5_item.create_group(entry_name)
        nxentry.attrs.update({
            "NX_class": "NXentry",
            "canSAS_class": "SASentry",
            "version": "1.0"
        })
        nxentry["definition"] = "NXcanSAS"
        nxentry["run"] = "<see the documentation>"
        nxentry["title"] = self.metadata["sample.description"]

        instrument = nxentry.create_group("instrument")
        total_length = 0
        for d_id, sn in enumerate(short_detectors):
            detname = 'detector_{short_name}'.format(short_name=sn)
            det = self.detectors.get(detname, None)
            if det is None:
                continue
            g = instrument.create_group(detname)
            g.attrs["NX_class"] = "NXdetector"
            g["data"] = det["data"].x
            g["data_variance"] = det["data"].variance
            g["Qx"] = det["Qx"]
            g["Qy"] = det["Qy"]
            g["Qz"] = det["Qz"]
            total_length += det["data"].x.size

        I = np.empty((total_length), dtype=float)
        dI = np.empty((total_length), dtype=float)
        Q = np.empty((3,total_length), dtype=float)

        data_cursor = 0
        for d_id, sn in enumerate(short_detectors):
            detname = 'detector_{short_name}'.format(short_name=sn)
            det = self.detectors.get(detname, None)
            if det is None:
                continue
            I_new = det["data"].x
            dI_new = det["data"].variance
            I[data_cursor:data_cursor + I_new.size] = I_new.ravel("C")
            dI[data_cursor:data_cursor + I_new.size] = dI_new.ravel("C")
            for qi, qn in enumerate(["Qx", "Qy", "Qz"]):
                Q[qi, data_cursor:data_cursor + I_new.size] = det[qn].ravel("C")

        # TODO: convert this to a view of detectors using h5py.VirtualSource?
        datagroup = nxentry.create_group("data")
        datagroup.attrs.update({
            "NX_class": "NXdata",
            "canSAS_class": "SASdata",
            "signal": "I",
            "I_axes": "<see the documentation>",
            "Q_indices": [1,2,3]
        })
        datagroup["I"] = I
        datagroup["I"].attrs["units"] = "1/m"
        datagroup["I"].attrs["uncertainties"] = "Idev"
        datagroup["Idev"] = dI
        datagroup["Idev"].attrs["units"] = datagroup["I"].attrs["units"]
        datagroup["Q"] = Q
        datagroup["Q"].attrs["units"] = "1/nm"

        return {
            "name": _s(self.metadata.get("name", "default_name")),
            "entry": _s(self.metadata.get("entry", "default_entry")),
            "file_suffix": ".sansIQ.nx.h5",
            "value": h5_item,
        }

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
            "value": output,
        }
