"""
USANS data loader
================

Load USANS NeXus file into :mod:`usansred.usansdata` data structure.
"""
import io
from collections import OrderedDict
import h5py

from reductus.dataflow.lib import hzf_readonly_stripped as hzf
from reductus.dataflow.lib import unit
from reductus.dataflow.lib.h5_open import h5_open_zip
from reductus.dataflow.lib.strings import _s, _b

from .usansdata import RawData, USansData

metadata_lookup = OrderedDict([
    ("run.filename", "DAS_logs/trajectoryData/fileName"),
    ("analysis.intent", "DAS_logs/trajectoryData/intent"),
    ("sample.name", "DAS_logs/sample/name"),
    ("run.filePrefix", "DAS_logs/trajectoryData/filePrefix"),
    ("run.instFileNum", "DAS_logs/trajectoryData/instFileNum"),
    ("start_time","start_time"),
    ("end_time","end_time"),
    ("eventfile", "DAS_logs/areaDetector/eventFileName"),
])

def readUSANSNexus(input_file, file_obj=None, metadata_lookup=metadata_lookup, det_deadtime=0.0, trans_deadtime=0.0):
    """
    Load all entries from the NeXus file into sans data sets.
    """
    datasets = []
    file = h5_open_zip(input_file, file_obj)
    for entryname, entry in file.items():
        metadata = OrderedDict([
            ("run.filename", _s(entry["DAS_logs/trajectoryData/fileName"][0])),
            ("analysis.intent", _s(entry["DAS_logs/trajectoryData/intent"][0])),
            ("sample.name", _s(entry["DAS_logs/sample/name"][0])),
            ("run.filePrefix", _s(entry["DAS_logs/trajectoryData/filePrefix"][0])),
            ("run.instFileNum", int(entry["DAS_logs/trajectoryData/instFileNum"][0])),
            ("start_time", _s(entry["start_time"][0])),
            ("end_time",_s(entry["end_time"][0])),
            ("entry", _s(entryname)),
            ("dQv", 0.117), # constant of the instrument.  Should it be in the nexus def?
        ])

        counts = entry['DAS_logs/linearDetector/counts'][()]
        countTime = entry['DAS_logs/counter/liveTime'][()]
        trans_counts = entry['DAS_logs/transDetector/counts'][()]
        detCts = (counts / (1.0 - (counts*det_deadtime/countTime[:,None]))).sum(axis=1)
        transCts = (trans_counts / (1.0 - (trans_counts*trans_deadtime/countTime[:,None]))).sum(axis=1)
        monCts = entry['DAS_logs/counter/liveMonitor'][()]
        Q = entry['DAS_logs/analyzerRotation/softPosition'][()]

        dataset = USansData(metadata=metadata, countTime=countTime, detCts=detCts, transCts=transCts, monCts=monCts, Q=Q) 
        datasets.append(dataset)   
    return datasets
