import datetime
from copy import copy, deepcopy
import StringIO
import json

import numpy as np

from dataflow.lib.uncertainty import Uncertainty

IGNORE_CORNER_PIXELS = True

class SansData(object):
    """SansData object used for storing values from a sample file (not div/mask).
       Stores the array of data as a Uncertainty object (detailed in uncertainty.py)
       Stores all metadata
       q, qx, qy, theta all get updated with values throughout the reduction process
       Tsam and Temp are just used for storage across modules (in wireit)
    """
    def __init__(self, data=None, metadata=None, q=None, qx=None, qy=None,
                 theta=None, Tsam=None, Temp=None, attenuation_corrected=False):
        if isinstance(data, np.ndarray):
            self.data = Uncertainty(data, data)
        else:
            self.data = data
        self.metadata = metadata
        # There are many places where q was not set, i think i fixed most,
        # but there might be more; be wary
        self.q = q
        self.qx = qx
        self.qy = qy
        self.theta = theta
        self.attenuation_corrected = attenuation_corrected

        self.Tsam = None #Tsam and Temp are used to store the transmissions for later use
        self.Temp = None
    # Note that I have not defined an inplace subtraction
    def __sub__(self, other):
        result = self.copy()
        if isinstance(other, SansData):
            result.data = self.data - other.data
        else:
            result.data = self.data - other
        return result
    # Actual subtraction
    def __sub1__(self, other):
        result = self.copy()
        if isinstance(other, SansData):
            result.data = self.data - other.data
        else:
            result.data = self.data - other
        return result
    def __add__(self, other):
        result = self.copy()
        if isinstance(other, SansData):
            result.data = self.data + other.data
        else:
            result.data = self.data + other
        return result
    def __rsub__(self, other):
        result = self.copy()
        result.data = other - self.data
        return result
    def __truediv__(self, other):
        result = self.copy()
        if isinstance(other, SansData):
            result.data = self.data/other.data
        else:
            result.data = self.data/other
        return result
    def __mul__(self, other):
        result = self.copy()
        if isinstance(other, SansData):
            result.data = self.data * other.data
        else:
            result.data = self.data * other
        return result

    def copy(self):
        return SansData(copy(self.data), deepcopy(self.metadata),
                        q=copy(self.q), qx=copy(self.qx), qy=copy(self.qy),
                        theta=copy(self.theta),
                        attenuation_corrected=self.attenuation_corrected)

    def __copy__(self):
        return self.copy()

    #def __str__(self):
        #return self.data.x.__str__()
    #def __repr__(self):
        #return self.__str__()

    def get_plottable(self):
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
            xmin = 0
            xmax = 128
            ymin = 0
            ymax = 128
            xlabel = "X"
            ylabel = "Y"
        else:
            xmin = self.qx.min()
            xmax = self.qx.max()
            ymin = self.qy.min()
            ymax = self.qy.max()
            xlabel = "Qx (inv. Angstroms)"
            ylabel = "Qy (inv. Angstroms)"
        plottable_data = {
            'type': '2d',
            'z':  [data.T.tolist()],
            'title': self.metadata['run.filename']+': ' + self.metadata['sample.labl'],
            #'metadata': self.metadata,
            'options': {
                'fixedAspect': {
                    'fixAspect': True,
                    'aspectRatio': 1.0
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
            'xlabel': xlabel,
            'ylabel': ylabel,
            'zlabel': 'Intensity (I)',
        }
        return plottable_data

    def get_metadata(self):
        metadata = {}
        metadata.update(self.metadata)
        metadata['plottable'] = self.get_plottable()
        return metadata

    def dumps(self):
        return pickle.dumps(self)

    @classmethod
    def loads(cls, str):
        return pickle.loads(str)

class Sans1dData(object):
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

    def todict(self):
        obj = self
        props = {}
        properties = self.properties
        for a in properties:
            attr = getattr(obj, a)
            if isinstance(attr, np.integer):
                obj = int(attr)
            elif isinstance(attr, np.floating):
                attr = float(attr)
            elif isinstance(attr, np.ndarray):
                attr = attr.tolist()
            elif isinstance(attr, datetime.datetime):
                attr = [attr.year, attr.month, attr.day,
                        attr.hour, attr.minute, attr.second]
            props[a] = attr
        return props

    def get_plottable(self):
        return self.todict()

    def get_metadata(self):
        return self.todict()

    def export(self):
        fid = StringIO.StringIO()
        fid.write("# %s\n" % json.dumps(self.metadata).strip("{}"))
        columns = {"columns": [self.xlabel, self.vlabel, "uncertainty", "resolution"]}
        units = {"units": [self.xunits, self.vunits, self.vunits, self.xunits]}
        fid.write("# %s\n" % json.dumps(columns).strip("{}"))
        fid.write("# %s\n" % json.dumps(units).strip("{}"))
        np.savetxt(fid, np.vstack([self.x, self.v, self.dv, self.dx]).T, fmt="%.10e")
        fid.seek(0)
        name = getattr(self, "name", "default_name")
        entry = getattr(self.metadata, "entry", "default_entry")
        return {"name": name, "entry": entry, "export_string": fid.read()}

class Parameters(dict):
    def get_metadata(self):
        return self

    def get_plottable(self):
        return self
