from dataflow import core as df

from reflred.steps import steps
from reflred.steps import load
from reflred.refldata import ReflData
from reflred.steps.polarization import PolarizationData
from reflred.steps.deadtime import DeadTimeData

INSTRUMENT = "ncnr.refl"



def define_instrument(data_source):
    # Set the data source
    load.DATA_SOURCE = data_source

    # Define modules
    modules = df.make_modules(steps.ALL_ACTIONS, prefix=INSTRUMENT+'.')

    # Define data types
    refldata = df.DataType(INSTRUMENT+".refldata", ReflData)
    poldata = df.DataType(INSTRUMENT+".poldata", PolarizationData)
    deadtime = df.DataType(INSTRUMENT+".deadtime", DeadTimeData)

    import json
    import os
    from unpolarized_template import template
    # Define instrument
    refl1d = df.Instrument(
        id=INSTRUMENT,
        name='NCNR reflectometer',
        menu=[('steps', modules)],
        datatypes=[refldata, poldata, deadtime],
        archive="NCNR",
        template_defs = [template],
        )

    # Register instrument
    df.register_instrument(refl1d)
    return refl1d


def loader_template():
    from dataflow.core import make_template, lookup_instrument
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
    from dataflow.core import make_template, lookup_instrument
    refl1d = lookup_instrument(INSTRUMENT)
    diagram = [
        # Load the data
        ["ncnr_load", {}],

        # Preprocessing common to all data sets
        #["monitor_saturation", {"data": "-.output"}],
        #["detector_saturation", {"data": "-.output"}],
        ["divergence", {"data": "-.output"}],
        ["normalize", {"data": "-.output", "base": "auto"}],
        ["mark_intent", {"data": "-.output", "intent": "auto"}],
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
        ["rescale",  {"data": "-.output", "scale": 1.0, "dscale": 0.0}],
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

def demo6():
    from dataflow.calc import process_template

    template = unpolarized_template()
    #print "========== Template ========"
    #template.show()
    #print "="*24
    test_dataset = [{'path': "ncnrdata/cgd/201511/21066/data/HMDSO_17nm_dry14.nxz.cgd",
                     "mtime": 1447353278}]
    experiment = "ncnrdata/cgd/201511/21066/data/"
    ext = '.nxz.cgd'
    datasets = ["..."]
    #files = [{'path':experiment+f+ext,'mtime':0} for f in datasets]
    files = test_dataset
    refl = process_template(template=template,
                            config={"0": {"filelist": test_dataset}},
                            target=(len(template.modules)-1, "output"))
    print "refl",refl.values
    return refl.values


def demo1():
    from dataflow.calc import process_template

    template = loader_template()
    #print "========== Template ========"
    #template.show()
    #print "="*24
    test_dataset = [{'path': "ncnrdata/cgd/201511/21066/data/HMDSO_17nm_dry14.nxz.cgd",
                     "mtime": 1447353278}]
    experiment = "ncnrdata/cgd/201511/21066/data/"
    ext = '.nxz.cgd'
    datasets = ["..."]
    #files = [{'path':experiment+f+ext,'mtime':0} for f in datasets]
    files = test_dataset
    print "ready"
    refl = process_template(template=template,
                            config={"0": {"filelist": test_dataset}},
                            #target=(len(template.modules)-1, "output"),
                            target=(0, "output"),
                            )
    print "refl",refl
    return refl


def demo7():
    from dataflow.core import Template
    from dataflow.calc import process_template
    from unpolarized_template import template as template_def
    define_instrument(data_source="http://ncnr.nist.gov/pub/")
    template = Template("unpolarized", "reflweb default unpolarized template", modules=template_def['modules'], wires=template_def['wires'], instrument="ncnr.magik", version=1.0)
    test_dataset = [{'path': "ncnrdata/cgd/201511/21066/data/HMDSO_17nm_dry14.nxz.cgd",
                     "mtime": 1447353278}]
    files = test_dataset
    template_config = {"0": {"filelist": test_dataset}, "1": {"mask_indices": {"0": [1,2]}}}
    #for i in range(len(template_def['modules'])):
    #    if not str(i) in template_config:
    #        template_config[str(i)] = {}
    #    template_config[str(i)]['version'] = '1.0'
    #print template_config
    refl = process_template(template=template,
                            config=template_config,
                            target=(0, "output"))
    print "refl",refl.values
    return refl.values

if __name__ == "__main__":
    from dataflow.cache import use_redis
    use_redis()
    define_instrument(data_source="http://ncnr.nist.gov/pub/")
    demo6()

