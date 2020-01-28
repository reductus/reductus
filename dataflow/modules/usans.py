from dataflow import core as df
from dataflow.automod import make_modules
from dataflow import templates

from usansred import steps
from usansred.usansdata import RawData, USansData

INSTRUMENT = "ncnr.usans"

def define_instrument():
    # Define modules
    modules = make_modules(steps.ALL_ACTIONS, prefix=INSTRUMENT+'.')

    # Define data types
    usansraw = df.DataType(INSTRUMENT+".raw", RawData)
    usansdata = df.DataType(INSTRUMENT+".data", USansData)
    #params = df.DataType(INSTRUMENT+".params", Parameters)

    # Define instrument
    usans = df.Instrument(
        id=INSTRUMENT,
        name='NCNR Ultra-Small Angle Neutron Scattering Instrument (USANS)',
        menu=[('steps', modules)],
        datatypes=[usansdata], #, usansraw], # params],
        template_defs=templates.get_templates(INSTRUMENT),
        )

    # Register instrument
    df.register_instrument(usans)
    return usans
