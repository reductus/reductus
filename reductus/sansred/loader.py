"""
SANS data loader
================

Load SANS NeXus file into :mod:`sansred.sansdata` data structure.
"""
import io
from zipfile import ZipFile, is_zipfile
from collections import OrderedDict
import h5py

from reductus.dataflow.lib import hzf_readonly_stripped as hzf
from reductus.dataflow.lib import unit
from reductus.dataflow.lib.h5_open import h5_open_zip

from reductus.vsansred.loader import load_detector, load_metadata
from reductus.vsansred.steps import _s, _b

from .sansdata import SansData, RawSANSData

metadata_lookup = OrderedDict([
    ("run.filename", "DAS_logs/trajectoryData/fileName"),
    ("analysis.intent", "DAS_logs/trajectoryData/intent"),
    ("analysis.filepurpose", "DAS_logs/trajectoryData/filePurpose"),
    ("det.des_dis", "DAS_logs/detectorPosition/desiredSoftPosition"),
    ("det.dis", "DAS_logs/detectorPosition/softPosition"),
    ("run.guide", "DAS_logs/guide/guide"),
    ("sample.description", "DAS_logs/sample/description"), # overwritten on load
    ("sample.labl", "DAS_logs/sample/description"), # compatibility
    ("resolution.lmda", "instrument/monochromator/wavelength"),
    ("resolution.dlmda", "instrument/monochromator/wavelength_error"),
    ("det.beamx", "instrument/detector/beam_center_x"),
    ("det.beamy", "instrument/detector/beam_center_y"),
    ("det.bstop", "DAS_logs/beamStop/size"),
    #("det.pixeloffsetx", "instrument/detector/x_offset"), # this is useless
    ("det.pixelsizex", "instrument/detector/x_pixel_size"),
    #("det.pixeloffsety", "instrument/detector/y_offset"), # this is also useless
    ("det.pixelsizey", "instrument/detector/y_pixel_size"),
    ("sample.name", "DAS_logs/sample/name"),
    ("polarization.front", "DAS_logs/frontPolarization/direction"),
    ("polarization.back", "DAS_logs/backPolarization/direction"),
    ("polarization.backname", "DAS_logs/backPolarization/name"),
    ("run.filePrefix", "DAS_logs/trajectoryData/filePrefix"),
    ("run.instFileNum", "DAS_logs/trajectoryData/instFileNum"),
    ("run.experimentScanID", "DAS_logs/trajectory/experimentScanID"),
    ("run.instrumentScanID", "DAS_logs/trajectory/instrumentScanID"),
    ("run.experimentPointID", "DAS_logs/trajectory/experimentPointID"),
    ("run.pointnum", "DAS_logs/trajectoryData/pointNum"),
    ("run.detcnt", "control/detector_counts"),
    ("run.rtime", "control/count_time"),
    ("run.moncnt", "control/monitor_counts"),
    ("run.atten", "DAS_logs/counter/actualAttenuatorsDropped"),
    ("analysis.groupid", "DAS_logs/trajectoryData/groupid"),
    ("run.configuration", "DAS_logs/configuration/key"),
    ("sample.thk", "DAS_logs/sample/thickness"),
    ("adam.voltage", "DAS_logs/adam4021/voltage"),
    ("sample.temp", "DAS_logs/temp/primaryNode/average_value"),
    ("resolution.ap1", "DAS_logs/geometry/sourceAperture"),
    ("resolution.ap2", "DAS_logs/geometry/externalSampleAperture"),
    ("resolution.ap2Off", "instrument/sample_aperture/distance"),
    ("resolution.ap12dis", "DAS_logs/geometry/sourceApertureToSampleAperture"),
    ("sample.position", "DAS_logs/geometry/samplePositionOffset"),
    ("electromagnet_lrm.field","DAS_logs/electromagnet_lrm/field"),
    ("mag.value","DAS_logs/mag/value"),
    ("acamplitude.voltage",  "DAS_logs/acAmplitude/voltage"),
    ("waveformgenerator.frequency",  "DAS_logs/waveformGenerator/frequency"),
    ("rfflipperpowersupply.voltage",  "DAS_logs/RFFlipperPowerSupply/actualVoltage/average_value"),
    ("rfflipperpowersupply.frequency",  "DAS_logs/RFFlipperPowerSupply/frequency"),
    ("huberRotation.softPosition",  "DAS_logs/huberRotation/softPosition"),
    ("start_time","start_time"),
    ("end_time","end_time"),
    ("eventfile", "DAS_logs/areaDetector/eventFileName"),
])

unit_specifiers = {
    "det.dis": "cm",
    "det.pixelsizex": "cm",
    "det.pixeloffsetx": "cm",
    "det.pixelsizey": "cm",
    "det.pixeloffsety": "cm",
    "sample.thk": "cm",
    "resolution.ap1": "cm",
    "resolution.ap2": "cm",
    "resolution.ap2Off": "cm",
}

def process_sourceAperture(field, units):
    import numpy as np
    def handler(v):
        return float(v.split()[0])
    handle_values = np.vectorize(handler)
    value = handle_values(field[()])
    units_from = ""
    v0 = field[0].split()
    if len(v0) > 1:
        units_from = v0[1]
    if type(units_from) == bytes:
        units_from = units_from.decode('utf-8')
    converter = unit.Converter(units_from)
    return converter(value, units)    

def data_as(field, units):
    """
    Return value of field in the desired units.
    """
    if field.name.split('/')[-1] == 'sourceAperture':
        return process_sourceAperture(field, units)
    else:
        units_in = field.attrs.get('units', '')
        if type(units_in) == bytes:
            units_in = units_in.decode('utf-8')
        converter = unit.Converter(units_in)
        value = converter(field[()], units)
        return value

def readSANSNexuz(input_file, file_obj=None, metadata_lookup=metadata_lookup):
    """
    Load all entries from the NeXus file into sans data sets.
    """
    datasets = []
    file = h5_open_zip(input_file, file_obj)
    for entryname, entry in file.items():        
        multiplicity = 1
        for i in range(multiplicity):
            metadata = load_metadata(entry, multiplicity, i, metadata_lookup=metadata_lookup, unit_specifiers=unit_specifiers)
            #print(metadata)
            detector_keys = ['detector']
            detectors = dict([(k, load_detector(entry['instrument'][k])) for k in detector_keys])
            metadata['entry'] = entryname
            # hack to remove configuration from sample label (it is still stored in run.configuration)
            metadata['sample.description'] = _s(metadata["sample.labl"]).replace(_s(metadata["run.configuration"]), "")
            dataset = RawSANSData(metadata=metadata, detectors=detectors)
            datasets.append(dataset)            

    return datasets

def readSANSNexuz_old(input_file, file_obj=None):
    """
    Load all entries from the NeXus file into sans data sets.
    """
    datasets = []
    file = h5_open_zip(input_file, file_obj)
    for entryname, entry in file.items():
        areaDetector = entry['data/areaDetector'][()]
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
                        field = field[()]
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
