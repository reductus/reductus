from reductus.dataflow import core as df
from reductus.dataflow.automod import make_modules, make_template, auto_module, get_modules
from reductus.dataflow.calc import process_template
from reductus.dataflow.data import Plottable
from reductus.dataflow.lib.exporters import exports_json

from . import steps
from . import templates
from .alignfit import GaussianBackgroundFitResult, LineXInterceptFitResult, ErrorFitResult
from reductus.reflred.refldata import ReflData
from reductus.reflred.footprint import FootprintData
from reductus.reflred.backgroundfield import BackgroundFieldData

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
    backgroundfield = df.DataType("ncnr.refl.backgroundfield.params", BackgroundFieldData)

    # Define instrument
    gans = df.Instrument(
        id=INSTRUMENT,
        name='GANS',
        menu=[('steps', modules)],
        datatypes=[
            refldata, footprint, plottable, gaussianparams, linexinterceptparams, errorparams, backgroundfield
            ],
        template_defs=df.load_templates(templates),
        )

    # Register instrument
    df.register_instrument(gans)
    return gans
