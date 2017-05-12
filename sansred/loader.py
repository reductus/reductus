"""
SANS data loader
================

Load SANS NeXus file into :mod:`sansred.sansdata` data structure.
"""

from dataflow.lib import hzf_readonly_stripped as hzf
from dataflow.lib import unit

from .sansdata import SansData

metadata_lookup = {
    "det.dis": "DAS_logs/detectorPosition/softPosition",
    "resolution.lmda" : "DAS_logs/wavelength/wavelength",
    "det.beamx": "DAS_logs/areaDetector/beamCenterX",
    "det.beamy": "DAS_logs/areaDetector/beamCenterY",
    "det.pixelsizex": "instrument/detector/x_pixel_size",
    "det.pixelsizey": "instrument/detector/y_pixel_size",
    "analysis.intent": "DAS_logs/trajectoryData/intent",
    "analysis.filepurpose": "DAS_logs/trajectoryData/filepurpose",
    "sample.name": "DAS_logs/sample/name",
    "sample.description": "DAS_logs/sample/description",
    "sample.labl": "DAS_logs/sample/description", # compatibility
    "polarization.front": "DAS_logs/frontPolarization/direction",
    "polarization.back": "DAS_logs/backPolarization/direction",
    "run.filename": "DAS_logs/trajectoryData/fileName",
    "run.filePrefix": "DAS_logs/trajectoryData/filePrefix",
    "run.experimentScanID": "DAS_logs/trajectory/experimentScanID",
    "run.detcnt": "control/detector_counts",
    "run.rtime": "control/count_time",
    "run.moncnt": "control/monitor_counts",
    "run.atten": "instrument/attenuator/index",
    "analysis.groupid": "DAS_logs/trajectoryData/groupid",
    "run.configuration": "DAS_logs/configuration/key",
    "sample.thk": "DAS_logs/sample/thickness",
}

unit_specifiers = {
    "det.dis": "cm",
    "det.pixelsizex": "cm",
    "det.pixelsizey": "cm",
    "sample.thk": "cm"
}

def data_as(field, units):
    """
    Return value of field in the desired units.
    """
    converter = unit.Converter(field.attrs.get('units', ''))
    value = converter(field.value, units)
    return value

def readSANSNexuz(input_file, file_obj=None):
    """
    Load all entries from the NeXus file into sans data sets.
    """
    datasets = []
    file = hzf.File(input_file, file_obj)
    for entryname, entry in file.items():
        metadata = {}
        reals = {}

        detdata = entry['data/areaDetector'].value.reshape(128, 128)

        for mkey in metadata_lookup:
            field = entry.get(metadata_lookup[mkey], None)
            if field is not None:
                if mkey in unit_specifiers:
                    field = data_as(field, unit_specifiers[mkey])[0]
                else:
                    field = field.value[0]
                if field.dtype.kind == 'f':
                    field = field.astype("float")
                elif field.dtype.kind == 'i':
                    field = field.astype("int")

            metadata[mkey] = field

        metadata['entry'] = entryname
        #metadata['det.dis'] = das['detectorPosition/softPosition'].value[0]
        #metadata['resolution.lmda'] = das['wavelength/ewavelength'].value[0]
        #metadata['det.beamx'] = das['areaDetector/beamCenterX'].value[0]
        #metadata['det.beamy'] = das['areaDetector/beamCenterY'].value[0]

        dataset = SansData(data=detdata, metadata=metadata)
        datasets.append(dataset)

    return datasets
