# This program is public domain

"""
Load a NeXus file into a reflectometry data structure.
"""

import refldata

def register_extensions(registry):
    registry['.nxs'] = readentries

def readentries(filename):
    tree = nexus.read(filename)
    ret = []
    for name,entry in tree.nodes():
        if entry.nxclass == 'NXentry':
            ret.append(NeXusRefl(entry,filename))
    return ret

class NeXusRefl(refldata.ReflData):
    format = "NeXus"

    def __init__(self, entry, filename):
        super(ReflIcp,self).__init__(args, kw)
        self.filename = os.path.abspath(filename)

        if entry.definition == "TOFRAW":
            self._load_TOFRAW(entry)
        else:
            raise ValueError, "NeXusRefl only supports TOFRAW format"

    def _load_slits(self, instrument):
        """
        Slit names have not been standardized.  Instead sort the
        NXaperature components by distance and assign them according
        to serial order, negative aperatures first and positive second.
        """
        instrument.match('NXaperature')
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
                
    def _load_TOFRAW(self):
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

        sample = entry.find('NXsample')
        self.sample.description = sample.name.value
        
        # TODO: entry has sample changer position, which is a
        # way of saying we have no idea what sample is in the
        # beam.  I hope the control software handles this
        # properly!

        instrument = entry.find('NXinstrument')            
        self._load_slits(instrument)
        moderator = instrument.find('NXmoderator')
        self.moderator.distance = moderator.distance.read('meters')
        self.moderator.type = moderator.type.read()
        self.moderator.temperature = moderator.temperature.read('kelvin')
