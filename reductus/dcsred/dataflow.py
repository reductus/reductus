from reductus.dataflow import core as df
from reductus.dataflow.automod import make_modules

from . import steps
from . import templates
from .dcsdata import RawData, EQData, DCS1dData, EfTwoThetaData

INSTRUMENT = "ncnr.dcs"

def define_instrument():
    # Define modules
    modules = make_modules(steps.ALL_ACTIONS, prefix=INSTRUMENT+'.')

    # Define data types
    dcsraw = df.DataType(INSTRUMENT+".raw", RawData)
    eqdata = df.DataType(INSTRUMENT+".eq", EQData)
    ef2thetadata = df.DataType(INSTRUMENT+".ef2th", EfTwoThetaData)
    eq1ddata = df.DataType(INSTRUMENT+".eq1d", DCS1dData)
    #params = df.DataType(INSTRUMENT+".params", Parameters)

    # Define instrument
    dcs = df.Instrument(
        id=INSTRUMENT,
        name='NCNR Disk Chopper Spectrometer',
        menu=[('steps', modules)],
        datatypes=[dcsraw, eqdata, eq1ddata, ef2thetadata], # params],
        template_defs=df.load_templates(templates),
        )

    # Register instrument
    df.register_instrument(dcs)
    return dcs
