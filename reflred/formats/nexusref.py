# This program is public domain

"""
Load a NeXus file into a reflectometry data structure.
"""
import os

import h5py as h5
from .. import refldata
from . import unit
from . import iso8601

def data_as(field, units):
    """
    Return value of field in the desired units.
    """
    converter = unit.Converter(field.attrs.get('units', ''))
    return converter(field.value, units)

def nxfind(group, nxclass):
    """
    Iterate over the entries of type *nxclass* in the hdf5 *group*.
    """
    for entry in group.values():
        if nxclass == entry.attrs.get('NX_class', None):
            yield entry

def load_entries(filename):
    """
    Load the summary info for all entries in a NeXus file.
    """
    file = h5.File(filename)
    measurements = []
    for name,entry in file.items():
        nxclass = entry.attrs.get('NX_class', None)
        if nxclass == 'NXentry':
            measurements.append(NCNRNeXusRefl(entry,filename))
    return measurements


class NCNRNeXusRefl(refldata.ReflData):
    """
    NeXus reflectometry entry.

    See :class:`reflred.refldata.ReflData` for details.
    """
    format = "NeXus"

    def __init__(self, entry, filename):
        super(NCNRNeXusRefl,self).__init__()
        self.filename = os.path.abspath(filename)
        self.name = os.path.basename(filename).split('.')[0]
        self._set_metadata(entry)

        # Callback for lazy data
        self.detector.loadcounts = self.loadcounts

    def _set_metadata(self, entry):
        self.entry = entry
        self.date = iso8601.parse_date(entry['start_time'][0])
        self.description = entry['experiment_description'][0]
        self.sample.description = entry['sample/description'][0,0]
        self.instrument = entry['instrument/name'][0,0]
        self.detector.distance = 


    def loadcounts(self):
        # Load the counts from the data file
        counts = self.entry.NXinstrument.NXdetector.data.read()
        return counts

    def _load_slits(self, instrument):
        """
        Slit names have not been standardized.  Instead sort the
        NXaperature components by distance and assign them according
        to serial order, negative aperatures first and positive second.
        """
        slits = list(nxfind(instrument, 'NXaperature'))
        # Note: only supports to aperatures before and after.
        # Assumes x and y aperatures are coupled in the same
        # component.  This will likely be wrong for some instruments,
        # but we won't deal with that until we have real NeXus files
        # to support.
        # Assume the file writer was sane and specified all slit
        # distances in the same units so that sorting is simple.
        # Currently only slit distance is recorded, not slit opening.
        slits.sort(lambda a,b: -1 if a.distance < b.distance else 1)
        index = 0
        for slit in slits:
            d = slit.distance.value('meters')
            if d <= 0:
                # process first two slits only
                if index == 0:
                    self.slit1.distance = d
                    index += 1
                elif index == 1:
                    self.slit2.distance = d
                    index += 1
            elif d > 0:
                # skip leading slits
                if index < 2: index = 2
                if index == 2:
                    self.slit3.distance = d
                    index += 1
                elif index == 3:
                    self.slit4.distance = d
                    index += 1

    def load(self):
        entry = self.entry
        self.instrument = entry.NXinstrument.name.value
        self.probe = 'neutron'
        # Use proton charge as a proxy for monitor; we will use the
        # real monitor when it comes available.
        self.monitor.source_power_units = 'coulombs'
        self.monitor.source_power \
            = entry.proton_charge.read(self.monitor.source_power_units)
        self.monitor.count_time = entry.duration.read('seconds')
        self.monitor.base = 'power'

        # TODO: we are not yet reading the monitor values for the
        # reflectometers since they are not yet in place.  When they
        # are in place, it will be problematic since it will not
        # be clear to the reduction software whether it should be
        # using monitor 1 or monitor 2, and how it should normalize
        # if it is using one or the other without hardcoding details
        # of SNS Liquids into the reduction process.

        sample = entry.NXsample
        self.sample.description = sample.name.value

        # TODO: entry has sample changer position, which is a
        # way of saying we have no idea what sample is in the
        # beam.  I hope the control software handles this
        # properly!

        instrument = entry.NXinstrument
        self._load_slits(instrument)
        moderator = instrument.NXmoderator
        self.moderator.distance = moderator.distance.read('meters')
        self.moderator.type = moderator.type.value
        self.moderator.temperature = moderator.temperature.read('kelvin')
