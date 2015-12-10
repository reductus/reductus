"""
Load data sets.
"""

import os, gzip

try:
    import dataflow
except ImportError:
    def _cousin_path(path, degree, *parts):
        from os.path import dirname, join as joinpath, abspath
        path = abspath(path)
        for _ in range(degree):
            path = dirname(path)
        return joinpath(path, *parts)
    def _add_cousin_path(degree, *parts):
        import sys
        sys.path.append(_cousin_path(__file__, degree, *parts))
        #print("\n".join(sys.path))
    _add_cousin_path(4, "dataflow")

from dataflow.core import Module
from dataflow.core import lookup_module, lookup_datatype

from reflred.formats import nexusref
from reflred.steps import steps

test_dataset = [{'path': "ncnrdata/cgd/201511/21066/data/HMDSO_17nm_dry14.nxz.cgd", "mtime": 1447353278}]
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
    "action": steps.normalize,
    "name": "Load NeXuS Reflectometry Data"
    
}

normalize_module = Module(**normalize_kw)
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
    register_datatype(rdata)
    # a = load_action(files=test_dataset)
    #modules = [{"module": "ncnr.refl.load", "version": 0.1, "config": {"files": test_dataset}}]
    modules = [{"module": "ncnr.refl.load", "version": 0.1, "config": {}}]
    template = Template("test", "test template", modules, [], "ncnr.magik", version='0.0')
    refl = calc_single(template, {0: {"files": test_dataset}}, 0, "output")
    return refl
    
if __name__ == "__main__":
    test()