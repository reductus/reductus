"""
Load data sets.
"""
from reflred.formats import nexusref
from reflred.steps import steps

from dataflow.core import Module

test_dataset = [
  {'path': "ncnrdata/cgd/201511/21066/data/HMDSO_17nm_dry14.nxz.cgd", "mtime": 1447353278},
  {'path': "ncnrdata/cgd/201511/21066/data/HMDSO_17nm_dry15.nxz.cgd", "mtime": 1447353664},
  {'path': "ncnrdata/cgd/201511/21066/data/HMDSO_17nm_dry16.nxz.cgd", "mtime": 1447354137}
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
    "version": 0.1,
    "description": "load reflectometry NeXus files",
    "terminals": [
        {
            "id": "output", 
            "datatype": "ncnr.refl.data",
            "use": "out",
            "description": "data"
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
    "version": 0.1,
    "description": "mask reflectometry NeXus files",
    "terminals": [
        {
            "id": "output", 
            "datatype": "ncnr.refl.data",
            "use": "out",
            "description": "masked data"
        },
        {
            "id": "input",
            "datatype": "ncnr.refl.data",
            "use": "in",
            "description": "unmasked data"
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
    "version": 0.1,
    "description": "normalize reflectometry NeXus files",
    "terminals": [
        {
            "id": "output", 
            "datatype": "ncnr.refl.data",
            "use": "out",
            "description": "normalized data"
        },
        {
            "id": "input",
            "datatype": "ncnr.refl.data",
            "use": "in",
            "description": "unnormalized data"
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
    "version": 0.1,
    "description": "join reflectometry NeXus files",
    "terminals": [
        {
            "id": "output", 
            "datatype": "ncnr.refl.data",
            "use": "out",
            "description": "joined data"
        },
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
    from dataflow.core import register_module, register_datatype, Template, Data
    from dataflow.calc import calc_single
    from reflred.refldata import ReflData
    rdata = Data("ncnr.refl.data", ReflData, loaders=[{'function':load_action, 'id':'LoadNeXuS'}])
    register_module(load_module)
    register_module(normalize_module)
    register_module(join_module)
    register_module(mask_module)
    register_datatype(rdata)
    # a = load_action(files=test_dataset)
    #modules = [{"module": "ncnr.refl.load", "version": 0.1, "config": {"files": test_dataset}}]
    modules = [
        {"module": "ncnr.refl.load", "version": 0.1, "config": {}},
        {"module": "ncnr.refl.mask", "version": 0.1, "config": {}},
        {"module": "ncnr.refl.join", "version": 0.1, "config": {}}
    ]
    wires = [
        {"source": [0,"output"], "target": [1,"input"]},
        {"source": [1,"output"], "target": [2,"input"]},
    ]
    template = Template("test", "test template", modules, wires, "ncnr.magik", version='0.0')
    refl = calc_single(template, {"0": {"files": test_dataset}, "1": {"mask_indices": {"0": [0,-1]}}}, 1, "output")
    return refl
    
if __name__ == "__main__":
    test()
