"""
Load data sets.
"""
from reflred.formats import nexusref
from reflred.steps import steps

from dataflow.core import Module

test_dataset = [
  #{'path': "ncnrdata/cgd/201511/21066/data/HMDSO_17nm_dry14.nxz.cgd", "mtime": 1447353278},
  #{'path': "ncnrdata/cgd/201511/21066/data/HMDSO_17nm_dry15.nxz.cgd", "mtime": 1447353664},
  #{'path': "ncnrdata/cgd/201511/21066/data/HMDSO_17nm_dry16.nxz.cgd", "mtime": 1447354137},
  {'path': "ncnrdata/cgd/201511/21066/data/HMDSO_50w_45nm160.nxz.cgd", "mtime": 1447562764},
  {'path': "ncnrdata/cgd/201511/21066/data/HMDSO_50w_45nm159.nxz.cgd", "mtime": 1447551474},
  {'path': "ncnrdata/cgd/201511/21066/data/HMDSO_50w_45nm158.nxz.cgd", "mtime": 1447548245}
]
DATA_SOURCE = "http://ncnr.nist.gov/pub/"

class FileNewerError(Exception):
    def __str__(self):
        return "File mtime specified is newer than the one in the repository: " + Exception.__str__(self) 

class FileOlderError(Exception):
    def __str__(self):
        return "File mtime specified is older than the one in the repository: " + Exception.__str__(self) 

def load_action(files=[], **kwargs):
    print "loading saved results"
    #import tarfile
    #from ...apps.tracks.models import File
    import urllib2, StringIO, datetime, pytz
    result = []
    for f in files:
        print 'f: ', f
        try:
            fp = urllib2.urlopen(DATA_SOURCE + f['path'])
            fn = f['path'].split("/")[-1]
            mtime = fp.info().getdate('last-modified')
            cm = datetime.datetime(*mtime[:7], tzinfo=pytz.utc)
            fm = datetime.datetime.fromtimestamp(f['mtime'], pytz.utc)
            if fm < cm:
                raise FileNewerError()
            elif fm > cm:
                raise FileOlderError()
            else:
                #get it!
                ff = StringIO.StringIO(fp.read())
                nx_entries = nexusref.load_entries(fn, ff)
                result.extend(nx_entries)
                ff.close()
            fp.close()
        except urllib2.HTTPError:
            print("couldn't open file")
        
        
        #fn = Fileobj.name
        #cls = lookup_datatype(Fileobj.datatype).cls

        #fn = Fileobj.name
        #fp = Fileobj.location
        #tf = tarfile.open(os.path.join(fp, fn), 'r:gz')
        #result_objs = [tf.extractfile(member) for member in tf.getmembers()]
        #result.extend([cls.loads(robj.read()) for robj in result_objs])        
        #result = [cls.loads(str) for str in server.lrange(terminal_fp, 0, -1)]
        #fp = Fileobj.location
        #read_here = os.path.join(fp, fn)
        #result_str = gzip.open(read_here, 'rb').read()
        #result.append(cls.loads(result_str))
    #result = [FilterableMetaArray.loads(robj.read()) for robj in result_objs]
    return dict(output=result)

load_kw = {
    "id": "ncnr.refl.load",
    "version": "0.1",
    "description": "load reflectometry NeXus files",
    "outputs": [
        {
            "id": "output", 
            "datatype": "ncnr.refl.data",
            "use": "out",
            "description": "data",
            "multiple": True
        }
    ],
    "fields": {
        "files": {
            "type":"files",
            "label": "Files",
            "name": "files",
            "value": []
        }
    },
    "action": load_action,
    "name": "Load NeXuS Reflectometry Data"
    
}

load_module = Module(**load_kw)

def mask_action(input=None, mask_indices=None, **kwargs):
    """ take sparse index lists for masking
    e.g. mask_indices = {"0": [1,4,6], "5": [0]}
    operates to put masks on data items 0 and 5
    """
    if hasattr(input, '__iter__') and hasattr(mask_indices, '__contains__') :
        import numpy 
        for i, data in enumerate(input):
            data.mask = numpy.ones(data.detector.counts.shape, dtype="bool")
            if str(i) in mask_indices:
                for j in mask_indices[str(i)]:
                    data.mask[j] = False
    return dict(output=input)
    
mask_kw = {
    "id": "ncnr.refl.mask",
    "version": "0.1",
    "description": "mask reflectometry NeXus files",
    "outputs": [
        {
            "id": "output", 
            "datatype": "ncnr.refl.data",
            "use": "out",
            "description": "masked data",
            "multiple": True
        },
    ],
    "inputs": [
        {
            "id": "input",
            "datatype": "ncnr.refl.data",
            "use": "in",
            "description": "unmasked data",
            "multiple": True,
            "required": True
        }        
    ],
    "fields": {
        "base": {
            "type":"string",
            "label": "base",
            "name": "base",
            "value": "auto"
        }
    },
    "action": mask_action,
    "name": "Load NeXuS Reflectometry Data"
    
}

mask_module = Module(**mask_kw)

def normalize_action(input=None, base='auto'):
    from reflred.steps import scale
    for data in input:
        scale.apply_norm(data, base)
    return dict(output=input)
    
normalize_kw = {
    "id": "ncnr.refl.normalize",
    "version": "0.1",
    "description": "normalize reflectometry NeXus files",
    "outputs": [
        {
            "id": "output", 
            "datatype": "ncnr.refl.data",
            "use": "out",
            "description": "normalized data",
            "multiple": True,            
        },
    ],
    "inputs": [
        {
            "id": "input",
            "datatype": "ncnr.refl.data",
            "use": "in",
            "description": "unnormalized data",
            "multiple": True,
            "required": True
        }        
    ],
    "fields": {
        "base": {
            "type":"string",
            "label": "base",
            "name": "base",
            "value": "auto"
        }
    },
    "action": normalize_action,
    "name": "Normalize NeXuS Reflectometry Data"
    
}

normalize_module = Module(**normalize_kw)

def join_action(input=None, tolerance=0.0):
    from reflred.steps import joindata
    return dict(output=joindata.join_datasets(input, tolerance))
    
join_kw = {
    "id": "ncnr.refl.join",
    "version": "0.1",
    "description": "join reflectometry NeXus files",
    "outputs": [
        {
            "id": "output", 
            "datatype": "ncnr.refl.data",
            "use": "out",
            "description": "joined data"
        },
    ],
    "inputs": [
        {
            "id": "input",
            "datatype": "ncnr.refl.data",
            "use": "in",
            "description": "source data"
        }        
    ],
    "fields": {
        "tolerance": {
            "type":"number",
            "label": "tolerance",
            "name": "tolerance",
            "value": 0.0
        }
    },
    "action": join_action,
    "name": "join NeXuS Reflectometry Data"
    
}

join_module = Module(**join_kw)



"""
modules : [TemplateModule]

Modules used in the template
module : string
module id for template node

version : string

version number of the module

config : map
initial values for the fields
position : [int,int]
location of the module on the canvas.
"""

def test():
    import numpy; numpy.seterr(all='raise')
    from dataflow.core import register_module, register_datatype, Template, DataType
    from dataflow.calc import process_template
    from reflred.refldata import ReflData
    rdata = DataType("ncnr.refl.data", ReflData, loaders=[{'function':load_action, 'id':'LoadNeXuS'}])
    register_module(load_module)
    register_module(normalize_module)
    register_module(join_module)
    register_module(mask_module)
    register_datatype(rdata)
    # a = load_action(files=test_dataset)
    #modules = [{"module": "ncnr.refl.load", "version": 0.1, "config": {"files": test_dataset}}]
    modules = [
        {"module": "ncnr.refl.load", "version": "0.1", "config": {}},
        {"module": "ncnr.refl.mask", "version": "0.1", "config": {}},
        {"module": "ncnr.refl.join", "version": "0.1", "config": {}}
    ]
    wires = [
        {"source": [0,"output"], "target": [1,"input"]},
        {"source": [1,"output"], "target": [2,"input"]},
    ]
    template = Template("test", "test template", modules, wires, "ncnr.magik", version='0.0')
    refl = process_template(template, {"0": {"files": test_dataset}, "1": {"mask_indices": {"0": [0,-1]}}}, target=(1, "output"))
    return refl

def test2():
    from dataflow.core import register_module, register_datatype, Template, DataType
    #from dataflow.cache import use_redis
    #use_redis()
    from dataflow import core as df
    from dataflow.calc import process_template
    from reflred.steps import load, steps
    load.DATA_SOURCE = "http://ncnr.nist.gov/pub/"
    from reflred.refldata import ReflData
    INSTRUMENT_PREFIX = "ncnr.refl."

    modules = df.make_modules(steps.ALL_ACTIONS, prefix=INSTRUMENT_PREFIX)
    loader_name = INSTRUMENT_PREFIX + "ncnr_load"
    loader = [m for m in modules if m.id == loader_name][0]

    refldata = df.DataType(INSTRUMENT_PREFIX+"refldata", ReflData);
    for m in modules:
        df.register_module(m)
    df.register_module(loader)
    df.register_datatype(refldata)
    
    modules = [
        {"module": "ncnr.refl.super_load", "version": "0.1", "config": {}},
        {"module": "ncnr.refl.mask_points", "version": "0.1", "config": {}},
        {"module": "ncnr.refl.normalize", "version": "0.1", "config": {}},
        {"module": "ncnr.refl.join", "version": "0.1", "config": {}}
    ]
    wires = [
        {"source": [0,"output"], "target": [1,"data"]},
        {"source": [1,"output"], "target": [2,"data"]},
        {"source": [2,"output"], "target": [3,"data"]},
    ]
    template = Template("test", "test template", modules, wires, "ncnr.magik", version='0.0')
    refl = process_template(template, {"0": {"filelist": test_dataset, "auto_detector_saturation": False, "intent": "spec"}, "1": {"mask_indices": {"1": [0,-1]}}}, target=(1, "output"))
    return refl
    
def test3():
    from dataflow.core import register_module, register_datatype, Template, DataType
    #from dataflow.cache import use_redis
    #use_redis()
    from dataflow import core as df
    from dataflow.calc import process_template
    from reflred.steps import load, steps
    load.DATA_SOURCE = "http://ncnr.nist.gov/pub/"
    from reflred.refldata import ReflData
    INSTRUMENT_PREFIX = "ncnr.refl."

    modules = df.make_modules(steps.ALL_ACTIONS, prefix=INSTRUMENT_PREFIX)
    loader_name = INSTRUMENT_PREFIX + "ncnr_load"
    loader = [m for m in modules if m.id == loader_name][0]

    refldata = df.DataType(INSTRUMENT_PREFIX+"refldata", ReflData)
    
    for m in modules:
        df.register_module(m)
    df.register_module(loader)
    df.register_datatype(refldata)
    
    modules = [
        {"module": "ncnr.refl.super_load", "version": "0.1", "config": {}},
        #{"module": "ncnr.refl.nop", "version": "0.1", "config": {}},
    ]
    wires = [
        #{"source": [0,"output"], "target": [1,"data"]}
    ]
    template = Template("test", "test template", modules, wires, "ncnr.magik", version='0.0')
    refl = process_template(template, {"0": {"filelist": test_dataset}}, target=(0, str("output")))
    return refl



def unpolarized_template():
    from dataflow import core as df
    from reflred.refldata import ReflData
    from reflred.steps.polarization import PolarizationData
    from reflred.steps.deadtime import DeadTimeData
    INSTRUMENT_PREFIX = "ncnr.refl."
    modules = df.make_modules(steps.ALL_ACTIONS, prefix=INSTRUMENT_PREFIX)
    loader_name = INSTRUMENT_PREFIX + "ncnr_load"
    loader = [m for m in modules if m.id == loader_name][0]
    refldata = df.Data(INSTRUMENT_PREFIX+"refldata", ReflData,
                       loaders=[{'function': loader, 'id': 'LoadNeXuS'}])
    poldata = df.Data(INSTRUMENT_PREFIX+"poldata", PolarizationData, loaders=[])
    deadtime = df.Data(INSTRUMENT_PREFIX+"deadtime", DeadTimeData, loaders=[])
                       
    refl1d = df.Instrument(
        id=INSTRUMENT_PREFIX[:-1],
        name='NCNR reflectometer',
        menu=[('steps', modules)],
        datatypes=[refldata, poldata, deadtime],
        archive="NCNR",
    )
    
    from dataflow.core import make_template
    diagram = [
        # Load the data
        ["super_load", {"intent": "specular"}],
        ["mask_points", {"data": "-.output"}],
        ["join", {"data": "-.output"}],
        
        ["super_load", {"intent": "background+"}],
        ["mask_points", {"data": "-.output"}],
        ["join", {"data": "-.output"}],
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

if __name__ == "__main__":
    test()
