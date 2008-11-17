# This program is public domain.

"""
Support for rarely varying instrument configuration parameters.

Instrument configuration parameters will change throughout the
lifetime of an instrument.  For example, the properties of the
beam such as wavelength and wavelength divergence will change
when a new monochromator is installed on the instrument.  Ideally,
all such parameters would be encoded in the data file (this is
one goal of the NeXus file format), but this is not the case for
all instrument formats available today.

We cannot simply hard code the current value of the instrument
parameters in the file reader for the data file format.  Such a
reader will give bad values for old data files and for new data
files after the format has changed.  Nor should we burden the user
with knowing and entering values for such parameters on their own.

Instead, we provide support for dated values.  Each instrument has
a table of values and the date the values come into effect.  When
a file is loaded, the software scans the list of values, extracting
all that are in effect on the file date.

As instrument parameters change add additional lines to the configuration
file indicating the new value and the date of the change.  The order of
# the entries does not matter.  The timestamp on the file will
determine which value will be used.

The format of the entries should be::
    default.NAME = (VALUE, 'YYYY-MM-DD')  # value after MM/DD/YYYY
    default.NAME = (VALUE, '')            # value at commissioning

[Not implemented] Each data reader has an associated URL which
contains the configuration file for the instrument.  On file
load, the program will fetch dated values from the URL and use
them to populate the configuration data for the instrument.  This
gives control of the instrument parameters to the instrument
scientist where it belongs.

Example
=======

The following parameters are needed for the NG71reflectometer::

    config = properties.DatedValues()
    config.wavelength = (4.76,'')  # in case ICP records the wrong value

    # Detector response is uniform below 15000 counts/s.  The efficiency
    # curve above 15000 has not been measured.
    config.saturation = (numpy.array([[1,15000,0]]),'')

    config.detector_distance = (36*25.4, '') # mm
    config.psd_width = (20, '') # mm
    config.slit1_distance = (-75*25.4, '') # mm
    config.slit2_distance = (-14*25.4, '') # mm
    config.slit3_distance = (9*25.4, '') # mm
    config.slit4_distance = (42*25.4, '') # mm
    config.detector_distance = (48*25.4, '2004-02-15')

The defaults are used as follows::

    class Data:
         def load(filename):
             data = readheaders(filename)
             self.config = config(str(data.date))
             self.detector.distance = self.config.detector_distance
             ...

"""

# TODO: provide URI for the instrument configuration
# Check the URI if the file date is newer than the configuration date.  This
# will normally be true for the user, but there is no other way to make sure
# that they are using the most up-to-date values available.  The URI will
# be given on the constructor as DatedValues('URI').

# TODO: optimize repeated lookups.
# Currently we scan the table once for each file. A cheap optimization is to
# identify the range of dates surrounding the current date for which the
# value is correct and check if the new file falls in that range.  The next
# level is to cache a set of these ordered by date.  A third option is to
# build an in-memory database while the configuration values are registered
# so they don't need to be scanned on file load.

# TODO: identify data reader version required
# As the data format for the instrument evolves, old data readers may not
# be sufficient to read the new data.  For example, if the reflectometer
# gets a 2-D detector but the reflectometry data format does not yet
# support 2-D detectors, then a new reader will be required.

# TODO: property sheet editor
# Once the file parameters are loaded the values are displayed to
# the user on a property sheet.  Values different from the default
# are highlighted.  Users can edit the values, with changes noted in
# the reduction log so that data history is preserved.

# TODO: XML support
# We should probably support to/from xml for the purposes of
# saving and reloading corrections.


import re
datepattern = re.compile(r'^(19|20)\d\d-\d\d-\d\d$')
class DatedValuesInstance: pass
class DatedValues(object):
    def __init__(self):
        self.__dict__['_parameters'] = {}

    def __setattr__(self, name, pair):
        """
        Record the parameter value and the date it was set.  The pair should
        contain the value and the date.  The assignment will look like:
            datedvalue.name = (value, 'yyyy-mm-dd')
        """
        # Check that the date is valid
        value,date = pair
        assert date == "" or datepattern.match(date), \
            "Expected default.%s = (value,'YYYYMMDD')"%(name)

        # Record the value-date pair on the list of values for that parameters
        if name not in self._parameters:
            self._parameters[name] = []
        self._parameters[name].append(pair)

    def __call__(self, date):
        """
        Recover the parameter value for a specific date.
        """
        instance = DatedValuesInstance()
        for name,values in self._parameters.iteritems():
            # Sort parameter entries by date
            values.sort(lambda a,b: cmp(a[0],b[0]))
            for v,d in values:
                if d <= date: setattr(instance,name,v)
                else: break
        return instance

def test():
    default = DatedValues()
    default.a = (1,'')
    default.a = (2,'2000-12-15')
    default.a = (3,'2004-02-05')
    assert default('1993-01-01').a == 1
    assert default('2000-12-14').a == 1
    assert default('2000-12-15').a == 2
    assert default('2000-12-16').a == 2
    assert default('2006-02-19').a == 3

if __name__ == "__main__": test()
