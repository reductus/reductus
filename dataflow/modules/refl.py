from dataflow import core as df

from reflred.steps import steps
from reflred.refldata import ReflData
from reflred.steps.polarization import PolarizationData
from reflred.steps.deadtime import DeadTimeData

INSTRUMENT_PREFIX = "refl1d.ncnr."

# Define modules
modules = df.make_modules(steps.ALL_ACTIONS, prefix=INSTRUMENT_PREFIX)
#for m in modules: print m.id

# Define data types
# Note: retrieving the data loader is more awkward than just using
# steps.ncnr_load because we need the automatic wrapper to turn the
# output list into an output dictionary.
# TODO: actions should return lists rather than dictionaries
loader_name = INSTRUMENT_PREFIX + "ncnr_load"
loader = [m for m in modules if m.id == loader_name][0]
refldata = df.Data(INSTRUMENT_PREFIX+"refldata", ReflData,
                   loaders=[{'function': loader, 'id': 'LoadNeXuS'}])
poldata = df.Data(INSTRUMENT_PREFIX+"poldata", PolarizationData, loaders=[])
deadtime = df.Data(INSTRUMENT_PREFIX+"deadtime", DeadTimeData, loaders=[])

# Define instrument
refl1d = df.Instrument(
    id=INSTRUMENT_PREFIX[:-1],
    name='NCNR reflectometer',
    menu=[('steps', modules)],
    datatypes=[refldata, poldata, deadtime],
    archive="NCNR",
    )

# Register instrument
df.register_instrument(refl1d)


def loader_template():
    from dataflow.core import make_template
    diagram = [
            ["ncnr_load", {}],
            #["divergence", {"data": "-.output"}],
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
    from dataflow.core import make_template
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
    from reflred.steps import load
    load.DATA_SOURCE = "http://ncnr.nist.gov/pub/"

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
    print "refl",refl
    return refl


def demo1():
    from dataflow.calc import process_template
    from reflred.steps import load
    load.DATA_SOURCE = "http://ncnr.nist.gov/pub/"

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


if __name__ == "__main__":
    demo6()

