# This program is public domain

# Author: Paul Kienzle
# Initial version: William Ratcliff

"""
ICP data reader.

summary(filename)  - reads the header information
read(filename) - reads header information and data
"""

import numpy as N
import datetime,sys
from reflectometry.reduction import _reduction

def readdata(fh):
    """
    Read ICP data, including PSD data if lines contain commas.
    """
    rows = []
    blocks = []

    line = fh.readline().rstrip()
    linenum = 1
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
        linenum += 1

        # Build up a multiline detector block by joining all lines that
        # contain a comma
        b = []
        while ',' in line:
            b.append(line)
            line = fh.readline()
            linenum += 1

		# If last line ended with a comma then the last number for the
		# the current block is on the current line.
        if b != [] and b[-1].rstrip()[-1] == ",":
            b.append(line)
            line = fh.readline()
            linenum += 1

        if b != []:
            # Have a detector block so add it
            s = "".join(b)
            # You can use numpy's string to matrix converter if for some
            # reason _reduction doesn't compile, but it is horribly slow.
            #z = N.matrix(s,'i').A
            if blocks != []:
                # Have an existing block, so we know what size to allocate
                z = N.empty(blocks[0].shape,'i')
                i,j = _reduction.str2imat(s,z)
                if i*j != z.size: 
                    raise IOError,"Inconsistent dims at line %d"%linenum
            else:
                # No existing block.  Worst case is 2 bytes per int.
                n = int(len(s)/2+1)
                z = N.empty(n,'i')
                i,j = _reduction.str2imat(s,z)
                # Keep the actual size
                if i==1 or j==1:
                    z = z[:i*j].reshape(i*j)
                else:
                    z = z[:i*j].reshape(i,j)
            blocks.append(z)

        elif blocks != []:
            # Oops...missing a detector block.  Set it to zero counts
            # of the same size as the last block
            blocks.append(N.zeros(blocks[-1].shape,'i'))
        # Otherwise no detector block and don't need one
        # Note: this strategy fails to identify that the first 
        # detector block is missing; those will be filled in later.

    # recover from missing leading detector blocks
    if blocks != [] and len(blocks) < len(rows):
        blank = N.zeros(blocks[0].shape,'i')
        blocks = [blank]*(len(blocks)-len(rows)) + blocks

    # Convert data to arrays
    X = N.array(rows, 'd')
    Z = N.array(blocks)
    return X,Z


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

class Lattice(object): pass
class Motor(object): pass
class MotorSet(object): pass
class ColumnSet(object): pass

class ICP(object):
    def __init__(self, path):
        self.path = path

    def readheader1(self):
        """
        Read the tow line summary at the start of the ICP data files.
        """

        file = self.file
        tokens = get_quoted_tokens(file)
        self.filename=tokens[0]
        self.timestamp = datetime.datetime(2000,1,1)
        self.date=self.timestamp.strptime(tokens[1],'%b %d %Y %H:%M')
        self.scantype = tokens[2]
        self.prefactor = float(tokens[3])
        self.monitor=float(tokens[4])
        self.count_type=tokens[5]
        self.points=int(tokens[6])
        self.data_type=tokens[7]

        #skip over names of fields 
        file.readline()

        #comment and polarization
        line = file.readline()
        polarized_index = line.find("F1: O", 52)
        if polarized_index > 0:
            self.comment = line[:polarized_index].rstrip()
            F1 = '+' if line.find("F1: ON", 52)>0 else '-'
            F2 = '+' if line.find("F2: ON", 52)>0 else '-'
            self.polarization = F1+F2
        else:
            self.comment = line.rstrip()
            self.polarization = ""


    def readiheader(self):
        """
        Read I-buffer structure, excluding motors.
        """
        file = self.file
        
        # Read in fields and field names
        tokenized=get_tokenized_line(file)
        fieldnames = file.readline()
        #print tokenized
        #print fieldnames

        #Collimation    Mosaic    Wavelength   T-Start   Incr.   H-field #Det
        self.collimations = [float(s) for s in tokenized[0:4]]
        self.mosaic = [float(s) for s in tokenized[4:7]]
        self.wavelength=float(tokenized[7])
        self.Tstart=float(tokenized[8])
        self.Tstep=float(tokenized[9])
        self.Hfield=float(tokenized[10])

    def readrheader(self):
        """
        Read R-buffer structure, excluding motors.
        """
        file = self.file
        # Read in fields and field names
        tokenized=get_tokenized_line(file)
        fieldnames = file.readline()
        #print tokenized
        #print fieldnames

        #Mon1    Exp   Dm      Wavel  T-Start  Incr. Hf(Tesla) #Det SclFac
        self.Mon1=float(tokenized[0])
        self.Exp=float(tokenized[1])
        self.Dm=float(tokenized[2])
        self.wavelength=float(tokenized[3])
        self.Tstart=float(tokenized[4])
        self.Tstep=float(tokenized[5])
        self.Hfield=float(tokenized[6])
        self.numDet=float(tokenized[7])
        self.SclFac=float(tokenized[8])

    def readqheader(self):
        """
        Read Q-buffer structure.
        """
        file = self.file
        #experiment info
        tokenized=get_tokenized_line(file)
        self.collimations=[float(s) for s in tokenized[0:4]]
        self.mosaic=[float(s) for s in tokenized[4:7]]
        orient1=[float(s) for s in tokenized[7:10]]
        #ignore the "angle" field
        orient2=[float(s) for s in tokenized[11:14]]
        #skip line with field names
        file.readline()
        tokenized=get_tokenized_line(file)
        lattice=Lattice()
        lattice.a=float(tokenized[0])
        lattice.b=float(tokenized[1])
        lattice.c=float(tokenized[2])
        lattice.alpha=float(tokenized[3])
        lattice.beta=float(tokenized[4])
        lattice.gamma=float(tokenized[5])
        self.lattice=lattice
        #skip line with field names
        file.readline()
        tokenized=get_tokenized_line(file)
        self.ecenter=float(tokenized[0])
        self.deltae=float(tokenized[1])
        self.ef=float(tokenized[2])
        self.monochromator_dspacing=float(tokenized[3])
        self.analyzer_dspacing=float(tokenized[4])
        self.tstart=float(tokenized[5])
        self.tstep=float(tokenized[6])
        tokenized=get_tokenized_line(file)
        self.Efixed=tokenized[4]
        tokenized=get_tokenized_line(file)
        self.qcenter=[float(s) for s in tokenized[0:3]]
        self.qstep=[float(s) for s in tokenized[3:6]]
        self.hfield=float(tokenized[6])
        #skip line describing fields
        file.readline()
    
    def check_wavelength(self, default, overrides):
        """
        ICP sometimes records the incorrect wavelength in the file.  Make
        sure the right value is being used.  Be annoying about it so that
        if the wavelength was changed for a legitimate reason the user can
        override.  L is the value in the file.  dectector.wavelength should
        already be set to the default for the instrument.
        """
        dataset = self.filename[:5]
        wavelength = self.wavelength
        if dataset in overrides:
            # yuck! If already overridden for a particular file in
            # a dataset, override for all files in the dataset.
            wavelength = overrides[dataset]
            message("Using wavelength %s for %s"%(wavelength,dataset))
        elif wavelength == 0:
            # yuck! If stored value is 0, use the default
            wavelength = default
            message("Using default wavelength %s for %s"\
                    %(wavelength,self.path))
        elif abs(default-wavelength)/default > 0.01:
            # yuck! Value differs significantly from the default
            if question("ICP recorded a wavelength of %s in %s. \
    Do you want to use the default wavelength %s instead?"\
              %(wavelength,self.path,default)):
                wavelength = default
        # Regardless of how the value was obtained, use that value for 
        # the entire dataset
        return wavelength

    
    def readmotors(self):
        """
        Read the 6 motor lines, returning a dictionary of
        motor names and start-step-stop values.
        E.g.,
        
        M = _readmotors(file)
        print M['a1'].start
        """
        self.motor = MotorSet()
        while True:  # read until 'Mot:' line
            words=get_tokenized_line(self.file)
            if words[0] == 'Mot:': break
            motor = Motor()
            motor.start=float(words[1])
            motor.step=float(words[2])
            motor.stop=float(words[3])
            name = words[0] if not words[0].isdigit() else 'a'+words[0]
            setattr(self.motor,name,motor)
    
    def readcolumnheaders(self):
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
        line = self.file.readline()
        line = line.lower()
        for (old,new) in (('#1 counts','counts'),
                          ('#2 counts','counts2'),
                          (' mon ',' monitor '),
                          (' min ',' time '),
                          ('(',''),
                          (')',''),
                          ):
            line = line.replace(old,new)
        self.columnnames = line.split()
    
    
    def readcolumns(self):
        '''
        Read and parse ICP data columns listed in columns.  Return a dict of
        column name: vector.  If using a position sensitive detector, return 
        an array of detector values x scan points.
        '''
        values,detector = readdata(self.file)
        self.column = ColumnSet()
        for (c,v) in zip(self.columnnames,values.T):
            setattr(self.column,c,v)
        self.detector = detector
        self.counts = detector if detector.size > 0 else self.column.counts
        self.points = len(self.column.counts)
        
    def genmotorcolumns(self):
        """
        Generate vectors for each of the motors if a vector is not
        already stored in the file.
        """
        for (M,R) in self.motor.__dict__.iteritems():
            if not hasattr(self.column,M):
                if R.step != 0.:
                    vector = N.arange(R.start,R.step,R.stop)
                    # truncate to number of points measured
                    vector = vector[:self.points]+0  
                else:
                    vector = R.start * N.ones(self.points)
                setattr(self.column,M,vector)
        pass
    
    def parseheader(self):
        """
        Read and parse ICP header information
        """
        # Determine FileType
        file = self.file
        self.readheader1()
        if self.scantype=='I':
            self.readiheader()
            self.readmotors()
        elif self.scantype=='Q':
            self.readqheader()
        elif self.scantype=='B':
            self.readqheader()
            self.readmotors()
        elif self.scantype=='R':
            self.readrheader()
            self.readmotors()
        else:
            raise ValueError, "Unknown scantype %s in ICP file"%scantype
        self.readcolumnheaders()

    def summary(self):
        """
        Read header from file, returning a dict of fields.
        """
        self.file = gzopen(self.path)
        self.parseheader()
        data1 = self.file.readline()
        data2 = self.file.readline()
        self.PSD = (',' in data2)
        self.file.close()
    
    def read(self):
        """
        Read header and data from file, returning a dict of fields.
        """
        self.file = gzopen(self.path)
        self.parseheader()
        
        #read columns and detector images if available
        self.readcolumns()
        self.PSD = (self.detector.size>0)
    
        # fill in missing motor columns
        self.genmotorcolumns()

        self.file.close()

    def __contains__(self, column):
        return hasattr(self.column,column)
    
    def counts(self):
        if self.detector.size > 1:
            return self.detector
        else:
            return self.column.counts

def read(filename):
    """Read an ICP file and return the corresponding ICP file object"""
    icp = ICP(filename)
    icp.read()
    return icp

def summary(filename):
    """Read an ICP file header and return the corresponding ICP file object"""
    icp = ICP(filename)
    icp.summary()
    return icp

def gzopen(filename,mode='r'):
    """
    Open file or gzip file
    """
    if filename.endswith('.gz'):
        import gzip
        file = gzip.open(filename, mode)
    else:
        file = open(filename, mode)
    return file

def asdata(icp):
    import data, numpy
    d = data.Data()
    for (k,v) in icp.__dict__.iteritems():
        setattr(d.prop,k,v)
    d.vlabel = 'Counts'
    d.v = d.prop.counts
    d.xlabel = d.prop.columnnames[0].capitalize()
    d.x = getattr(d.prop.column, d.prop.columnnames[0])
    if len(d.v.shape) > 1:
        d.ylabel = 'Pixel'
        d.y = numpy.arange(d.v.shape[0])
    return d

def data(filename):
    icp = ICP(filename)
    icp.read()
    return asdata(icp)

# TODO: need message/question functions
def message(text): pass
def question(text): return True

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
