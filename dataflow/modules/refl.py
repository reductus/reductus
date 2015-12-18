from dataflow import core as df

from reflred.steps import steps
from reflred.refldata import ReflData
from reflred.steps.polarization import PolarizationData
from reflred.steps.deadtime import DeadTimeData

DATA_SOURCE = "http://ncnr.nist.gov/pub/"
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
    id='ncnr.refl1d',
    name='NCNR reflectometer',
    menu=[('steps', modules)],
    datatypes=[refldata, poldata, deadtime],
    archive=DATA_SOURCE,
    )

# Register instrument
df.register_instrument(refl1d)


def test():
    from dataflow.core import Template
    from dataflow.calc import calc_single
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

if __name__ == "__main__":
    test()