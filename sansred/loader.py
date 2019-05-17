"""
SANS data loader
================

Load SANS NeXus file into :mod:`sansred.sansdata` data structure.
"""
import io
from zipfile import ZipFile, is_zipfile
import h5py

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
    "run.experimentPointID": "DAS_logs/trajectory/experimentPointID",
    "run.pointnum": "DAS_logs/trajectoryData/pointNum",
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
    "electromagnet_lrm.field":"DAS_logs/electromagnet_lrm/field",
    "mag.value":"DAS_logs/mag/value",
    "acamplitude.voltage":  "DAS_logs/acAmplitude/voltage",
    "waveformgenerator.frequency":  "DAS_logs/waveformGenerator/frequency",
    "rfflipperpowersupply.voltage":  "DAS_logs/RFFlipperPowerSupply/actualVoltage/average_value",
    "rfflipperpowersupply.frequency":  "DAS_logs/RFFlipperPowerSupply/frequency",
    "huberRotation.softPosition":  "DAS_logs/huberRotation/softPosition",
    "start_time":"start_time",
    "end_time":"end_time",
    "eventfile": "DAS_logs/areaDetector/eventFileName"
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
        value = converter(field.value, units)
        return value

def h5_open_zip(filename, file_obj=None, **kw):
    """
    Open a NeXus file, even if it is in a zip file,
    or if it is a NeXus-zip file.

    If the filename ends in '.zip', it will be unzipped to a temporary
    directory before opening and deleted on :func:`closezip`.  If opened
    for writing, then the file will be created in a temporary directory,
    then zipped and deleted on :func:`closezip`.

    If it is a zipfile but doesn't end in '.zip', it is assumed
    to be a NeXus-zip file and is opened with that library.

    Arguments are the same as for :func:`open`.
    """
    if file_obj is None:
        file_obj = io.BytesIO(open(filename, mode='rb', buffering=-1).read())
    is_zip = is_zipfile(file_obj) # is_zipfile(file_obj) doens't work in py2.6
    if is_zip and '.attrs' in ZipFile(file_obj).namelist():
        # then it's a nexus-zip file, rather than
        # a zipped hdf5 nexus file
        f = hzf.File(filename, file_obj)
        f.delete_on_close = False
        f.zip_on_close = False
    else:
        zip_on_close = None
        if is_zip:
            zf = ZipFile(file_obj)
            members = zf.namelist()
            assert len(members) == 1
            file_obj = io.BytesIO(zf.read(members[0]))
            filename = os.path.join(path, members[0])
        
        f = h5py.File(file_obj, **kw)
        f.delete_on_close = is_zip
        f.zip_on_close = zip_on_close
    return f

def readSANSNexuz(input_file, file_obj=None):
    """
    Load all entries from the NeXus file into sans data sets.
    """
    datasets = []
    file = h5_open_zip(input_file, file_obj)
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
