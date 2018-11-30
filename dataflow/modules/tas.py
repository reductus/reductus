from dataflow import core as df
from dataflow.automod import make_modules
from dataflow import templates

from tasred import steps
from tasred.readncnr5 import datareader
INSTRUMENT = "ncnr.tas"

def define_instrument():
    # Define modules
    modules = make_modules(steps.ALL_ACTIONS, prefix=INSTRUMENT+'.')

    # Define data types
    tasraw = df.DataType(INSTRUMENT+".raw", datareader)
    #params = df.DataType(INSTRUMENT+".params", Parameters)

    # Define instrument
    tas = df.Instrument(
        id=INSTRUMENT,
        name='NCNR Triple Axis',
        menu=[('steps', modules)],
        datatypes=[tasraw], # params],
        template_defs=templates.get_templates(INSTRUMENT),
        )

    # Register instrument
    df.register_instrument(tas)
    return tas
