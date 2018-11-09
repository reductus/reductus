# This program is public domain
# -*- coding: UTF-8 -*-
# Author: Paul Kienzle

import re

import time

from typing import Dict, List, Tuple, Any, Optional, Union

from numpy import inf
import numpy as np


class Device(object):
    # Note: using "private" names for device level properties so that the
    # node names can be used without conflict.  In particular, the
    # experiment virtual device has a description node, which otherwise
    # would overwrite the experiment device description
    _description = None # type: str
    _nodes = None  # type: Dict[str, Dict[str, Any]]
    _type = None # type: str
    _primary = None # type: str

    def get_config(self):
        # type: () -> Dict[str, Any]
        result = {
            "description": self._description,
            "type": self._type,
            "fields": self._nodes,
        }
        if self._primary is not None:
            result["primary"] = self._primary
        return result

    def get_data(self, name):
        # type: () -> Dict[str, Any]
        result = dict((name+'.'+k, getattr(self, k)) for k in self._nodes)
        return result

    def set_data(self, **args):
        for k, v in args.items():
            if k not in self._nodes:
                raise AttributeError("Node %s is not in device"%k)
            setattr(self, k, v)


class Virtual(Device):
    _type = "virtual"
    _data = None  # type: Dict[str, Any]

    def __init__(self, description, primary=None, fields=None, data=None, type="virtual"):
        # type (str, Optional[str], Dict[str, Dict[str, Any]], Dict[str, Any]) -> None
        self._description = description
        self._primary = primary
        self._nodes = fields
        self._data = {} if data is None else data.copy()
        for k in self._nodes:
            self._data.setdefault(k, None)
        self._type = type

    def get_data(self, name):
        return dict((name+"."+k, v) for k, v in self._data.items())

    def set_data(self, **args):
        for k, v in args.items():
            if k not in self._data:
                raise AttributeError("Node %s is not in device"%k)
            self._data[k] = v


class Experiment(Device):
    _type = "data"
    _description = "Experiment properties (may change throught the experiment)"
    _nodes = {
        "dataPath": {
            "label": "experiment data path",
            "mode": "configure",
            "note": "location of the data files",
            "type": "string"
        },
        "description": {
            "label": "experiment description",
            "mode": "configure",
            "note": "Proposal description",
            "type": "string"
        },
        "email": {
            "label": "experiment email",
            "mode": "configure",
            "note": "Research participant emails",
            "type": "string[]"
        },
        "instrument": {
            "label": "experiment instrument",
            "mode": "configure",
            "note": "Instrument used in the experiment",
            "type": "string"
        },
        "localContact": {
            "label": "experiment local contact",
            "mode": "configure",
            "note": "Local contact for the proposal",
            "type": "string"
        },
        "participants": {
            "label": "experiment participants",
            "mode": "configure",
            "note": "Research participants",
            "type": "string"
        },
        "proposalId": {
            "label": "experiment proposal id",
            "mode": "configure",
            "note": "Proposal number",
            "type": "string"
        },
        "publishMode": {
            "label": "experiment publish mode",
            "mode": "configure",
            "note": "Experimental data can be normal, private, or deterred.",
            "type": "string"
        },
        "title": {
            "label": "experiment title",
            "mode": "configure",
            "note": "Proposal title",
            "type": "string"
        }
    }


    dataPath = ""
    description = ""
    email = None # type: List[str]
    instrument = ""
    localContact = ""
    participants = ""
    proposalId = "nonims1"
    publishMode = "NORMAL"
    title = ""

    def __init__(self, instrument):
        # type: (str) -> None
        self.instrument = instrument
        self.email = []


class Trajectory(Device):
    _type = "data"
    _primary = None
    _description = "Scan description"
    _nodes = {
        "command": {
          "label": "trajectory command",
          "mode": "configure",
          "note": "Command used to run the trajectory",
          "type": "string"
        },
        "config": {
          "label": "trajectory config",
          "mode": "configure",
          "note": "Trajectory configuration",
          "type": "string"
        },
        "configFile": {
          "label": "trajectory config file",
          "mode": "configure",
          "note": "Trajectory configuration file name",
          "type": "string"
        },
        "controlVariables": {
          "label": "trajectory control variables",
          "mode": "configure",
          "note": "Devices directly controlled by the trajectory.",
          "type": "string[]"
        },
        "dataStream": {
          "label": "trajectory data stream",
          "mode": "configure",
          "note": "Name of the stream file for the scan",
          "type": "string"
        },
        "defaultXAxisPlotNode": {
          "label": "trajectory default X axis plot node",
          "mode": "configure",
          "note": "The full id of the node which should be used as the X axis of the default plot.",
          "type": "string"
        },
        "defaultYAxisNormalizationChannel": {
          "label": "trajectory default Y axis normalization channel",
          "mode": "configure",
          "note": "If the node specified in \"defaultYAxisNormalizationNode\" is a list, then this channel specifies the index of the list element which should be used to normalize the Y axis of the default plot.  A value of -1 means not specified.",
          "type": "int32"
        },
        "defaultYAxisNormalizationNode": {
          "label": "trajectory default Y axis normalization node",
          "mode": "configure",
          "note": "The full id of the node which should be used to normalize the Y axis of the default plot.  If the node is of list type, then \"defaultYAxisNormalizationChannel\" is additionally used to specify one element of the list.",
          "type": "string"
        },
        "defaultYAxisPlotChannel": {
          "label": "trajectory default Y axis plot channel",
          "mode": "configure",
          "note": "If the node specified in \"defaultYAxisPlotNode\" is a list, then this channel specifies the index of the list element which should be used as the Y axis of the default plot.  A value of -1 means not specified.",
          "type": "int32"
        },
        "defaultYAxisPlotNode": {
            "label": "trajectory default Y axis plot node",
            "mode": "configure",
            "note": "The full id of the node which should be used as the Y axis of the default plot.  If the node is of list type, then \"defaultYAxisPlotChannel\" is additionally used to specify one element of the list.",
            "type": "string"
        },
        "entryID": {
            "label": "trajectory entry ID",
            "mode": "configure",
            "note": "file:entry to store which contains the scan",
            "type": "string"
        },
        "estimatedTime": {
            "error": 0.0,
            "label": "trajectory estimated time",
            "mode": "configure",
            "note": "trajectory estimated time in sec",
            "type": "float32"
        },
        "experimentPointID": {
            "label": "trajectory experiment point ID",
            "mode": "state",
            "note": "Measured point number within the experiment.",
            "type": "int32"
        },
        "experimentScanID": {
            "label": "trajectory experiment scan ID",
            "mode": "configure",
            "note": "Scan number within the experiment.",
            "type": "int32"
        },
        "instrumentScanID": {
            "label": "trajectory instrument scan ID",
            "mode": "configure",
            "note": "Scan number for the instrument.",
            "type": "int32"
        },
        "length": {
            "label": "trajectory length",
            "mode": "configure",
            "note": "Expected number of points in trajectory, or 0 if unknown.",
            "type": "int32"
        },
        "name": {
            "label": "trajectory name",
            "mode": "configure",
            "note": "Name of the scan",
            "type": "string"
        },
        "program": {
            "label": "trajectory program",
            "mode": "configure",
            "note": "Name of the program used to generate the scan",
            "type": "string"
        },
        "scanLength": {
            "label": "trajectory scan length",
            "mode": "configure",
            "note": "Expected number of points in scan, or 0 if unknown.",
            "type": "int32"
        },
        "scannedVariables": {
            "label": "trajectory scanned variables",
            "mode": "configure",
            "note": "Devices modified within a scan.",
            "type": "string[]"
        },
        "trajectoryID": {
            "label": "trajectory trajectory ID",
            "mode": "configure",
            "note": "Trajectory number for the instrument.",
            "type": "int32"
        },
        "version": {
            "label": "trajectory version",
            "mode": "configure",
            "note": "Program version",
            "type": "string"
        }
    }

    command = "inittraj {\"counter.countAgainst\"=\"TIME\"}"
    config = ""
    configFile = "/usr/local/nice/server_data/experiments/22305/trajectories/spec_fixed2.json"
    controlVariables = ["detectorAngle.softPosition", "sampleAngle.softPosition", "slitAperture1.softPosition", "slitAperture2.softPosition", "slitAperture3.softPosition", "slitAperture4.softPosition"]
    dataStream = "/usr/local/nice/server_data/experiments/22305/streams/64975.stream.bz2"
    defaultXAxisPlotNode = ""
    defaultYAxisNormalizationChannel = -1
    defaultYAxisNormalizationNode = ""
    defaultYAxisPlotChannel = -1
    defaultYAxisPlotNode = "counter.liveROI"
    entryID = "Grating225_Air3282:unpolarized"
    estimatedTime = 14349.335000000001
    experimentPointID = 6220
    experimentScanID = 19
    instrumentScanID = 2949
    length = 1001
    name = "spec_fixed2"
    program = "NICE"
    scanLength = 1001
    scannedVariables = ["counter.primaryNode", "counter.timePreset", "detectorAngle.softPosition", "q.z", "sampleAngle.softPosition", "trajectoryData._q", "trajectoryData._w"]
    trajectoryID = 64975
    version = "0"

    def __init__(self):
        pass


class TrajectoryData(Device):
    _type = "data"
    _description = "Variables defined by the trajectory"
    _common_nodes = {
        "alwaysWrite": {
            "label": "trajectory data always write",
            "mode": "configure",
            "note": "Trajectory variable",
            "type": "json",
            "units": ""
        },
        "description": {
            "label": "trajectory data description",
            "mode": "configure",
            "note": "Trajectory variable",
            "type": "json",
            "units": ""
        },
        "editor": {
            "label": "trajectory data editor",
            "mode": "configure",
            "note": "Trajectory variable",
            "type": "json",
            "units": ""
        },
        "entryName": {
            "label": "trajectory data entry name",
            "mode": "configure",
            "note": "Trajectory variable",
            "type": "json",
            "units": ""
        },
        "expPointNum": {
            "label": "trajectory data exp point num",
            "mode": "configure",
            "note": "Trajectory variable",
            "type": "json",
            "units": ""
        },
        "fileGroup": {
            "label": "trajectory data file group",
            "mode": "configure",
            "note": "Trajectory variable",
            "type": "json",
            "units": ""
        },
        "fileName": {
            "label": "trajectory data file name",
            "mode": "configure",
            "note": "Trajectory variable",
            "type": "json",
            "units": ""
        },
        "fileNum": {
            "label": "trajectory data file num",
            "mode": "configure",
            "note": "Trajectory variable",
            "type": "json",
            "units": ""
        },
        "filePrefix": {
            "label": "trajectory data file prefix",
            "mode": "configure",
            "note": "Trajectory variable",
            "type": "json",
            "units": ""
        },
        "instFileNum": {
            "label": "trajectory data inst file num",
            "mode": "configure",
            "note": "Trajectory variable",
            "type": "json",
            "units": ""
        },
        "neverWrite": {
            "label": "trajectory data never write",
            "mode": "configure",
            "note": "Trajectory variable",
            "type": "json",
            "units": ""
        },
        "normalize": {
            "label": "trajectory data normalize",
            "mode": "configure",
            "note": "Trajectory variable",
            "type": "json",
            "units": ""
        },
        "pointNum": {
            "label": "trajectory data point num",
            "mode": "configure",
            "note": "Trajectory variable",
            "type": "json",
            "units": ""
        },
        "skip": {
            "label": "trajectory data skip",
            "mode": "configure",
            "note": "Trajectory variable",
            "type": "json",
            "units": ""
        },
        "trajName": {
            "label": "trajectory data traj name",
            "mode": "configure",
            "note": "Trajectory variable",
            "type": "json",
            "units": ""
        },
        "xAxis": {
            "label": "trajectory data x axis",
            "mode": "configure",
            "note": "Trajectory variable",
            "type": "json",
            "units": ""
        },
        "yAxis": {
            "label": "trajectory data y axis",
            "mode": "configure",
            "note": "Trajectory variable",
            "type": "json",
            "units": ""
        }
    }
    alwaysWrite = ""
    description = "grating225 coated scaffold in air in the cell"
    editor = "'MAGIK/PBR Editor'"
    entryName = "unpolarized"
    expPointNum = 7221
    fileGroup = ""
    fileName = "Grating225_Air3282"
    fileNum = 3282
    filePrefix = "Grating225_Air"
    instFileNum = 64725
    neverWrite = ""
    normalize = ""
    pointNum = 1001
    skip = False
    trajName = "spec_fixed2"
    xAxis = "trajectoryData._q"
    yAxis = "counter.liveROI"


    def __init__(self):
        self._nodes = self._common_nodes.copy()

    def set_nodes(self, config_nodes=None, state_nodes=None):
        # type: (List[str], List[str]) -> None
        if config_nodes is None: config_nodes = []
        if state_nodes is None: state_nodes = []
        nodes = config_nodes + state_nodes

        # Remove attributes that are no longer used
        for k in self._nodes:
            if k not in self._common_nodes and k not in nodes:
                delattr(self, k)

        # Add new attributes with value None
        for k in nodes:
            if not hasattr(self, k):
                setattr(self, k, None)

        # Define the new set of nodes
        self._nodes = self._common_nodes.copy()
        for k in config_nodes:
            self._nodes[k] = {
                "label": "trajectory data " + trajectory_variable_to_text(k),
                "mode": "configure",
                "note": "Trajectory variable",
                "type": "json",
                "units": "",
            }
        for k in state_nodes:
            self._nodes[k] = {
                "label": "trajectory data " + trajectory_variable_to_text(k),
                "mode": "state",
                "note": "Trajectory variable",
                "type": "json",
                "units": "",
            }

class InOut(Device):
    _type = "map"
    _primary = "key"

    key = 0
    map = None  # type: List[Any]

    def __init__(self, label):
        # type: (str, str, Tuple[str, str]) -> None
        self._description = "Convert %s translation position to in/out status" % label
        self._nodes = {
            "key": {
                "label": label,
                "mode": "state",
                "note": "Current map key.",
                "type": "str",
                "units": ""
            },
            "map": {
                "label": label+" map",
                "mode": "configure",
                "note": "Input key to output value map.  On write, entirely replaces existing map.",
                "type": "map<str,float32>"
            }
        }
        self.map = ["IN", 0, "OUT", 1]

class Map(Device):
    _type = "map"
    _primary = "key"

    key = 0
    map = None  # type: List[Any]

    def __init__(self, label, description, types, map=None):
        # type: (str, str, Tuple[str, str]) -> None
        self.map = [] if map is None else map
        self._description = description
        self._nodes = {
            "key": {
                "label": label,
                "mode": "state",
                "note": "Current map key.",
                "type": types[0],
                "units": ""
            },
            "map": {
                "label": label+" map",
                "mode": "configure",
                "note": "Input key to output value map.  On write, entirely replaces existing map.",
                "type": "map<%s,%s>"%(types)
            }
        }


class RateMeter(Device):
    _type = "hardware"
    _primary = None
    _description = "Hardware count rate meter."
    _nodes = {
        "backgroundPollPeriod": {
            "error": 0.001,
            "label": "rate meter background poll period",
            "mode": "configure",
            "note": "The default time period between successive polls of the background-polled hardware properties of this device.  Positive infinity means poll once then never again.  NaN means never poll.",
            "type": "float32",
            "units": "s"
        },
        "detectorRate": {
            "error": 0.001,
            "label": "rate meter detector rate",
            "mode": "log",
            "note": "Proxy for driver property \"detectorRate\".",
            "type": "float32",
            "units": "1/s"
        },
        "monitorRate": {
            "error": 0.001,
            "label": "rate meter monitor rate",
            "mode": "log",
            "note": "Proxy for driver property \"monitorRate\".",
            "type": "float32",
            "units": "1/s"
        }
    }

    backgroundPollPeriod = 120.
    detectorRate = 0.
    monitorRate = 0.

    def __init__(self):
        pass


class Counter(Device):
    _type = "main_counter"
    _primary = None
    _description = "Counter device"
    _nodes = {
        "backgroundPollPeriod": {
            "error": 0.001,
            "label": "counter background poll period",
            "mode": "configure",
            "note": "The default time period between successive polls of the background-polled hardware properties of this device.  Positive infinity means poll once then never again.  NaN means never poll.",
            "type": "float32",
            "units": "s"
        },
        "countAgainst": {
            "label": "counter count against",
            "mode": "state",
            "note": "NICE will terminate the count as soon as it determines that ROICount has reached or exceeded this value.",
            "options": ["TIME", "MONITOR", "ROI", "TIME_MONITOR", "TIME_ROI", "MONITOR_ROI", "TIME_MONITOR_ROI"],
            "type": "string"
        },
        "liveMonitor": {
            "label": "counter live monitor",
            "mode": "counts",
            "note": "How many monitor counts accrued while the counter was active.",
            "type": "int32",
            "units": ""
        },
        "liveROI": {
            "error": 0.001,
            "label": "counter live ROI",
            "mode": "counts",
            "note": "The ROI sum accrued while the counter was active.",
            "type": "float32",
            "units": ""
        },
        "liveTime": {
            "error": 0.001,
            "label": "counter live time",
            "mode": "counts",
            "note": "How long the counter was active.",
            "type": "float32",
            "units": "s"
        },
        "monitorPreset": {
            "label": "counter monitor preset",
            "mode": "state",
            "note": "NICE will terminate the count as soon as it determines that monitorCount has reached or exceeded this value.",
            "type": "int32",
            "units": ""
        },
        "roiAgainst": {
            "label": "counter roi against",
            "mode": "state",
            "note": "If countAgainst includes ROI, logical counter ID should be provided here for roi calculation against that logical counter.",
            "type": "string"
        },
        "roiPreset": {
            "error": 0.001,
            "label": "counter roi preset",
            "mode": "state",
            "note": "NICE will terminate the count as soon as it determines that liveROI has reached or exceeded this value.",
            "type": "float32",
            "units": ""
        },
        "startTime": {
            "label": "counter start time",
            "mode": "counts",
            "note": "Time at which the counter is armed.",
            "type": "time"
        },
        "stopTime": {
            "label": "counter stop time",
            "mode": "counts",
            "note": "Time at which the counter is is disarmed.",
            "type": "time"
        },
        "timePreset": {
            "error": 0.001,
            "label": "counter time preset",
            "mode": "state",
            "note": "NICE will terminate the count as soon as it determines that liveTime has reached or exceeded this value.",
            "type": "float32",
            "units": "s"
        }
    }

    backgroundPollPeriod = inf
    countAgainst = "TIME"
    roiAgainst = "detector"
    monitorPreset = 80000
    roiPreset = 10000.
    timePreset = 10.

    liveMonitor = 0
    liveROI = 0.
    liveTime = 0.
    startTime = 0  # ms since epoch
    stopTime = 0   # ms since epoch

    def __init__(self):
        pass


class Detector(Device):
    _type = "logical_counter"
    _primary = "counts"
    _nodes = {
        "chooseROI": {
            "label": "point detector choose ROI",
            "mode": "configure",
            "note": "Depending upon the selection here, liveROI is displayed (NOTHING - Do not display, RAW_COUNTS - Full array of raw logical counter data, SUM_OF_RAW_COUNTS - Sum of raw logical counter data, ACTUAL_ROI - Sum of raw logical counter data multiplied by the ROI mask)",
            "options": ["NOTHING", "RAW_COUNTS", "SUM_OF_RAW_COUNTS", "ACTUAL_ROI"],
            "type": "string"
        },
        "counts": {
            "label": "point detector",
            "mode": "counts",
            "note": "",
            "shape": [1],
            "type": "int32[]",
            "units": ""
        },
        "dimension": {
            "label": "point detector dimension",
            "mode": "configure",
            "note": "Specifies the dimensions of this counter in an Integer array. e.g. 128x200 counter would be specified as [128,200].",
            "shape": [1],
            "type": "int32[]",
            "units": ""
        },
        "liveROI": {
            "error": 0.001,
            "label": "point detector live ROI",
            "mode": "counts",
            "note": "The ROI sum accrued for the logical counter.",
            "type": "float32",
            "units": ""
        },
        "offset": {
            "label": "point detector offset",
            "mode": "configure",
            "note": "Specifies the region in the detectorArray by the offset from the beginning of the detectorArray.",
            "type": "int32",
            "units": ""
        },
        "roiMask": {
            "error": 0.001,
            "label": "point detector roi mask",
            "mode": "state",
            "note": "An array holding weights for all counters on the instrument used to construct an ROI sum.  This corresponds directly to detectorArray's arrangement.",
            "shape": [1],
            "type": "float32[]",
            "units": ""
        },
        "roiShape": {
            "label": "point detector roi shape",
            "mode": "configure",
            "note": "A geometrical shape that defines the counter ROI mask. Examples: move areaDetector.roishape {name=circle, x=2, y=4, rad=5}, move areaDetector.roishape {name=rect, x1=2, y1=2, x2=3, y2=4}, move areaDetector.roishape {name=ring, x=2, y=4, intrad=3, extrad=5}",
            "type": "map<string,string>"
        },
        "sliceCounts": {
            'label': 'area detector',
            'mode': 'counts',
            'note': '',
            'shape': [1],
            'type': 'int32[]',
            'units': ''},
        "strides": {
            "label": "point detector strides",
            "mode": "configure",
            "note": "",
            "shape": [1],
            "type": "int32[]",
            "units": ""
        }
    }

    # dimension, offset, strides are for converting from detector to pixel id;
    # this will be needed for interpreting event mode data which is stored as
    # a series of times and pixel ids.
    dimension = None  # type: List[int]
    offset = None  # type: int
    strides = None  # type: List[int]
    roiMask = None  # type: List[Union[float, List[float]]]
    roiShape = None  # type: List[str]
    chooseROI = "SUM_OF_RAW_COUNTS"  # type: str
    liveROI = 0.  # type: float
    counts = None  # type: List[Union[int, List[int]]]

    def __init__(self, description, dimension=None, offset=None, strides=None):
        self.dimension = [1] if dimension is None else dimension
        self.offset = 0 if offset is None else offset
        self.strides = (np.cumproduct(np.hstack((1, self.dimension)))[:-1].tolist()
                        if strides is None else strides)
        self.roiMask = np.ones(self.dimension).tolist()
        self.roiShape = ["name", "unknown"]
        self.liveROI = 0.
        self.counts = np.zeros(self.dimension, 'int32').tolist()
        self.sliceCounts = np.zeros(self.dimension, 'int32').tolist()

        self._description = description


class Motor(Device):
    _type = "motor"
    _primary = "softPosition"

    # Default values for each field
    desiredSoftPosition = 0.0
    softPosition = 0.0
    hardPosition = 0.0
    conversion = 1.0
    zero = 0.0
    rawPosition = 0.0
    rawTolerance = 0.01
    softTolerance = 0.01

    negLimitState = False
    posLimitState = False
    rawLowerLimit = -inf
    rawUpperLimit = inf
    softLowerLimit = -inf
    softUpperLimit = inf

    backgroundPollPeriod = 30.0
    backlash = 0.0
    distanceToEngaged = 0.0
    driveCurrentAutoMode = False
    maxRetries = 4
    parity = 1

    def __init__(self, label, description, units=None):
        # type: (str, str, str, Optional[str]) -> None
        self._description = description
        self._nodes = {
            "backgroundPollPeriod": {
              "error": 0.001,
              "label": label+" background poll period",
              "mode": "configure",
              "note": "The default time period between successive polls of the background-polled hardware properties of this device.  Positive infinity means poll once then never again.  NaN means never poll.",
              "type": "float32",
              "units": "s"
            },
            "backlash": {
              "error": 0.001,
              "label": label+" backlash",
              "mode": "configure",
              "note": "The amount of motion in softPosition guaranteed to take out any possible slack and fully engage the motor's load.  This value should be an overestimate of the minimum distance required to take out slack.  If backlash is positive it is only applied to moves that decrease softPosition, and if it is negative it is only applied to moves that increase softPosition.",
              "type": "float32",
              "units": units
            },
            "conversion": {
              "error": 0.001,
              "label": label+" conversion",
              "mode": "configure",
              "note": "Conversion factor in hard units per raw unit.  hardPosition = rawPosition * conversion",
              "type": "float32",
              "units": units
            },
            "desiredSoftPosition": {
              "error": 0.001,
              "label": label,
              "mode": "state",
              "note": label+" desired value",
              "type": "float32",
              "units": units
            },
            "distanceToEngaged": {
              "error": 0.001,
              "label": label+" distance to engaged",
              "mode": "state",
              "note": "The distance the motor must be moved to reach the \"fully engaged position\", in units of softPosition.  Since backlash is intentionally an overestimate the motor may technically be engaged when distanceToEngaged is nonzero, however we can only guarantee it is engaged when distanceToEngaged equals zero.  A successful move ends with distanceToEngaged equal to zero.  NOTE: If distanceToEngaged is nonzero it is not accurate to calculate the load's position by adding distanceToEngaged to the motor's position.  All that can be said reliably is that once distanceToEngaged is reduced to 0, then the load's position can be considered to be at the motor's position.",
              "type": "float32",
              "units": units
            },
            "driveCurrentAutoMode": {
              "label": label+" drive current auto mode",
              "mode": "configure",
              "note": "If set to true then the drive current is automatically turned on before moving the motor and turned off when the move is complete.  If set to false it then driveCurrent can be turned on and off manually.",
              "type": "bool"
            },
            "hardPosition": {
              "error": 0.001,
              "label": label+" hard position",
              "mode": "state",
              "note": "Motor position in instrument coordinates, calculated as hardPosition = rawPosition * conversion.",
              "type": "float32",
              "units": units
            },
            "maxRetries": {
              "label": label+" max retries",
              "mode": "configure",
              "note": "Maximum number of attempts which will be made in order to reach move destination within tolerance.  Taking out backlash counts as a retry attempt, so this setting should be at least 1 if you have a non-zero backlash.",
              "type": "int32",
              "units": ""
            },
            "negLimitState": {
              "label": label+" neg limit state",
              "mode": "state",
              "note": "State of the negative limit  switch during the last move operation.  This is used to determine a possible error after a move finishes.  NOTE: This may represent latched state of the limit switch, if the current state is unreliable.",
              "type": "bool"
            },
            "parity": {
              "label": label+" parity",
              "mode": "configure",
              "note": "If negative, then the positive direction in hardPosition corresponds to the negative direction in softPosition  (value is +1 or -1).",
              "type": "int32",
              "units": ""
            },
            "posLimitState": {
              "label": label+" pos limit state",
              "mode": "state",
              "note": "State of the positive limit  switch during the last move operation.  This is used to determine a possible error after a move finishes.  NOTE: This may represent latched state of the limit switch, if the current state is unreliable.",
              "type": "bool"
            },
            "rawLowerLimit": {
              "error": 0.001,
              "label": label+" raw lower limit",
              "mode": "configure",
              "note": "Minimum position to which the rawPosition can be driven.",
              "type": "float32",
              "units": ""
            },
            "rawPosition": {
              "error": 0.001,
              "label": label+" raw position",
              "mode": "state",
              "note": "Motor position in terms of \"raw units\".  This may be drive/encoder steps, or in the case of a system like VIPER it may be angle in degrees.",
              "type": "float32",
              "units": ""
            },
            "rawTolerance": {
              "error": 0.001,
              "label": label+" raw tolerance",
              "mode": "configure",
              "note": "Acceptable deviation of rawPosition from set value.  If the motor does not finish movement within this range, it will attempt the move again until the configurable number of retries is reached.",
              "type": "float32",
              "units": ""
            },
            "rawUpperLimit": {
              "error": 0.001,
              "label": label+" raw upper limit",
              "mode": "configure",
              "note": "Maximum position to which the rawPosition can be driven.",
              "type": "float32",
              "units": ""
            },
            "softLowerLimit": {
              "error": 0.001,
              "label": label+" soft lower limit",
              "mode": "configure",
              "note": "Minimum position to which the softPosition can be driven.  This value will change automatically if zero or raw limits change.  Setting it causes the corresponding raw limit to change.",
              "type": "float32",
              "units": units
            },
            "softPosition": {
              "error": 0.001,
              "label": label,
              "mode": "state",
              "note": "Motor position in experiment coordinates, calculated as softPosition = parity * (hardPosition - zero).",
              "type": "float32",
              "units": units
            },
            "softTolerance": {
              "error": 0.001,
              "label": label+" soft tolerance",
              "mode": "configure",
              "note": "Acceptable deviation of hard/soft position from set value.  If the motor does not finish movement within this range, it will attempt the move again until the configurable number of retries is reached.  This value is tied to rawTolerance.",
              "type": "float32",
              "units": units
            },
            "softUpperLimit": {
              "error": 0.001,
              "label": label+" soft upper limit",
              "mode": "configure",
              "note": "Maximum position to which the softPosition can be driven.  This value will change automatically if zero or raw limits change.  Setting it causes the corresponding raw limit to change.",
              "type": "float32",
              "units": units
            },
            "zero": {
              "error": 0.001,
              "label": label+" zero",
              "mode": "configure",
              "note": "Value of hardPosition corresponding to a softPosition of zero.  Setting this will update the soft limits.  softPosition = parity * (hardPosition - zero)",
              "type": "float32",
              "units": units
            }
        }



class Instrument(object):
    nexus = None  # type: Dict[str, Any]
    experiment = None  # type: Experiment
    trajectory = None  # type: Trajectory
    trajectoryData = None  # type: TrajectoryData

    experimentPointID = 0
    experimentScanID = 0
    instrumentScanID = 0
    trajectoryID = 0
    last_data = None # type: Dict[str, Any]

    def __init__(self):
        self.last_data = {}
        # derived class should define these
        #self.experiment = Experiment("CANDOR")
        #self.trajectory = Trajectory()
        #self.trajectoryData = TrajectoryData()

    def devices(self):
        # type: () -> Dict[str, Device]
        result = dict((k, getattr(self, k)) for k in dir(self))
        result = dict((k, v) for k, v in result.items() if isinstance(v, Device))

        # python 3.7 local capture syntax
        #result = dict((k, v) for k in dir(self)
        #              if isinstance(v := getattr(self, k), Device))
        return result

    def device_config(self):
        # type: () -> Dict[str, Any]
        devices = dict((k, v.get_config()) for k, v in self.devices().items())
        return devices

    def get_data(self):
        # type: () -> Dict[str, Any]
        result = {}
        for k, v in self.devices().items():
            result.update(v.get_data(k))
        return result

    def get_delta(self):
        # type: () -> Dict[str, Any]
        """
        Return a dictionary of changed nodes since the last time delta was
        called. The delta is reset on :meth:`config_record`.
        """
        data = self.get_data()
        result = dict((k, v) for k, v in data.items()
                      if v != self.last_data.get(k, None))
        self.last_data = data
        return result

    def move(self, **args):
        # type: (Any...) -> None
        for k, v in args.items():
            if isinstance(v, np.ndarray):
                v = v.tolist()
            device_id, node_id = k.split('_', 1)
            device = getattr(self, device_id)  # type: Device
            device.set_data(**{node_id: v})

    def config_record(self, timestamp):
        # type: (int) -> Dict[str, Any]
        self.last_data = self.get_data()
        self.trajectoryID += 1
        self.trajectory.trajectoryID = self.trajectoryID
        result = {
            'command': "Configure",
            'devices': self.device_config(),
            'data': self.last_data,
            #'errors': {}
            'experiment': self.experiment.proposalId,
            'nexus': self.nexus,
            'time': timestamp,
            'version': "1.0",
        }
        return result

    def open_record(self, timestamp):
        # type: (int) -> Dict[str, Any]
        result = {
            'command': "Open",
            'data': self.get_delta(),
            'scan': self.trajectory.entryID,
            'time': timestamp,
        }
        return result

    def state_record(self, timestamp):
        # type: (int) -> Dict[str, Any]
        result = {
            'command': "State",
            'data': self.get_delta(),
            'restart': False,
            'scan': self.trajectory.entryID,
            'time': timestamp,
        }
        return result

    def count_record(self, timestamp):
        # type: (int) -> Dict[str, Any]
        result = {
            'command': "Counts",
            'data': self.get_delta(),
            'scan': self.trajectory.entryID,
            'time': timestamp,
        }
        return result

    def log_record(self, timestamp):
        # type: (int) -> Dict[str, Any]
        result = {
            'command': "Log",
            'data': self.get_delta(),
            'time': timestamp,
        }
        return result

    def close_record(self, timestamp):
        # type: (int) -> Dict[str, Any]
        result = {
            'command': "Close",
            'scan': self.trajectory.entryID,
            'time': timestamp,
        }
        return result

    def end_record(self, timestamp):
        # type: (int) -> Dict[str, Any]
        result = {
            'command': "End",
            'time': timestamp,
        }
        return result


def trajectory_variable_to_text(identifier):
    # type: (str) -> str
    if identifier.startswith('_'):
        identifier = identifier[1:]
    if "_" in identifier:
        return " ".join(identifier.split('_'))
    else:
        return " ".join(uncapitalize(s) for s in camel_case_split(identifier))

def camel_case_split(s):
    # type: (str) -> List[str]
    matches = re.finditer('.+?(?:(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z0-9])|$)', s)
    return [m.group(0) for m in matches]

def uncapitalize(s):
    # type: (str) -> str
    if all(a.isupper() for a in s):
        return s
    else:
        return s.lower()