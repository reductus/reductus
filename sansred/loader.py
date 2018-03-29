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
    "resolution.lmda" : "instrument/monochromator/wavelength",
    "resolution.dlmda": "instrument/monochromator/wavelength_error",
    "det.beamx": "instrument/detector/beam_center_x",
    "det.beamy": "instrument/detector/beam_center_y",
    "det.pixeloffsetx": "instrument/detector/x_offset",
    "det.pixelsizex": "instrument/detector/x_pixel_size",
    "det.pixeloffsety": "instrument/detector/y_offset",
    "det.pixelsizey": "instrument/detector/y_pixel_size",
    "analysis.intent": "DAS_logs/trajectoryData/intent",
    "analysis.filepurpose": "DAS_logs/trajectoryData/filePurpose",
    "sample.name": "DAS_logs/sample/name",
    "sample.description": "DAS_logs/sample/description",
    "sample.labl": "DAS_logs/sample/description", # compatibility
    "polarization.front": "DAS_logs/frontPolarization/direction",
    "polarization.back": "DAS_logs/backPolarization/direction",
    "run.filename": "DAS_logs/trajectoryData/fileName",
    "run.filePrefix": "DAS_logs/trajectoryData/filePrefix",
    "run.experimentScanID": "DAS_logs/trajectory/experimentScanID",
    "run.instrumentScanID": "DAS_logs/trajectory/instrumentScanID",
    "run.detcnt": "control/detector_counts",
    "run.rtime": "control/count_time",
    "run.moncnt": "control/monitor_counts",
    "run.atten": "instrument/attenuator/index",
    "analysis.groupid": "DAS_logs/trajectoryData/groupid",
    "run.configuration": "DAS_logs/configuration/key",
    "sample.thk": "DAS_logs/sample/thickness",
    "adam.voltage": "DAS_logs/adam4021/voltage",
    "sample.temp": "DAS_logs/temp/primaryNode/average_value",
    "resolution.ap1": "DAS_logs/geometry/sourceAperture",
    "resolution.ap2": "instrument/sample_aperture/size",
    "resolution.ap12dis": "instrument/source_aperture/distance",
    "sample.position": "instrument/sample_aperture/distance",
    "rfflipperpowersupply.voltage":  "DAS_logs/RFFlipperPowerSupply/actualVoltage/average_value",
    "rfflipperpowersupply.frequency":  "DAS_logs/RFFlipperPowerSupply/frequency",
    "huberRotation.softPosition":  "DAS_logs/huberRotation/softPosition",
    "start_time":"start_time",
    "end_time":"end_time",
}

unit_specifiers = {
    "det.dis": "cm",
    "det.pixelsizex": "cm",
    "det.pixeloffsetx": "cm",
    "det.pixelsizey": "cm",
    "det.pixeloffsety": "cm",
    "sample.thk": "cm",
    "resolution.ap1": "cm",
    "resolution.ap2": "cm",
    "sample.thk": "cm"
}

def process_sourceAperture(field, units):
    import numpy as np
    def handler(v):
        return np.float(v.split()[0])
    handle_values = np.vectorize(handler)
    value = handle_values(field.value)
    units_from = ""
    v0 = field.value[0].split()
    if len(v0) > 1:
        units_from = v0[1]
    converter = unit.Converter(units_from)
    return converter(value, units)    

def data_as(field, units):
    """
    Return value of field in the desired units.
    """
    if field.name.split('/')[-1] == 'sourceAperture':
        return process_sourceAperture(field, units)
    else:
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
        areaDetector = entry['data/areaDetector'].value
        shape = areaDetector.shape
        if len(shape) < 2 or len(shape) > 3:
            raise ValueError("areaDetector data must have dimension 2 or 3")
            return
        if len(shape) == 2:
            # add another dimension at the front
            shape = (1,) + shape
            areaDetector = areaDetector.reshape(shape)
            
        for i in range(shape[0]):
            metadata = {}
            for mkey in metadata_lookup:
                field = entry.get(metadata_lookup[mkey], None)
                if field is not None:
                    if mkey in unit_specifiers:
                        field = data_as(field, unit_specifiers[mkey])
                    else:
                        field = field.value
                    if field.dtype.kind == 'f':
                        field = field.astype("float")
                    elif field.dtype.kind == 'i':
                        field = field.astype("int")
                
                    if len(field) == shape[0]:
                        metadata[mkey] = field[i]
                    else:
                        metadata[mkey] = field
                else:
                    metadata[mkey] = field

            metadata['entry'] = entryname
            dataset = SansData(data=areaDetector[i].copy(), metadata=metadata)
            datasets.append(dataset)            

    return datasets
