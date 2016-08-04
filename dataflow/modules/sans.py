from dataflow import core as df
from dataflow.automod import make_modules
from dataflow import templates

from sansred import steps
from sansred.sansdata import SansData

INSTRUMENT = "ncnr.sans"

class Parameters(dict):
    def get_metadata(self):
        return self
    def get_plottable(self):
        return self

def define_instrument():
    # Define modules
    modules = make_modules(steps.ALL_ACTIONS, prefix=INSTRUMENT+'.')

    # Define data types
    sans2d = df.DataType(INSTRUMENT+".sans2d", SansData)
    #ospec1d = df.DataType(INSTRUMENT+".ospec1d", FilterableMetaArray)
    params = df.DataType(INSTRUMENT+".params", Parameters)
    #offset_data = df.DataType(INSTRUMENT+".offset_data", dict)
    
    # Define instrument
    sans = df.Instrument(
        id=INSTRUMENT,
        name='NCNR SANS',
        menu=[('steps', modules)],
        datatypes=[sans2d], # params],
        template_defs = templates.get_templates(INSTRUMENT),
        )

    # Register instrument
    df.register_instrument(sans)
    return sans
