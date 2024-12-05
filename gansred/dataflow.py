from dataflow import core as df
from dataflow.automod import make_modules, make_template, auto_module, get_modules
from dataflow.calc import process_template
from dataflow.data import Plottable
from dataflow.lib.exporters import exports_json

from . import steps
from . import templates
from .alignfit import GaussianBackgroundFitResult, LineXInterceptFitResult, ErrorFitResult
from reflred.refldata import ReflData
from reflred.footprint import FootprintData

INSTRUMENT = "gans"

def define_instrument():
    # Define modules
    actions = get_modules(steps)
    modules = make_modules(actions, prefix=INSTRUMENT+'.')
    # Define data types
    refldata = df.DataType(INSTRUMENT+".refldata", ReflData)
    footprint = df.DataType("ncnr.refl.footprint.params", FootprintData)
    errorparams = df.DataType(INSTRUMENT + ".fitters.errorparams", ErrorFitResult)
    gaussianparams = df.DataType(INSTRUMENT + ".fitters.gaussianparams", GaussianBackgroundFitResult)
    linexinterceptparams = df.DataType(INSTRUMENT + ".fitters.linearparams", LineXInterceptFitResult)
    plottable = df.DataType(INSTRUMENT+".plot", Plottable)

    # Define instrument
    gans = df.Instrument(
        id=INSTRUMENT,
        name='GANS',
        menu=[('steps', modules)],
        datatypes=[
            refldata, footprint, plottable, gaussianparams, linexinterceptparams, errorparams
            ],
        template_defs=df.load_templates(templates),
        )

    # Register instrument
    df.register_instrument(gans)
    return gans
