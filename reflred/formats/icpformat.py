# This program is public domain

# Author: Paul Kienzle
# Initial version: William Ratcliff

"""
ICP data reader.

summary(filename)  - reads the header information
read(filename) - reads header information and data
"""
from __future__ import division

import os
import datetime

import numpy as np

from ..data import edges_from_centers


# Try using precompiled matrix loader
try:
    from . import _reduction
    def parsematrix(s, shape=None, linenum=0):
        """
        Parse a string into a matrix.  Provide a shape parameter if you
        know the expected matrix size.
        """
        if shape != None:
            # Have an existing block, so we know what size to allocate
            z = np.empty(shape,'i')
            i,j = _reduction.str2imat(s,z)
            if i*j != z.size:
                raise IOError,"Inconsistent dims at line %d"%linenum
        else:
            # No existing block.  Worst case is 2 bytes per int.
            n = int(len(s)/2+1)
            z = np.empty(n,'i')
            i,j = _reduction.str2imat(s,z)
            # Keep the actual size
            if i==1 or j==1:
                z = z[:i*j].reshape(i*j)
            else:
                z = z[:i*j].reshape(i,j)
        return z
except:
    def parsematrix(s,shape=None,linenum=0):
        """
        Parse a string into a matrix.  Provide a shape parameter if you
        know the expected matrix size.
        """
        z = np.matrix(s,'i').A
        i,j = z.shape
        if i==1 or j==1:
            z = z.reshape(i*j)
        if shape != None and np.any(z.shape != shape):
            raise IOError,"Inconsistent dims at line %d"%linenum
        return z


def readdata(fh):
    """
    Read ICP data, including PSD data if lines contain commas.
    """
    rows = []
    blocks = []

    line = fh.readline().rstrip()
    linenum = 1
    while line != '' and ord(line[0]) != 0:
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
            if blocks != []:
                z = parsematrix(s, shape=blocks[0].shape, linenum=linenum)
            else:
                z = parsematrix(s, shape=None, linenum=linenum)
            blocks.append(z)

        elif blocks != []:
            # Oops...missing a detector block.  Set it to zero counts
            # of the same size as the last block
            blocks.append(np.zeros(blocks[-1].shape,'i'))
        # Otherwise no detector block and don't need one
        # Note: this strategy fails to identify that the first
        # detector block is missing; those will be filled in later.

    # recover from missing leading detector blocks
    if blocks != [] and len(blocks) < len(rows):
        blank = np.zeros(blocks[0].shape,'i')
        blocks = [blank]*(len(blocks)-len(rows)) + blocks

    # Convert data to arrays
    X = np.array(rows, 'd')
    Z = np.array(blocks)
    return X,Z


def get_tokenized_line(file):
    """
    Read the next line of text into a set of words.
    """
    line=file.readline()
    return line.split()

def get_quoted_tokens(line):
    """
    Build a token list from a line which can be a mix of quoted strings
    and unquoted values separated by spaces.  Uses single quotes only.
    Does not test for escaped single quotes.
    """
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

class Lattice(object):
    def __str__(self):
        return ("a,b,c=%g,%g,%g  alpha,beta,gamma=%g,%g,%g"
                % (self.a,self.b,self.c,self.alpha,self.beta,self.gamma))
class Motor(object): pass
class MotorSet(object):
    def __str__(self):
        motornames = self.__dict__.keys()
        motornames.sort()
        details = [(m,self.__dict__[m].start,self.__dict__[m].stop)
                   for m in motornames]
        return ", ".join(["%s[%g:%g]"%m for m in details])
class ColumnSet(object):
    def __getitem__(self, k):
        return getattr(self,k)
    def __str__(self):
        columnnames = self.__dict__.keys()
        columnnames.sort()
        return ", ".join(columnnames)

def parse_date(datestr):
    stamp = datetime.datetime(2000,1,1) # need this to call strptime
    try: return stamp.strptime(datestr,'%b %d %Y %H:%M')
    except ValueError: pass
    try: return stamp.strptime(datestr,'%d-%b-%Y %H:%M')
    except ValueError: pass
    try: return stamp.strptime(datestr,'%Y-%m-%d %H:%M')
    except ValueError: pass
    raise ValueError("Unable to parse date %r"%datestr)

class ICP(object):
    def __init__(self, path):
        self.path = path

    def readheader1(self, file):
        """
        Read the tow line summary at the start of the ICP data files.
        """

        line = file.readline()
        if line.startswith(' Motor no.'):
            line = line.replace('Motor no.', '')
            line = line.replace('Intensity', 'counts')
            # must be a find-peak
            self.filename = os.path.basename(self.path)
            tokens = line.split()
            self.date = parse_date(" ".join(tokens[-4:]))
            self.columnnames = ["a"+c for c in tokens[:-5]] + [tokens[-5]]
            self.scantype = 'F'  # New scan type
            return

        tokens = get_quoted_tokens(line)
        self.filename=tokens[0]
        self.date = parse_date(tokens[1])
        self.scantype = tokens[2]
        self.prefactor = float(tokens[3])
        self.monitor = float(tokens[4])
        self.count_type = tokens[5]
        self.points = int(tokens[6])
        self.data_type = tokens[7]

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


    def readiheader(self, file):
        """
        Read I-buffer structure, excluding motors.
        """

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

    def readrheader(self, file):
        """
        Read R-buffer structure, excluding motors.
        """
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

    def readqheader(self, file):
        """
        Read Q-buffer structure (also works for T-buffer).
        """
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

    def readphipsi(self, file):
        tokenized = get_tokenized_line(file)
        assert tokenized[0] == "Phi:"
        assert tokenized[2] == "Psi:"
        self.phi = float(tokenized[1])
        self.psi = float(tokenized[3])

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
                    %(wavelength,self.filename))
        elif abs(default-wavelength)/default > 0.01:
            # yuck! Value differs significantly from the default
            if question("ICP recorded a wavelength of %s in %s. \
    Do you want to use the default wavelength %s instead?"\
              %(wavelength,self.filename,default)):
                wavelength = default
        # Regardless of how the value was obtained, use that value for
        # the entire dataset
        return wavelength


    def readmotors(self, file):
        """
        Read the 6 motor lines, returning a dictionary of
        motor names and start-step-stop values.
        E.g.,

        M = _readmotors(file)
        print M['a1'].start
        """
        self.motor = MotorSet()
        while True:  # read until 'Mot:' line
            words=get_tokenized_line(file)
            if words[0] == 'Mot:': break
            motor = Motor()
            motor.start=float(words[1])
            motor.step=float(words[2])
            motor.stop=float(words[3])
            name = words[0] if not words[0].isdigit() else 'a'+words[0]
            setattr(self.motor,name,motor)

    def readfixedmotors(self, file):
        """
        Read the 6 motor lines, returning a dictionary of
        motor names and start-step-stop values.
        E.g.,

        M = _readfixedmotors(file)
        print M['a1'].start
        """
        self.motor = MotorSet()
        while True:  # read until 'Mot:' line
            words=get_tokenized_line(file)
            if words[0] == 'Mot:': break
            motor = Motor()
            motor.start=float(words[1])
            motor.step=0.0
            motor.stop=motor.start
            name = words[0] if not words[0].isdigit() else 'a'+words[0]
            setattr(self.motor,name,motor)

    def readcolumnheaders(self, file):
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
        self.columnnames = line.split()


    def readcolumns(self, file):
        '''
        Read and parse ICP data columns listed in columns.  Return a dict of
        column name: vector.  If using a position sensitive detector, return
        an array of detector values x scan points.
        '''
        values,detector = readdata(file)
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
        if not hasattr(self, 'motor'): return
        if self.scantype in ['T']: return  # Skip motor generation for now for 'T'
        for (M,R) in self.motor.__dict__.iteritems():
            if not hasattr(self.column,M):
                if R.step != 0.:
                    vector = np.arange(R.start,R.step,R.stop)
                    # truncate to number of points measured
                    vector = vector[:self.points]+0
                else:
                    vector = R.start * np.ones(self.points)
                setattr(self.column,M,vector)
        pass

    def parseheader(self, file):
        """
        Read and parse ICP header information
        """
        # Determine FileType
        self.readheader1(file)
        if self.scantype == 'I':
            self.readiheader(file)
            self.readmotors(file)
        elif self.scantype in ['Q','T']:
            self.readqheader(file)
        elif self.scantype == 'B':
            self.readqheader(file)
            self.readmotors(file)
        elif self.scantype == 'D':
            self.readrheader(file)
            self.readmotors(file)
            self.readfixedmotors(file)
            self.readphipsi(file)
        elif self.scantype == 'R':
            self.readrheader(file)
            self.readmotors(file)
        elif self.scantype == 'F':
            return # Not going to read column headers
        else:
            raise ValueError, "Unknown scantype %s in ICP file"%self.scantype
        self.readcolumnheaders(file)

    def summary(self):
        """
        Read header from file, setting the corresponding attributes the ICP object
        """
        file = self.path if hasattr(self.path, 'read') else gzopen(self.path)
        self.parseheader(file)
        data1 = file.readline()
        data2 = file.readline()
        self.PSD = (',' in data2)
        if file != self.path:
            file.close()
        

    def read(self):
        """
        Read header and data from file, setting the corresponding attributes the ICP object
        """
        file = self.path if hasattr(self.path, 'read') else gzopen(self.path)
        self.parseheader(file)

        #read columns and detector images if available
        self.readcolumns(file)
        self.PSD = (self.detector.size>0)

        # fill in missing motor columns
        self.genmotorcolumns()

        if file != self.path:
            file.close()

    def __contains__(self, column):
        return hasattr(self.column,column)

    def counts(self):
        if self.detector.size > 1:
            return self.detector
        else:
            return self.column.counts


def write_icp_header(file, icpfile):
    raise NotImplemented


def _write_icp_frame(file, frame):
    # Round data to the nearest integer
    frame = np.asarray(frame+0.5,'uint32')
    if frame.ndim == 2:
        rows  = [ ",".join(str(v) for v in row) for row in frame ]
        text = ";".join(rows)
    else:
        text = ",".join(str(v) for v in frame)
    file.write(' ')
    offset = 0
    while len(text)-offset > 78:
        next = offset+78
        while text[next] not in ",;":
            next -= 1
        file.write(text[offset:next+1])
        file.write(' '*(78-(next-offset)))
        file.write('\n ')
        offset = next+1
    file.write(text[offset:])
    file.write('\n')


def write_icp_data(file, formats, columns, detector=None):
    """
    Write the data portion of the icp file.
    """
    for i in range(len(columns[0])):
        fields = [f%columns[k][i] for k,f in enumerate(formats)]
        file.write(' '.join(fields))
        file.write('\n')
        if detector != None and detector.size > 0:
            _write_icp_frame(file,detector[i])


def replace_data(infilename, outfilename, columns, detector=None):
    infile = open(infilename,'r')
    outfile = open(outfilename, 'w')

    # Copy everything to the motor column
    while True:
        line = infile.readline()
        outfile.write(line)
        if line.startswith(' Mot:'): break

    # Copy column headers
    line = infile.readline()
    outfile.write(line)

    # Guess output format from the first line of the data
    line = infile.readline()
    formats = []
    width = 0
    precision = 0
    increment_precision = False
    in_number = False
    for c in line[:-1]:
        width += 1
        if c == ' ':
            if in_number:
                formats.append('%'+str(width-1)+'.'+str(precision)+'f')
                width = 0
                precision = 0
                increment_precision = False
                in_number = False
        elif c == '.':
            increment_precision = True
        elif c.isdigit():
            in_number = True
            if increment_precision:
                precision+=1
    formats.append('%'+str(width)+'.'+str(precision)+'f')

    write_icp_data(outfile, formats, columns, detector)

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

def gzopen(filename, mode='r'):
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
    d = Data()
    d.path = icp.path
    d.filename = icp.filename
    if 'monitor' in icp.columnnames:
        d.vlabel = 'Counts per monitor'
        norm = icp.column['monitor']
    elif 'time' in icp.columnnames:
        d.vlabel = 'Counts per minute'
        norm = icp.column['time']
    else:
        d.vlabel = 'Counts'
        norm = np.ones(icp.counts.shape[0])
    if icp.counts.ndim == 2:
        norm = norm[:, None]
    d.v = np.asarray(icp.counts, 'd') / norm
    d.dv = np.sqrt(icp.counts) / norm

    if icp.scantype == 'D':
        x_name, y_name = icp.columnnames[0:2]
        d.x, d.y = icp.column[x_name], icp.column[y_name]
        d.xlabel, d.ylabel = x_name.capitalize(), y_name.capitalize()

    # Find first moving column, returning point numbers if no moving columns
    for c in icp.columnnames:
        x = icp.column[c]
        if (c not in ('counts', 'counts2', 'monitor', 'time',)
            and max(x) - min(x) > 1e-3):
            d.xlabel = c.capitalize()
            d.x = x
            break
    else:
        d.xlabel = 'Point'
        d.x = np.arange(1, 1+d.v.shape[0])

    if len(d.v.shape) > 1:
        d.ylabel = 'Pixel'
        d.y = np.arange(1, 1+d.v.shape[1])

    return d

def data(filename):
    icp = ICP(filename)
    icp.read()
    return asdata(icp)

class Data(object):
    def load(self):
        pass
    def plot(self):
        import pylab
        if len(self.v.shape) > 2:
            x,y = edges_from_centers(self.x), edges_from_centers(self.y)
            pylab.gca().pcolormesh(x, y, self.v[:, :, 0])
            pylab.xlabel(self.xlabel)
            pylab.ylabel(self.ylabel)
            h = pylab.colorbar()
            h.set_label(self.vlabel)
        elif len(self.v.shape) == 2:
            idx = slice(1,50) if self.filename.endswith('.bt4') else slice()
            x, y = edges_from_centers(self.x), edges_from_centers(self.y[idx])
            #x, y = self.x, self.y[idx]
            pylab.gca().pcolormesh(x, y, self.v[:, idx].T)
            pylab.xlabel(self.xlabel)
            pylab.ylabel(self.ylabel)
            h = pylab.colorbar()
            h.set_label(self.vlabel)
        elif hasattr(self, 'y'):
            # make a scatter plot
            pylab.scatter(self.x, self.y, c=self.v, s=20, lw=0)
            pylab.xlabel(self.xlabel)
            pylab.ylabel(self.ylabel)
            h = pylab.colorbar()
            h.set_label(self.vlabel)
        else:
            pylab.errorbar(self.x, self.v, yerr=self.dv,
                           fmt='.', label=self.filename)
            pylab.xlabel(self.xlabel)
            pylab.ylabel(self.vlabel)
    def text(self):
        with gzopen(self.path) as fid:
            return "\n".join(line.rstrip() for line in fid)
    __str__ = text


# TODO: need message/question functions
def message(text): pass
def question(text): return True


def copy_test():
    import sys
    if len(sys.argv) < 2:
        print "usage: python icpformat.py file"
        sys.exit()
    filename = sys.argv[1]
    icp = ICP(filename)
    icp.read()
    columns = [icp.column[n] for n in icp.columnnames]
    replace_data(filename,'copy.icp',columns,detector=icp.detector)


def demo():
    """
    Read and print all command line arguments
    """
    import sys
    if len(sys.argv) < 2:
        print "usage: python icpformat.py file*"
    for file in sys.argv[1:]:
        fields = read(file)
        keys = fields.__dict__.keys()
        keys.sort()
        for k in keys: print k,getattr(fields,k)


def plot_demo():
    import sys
    if len(sys.argv) != 2:
        print "usage: python icpformat.py file"
    else:
        data(sys.argv[1]).plot()
        import pylab; pylab.show()

if __name__=='__main__':
    plot_demo()
    #demo()
    #copy_test()
