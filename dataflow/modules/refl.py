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


def demo():
    from dataflow.core import Template
    from dataflow.calc import calc_single
    from reflred.steps import load
    load.DATA_SOURCE = "http://ncnr.nist.gov/pub/"

    test_dataset = [{'path': "ncnrdata/cgd/201511/21066/data/HMDSO_17nm_dry14.nxz.cgd",
                     "mtime": 1447353278}]
    # join data source to path within data source for full urls
    for d in test_dataset:
        d['path'] = refl1d.archive + d['path']
    import numpy; numpy.seterr(all='raise')
    modules = [{"module": "refl1d.ncnr.ncnr_load", "version": 0.1, "config": {}}]
    template = Template("test", "test template", modules, [],
                           "ncnr.magik", version='0.0')
    refl = calc_single(template, {"0": {"filelist": test_dataset}}, 0, "output")
    return refl

def unpolarized_template():
    from dataflow.core import make_template
    diagram = [
        # Load the data
        ["ncnr_load", {}],

        # Preprocessing common to all data sets
        ["monitor_saturation", {"data": "-.output"}],
        ["detector_saturation", {"data": "-.output"}],
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

        ["nop", {"data": "split.slit"}],
        ["rescale",  {"data": "-.output", "scale": 1.0, "dscale": 0.0}],
        ["join => slit",  {"data": "-.output", "tolerance": 0.0001}],

        # Operate on the combined data for the final reduction
        ["subtract_background", {
            "data": "spec.output",
            "backp": "backp.output",
            "backm": "backm.output"}],
        ["divide_intensity",  {"data": "-.output", "base": "slit.output"}],
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
    from dataflow.calc import calc_single
    from reflred.steps import load
    load.DATA_SOURCE = "http://ncnr.nist.gov/pub/"

    template = unpolarized_template()
    print template
    test_dataset = [{'path': "ncnrdata/cgd/201511/21066/data/HMDSO_17nm_dry14.nxz.cgd",
                     "mtime": 1447353278}]
    experiment = "ncnrdata/cgd/201511/21066/data/"
    ext = '.nxz.cgd'
    datasets = ["..."]
    #files = [{'path':experiment+f+ext,'mtime':0} for f in datasets]
    files = test_dataset
    refl = calc_single(template=template,
                       config={"0": {"filelist": test_dataset}},
                       nodenum=len(template.modules)-1, terminal_id="output")
    return refl


if __name__ == "__main__":
    demo()


"""
def demo2():
    experiment = "ncnrdata/cgd/201511/21066/data/"
    files = []
    template = Template()
    template.chain(refl1d.load())
    template.chain(refl1d.monitor_saturation())
    template.chain(refl1d.detector_saturation())
    template.chain(refl1d.divergence())
    template.chain(refl1d.normalize(base='auto'))
    template.chain(refl1d.mark_intent(intent='auto'))
    s = template.chain(refl1d.split())
    background_prep = Template()
    background_prep.chain(relf1d.mask_specular())
    background_prep.chain(refl1d.align_background(offset='auto'))

    # ...

def demo3():
    r = refl1d
    T = Template()

    T |= (
        ["load",  {)}]
        | r.monitor_saturation()
        | r.detector_saturution()
        | r.divergence()
        | r.normalize(base='auto')
        | r.mark_intent(intent='auto')
        | r.split()
    )
    T.specular |= (
        r.join()
    )
    T.backp |= (
        r.mask_specular()
        | r.align_background('auto')
        | r.join()
    )
    T.backm |= (
        r.mask_specular()
        | r.align_background('auto')
        | r.join()
    )
    T.slits |= (
        r.rescale(scale=1.0, dscale=0.0)
        | r.join(tolerance=0.0001)
    )
    T.specular |= (
        r.subtract_background(backp=T.backp, backm=T.backm)
        | r.divide_intensity(base=T.slits)
    )


def demo4():
    prep = groupby(
        field='intent',
        data=mark_intent(
            data=normalize(
                data=divergence(
                    data=detector_saturation(
                        data=monitor_saturation(
                            data=load(
                            ).output,
                        ).output,
                    ).output,
                ).output,
            ).output,
        ).output,
    )
    T = footprint(
            data=divide_intensity(
                data=subtract_background(
                    data=join(
                        data=prep.specular
                        ).output,
                    backp=join(
                        data=align_background(
                            offset='auto',
                            data=mask_specular(
                                data=prep.backp
                                ).output,
                            ).output,
                        ).output,
                    backm=join(
                        data=align_background(
                            offset='auto',
                            data=mask_specular(
                                data=prep.backp
                                ).output,
                            ).output,
                        ).output,
                    ),
                base=join(
                    tolerance=0.0001,
                    data=rescale(
                        scale=1.0,
                        dscale=0.0,
                        ).output
                    ).output,
                ).output,
            )

def demo5():
    from dataflow.calc import calc_single
    from dataflow.core import make_template
    r = refl1d.modules
    modules = [
        r.ncnr_load(),
        r.monitor_saturation(data='-.output'),
        r.detector_saturution(data='-.output'),
        r.divergence(data='-.output'),
        r.normalize(data='-.output', base='auto'),
        r.mark_intent(data='-.output', intent='auto'),
        r.group_by_intent(data='-.output').id('split'),

        r.join(data='split.specular').id('spec'),

        r.mask_specular(data='split.backp'),
        r.align_background(data='-.output', base='auto'),
        r.join(data='-.output').id('backp'),

        r.mask_specular(data='split.backm'),
        r.align_background(data='-.output', base='auto'),
        r.join(data='-.output').id('backm'),

        r.rescale(data='split.slit', scale=1.0, dscale=0.0),
        r.join(data='-.output', tolerance=0.0001).id('slit'),

        r.subtract_background(data='spec.output',
                              backp='backp.output',
                              backm='backm.output'),
        r.divide_intensity(data='-.output',
                           base='slit.output'),
        #r.footprint(data='-.output'),
    ]
    template = make_template(
        name="unpolarized",
        description="standard unpolarized reduction",
        modules=modules,
        instrument=refl1d,
        version=1.0)

    experiment = "ncnrdata/cgd/201511/21066/data/"
    ext = '.nxz.cgd'
    datasets = ["..."]
    files = [{'path':experiment+f+ext,'mtime':0} for f in datasets]
    refl = calc_single(template=template,
                       config=[("ncnr_load.filelist", files)],
                       target="footprint.output")
    return refl
"""

