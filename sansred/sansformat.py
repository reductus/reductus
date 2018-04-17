"""
File loaders for NCNR VAX SANS format
"""
from __future__ import print_function
import sys
import os
import struct
import time
import math

try:
    # pylint: disable=unused-import
    from typing import Tuple, Dict, List, Optional, Sequence, Any, Iterator, AnyStr
    # pylint: enable=unused-import
    ignore = 0  # keep pycharm happy
except ImportError:
    pass

import numpy as np

# CRUFT: python 2.x needs to convert unicode to str; 3.x leaves it as unicode
if sys.version_info[0] >= 3:
    def bytes_to_str(s):
        # type: (AnyStr) -> str
        return s.decode('utf-8') if isinstance(s, bytes) else s # type: ignore
    def str_to_bytes(s):
        # type: (AnyStr) -> bytes
        """Return byte string or list of byte strings"""
        return s.encode('utf-8') if isinstance(s, str) else s # type: ignore
    def write(fid, s):
        # type: (IO[Any], AnyStr) -> None
        #print("fid type=%s"%type(fid))
        fid.write(str_to_bytes(s))
else: # python 2.x
    def bytes_to_str(s):
        # type: (AnyStr) -> str
        return s
    def str_to_bytes(s):
        # type: (AnyStr) -> bytes
        """Return byte string or list of byte strings"""
        return s
    def write(fid, s):
        # type: (IO[Any], AnyStr) -> None
        fid.write(s)

__all__ = ["load", "save"]

DATETIME_FORMAT = '%d-%b-%Y %H:%M:%S'
DATE_FORMAT = '%d%b%y '

class SansFormatInfo:
    #: type for each field
    types = None  # type: Dict[str, str]
    #: units for each field
    units = None  # type: Dict[str, str]
    #: field names
    fields = None  # type: List[str]
    #: integer fields
    ints = None  # type: List[str]
    #: float fields
    reals = None  # type: List[str]
    #: string fields
    strings = None  # type: List[str]
    #: struct pack/unpack codes for header
    header_struct = None  # type: str
    #: struct pack/unpack codes for data
    data_struct = None  # type: str
    #: precision for each field
    precision = None  # type: Dict[str, float]
    def __init__(self, *args):
        # type: (*Tuple[str, str]) -> None
        self.types = dict(args)
        self.fields = [name for name, _ in args]
        dtype_to_struct_type = {
            'vaxR4': '4s',
            DATETIME_FORMAT: '20s',
            DATE_FORMAT: '8s',
            }
        self.header_struct = "<"+"".join(dtype_to_struct_type.get(dtype, dtype)
                                         for _, dtype in args)
        assert struct.calcsize(self.header_struct) == 512
        self.ints = [name for name, dtype in args if dtype == 'i']
        self.reals = [name for name, dtype in args if dtype == 'vaxR4']
        self.strings = [name for name, dtype in args if dtype.endswith('s')]
        self.data_struct = '<16401h'
        self.units = dict([
            ('run.ctime', 's'),           #  27  count time per prefactor (s)
            ('run.rtime', 's'),           #  31  total count time (s)
            ('sample.thk', 'cm'),         # 162  sample thickness (cm)
            ('sample.rotang', 'cm'),      # 170  sample rotation angle (degrees)
            ('sample.temp', 'C'),         # 186  sample temperature (C)
            ('det.calx1', 'mm'),          # 220  detector x pixel size (mm)
            ('det.caly1', 'mm'),          # 232  detector y pixel size (mm)
            ('det.dis', 'm'),             # 260  sample to detector distance (m)
            ('det.offset', 'cm'),         # 264  horizontal detector offset (cm)
            ('det.siz', 'cm'),            # 268  physical detector width (cm)
            ('det.bstop', 'mm'),          # 272  beam stop diameter (mm)
            ('resolution.ap1', 'mm'),     # 280  source aperture diameter (mm)
            ('resolution.ap2', 'mm'),     # 284  sample aperture diameter (mm)
            ('resolution.ap12dis', 'm'),  # 288  source aperature to sample aperture distance (m)
            ('resolution.lmda', 'Ang'),   # 292  wavelength (A)
            ('resolution.dlmda', ''),  # 296  wavelength spread (FWHM)
            ('bmstp.xpos', 'cm'),         # 368  beam stop X position (MCU app. cm)
            ('bmstp.ypos', 'cm'),         # 372  beam stop Y position (MCU app. cm)
            ])
        self.precision = { # default precision is 0.01
            }
    def default_value(self, key):
        # type: (str) -> Any
        """
        Return the default value for the field based on field type.
        """
        if self.types[key] == 'vaxR4':
            return 0.
        elif self.types[key] in ('L', 'i'):
            return 0
        elif self.types[key].endswith('s'):
            return ''
        elif self.types[key] == DATETIME_FORMAT:
            return time.gmtime()
        elif self.types[key] == DATE_FORMAT:
            return None
        else:
            raise RuntimeError("Missing default value for "+self.types[key])

INFO = SansFormatInfo(
    ('fname.filename', '21s'),      #   2  filename

    ('run.npre', 'i'),              #  23  number of run prefactors
    ('run.ctime', 'i'),             #  27  count time per prefactor (s)
    ('run.rtime', 'i'),             #  31  total count time (s)
    ('run.numruns', 'i'),           #  35
    ('run.moncnt', 'vaxR4'),        #  39  monitor count
    ('run.savmon', 'vaxR4'),        #  43
    ('run.detcnt', 'vaxR4'),        #  47  detector count (from the anode plane)
    ('run.atten', 'vaxR4'),         #  51  attenuator number (not transmission)
    ('run.datetime', '%d-%b-%Y %H:%M:%S'), #  55  data and time of collection DD-MMM-YYYY HH:MM:SS
    ('run.type', '3s'),             #  75  'RAW'
    ('run.defdir', '11s'),          #  78  NGxSANSnn
    ('run.mode', '1s'),             #  89  C, M
    ('run.reserve', '%d%b%y '),     #  90  DDMMMYY (another date prob. not needed)

    ('sample.labl', '60s'),         #  98  sample label
    ('sample.trns', 'vaxR4'),       # 158  sample transmission
    ('sample.thk', 'vaxR4'),        # 162  sample thickness (cm)
    ('sample.position', 'vaxR4'),   # 166  sample changer position
    ('sample.rotang', 'vaxR4'),     # 170  sample rotation angle (degrees)
    ('sample.table', 'i'),          # 174  chamber or huber position
    ('sample.holder', 'i'),         # 178  sample holder identifier
    ('sample.blank', 'i'),          # 182
    ('sample.temp', 'vaxR4'),       # 186  temperature (sample.tunits)
    # IGOR code says field strength for the electromagnets is at 348
    ('sample.field', 'vaxR4'),      # 190  applied field strength (sample.funits)
    ('sample.tctrlr', 'i'),         # 194  sample control identifier
    ('sample.magnet', 'i'),         # 198  magnet identifier
    ('sample.tunits', '6s'),        # 202  temperature units
    ('sample.funits', '6s'),        # 208  applied field units

    ('det.typ', '6s'),              # 214  ORNL or ILL
    ('det.calx1', 'vaxR4'),         # 220  detector x pixel size (mm)
    ('det.calx2', 'vaxR4'),         # 224  non-linear spatial (10000)
    ('det.calx3', 'vaxR4'),         # 228  corrections (0)
    ('det.caly1', 'vaxR4'),         # 232  detector y pixel size (mm)
    ('det.caly2', 'vaxR4'),         # 236  (10000)
    ('det.caly3', 'vaxR4'),         # 240  (0)
    ('det.num', 'i'),               # 244  area detector identifier
    ('det.spacer', 'i'),            # 248
    ('det.beamx', 'vaxR4'),         # 252  beam center x position (detector coord)
    ('det.beamy', 'vaxR4'),         # 256  beam center y position (detector coord)
    ('det.dis', 'vaxR4'),           # 260  sample to detector distance (m)
    ('det.offset', 'vaxR4'),        # 264  horizontal detector offset (cm)
    ('det.siz', 'vaxR4'),           # 268  physical detector width (cm)
    ('det.bstop', 'vaxR4'),         # 272  beam stop diameter (mm)
    ('det.blank', 'vaxR4'),         # 276

    ('resolution.ap1', 'vaxR4'),    # 280  source aperture diameter (mm)
    ('resolution.ap2', 'vaxR4'),    # 284  sample aperture diameter (mm)
    ('resolution.ap12dis', 'vaxR4'), # 288  source aperature to sample aperture distance (m)
    ('resolution.lmda', 'vaxR4'),   # 292  wavelength (A)
    ('resolution.dlmda', 'vaxR4'),  # 296  wavelength spread (FWHM)
    ('resolution.save', 'vaxR4'),   # 300  lens flag

    ('tslice.slicing', 'L'),        # 304
    ('tslice.multfact', 'i'),       # 308  multiplicative factor for slicing bins
    ('tslice.ltslice', 'i'),        # 312

    ('temp.printemp', 'L'),         # 316  print temp after prefactor
    ('temp.hold', 'vaxR4'),         # 320
    ('temp.err', 'vaxR4'),          # 324
    ('temp.blank', 'vaxR4'),        # 328
    ('temp.extra', 'i'),            # 332  (0x0001 print blue box temp; 0x0100 control from int. bath or ext. probe)
    ('temp.reserve', 'i'),          # 336

    ('magnet.printmag', 'L'),       # 340
    ('magnet.sensor', 'L'),         # 344
    ('magnet.current', 'vaxR4'),    # 348
    ('magnet.conv', 'vaxR4'),       # 352
    ('magnet.fieldlast', 'vaxR4'),  # 356
    ('magnet.blank', 'vaxR4'),      # 360
    ('magnet.spacer', 'vaxR4'),     # 364

    ('bmstp.xpos', 'vaxR4'),        # 368  beam stop X position (MCU app. cm)
    ('bmstp.ypos', 'vaxR4'),        # 372  beam stop Y position (MCU app. cm)

    ('params.blank1', 'i'),         # 376
    ('params.blank2', 'i'),         # 380
    ('params.blank3', 'i'),         # 384
    ('params.trsncnt', 'vaxR4'),    # 388  transmission detector count
    ('params.extra1', 'vaxR4'),     # 392  whole detector transmission
    ('params.extra2', 'vaxR4'),     # 396
    ('params.extra3', 'vaxR4'),     # 400
    ('params.reserve', '42s'),      # 404  first four characters are associated file suffix

    ('voltage.printvolt', 'L'),     # 446
    ('voltage.volts', 'vaxR4'),     # 450 field strength for the superconducting magnet
    ('voltage.blank', 'vaxR4'),     # 454
    ('voltage.spacer', 'i'),        # 458

    ('polarization.printpol', 'L'), # 462
    ('polarization.flipper', 'L'),  # 466
    ('polarization.horiz', 'vaxR4'), # 470
    ('polarization.vert', 'vaxR4'), # 474

    ('analysis.rows1', 'i'),        # 478  box x1  (user defined tranmsission est. box)
    ('analysis.rows2', 'i'),        # 482  box x2
    ('analysis.cols1', 'i'),        # 486  box y1
    ('analysis.cols2', 'i'),        # 490  box y2
    ('analysis.factor', 'vaxR4'),   # 494  box counts
    ('analysis.qmin', 'vaxR4'),     # 498
    ('analysis.qmax', 'vaxR4'),     # 502
    ('analysis.imin', 'vaxR4'),     # 506
    ('analysis.imax', 'vaxR4'),     # 510
)


def load(filename):
    # type: (str) -> Tuple[np.ndarray, Dict[str, Any]]
    """
    Load NCNR VAX SANS format filename.

    Returns data, metadata

    The filename type returned in metadata['run.type'] may be 'RAW' for a
    measurement filename, 'DIV' for a detector sensitivity filename or 'MASK' for
    a detector mask filename.

    The filename name is returned in metadata['fname.filename']

    Raises IOError if the filename length does not correspond to one of the
    possible filename types.  Other errors may be raised if the conversion fails.
    """
    size = os.path.getsize(filename)
    if size == 33316:
        data, metadata = readNCNRData(filename)
    elif size == 66116:
        data = readNCNRSensitivity(filename)
        metadata = {
            'fname.filename': filename,
            'run.type': 'DIV',
            }
    elif size == 16896:
        data = readNCNRMask(filename)
        metadata = {
            'fname.filename': filename,
            'run.type': 'MASK',
            }
    else:
        raise IOError("unknown SANS format filename '%s'"%filename)

    return data, metadata


def save(filename, data, metadata):
    # type: (str, np.ndarray, Dict[str, Any]) -> None
    """
    Save NCNR VAX SANS format filename.

    Input is data, metadata

    metadata['fname.filename'] is not used or modified.

    Raises IOError if the data size does not correspond to the file type.
    """
    writeNCNRData(filename, data, metadata)


def readNCNRSensitivity(inputfile):
    # type: (str) -> np.ndarray
    """
    Read VAX format SANS sensitivity file.
    """
    f = open(inputfile, 'rb')
    data = f.read()
    f.close()

    #skip the fake header and just read the data
    #data is 32bit VAX floats
    dataformatstring = '<65600s'
    #print len(data[516:])
    (rawdatastring,) = struct.unpack_from(dataformatstring, data, offset=516)

    detdata = np.empty(16384)

    a = 0
    offset = 0
    for _i in range(16):
        for _j in range(511):
            #if jj == 0: print rawdatastring[offset:offset+4]
            detdata[a] = R4_VAX2IEEE(rawdatastring[offset:offset+4])
            a += 1
            offset += 4

        offset += 2

        for _k in range(510):
            detdata[a] = R4_VAX2IEEE(rawdatastring[offset:offset+4])
            a += 1
            offset += 4

        offset += 2

    for _i in range(48):
        detdata[a] = R4_VAX2IEEE(rawdatastring[offset:offset+4])
        a += 1
        offset += 4

    detdata.resize((128, 128))

    return detdata


def readNCNRMask(inputfile):
    # type: (str) -> np.ndarray
    """
    Read NCNR format mask file
    """
    f = open(inputfile, 'rb')
    data = f.read()
    f.close()

    # four bytes before and 508 bytes after should be 0
    mask = np.array(struct.unpack_from('<16384B', data, offset=4)) # 4:16384+4
    mask.resize((128, 128))

    return mask

def readNCNRData(inputfile):
    # type: (str) -> Tuple[np.ndarray, Dict[str, Any]]
    """
    Read VAX format SANS data from NCNR.
    """
    #print "reading", inputfile
    f = open(inputfile, 'rb')
    data = f.read()
    f.close()

    if len(data) != 33316:
        raise IOError("Data file corrupted.  Incorrect length")


    # Interpret structure
    #print formatstring
    #print struct.calcsize(HEADER_STRUCT)
    metadata = dict(zip(INFO.fields,
                        struct.unpack_from(INFO.header_struct, data, offset=2)))

    #Process reals into metadata
    for k in INFO.reals:
        metadata[k] = R4_VAX2IEEE(metadata[k])

    #Remove spaces around string fields
    for k in INFO.strings:
        metadata[k] = bytes_to_str(metadata[k]).strip()
    #Convert dates
    metadata['run.datetime'] = time.strptime(bytes_to_str(metadata['run.datetime']),
                                             INFO.types['run.datetime'])

    #print "data len", len(data[514:])
    rawdata = np.array(struct.unpack_from(INFO.data_struct, data, offset=514))

    detdata = decompress(rawdata)

    #print "first 2", struct.unpack_from('>h', data, offset=0)
    return detdata, metadata

def writeNCNRData(filename, data, metadata):
    # type: (str, np.ndarray, Dict[str, Any]) -> None
    """
    Read VAX format SANS data from NCNR.
    """
    # Work with a copy since we are going to update values
    rawdata = metadata.copy()

    # Fill in missing data
    for k in INFO.fields:
        if k not in rawdata:
            rawdata[k] = INFO.default_value(k)

    # convert reals to vax format
    rawdata.update((k, R4_IEEE2VAX(rawdata[k], k)) for k in INFO.reals)

    # round floats to integers rather than truncating
    rawdata.update((k, round(rawdata[k])) for k in INFO.ints)

    # extend strings with spaces
    rawdata.update((k, _raw_str(rawdata[k], INFO.types[k]))
                   for k in INFO.strings)

    # Convert date/time field
    rawdata['run.datetime'] = time.strftime(INFO.types['run.datetime'],
                                            metadata['run.datetime']).upper()

    # If alternate date/time field is not set, set it to date/time value,
    # otherwise treat it as a string and make sure it has 8 characters
    if not rawdata['run.reserve']:
        rawdata['run.reserve'] = time.strftime(INFO.types['run.reserve'],
                                               metadata['run.datetime']).upper()
    else:
        rawdata['run.reserve'] = "%8s"%rawdata['run.reserve']
    rawdata['run.datetime'] = str_to_bytes(rawdata['run.datetime'])
    rawdata['run.reserve'] = str_to_bytes(rawdata['run.reserve'])

    #for k, v in rawdata.items(): print(k, type(v))

    # Pack data into byte arrays
    header = struct.pack(INFO.header_struct, *[rawdata[k] for k in INFO.fields])
    body = struct.pack(INFO.data_struct, *compress(data))  # type: ignore

    #print "reading", inputfile
    with open(filename, 'wb') as f:
        write(f, '\0\0')
        write(f, header)
        write(f, body)

def _raw_str(s, format):
    # type: (bytes, str) -> bytes
    """
    Pad strings with blanks to total length.
    """
    n = int(format[:-1])  # convert format code such as '12s' to length 12
    b = str_to_bytes(s)
    return b[:n] if len(b) >= n else (b+b' '*(n-len(b)))


def decompress(data):
    # type: (np.ndarray) -> np.ndarray
    """
    Convert semi-logarithmic 2-byte integer to 4-byte integer value.

    The storage format for numbers up to 32767 is the number itself
    The storage format for numbers above 32767 is
         - (mantissa + 10000*10**power)
    where the mantissa is 4 digits and power is 1, 2 or 3.
    """

    # Drop values at 0, 1022, 2*1022, ...
    idx = np.arange(len(data), dtype='i')%1022 != 0
    #print "not idx", data[~idx]
    data = data[idx]
    assert len(data) == 16384

    # Logarithmic decompression
    base = 10000
    idx = data <= -base
    power = np.floor(-data[idx]/base)
    data[idx] = np.asarray((-data[idx]%base)*10**power, data.dtype)

    # Recast as 128x128 array
    data = data.reshape((128, 128), order='F')
    return data

def compress(data):
    # type: (np.ndarray) -> np.ndarray
    """
    Convert 4-byte integer value to semi-logarithmic 2-byte integer.

    The storage format for numbers up to 32767 is the number itself
    The storage format for numbers above 32767 is
         - (mantissa + 10000*10**power)
    where the mantissa is 4 digits and power is 1, 2 or 3.

    add an extra integer at 0, 1024
    """
    data = np.asarray(data.flatten(), 'int32')
    assert len(data) == 16384

    # Logarithmic compression
    base = 10000
    erridx = data > 2767000
    idx = data > 32767
    power = np.ceil(np.log10(data[idx]))-4
    mantissa = data[idx] // (10**power)
    data[idx] = np.asarray(-(mantissa + power*base), data.dtype)
    data[erridx] = -777

    # Add values at 0, 1022, 2*1022, ...
    fulldata = np.zeros(16384 + 17, 'i')
    idx = np.arange(len(fulldata), dtype='i')%1022 != 0
    fulldata[idx] = data
    return fulldata

def R4_VAX2IEEE(vax):
    # type: (bytes) -> float
    """
    Convert 4 character VAX REAL*4 string into floating point value
    """
    intValue = bytes_to_int(vax)
    if intValue == 0:
        return 0.
    sign = (intValue >> 15) & 0x1
    exp = (intValue >> 7) & 0xff
    mant = ((intValue & 0x7f) << 16) | ((intValue >> 16) & 0xffff)

    value = (0.5 + mant / float(0x1000000)) * 2**(exp - 128)
    if sign == 1:
        value = -value
    return value

def R4_IEEE2VAX(fpValue, varName):
    # type: (float, str) -> bytes
    """
    Convert floating point value to VAR REAL*4 string
    """
    try:
        m, e = math.frexp(float(fpValue))
        if m == 0.0:
            intValue = 0
        else:
            sign = m < 0
            exp = e + 128
            mant = int((0x1000000 * (abs(m) - 0.5)) + 0.5)
            while mant >= 0x800000:
                exp += 1
                mant = (mant>> 1) - 0x400000
            if exp < 1:
                intValue = 0
            elif exp > 0xff:
                raise Exception("Exponent too large to store as VAX F float for %s."
                                % varName)
            else:
                intValue = ((sign << 15)
                            | (exp << 7)
                            | ((mant & 0x007f0000) >> 16)
                            | ((mant & 0x0000ffff) << 16))
        return int_to_bytes(intValue)
    except:
        print("VAX float F conversion error for %s value: %s"
              % (varName, fpValue))
        return b"\0\0\0\0"

# CRUFT: python 2.x support
if sys.version_info[0] == 2:
    def bytes_to_int(s):
        # type: (str) -> int
        return  ord(s[0]) | (ord(s[1]) << 8) | (ord(s[2]) << 16) | (ord(s[3]) << 24)
    def int_to_bytes(v):
        # type: (int) -> str
        return "".join(chr(k) for k in (v&0xff, (v>>8)&0xff, (v>>16)&0xff, (v>>24)&0xff))
else:
    def bytes_to_int(s):
        # type: (bytes) -> int
        return s[0] | (s[1]<<8) | (s[2]<<16) | (s[3]<<24)
    def int_to_bytes(v):
        # type: (int) -> bytes
        return bytes((v&0xff, (v>>8)&0xff, (v>>16)&0xff, (v>>24)&0xff))


# ==== demo ====
def plot(filename):
    # type: (str) -> None
    """
    Load and plot the SANS data filename.
    """
    from matplotlib import pyplot as plt
    try:
        data, metadata = load(filename)
    except IOError as exc:
        print(exc)
        return

    if metadata['run.type'] == 'RAW':
        data = np.log10(data+1)

    plt.figure()
    plt.imshow(data)
    plt.title(filename)

def _tocvs(f):
    # type: (Any) -> str
    # String
    try:
        return '"%s"'%(f.replace('\000', ' ').replace('\n', '\\n').replace('"', "'").strip())
    except Exception:
        pass
    # Date
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", f)
    except Exception:
        pass
    # Number
    return str(f)

def csv(fields):
    # type: (Iterator[Any]) -> str
    return ",".join(_tocvs(f) for f in fields)

def expand_input_args(*args):
    # type: (*str) -> List[str]
    """
    Convert args to a list of paths.

    If args[i] is a directory, return all .SA2 and .SA3 files in that directory.
    """
    import glob
    res = []
    for path in args:
        if os.path.isdir(path):
            res.extend(glob.glob(os.path.join(path, '*.SA[23]*')))
        else:
            res.append(path)
    return res


def show_meta(filename):
    # type: (str) -> None
    try:
        _, metadata = readNCNRData(filename)
        # analysis.factor doesn't match counts
        #x1, x2 = metadata['analysis.rows1'], metadata['analysis.rows2']
        #y1, y2 = metadata['analysis.rows1'], metadata['analysis.rows2']
        #metadata['analysis.ROIcounts'] = np.sum(detdata[x1:x2+1, y1:y2+1])
        del metadata['params.reserve']
        for k in sorted(metadata.keys()):
            print("%s: %s"%(k, metadata[k]))
    except IOError:
        print("* could not read %s"%filename)

def show_csv(filename, keys=None, headers=False):
    # type: (str, Optional[Sequence[str]], bool) -> None
    try:
        _, metadata = readNCNRData(filename)
        if keys is None:
            keys = list(sorted(metadata.keys()))
        if headers:
            print(",".join('"%s"'%k for k in keys))
        if 'directory' in keys:
            metadata['directory'] = os.path.dirname(filename)
        print(csv(metadata[k] for k in keys))
    except IOError:
        pass

def show_stats(filename, headers=False):
    # type: (str, bool) -> None
    if headers:
        print("filename, total, duration, rate, max")
    try:
        detdata, metadata = readNCNRData(filename)
        counts = np.sum(detdata)  # type: float
        count_time = metadata['run.rtime']
        rate = counts/count_time
        nmax = np.max(detdata)
        print("%s, %9d, %6d, %7.1f, %7d"
              % (filename, counts, count_time, rate, nmax))
    except Exception:
        print("%s,,,," % filename)

def demo():
    # type: () -> None
    summary_keys = [
        'directory',
        'fname.filename', 'run.datetime',
        'sample.labl', 'sample.position',
        'run.rtime', 'run.atten',
        'det.dis', 'resolution.ap1', 'resolution.ap2',
        'det.bstop', 'bmstp.xpos', 'bmstp.ypos', 'det.beamx', 'det.beamy',
        'resolution.lmda', 'resolution.dlmda',
        'sample.thk', 'sample.trns', 'sample.temp', 'sample.tunits',
        'run.moncnt', 'run.detcnt',
    ]

    if len(sys.argv) == 1 or "-?" in sys.argv:
        print("usage: [-s|-m|-c|-S] file ...")
        print(" -s  stats only")
        print(" -m  show metadata")
        print(" -c  convert to CSV")
        print(" -S  convert to CSV, but only include important fields")
        print(" -?  display this help and exit")
        return

    stats_only = len(sys.argv) > 1 and sys.argv[1] == '-s'
    show_metadata = len(sys.argv) > 1 and sys.argv[1] == '-m'
    show_csvdata = len(sys.argv) > 1 and sys.argv[1] in ('-c', '-S')
    # -S is cvsdata with a subset of the keys
    keys = summary_keys if sys.argv[1] == '-S' else None

    first_file_index = 2 if sys.argv[1].startswith('-') else 1
    files = expand_input_args(*sys.argv[first_file_index:])
    if stats_only:
        first = True
        for f in sys.argv[2:]:
            show_stats(f, headers=first)
            first = False
    elif show_metadata:
        for f in sys.argv[2:]:
            show_meta(f)
    elif show_csvdata:
        first = True
        for f in files:
            show_csv(f, keys=keys, headers=first)
            first = False
    else:
        for f in sys.argv[1:]:
            plot(f)
        from matplotlib import pyplot
        pyplot.show()

def copyfile(infile, outfile):
    # type: (str, str) -> None
    data, metadata = readNCNRData(infile)
    writeNCNRData(outfile, data, metadata)


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "copy":
        copyfile(sys.argv[2], sys.argv[3])
    else:
        demo()

if __name__ == '__main__':
    main()
