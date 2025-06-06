# -*- coding: latin-1 -*-
# This program is public domain
# Author: Paul Kienzle
"""
Define unit conversion support for NeXus style units.

The unit format is somewhat complicated.  There are variant spellings
and incorrect capitalization to worry about, as well as forms such as
"mili*metre" and "1e-7 seconds".

This is a minimal implementation.  It does not support the complete
dimensional analysis provided by the package UDUnits on which NeXus is
based, or even all the units used in the NeXus definition files.

Unlike other units modules, this module does not carry the units along
with the value, but merely provides a conversion function for
transforming values.

Usage example::

    >>> from reductus.dataflow.lib import unit
    >>> u = unit.Converter('mili*metre')  # Units stored in mm
    >>> v = u(3000, 'm')  # Convert the value 3000 mm into meters

NeXus example::

    # Load sample orientation in radians regardless of how it is stored.
    # 1. Open the path
    import nxs
    file = nxs.open(filename)
    file.openpath('/entry1/sample/sample_orientation')
    # 2. scan the attributes, retrieving 'units'
    units = [for attr, value in file.attrs() if attr == 'units']
    # 3. set up the converter (assumes that units actually exists)
    u = unit.Converter(units[0])
    # 4. read the data and convert to the correct units
    v = u(file.read(), 'radians')

NeXus example using h5py, and a private version of unit::

    import h5py
    from reductus.dataflow.lib import unit
    file = h5py.File(filename)
    field = file['/entry1/sample/sample_orientation']
    u = unit.Converter(field.attrs.get('units', ''))
    v = u(field[()], 'radians')

Note: minutes are used for angle and seconds are used for time.  We
cannot determine the correct interpretation without knowing something
about the fields themselves.  If this becomes an issue, we will need to
allow the application to set the dimension for the units rather than
getting the dimension from the units as we are currently doing.
"""

# TODO: Parse the udunits database directly
# UDUnits:
#  https://www.unidata.ucar.edu/software/udunits/udunits-1/udunits.txt

from __future__ import division

__all__ = ['Converter']

import math


# Limited form of units for returning objects of a specific type.
# Maybe want to do full units handling with e.g., pyre's
# unit class. For now lets keep it simple.  Note that
def _build_metric_units(unit, abbr):
    """
    Construct standard SI names for the given unit.
    Builds e.g.,
        s, ns
        second, nanosecond, nano*second
        seconds, nanoseconds
    Includes prefixes for femto through peta.

    Ack! Allows, e.g., Coulomb and coulomb even though Coulomb is not
    a unit because some NeXus files store it that way!

    Returns a dictionary of names and scales.
    """
    prefix = dict(peta=1e15, tera=1e12, giga=1e9, mega=1e6, kilo=1e3,
                  deci=1e-1, centi=1e-2, milli=1e-3, mili=1e-3, micro=1e-6,
                  nano=1e-9, pico=1e-12, femto=1e-15)
    short_prefix = dict(P=1e15, T=1e12, G=1e9, M=1e6, k=1e3,
                        d=1e-1, c=1e-2, m=1e-3, u=1e-6,
                        n=1e-9, p=1e-12, f=1e-15)
    short_prefix['μ'] = 1e-6
    map = {abbr:1}
    map.update([(P+abbr, scale) for (P, scale) in short_prefix.items()])
    for name in [unit, unit.capitalize()]:
        map.update({name:1, name+'s':1})
        map.update([(P+name, scale) for (P, scale) in prefix.items()])
        map.update([(P+'*'+name, scale) for (P, scale) in prefix.items()])
        map.update([(P+name+'s', scale) for (P, scale) in prefix.items()])
    return map


def _build_plural_units(**kw):
    """
    Construct names for the given units.  Builds singular and plural form.
    """
    map = {}
    map.update([(name, scale) for name, scale in kw.items()])
    map.update([(name+'s', scale) for name, scale in kw.items()])
    return map


def _build_all_units():
    # Various distance measures
    distance = _build_metric_units('meter', 'm')
    distance.update(_build_metric_units('metre', 'm'))
    distance.update(_build_plural_units(micron=1e-6,
                                        Angstrom=1e-10,
                                        angstrom=1e-10,
                                       ))
    distance.update({'A': 1e-10, 'Ang' :1e-10, 'Å': 1e-10, 'Ångström': 1e-10})

    # Various time measures.
    # Note: minutes are used for angle rather than time
    time = _build_metric_units('second', 's')
    time.update(_build_plural_units(hour=3600, day=24*3600, week=7*24*3600))
    time.update({'1e-7 s':1e-7, '1e-7 second':1e-7, '1e-7 seconds':1e-7})

    # Various angle measures.
    # Note: seconds are used for time rather than angle
    angle = _build_plural_units(degree=1, minute=1/60., arcminute=1/60.,
                                arcsecond=1/3600., radian=180/math.pi)
    angle.update(deg=1, arcmin=1/60., arcsec=1/3600., rad=180/math.pi)

    frequency = _build_metric_units('hertz', 'Hz')
    frequency.update(_build_metric_units('Hertz', 'Hz'))
    frequency.update(_build_plural_units(rpm=1/60.))

    # Note: degrees are used for angle
    # TODO: temperature needs an offset as well as a scale
    temperature = _build_metric_units('kelvin', 'K')
    temperature.update(_build_metric_units('Kelvin', 'K'))

    charge = _build_metric_units('coulomb', 'C')
    charge.update({'microAmp*hour':0.0036})

    sld = {'10^-6 Angstrom^-2': 1e-6, 'Angstrom^-2': 1}
    Q = {'invAng': 1, 'invAngstroms': 1,
         '10^-3 Angstrom^-1': 1e-3, 'nm^-1': 10}

    energy = _build_metric_units('electronvolt', 'eV')

    power = _build_metric_units('watt', 'W')

    # APS files may be using 'a.u.' for 'arbitrary units'.  Other
    # facilities are leaving the units blank, using ??? or not even
    # writing the units attributes.
    unknown = {None:1, '???':1, '': 1, 'a.u.':1}

    dims = [unknown, distance, time, angle, frequency,
            temperature, charge, sld, Q, energy, power]
    return dims


class Converter(object):
    """
    Unit converter for NeXus style units.
    """
    # Define the units, using both American and European spelling.
    scalemap = None
    scalebase = 1
    dims = _build_all_units()

    def __init__(self, name):
        self.base = name
        for map in self.dims:
            if name in map:
                self.scalemap = map
                self.scalebase = self.scalemap[name]
                break
        else:
            self.scalemap = {'': 1}
            self.scalebase = 1
            #raise ValueError, "Unknown unit %s"%name

    def scale(self, units=""):
        if units == "" or self.scalemap is None:
            return 1
        return self.scalebase/self.scalemap[units]

    def conversion(self, units=""):
        if units == "" or self.scalemap is None:
            return 1.0
        try:
            return self.scalebase/self.scalemap[units]
        except KeyError:
            raise KeyError("%s not in %s (base = %s)"%(units, " ".join(sorted(self.scalemap.keys())), self.base))

    def __call__(self, value, units=""):
        # Note: calculating value*1.0 rather than simply returning value
        # would produce an unnecessary copy of the array, which in the
        # case of the raw counts array would be bad.  Sometimes copying
        # and other times not copying is also bad, but copy on modify
        # semantics isn't supported.
        a = self.conversion(units)
        return value if a == 1.0 else value*a

def _check(expect, get):
    if expect != get:
        raise ValueError("Expected %s but got %s"%(expect, get))
    #print expect, "==", get

def test():
    _check(2, Converter('mm')(2000, 'm')) # 2000 mm -> 2 m
    _check(0.003, Converter('microseconds')(3, units='ms')) # 3 us -> 0.003 ms
    _check(45, Converter('nanokelvin')(45))  # 45 nK -> 45 nK
    # TODO: more tests
    _check(0.5, Converter('seconds')(1800, units='hours')) # 1800 -> 0.5 hr
    _check(2.5, Converter('a.u.')(2.5, units=''))

if __name__ == "__main__":
    test()
