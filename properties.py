# This program is public domain.

"""
A correction has a property sheet which currently is a list of
names of attributes for the correction.  The attributes are
assumed to be floating point values.  These need to be made richer 
so that properties contain names, labels and units for real valued 
properties, choice lists for string valued properties, and more 
sophisticated options such as reflectometry model definition panes 
for reflectometry model properties.  Note that some properties
are read-only.  Note that changes to properties must be logged,
at least as properties are used to represent and override metadata
in the data file format.

We should probably support to/from xml for the purposes of
saving and reloading corrections.

Many data file format assume hard-coded instrument 
parameters which may vary occasionally over time.   We 
need a systematic way of dealing with these.  Putting them 
in configuration files is a bad idea because then the results 
of the analysis will depend on the machine on which they were
run.  The safest approach is to use the file date in order
to select the correct values for the constants, and update
the data reader whenever the instrument configuration
changes.  

Keeping the data reader up to date on the users machine will
be a challenge.  A portal strategy reduces the problem because
then only the portal versions need to be updated.  Placing the 
data reader at a fixed URI and making it trivial for the user to 
update to the new version when they load the file will be important 
for assuring that they are using the most up to date information 
available.

Example:


# Instrument parameters
# As instrument parameters change add additional lines to this file
# indicating the new value and the date of the change.  The order of
# the entries does not matter.  The timestamp on the file will
# determine which value will be used.
# The format of the entries should be:
#      default.NAME = (VALUE, 'YYYY-MM-DD')  # value in effect after DD/MM/YYYY
#      default.NAME = (VALUE, '')          # value in effect at commissioning
default = properties.DatedValues()
default.wavelength = (4.76,'')  # in case ICP records the wrong value

# Detector saturates at 15000 counts/s.  The efficiency curve above 
# 15000 has not been measured.
default.saturation = (numpy.array([[1,15000,0]]),'')

    
default.detector_distance = (36*25.4, '') # mm
default.psd_width = (20, '') # mm
default.slit1_distance = (-75*25.4, '') # mm
default.slit2_distance = (-14*25.4, '') # mm
default.slit3_distance = (9*25.4, '') # mm
default.slit4_distance = (42*25.4, '') # mm
default.detector_distance = (48*25.4, '2004-02-15')

class Data:
     def load(filename):
         data = readheaders(filename)
         self.default = default(str(data.date))
         self.detector.distance = self.default.detector_distance
         ...
"""

import re
datepattern = re.compile(r'^(19|20)\d\d-\d\d-\d\d$')
class DatedValuesInstance: pass
class DatedValues(object):
    def __init__(self):
        self.__dict__['_parameters'] = {}
    def __setattr__(self, name, pair):
        """
        Record the parameter value on a specific date.
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
        parameters = self._parameters
        instance = DatedValuesInstance()
        for name,values in parameters.iteritems():
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
