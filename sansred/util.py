# -*- coding: UTF-8 -*-
"""
Helper functions common to many writers.

To help with unicode support which is uniform between python 2 and python 3,
use :func:`unicode_to_str`, :func:`str_to_unicode`, :func:`bytes_to_str` and
:func:`bytes_to_unicode`.  Rather than *fid.write*, which expects *bytes* in
python 3 but *str* in python 2, use :func:`write`.  The *unicode* symbol is
defined for python 3 so that functions that are expecting unicode can be
labelled as such in the type hints. :func:`ascii_units` converts the extended
character symbos for degrees, Angstroms, Celsius, Farenheit and Ohms into
pure ascii strings using the NeXus names.
"""
from __future__ import print_function

import os
import sys
from math import floor, ceil, log10

import numpy as np

try:
    # pylint: disable=unused-import
    from typing import (Any, Dict, Sequence, Tuple, Union, Optional, List, Text,
                        AnyStr, TextIO, BinaryIO, IO, Iterator, Callable)
    # pylint: enable=unused-import
    ignore = 0  # keep pycharm happy
    Numeric = Union[float, int, np.ndarray]
    Record = Dict[str, Any]
    Stream = Iterator[Record]
except ImportError:
    Numeric = None
    Record = None
    Stream = None

from . import formatnum
from . import iso8601

MAX_DIGITS = 8
TRAJECTORY_DEVICE = "trajectory"
SCANNED_VARIABLES = TRAJECTORY_DEVICE + ".scannedVariables"
CONTROL_VARIABLES = TRAJECTORY_DEVICE + ".controlVariables"
TRAJECTORY_TITLE = TRAJECTORY_DEVICE + ".name"

# Name is specially chosen: counter device is renamed to empty
# and counter field is renamed to empty, so the result is
# shortened to counters.
COUNTS_ERROR_KEY = "counter.counter"

ASCII_UNITS = [
    ('°', 'deg'),
    ('Å', 'Ang'),
    ('℃', 'degC'),
    ('℉', 'degF'),
    ('Ω', 'ohm'),
    ]

# CRUFT: python 2.x needs to convert unicode to str; 3.x leaves it as unicode
if sys.version_info[0] >= 3:
    def unicode_to_str(s):
        # type: (AnyStr) -> str
        return s  # type: ignore
    def str_to_unicode(s):
        # type: (AnyStr) -> Text
        return s  # type: ignore
    def bytes_to_str(s):
        # type: (AnyStr) -> str
        return s.decode('utf-8') if isinstance(s, bytes) else s # type: ignore
    def str_to_bytes(s):
        # type: (AnyStr) -> bytes
        """Return byte string or list of byte strings"""
        if isinstance(s, list):
            return [(sk.encode('utf-8') if isinstance(sk, str) else sk)
                    for sk in s]
        else:
            return s.encode('utf-8') if isinstance(s, str) else s # type: ignore
    def write(fid, s):
        # type: (IO[Any], AnyStr) -> None
        #print("fid type=%s"%type(fid))
        fid.write(str_to_bytes(s))
else: # python 2.x
    # Note: python 2.x defines bytes=str, unicode
    def unicode_to_str(s):
        # type: (AnyStr) -> str
        # Note: slightly faster to beg for forgiveness
        try:
            return s.encode('utf-8')
        except AttributeError:
            return s
        #return s.encode('utf-8') if isinstance(s, unicode) else s
    def str_to_unicode(s):
        # type: (AnyStr) -> unicode
        try:
            return s.decode('utf-8')
        except AttributeError:
            return s
        #return s.decode('utf-8') if isinstance(s, str) else s
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

def ascii_units(s):
    # type: (Optional[Text]) -> Text
    if s is None:
        return s
    for old, new in ASCII_UNITS:
        s = s.replace(old, new)
    return s

def equal_nan(x, y):
    # type: (np.ndarray, np.ndarray) -> np.ndarray
    """
    Compare two numpy arrays, treating NaN objects as equal
    """
    if x.dtype.char in 'fdgFDG':
        return (x == y) | ((x != x) & (y != y)) # type: ignore
    else:
        return x == y # type: ignore


def make_directory(path):
    # type: (str) -> None
    """
    Create any directories required to store the file in *path*.
    """
    dirname = os.path.dirname(path)
    # Multiple writers may be trying to create the same path at the same time
    # leading to a race condition. Try again after failure; at this point the
    # shared part of the path should have already been created and so the
    # race condition will be gone.  In the case that dirname is bad, checking
    # twice is harmless.
    try:
        if not os.path.exists(dirname):
            os.makedirs(dirname)
    except Exception:
        if not os.path.exists(dirname):
            os.makedirs(dirname)

def timestamp(time):
    # type: (float) -> str
    """
    Return NICE timestamp as ISO 8601 format string.
    """
    return iso8601.format_date(time*0.001, precision=3)


def sensor_summary(sensor_data, latest_value):
    # type: (Sequence[Tuple[float, float, int, str]], float) -> float
    values = [vi for _time, vi, status, _msg in sensor_data if status == 0]
    return np.mean(values) if len(values) > 0 else latest_value

def data_width(field):
    # type: (Dict[str, Any]) -> int
    """
    Find the width of a data field given the field definition in the
    configure record.
    """
    datatype = field['type']
    if datatype.startswith('int'):
        if 'options' in field:
            datawidth = max(len(s) for s in field['options'])
        else:
            datawidth = 10
    elif datatype.startswith('float'):
        #if 'error' not in field: print "error missing from", field
        precision = field.get('error', 0.01)
        datawidth = len(formatnum.format_value(-100000, precision, max_digits=MAX_DIGITS))
    elif datatype == 'bool':
        datawidth = 1
    elif datatype in ('string', 'json'):
        if 'options' in field:
            datawidth = max(len(s) for s in field['options'])
        else:
            datawidth = 20
    elif datatype == 'time':
        # Assume time will be represented by delta from start of scan
        datawidth = 10
    else:
        print("unknown width for %s"%(field,))
        datawidth = 20
    return datawidth


def rename_field(fullname):
    # type: (str) -> str
    """
    Rename a field according to device and field name maps.

    The field name map is initialized from the file shortname.txt in the
    nice.writer source directory.  You probably want to update the names
    there.  For instrument specific changes, you can modify the global
    variables util.DEVICE_NAME_MAP and util.FIELD_NAME_MAP.  These will update
    the maps for all writers in the same process, so use with caution.

    Deprecated: should use filter.SetAlias instead
    """
    # Note: should be merged with the code in filter.SetAlias so that the
    # two mechanisms work the same.
    device, field = fullname.split('.')
    try:
        field, index = field.split('_')
    except Exception:
        index = ''
    device = DEVICE_NAME_MAP.get(device, device)
    field = FIELD_NAME_MAP.get(field, field)
    if device == '':
        return field+index
    elif field == '':
        return device+index
    else:
        return device+"."+field+index


def _shortnames_from_file(config_file):
    # type: (str) -> Dict[str, str]
    config = open(os.path.join(os.path.dirname(__file__), config_file)).read()
    return _shortnames(config)


def _shortnames(config):
    # type: (str) -> Dict[str, str]
    mapping = {}
    for line in config.split('\n'):
        if line.strip() != "" and not line.startswith('#'):
            longname, shortname = line.split()
            mapping[longname] = shortname if shortname != '-' else ""
    return mapping

DEVICE_NAME_MAP = _shortnames_from_file('devicenames.txt')
FIELD_NAME_MAP = _shortnames_from_file('fieldnames.txt')

def trim_digits(value, uncertainty, ndigits=2):
    # type: (float, float, int) -> Tuple[float, float]
    """
    Return value and uncertainty with the appropriate number of digits
    """
    err_place = int(floor(log10(uncertainty)))
    scale = 10.**(err_place-ndigits+1)
    uncertainty = floor(uncertainty/scale+0.5)*scale
    value = floor(value/scale+0.5)*scale
    return value, uncertainty

def sigfigs(value, ndigits=2):
    # type: (float, int) -> float
    """
    Return value with the given number of digits of precision.  This is
    not the number of digits after the decimal.  For that, use round(v, n)
    """
    if value == 0:
        return 0
    else:
        return round(value, -int(floor(log10(abs(value)))-ndigits+1))

def profile(fn, *args, **kw):
    # type: (Callable, *Any, **Any) -> Any
    """
    Profile a function called with the given arguments.
    """
    import cProfile
    import pstats
    datafile = 'profile.out'
    context = {'fn': fn, 'args': args, 'kw': kw}
    cProfile.runctx('result = fn(*args, **kw)', {}, context, datafile)
    stats = pstats.Stats(datafile)
    #order = 'calls'
    order = 'cumulative'
    #order = 'pcalls'
    #order = 'time'
    stats.sort_stats(order)
    stats.print_stats()
    os.unlink(datafile)
    return context['result']


class WriterStatus(object):
    """
    Notification of writer status.

    Writers should call the appropriate method when the data file is updated,
    leaving it to the notifier to determine how this is reported to the user.

    Create a new notifier by subclassing WriterStatus and overriding the
    methods corresponding to notifications that should be shared with the user.
    """
    def open_file(self, path, state):
        #type: (str, state.State) -> None
        """New has been opened."""
        pass
    def close_file(self, path, state):
        #type: (str, state.State) -> None
        """File has been closed"""
        pass
    def update_count(self, path, state):
        #type: (str, state.State) -> None
        """Counts have been updated, but still counting point"""
        pass
    def end_count(self, path, state):
        #type: (str, state.State) -> None
        """Counts have been completed for the current point"""
        pass
    def add_note(self, path, state):
        #type: (str, state.State) -> None
        """A note has file has been added to the file (e.g., peak fit results)."""
        pass


class ConsoleWriterStatus(WriterStatus):
    """
    Indicate writer status on the console.  Only reports open/close.
    """
    def _notify(self, action, path, state):
        #type: (str, str, state.State) -> None
        print('%s writing file "%s" for trajectory %s in experiment "%s"'
              %(action, path,
                state.data['trajectory.trajectoryID'],
                state.data['experiment.proposalId']))
        sys.stdout.flush()

    def open_file(self, path, state):
        #type: (str, state.State) -> None
        self._notify("Begin", path, state)

    def close_file(self, path, state):
        #type: (str, state.State) -> None
        self._notify("End", path, state)

writer_status = ConsoleWriterStatus()

def set_writer_status(notifier):
    # type: (WriterStatus) -> None
    """
    Set writer status notification handler.

    *notifier* is a :class:`WriterStatus` object.
    """
    global writer_status
    writer_status = notifier

# CRUFT: 2017-05-25 support for legacy writer status reporting
# Leave existing report_file_writing function as a shim for the new
# WriterStatus interface.  This allows existing writers to run without
# change.
class FakeState(object):
    """
    Shim for :class:`nice.writer.state.State` so data can be accessed as state.data
    """
    def __init__(self, data):
        # type: (Dict[str, Any]) -> None
        self.data = data
def report_file_writing(is_opening, path, data):
    # type: (bool, str, Dict[str, Any]) -> None
    """
    **Deprecated** Report writer status to the user

    New writers should use the :class:`WriterStatus` interface.
    """
    if is_opening:
        writer_status.open_file(path, FakeState(data))
    else:
        writer_status.close_file(path, FakeState(data))


def write_table_block_data(fid, frame, minimum_digits):
    # type: (TextIO, np.ndarray, int) -> None
    """
    Write data for one PSD or area detector frame.  Choose a column width
    so that columns are aligned between rows and the table is human readable.
    """
    max_counts = frame.max()
    digits = int(ceil(log10(max_counts))) if max_counts > 0 else 1
    digits = max(digits, minimum_digits)
    for row in frame:  # type: ignore
        fid.write(" ".join("%*d"%(digits, col) for col in row))  # type: ignore
        fid.write("\n")


def write_comma_block_data(fid, frame):
    # type: (TextIO, np.ndarray) -> None
    """
    Write data for one PSD or area detector frame.  Use ICP format, with
    comma separating columns, semicolon separating rows, and no lines longer
    than 78 characters.
    """
    # Round data to the nearest integer
    if frame.ndim == 2:
        rows = [",".join(str(v) for v in row) for row in frame]  # type: ignore
        text = ";".join(rows)
    else:
        text = ",".join(str(v) for v in frame)  # type: ignore
    fid.write(' ')
    start = 0
    while len(text)-start > 78:
        end = start+78
        while text[end] not in ",;":
            end -= 1
        fid.write(text[start:end+1])
        fid.write(' '*(78-(end-start)))
        fid.write('\n ')
        start = end+1
    fid.write(text[start:])
    fid.write('\n')


# CRUFT: python 2.x needs to convert unicode to str; 3.x leaves it as unicode
if sys.version_info[0] >= 3:
    DEICE_PASSTHROUGH = (str, bool, int, type(None))
else:
    DEICE_PASSTHROUGH = (str, bool, int, long, unicode, type(None))

def deice(obj):
    # type: (Any) -> Any
    """
    Convert a NICE type into python primitives which can be pickled by JSON.
    """
    import Ice
    # Note: the following assumes nice.config.load_slice() has been called
    # so that nice.api.data is available on the
    from nice.api import data  # type: ignore

    if isinstance(obj, float):
        # Special handling of floats to convert exceptional values to
        # specific numbers; ideally we would forward these to the server
        # and eventually forward them to the browser once JSON learns to
        # handle exceptional values.
        if np.isfinite(obj):
            return obj
        elif obj > 0:
            return 1e308
        elif obj < 0:
            return -1e308
        else: # NaN always compares false
            return 1e-308
    elif isinstance(obj, data.Value):
        # Special handling of data values needed to support polymorphism
        return deice(obj.val)
    elif isinstance(obj, Ice.Exception):
        # Convert exceptions into strings.
        return str(obj)
    elif isinstance(obj, Ice.Object):
        # A slice class definition
        return dict((k, deice(v)) for k, v in obj.__dict__.items())
    elif hasattr(obj, "value") and hasattr(obj, "_names"):
        # Convert enum value to a string representation
        return str(obj)
    elif isinstance(obj, dict):
        # A slice dictionary is a simple dictionary
        return dict((k, deice(v)) for k, v in obj.items())
    elif isinstance(obj, list):
        # A slice array is a list of slice objects
        return [deice(v) for v in obj]
    elif isinstance(obj, tuple):
        # A slice array is a list of slice objects
        return (deice(v) for v in obj)
    elif isinstance(obj, bytes):
        # Zero-C sends unicode from Java as strings in 'utf-8'
        return obj.decode('utf-8')
    elif isinstance(obj, DEICE_PASSTHROUGH):
        # Slice base type
        #print 'zeroc decodes', obj, 'as', type(obj)
        return obj
    else:
        # A slice struct is just an object with a dictionary
        #print "struct", str(type(obj)), obj.__dict__
        return dict((k, deice(v)) for k, v in obj.__dict__.items())

# Rob Cowie at stack overflow
# https://stackoverflow.com/questions/6796492/temporarily-redirect-stdout-stderr/6796752#6796752
class RedirectStdStreams(object):
    """
    Temporarily redirect standard streams.

    Usage::

        with RedirectStdStream(stdout=open('outputfile', 'w')):
            print("something")

    Only handles stdout and stderr, not stdin.
    """
    def __init__(self, stdout=None, stderr=None):
        # type: (Optional[file], Optional[file]) -> None
        self._stdout = stdout or sys.stdout
        self._stderr = stderr or sys.stderr

    def __enter__(self):
        # type: () -> None
        self.old_stdout, self.old_stderr = sys.stdout, sys.stderr
        self.old_stdout.flush()
        self.old_stderr.flush()
        sys.stdout, sys.stderr = self._stdout, self._stderr

    def __exit__(self, exc_type, exc_value, traceback):
        # type: (type, BaseException, types.TracebackType) -> Optional[bool]
        self._stdout.flush()
        self._stderr.flush()
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
