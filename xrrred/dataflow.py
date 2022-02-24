from dataflow import core as df
from dataflow.automod import make_modules, make_template, auto_module, get_modules
from dataflow.calc import process_template
from dataflow.data import Plottable
from dataflow.lib.exporters import exports_json

from . import steps
from . import templates
from reflred.refldata import ReflData
from reflred.footprint import FootprintData

INSTRUMENT = "xrr"

def define_instrument():
    # Define modules
    actions = get_modules(steps)
    modules = make_modules(actions, prefix=INSTRUMENT+'.')
    # Define data types
    refldata = df.DataType(INSTRUMENT+".refldata", ReflData)
    footprint = df.DataType(INSTRUMENT+".footprint.params", FootprintData)
    plottable = df.DataType(INSTRUMENT+".plot", Plottable)

    # Define instrument
    xrr = df.Instrument(
        id=INSTRUMENT,
        name='X-ray reflectometer',
        menu=[('steps', modules)],
        datatypes=[
            refldata, footprint, plottable,
            ],
        template_defs=df.load_templates(templates),
        )

    # Register instrument
    df.register_instrument(xrr)
    return xrr
