# This program is public domain

# Author: Paul Kienzle
# Initial version: William Ratcliff

"""
ICP data reader.

summary(filename)  - reads the header information
read(filename) - reads header information and data
"""

import numpy as N
import datetime

def readdata(fh):
    """
    Read ICP data, including PSD data if lines contain commas.
    """
    rows = []
    blocks = []

    line = fh.readline().rstrip()
    while line != '':
        # While it might be easy to check for a comment mark on the beginning
        # of the line, supporting this is ill-adviced.  First, users should
        # be strongly discouraged from modifying the original data.
        # Second, sequencing against the automatically generated motor
        # columns will become more complicated.  Let's make life easier
        # and put the masking in the application rather than the data reader.

        # Process the instrument configuration line and move to the next line
        rows.append([float(val) for val in line.split()])
        line = fh.readline().rstrip()

        # Build up a multiline detector block by joining all lines that
        # end with a comma.
        b = []
        while line[-1]==',':
            b += line[1:-1].split(',')
            line = fh.readline().rstrip()
        # Process the next line which doesn't end in a comma.  If we have
        # already seen lines with commas, then this line is a continuation
        # of the block.  If we haven't seen lines with commas yet, check if
        # the whole block is on a single line.
        if b is not []:
            # Extending multiline block
            b += line[1:].split(',')
            line = fh.readline().rstrip()
        elif line.find(',') > 0:
            # The whole block is on one line
            b = line[1:].split(',')
            line = fh.readline().rstrip()

        if b is not []:
            # Have a detector block so add it
            blocks.append(N.array([int(v) for v in b]))
        elif blocks is not []:
            # Oops...missing a detector block.  Set it to zero counts
            # of the same size as the last block
            blocks.append(N.zeros(blocks[-1].shape,'i'))
        # Otherwise no detector block and don't need one
        # Note: this strategy fails to identify that the first 
        # detector block is missing

    # recover from missing leading detector blocks
    if len(blocks) > 0 and len(blocks) < len(rows):
        blank = N.zeros(blocks[0].shape,'i')
        blocks = [blank]*(len(blocks)-len(rows)) + blocks

    # Convert data to arrays
    X = N.array(rows, 'f')
    Z = N.array(blocks)
    return X.T,Z.T


def get_tokenized_line(file):
    """
    Read the next line of text into a set of words.
    """
    line=file.readline()
    return line.split()

def get_quoted_tokens(file):
    """
    Build a token list from a line which can be a mix of quoted strings
    and unquoted values separated by spaces.  Uses single quotes only.
    Does not test for escaped single quotes.
    """
    line = file.readline()
    tokens = []
    curtoken=None
    inquote = False
    for c in line:
        if c == "'":
            if inquote:
                tokens.append("".join(curtoken))
                curtoken = None
                inquote = False
            else:
                curtoken = []
                inquote = True
        elif inquote:
            curtoken.append(c)
        elif c.isspace():
            if curtoken != None:
                tokens.append("".join(curtoken))
                curtoken = None
        else:
            if curtoken == None:
                curtoken = [c]
            else:
                curtoken.append(c)
                
    return tokens

def readheader1(file):
    """
    Read the tow line summary at the start of the ICP data files.
    """
    tokens = get_quoted_tokens(file)
    header={}
    header['filename']=tokens[0]
    timestamp = datetime.datetime(2000,1,1)
    header['date']=timestamp.strptime(tokens[1],'%b %d %Y %H:%M')
    header['scantype'] = tokens[2]
    header['prefactor'] = float(tokens[3])
    header['monitor']=float(tokens[4])
    header['count_type']=tokens[5]
    header['points']=int(tokens[6])
    header['data_type']=tokens[7]
    #skip over names of fields 
    file.readline()
    #comment and polarization
    line = file.readline()
    polarized_index = line.find("F1: O", 52)
    if polarized_index > 0:
        header['comment'] = line[:polarized_index].rstrip()
        F1 = '+' if line.find("F1: ON", 52)>0 else '-'
        F2 = '+' if line.find("F2: ON", 52)>0 else '-'
        header['polarization'] = F1+F2
    else:
        header['comment'] = line.rstrip()
        header['polarization'] = ""
    return header


def readiheader(file):
    """
    Read I-buffer structure, excluding motors.
    """
    # Read in fields and field names
    tokenized=get_tokenized_line(file)
    fieldnames = file.readline()
    #print tokenized
    #print fieldnames

    header = {}
    if "Collimation" in fieldnames:
        #Collimation    Mosaic    Wavelength   T-Start   Incr.   H-field #Det    
        collimations=[] #in stream order
        collimations.append(float(tokenized[0]))
        collimations.append(float(tokenized[1]))
        collimations.append(float(tokenized[2]))
        collimations.append(float(tokenized[3]))
        mosaic=[] #order is monochromator, sample, mosaic
        mosaic.append(float(tokenized[4]))
        mosaic.append(float(tokenized[5]))
        mosaic.append(float(tokenized[6]))
        header['collimations']=collimations
        header['mosaic']=mosaic
        header['wavelength']=float(tokenized[7])
        header['Tstart']=float(tokenized[8])
        header['Tstep']=float(tokenized[9])
        header['Hfield']=float(tokenized[10])
    else:
        #Mon1    Exp   Dm      Wavel  T-Start  Incr. Hf(Tesla) #Det SclFac
        header['Mon1']=float(tokenized[0])
        header['Exp']=float(tokenized[1])
        header['Dm']=float(tokenized[2])
        header['wavelength']=float(tokenized[3])
        header['Tstart']=float(tokenized[4])
        header['Tstep']=float(tokenized[5])
        header['Hfield']=float(tokenized[6])
        header['numDet']=float(tokenized[7])
        header['SclFac']=float(tokenized[8])

    return header


def readqheader(file):
    """
    Read Q-buffer structure.
    """
    #experiment info
    tokenized=get_tokenized_line(file)
    header = {}
    collimations=[] #in stream order
    collimations.append(float(tokenized[0]))
    collimations.append(float(tokenized[1]))
    collimations.append(float(tokenized[2]))
    collimations.append(float(tokenized[3]))
    header['collimations']=collimations
    mosaic=[] #order is monochromator, sample, mosaic
    mosaic.append(float(tokenized[4]))
    mosaic.append(float(tokenized[5]))
    mosaic.append(float(tokenized[6]))
    header['mosaic']=mosaic
    orient1=[]
    orient1.append(float(tokenized[7]))
    orient1.append(float(tokenized[8]))
    orient1.append(float(tokenized[9]))
    header['orient1']=orient1
    #ignore the "angle" field
    orient2=[]
    orient2.append(float(tokenized[11]))
    orient2.append(float(tokenized[12]))
    orient2.append(float(tokenized[13]))
    header['orient2']=orient2
    #skip line with field names
    file.readline()
    tokenized=get_tokenized_line(file)
    lattice={}
    lattice['a']=float(tokenized[0])
    lattice['b']=float(tokenized[1])
    lattice['c']=float(tokenized[2])
    lattice['alpha']=float(tokenized[3])
    lattice['beta']=float(tokenized[4])
    lattice['gamma']=float(tokenized[5])
    header['lattice']=lattice
    #skip line with field names
    file.readline()
    tokenized=get_tokenized_line(file)
    header['ecenter']=float(tokenized[0])
    header['deltae']=float(tokenized[1])
    header['ef']=float(tokenized[2])
    header['monochromator_dspacing']=float(tokenized[3])
    header['analyzer_dspacing']=float(tokenized[4])
    header['tstart']=float(tokenized[5])
    header['tstep']=float(tokenized[6])
    tokenized=get_tokenized_line(file)
    header['Efixed']=tokenized[4]
    tokenized=get_tokenized_line(file)
    qcenter=[]
    qstep=[]
    qcenter.append(float(tokenized[0]))
    qcenter.append(float(tokenized[1]))
    qcenter.append(float(tokenized[2]))
    qstep.append(float(tokenized[3]))
    qstep.append(float(tokenized[4]))
    qstep.append(float(tokenized[5]))
    header['qcenter']=qcenter
    header['qstep']=qstep
    header['hfield']=float(tokenized[6])
    #skip line describing fields
    file.readline()
    return


def readmotors(file):
    """
    Read the 6 motor lines, returning a dictionary of
    motor names and start-step-stop values.
    E.g.,
    
    M = _readmotors(file)
    print M['a1'].start
    """
    motors = {}
    while True:  # read until 'Mot:' line
        words=get_tokenized_line(file)
        if words[0] == 'Mot:': break
        arange=dict(start=float(words[1]),
                    step=float(words[2]),
                    stop=float(words[3]))
        name = words[0] if not words[0].isdigit() else 'a'+words[0]
        motors[name] = arange
    return motors

def readcolumnheaders(file):
    """
    Get a list of column names. Transform the names of certain
    columns to make our lives easier elsewhere:
          #1 COUNTS -> counts
          #2 COUNTS -> counts2
          MON -> monitor
          MIN -> time
          Q(x) -> qx, Q(y) -> qy, Q(z) -> qz
    All column names are uppercase.
    """
    line = file.readline()
    line = line.lower()
    for (old,new) in (('#1 counts','counts'),
                      ('#2 counts','counts2'),
                      (' mon ',' monitor '),
                      (' min ',' time '),
                      ('(',''),
                      (')',''),
                      ):
        line = line.replace(old,new)
    return line.split()


def readcolumns(file, columns):
    '''
    Read and parse ICP data columns listed in columns.  Return a dict of
    column name: vector.  If using a position sensitive detector, return 
    an array of detector values x scan points.
    '''
    values,detector = readdata(file)
    return dict(zip(columns,values)),detector

def genmotorcolumns(columns,motors):
    """
    Generate vectors for each of the motors if a vector is not
    already stored in the file.
    """
    n = len(columns['counts'])
    for (M,R) in motors.iteritems():
        if M not in columns:
            if R['step'] != 0.:
                vector = N.arange(R['start'],R['step'],R['stop'])
                vector = vector[:n]+0  # truncate to # points measured
            else:
                vector = R['start'] * N.ones(n)
            columns[M] = vector
    pass

def parseheader(file):
    """
    Read and parse ICP header information
    """
    # Determine FileType
    fields = readheader1(file)
    scantype = fields['scantype']
    if scantype=='I':
        fields.update(readiheader(file))
        fields['motors'] = readmotors(file)
    elif scantype=='Q':
        fields.update(readqheader(file))
    elif scantype=='B':
        fields.update(readqheader(file))
        fields['motors'] = readmotors(file)
    else:
        raise ValueError, "Unknown scantype %s"%scantype
    fields['columnnames'] = readcolumnheaders(file)
    return fields


def gzopen(filename):
    """
    Open file or gzip file
    """
    if filename.endswith('.gz'):
        import gzip
        file = gzip.open(filename,'r')
    else:
        file = open(filename, 'r')
    return file

def summary(filename):
    """
    Read header from file, returning a dict of fields.
    """
    file = gzopen(filename)
    fields = parseheader(file)
    data1 = file.readline()
    data2 = file.readline()
    fields['PSD'] = (',' in data2)
    file.close()
    return fields

def read(filename):
    """
    Read header and data from file, returning a dict of fields.
    """
    file = gzopen(filename)
    fields = parseheader(file)
    
    #read columns and detector images if available
    fields['columns'],fields['detector'] \
        = readcolumns(file,fields['columnnames'])
    fields['PSD'] = (fields['detector'].size>0)

    # fill in missing motor columns
    genmotorcolumns(fields['columns'],fields['motors'])
    
    file.close()
    
    return fields


def asdata(fields):
    import data, numpy
    d = data.Data()
    for (k,v) in fields.iteritems():
        setattr(d.prop,k,v)
    d.vlabel = 'Counts'
    d.v = d.prop.detector
    d.xlabel = d.prop.columnnames[0].capitalize()
    d.x = d.prop.columns[d.prop.columnnames[0]]
    if len(d.v.shape) > 1:
        d.ylabel = 'Pixel'
        d.y = numpy.arange(d.v.shape[0])
    return d

def data(filename):
    fields = read(filename)
    return asdata(fields)

# TODO: need message/question functions
def message(text): pass
def question(text): return True

def check_wavelength(fields, default, overrides):
    """
    ICP sometimes records the incorrect wavelength in the file.  Make
    sure the right value is being used.  Be annoying about it so that
    if the wavelength was changed for a legitimate reason the user can
    override.  L is the value in the file.  dectector.wavelength should
    already be set to the default for the instrument.
    """
    filename = fields['filename']
    dataset = filename[:5]
    wavelength = fields['wavelength']
    if dataset in overrides:
        # yuck! If already overridden for a particular file in
        # a dataset, override for all files in the dataset.
        wavelength = overrides[dataset]
        message("Using wavelength %s for %s"%(wavelength,dataset))
    elif L == 0:
        # yuck! If stored value is 0, use the default
        wavelength = default
        message("Using default wavelength %s for %s"%(wavelength,filename))
    elif abs(L-wavelength)/L > 0.01:
        # yuck! Value differs significantly from the default
        if question("ICP recorded a wavelength of %s in %s. \
Do you want to use the default wavelength %s instead?"\
          %(wavelength,filename,default)):
            wavelength = default
    # Regardless of how the value was obtained, use that value for 
    # the entire dataset
    return wavelength

def demo():
    """
    Read and print all command line arguments
    """
    import sys
    for file in sys.argv[1:]:
        fields = read(file)
        keys = fields.keys()
        keys.sort()
        for k in keys: print k,fields[k]
    
def plot(filename):
    """
    Read and print all command line arguments
    """
    import sys, pylab, wx
    canvas = pylab.gcf().canvas
    d = data(filename)
    if len(d.v.shape) > 1:
        pylab.gca().pcolorfast(d.xedges,d.yedges,d.v)
        pylab.xlabel(d.xlabel)
        pylab.ylabel(d.ylabel)
    else:
        pylab.plot(d.x,d.v)
        pylab.xlabel(d.xlabel)
        pylab.ylabel(d.vlabel)
    pylab.show()

if __name__=='__main__':
    import wx,sys; app = wx.PySimpleApp(); plot(sys.argv[1])
    #demo()
