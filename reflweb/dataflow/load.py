"""
Load data sets.
"""

import sys
sys.path.append("/home/brian/work/dataflow")
from reflred.formats import nexusref
from dataflow.core import Module
from dataflow.core import lookup_module, lookup_datatype
import os, gzip

test_dataset = [{'url': "http://www.ncnr.nist.gov/pub/ncnrdata/cgd/201511/21066/data/HMDSO_17nm_dry14.nxz.cgd", "mtime": 1447353278}]

def load_action(files=[], **kwargs):
    print "loading saved results"
    #import tarfile
    #from ...apps.tracks.models import File
    import urllib2, StringIO, datetime, pytz
    result = []
    for f in files:
        print 'f: ', f
        try:
            fc = urllib2.urlopen(f['url'])
            fn = f['url'].split("/")[-1]
            mtime = fc.info().getdate('last-modified')
            cm = datetime.datetime(*mtime[:7], tzinfo=pytz.utc)
            fm = datetime.datetime.fromtimestamp(f['mtime'], pytz.utc)
            if fm < cm:
                print fm, cm, "newer file in archive"
            elif fm > cm:
                print fm, cm, "older file in archive"
            else:
                #get it!
                fcontent = fc.read()
                ff = StringIO.StringIO(fcontent)
                nx_entries = nexusref.load_entries(fn, ff)
                result.extend(nx_entries)
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

def load_module(id=None, datatype=None, action=load_action,
                version='0.0', fields={}, xtype='WireIt.Container', **kwargs):
    """Module for loading data from a raw datafile"""

   
    terminals = [
        #dict(id='input',
        #     datatype=datatype,
        #     use='in',
        #     description='data',
        #     required=False,
        #     multiple=True,
        #     ),
        dict(id='output',
             datatype=datatype,
             use='out',
             description='data',
             ),
    ]

    files_field = {
        "type":"files",
        "label": "Files",
        "name": "files",
        "value": [],
    }
    intent_field = {
        "type":"string",
        "label":"Intent",
        "name": "intent",
        "value": '',
    }
    
    fields.update({'files': files_field, 'intent': intent_field})
    
    # Combine everything into a module.
    module = Module(id=id,
                  name='Load Raw',
                  version=version,
                  description=action.__doc__,
                  #icon=icon,
                  terminals=terminals,
                  fields=fields,
                  action=action,
                  xtype=xtype,
                  **kwargs
                  )

    return module
