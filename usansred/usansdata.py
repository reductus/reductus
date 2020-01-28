# -*- coding: UTF-8 -*-
from collections import OrderedDict
import datetime
import numpy as np
import json
import io
import sys

IS_PY3 = sys.version_info[0] >= 3

from dataflow.lib.strings import _s, _b

class RawData(object):
    def __init__(self, metadata=None, detCts=None, transCts=None, monCts=None, angle=None):
        self.metadata = metadata
        self.detCts = detCts
        self.transCts = transCts
        self.monCts = monCts
        self.angle = angle

    def todict(self):
        return _toDictItem(self.metadata)

    def get_plottable(self):
        return {"entry": "entry", "type": "metadata", "values": _toDictItem(self.metadata)}

    def get_metadata(self):
        return _toDictItem(self.metadata)

class USansData(RawData):
    def get_plottable(self):
        name = self.metadata.get("run.filename", "")
        entry = ""
        xcol = "angle"
        ycol = "I_det"
        columns = OrderedDict([
            ('angle', {'label': 'angle', 'units': 'degrees'}),
            ('I_det', {'label': 'Counts', 'units': '', 'errorbars': 'dI'}),
            ('I_trans', {'label': 'Transmission Counts', 'units': '', 'errorbars': 'dIt'}),
            ('I_mon', {'label': 'Monitor Counts', 'units': '', 'errorbars': 'dIm'}),
        ])
        datas = {
            "angle": {"values": self.angle.tolist()},
            "I_det": {"values": self.detCts.tolist(), "errorbars": np.sqrt(self.detCts).tolist()},
            "I_trans": {"values": self.transCts.tolist(), "errorbars": np.sqrt(self.transCts).tolist()},
            "I_mon": {"values": self.monCts.tolist(), "errorbars": np.sqrt(self.monCts).tolist()},
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
