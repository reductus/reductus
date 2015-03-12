import sys, os
import SocketServer
import SimpleHTTPServer
import BaseHTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer, SimpleJSONRPCRequestHandler, SimpleJSONRPCDispatcher
import socket

import urlparse

from OpenSSL import SSL

import jsonrpclib.config

import multiprocessing
import webbrowser

jsonrpclib.config.use_jsonclass = False

"""
HandlerClass = SimpleHTTPRequestHandler
ServerClass  = BaseHTTPServer.HTTPServer
Protocol     = "HTTP/1.0"

if sys.argv[1:]:
    port = int(sys.argv[1])
else:
    port = 8000
server_address = ('localhost', 8001) # get next open socket

HandlerClass.protocol_version = Protocol
httpd = ServerClass(server_address, HandlerClass)
http_port = httpd.socket.getsockname()[1]
print "http port: ", http_port

sa = httpd.socket.getsockname()
print "Serving HTTP on", sa[0], "port", sa[1], "..."
# httpd.serve_forever()
#http_process = multiprocessing.Process(target=httpd.serve_forever)
#http_process.start()
"""

currdir = os.path.dirname( __file__ )

class JSONRPCRequestHandler(SimpleHTTPRequestHandler, SimpleJSONRPCRequestHandler):
    """JSON-RPC and documentation request handler class.

    Handles all HTTP POST requests and attempts to decode them as
    XML-RPC requests.

    Handles all HTTP GET requests and interprets them as requests
    for web pages, js, json or css.
    
    Put all static files to be served in 'static' subdirectory.
    """
    #rpc_paths = ('/', '/RPC2')
    rpc_paths = () # accept all
    
    def do_OPTIONS(self):
        self.send_response(200, "ok")       
        #self.send_header('Access-Control-Allow-Origin', 'http://localhost:8000')
        #self.send_header('Access-Control-Allow-Origin', "http://localhost:%d" % (http_port,))           
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.end_headers()
        self.connection.shutdown(0)
        
    # Add these headers to all responses
    def end_headers(self):
        self.send_header("Access-Control-Allow-Headers", 
                         "Origin, X-Requested-With, Content-Type, Accept")
        self.send_header("Access-Control-Allow-Origin", "*") #"http://localhost:%d" % (server_address[1],))
        SimpleJSONRPCRequestHandler.end_headers(self)
        
    
class SecureJSONRPCServer(BaseHTTPServer.HTTPServer, SimpleJSONRPCDispatcher):
    #request_queue_size = 256
    def __init__(self, server_address, HandlerClass, logRequests=True):
        """Secure XML-RPC server.

        It it very similar to SimpleXMLRPCServer but it uses HTTPS for transporting XML data.
        """
        self.logRequests = logRequests

        SimpleJSONRPCDispatcher.__init__(self)
        SocketServer.BaseServer.__init__(self, server_address, HandlerClass)
        self.socket = socket.socket(self.address_family,
                                    self.socket_type)
        #ctx = SSL.Context(SSL.SSLv23_METHOD)
        #ctx.use_privatekey_file (self.KEYFILE)
        #ctx.use_certificate_file(self.CERTFILE)
        #self.socket = SSL.Connection(ctx, socket.socket(self.address_family,
        #                                                self.socket_type))
        self.server_bind()
        self.server_activate()
        
server = SimpleJSONRPCServer(('localhost', 0), encoding='utf8', requestHandler=JSONRPCRequestHandler)
#server = SecureJSONRPCServer(('localhost', 0), JSONRPCRequestHandler)
rpc_port = server.socket.getsockname()[1]
webbrowser.open_new_tab('http://localhost:%d/index_one_d3.html' % (rpc_port,))
server.register_function(pow)
server.register_function(lambda x,y: x+y, 'add')
server.register_function(lambda x: x, 'ping')

import thread
def server_kill():
    print "closing server now"
    thread.start_new_thread(server.shutdown, ())
    
server.register_function(server_kill, 'shutdown')

import h5py, os, simplejson

def categorize_files(path='./'):
    fns = os.listdir(path)
    fns.sort()
    categories = {\
        'Specular': 'SPEC',
        'Background': 'BG', 
        'Rocking': 'ROCK',
        'Slit': 'SLIT'}
    output = {}
    for fn in fns:
        try:
            f = h5py.File(os.path.join(path, fn))
            for entry in f.keys():
                _name = f[entry].get('DAS_logs/sample/name').value.flatten()[0]
                output.setdefault(_name, {})
                _num = f[entry].get('DAS_logs/trajectoryData/fileNum').value.flatten()[0]
                _scanType = f[entry].get('DAS_logs/trajectoryData/_scanType')
                if _scanType is not None:
                    _scanType = _scanType.value.flatten()[0]
                elif f[entry].get('title', None).value.flatten()[0] == 'fp':
                    _scanType = 'findPeak'
                else:
                    _scanType = 'uncategorized'
                output[_name].setdefault(_scanType, {})
                output[_name][_scanType]['%d:%s' % (_num, entry)] = {'filename': fn, 'entry': entry}
        except:
            pass
            
    #return simplejson.dumps(output)
    return output

def get_file_metadata(path='./'):
    fns = os.listdir(path)
    fns.sort()
    metadata = []
    for fn in fns:
        try:
            f = h5py.File(os.path.join(path, fn))
            for entry in f.keys():
                output = {}
                DAS = f[entry].get('DAS_logs')
                xAxis = DAS.get('trajectoryData/xAxis')
                if xAxis is not None:
                    xAxis = xAxis.value[0] #.replace('.', '/')
                if xAxis in DAS.keys() and 'primary' in DAS[xAxis].attrs: 
                    # then it's a device name: convert to primary node
                    xAxis = xAxis + "/" + DAS[xAxis].attrs['primary']
                if not xAxis in DAS:
                    xAxis = DAS.get('trajectory/defaultXAxisPlotNode', "").value[0] #.replace('.', '/')
                if xAxis == "":
                    xAxis = DAS['trajectory/scannedVariables'].value[0].split()[0] #.replace('.', '/')
                _name = DAS.get('sample/name').value.flatten()[0]
                output['sample_name'] = str(_name)
                _num = DAS.get('trajectoryData/fileNum').value.flatten()[0]
                output['fileNum'] = "%d" % (_num,)
                _scanType = DAS.get('trajectoryData/_scanType')
                if _scanType is not None:
                    _scanType = _scanType.value.flatten()[0]
                elif f[entry].get('title', None).value.flatten()[0] == 'fp':
                    _scanType = 'fp:%s' % (xAxis,)
                else:
                    _scanType = 'uncategorized'
                output['scanType'] = _scanType
                output['filename'] = fn
                output['path'] = path
                output['entry'] = entry
                output['xaxis'] = xAxis
                metadata.append(output)
        except:
            pass
    return metadata

def get_jstree(path='./'):
    files = categorize_files(path)
    categories = ['SPEC','BG','ROCK','SLIT','findPeak','uncategorized']
    output = {'core': {'data': []}}
    sample_names = files.keys()
    for sample in sample_names:
        samp_out = {"text": sample}
        samp_out['children'] = []
        for cat in categories:
            if not cat in files[sample]: break
            cat_out = {"text": cat, "children": []}
            item_keys = files[sample][cat].keys()
            item_keys.sort()
            for child in item_keys:
                cat_out['children'].append({"text": child, "extra_data": {
                    "filename": files[sample][cat][child]['filename'],
                    "entry": files[sample][cat][child]['entry'],
                    "path": path}});
            samp_out['children'].append(cat_out)
        output['core']['data'].append(samp_out)
    return output 
        
def get_plottable(file_and_entry):
    """ file_and_entry should be list of dicts:
    [{ "filename": fn1, "entry": entryname1 }, { "filename": fn2, ...} ...]
    """
    print file_and_entry
    fig = {
        "title": "plot",
        "type": "1d",
        "data": [],
        "options": {
            "axes": {"xaxis": {}, "yaxis": {}},
            "series": [],
            },
        }
    for item in file_and_entry:
        f = h5py.File(item['filename'])
        DAS = f[item['entry']]['DAS_logs']
        print DAS
        xAxis = DAS.get('trajectoryData/xAxis')
        if xAxis is not None:
            xAxis = xAxis.value[0].replace('.', '/')
        if xAxis in DAS.keys() and 'primary' in DAS[xAxis].attrs: 
            # then it's a device name: convert to primary node
            xAxis = xAxis + "/" + DAS[xAxis].attrs['primary']
        if not xAxis in DAS:
            xAxis = DAS.get('trajectory/defaultXAxisPlotNode', "").value[0].replace('.', '/')
        if xAxis == "":
            xAxis = DAS['trajectory/scannedVariables'].value[0].split()[0].replace('.', '/')
        
        yAxis=DAS.get('trajectory/defaultYAxisPlotNode', "").value[0].replace('.', '/')
        if yAxis == "":
            yAxis = "counter/liveROI"
        yAxisChannel = DAS.get('trajectory/defaultYAxisPlotChannel', -1)
        fig_x = fig['options']['axes']['xaxis']
        fig_y = fig['options']['axes']['yaxis']
        if "label" in fig_x:
            if not fig_x['label'] == xAxis:
                raise Exception("axes do not match")
        else:
            fig_x['label'] = xAxis
        if "label" in fig_y:
            if not fig_y['label'] == yAxis:
                raise Exception("axes do not match")
        else: 
            fig_y['label'] = yAxis
        _num = DAS.get('trajectoryData/fileNum').value.flatten()[0]
        fig['options']['series'].append({"label": '%d:%s' % (_num, item['entry'])})
        #fig['options']['series'].append({"label": item['filename'] + ':' + item['entry']})
        x = DAS[xAxis].value.astype('float')
        y = DAS[yAxis].value.astype('float')
        xy = [[xx,yy] for xx, yy in zip(x,y)]
        fig['data'].append(xy)
        
    fig['options']['axes']['xaxis']['label'] = fig['options']['axes']['xaxis']['label'].replace('/', '.')
    fig['options']['axes']['yaxis']['label'] = fig['options']['axes']['yaxis']['label'].replace('/', '.')
    return fig
    
server.register_function(categorize_files) # deprecated
server.register_function(get_plottable)
server.register_function(get_jstree) # deprecated
server.register_function(get_file_metadata)
server.serve_forever()
print "done serving rpc forever"
