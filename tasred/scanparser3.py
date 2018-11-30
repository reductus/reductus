#import numpy as N
threshold=1e-6


simple_scans_parameter=['title','type','ef', 'ei','fixede','counts','counttype','detectortype','prefac','npts','timeout','holdpoint','holdscan','comment',
                        'filename']
aliased_scan_parameter=['w_i','w_c','w_f','w_s',
                        'h_i','h_c','h_f','h_s',
                        'k_i','k_c','k_f','k_s',
                        'l_i','l_c','l_f','l_s']

#energy_alias=['w_i','w_c','w_f','w_s']
w_alias=['w_i','w_c','w_f','w_s']
h_alias=['h_i','h_c','h_f','h_s']
k_alias=['k_i','k_c','k_f','k_s']
l_alias=['l_i','l_c','l_f','l_s']
ignore_list=['range_strings','scan_string']


class scanparser:
    def __init__(self,scanstr):
        self.scanstr=scanstr
        self.scan_description={}
    def parse_range(self,rangestr):
        prange={}
        orange={} #original range
        npts=self.scan_description['npts']
        range_split=rangestr.split('range=')
        fields=range_split[1].split('=')
        field=fields[0]
        if field!='q':
            prange[field]={}
            orange[field]={}
            toks=fields[1].split()
            if len(toks)==3:
                if toks[-1]=='s':
                    orange[field]['start']=float(toks[0])
                    orange[field]['stop']=float(toks[1])
                    prange[field]['start']=min(float(toks[0]),float(toks[1]))
                    prange[field]['stop']=max(float(toks[0]),float(toks[1]))
                    if npts>1:
                        prange[field]['step']=float(prange[field]['stop']-prange[field]['start'])/(npts-1)
                    else:
                        prange[field]['step']=float(0)
                elif toks[-1]=='i':
                    orange[field]['start']=toks[0]
                    orange[field]['step']=toks[1]
                    start=float(toks[0])
                    step=float(toks[1])
                    stop=start+(npts-1)*step
                    prange[field]['step']=abs(step)
                    prange[field]['start']=min(start,stop)
                    prange[field]['stop']=max(start,stop)
                    #prange['type']=toks[-1]

            else:
                orange[field]['center']=toks[0]
                orange[field]['step']=toks[1]
                #orange[field]['type']=''
                step=float(toks[1])
                center=float(toks[0])
                start=center-float(step)*(npts-1)/2
                stop=center+float(step)*(npts-1)/2
                prange[field]['step']=abs(step)
                prange[field]['start']=min(start,stop)
                prange[field]['stop']=max(start,stop)
                #prange['type']=''
        if 1:
            if fields[0]=='q':
                toks=fields[1].split()
                prange['qx']={}
                prange['qy']={}
                prange['qz']={}
                orange['qx']={}
                orange['qy']={}
                orange['qz']={}
                if len(toks)==3:
                    if toks[-1]=='s':
                        #print 'start stop'
                        start=toks[0].split('~')
                        start=[float(s) for s in start]
                        #start=N.array(start).astype('Float64')
                        prange['qx']['start']=start[0]
                        prange['qy']['start']=start[1]
                        prange['qz']['start']=start[2]
                        orange['qx']['start']=start[0]
                        orange['qy']['start']=start[1]
                        orange['qz']['start']=start[2]
                        stop=toks[1].split('~')
                        stop=[float(s) for s in stop]
                        #stop=N.array(stop).astype('Float64')
                        prange['qx']['stop']=stop[0]
                        prange['qy']['stop']=stop[1]
                        prange['qz']['stop']=stop[2]
                        orange['qx']['stop']=stop[0]
                        orange['qy']['stop']=stop[1]
                        orange['qz']['stop']=stop[2]
                        #orange['type']=toks[-1]
                        #prange['type']=toks[-1]
                        if npts>1:
                            step=[]
                            for i in range(len(stop)):
                                step.append((stop[i]-start[i])/(npts-1))
                            prange['qx']['step']=step[0]
                            prange['qy']['step']=step[1]
                            prange['qz']['step']=step[2]
                        else:
                            prange['qx']['step']=float(0)
                            prange['qy']['step']=float(0)
                            prange['qz']['step']=float(0)
                    elif toks[-1]=='i':
                        start=toks[0].split('~')
                        start=[float(s) for s in start]
                        #start=N.array(start).astype('Float64')
                        step=toks[1].split('~')
                        step=[float(s) for s in step]
                        #step=N.array(step).astype('Float64')
                        stop=[]
                        for i in range(len(step)):
                            stop.append(start[i]+(npts-1)*step[i])
                        orange['qx']['start']=start[0]
                        orange['qy']['start']=start[1]
                        orange['qz']['start']=start[2]
                        orange['qx']['step']=step[0]
                        orange['qy']['step']=step[1]
                        orange['qz']['step']=step[2]
                        prange['qx']['start']=start[0]
                        prange['qy']['start']=start[1]
                        prange['qz']['start']=start[2]
                        prange['qx']['step']=step[0]
                        prange['qy']['step']=step[1]
                        prange['qz']['step']=step[2]                        
                        prange['qx']['stop']=stop[0]
                        prange['qy']['stop']=stop[1]
                        prange['qz']['stop']=stop[2]
                        #prange['type']=toks[-1]
                        #orange['type']=toks[-1]
                else:
                    center=toks[0].split('~')
                    center=[float(s) for s in center]
                    #center=N.array(center).astype('Float64')
                    step=toks[1].split('~')
                    step=[float(s) for s in step]
                    #step=N.array(step).astype('Float64')
                    start=[]
                    stop=[]
                    for i in range(len(center)):
                        start.append(center[i]-(npts-1)/2*step[i])
                        stop.append(center[i]+(npts-1)/2*step[i])
                    
                    prange['qx']['center']=center[0]
                    prange['qy']['center']=center[1]
                    prange['qz']['center']=center[2]
                    prange['qx']['step']=step[0]
                    prange['qy']['step']=step[1]
                    prange['qz']['step']=step[2]
                    
                    
                    
                    
                    
                    prange['qx']['start']=start[0]
                    prange['qy']['start']=start[1]
                    prange['qz']['start']=start[2]
                    prange['qx']['step']=step[0]
                    prange['qy']['step']=step[1]
                    prange['qz']['step']=step[2]
                    prange['qx']['stop']=stop[0]
                    prange['qy']['stop']=stop[1]
                    prange['qz']['stop']=stop[2]

        return prange,orange


    def parse_scan(self):
        scanstr=self.scanstr.lower().strip()
        self.scan_description={}
        scan_description=self.scan_description
        scan_description['scan_string']=scanstr
        scan_description['range_strings']=[]

        toks=scanstr.split(':')
        toks=[str(i) for i in toks]
        try:
            if toks[0].lower().strip()!='scan':
                raise BadScanError('Not a Valid Scan')
            toks=toks[1:]
            for tok in toks:
                field=tok.split('=')
                #print 'field',field
                if field[0]=='':
                    return self.scan_description # for fpx scans can get a '::Title'  ack!!!!!!
                else:
                    key=str(field[0].lower())
                    value=field[1]
                    if key.lower()=='range':
                        scan_description['range_strings'].append(tok.lower())
                    else:
                        try:
                            scan_description[key]=float(value)
                        except ValueError:
                            scan_description[key]=value
            return self.scan_description
        except BadScanError:
            print('Not a Valid Scan')
            self.scan_description={}
            return self.scan_description

    def get_varying(self):
        #print 'get varying'
        scan_description=self.scan_description
        scanstr_parsed=self.parse_scan()
        if self.scan_description=={}:
            self.ranges={}
            self.oranges={}
            return self.ranges
        else:
            self.ranges={}
            self.oranges={}
            self.varying=[]
            for range_string in scanstr_parsed['range_strings']:
                ranges,oranges=self.parse_range(range_string)
                #print 'ranges',ranges
                for key,value in ranges.iteritems():
                    self.ranges[key]=value
                    #print 'key',key,'value',value
                    if abs(value['step'])>threshold:
                        self.varying.append(key)
                for key,value in oranges.iteritems():
                    self.oranges[key]=value
            return self.varying
  
        
    def add_parameter(self,key,value):
        if key in simple_scans_parameter:
            #print 'simple_scan_parameter'
            if not (value==None):
                self.scan_description[key]=value
        elif key in aliased_scan_parameter:
            #print 'aliased'
            if key in w_alias and not (value==None):
                rangetype='e'
                if not (self.oranges.has_key('e')):
                        self.oranges['e']={}   
                if key=='w_i' and not (value==None):
                    self.oranges['e']['start']=value
                if key=='w_f' and not (value==None):
                    self.oranges['e']['stop']=value
                if key=='w_s' and not (value==None):
                    self.oranges['e']['step']=value
                if key=='w_c' and not (value==None):
                    self.oranges['e']['center']=value  #I don't know what order keys will come in, so I'll have to sort it out afterwards
            if (key in h_alias) or (key in k_alias) or (key in l_alias):
                rangetype='Q'
                if not (self.oranges.has_key('qx')) and not (value==None):
                    self.oranges['qx']={} 
                if key=='h_i'and not (value==None):
                    self.oranges['qx']['start']=value
                if key=='h_f' and not (value==None):
                    self.oranges['qx']['stop']=value
                if key=='h_s' and not (value==None):
                    self.oranges['qx']['step']=value
                if key=='h_c' and not (value==None):
                    self.oranges['qx']['center']=value 
                    
                if not (self.oranges.has_key('qy')) and not (value==None):
                    self.oranges['qy']={} 
                if key=='k_i' and not (value==None):
                    self.oranges['qy']['start']=value
                if key=='k_f' and not (value==None):
                    self.oranges['qy']['stop']=value
                if key=='k_s' and not (value==None):
                    self.oranges['qy']['step']=value
                if key=='k_c' and not (value==None):
                    self.oranges['qy']['center']=value
                    
                if not (self.oranges.has_key('qz')) and not (value==None):
                    self.oranges['qz']={} 
                if key=='l_i' and not (value==None):
                    self.oranges['qz']['start']=value
                if key=='l_f' and not (value==None):
                    self.oranges['qz']['stop']=value
                if key=='l_s' and not (value==None):
                    self.oranges['qz']['step']=value
                if key=='l_c' and not (value==None):
                    self.oranges['qz']['center']=value 
        elif not key in ['delete']: 
            #print 'nonaliased range'
            #a nonaliased range
            keyparts=key.split('_')
            devname=keyparts[0]
            #print keyparts
            #if len(keyparts)==2:
            component=keyparts[1]
            if not (self.oranges.has_key(devname)) and not (value==None):
                #print 'new_orange',key
                self.oranges[devname]={}
            
            if  component=='i' and not (value==None):
                    self.oranges[devname]['start']=value
            if component=='f' and not (value==None):
                    self.oranges[devname]['stop']=value
            if component=='s' and not (value==None):
                    self.oranges[devname]['step']=value
            if component=='c' and not (value==None):
                    self.oranges[devname]['center']=value      

    def delete_parameter(self,key,value):
        deletekeys=value.split()  #we should delete tags first to be safe
        for deletekey in deletekeys:
            if deletekey in simple_scans_parameter:
                del(self.scan_description['deletekey'])
            elif deletekey in aliased_scan_parameter:
                if deletekey in w_alias:
                    rangetype='e'
                    if not (self.oranges.has_key('e')):
                            raise BadScanError('Trying to delete a parameter that doesn not exist in original scan!') #  If this isn't here, then there is no parameter to delete!!!! self.oranges['e']={}   
                    if deletekey=='w_i':
                        del(self.oranges['e']['start'])
                    if deletekey=='w_f':
                        del(self.oranges['e']['stop'])
                    if deletekey=='w_s':
                        del(self.oranges['e']['step'])
                    if deletekey=='w_c':
                        del(self.oranges['e']['center'])  #I don't know what order keys will come in, so I'll have to sort it out afterwards
                if (deletekey in h_alias) or (deletekey in k_alias) or (deletekey in l_alias):
                    rangetype='Q'
                    if not (self.oranges.has_key('qx')):
                        raise BadScanError('Trying to delete a parameter that doesn not exist in original scan!') #  If this isn't here, then there is no parameter to delete!!!! self.oranges['e']={}   
                    if deletekey=='h_i':
                        del(self.oranges['qx']['start'])
                    if deletekey=='h_f':
                        del(self.oranges['qx']['stop'])
                    if deletekey=='h_s':
                        del(self.oranges['qx']['step'])
                    if deletekey=='h_c':
                        del(self.oranges['qx']['center']) 
                        
                    if not (self.oranges.has_key('qy')):
                        raise BadScanError('Trying to delete a parameter that doesn not exist in original scan!') #  If this isn't here, then there is no parameter to delete!!!! self.oranges['e']={}   
                    if deletekey=='k_i':
                        del(self.oranges['qy']['start'])
                    if deletekey=='k_f':
                        del(self.oranges['qy']['stop'])
                    if deletekey=='k_s':
                        del(self.oranges['qy']['step'])
                    if deletekey=='k_c':
                        del(self.oranges['qy']['center'])
                        
                    if not (self.oranges.has_key('qz')):
                        raise BadScanError('Trying to delete a parameter that doesn not exist in original scan!') #  If this isn't here, then there is no parameter to delete!!!! self.oranges['e']={}   
                    if deletekey=='l_i':
                        del(self.oranges['qz']['start'])
                    if deletekey=='l_f':
                        del(self.oranges['qz']['stop'])
                    if deletekey=='l_s':
                        del(self.oranges['qz']['step'])
                    if deletekey=='l_c':
                        del(self.oranges['qz']['center']) 
            else: 
                #a nonaliased range
                if not (self.oranges.has_key(deletekey)):
                                raise BadScanError('Trying to delete a parameter that doesn not exist in original scan!') #  If this isn't here, then there is no parameter to delete!!!! self.oranges['e']={}   
                keyparts=deletekey.split('_')
                devname=keyparts[0]
                component=keyparts[1]
                if  component=='i':
                        del(self.oranges[devname]['start'])
                if component=='f':
                        del(self.oranges[devname]['stop'])
                if component=='s':
                        del(self.oranges[devname]['step'])
                if component=='c':
                        del(self.oranges[devname]['center'])      

                    
        
    def scanop(self,newobj):
        for key,value in newobj.__dict__.iteritems():
            if key=='scans':
                pass
            elif key=='delete' and not value==None:
                self.delete_parameter(key,value)
            else:
                #print 'adding'
                self.add_parameter(key,value)
                #print 'added'
    
    def verify(self):
        """"
        verify that the resulting scan is valid--nominally.  We will do an additional check in the code by sending it to 
        the server and trying to run it as a dry run.  If the dryrun succeeds, then we will replace the original scan, otherwise,
        we will fail...
        """
        for key,value in self.oranges.iteritems():
            if len(value.keys())==4:                
                raise BadScanError('%s range has too many parameters.  Scan is ill defined'%(key,)) 
            elif len(value.keys())==2 and not self.scan_description.has_key('npts'):
                raise BadScanError('%s range is missing the npts parameter.  Scan is ill defined' %(key,))
            else:
                if len(value.keys())==2:
                    if value.has_key('start') and value.has_key('step'):
                        self.oranges[key]['type']='i'
                    elif value.has_key('center') and value.has_key('step'):
                        self.oranges[key]['type']=''
                    elif value.has_key('start') and  value.has_key('stop'):
                        self.oranges[key]['type']='s'
                    else:
                        raise BadScanError('%s range is bad (note:  There is no center final scan).  Scan is ill defined' %(key,))
                elif len(value.keys())==3:
                    raise BadScanError('%s range has too many parameters.  Scan is ill defined'%(key,))
        if self.oranges.has_key('qx'):
            if self.oranges['qx'].has_key('type') and self.oranges['qy'].has_key('type') and self.oranges['qz'].has_key('type'):
                if not (self.oranges['qx']['type']==self.oranges['qy']['type'] and
                self.oranges['qx']['type']==self.oranges['qz']['type'] and
                self.oranges['qy']['type']==self.oranges['qz']['type']):
                    raise BadScanError('qx,qy,and qz are different types of scans!  Scan is ill defined')
            else:
                raise BadScanError('qx,qy,and qz are different types of scans!  Scan is ill defined')

#simple_scans_parameter=['title','type','ef', 'ei','efixed','counts','counttype','detectortype','prefac','npts','timeout','holdpoint','holdscan','comment',
#                        'filename']        
            
                    
    def generate_new_description(self):
        s='Scan'
        for key,value in self.scan_description.iteritems():
            if not key in ignore_list and not value==None:
                #print 'key',key,value
                if key in ['npts','fixed','subid']:
                    s='%s:%s=%d'%(s,key,int(value))
                elif key in ['holdpoint','counts','prefac','holdscan']:
                    s='%s:%s=%3.1f'%(s,key,float(value))
                else:
                    try:
                        s='%s:%s=%3.5f'%(s,key,float(value))
                    except:
                        s='%s:%s=%s'%(s,key,str(value))                    
        for key,value in self.oranges.iteritems():
            if not key in ['qx','qy','qz']:
                s='%s:Range=%s='%(s,key.upper())
                if value['type']=='s':
                    s='%s%4.5f %4.5f s'%(s,float(value['start']), float(value['stop']))
                if value['type']=='i':
                    s='%s%4.5f %4.5f i'%(s,float(value['start']), float(value['step']))
                if value['type']=='':
                    s='%s%4.5f %4.5f'%(s,float(value['center']), float(value['step']))
        if self.oranges.has_key('qx'):
            if self.oranges['qx']['type']=='s':
                s='%s:RANGE=Q=%3.5f~%3.5f~%3.5f %3.5f~%3.5f~%3.5f s'%(s,float(self.oranges['qx']['start']),float(self.oranges['qy']['start']),float(self.oranges['qz']['start']),
                                                                   float(self.oranges['qx']['stop']),float(self.oranges['qy']['stop']),float(self.oranges['qz']['stop']))
            elif self.oranges['qx']['type']=='i':
                s='%s:RANGE=Q=%3.5f~%3.5f~%3.5f %3.5f~%3.5f~%3.5f i'%(s,float(self.oranges['qx']['start']),float(self.oranges['qy']['start']),float(self.oranges['qz']['start']),
                                                                   float(self.oranges['qx']['step']),float(self.oranges['qy']['step']),float(self.oranges['qz']['step']))   
            elif self.oranges['qx']['type']=='':
                s='%s:RANGE=Q=%3.5f~%3.5f~%3.5f %3.5f~%3.5f~%3.5f'%(s,float(self.oranges['qx']['center']),float(self.oranges['qy']['center']),float(self.oranges['qz']['center']),
                                                                   float(self.oranges['qx']['step']),float(self.oranges['qy']['step']),float(self.oranges['qz']['step']))            
        return s
    
    

class Parseobj(object):
    def __init__(self):
        self.npts=5
        self.h_i=7
        #self.h_c=1
        #self.k_c=3
        #self.l_c=0
        #self.h_s=0.1
        #self.k_s=0.2
        #self.l_s=0.3
        
        #self.delete='h_f k_f l_f h_i k_i l_i'

def driver(original_scan,parseobj):
    
    #if hasattr(parseob,'ei') and hasattr(parseob,'ef'):
    if parseobj.ei==True and parseobj.ef==True:
        raise BadScanError('Not a Valid Scan.  Cannot fix both ei and ef.')
    elif parseobj.ei==True:
        parsobj.fixed=0
        #print 'ei tested'
    elif parseobj.ef==True:
        parsobj.fixed=1
        #print 'ef tested'
    delattr(parseobj,'ei')
    #print 'deleted ei'
    delattr(parseobj,'ef')
    for key,value in parseobj.__dict__.iteritems():
        if not value==None:
            try:
                parseobj.__dict__[key]=value[0]
            except:
                pass
            #print key,parseobj.__dict__[key]
    print('original_scan\n', original_scan)
    myparser=scanparser(original_scan)
    #print 'instantiated', myparser.__dict__.keys()
    scanstr_parsed=myparser.parse_scan()
    #print 'scanstr_parsed',scanstr_parsed
    varying=myparser.get_varying()
    #print 'varying',varying
    myparser.scanop(parseobj)
    #print 'oranges',myparser.oranges
    myparser.verify()
    s=myparser.generate_new_description()
    return s 
    
    
class BadScanError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

if  __name__=='__main__':
#find peak, A3-A4
    if 0:
        scanstr='Scan:Title=ICEFindPeak:Type=6:Fixed=0:FixedE=1:CountType=Time:Counts=2.0:Range=A4=50.0095 0.2:Npts=21:DetectorType=Detector:Filename=fpx:Range=A3=115.113 0.1::Title=FindPeak'
#inititial final h
    if 1:
        scanstr='Scan:SubID=13176:JType=VECTOR:Fixed=1:FixedE=13.6998911684:Npts=3:Counts=1.0:Prefac=1.0:DetectorType=Detector:CountType=Time:Filename=dumb:HoldScan=0.0:Range=Q=1.0~0.0~0.0 2.0~0.0~0.0 s:Range=E=0.0 0.0 s'
#initial step h
    if 0:
        scanstr='Scan:SubID=13176:JType=VECTOR:Fixed=1:FixedE=13.6998911684:Npts=3:Counts=1.0:Prefac=1.0:DetectorType=Detector:CountType=Time:Filename=dumb:HoldScan=0.0:Range=Q=1.0~0.0~0.0 2.0~0.0~0.0 i:Range=E=0.0 0.0 i'
#center step h
    if 0:
        scanstr='Scan:SubID=13176:JType=VECTOR:Fixed=1:FixedE=13.6998911684:Npts=3:Counts=1.0:Prefac=1.0:DetectorType=Detector:CountType=Time:Filename=dumb:HoldScan=0.0:Range=Q=1.0~0.0~0.0 2.0~0.0~0.0:Range=E=0.0 0.0'

#center step e [-1,0,1]
    if 0:
        scanstr='Scan:SubID=13176:JType=VECTOR:Fixed=1:FixedE=13.6998911684:Npts=3:Counts=1.0:Prefac=1.0:DetectorType=Detector:CountType=Monitor:Filename=dumb:HoldScan=0.0:Range=Q=0.0~0.0~0.0 0.0~0.0~0.0:Range=E=0.0 1.0'
#center step e [-.5,.5]
    if 0:
        scanstr='Scan:SubID=13176:JType=VECTOR:Fixed=1:FixedE=13.6998911684:Npts=2:Counts=1.0:Prefac=1.0:DetectorType=Detector:CountType=Monitor:Filename=dumb:HoldScan=0.0:Range=Q=0.0~0.0~0.0 0.0~0.0~0.0:Range=E=0.0 1.0'
#initial step e [0,1,2]
    if 0:
        scanstr='Scan:SubID=13176:JType=VECTOR:Fixed=1:FixedE=13.6998911684:Npts=3:Counts=1.0:Prefac=1.0:DetectorType=Detector:CountType=Monitor:Filename=dumb:HoldScan=0.0:Range=Q=0.0~0.0~0.0 0.0~0.0~0.0 i:Range=E=0.0 1.0 i'
#start stop e [0,.5,1]
    if 0:
        scanstr='Scan:SubID=13176:JType=VECTOR:Fixed=1:FixedE=13.6998911684:Npts=3:Counts=1.0:Prefac=1.0:DetectorType=Detector:CountType=Monitor:Filename=dumb:HoldScan=0.0:Range=Q=0.0~0.0~0.0 0.0~0.0~0.0 s:Range=E=0.0 1.0 s'

    if 1:
        parseobj=Parseobj()
        s=driver(scanstr,parseobj)
        print('s',s)
    