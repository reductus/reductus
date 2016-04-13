from dataflow import core as df
from dataflow.automod import make_modules
from dataflow import templates

from reflred.steps import steps
from reflred.steps import load
from reflred.refldata import ReflData
from reflred.steps.polarization import PolarizationData
from reflred.steps.deadtime import DeadTimeData

INSTRUMENT = "ncnr.refl"

class DataflowReflData(ReflData):
    """ 
    This doesn't work because on first load, the class is still ReflData from nexusref
    (only becomes DataFlowReflData on cache/reload)
    """
    def get_plottable_JSON(self):
        plottable = {
            'axes': {
                'xaxis': {'label': self.xlabel + ' (' + self.xunits + ')'},
                'yaxis': {'label': self.vlabel + ' (' + self.vunits + ')'}
            },
            'data': [[x,y,{'yupper': y+dy, 'ylower':y-dy,'xupper':x,'xlower':x}] for x,y,dy in zip(self.x, self.v, self.dv)],
            'title': self.name + ":" + self.entry
        }
        return plottable

    def get_plottable(self):
        return self.todict()
    def get_metadata(self):
        return self.todict()

def define_instrument():
    # Define modules
    modules = make_modules(steps.ALL_ACTIONS, prefix=INSTRUMENT+'.')

    # Define data types
    refldata = df.DataType(INSTRUMENT+".refldata", ReflData)
    poldata = df.DataType(INSTRUMENT+".poldata", PolarizationData)
    deadtime = df.DataType(INSTRUMENT+".deadtime", DeadTimeData)

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
        datatypes=[refldata, poldata, deadtime],
        template_defs = templates.get_templates(),
        )

    # Register instrument
    df.register_instrument(refl1d)
    return refl1d


def loader_template():
    from dataflow.automod import make_template
    from dataflow.core import lookup_instrument
    refl1d = lookup_instrument(INSTRUMENT)
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
    from dataflow.automod import make_template
    from dataflow.core import lookup_instrument
    refl1d = lookup_instrument(INSTRUMENT)
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
        ["mask_specular",  {"data": "-.output"}],
        ["align_background",  {"data": "-.output", "offset": "auto"}],
        ["join => backp",  {"data": "-.output"},],

        ["nop", {"data": "split.backm"}],
        ["mask_specular",  {"data": "-.output"}],
        ["align_background",  {"data": "-.output", "offset": "auto"}],
        ["join => backm",  {"data": "-.output"}],

        ["nop", {"data": "split.intensity"}],
        ["rescale",  {"data": "-.output", "scale": [1.0], "dscale": [0.0]}],
        ["join => intensity",  {"data": "-.output", "tolerance": 0.0001}],

        # Operate on the combined data for the final reduction
        ["subtract_background", {
            "data": "spec.output",
            "backp": "backp.output",
            "backm": "backm.output"}],
        ["divide_intensity",  {"data": "-.output", "base": "intensity.output"}],
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
    from dataflow.calc import process_template

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
    from dataflow.cache import use_redis
    use_redis()
    define_instrument()
    demo()

