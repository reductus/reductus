import sys, traceback, Ice
import Dataflow

class UtilI(Dataflow.Util):
    def get_file_metadata(self, pathlist=None, current=None):
        if pathlist is None: pathlist = []
        print pathlist
        import urllib
        import urllib2

        url = 'http://ncnr.nist.gov/ipeek/listftpfiles.php'
        values = {'pathlist[]' : pathlist}
        data = urllib.urlencode(values, True)
        req = urllib2.Request(url, data)
        response = urllib2.urlopen(req)
        fn = response.read()
        return fn

from dataflow.core import register_module, register_datatype, Template, Data
from dataflow.cache import use_redis
use_redis()
from dataflow.calc import calc_single
from dataflow.modules.load import load_module, load_action
from reflred.refldata import ReflData
rdata = Data("ncnr.refl.data", ReflData, loaders=[{'function':load_action, 'id':'LoadNeXuS'}])
register_module(load_module)
register_datatype(rdata)
import json

class CalcI(Dataflow.Calc):    
    def refl_load(file_descriptors):
        """ 
        file_descriptors will be a list of dicts like 
        [{"path": "ncnrdata/cgd/201511/21066/data/HMDSO_17nm_dry14.nxz.cgd", "mtime": 1447353278}, ...]
        """
        modules = [{"module": "ncnr.refl.load", "version": "0.1", "config": {}}]
        template = Template("test", "test template", modules, [], "ncnr.magik", version='0.0')
        refl = calc_single(template, {0: {"files": file_descriptors}}, 0, "output")
        return [r._toDict(sanitized=True) for r in refl]

    def calc_single(self, template_def, config, nodenum, terminal_id, current=None):
        """ json-rpc wrapper for calc_single
        template_def = 
        {"name": "template_name",
         "description": "template description!",
         "modules": ["list of modules"],
         "wires": ["list of wires"],
         "instrument": "facility.instrument_name",
         "version": "2.7.3"
        }
        
        where modules in list of modules above have structure:
        module = 
        {"module": "facility.instrument_name.module_name",
         "version": "0.3.2"
        }
        
        and wires have structure:
        [["wire_start_module_id:wire_start_terminal_id", "wire_end_module_id:wire_end_terminal_id"],
         ["1:output", "2:input"],
         ["0:xslice", "3:input"]
        ]
        
        config = 
        [{"param": "value"}, ...]
        
        nodenum is the module number from the template for which you wish to get the calculated value
        
        terminal_id is the id of the terminal for that module, that you want to get the value from
        (output terminals only).
        """
        template = Template(**json.loads(template_def))
        config = json.loads(config)
        print template
        retvals = calc_single(template, config, nodenum, terminal_id)
        return [r._toDict(sanitized=True) for r in retvals]
    
status = 0
ic = None
try:
    ic = Ice.initialize(sys.argv)
    df_adapter = ic.createObjectAdapterWithEndpoints("DataflowAdapter", "ws -h localhost -p 10001")
    df_obj = CalcI()
    df_adapter.add(df_obj, ic.stringToIdentity("Calc"))
    util_obj = UtilI()
    df_adapter.add(util_obj, ic.stringToIdentity("Util"))
    df_adapter.activate()
    ic.waitForShutdown()
except:
    traceback.print_exc()
    status = 1
 
if ic:
    # Clean up
    try:
        ic.destroy()
    except:
        traceback.print_exc()
        status = 1
 
sys.exit(status)
