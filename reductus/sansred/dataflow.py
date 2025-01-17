from reductus.dataflow import core as df
from reductus.dataflow.automod import make_modules

from . import steps
from . import templates
from .sansdata import RawSANSData, SansData, Sans1dData, SansIQData, Parameters

INSTRUMENT = "ncnr.sans"

def define_instrument():
    # Define modules
    modules = make_modules(steps.ALL_ACTIONS, prefix=INSTRUMENT+'.')

    # Define data types
    sansraw = df.DataType(INSTRUMENT+".raw", RawSANSData)
    sans2d = df.DataType(INSTRUMENT+".sans2d", SansData)
    sans1d = df.DataType(INSTRUMENT+".sans1d", Sans1dData)
    sansIQ = df.DataType(INSTRUMENT+".sansIQ", SansIQData)
    params = df.DataType(INSTRUMENT+".params", Parameters)
    #offset_data = df.DataType(INSTRUMENT+".offset_data", dict)

    # Define instrument
    sans = df.Instrument(
        id=INSTRUMENT,
        name='NCNR SANS',
        menu=[('steps', modules)],
        datatypes=[sansraw, sans2d, sans1d, sansIQ, params],
        template_defs=df.load_templates(templates),
        )

    # Register instrument
    df.register_instrument(sans)
    return sans
