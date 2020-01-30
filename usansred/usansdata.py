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
