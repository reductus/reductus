from dataflow import core as df
from dataflow.automod import make_modules
from dataflow.lib import exporters
from dataflow import templates

from vsansred import steps
from vsansred.vsansdata import RawVSANSData, VSansDataRealSpace, VSansDataQSpace, Parameters, VSans1dData #, Metadata

INSTRUMENT = "ncnr.vsans"

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
    vsans_raw = df.DataType(INSTRUMENT+".raw", RawVSANSData, export_types=column_export)
    vsans_realspace = df.DataType(INSTRUMENT+".realspace", VSansDataRealSpace)
    vsans_qspace = df.DataType(INSTRUMENT+".qspace", VSansDataQSpace, export_types=hdf_and_column_exports)
    vsans_1d = df.DataType(INSTRUMENT+'.v1d', VSans1dData, export_types=column_export)
    #vsans_metadata = df.DataType(INSTRUMENT+".metadata", Metadata)
    params = df.DataType(INSTRUMENT+".params", Parameters)

    # Define instrument
    vsans = df.Instrument(
        id=INSTRUMENT,
        name='NCNR Very Small Angle Neutron Scattering (VSANS) instrument',
        menu=[('steps', modules)],
        datatypes=[vsans_raw, vsans_realspace, vsans_qspace, params, vsans_1d],
        template_defs=templates.get_templates(INSTRUMENT),
        )

    # Register instrument
    df.register_instrument(vsans)
    return vsans
