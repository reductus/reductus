from collections import OrderedDict
import datetime

import numpy as np

from .lib.exporters import exports_json

def todict(obj, convert_bytes=False):
    if isinstance(obj, np.integer):
        obj = int(obj)
    elif isinstance(obj, np.floating):
        obj = float(obj)
    elif isinstance(obj, np.ndarray):
        obj = obj.tolist()
    elif isinstance(obj, datetime.datetime):
        obj = [obj.year, obj.month, obj.day, obj.hour, obj.minute, obj.second]
    elif isinstance(obj, (list, tuple)):
        obj = [todict(a, convert_bytes=convert_bytes) for a in obj]
    elif isinstance(obj, (dict, OrderedDict)):
        obj = OrderedDict([(k, todict(v, convert_bytes=convert_bytes))
                           for k, v in obj.items()])
    elif isinstance(obj, bytes) and convert_bytes:
        obj = obj.decode()
    return obj

class Parameters(OrderedDict):
    """
    Untyped parameter object for passing information between modules.

    The source can create the data object using::

        data = Parameters(key=value, ...)

    The target can reference the data object using::

        value = data.key
        value = data['key']

    The order of the key-value pairs will be preserved, and may be displayed
    in that order when the output node is in focus. A key or attribute error
    will be raised if you do not, depending which form you use to access the
    data object.

    If used directly, your modules will need to check that the correct
    data has been passed from the source to the target.

    Alternatively, using a trivial subclass you can provide a typed link
    that will only accept connections from the correct outputs to the
    correct inputs in your graph template.  In your instrument definition
    do the following::

        from reductus.dataflow.data import Parameters
        import dataflow.core as df

        INSTRUMENT = 'ncnr.refl'
        class DeadtimeData(Parameters):
            pass
        deadtime = df.DataType(INSTRUMENT+'.deadtime', DeadtimeData)
        refl1d = df.Instrument(
            id=INSTRUMENT,
            ...
            datatype=[..., deadtime],
        )
        df.register_instrument(refl1d)

    Note: as of python 3.6, the order of the arguments given in the
    constructor will be preserved in the ordered dictionary.
    """
    def get_metadata(self):
        return todict(self)

    def get_plottable(self):
        return {"entry": "entry", "type": "params", "params": todict(self)}

    # For compatibility with existing Parameters objects in sansred, etc.
    @property
    def params(self):
        return self

    # Allow dot-notation to access fields
    def __getattr__(self, name):
        if name in self:
            return self[name]
        raise AttributeError("Name '{name}' is not {self.__class__.__name__}".format(name=name, self=self))

    @exports_json("json")
    def to_json_text(self):
        return {
            "name": getattr(self, "name", self.__class__.__name__),
            #"entry": getattr(self, "entry", "default_entry"),
            "file_suffix": ".json",
            "value": todict(self, convert_bytes=True),
        }

class Plottable:
    """
    Simple class for plotting output that isn't passed from node to node.

    *layout* is an arbitrary plottable.  layout['title'] should be of the
    form "name:entry" in case the user wants to save the output as a json
    structure rather than exporting svg or png.
    """
    def __init__(self, layout):
        self.layout = layout

    def get_metadata(self):
        # Not sure what this is for...
        return todict(self.layout)

    def get_plottable(self):
        return todict(self.layout)

    @exports_json("json")
    def to_json_text(self):
        title = self.layout.get("title", "name:entry")
        name, entry = title.split(':', 1) if ':' in title else (title,"entry")
        return {
            "name": name,
            "entry": entry,
            "file_suffix": ".plot.json",
            "value": todict(self.layout),
        }
