import os

import numpy as np

from reductus.dataflow.lib import iso8601
from .refldata import ReflData
from .nexusref import data_as, str_data
from .nexusref import NCNRNeXusRefl, load_nexus_entries

def load_entries(filename, file_obj=None, entries=None):
    #print("loading", filename, file_obj)
    return load_nexus_entries(filename, file_obj=file_obj, entries=entries,
                              meta_only=False, entry_loader=MagikHorizontal)

class MagikHorizontal(NCNRNeXusRefl):
    """
    MAGIK horizontal-mode data entry.

    See :class:`refldata.ReflData` for details.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry = "horizontal"
        self.align_intensity = "sample.angle_x"

    def load(self, entry):
        super().load(entry)
        das = entry['DAS_logs']
        n = self.points
        self.slit2.distance = data_as(das, 'horizontalGeom/dS2', '') #das['trajectoryData/_S2'].value
        self.slit1.distance = data_as(das, 'horizontalGeom/d21', '')  + self.slit2.distance
        if 'horizontalGeomBackSlit/dS3' in das:
            self.slit3.distance = data_as(das, 'horizontalGeomBackSlit/dS3', '')

        for k, s in enumerate([self.slit1, self.slit2, self.slit3, self.slit4]):
            s.y = s.x
            s.y_target = s.x_target
            s.x = np.ones_like(s.y) * np.inf
            s.x_target = np.ones_like(s.y) * np.inf

        for k, s in enumerate([self.slit1, self.slit2, self.slit3]):
            x = 'CVertSlit%d/opening'%(k+1)
            if x in das:
                s.x = data_as(das, x, '', rep=n)
                s.x_target = s.x

        tilt = data_as(das, 'horizontalGeom/angleZero', '', rep=n)
        angle = data_as(das, 'horizontalGeom/angle', '', rep=n)
        self.sample.angle_x = angle
        if (self.intent.startswith('rock')):
            self.sample.angle_x -= tilt
        self.sample.angle_x_target = self.sample.angle_x
        if 'horizontalGeomBackSlit/angleMultiplier' in das:
            # then we have a back slit that defines scattering angle
            multiplier = data_as(das, 'horizontalGeomBackSlit/angleMultiplier', '', rep=n)
        else:
            multiplier = 1
        self.detector.angle_x = angle + (angle * multiplier)
        self.detector.angle_x_target = self.detector.angle_x
