# This program is public domain.
#
# Author: Paul Kienzle
# Based on iso8601 by Michael Twomey
"""
ISO 8601 date time support

Basic usage::

    >>> import iso8601
    >>> iso8601.parse_date("2007-01-25T12:34:56Z")
    datetime.datetime(2007, 1, 25, 12, 34, 56, tzinfo=<TimeZone 'UTC'>)
    >>> iso8601.parse_date("2007-01-25T12:34:56-0500")
    datetime.datetime(2007, 1, 25, 12, 34, 56, tzinfo=<TimeZone '-0500'>)
    >>> iso8601.seconds_since_epoch("2007-01-25T12:00:00Z")
    1169744400.0
    >>> print iso8601.format_date(1169744400.0)
    2007-01-25T07:00:00-05:00

The above examples assume US Eastern Standard Time, and may be different
in your time zone.

This code is incomplete.  It does not accept compressed formats (YYYYMMDD
and HHMMSS), week numbers (YYYY-Www-D), day numbers (YYYY-DDD), durations
P#Y#M#DT#H#M#S, intervals (date/date or date/interval), or repeating intervals
(R#/date/date or R#/date/interval).
"""
__all__ = ["parse_date", "format_date", "now", "seconds_since_epoch"]

import time
from datetime import datetime, timedelta, tzinfo
import re

ISO8601_RELAXED = re.compile(r"""^ # anchor to start of string
  (?P<year>[0-9]{4})               # year   YYYY
  (-(?P<month>[0-9]{1,2})          # month  -M or -MM
    (-(?P<day>[0-9]{1,2})          # day    -D or -DD
      (.                           # separator (usually T or space)
        (?P<hour>[0-9]{1,2})       # hour   H or HH
        :(?P<minute>[0-9]{2})      # minute :MM
        (:(?P<second>[0-9]{2})     # second :SS
          (\.(?P<fraction>[0-9]+)  # fractional second .SSS to arbitrary precision
          )?                       # .SSS is optional
        )?                         # SS.SSS is optional
        (?P<timezone>
          Z                        # use Z for UTC
          |
          (?P<tzprefix>[+-])       # +/- offset
          (?P<tzhour>[0-9]{1,2})   # hour offset H or HH
          (:?                      # optional separator for minute offset
            (?P<tzminute>[0-9]{2}) # minute offset MM
          )?                       # optional minute offset
        )?                         # optional time zone
      )?                           # optional time+time zone
    )?                             # YYYY-MM only
  )?                               # YYYY only
  $                                # anchor to end of the string
  """, re.VERBOSE)
ISO8601_STRICT = re.compile(r"""^ # anchor to start of string
  (?P<year>[0-9]{4})              # year   YYYY
  -(?P<month>[0-9]{2})            # month  -MM
  -(?P<day>[0-9]{2})              # day    -DD
  (\ |T)(?P<hour>[0-9]{2})        # hour   THH
  :(?P<minute>[0-9]{2})           # minute :MM
  (:(?P<second>[0-9]{2})          # second :SS
    (\.(?P<fraction>[0-9]+))?     # optional fractional second .SSS to arbitrary precision
  )?                              # optional SS.SSS
  (?P<timezone>
    Z                             # use Z for UTC
    |
    (?P<tzprefix>[+-])            # +/- offset
    (?P<tzhour>[0-9]{2})          # hour offset HH
    :?                            # optional separator for minute offset
    (?P<tzminute>[0-9]{2})        # minute offset MM
  )?                              # time zone is optional, except for really strict
  $                               # anchor to end of the string
  """, re.VERBOSE)

def now(use_microsecond=False):
    """
    Return the current time as an ISO 8601 string.

    Times are recorded in the local time zone, with an offset from UTC.

    If *use_microsecond* then include fractional seconds in the
    returned string.
    """
    return format_date(time.time(),precision=(6 if use_microsecond else 0))

def format_date(timestamp, precision=0):
    """
    Construct an ISO 8601 time from a timestamp.

    There are several possible sources for *timestamp*.

    - time.time() returns a floating point number of seconds since the
      UNIX epoch of Jan 1, 1970 UTC.

    - time.localtime(time.time()) returns a time tuple for the current
      time using the local time representation.

    - datetime.datetime.now() returns a datetime object for the current
      time using the local time representation, but with no information
      about time zone.

    - iso8601.parse_date(str) returns a datetime object for a previously
      stored time stamp which retains time zone information.

    In the first three cases the formatted date will use the local time
    representation but include the UTC offset for the local time.  The
    fourth case the UTC offset of the time stamp will be preserved in
    formatting.

    If *precision* is given, encode fractional seconds with this many digits
    of precision. This only works if *timestamp* is datetime object or seconds
    since epoch.
    """
    dt = None
    microsecond = 0

    # Try converting from seconds to time_struct
    try:
        microsecond = int(1000000*(timestamp-int(timestamp)))
        timestamp = time.localtime(timestamp)
    except TypeError:
        # Not a floating point timestamp; could be datetime or time_struct
        pass

    # Try converting from datetime to time_struct
    if isinstance(timestamp, datetime):
        microsecond = timestamp.microsecond
        tz = timestamp.utcoffset()
        if tz is not None:
            dt = tz.days*86400 + tz.seconds
        timestamp = timestamp.timetuple()

    # Find time zone offset
    isdst = timestamp.tm_isdst if timestamp.tm_isdst >=0 else 0
    if dt is None:
        dt = -(time.timezone,time.altzone)[isdst]

    # Do the formatting
    local = time.strftime('%Y-%m-%dT%H:%M:%S',timestamp)
    sign = "+" if dt >= 0 else "-"
    offset = "%02d:%02d"%(abs(dt)//3600,(abs(dt)%3600)//60)
    fraction = ".%0*d"%(precision,microsecond//10**(6-precision)) if precision else ""
    return "".join((local,fraction,sign,offset))

class TimeZone(tzinfo):
    """
    Fixed offset time zone in seconds from UTC
    """
    def __init__(self, offset=0, name=None):
        second = int(abs(offset)+0.5)
        if second%60 != 0:
            raise ValueError("offset must be a whole number of minutes")
        self.__offset = timedelta(seconds=offset)
        if name is None:
            sign = '-' if offset < 0 else '+'
            hour = second//3600
            minute = (second%3600)//60
            name = "%s%02d:%02d"%(sign,hour,minute)
        self.__name = name

    def utcoffset(self, dt):
        """
        Return offset from UTC.
        """
        return self.__offset

    def tzname(self, dt):
        """
        Return a description of the time zone.

        This will just be the string offset, or it will be UTC.
        """
        return self.__name

    def dst(self, dt):
        """
        Return daylight savings time offset.

        We can't tell from the +/- offset timestamp if daylight savings
        is in effect, or if we are just one timezone removed, so DST always
        returns a time delta of 0.
        """
        return timedelta(0)

    def __repr__(self):
        return "<TimeZone %r>" % self.__name

UTC = TimeZone(name="UTC")
EPOCH = datetime(1970,1,1,tzinfo=UTC)

def parse_date(datestring, default_timezone=UTC, strict=False):
    """
    Parses ISO 8601 dates into datetime objects

    The timezone is parsed from the date string. However it is quite common to
    have dates without a timezone (not strictly correct). In this case the
    default timezone specified in default_timezone is used. This is UTC by
    default.

    If strict is True, then only accept YYYY-MM-DD.HH:MM[:SS.SSS][time zone]

    Raises TypeError if not passed a string.
    Raises ValueError if the string is not a valid time stamp.
    """
    try:
        if not strict:
            m = ISO8601_RELAXED.match(datestring)
        else:
            m = ISO8601_STRICT.match(datestring)
    except TypeError:
        raise TypeError("parse_date expects a string")
    if not m:
        raise ValueError("Unable to parse date string %r" % datestring)
    groups = m.groupdict()
    year = int(groups["year"])
    month = int(groups["month"]) if groups["month"] else 1
    day = int(groups["day"]) if groups["day"] else 1
    hour = int(groups["hour"]) if groups["hour"] else 0
    minute = int(groups["minute"]) if groups["minute"] else 0
    second = int(groups["second"]) if groups["second"] else 0
    fraction = int(float("0.%s" % groups["fraction"]) * 1e6) if groups["fraction"] else 0
    if groups["timezone"] is None:
        tz = default_timezone
    elif groups["timezone"]=="Z":
        tz = UTC
    else:
        sign = +1 if groups["tzprefix"]=="+" else -1
        dt = (int(groups["tzhour"])*60
              + (int(groups["tzminute"]) if groups["tzminute"] else 0))
        tz = TimeZone(name=groups["timezone"], offset=sign*dt*60)
    return datetime(year,month,day,hour,minute,second,fraction,tz)

def seconds_since_epoch(datestring, default_timezone=UTC):
    """
    Parse ISO 8601 dates into seconds since epoch.
    """
    t = parse_date(datestring, default_timezone=default_timezone)
    dt = t - EPOCH
    return dt.days*86400 + dt.seconds + dt.microseconds*1e-6


# ================= TESTS =================
def _check_date(s,d,strict):
    t = parse_date(s)
    assert t-d == timedelta(0),"%r != %s"%(s,d)
    try:
        parse_date(s, strict=True)
        if not strict:
            raise Exception("exception not raised for strict %r"%s)
    except ValueError, exc:
        if strict:
            raise Exception("unexpected exception for strict %r\n  %s"
                            %(s,str(exc)))
def _check_fail(s):
    try: parse_date(s)
    except: return
    raise Exception("exception not raised for %r")

def _check_equal(s1,s2):
    assert parse_date(s1)-parse_date(s2) == timedelta(0), "%r != %r"%(s1,s2)

def _check_format(s,d):
    s2 = format_date(d)
    assert s==s2, "%r != %r"%(s,s2)
def test():
    _check_fail("2007-03-23T05:27Z0500")
    _check_fail("200")
    _check_fail("garbage")
    _check_date("2007",datetime(2007,1,1,0,0,0,0,UTC),strict=False)
    _check_date("2007-03",datetime(2007,3,1,0,0,0,0,UTC),strict=False)
    _check_date("2007-03-23",datetime(2007,3,23,0,0,0,0,UTC),strict=False)
    _check_date("2007-3-23",datetime(2007,3,23,0,0,0,0,UTC),strict=False)
    _check_date("2007-3-3",datetime(2007,3,3,0,0,0,0,UTC),strict=False)
    _check_date("2007-03-23T05:27",datetime(2007,3,23,5,27,0,0,UTC),strict=True)
    _check_date("2007-03-23 05:27",datetime(2007,3,23,5,27,0,0,UTC),strict=True)
    _check_date("2007-03-23 05:27Z",datetime(2007,3,23,5,27,0,0,UTC),strict=True)
    _check_date("2007-03-23 05:27Z",datetime(2007,3,23,5,27,0,0,UTC),strict=True)
    _check_date("2007-03-23T05:27-0300",
                datetime(2007,3,23,5,27,0,0,TimeZone(-3*3600)),strict=True)
    _check_date("2007-03-23T05:27-300",
                datetime(2007,3,23,5,27,0,0,TimeZone(-3*3600)),strict=False)
    _check_date("2007-03-23T05:27-03",
                datetime(2007,3,23,5,27,0,0,TimeZone(-3*3600)),strict=False)
    _check_date("2007-03-23T05:27+2",
                datetime(2007,3,23,5,27,0,0,TimeZone(2*3600)),strict=False)
    _check_date("2007-03-23T05:27:23.023-0300",
                datetime(2007,3,23,5,27,23,23000,TimeZone(-3*3600)),strict=True)
    _check_date("2007-03-23T05:27:23.023-0300",
                datetime(2007,3,23,5,27,23,23000,TimeZone(-3*3600)),strict=True)
    _check_equal("2007-03-23T02:17-0330","2007-03-23T05:47Z")

    # Check seconds since epoch calculations
    got = seconds_since_epoch("2007-01-25T12:30:00Z")
    expected = 1169728200
    assert got == expected,"%s != %s"%(got,expected)
    got = seconds_since_epoch("2007-01-25T12:30:00-0100")
    assert got == expected+3600,"%s != %s"%(got,expected+3600)
    got = seconds_since_epoch("2007-01-25T12:30:00.1-0100")
    assert abs(got-(expected+3600.1))<1e-6,"%s != %s"%(got,expected+3600.1)

    # Determine local time offset
    hrs = abs(time.timezone)//3600
    mins = (abs(time.timezone)%3600)//60
    utcoffset = "%s%02d:%02d"%('-' if time.timezone>=0 else '+', hrs, mins)

    # Check format from naive datetime object
    _check_format("2007-01-24T05:27:23"+utcoffset,
                  datetime(2007,1,24,5,27,23,16400))

    # Check formatting from struct_time object
    _check_format("2007-01-23T05:27:24"+utcoffset,
                  datetime(2007,1,23,5,27,24).timetuple())

    # Check formatting from seconds since epoch
    got = format_date(seconds_since_epoch("2007-01-25T11:30:00-0100"))
    expected = format_date(datetime(2007,1,25,12-hrs,30-mins))
    assert got == expected, "%r != %r"%(got, expected)

    # Check formatting from zoned datetime objects
    expected = "2007-01-25T11:30:00-01:00"
    got = format_date(parse_date(expected))
    assert got == expected, "%r != %r"%(got, expected)

if __name__ == "__main__":
    test()
