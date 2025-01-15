from reductus.dataflow import core as df
from reductus.dataflow.automod import get_modules, make_modules, make_template

from . import magik_filters_func as steps
from . import templates
from .FilterableMetaArray import FilterableMetaArray

INSTRUMENT = "ncnr.ospec"

class Parameters(dict):
    def get_metadata(self):
        return self
    def get_plottable(self):
        return {"params": self.get_metadata(), "type": "params"}

def define_instrument():
    # Define modules
    actions = get_modules(steps)
    modules = make_modules(actions, prefix=INSTRUMENT+'.')

    # Define data types
    ospec2d = df.DataType(INSTRUMENT+".ospec2d", FilterableMetaArray)
    #ospec1d = df.DataType(INSTRUMENT+".ospec1d", FilterableMetaArray)
    ospecnd = df.DataType(INSTRUMENT+".ospecnd", FilterableMetaArray)
    params = df.DataType(INSTRUMENT+".params", Parameters)
    #offset_data = df.DataType(INSTRUMENT+".offset_data", dict)

    # Define instrument
    ospec = df.Instrument(
        id=INSTRUMENT,
        name='NCNR offspecular',
        menu=[('steps', modules)],
        datatypes=[ospec2d, ospecnd, params],
        template_defs=df.load_templates(templates),
        )

    # Register instrument
    df.register_instrument(ospec)
    return ospec


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
        ["mask_specular",  {"data": "-.output"}],
        ["align_background",  {"data": "-.output", "offset": "auto"}],
        ["join => backp",  {"data": "-.output"}],

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
    #print "refl", refl.values
    return refl.values


if __name__ == "__main__":
    from reductus.dataflow.cache import use_redis
    use_redis()
    define_instrument()
    demo()

