from reflred import hzf_readonly_stripped as hzf
from sansdata import SansData

metadata_lookup = {
    "det.dis": "detectorPosition/softPosition",
    "resolution.lmda" : "wavelength/wavelength",
    "det.beamx": "areaDetector/beamCenterX",
    "det.beamy": "areaDetector/beamCenterY",
    "analysis.intent": "trajectoryData/intent",
    "analysis.filepurpose": "trajectoryData/filepurpose",
    "sample.name": "sample/name",
    "sample.description": "sample/description",
    "sample.labl": "sample/description", # compatibility
    "polarization.front": "frontPolarization/direction",
    "polarization.back": "backPolarization/direction",
    "run.filename": "trajectoryData/fileName"
}

def readSANSNexuz(input_file, file_obj=None):
    datasets = []
    file = hzf.File(input_file, file_obj)
    for entryname, entry in file.items():
        metadata = {}
        reals = {}
        das = entry['DAS_logs']
    
        detdata = entry['data/areaDetector'].value.reshape(128,128)

        for mkey in metadata_lookup:
            field = das.get(metadata_lookup[mkey], None)
            if field is not None:
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
        
        dataset = SansData(data = detdata, metadata = metadata)
        datasets.append(dataset)
    
    return datasets
    
