from reductus.dataflow import core as df
from reductus.dataflow.automod import make_modules

from . import steps
from . import templates
from .usansdata import RawData, USansData, USansCorData
from reductus.sansred.sansdata import Parameters

INSTRUMENT = "ncnr.usans"

def define_instrument():
    # Define modules
    modules = make_modules(steps.ALL_ACTIONS, prefix=INSTRUMENT+'.')

    # Define data types
    usansraw = df.DataType(INSTRUMENT+".raw", RawData)
    usansdata = df.DataType(INSTRUMENT+".data", USansData)
    usanscor = df.DataType(INSTRUMENT+".cor", USansCorData)
    params = df.DataType(INSTRUMENT+".params", Parameters)

    # Define instrument
    usans = df.Instrument(
        id=INSTRUMENT,
        name='NCNR Ultra-Small Angle Neutron Scattering Instrument (USANS)',
        menu=[('steps', modules)],
        datatypes=[usansdata, params, usanscor], # usansraw],
        template_defs=df.load_templates(templates),
        )

    # Register instrument
    df.register_instrument(usans)
    return usans
