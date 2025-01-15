from reductus.dataflow import core as df
from reductus.dataflow.automod import make_modules, make_template, auto_module, get_modules
from reductus.dataflow.calc import process_template
from reductus.dataflow.data import Plottable
from reductus.dataflow.lib.exporters import exports_json

from . import steps
from . import candor_steps
from . import templates
from .refldata import ReflData, PSDData
from .candor import Candor
from .polarization import PolarizationData
from .deadtime import DeadTimeData
from .footprint import FootprintData
from .backgroundfield import BackgroundFieldData

INSTRUMENT = "ncnr.refl"

class FluxData(object):
    def __init__(self, fluxes, total_flux):
        self.fluxes = fluxes
        self.total_flux = total_flux

    def get_metadata(self):
        return {
            "fluxes": self.fluxes,
            "total_flux": self.total_flux
        }

    def get_plottable(self):
        return self.get_metadata()

    @exports_json
    def to_json_text(self):
        return {
            "name": "fluxes",
            "entry": "",
            "file_suffix": ".json",
            "value": self.get_metadata(),
            "compact": False,  # pretty-print result
        }

def make_cached_subloader_module(load_action, prefix=""):
    """
    This assumes that the load_action can be run with a single fileinfo
    in any of the fields of datatype 'fileinfo',
    and collates the results of running them one at a time.
    """
    # Read the module defintion from the docstring
    module_description = auto_module(load_action)
    fields = module_description['fields']
    fileinfo_fields = [f for f in fields if f['datatype'] == 'fileinfo']

    # Tag module ids with prefix
    module_description['name'] += " (cached)"
    mod_id = module_description['id'] = prefix + module_description['id']
    template_def = {
        "name": "loader_template",
        "description": "cached remote loader",
        "modules": [
            {"module": mod_id, "version": "0.1", "config": {}}
        ],
        "wires": [],
        "instrument": INSTRUMENT,
        "version": "0.0"
    }
    template = df.Template(**template_def)

    # Tag each terminal data type with the data type prefix, if it is
    # not already a fully qualified name
    for v in module_description['inputs'] + module_description['outputs']:
        if '.' not in v['datatype']:
            v['datatype'] = prefix + v['datatype']

    def new_action(**kwargs):
        outputs = []
        fileinfos = {}
        for ff in fileinfo_fields:
            fileinfos[ff['id']] = kwargs.pop(ff['id'], [])
            # replace fileinfos with empty lists
            kwargs[ff['id']] = []
        for field_id in fileinfos:
            fileinfo = fileinfos[field_id]
            for fi in fileinfo:
                # put a single fileinfo into the hopper
                kwargs[field_id] = [fi]
                config = {"0": kwargs}
                nodenum = 0
                terminal_id = "output"
                retval = process_template(template, config, target=(nodenum, terminal_id))
                outputs.extend(retval.values)
                # take it back out before continuing the loop(s)
                kwargs[field_id] = []
        return outputs

    new_action.cached = True
    module_description['id'] += ".cached"
    # Define and register the module
    return df.Module(action=new_action, **module_description)

def define_instrument():
    # Define modules
    actions = get_modules(steps) + get_modules(candor_steps)
    modules = make_modules(actions, prefix=INSTRUMENT+'.')
    modules.append(make_cached_subloader_module(steps.super_load, prefix=INSTRUMENT+'.'))
    modules.append(make_cached_subloader_module(steps.ncnr_load, prefix=INSTRUMENT+'.'))
    # Define data types
    refldata = df.DataType(INSTRUMENT+".refldata", ReflData)
    poldata = df.DataType(INSTRUMENT+".poldata", PolarizationData)
    psddata = df.DataType(INSTRUMENT+".psddata", PSDData)
    candordata = df.DataType(INSTRUMENT+".candordata", Candor)
    deadtime = df.DataType(INSTRUMENT+".deadtime", DeadTimeData)
    footprint = df.DataType(INSTRUMENT+".footprint.params", FootprintData)
    flux = df.DataType(INSTRUMENT+".flux.params", FluxData)
    backgroundfield = df.DataType(INSTRUMENT + ".backgroundfield.params", BackgroundFieldData)
    plottable = df.DataType(INSTRUMENT+".plot", Plottable)

    #import json
    #import os
    #from pkg_resources import resource_string, resource_listdir
    #template_names = [fn for fn in resource_listdir('dataflow', 'templates') if fn.endswith(".json")]
    #templates = [json.loads(resource_string('dataflow', 'templates/' + tn)) for tn in template_names]
    #template_path = resource_path("../dataflow/templates")
    #template_names = [fn for fn in os.listdir(template_path) if fn.endswith(".json")]
    #templates = [json.loads(open(os.path.join(template_path, tn), 'r').read()) for tn in template_names]

    # Define instrument
    refl1d = df.Instrument(
        id=INSTRUMENT,
        name='NCNR reflectometer',
        menu=[('steps', modules)],
        datatypes=[
            refldata, poldata, psddata, candordata, deadtime, footprint,
            flux, backgroundfield, plottable,
            ],
        template_defs=df.load_templates(templates),
        )

    # Register instrument
    df.register_instrument(refl1d)
    return refl1d


def loader_template():
    refl1d = df.lookup_instrument(INSTRUMENT)
    diagram = [
        ["ncnr_load", {}],
        ["divergence", {"data": "-.output"}],
    ]
    template = make_template(
        name="loader",
        description="loader only",
        diagram=diagram,
        instrument=refl1d,
        version=1.0,
        )
    return template


def unpolarized_template():
    refl1d = df.lookup_instrument(INSTRUMENT)
    diagram = [
        # Load the data
        ["ncnr_load", {}],

        # Preprocessing common to all data sets
        #["monitor_saturation", {"data": "-.output"}],
        #["detector_saturation", {"data": "-.output"}],
        ["divergence", {"data": "-.output"}],
        ["normalize", {"data": "-.output", "base": "auto"}],
        ["mark_intent", {"data": "-.output", "intent": ["auto"]}],
        ["group_by_intent => split", {"data": "-.output"}],

        # Preprocessing particular to each data type
        # Use nop to restart pipeline after split so that it is easier to
        # add/remove/rearrange steps for the different data types.
        ["nop", {"data": "split.specular"}],
        ["join => spec", {"data": "-.output"}],

        ["nop", {"data": "split.backp"}],
        ["mask_specular", {"data": "-.output"}],
        ["align_background", {"data": "-.output", "offset": "auto"}],
        ["join => backp", {"data": "-.output"}],

        ["nop", {"data": "split.backm"}],
        ["mask_specular", {"data": "-.output"}],
        ["align_background", {"data": "-.output", "offset": "auto"}],
        ["join => backm", {"data": "-.output"}],

        ["nop", {"data": "split.intensity"}],
        ["rescale", {"data": "-.output", "scale": [1.0], "dscale": [0.0]}],
        ["join => intensity", {"data": "-.output", "tolerance": 0.0001}],

        # Operate on the combined data for the final reduction
        ["subtract_background", {
            "data": "spec.output",
            "backp": "backp.output",
            "backm": "backm.output"}],
        ["divide_intensity", {"data": "-.output", "base": "intensity.output"}],
        #["footprint",  {"data": "-.output")}],
    ]
    #for m in refl1d.modules: print m.__dict__
    #for m in refl1d.modules: print m.terminals[0]
    template = make_template(
        name="unpolarized",
        description="standard unpolarized reduction",
        diagram=diagram,
        instrument=refl1d,
        version=1.0,
        )
    return template

def demo():
    from reductus.dataflow.calc import process_template

    template = unpolarized_template()
    #print "========== Template ========"
    #template.show()
    #print "="*24
    test_dataset = [{'path': "ncnrdata/cgd/201511/21066/data/HMDSO_17nm_dry14.nxz.cgd",
                     'mtime': 1447353278}]
    refl = process_template(template=template,
                            config={"0": {"filelist": test_dataset}},
                            target=(len(template.modules)-1, "output"),
                            #target=(2, "data"),  # return an input
                           )
    #print "refl",refl.values
    return refl.values


if __name__ == "__main__":
    from reductus.dataflow.cache import use_redis
    use_redis()
    define_instrument()
    demo()

