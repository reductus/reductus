from dataflow import core as df
from dataflow.automod import make_modules
from dataflow import templates

from vsansred import steps
from vsansred.vsansdata import RawVSANSData, VSansData

INSTRUMENT = "ncnr.vsans"

def define_instrument():
    # Define modules
    modules = make_modules(steps.ALL_ACTIONS, prefix=INSTRUMENT+'.')

    # Define data types
    vsansraw = df.DataType(INSTRUMENT+".raw", RawVSANSData)
    vsansdata = df.DataType(INSTRUMENT+".vsansdata", VSansData)
    #params = df.DataType(INSTRUMENT+".params", Parameters)

    # Define instrument
    vsans = df.Instrument(
        id=INSTRUMENT,
        name='NCNR Very Small Angle Neutron Scattering (VSANS) instrument',
        menu=[('steps', modules)],
        datatypes=[vsansraw, vsansdata], # params],
        template_defs=templates.get_templates(INSTRUMENT),
        )

    # Register instrument
    df.register_instrument(vsans)
    return vsans
