# -*- coding: UTF-8 -*-
from collections import OrderedDict
import datetime
import numpy as np
import json
import io
import sys

IS_PY3 = sys.version_info[0] >= 3

from dataflow.lib.uncertainty import Uncertainty
from dataflow.lib.strings import _s, _b
from dataflow.lib.exporters import exports_text

class RawData(object):
    def __init__(self, metadata=None, countTime=None, detCts=None, transCts=None, monCts=None, Q=None):
        self.metadata = metadata
        self.countTime = countTime
        self.detCts = Uncertainty(detCts, detCts + (detCts == 0))
        self.transCts = Uncertainty(transCts, transCts + (transCts == 0))
        self.monCts = Uncertainty(monCts, monCts + (monCts == 0))
        self.Q = Q
        self.Q_offset = 0.0

    def todict(self):
        return _toDictItem(self.metadata)

    def get_plottable(self):
        return {"entry": "entry", "type": "metadata", "values": _toDictItem(self.metadata)}

    def get_metadata(self):
        return _toDictItem(self.metadata)

class USansData(RawData):
    xcol = "Q"
    xlabel = "Q"
    xunits = "1/Ang"
    ycol = "I_det"
    ylabel = "Counts"
    yunits = "arb. units"
    def get_plottable(self):
        name = self.metadata.get("run.filename", "")
        entry = ""
        xcol = "Q"
        ycol = "I_det"
        columns = OrderedDict([
            ('Q', {'label': 'Q', 'units': '1/Ang'}),
            ('I_det', {'label': 'Counts', 'units': '', 'errorbars': 'dI'}),
            ('I_trans', {'label': 'Transmission Counts', 'units': '', 'errorbars': 'dIt'}),
            ('I_mon', {'label': 'Monitor Counts', 'units': '', 'errorbars': 'dIm'}),
            ('countTime', {'label': 'Count Time', 'units': 's'}),
        ])
        datas = {
            "Q": {"values": self.Q.tolist()},
            "I_det": {"values": self.detCts.x.tolist(), "errorbars": np.sqrt(self.detCts.variance).tolist()},
            "I_trans": {"values": self.transCts.x.tolist(), "errorbars": np.sqrt(self.transCts.variance).tolist()},
            "I_mon": {"values": self.monCts.x.tolist(), "errorbars": np.sqrt(self.monCts.variance).tolist()},
            "countTime": {"values": self.countTime.tolist()},
        }
        series = [{"label": "%s:%s" % (name, entry)}]
        plottable = {
            "type": "nd",
            "title": "%s:%s" % (name, entry),
            "entry": "entry",
            "columns": columns,
            "options": {
                "series": series,
                "axes": {
                    "xaxis": {"label": "%s(%s)" % (columns[xcol]["label"], columns[xcol]["units"])},
                    "yaxis": {"label": "%s(%s)" % (columns[ycol]["label"], columns[ycol]["units"])}
                },
                "xcol": xcol,
                "ycol": ycol,
                "errorbar_width": 0
            },
            "datas": datas
        }
        #print(plottable)
        return plottable

class USansCorData(object):
    def __init__(self, metadata=None, iqCOR=None, Q=None):
        self.metadata = metadata
        self.iqCOR = iqCOR
        self.Q = Q

    def todict(self):
        return _toDictItem(self.metadata)

    def get_plottable(self):
        if isinstance(self.metadata, list):
            name = ",".join([m.get("Sample file", "") for m in self.metadata])
        else:
            name = self.metadata.get("Sample file", "")
        entry = ""
        xcol = "Q"
        ycol = "iqCOR"
        columns = OrderedDict([
            ('Q', {'label': 'Q', 'units': '1/Ang'}),
            ('iqCOR', {'label': 'Corrected Counts', 'units': '/1E6 Monitor', 'errorbars': 'dI'}),
        ])
        datas = {
            "Q": {"values": self.Q.tolist()},
            "iqCOR": {"values": self.iqCOR.x.tolist(), "errorbars": np.sqrt(self.iqCOR.variance).tolist()},
        }
        series = [{"label": "%s:%s" % (name, entry)}]
        plottable = {
            "type": "nd",
            "title": "%s:%s" % (name, entry),
            "entry": "entry",
            "columns": columns,
            "options": {
                "series": series,
                "axes": {
                    "xaxis": {"label": "%s(%s)" % (columns[xcol]["label"], columns[xcol]["units"])},
                    "yaxis": {"label": "%s(%s)" % (columns[ycol]["label"], columns[ycol]["units"])}
                },
                "xcol": xcol,
                "ycol": ycol,
                "errorbar_width": 0
            },
            "datas": datas
        }
        #print(plottable)
        return plottable

    def get_metadata(self):
        return _toDictItem(self.metadata)
    
    @exports_text(name="column")
    def to_column_text(self):
        from io import BytesIO
        # export to 6-column format compatible with SASVIEW
        # Data columns are Qx - Qy - I(Qx,Qy) - err(I) - Qz - SigmaQ_parall - SigmaQ_perp - fSubS(beam stop shadow)
        labels = ["Qx (1/A)", "I(Q) (Counts/sec/(1e6 Monitor))", "std. dev. I(Q) (1/cm)", "dQ (1/A)", "filler", "filler"]

        with BytesIO() as fid:
            cleaned_metadata = _toDictItem(self.metadata, convert_bytes=True)
            if not isinstance(cleaned_metadata, list):
                cleaned_metadata = [cleaned_metadata]
            for c in cleaned_metadata:
                fid.write(b'### Parameters:\n')
                for k,v in c.items():
                    fid.write(_b("# %s\n" % json.dumps({k: v}).strip("{}")))
            #fid.write(_b("# %s\n" % json.dumps(_toDictItem(self.metadata, convert_bytes=True)).strip("{}")))
            fid.write(_b("# %s\n" % json.dumps({"columns": labels}).strip("{}")))
            filler = np.ones_like(self.Q, dtype='float') * -1.0 * cleaned_metadata[0]["dQv"]
            np.savetxt(fid, np.vstack([self.Q, self.iqCOR.x, np.sqrt(self.iqCOR.variance), filler, filler, filler]).T, fmt="%15.6g")
            fid.seek(0)
            name = _s(cleaned_metadata[0]["Sample file"])
            entry = ""
            value = fid.read()

        return {
            "name": name,
            "entry": "",
            "file_suffix": ".usans.cor",
            "value": value.decode(),
        }

class Parameters(dict):
    def get_metadata(self):
        return _toDictItem(self)

    def get_plottable(self):
        return {"entry": "entry", "type": "metadata", "values": _toDictItem(self)}


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
