
import numpy as N
#import pylab
import datetime
from time import mktime
#import mx.DateTime
import re
from tasred import scanparser3 as scanparser
import os
#from ...apps.tracks.models import File


months = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
          'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}


def get_tokenized_line(myfile, returnline=['']):
    lineStr = myfile.readline().decode()
    returnline[0] = lineStr.rstrip()
    strippedLine = lineStr.lower().rstrip()
    tokenized = strippedLine.split()

    return tokenized


class datareader(object):
    def __init__(self, filename=None, friendly_name=None):
        self.myfilestr = filename
        self.friendly_name = filename if (friendly_name is None) else friendly_name
        # define Data Abstraction Layer
        self.data_abstraction_layer()
        return

    def get_metadata(self):
        return self.metadata

    def get_plottable(self):
        return [self.metadata, self.columnlist, self.columndict]

    def data_abstraction_layer(self):
        self.metadata = {}
        self.data = {}
        self.additional_metadata = {}
        self.metadata['entry'] = 'entry'
        self.metadata['monitor_base'] = None  # float(tokenized[6])
        self.metadata['monitor_prefactor'] = None  # float(tokenized[7])
        # self.metadata['monitor_base']*self.metadata['monitor_prefactor']
        self.metadata['monitor'] = None
        # can be 'monitor', 'time' #tokenized[8].strip("'").lower()
        self.metadata['count_type'] = None
        self.metadata['signal'] = None  # for example, 'detector'
        self.metadata['varying'] = None
        self.metadata['ranges'] = None
        self.metadata['analyzerdetectormode'] = None
        self.metadata['AnalyzerDetectorDevicesOfInterest'.lower()] = None
        self.metadata['AnalyzerDDGroup'.lower()] = None
        self.metadata['AnalyzerPSDGroup'.lower()] = None
        self.metadata['AnalyzerSDGroup'.lower()] = None
        self.metadata['AnalyzerDoorDetectorGroup'.lower()] = None
        self.metadata['analyzerfocusmode'] = None
        self.metadata['monovertifocus'] = None
        self.metadata['monohorizfocus'] = None

        self.metadata['filename'] = None  # tokenized[0].strip("'")
        self.metadata['filebase'] = None  # self.metadata['filename'][0:5]
        self.metadata['fileseq_number'] = None
        self.metadata['scantype'] = None  # tokenized[5].strip("'").lower()
        # self.metadata['filename'].split('.')[1].lower()
        self.metadata['instrument'] = None
        self.metadata['comment'] = None  # myfile.readline().rstrip()
        self.metadata['scan_description'] = None
        self.metadata['experiment_id'] = None
        self.metadata['fixed_devices'] = None

        # int, for icp data it is translated using the months dict
        self.metadata['month'] = None
        self.metadata['day'] = None  # int
        self.metadata['year'] = None  # int
        self.metadata['start_time'] = None  # str
        self.metadata['epoch'] = None  # float

        # self.metadata['coll1']=None#float(tokenized[0])
        # self.metadata['coll2']=None#float(tokenized[1])
        # self.metadata['coll3']=None#float(tokenized[2])
        # self.metadata['coll4']=None#float(tokenized[3])

        self.metadata['mosaic_monochromator'] = None  # float(tokenized[4])
        self.metadata['mosaic_sample'] = None  # float(tokenized[5])
        self.metadata['mosaic_analyzer'] = None  # float(tokenized[6])

        self.metadata['monochromator_dspacing'] = None  # float(tokenized[3])
        self.metadata['analyzer_dspacing'] = None  # float(tokenized[4])

        self.metadata['wavelength'] = None  # float(tokenized[7])
        self.metadata['ef'] = None  # float(tokenized[2])
        self.metadata['efixed'] = None  # Should be 'ei,ef'#tokenized[4]

        self.metadata['orient1'] = {}
        self.metadata['orient1']['h'] = None  # float(tokenized[7])
        self.metadata['orient1']['k'] = None  # float(tokenized[8])
        self.metadata['orient1']['l'] = None  # float(tokenized[9])
        # ignore "angle" field
        self.metadata['orient2'] = {}
        self.metadata['orient2']['h'] = None  # float(tokenized[11])
        self.metadata['orient2']['k'] = None  # float(tokenized[12])
        self.metadata['orient2']['l'] = None  # float(tokenized[13])

        self.metadata['lattice'] = {}
        self.metadata['lattice']['a'] = None  # float(tokenized[0])
        self.metadata['lattice']['b'] = None  # float(tokenized[1])
        self.metadata['lattice']['c'] = None  # float(tokenized[2])
        self.metadata['lattice']['alpha'] = None  # float(tokenized[3])
        self.metadata['lattice']['beta'] = None  # float(tokenized[4])
        self.metadata['lattice']['gamma'] = None  # float(tokenized[5])

        self.metadata['q_center'] = {}
        self.metadata['q_center']['e_center'] = None  # float(tokenized[0])
        self.metadata['q_center']['h_center'] = None  # (tokenized[0])
        self.metadata['q_center']['k_center'] = None  # (tokenized[1])
        self.metadata['q_center']['l_center'] = None  # (tokenized[2])

        self.metadata['q_step'] = {}
        self.metadata['q_step']['delta_h'] = None  # float(tokenized[3])
        self.metadata['q_step']['delta_k'] = None  # float(tokenized[4])
        self.metadata['q_step']['delta_l'] = None  # float(tokenized[5])
        self.metadata['q_step']['delta_e'] = None  # float(tokenized[1])

        self.metadata['temperature_info'] = {}
        # float(tokenized[5])
        self.metadata['temperature_info']['temperature_start'] = None
        # float(tokenized[6])
        self.metadata['temperature_info']['temperature_step'] = None
        # float(tokenized[6])
        self.metadata['temperature_info']['temperature_units'] = None

        self.metadata['hfield'] = None  # float(tokenized[10])
        self.metadata['extrema'] = {}
        return

    def readimotors(self, myfile):
        # motor1
        tokenized = get_tokenized_line(myfile)
    #    print tokenized
        motor1 = {'start': float(tokenized[1])}
        motor1['step'] = float(tokenized[2])
        motor1['end'] = float(tokenized[3])
        self.metadata['motor1'] = motor1

    # motor2
        tokenized = get_tokenized_line(myfile)
    #    print tokenized
        motor2 = {'start': float(tokenized[1])}
        motor2['step'] = float(tokenized[2])
        motor2['end'] = float(tokenized[3])
        self.metadata['motor2'] = motor2

    # motor3
        tokenized = get_tokenized_line(myfile)
    #    print tokenized
        motor3 = {'start': float(tokenized[1])}
        motor3['step'] = float(tokenized[2])
        motor3['end'] = float(tokenized[3])
        self.metadata['motor3'] = motor3

    # motor4
        tokenized = get_tokenized_line(myfile)
    #    print tokenized
        motor4 = {'start': float(tokenized[1])}
        motor4['step'] = float(tokenized[2])
        motor4['end'] = float(tokenized[3])
        self.metadata['motor4'] = motor4

    # motor5
        tokenized = get_tokenized_line(myfile)
    #    print tokenized
        motor5 = {'start': float(tokenized[1])}
        motor5['step'] = float(tokenized[2])
        motor5['end'] = float(tokenized[3])
        self.metadata['motor5'] = motor5

    # motor6
        tokenized = get_tokenized_line(myfile)
    #    print tokenized
        motor6 = {'start': float(tokenized[1])}
        motor6['step'] = float(tokenized[2])
        motor6['end'] = float(tokenized[3])
        self.metadata['motor6'] = motor6
        # skip line describing Motor Start Step End
        lineStr = myfile.readline()
        return

    def readimetadata(self, myfile):
        # experiment info
        tokenized = get_tokenized_line(myfile)
        # collimations=[] #in stream order

        # self.metadata={}
        self.data['premonocoll'] = float(
            tokenized[0])*N.ones(self.metadata['pts_planned'], 'Float64')
        self.data['postmonocoll'] = float(
            tokenized[1])*N.ones(self.metadata['pts_planned'], 'Float64')
        self.data['preanacoll'] = float(
            tokenized[2])*N.ones(self.metadata['pts_planned'], 'Float64')
        self.data['postanacoll'] = float(
            tokenized[3])*N.ones(self.metadata['pts_planned'], 'Float64')
        # collimations.append(float(tokenized[1]))
        # collimations.append(float(tokenized[2]))
        # collimations.append(float(tokenized[3]))

        # mosaic=[] #order is monochromator, sample, mosaic
        # self.metadata={}
        self.metadata['mosaic_monochromator'] = float(tokenized[4])
        self.metadata['mosaic_sample'] = float(tokenized[5])
        self.metadata['mosaic_analyzer'] = float(tokenized[6])

        # self.metadata={}
        self.metadata['wavelength'] = float(tokenized[7])

        # self.metadata={}
        self.metadata['temperature_start'] = float(tokenized[8])
        self.metadata['temperature_step'] = float(tokenized[9])

        # self.metadata={}
        self.metadata['hfield'] = float(tokenized[10])
        #print tokenized
        # skip field names of experiment info
        lineStr = myfile.readline()
        self.readimotors(myfile)
        return

    def readqmetadata(self, myfile):
        # experiment info
        tokenized = get_tokenized_line(myfile)

        self.data['premonocoll'] = float(
            tokenized[0])*N.ones(self.metadata['pts_planned'], 'Float64')
        self.data['postmonocoll'] = float(
            tokenized[1])*N.ones(self.metadata['pts_planned'], 'Float64')
        self.data['preanacoll'] = float(
            tokenized[2])*N.ones(self.metadata['pts_planned'], 'Float64')
        self.data['postanacoll'] = float(
            tokenized[3])*N.ones(self.metadata['pts_planned'], 'Float64')

        self.metadata['mosaic_monochromator'] = float(tokenized[4])
        self.metadata['mosaic_sample'] = float(tokenized[5])
        self.metadata['mosaic_analyzer'] = float(tokenized[6])

        # self.metadata['orient1']={}
        self.metadata['orient1']['h'] = float(tokenized[7])
        self.metadata['orient1']['k'] = float(tokenized[8])
        self.metadata['orient1']['l'] = float(tokenized[9])
        # ignore "angle" field
        # self.metadata['orient2']={}
        self.metadata['orient2']['h'] = float(tokenized[11])
        self.metadata['orient2']['k'] = float(tokenized[12])
        self.metadata['orient2']['l'] = float(tokenized[13])

        # skip line with field names
        myfile.readline()
        tokenized = get_tokenized_line(myfile)
        self.metadata['lattice']['a'] = float(tokenized[0])
        self.metadata['lattice']['b'] = float(tokenized[1])
        self.metadata['lattice']['c'] = float(tokenized[2])
        self.metadata['lattice']['alpha'] = float(tokenized[3])
        self.metadata['lattice']['beta'] = float(tokenized[4])
        self.metadata['lattice']['gamma'] = float(tokenized[5])
        # skip line with field names
        myfile.readline()
        tokenized = get_tokenized_line(myfile)
        self.metadata['q_center']['e_center'] = float(tokenized[0])
        self.metadata['q_step']['delta_e'] = float(tokenized[1])
        self.metadata['ef'] = float(tokenized[2])
        self.metadata['monochromator_dspacing'] = float(tokenized[3])
        self.metadata['analyzer_dspacing'] = float(tokenized[4])
        self.metadata['temperature_start'] = float(tokenized[5])
        self.metadata['temperature_step'] = float(tokenized[6])
        tokenized = get_tokenized_line(myfile)
        if tokenized[4].lower() == 'ea':
            self.metadata['efixed'] = 'ef'
        elif tokenized[4].lower() == 'em':
            self.metadata['efixed'] = 'ei'
        tokenized = get_tokenized_line(myfile)
        self.metadata['q_center']['h_center'] = float(tokenized[0])
        self.metadata['q_center']['k_center'] = float(tokenized[1])
        self.metadata['q_center']['l_center'] = float(tokenized[2])
        self.metadata['q_step']['delta_h'] = float(tokenized[3])
        self.metadata['q_step']['delta_k'] = float(tokenized[4])
        self.metadata['q_step']['delta_l'] = float(tokenized[5])
        self.metadata['hfield'] = float(tokenized[6])
        # skip line describing fields
        linestr = myfile.readline()
        return

    def readbmetadata(self, myfile):
        self.readqmetadata(myfile)
        self.readimotors(myfile)
        return

    def get_columnmetadatas(self, myfile):
        # get first line
        tokenized = get_tokenized_line(myfile)
        self.columndict = {}
        self.columnlist = []
        for i in N.arange(len(tokenized)):
            field = tokenized[i].lower()
            if field == 'Q(x)'.lower():
                field = 'h'  # field='Qx'.lower()
            if field == 'Q(y)'.lower():
                field = 'k'  # field='Qy'.lower()
            if field == 'Q(z)'.lower():
                field = 'l'  # field='Qz'.lower()
            if field == 'T-act'.lower():
                field = 'temp'  # field='Temp'.lower()
            self.columndict[field] = []
            self.columnlist.append(field)
        return

    def determinefiletype(self, myfile):
        # get first line
        tokenized = get_tokenized_line(myfile)
        print(tokenized)
        # Handling for older files whose dates are 'day-month-year' e.g. '23-apr-1994'
        thedate = tokenized[1].split('-')
        if len(thedate) > 1:
            # we want order: month, day, year
            # inserting in reverse order: year --> day --> month
            tokenized.pop(1)  # remove the date string
            tokenized.insert(1, thedate[2])
            tokenized.insert(1, thedate[0])
            tokenized.insert(1, thedate[1])

        self.metadata['monitor_base'] = float(tokenized[6])
        self.metadata['monitor_prefactor'] = float(tokenized[7])
        self.metadata['monitor'] = self.metadata['monitor_base'] * \
            self.metadata['monitor_prefactor']
        if tokenized[8].strip("'").lower() == 'neut':
            # tokenized[8].strip("'").lower()
            self.metadata['count_type'] = 'monitor'
        else:
            # tokenized[8].strip("'").lower()
            self.metadata['count_type'] = 'time'
        self.metadata['pts_planned'] = int(tokenized[9])
        self.metadata['filename'] = tokenized[0].strip("'")
        self.metadata['filebase'] = self.metadata['filename'][0:5]
        self.metadata['scantype'] = tokenized[5].strip("'").lower()
        self.metadata['instrument'] = self.metadata['filename'].split('.')[
            1].lower()

        month_str = tokenized[1].strip("\'").lower()

        # tokenized[1].strip("\'").lower()
        self.metadata['month'] = months[month_str]
        self.metadata['day'] = int(tokenized[2].strip("\'"))
        self.metadata['year'] = int(tokenized[3].strip("\'"))
        self.metadata['start_time'] = tokenized[4].strip("\'")

        # skip over names of fields
        lineStr = myfile.readline()
        #comment and filename
        self.metadata['comment'] = myfile.readline().rstrip()
        return self.metadata['scantype']

    def readcolumns(self, myfile):
        self.get_columnmetadatas(myfile)
        # get the names of the fields
    #   prepare to read the data
        count = 0
        while 1:
            lineStr = myfile.readline()
            if not(lineStr):
                break
            if lineStr[0] != "#":
                count = count + 1
                strippedLine = lineStr.rstrip().lower()
                tokenized = strippedLine.split()
                for i in range(len(tokenized)):
                    field = self.columnlist[i]
                    self.update_extrema(field, float(tokenized[i]))
                    self.columndict[field].append(float(tokenized[i]))
        return

    def get_columnmetadatas_bt7(self, tokenized):
        # get first line
        #    tokenized=get_tokenized_line(myfile)
        self.columndict = {}
        self.columnlist = []
        self.timestamp_flag = True
        # originally set the timestamp flag to True, if it turns out that there is not timestamp in the file, then create one using the time field
        for i in N.arange(1, len(tokenized)):
            field = tokenized[i]
            if field == 'QX':
                field = 'h'  # field='Qx'.lower()
            if field == 'QY':
                field = 'k'  # field='Qy'.lower()
            if field == 'QZ':
                field = 'l'  # field='Qz'.lower()
            if field == 'T-act':
                field = 'temp'  # field='Temp'.lower()
            self.columndict[field] = []
            self.columnlist.append(field)
        # In old bt7 files, there was no timestamp, so add one for those, otherwise use the one in the file
        if self.columndict.has_key('timestamp') == False:
            self.timestamp_flag = False
            self.columnlist.append('timestamp')
            #print 'no timestamp'
            self.columndict['timestamp'] = []
        return

    def range_parser(self, rangestr, scan_description):
        #print rangestr
        range_split = rangestr.split('range=')
        fields = range_split[1].split('=')
        #print fields
        if fields[0] == 'e':
            toks = fields[1].split()
            if len(toks) == 3:
                scan_description['range']['e']['start'] = float(toks[0])
                scan_description['range']['e']['stop'] = float(toks[1])
            else:
                scan_description['range']['e']['center'] = float(toks[0])
                scan_description['range']['e']['step'] = float(toks[1])

        if fields[0] == 'q':
            toks = fields[1].split()
            #print 'toks',toks
            if len(toks) == 3:
                start = toks[0].split('~')
                scan_description['range']['q']['start'] = {}
                scan_description['range']['q']['stop'] = {}
                scan_description['range']['q']['start']['h'] = float(start[0])
                scan_description['range']['q']['start']['k'] = float(start[1])
                scan_description['range']['q']['start']['l'] = float(start[2])
                stop = toks[0].split('~')
                scan_description['range']['q']['stop']['h'] = float(stop[0])
                scan_description['range']['q']['stop']['k'] = float(stop[1])
                scan_description['range']['q']['stop']['l'] = float(stop[2])
            else:
                start = toks[0].split('~')
                scan_description['range']['q']['center'] = {}
                scan_description['range']['q']['step'] = {}
                scan_description['range']['q']['center']['h'] = float(start[0])
                scan_description['range']['q']['center']['k'] = float(start[1])
                scan_description['range']['q']['center']['l'] = float(start[2])
                stop = toks[0].split('~')
                scan_description['range']['q']['step']['h'] = float(stop[0])
                scan_description['range']['q']['step']['k'] = float(stop[1])
                scan_description['range']['q']['step']['l'] = float(stop[2])

        #print 'Range', scan_description['range']
        return

    def parse_scan(self, scanstr):
        scan_description = {}
        scan_description['scan_string'] = scanstr
        scan_description['range'] = {}
        scan_description['range']['e'] = {}
        scan_description['range']['q'] = {}

        toks = scanstr.split(':')
        for i in range(1, len(toks)):
            if toks[i][0] == 'r':
                self.range_parser(toks[i], scan_description)
            else:
                fields = toks[i].split('=')
                try:
                    scan_description[fields[0]] = float(fields[1])
                except ValueError:
                    scan_description[fields[0]] = (fields[1])
        return scan_description

    def readbt7(self, myfile):
        # get first line
        myFlag = True
        # self.metadata={}
        self.header = []
        returnline = ['']
        while myFlag:
            tokenized = get_tokenized_line(myfile, returnline=returnline)
            #print tokenized
            if tokenized == []:
                tokenized = ['']
            if tokenized[0].lower() == "#Date".lower():
                pass
            if tokenized[0].lower() == "#Date".lower():
                date_tokens = tokenized[1].split('-')
                month = int(date_tokens[1].strip("\'"))
                day = int(date_tokens[2].strip("\'"))
                year = int(date_tokens[0].strip("\'"))
                stime = tokenized[2].strip("\'")
                stimetok = stime.split(':')
                hour = int(stimetok[0])
                minute = int(stimetok[1])
                second = int(stimetok[2])
                self.metadata['month'] = int(date_tokens[1].strip("\'"))
                self.metadata['day'] = int(date_tokens[2].strip("\'"))
                self.metadata['year'] = int(date_tokens[0].strip("\'"))
                self.metadata['start_time'] = tokenized[2].strip("\'")
            elif tokenized[0].lower() == "#Epoch".lower():
                # timeobj=date.datatetime(year,month,day,hour,minute,second)
                Epoch = float(tokenized[1])
                # timeobj=mx.DateTime.DateTimeFromTicks(ticks=Epoch) #what I originally used
                timeobj = datetime.datetime.fromtimestamp(Epoch)
                #print 'timeobj ',timeobj
                #print 'Epoch ', Epoch
                self.metadata['epoch'] = Epoch  # timeobj
                #print self.metadata
            elif tokenized[0].lower() == "#InstrName".lower():
                self.metadata['instrument'] = tokenized[1].lower()
            elif tokenized[0].lower() == "#ExptID".lower():
                self.metadata['experiment_id'] = tokenized[1].lower()
            elif tokenized[0].lower() == "#Fixed".lower():
                self.metadata['fixed_devices'] = tokenized[1:]
            elif tokenized[0].lower() == "#Filename".lower():
                self.metadata['filename'] = tokenized[1]
                #print 'filename ', tokenized[1]
                pattern = re.compile(
                    '^(?P<base>[^.]*?)(?P<seq>[0-9]*)(?P<ext>[.].*)?$')
                match = pattern.match(tokenized[1]+'.bt7')
                dict((a, match.group(a)+"") for a in ['base', 'seq', 'ext'])
                #print 'filebase ',match.group('base')
                self.metadata['filebase'] = match.group('base')
                self.metadata['fileseq_number'] = match.group('seq')
            elif tokenized[0].lower() == "#Comment".lower():
                mycomment = ''
                for i in range(1, len(tokenized)):
                    mycomment = mycomment+' '+tokenized[i]
                self.metadata['comment'] = mycomment
            elif tokenized[0].lower() == "#MonoSpacing".lower():
                self.metadata['monochromator_dspacing'] = float(tokenized[1])
            elif tokenized[0].lower() == "#AnaSpacing".lower():
                self.metadata['analyzer_dspacing'] = float(tokenized[1])
            elif tokenized[0].lower() == "#TemperatureUnits".lower():
                self.metadata['temperature_units'] = tokenized[1]
            elif tokenized[0].lower() == "#Orient".lower():
                self.metadata['orient1']['h'] = float(tokenized[1])
                self.metadata['orient1']['k'] = float(tokenized[2])
                self.metadata['orient1']['l'] = float(tokenized[3])
                self.metadata['orient2']['h'] = float(tokenized[4])
                self.metadata['orient2']['k'] = float(tokenized[5])
                self.metadata['orient2']['l'] = float(tokenized[6])
            elif tokenized[0].lower() == "#Lattice".lower():
                self.metadata['lattice']['a'] = float(tokenized[1])
                self.metadata['lattice']['b'] = float(tokenized[2])
                self.metadata['lattice']['c'] = float(tokenized[3])
                self.metadata['lattice']['alpha'] = float(tokenized[4])
                self.metadata['lattice']['beta'] = float(tokenized[5])
                self.metadata['lattice']['gamma'] = float(tokenized[6])
            elif tokenized[0].lower() == "#AnalyzerDetectorMode".lower():
                self.metadata['analyzerdetectormode'] = tokenized[2].lower()
            elif tokenized[0].lower() == "#Reference".lower():
                self.metadata['count_type'] = tokenized[2].lower()
            elif tokenized[0].lower() == "#Signal".lower():
                self.metadata['signal'] = tokenized[2].lower()
            elif tokenized[0].lower() == "#AnalyzerDetectorDevicesOfInterest".lower():
                self.metadata['AnalyzerDetectorDevicesOfInterest'.lower()
                              ] = tokenized[1:]
            elif tokenized[0].lower() == "#AnalyzerDDGroup".lower():
                self.metadata['AnalyzerDDGroup'.lower()] = tokenized[1:]
            elif tokenized[0].lower() == "#AnalyzerDoorDetectorGroup".lower():
                self.metadata['AnalyzerDoorDetectorGroup'.lower()
                              ] = tokenized[1:]
            elif tokenized[0].lower() == "#AnalyzerSDGroup".lower():
                self.metadata['AnalyzerSDGroup'.lower()] = tokenized[1:]
            elif tokenized[0].lower() == "#AnalyzerPSDGroup".lower():
                self.metadata['AnalyzerPSDGroup'.lower()] = tokenized[1:]
            elif tokenized[0].lower() == "#AnalyzerFocusMode".lower():
                self.metadata['analyzerfocusmode'.lower()] = tokenized[1]
            elif tokenized[0].lower() == "#MonoVertiFocus".lower():
                self.metadata['monovertifocus'.lower()] = tokenized[1]
            elif tokenized[0].lower() == "#MonoHorizFocus".lower():
                self.metadata['monohorizfocus'.lower()] = tokenized[1]
            elif tokenized[0].lower() == "#FixedE".lower():
                try:
                    self.metadata['efixed'.lower()] = tokenized[1]
                except IndexError:
                    pass
                try:
                    self.metadata['ef'.lower()] = float(tokenized[2])
                except IndexError:
                    pass
            elif tokenized[0].lower() == "#ScanDescr".lower():
                scanstr = ''
                for i in range(1, len(tokenized)):
                    scanstr = scanstr+tokenized[i]+' '
                self.metadata['scan_description'] = scanstr
                #print 'scanstr',scanstr
                myparser = scanparser.scanparser(scanstr)
                self.metadata['varying'] = myparser.get_varying()
                self.metadata['ranges'] = myparser.ranges
                #print 'parsed'
                # if self.metadata['filebase']!='fpx':
                #    self.additional_metadata['parsed_scandescription']=self.parse_scan(scanstr)

                # CAN'T SEEM TO PARSE fpx files, but if the filename is broken as in the last cycle, then how do I know?
                # Better soln is to fix parser
                #print self.metadata['scan_description']['range']
            else:
                currfield = tokenized[0].lower().lower().strip('#')
                self.additional_metadata[currfield] = (tokenized[1:])
            if tokenized[0] != '#Columns'.lower():
                self.header.append(returnline[0])
            if tokenized[0] == '#Columns'.lower():
                self.get_columnmetadatas_bt7(tokenized)
                count = 0
                try:
                    lines = int(self.lines)
                except:
                    lines = N.Inf
                while 1:
                    lineStr = myfile.readline()
                    if not(lineStr):
                        break
                    if lineStr[0] != "#":
                        if count >= lines:
                            break
                        strippedLine = lineStr.rstrip()
                        tokenized = strippedLine.split()
                        for i in range(len(tokenized)):
                            field = self.columnlist[i]
                            try:
                                if field.lower() == 'time' and self.timestamp_flag == False:
                                    # timedelta=mx.DateTime.DateTimeDelta(0,0,0,float(tokenized[i])) #orig
                                    # self.columndict['timestamp'].append((timeobj+timedelta).ticks()) #orig
                                    # timestamp_flag is True if the timestamp is already given in the file
                                    timedelta = datetime.timedelta(
                                        seconds=float(tokenized[i]))
                                    self.columndict['timestamp'].append(
                                        mktime((timeobj+timedelta).timetuple()))
                                    timeobj = timeobj+timedelta
                                self.update_extrema(field, float(tokenized[i]))
                                self.columndict[field].append(
                                    float(tokenized[i]))
                            except ValueError:
                                # update_extrema(self, field, tokenized[i]) # is it appropriate for non-number fields?
                                self.columndict[field].append((tokenized[i]))
                        count = count+1
                myFlag = False
        if len(self.columndict[self.columnlist[0]]) == 0:
            self.columndict = {}
            self.columnlist = []
            # This is a drastic step, but if the file is empty, then no point in even recording the placeholders
        #print self.columndict['Qx']
        #print self.columnlist
        return

    def readbt4(self, myfile):
        # Assumes all metadata has already been read in. The first line read
        # should be the column headers
        myFlag = True
        returnline = ['']
        self.get_columnmetadatas(myfile)

        #field_names = get_tokenized_line(myfile)
        # for field in field_names:
        #        self.columndict[field] = []

        while myFlag:
            tokenized = get_tokenized_line(myfile)
            if tokenized == None or tokenized == []:
                break

            if len(tokenized) > 1:
                for i in range(len(self.columnlist)):
                    self.update_extrema(
                        self.columnlist[i], float(tokenized[i]))
                    self.columndict[self.columnlist[i]].append(
                        float(tokenized[i]))

        return

    def readbuffer(self, filename, fileobj=None, lines=N.Inf, friendly_name=None):

        self.lines = lines
        myfile = open(filename, 'r') if fileobj is None else fileobj
        filestr = filename if (friendly_name is None) else friendly_name
        self.instrument = os.path.splitext(filestr)[1].split('.')[1].lower()
        self.metadata['extrema'] = {}

        if self.instrument in ['bt2', 'bt4', 'bt9', 'ng5']:
            # Determine FileType
            self.determinefiletype(myfile)
            if self.metadata['scantype'].lower() == 'i':
                print("calling readibuffer")
                self.readimetadata(myfile)
            if self.metadata['scantype'].lower() == 'b':
                print("calling readbbuffer")
                self.readbmetadata(myfile)
            if self.metadata['scantype'].lower() == 'q':
                print("calling readqbuffer")
                self.readqmetadata(myfile)

            # read columns
            if self.instrument == 'bt4':
                self.readbt4(myfile)
            else:
                self.readcolumns(myfile)

            myfile.close()
            mydata = Data(self.metadata, self.columndict)
            #print self.metadata
            #print self.columnlist
            filename = os.path.split(filestr)[-1]
            self.metadata['filename'] = filename
            #print 'filename ', tokenized[1]
            pattern = re.compile(
                '^(?P<base>[^.]*?)(?P<seq>[0-9]*)(?P<ext>[.].*)?$')
            match = pattern.match(filename)
            dict((a, match.group(a)+"") for a in ['base', 'seq', 'ext'])
            #print 'filebase ',match.group('base')
            self.metadata['filebase'] = match.group('base')
            self.metadata['fileseq_number'] = match.group('seq')
        else:
            #instrument is bt7
            self.readbt7(myfile)
            # self.readbt7columns(myfile)
            myfile.close()
            if self.header == None:
                self.header = []
            mydata = Data(self.metadata, self.columndict,
                          self.header, self.additional_metadata)
            # repair ice files with missing file names
            if mydata.metadata['filename'] == None:
                filename = os.path.split(filename)[-1]
                self.metadata['filename'] = filename
                #print 'filename ', tokenized[1]
                pattern = re.compile(
                    '^(?P<base>[^.]*?)(?P<seq>[0-9]*)(?P<ext>[.].*)?$')
                match = pattern.match(filename)
                dict((a, match.group(a)+"") for a in ['base', 'seq', 'ext'])
                #print 'filebase ',match.group('base')
                self.metadata['filebase'] = match.group('base')
                self.metadata['fileseq_number'] = match.group('seq')

        return mydata

    def update_extrema(self, field, value):
        if not field in self.metadata['extrema'].keys():
            # if it doesn't have a min, it shouldn't have a max either.
            # if no min/max, then make the current value the min and max
            self.metadata['extrema'][field] = [value, value]
        else:
            if value < self.metadata['extrema'][field][0]:  # val < min
                self.metadata['extrema'][field][0] = value
            if value > self.metadata['extrema'][field][1]:  # val > max
                self.metadata['extrema'][field][1] = value


class Data(object):
    def __init__(self, metadata, data, header=None, additional_metadata=None):
        self.metadata = metadata
        self.data = data
        self.header = header
        self.additional_metadata = additional_metadata

    def get_monitor(self):
        return self.metadata['monitor']
    # @property
    # def monitor(self):
    #    "The monitor rate"
    #    def fget(self):
    #        return self.metadata['monitor']
    # def get_filetype(self):
    # return self.metadata['filetype']
    # def get_data_fields(self):
    #    return self.data['columnlist']

    def get_motor1(self):
        return self.metadata['motor1']

    def get_motor2(self):
        return self.metadata['motor2']

    def get_motor3(self):
        return self.metadata['motor3']

    def get_motor4(self):
        return self.metadata['motor4']

    def get_motor5(self):
        return self.metadata['motor5']

    def get_motor6(self):
        return self.metadata['motor6']

    def get_field(self, field):
        return self.data[field]

    def gen_motor1_arr(self):
        motor = self.get_motor1()
        step = motor['step']
        start = motor['start']
        if step == 0.0:
            res = start*N.ones((1, self.npts), 'd')
        else:
            res = N.arange(start, motor['end'], step)
        return res

    def gen_motor2_arr(self):
        motor = self.get_motor2()
        step = motor['step']
        start = motor['start']
        if step == 0.0:
            res = start*N.ones((1, self.npts), 'd')
        else:
            res = N.arange(start, motor['end'], step)
        return res

    def gen_motor3_arr(self):
        motor = self.get_motor3()
        step = motor['step']
        start = motor['start']
        if step == 0.0:
            res = start*N.ones((1, self.npts), 'd')
        else:
            res = N.arange(start, motor['end'], step)
        return res

    def gen_motor4_arr(self):
        motor = self.get_motor4()
        step = motor['step']
        start = motor['start']
        if step == 0.0:
            res = start*N.ones((1, self.npts), 'd')
        else:
            res = N.arange(start, motor['end'], step)
        return res

    def gen_motor5_arr(self):
        motor = self.get_motor5()
        step = motor['step']
        start = motor['start']
        if step == 0.0:
            res = start*N.ones((1, self.npts), 'd')
        else:
            res = N.arange(start, motor['end'], step)
        return res

    def gen_motor6_arr(self):
        motor = self.get_motor6()
        step = motor['step']
        start = motor['start']
        if step == 0.0:
            res = start*N.ones((1, self.npts), 'd')
        else:
            res = N.arange(start, motor['end'], step)
        return res


#   self.columndict[field]

    # count_type=property(get_count_type)
    # filetype=property(get_filetype)
    # npts=property(get_npts)
    motor1 = property(get_motor1)
    motor2 = property(get_motor2)
    motor3 = property(get_motor3)
    motor4 = property(get_motor4)
    motor5 = property(get_motor5)
    motor6 = property(get_motor6)
    # data_fields=property(get_data_fields)
    # monitor=property(get_monitor)


def num2string(num):
    numstr = None
    if num < 10:
        numstr = '00'+str(num)
    elif (num >= 10 & num < 100):
        numstr = '0'+str(num)
    elif (num > 100):
        numstr = str(num)
    return numstr


if __name__ == '__main__':
    myfilestr = r'EscanQQ7HorNSF91831.bt7'
    mydatareader = datareader()
    # mydata=mydatareader.readbuffer(myfilestr,lines=91)
    mydata = mydatareader.readbuffer(myfilestr)

    print(mydata.data['timestamp'])
    print(mydata.data.keys())
    print('done')
    print(mydata.metadata['varying'])
    
    if 0:
        # bragg
        myfilestr = r'c:\sqltest\\nuc10014.bt9'
    if 0:
        # qbuff
        myfilestr = r'c:\sqltest\\mnl1p004.ng5'

    if 0:
        mydatareader = datareader()
        mydata = mydatareader.readbuffer(myfilestr, lines=91)