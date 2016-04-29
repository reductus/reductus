# This program is public domain
"""
Attenuator correction.

Determine attenuator values from measurements.
"""
from ..pipeline import Correction
from ..refldata import Intent

from .util import group_data

class AdjustAttenuators(Correction):
    def apply(self, data):
        """Apply the angle correction to the data"""
        datasets = group_data(data)

        slits = dict((pol,d)
                     for (intent,pol),d in datasets.items()
                     if intent == Intent.slit)
