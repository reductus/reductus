"""
VSANS data loader
================

Load VSANS NeXus file into :mod:`vsansred.vsansdata` data structure.
"""
import io
from zipfile import ZipFile, is_zipfile
from collections import OrderedDict
import datetime
import h5py
import numpy as np

from reductus.dataflow.lib import hzf_readonly_stripped as hzf
from reductus.dataflow.lib import unit
from reductus.dataflow.lib.h5_open import h5_open_zip

from .vsansdata import VSansData, RawVSANSData, _s, _b

metadata_lookup = OrderedDict([
    #"det.dis", "DAS_logs/detectorPosition/softPosition",
    
    #"det.beamx", "instrument/detector/beam_center_x",
    #"det.beamy", "instrument/detector/beam_center_y",
    #"det.pixeloffsetx", "instrument/detector/x_offset",
    #"det.pixelsizex", "instrument/detector/x_pixel_size",
    #"det.pixeloffsety", "instrument/detector/y_offset",
    #"det.pixelsizey", "instrument/detector/y_pixel_size",
    ("run.filename", "DAS_logs/trajectoryData/fileName"),
    ("analysis.intent", "DAS_logs/trajectoryData/intent"),
    ("analysis.filepurpose", "DAS_logs/trajectoryData/filePurpose"),
    ("sample.name", "DAS_logs/sample/name"),
    #("sample.description", "DAS_logs/sample/description"),
    ("sample.labl", "DAS_logs/sample/description"), # compatibility
    ("resolution.lmda" , "instrument/beam/monochromator/wavelength"),
    ("resolution.dlmda", "instrument/beam/monochromator/wavelength_spread"),
    ("m_det.beamx", "DAS_logs/middleRightAreaDetector/beamCenterX"),
    ("m_det.beamy", "DAS_logs/middleRightAreaDetector/beamCenterY"),
    ("m_det.dis", "DAS_logs/geometry/sampleToMiddleRightDetector"),
    ("f_det.beamx", "DAS_logs/frontRightAreaDetector/beamCenterX"),
    ("f_det.beamy", "DAS_logs/frontRightAreaDetector/beamCenterY"),
    ("f_det.dis", "DAS_logs/geometry/sampleToFrontRightDetector"),
    ("m_det_des.dis", "DAS_logs/carriage2Trans/desiredSoftPosition"),
    ("f_det_des.dis", "DAS_logs/carriage1Trans/desiredSoftPosition"),
    ("polarization.front", "DAS_logs/frontPolarization/direction"),
    ("polarization.back", "DAS_logs/backPolarization/direction"),
    ("polarization.backname", "DAS_logs/backPolarization/name"),
    ("polarization.backstart", "DAS_logs/backPolarization/timestamp"),
    ("run.filePrefix", "DAS_logs/trajectoryData/filePrefix"),
    ("run.instFileNum", "DAS_logs/trajectoryData/instFileNum"),
    ("run.pointnum", "DAS_logs/trajectoryData/pointNum"),
    #("run.detcnt", "control/detector_counts"),
    ("run.rtime", "control/count_time"),
    ("run.moncnt", "control/monitor_counts"),
    ("run.atten", "instrument/attenuator/num_atten_dropped"),
    ("analysis.groupid", "DAS_logs/trajectoryData/groupid"),
    ("run.configuration", "DAS_logs/configuration/key"),
    ("sample.thk", "DAS_logs/sample/thickness"),
    ("adam.voltage", "DAS_logs/adam4021/voltage"),
    ("sample.temp", "DAS_logs/temp/primaryNode/average_value"),
    ("sample_des.temp", "DAS_logs/temp/desiredPrimaryNode"),
    ("resolution.ap1", "DAS_logs/geometry/sourceAperture"),
    ("resolution.ap2", "instrument/sample_aperture/size"),
    ("resolution.ap12dis", "instrument/source_aperture/distance"),
    ("resolution.guide", "DAS_logs/guide/guide"),
    ("sample.position", "instrument/sample_aperture/distance"),
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
    ("he3_back.opacity", "DAS_logs/backPolarization/opacityAt1Ang"),
    ("he3_back.te", "DAS_logs/backPolarization/glassTransmission"),
])

he3_metadata_lookup = OrderedDict([
    ("run.filename", "DAS_logs/trajectoryData/fileName"),
    ("sample.labl", "DAS_logs/sample/description"), # compatibility
    ("analysis.intent", "DAS_logs/trajectoryData/intent"),
    ("analysis.filepurpose", "DAS_logs/trajectoryData/filePurpose"),
    ("he3_back.starttime", "DAS_logs/backPolarization/timestamp"),
    ("he3_back.name", "DAS_logs/backPolarization/name"),
    ("he3_back.inbeam", "DAS_logs/backPolarization/inBeam"),
    ("he3_back.opacity", "DAS_logs/backPolarization/opacityAt1Ang"),
    ("he3_back.te", "DAS_logs/backPolarization/glassTransmission"),
    ("he3_back.direction", "DAS_logs/backPolarization/direction"),
    ("run.instrumentScanID", "DAS_logs/trajectory/instrumentScanID"),
    ("run.instFileNum", "DAS_logs/trajectoryData/instFileNum"),
    ("run.rtime", "control/count_time"),
    ("run.moncnt", "control/monitor_counts"),
    ("run.atten", "instrument/attenuator/num_atten_dropped"),
    ("sample.name", "DAS_logs/sample/name"),
    ("resolution.lmda" , "instrument/beam/monochromator/wavelength"),
    ("resolution.dlmda", "instrument/beam/monochromator/wavelength_spread"),
    ("m_det.dis_des", "DAS_logs/carriage2Trans/desiredSoftPosition"),
    ("f_det.dis_des", "DAS_logs/carriage1Trans/desiredSoftPosition"),
    ("start_time","start_time"),
    ("end_time","end_time"),
    ("eventfile", "DAS_logs/areaDetector/eventFileName")
])

unit_specifiers = {
    "det.dis": "cm",
    "det.pixelsizex": "cm",
    "det.pixeloffsetx": "cm",
    "det.pixelsizey": "cm",
    "det.pixeloffsety": "cm",
    "sample.thk": "cm",
    "resolution.ap1": "cm",
    "resolution.ap2": "cm"
}

def process_sourceAperture(field, units):
    import numpy as np
    def handler(v):
        if _s(v) == 'OUT':
            return v
        else:
            return float(v.split()[0])
    handle_values = np.vectorize(handler)
    value = handle_values(field[()])
    units_from = ""
    v0 = field[0].split()
    if _s(value[0]) == 'OUT':
        return value
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

def load_detector(dobj, load_data=True):
    # load detector information from a NeXuS group
    detector = OrderedDict()
    for k in dobj:
        if not load_data and k == 'data':
            continue
        subobj = dobj[k]
        detector[k] = OrderedDict(value=subobj[()], attrs=OrderedDict(_toDictItem(subobj.attrs)))
        if hasattr(subobj, 'shape'):
            detector[k]['attrs']['shape'] = subobj.shape
        if hasattr(subobj, 'dtype'):
            detector[k]['attrs']['dtype'] = subobj.dtype.name
    return detector

def load_metadata(entry, multiplicity=1, i=1, metadata_lookup=metadata_lookup, unit_specifiers=unit_specifiers):
    metadata = OrderedDict()
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
        
            if len(field) == multiplicity:
                metadata[mkey] = field[i]
            else:
                metadata[mkey] = field
        else:
            metadata[mkey] = field
    return metadata

def readVSANSNexuz(input_file, file_obj=None, metadata_lookup=metadata_lookup, load_data=True):
    """
    Load all entries from the NeXus file into sans data sets.
    """
    datasets = []
    file = h5_open_zip(input_file, file_obj)
    for entryname, entry in file.items():
        #areaDetector = entry['data/areaDetector'].value
        #shape = areaDetector.shape
        #if len(shape) < 2 or len(shape) > 3:
        #    raise ValueError("areaDetector data must have dimension 2 or 3")
        #    return
        #if len(shape) == 2:
            # add another dimension at the front
        #    shape = (1,) + shape
        #    areaDetector = areaDetector.reshape(shape)
        
        multiplicity = 1
        for i in range(multiplicity):
            metadata = load_metadata(entry, multiplicity, i, metadata_lookup=metadata_lookup, unit_specifiers=unit_specifiers)
            #print(metadata)
            detector_keys = [n for n in entry['instrument'] if n.startswith('detector_')]
            detectors = dict([(k, load_detector(entry['instrument'][k], load_data=load_data)) for k in detector_keys])
            metadata['entry'] = entryname
            if metadata.get('sample.labl', None) is not None and metadata.get('run.configuration', None) is not None:
                metadata['sample.description'] = _s(metadata["sample.labl"]).replace(_s(metadata["run.configuration"]), "")
            if metadata.get('run.filename', None) is None:
                metadata['run.filename'] = input_file
            dataset = RawVSANSData(metadata=metadata, detectors=detectors)
            datasets.append(dataset)            

    return datasets

def _toDictItem(obj, convert_bytes=False):
    if isinstance(obj, np.integer):
        obj = int(obj)
    elif isinstance(obj, np.floating):
        obj = float(obj)
    elif isinstance(obj, np.ndarray):
        obj = obj.tolist()
    elif isinstance(obj, datetime.datetime):
        obj = [obj.year, obj.month, obj.day, obj.hour, obj.minute, obj.second]
    elif isinstance(obj, list):
        obj = [_toDictItem(a, convert_bytes=convert_bytes) for a in obj]
    elif isinstance(obj, dict):
        obj = OrderedDict([(k, _toDictItem(v, convert_bytes=convert_bytes)) for k, v in obj.items()])
    elif isinstance(obj, bytes) and convert_bytes == True:
        obj = obj.decode()
    return obj
