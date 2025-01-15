from reductus.dataflow import core as df
from reductus.dataflow.automod import make_modules, make_template, auto_module, get_modules
from reductus.dataflow.calc import process_template
from reductus.dataflow.data import Plottable
from reductus.dataflow.lib.exporters import exports_json

from . import steps
from . import templates
from reductus.reflred.refldata import ReflData
from reductus.reflred.footprint import FootprintData

INSTRUMENT = "xrr"

def define_instrument():
    # Define modules
    actions = get_modules(steps)
    modules = make_modules(actions, prefix=INSTRUMENT+'.')
    # Define data types
    refldata = df.DataType(INSTRUMENT+".refldata", ReflData)
    footprint = df.DataType("ncnr.refl.footprint.params", FootprintData)
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
