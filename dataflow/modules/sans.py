from dataflow import core as df
from dataflow.automod import make_modules
from dataflow import templates
from dataflow.lib import exporters

from sansred import steps
from sansred.sansdata import RawSANSData, SansData, Sans1dData, SansIQData, Parameters

INSTRUMENT = "ncnr.sans"

def define_instrument():
    # Define modules
    modules = make_modules(steps.ALL_ACTIONS, prefix=INSTRUMENT+'.')

    # Define data types
    column_export = {
        "columns": {"method_name": "to_column_text", "exporter": exporters.text},
    }
    hdf_and_column_exports = {
        "columns": {"method_name": "to_column_text", "exporter": exporters.text},
        "NXcanSAS": {"method_name": "to_NXcanSAS", "exporter": exporters.hdf},
    }
    sansraw = df.DataType(INSTRUMENT+".raw", RawSANSData)
    sans2d = df.DataType(INSTRUMENT+".sans2d", SansData)
    sans1d = df.DataType(INSTRUMENT+".sans1d", Sans1dData, export_types=column_export)
    sansIQ = df.DataType(INSTRUMENT+".sansIQ", SansIQData, export_types=hdf_and_column_exports)
    params = df.DataType(INSTRUMENT+".params", Parameters)
    #offset_data = df.DataType(INSTRUMENT+".offset_data", dict)

    # Define instrument
    sans = df.Instrument(
        id=INSTRUMENT,
        name='NCNR SANS',
        menu=[('steps', modules)],
        datatypes=[sansraw, sans2d, sans1d, sansIQ, params],
        template_defs=templates.get_templates(INSTRUMENT),
        )

    # Register instrument
    df.register_instrument(sans)
    return sans
