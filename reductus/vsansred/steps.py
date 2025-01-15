from posixpath import basename, join
from copy import copy, deepcopy
from io import BytesIO
import sys
import numpy as np

from reductus.dataflow.lib.uncertainty import Uncertainty

# Action names
__all__ = [] # type: List[str]

# Action methods
ALL_ACTIONS = [] # type: List[Callable[Any, Any]]

IS_PY3 = sys.version_info[0] >= 3

def _b(s):
    if IS_PY3:
        return s.encode('utf-8')
    else:
        return s

def _s(b):
    if IS_PY3:
        return b.decode('utf-8') if hasattr(b, 'decode') else b
    else:
        return b

def cache(action):
    """
    Decorator which adds the *cached* attribute to the function.

    Use *@cache* to force caching to always occur (for example, when
    the function references remote resources, vastly reduces memory, or is
    expensive to compute.  Use *@nocache* when debugging a function
    so that it will be recomputed each time regardless of whether or not it
    is seen again.
    """
    action.cached = True
    return action

def nocache(action):
    """
    Decorator which adds the *cached* attribute to the function.

    Use *@cache* to force caching to always occur (for example, when
    the function references remote resources, vastly reduces memory, or is
    expensive to compute.  Use *@nocache* when debugging a function
    so that it will be recomputed each time regardless of whether or not it
    is seen again.
    """
    action.cached = False
    return action

def module(action):
    """
    Decorator which records the action in *ALL_ACTIONS*.

    This just collects the action, it does not otherwise modify it.
    """
    ALL_ACTIONS.append(action)
    __all__.append(action.__name__)

    # Sort modules alphabetically
    ALL_ACTIONS.sort(key=lambda action: action.__name__)
    __all__.sort()

    # This is a decorator, so return the original function
    return action

def hidden(action):
    """
    Decorator which indicates method is not to be shown in GUI
    """
    action.visible = False
    return action

@cache
@module
@hidden
def _LoadVSANS(filelist=None, check_timestamps=True):
    """
    loads a data file into a VSansData obj and returns that.

    **Inputs**

    filelist (fileinfo[]): Files to open.
    
    check_timestamps (bool): verify that timestamps on file match request

    **Returns**

    output (raw[]): all the entries loaded.

    | 2018-04-29 Brian Maranville
    | 2020-10-01 Brian Maranville adding fileinfo to metadata
    """
    from reductus.dataflow.fetch import url_get
    from .loader import readVSANSNexuz
    if filelist is None:
        filelist = []
    data = []
    for fileinfo in filelist:
        path, mtime, entries = fileinfo['path'], fileinfo.get('mtime', None), fileinfo.get('entries', None)
        name = basename(path)
        fid = BytesIO(url_get(fileinfo, mtime_check=check_timestamps))
        entries = readVSANSNexuz(name, fid)
        for entry in entries:
            if fileinfo['path'].endswith("DIV.h5"):
                print('div file...')
                entry.metadata['analysis.filepurpose'] = "Sensitivity"
                entry.metadata['analysis.intent'] = "DIV"
                entry.metadata['sample.description'] = entry.metadata['run.filename']
            fi = fileinfo.copy()
            fi['entries'] = [entry.metadata['entry']]
            entry.metadata['fileinfo'] = fi
        data.extend(entries)

    return data

@nocache
@module
def LoadVSANS(filelist=None, check_timestamps=True, load_data=True):
    """
    loads a data file into a VSansData obj and returns that. (uses cached values)

    **Inputs**

    filelist (fileinfo[]): Files to open.
    
    check_timestamps (bool): verify that timestamps on file match request

    load_data (bool): include the data in the load

    **Returns**

    output (raw[]): all the entries loaded.

    | 2018-10-30 Brian Maranville
    | 2020-09-30 Brian Maranville adding option to not load data
    """

    from reductus.dataflow.calc import process_template
    from reductus.dataflow.core import Template

    template_def = {
        "name": "loader_template",
        "description": "VSANS remote loader",
        "modules": [
        {"module": "ncnr.vsans._LoadVSANS", "version": "0.1", "config": {}}
        ],
        "wires": [],
        "instrument": "ncnr.vsans",
        "version": "0.0"
    }

    template = Template(**template_def)
    output = []
    for fi in filelist:
        config = {"0": {"filelist": [fi], "check_timestamps": check_timestamps, "load_data": load_data}}
        nodenum = 0
        terminal_id = "output"
        retval = process_template(template, config, target=(nodenum, terminal_id))
        output.extend(retval.values)

    return output


def addSimple(data):
    """
    Naive addition of counts and monitor from different datasets,
    assuming all datasets were taken under identical conditions
    (except for count time)

    Just adds together count time, counts and monitor.

    Use metadata from first dataset for output.

    **Inputs**

    data (realspace[]): measurements to be added together

    **Returns**

    sum (realspace): sum of inputs

    2019-09-22  Brian Maranville
    """

    output = data[0].copy()
    for d in data[1:]:
        for detname in output.detectors:
            if detname in d.detectors:
                output.detectors[detname]['data'] += d.detectors[detname]['data']
        output.metadata['run.moncnt'] += d.metadata['run.moncnt']
        output.metadata['run.rtime'] += d.metadata['run.rtime']
        #output.metadata['run.detcnt'] += d.metadata['run.detcnt']
    return output

@cache
@module
def LoadVSANSHe3(filelist=None, check_timestamps=True):
    """
    loads a data file into a VSansData obj and returns that.

    **Inputs**

    filelist (fileinfo[]): Files to open.
    
    check_timestamps (bool): verify that timestamps on file match request

    **Returns**

    output (raw[]): all the entries loaded.

    2018-04-29 Brian Maranville
    """
    from reductus.dataflow.fetch import url_get
    from .loader import readVSANSNexuz, he3_metadata_lookup
    if filelist is None:
        filelist = []
    data = []
    for fileinfo in filelist:
        path, mtime, entries = fileinfo['path'], fileinfo.get('mtime', None), fileinfo.get('entries', None)
        name = basename(path)
        fid = BytesIO(url_get(fileinfo, mtime_check=check_timestamps))
        entries = readVSANSNexuz(name, fid, metadata_lookup=he3_metadata_lookup)
        data.extend(entries)

    return data


@nocache
@module
def LoadVSANSHe3Parallel(filelist=None, check_timestamps=True):
    """
    loads a data file into a VSansData obj and returns that.

    **Inputs**

    filelist (fileinfo[]): Files to open.
    
    check_timestamps (bool): verify that timestamps on file match request

    **Returns**

    output (raw[]): all the entries loaded.

    | 2018-04-29 Brian Maranville
    | 2019-11-20 Brian Maranville changed metadata list
    """

    from reductus.dataflow.calc import process_template
    from reductus.dataflow.core import Template

    template_def = {
        "name": "loader_template",
        "description": "VSANS remote loader",
        "modules": [
        {"module": "ncnr.vsans.LoadVSANSHe3", "version": "0.1", "config": {}}
        ],
        "wires": [],
        "instrument": "ncnr.vsans",
        "version": "0.0"
    }

    template = Template(**template_def)
    output = []
    for fi in filelist:
        #config = {"0": {"filelist": [{"path": fi["path"], "source": fi["source"], "mtime": fi["mtime"]}]}}
        config = {"0": {"filelist": [fi]}}
        nodenum = 0
        terminal_id = "output"
        retval = process_template(template, config, target=(nodenum, terminal_id))
        output.extend(retval.values)

    return output

@nocache
@module
def LoadVSANSDIV(filelist=None, check_timestamps=True):
    """
    loads a DIV file into a VSansData obj and returns that.

    **Inputs**

    filelist (fileinfo[]): Files to open.
    
    check_timestamps (bool): verify that timestamps on file match request

    **Returns**

    output (realspace[]): all the entries loaded.

    2019-10-30 Brian Maranville
    """
    from reductus.dataflow.fetch import url_get
    from .loader import readVSANSNexuz
    

    if filelist is None:
        filelist = []

    data = []
    for fileinfo in filelist:
        path, mtime, entries = fileinfo['path'], fileinfo.get('mtime', None), fileinfo.get('entries', None)
        name = basename(path)
        fid = BytesIO(url_get(fileinfo, mtime_check=check_timestamps))
        entries = readVSANSNexuz(name, fid) # metadata_lookup=div_metadata_lookup)
        for entry in entries:
            div_entries = _loadDivData(entry)
            data.extend(div_entries)

    return data

def _loadDivData(entry):
    from collections import OrderedDict
    from .vsansdata import VSansDataRealSpace, short_detectors

    div_entries = []

    for sn in short_detectors:
        new_detectors = OrderedDict()
        new_metadata = deepcopy(entry.metadata)
        detname = 'detector_{short_name}'.format(short_name=sn)
        if not detname in entry.detectors:
            continue
        det = deepcopy(entry.detectors[detname])

        data = det['data']['value']
        if 'linear_data_error' in det and 'value' in det['linear_data_error']:
            data_variance = np.sqrt(det['linear_data_error']['value'])
        else:
            data_variance = data
        udata = Uncertainty(data, data_variance)
        det['data'] = udata
        det['norm'] = 1.0
        xDim, yDim = data.shape[:2]
        det['X'] = np.arange(xDim)
        det['Y'] = np.arange(yDim)
        det['dX'] = det['dY'] = 1

        new_metadata['sample.labl'] = detname
        new_detectors[detname] = det
        div_entries.append(VSansDataRealSpace(metadata=new_metadata, detectors=new_detectors))
    
    return div_entries

@module
def SortDataAutomatic(data):
    """
    Sorting with algorithms to categorize all files and auto-associate

    **Inputs**

    data (raw[]): data files to sort, typically all of them

    **Returns**

    sorting_info (params): associations and metadata, by filenumber

    2020-05-06 Brian Maranville
    """

    from .categorize import SortDataAutomatic
    from .vsansdata import Parameters

    return Parameters(SortDataAutomatic(data))

@cache
@module
def He3_transmission(he3data, trans_panel="auto"):
    """
    Calculate transmissions

    **Inputs**

    he3data (raw[]): datafiles with he3 transmissions

    trans_panel (opt:auto|MB|MT|ML|MR|FT|FB|FL|FR): panel to use for transmissions

    **Returns**

    annotated (raw[]): datafiles grouped by cell

    transmissions (v1d[]): 1d transmissions per cell

    atomic_pols (v1d[]): 1d atomic polarizations per cell

    mappings (params[]): cell parameters

    | 2018-05-01 Brian Maranville
    | 2020-07-30 Brian Maranville update cell name
    | 2020-10-01 Brian Maranville add atomic_pol

    """
    from .vsansdata import short_detectors, Parameters, VSans1dData,  _toDictItem
    import dateutil.parser
    import datetime
    from collections import OrderedDict

    he3data.sort(key=lambda d:  d.metadata.get("run.instrumentScanID", None))

    BlockedBeams = OrderedDict()
    for d in he3data:
        filename = d.metadata.get("run.filename", "unknown_file")
        if _s(d.metadata.get('analysis.intent', '')).lower().startswith('bl'):
            m_det_dis_desired = int(d.metadata.get("m_det.dis_des", 0))
            f_det_dis_desired = int(d.metadata.get("f_det.dis_des", 0))
            num_attenuators = int(d.metadata.get("run.atten", 0))
            #t_key = "{:d}_{:d}_{:d}".format(m_det_dis_desired, f_det_dis_desired, num_attenuators)
            count_time = d.metadata['run.rtime']
            if count_time == 0: count_time = 1
            trans_counts = get_transmission_sum(d.detectors, panel_name=trans_panel)
            BlockedBeams[(m_det_dis_desired, f_det_dis_desired, num_attenuators)] = OrderedDict([
                ("filename", filename),
                ("counts_per_second", trans_counts / count_time),
                ("middle_detector_distance", m_det_dis_desired),
                ("front_detector_distance", f_det_dis_desired),
                ("attenuators", num_attenuators),
            ])

    mappings = OrderedDict()
    previous_transmission = {}
    previous_scan_id = 0
    for d in he3data:
        scan_id = d.metadata.get("run.instrumentScanID", 0)
        cellstart = d.metadata.get("he3_back.starttime", None)
        if cellstart is None:
            cellstart = 0
        cellstart = int(cellstart) # coerce strings
        cellstartstr = "{ts:d}".format(ts=cellstart)
        tend = dateutil.parser.parse(d.metadata.get("end_time", "1969")).timestamp()
        count_time =  d.metadata['run.rtime']
        monitor_counts = d.metadata['run.moncnt']
        detector_counts = get_transmission_sum(d.detectors, panel_name=trans_panel)
        filename = d.metadata.get("run.filename", "unknown_file")
        m_det_dis_desired = d.metadata.get("m_det.dis_des", 0)
        f_det_dis_desired = d.metadata.get("f_det.dis_des", 0)
        num_attenuators = d.metadata.get("run.atten", 0)
        middle_timestamp = (tend - (count_time / 2.0)) # in seconds
        opacity = d.metadata.get("he3_back.opacity", 0.0)
        wavelength = d.metadata.get("resolution.lmda")
        Te = d.metadata.get("he3_back.te", 1.0)
        Mu = opacity*wavelength
        mappings.setdefault(cellstartstr, {
            "Insert_time": cellstart,
            "Insert_datetime": datetime.datetime.fromtimestamp(cellstart/1000).ctime(),
            "Cell_name": _s(d.metadata.get("he3_back.name", "unknown")),
            "Te": Te,
            "Mu": Mu,
            "P0": None,
            "Gamma": None,
            "Transmissions": []
        })

        # assume that He3 OUT is measured before He3 IN
        mapping_trans = mappings[cellstartstr]["Transmissions"]
        t_key = (m_det_dis_desired, f_det_dis_desired, num_attenuators)
        direction = _s(d.metadata.get("he3_back.direction", "UNPOLARIZED"))
        if direction != "UNPOLARIZED" and (scan_id - previous_scan_id) == 1:
            p = previous_transmission
            #print('previous transmission: ', p)
            #print(p.get("CellTimeIdentifier", None), tstart,
            #        p.get("m_det_dis_desired", None),  m_det_dis_desired, 
            #        p.get("f_det_dis_desired", None), f_det_dis_desired,
            #        p.get("num_attenuators", None),  num_attenuators)
            if p.get("CellTimeIdentifier", None) == cellstart and \
                    p.get("m_det_dis_desired", None) == m_det_dis_desired and \
                    p.get("f_det_dis_desired", None) == f_det_dis_desired and \
                    p.get("num_attenuators", None) == num_attenuators:
                p["HE3_IN_file"] = filename
                p["HE3_IN_counts"] = detector_counts
                p["HE3_IN_count_time"] = count_time
                p["HE3_IN_mon"] = monitor_counts
                p["HE3_IN_timestamp"] = middle_timestamp

                if t_key in BlockedBeams:
                    bb = BlockedBeams[t_key]
                    BlockBeamRate = bb['counts_per_second']
                    BlockBeam_filename = bb['filename']
                else:
                    BlockBeamRate = 0
                    BlockBeam_filename = "missing"
                
                p["BlockedBeam_filename"] = BlockBeam_filename
                HE3_transmission_IN = (p["HE3_IN_counts"] - BlockBeamRate*p["HE3_IN_count_time"])/p["HE3_IN_mon"]
                HE3_transmission_OUT = (p["HE3_OUT_counts"] - BlockBeamRate*p["HE3_OUT_count_time"])/p["HE3_OUT_mon"]
                HE3_transmission = HE3_transmission_IN / HE3_transmission_OUT
                p['transmission'] = HE3_transmission
                p['atomic_pol'] = np.arccosh(HE3_transmission / (Te * np.exp(-Mu))) / Mu
                mapping_trans.append(deepcopy(p))
        else:
            previous_transmission = {
                "CellTimeIdentifier": cellstart,
                "HE3_OUT_file": filename,
                "HE3_OUT_counts": detector_counts,
                "HE3_OUT_count_time": count_time,
                "HE3_OUT_mon": monitor_counts,
                "m_det_dis_desired": m_det_dis_desired,
                "f_det_dis_desired": f_det_dis_desired,
                "num_attenuators": num_attenuators
            }
            previous_scan_id = scan_id
        # catch back-to-back 

    bb_out = _toDictItem(list(BlockedBeams.values()))
    trans_1d = []
    atomic_pol_1d = []
    for m in mappings.values():
        transmissions = []
        atomic_pols = []
        timestamps = []
        for c in m["Transmissions"]:
            t = c['transmission']
            ap = c['atomic_pol']
            if t > 0:
                transmissions.append(t)
                atomic_pols.append(ap)
                timestamps.append(c['HE3_IN_timestamp'])
        x = np.array(timestamps)
        x0 = m['Insert_time']/1000.0
        xa = (x-x0)/(3600)
        dx = np.zeros_like(x)
        v = np.array(transmissions)
        dv = np.zeros_like(v)
        va = np.array(atomic_pols)
        dva = np.zeros_like(va)
        if (len(timestamps) > 1):
            ginv, logP = np.polyfit(xa, np.log(va), 1)
            m['P0'] = np.exp(logP)
            m['Gamma'] = -1/ginv
        else:
            m['P0'] = va[0]
        ordering = np.argsort(x)
        trans_1d.append(VSans1dData(x[ordering] - x0, v[ordering], dx=dx, dv=dv, xlabel="timestamp (s)", vlabel="Transmission", metadata={"title": _s(m["Cell_name"])}))
        atomic_pol_1d.append(VSans1dData(xa[ordering], va[ordering], dx=dx, dv=dva, xlabel="timestamp (h)", vlabel="Atomic Polarization", metadata={"title": _s(m["Cell_name"])}))

    return he3data, trans_1d, atomic_pol_1d, [Parameters({"cells": mappings, "blocked_beams": bb_out})]

def get_transmission_sum(detectors, panel_name="auto"):
    from .vsansdata import short_detectors
    total_counts = -np.inf
    if panel_name == 'auto':
        for sn in short_detectors:
            detname = "detector_{sn}".format(sn=sn)
            if 'data' in detectors[detname]:
                counts = detectors[detname]['data']['value'].sum()
                if counts > total_counts:
                    total_counts = counts
    else:
        detname = "detector_{sn}".format(sn=panel_name)
        total_counts = detectors[detname]['data']['value'].sum()
    return total_counts

@nocache
@module
def patch(data, patches=None):
    """
    loads a data file into a VSansData obj and returns that.

    **Inputs**

    data (raw): datafiles with metadata to patch

    patches (patch_metadata[]:run.filename): patches to be applied, with run.filename used as unique key

    **Returns**

    patched (raw): datafiles with patched metadata

    2019-07-26 Brian Maranville
    """
    if patches is None:
        return data
    
    from jsonpatch import JsonPatch
    from collections import OrderedDict

    # make a master dict of metadata from provided key:

    key="run.filename"

    master = OrderedDict([(_s(d.metadata[key]), d.metadata) for d in data])
    to_apply = JsonPatch(patches)
    to_apply.apply(master, in_place=True)

    return data

@nocache
@module
def sort_sample(raw_data):
    """
    categorize data files

    **Inputs**

    raw_data (raw[]): datafiles in

    **Returns**

    blocked_beam (raw[]): datafiles with "blocked beam" intent

    2018-04-27 Brian Maranville
    """

    blocked_beam = [f for f in raw_data if _s(f.metadata.get('analysis.intent', '')).lower().startswith('bl')]

    return blocked_beam

@nocache
@module
def calculate_XY(raw_data, solid_angle_correction=True):
    """
    from embedded detector metadata, calculates the x,y,z values for each detector.

    **Inputs**

    raw_data (raw): raw datafiles

    solid_angle_correction (bool): Divide by solid angle

    **Returns**

    realspace_data (realspace): datafiles with realspace information

    | 2018-04-28 Brian Maranville
    | 2019-09-19 Added monitor normalization
    | 2019-09-22 Separated monitor and dOmega norm
    | 2020-10-02 Brian Maranville ignore back detector when data missing
    """
    from .vsansdata import VSansDataRealSpace, short_detectors
    from collections import OrderedDict

    metadata = deepcopy(raw_data.metadata)
    monitor_counts = metadata['run.moncnt']
    new_detectors = OrderedDict()
    for sn in short_detectors:
        detname = 'detector_{short_name}'.format(short_name=sn)
        det = deepcopy(raw_data.detectors[detname])

        dimX = int(det['pixel_num_x']['value'][0])
        dimY = int(det['pixel_num_y']['value'][0])
        z_offset = det.get('setback', {"value": [0.0]})['value'][0]
        z = det['distance']['value'][0] + z_offset

        if sn == "B":
            # special handling for back detector
            total = det['integrated_count']['value'][0] if 'integrated_count' in det else 0
            if total < 1:
                # don't load the back detector if it has no counts (turned off)
                continue
            beam_center_x_pixels = det['beam_center_x']['value'][0] # in pixels
            beam_center_y_pixels = det['beam_center_y']['value'][0]

            cal_x = det['cal_x']['value'] # in cm
            cal_y = det['cal_y']['value']

            x_pixel_size = cal_x[0] # cm
            y_pixel_size = cal_y[0] # cm

            beam_center_x = x_pixel_size * beam_center_x_pixels
            beam_center_y = y_pixel_size * beam_center_y_pixels

            # lateral_offset = det['lateral_offset']['value'][0] # # already cm
            realDistX =  0.5 * x_pixel_size
            realDistY =  0.5 * y_pixel_size

            data = det['data']['value']
            if 'linear_data_error' in det and 'value' in det['linear_data_error']:
                data_variance = np.sqrt(det['linear_data_error']['value'])
            else:
                data_variance = data
            udata = Uncertainty(data, data_variance)

        else:
            
            orientation = det['tube_orientation']['value'][0].decode().upper()
            coeffs = det['spatial_calibration']['value']
            lateral_offset = 0
            vertical_offset = 0
            beam_center_x = det['beam_center_x']['value'][0]
            beam_center_y = det['beam_center_y']['value'][0]
            panel_gap = det['panel_gap']['value'][0]/10.0 # mm to cm
            if (orientation == "VERTICAL"):
                x_pixel_size = det['x_pixel_size']['value'][0] / 10.0 # mm to cm
                y_pixel_size = coeffs[1][0] / 10.0 # mm to cm 
                lateral_offset = det['lateral_offset']['value'][0] # # already cm

            else:
                x_pixel_size = coeffs[1][0] / 10.0
                y_pixel_size = det['y_pixel_size']['value'][0] / 10.0 # mm to cm
                vertical_offset = det['vertical_offset']['value'][0] # already cm

            #solid_angle_correction = z*z / 1e6
            data = det['data']['value']
            if 'linear_data_error' in det and 'value' in det['linear_data_error']:
                data_variance = np.sqrt(det['linear_data_error']['value'])
            else:
                data_variance = data
            udata = Uncertainty(data, data_variance)
            position_key = sn[-1]
            if position_key == 'T':
                # FROM IGOR: (q,p = 0 for lower-left pixel) 
                # if(cmpstr("T",detStr[1]) == 0)
                #   data_realDistY[][] = tube_width*(q+1/2) + offset + gap/2		
                #   data_realDistX[][] = coefW[0][q] + coefW[1][q]*p + coefW[2][q]*p*p
                realDistX =  coeffs[0][0]/10.0 # to cm
                realDistY =  0.5 * y_pixel_size + vertical_offset + panel_gap/2.0
            
            elif position_key == 'B':
                # FROM IGOR: (q,p = 0 for lower-left pixel) 
                # if(cmpstr("B",detStr[1]) == 0)
                #   data_realDistY[][] = offset - (dimY - q - 1/2)*tube_width - gap/2
                #   data_realDistX[][] = coefW[0][q] + coefW[1][q]*p + coefW[2][q]*p*p
                realDistX =  coeffs[0][0]/10.0
                realDistY =  vertical_offset - (dimY - 0.5)*y_pixel_size - panel_gap/2.0
                
            elif position_key == 'L':
                # FROM IGOR: (q,p = 0 for lower-left pixel) 
                # if(cmpstr("L",detStr[1]) == 0)
                #   data_realDistY[][] = coefW[0][p] + coefW[1][p]*q + coefW[2][p]*q*q
                #   data_realDistX[][] = offset - (dimX - p - 1/2)*tube_width - gap/2
                realDistX =  lateral_offset - (dimX - 0.5)*x_pixel_size - panel_gap/2.0
                realDistY =  coeffs[0][0]/10.0
                
            elif position_key == 'R':
                # FROM IGOR: (q,p = 0 for lower-left pixel) 
                #   data_realDistY[][] = coefW[0][p] + coefW[1][p]*q + coefW[2][p]*q*q
                #   data_realDistX[][] = tube_width*(p+1/2) + offset + gap/2
                realDistX =  x_pixel_size*(0.5) + lateral_offset + panel_gap/2.0
                realDistY =  coeffs[0][0]/10.0

        #x_pos = size_x/2.0 # place panel with lower-right corner at center of view
        #y_pos = size_y/2.0 # 
        x0_pos = realDistX - beam_center_x # then move it the 'real' distance away from the origin,
        y0_pos = realDistY - beam_center_y # which is the beam center

        #metadata['det_' + short_name + '_x0_pos'] = x0_pos
        #metadata['det_' + short_name + '_y0_pos'] = y0_pos
        X,Y = np.indices((dimX, dimY))
        X = X * x_pixel_size + x0_pos
        Y = Y * y_pixel_size + y0_pos
        det['data'] = udata
        det['X'] = X
        det['dX'] = x_pixel_size
        det['Y'] = Y
        det['dY'] = y_pixel_size
        det['Z'] = z
        det['dOmega'] = x_pixel_size * y_pixel_size / z**2
        if solid_angle_correction:
            det['data'] /= det['dOmega']

        new_detectors[detname] = det
    output = VSansDataRealSpace(metadata=metadata, detectors=new_detectors)
    return output

@cache
@module
def oversample_XY(realspace_data, oversampling=3, exclude_back_detector=True):
    """
    Split each pixel into subpixels in realspace

    **Inputs**

    realspace_data (realspace): data in XY coordinates

    oversampling (int): how many subpixels to create along x and y 
      (e.g. oversampling=3 results in 9 subpixels per input pixel)

    exclude_back_detector {exclude back detector} (bool): Skip oversampling for the back detector when true

    **Returns**

    oversampled (realspace): datasets with oversampled pixels

    | 2019-10-29 Brian Maranville
    """
    from .vsansdata import short_detectors
    rd = realspace_data.copy()

    for sn in short_detectors:
        detname = 'detector_{short_name}'.format(short_name=sn)
        if detname == 'detector_B' and exclude_back_detector:
            continue
        if not detname in rd.detectors:
            continue
        det = rd.detectors[detname]
        
        X = det['X']
        Y = det['Y']
        dX = det['dX']
        dY = det['dY']
        x_min = X.min() - dX/2.0
        y_min = Y.min() - dY/2.0

        data = det['data']
        dimX, dimY = data.shape
        dimX *= oversampling
        dimY *= oversampling
        dX /= oversampling
        dY /= oversampling
        X,Y = np.indices((dimX, dimY))
        X = X * dX + x_min + dX/2.0
        Y = Y * dY + y_min + dY/2.0

        det['data'] = np.repeat(np.repeat(data, oversampling, 0), oversampling, 1) / oversampling**2
        det['X'] = X
        det['dX'] = dX
        det['Y'] = Y
        det['dY'] = dY
        det['dOmega'] /= oversampling**2
        det['oversampling'] = det.get('oversampling', 1.0) * oversampling

    return rd

@module
def monitor_normalize(qdata, mon0=1e8):
    """"
    Given a SansData object, normalize the data to the provided monitor

    **Inputs**

    qdata (qspace): data in

    mon0 (float): provided monitor

    **Returns**

    output (qspace): corrected for monitor counts
    2019-09-19  Brian Maranville
    """
    output = qdata.copy()
    monitor = output.metadata['run.moncnt']
    umon = Uncertainty(monitor, monitor)
    for d in output.detectors:
        output.detectors[d]['data'] *= mon0/umon
    return output

@cache
@module
def correct_detector_sensitivity(data, sensitivity, exclude_back_detector=True):
    """
    Divide by detector sensitivity

     **Inputs**

    data (realspace): datafile in realspace X,Y coordinates

    sensitivity (realspace): DIV file

    exclude_back_detector {exclude back detector} (bool): Skip correcting the back detector when true 

    **Returns**

    div_corrected (realspace): datafiles where output is divided by sensitivity

    2019-10-30 Brian Maranville
    """
    from .vsansdata import VSansDataQSpace, short_detectors
    from collections import OrderedDict

    
    new_data = data.copy()
    for detname in data.detectors:
        det = new_data.detectors[detname]
        div_det = sensitivity.detectors.get(detname, None)
        if detname.endswith("_B") and exclude_back_detector:
            continue
        if div_det is not None:
            det['data'] /= div_det['data']

    return new_data


@nocache
@module   
def calculate_Q(realspace_data):
    """
    Calculates Q values (Qx, Qy) from realspace coordinates and wavelength
     **Inputs**

    realspace_data (realspace): datafiles in realspace X,Y coordinates

    **Returns**

    QxQy_data (qspace): datafiles with Q information

    2018-04-27 Brian Maranville
    """
    from .vsansdata import VSansDataQSpace, short_detectors
    from collections import OrderedDict

    metadata = deepcopy(realspace_data.metadata)
    wavelength = metadata['resolution.lmda']
    delta_wavelength = metadata['resolution.dlmda']
    new_detectors = OrderedDict()
    #print(r.detectors)
    for sn in short_detectors:
        detname = 'detector_{short_name}'.format(short_name=sn)
        if not detname in realspace_data.detectors:
            continue
        det = deepcopy(realspace_data.detectors[detname])
        X = det['X']
        Y = det['Y']
        z = det['Z']
        r = np.sqrt(X**2+Y**2)
        theta = np.arctan2(r, z)/2 #remember to convert L2 to cm from meters
        q = (4*np.pi/wavelength)*np.sin(theta)
        phi = np.arctan2(Y, X)
        # need to add qz... and qx and qy are really e.g. q*cos(theta)*sin(alpha)...
        # qz = q * sin(theta)
        qx = q * np.cos(theta) * np.cos(phi)
        qy = q * np.cos(theta) * np.sin(phi)
        qz = q * np.sin(theta)
        det['Qx'] = qx
        det['Qy'] = qy
        det['Qz'] = qz
        det['Q'] = q
        new_detectors[detname] = det

    output = VSansDataQSpace(metadata=metadata, detectors=new_detectors)
    return output


@cache
@module
def circular_av_new(qspace_data, q_min=None, q_max=None, q_step=None):
    """
    Calculates I vs Q from qpace coordinate data
     **Inputs**

    qspace_data (qspace): datafiles in qspace X,Y coordinates

    q_min (float): minimum Q value for binning (defaults to q_step)

    q_max (float): maxiumum Q value for binning (defaults to max of q values in data)

    q_step (float): step size for Q bins (defaults to minimum qx step)

    **Returns**

    I_Q (v1d[]): VSANS 1d data

    | 2019-10-29 Brian Maranville
    """
    from .vsansdata import short_detectors, VSans1dData

    output = []
    for sn in short_detectors:
        detname = 'detector_{short_name}'.format(short_name=sn)
        if not detname in qspace_data.detectors:
            continue
        det = deepcopy(qspace_data.detectors[detname])

        my_q_step = (det['Qx'][1, 0] - det['Qx'][0, 0]) * det.get('oversampling', 1.0) if q_step is None else q_step

        my_q_min = my_q_step if q_min is None else q_min
        
        my_q_max = det['Q'].max() if q_max is None else q_max

        q_bins = np.arange(my_q_min, my_q_max+my_q_step, my_q_step)
        Q = (q_bins[:-1] + q_bins[1:])/2.0
        dx = np.zeros_like(Q)

        mask = det.get('shadow_mask', np.ones_like(det['Q'], dtype=bool))

        # dq = data.dq_para if hasattr(data, 'dqpara') else np.ones_like(data.q) * q_step
        I, _bins_used = np.histogram(det['Q'][mask], bins=q_bins, weights=(det['data'].x)[mask])
        I_norm, _ = np.histogram(det['Q'][mask], bins=q_bins, weights=np.ones_like(det['data'].x[mask]))
        I_var, _ = np.histogram(det['Q'][mask], bins=q_bins, weights=det['data'].variance[mask])
        #Q_ave, _ = np.histogram(data.q, bins=q_bins, weights=data.q)
        #Q_var, _ = np.histogram(data.q, bins=q_bins, weights=data.dq_para**2)
        #Q_mean, _ = np.histogram(data.meanQ[mask], bins=q_bins, weights=data.meanQ[mask])
        #Q_mean_lookup = np.digitize(data.meanQ[mask], bins=q_bins)
        #Q_mean_norm, _ = np.histogram(data.meanQ[mask], bins=q_bins, weights=np.ones_like(data.data.x[mask]))
        #ShadowFactor, _ = np.histogram(data.meanQ[mask], bins=q_bins, weights=data.shadow_factor[mask])

        nonzero_mask = I_norm > 0

        I[nonzero_mask] /= I_norm[nonzero_mask]
        I_var[nonzero_mask] /= (I_norm[nonzero_mask]**2)
        #Q_mean[Q_mean_norm > 0] /= Q_mean_norm[Q_mean_norm > 0]
        #ShadowFactor[Q_mean_norm > 0] /= Q_mean_norm[Q_mean_norm > 0]

        # calculate Q_var...
        # remarkably, the variance of a sum of normalized gaussians 
        # with variances v_i, displaced from the mean center by xc_i
        # is the sum of (xc_i**2 + v_i).   Gaussians are weird.

        # exclude Q_mean_lookups that overflow the length of the calculated Q_mean:
        #Q_var_mask = (Q_mean_lookup < len(Q_mean))
        #Q_mean_center = Q_mean[Q_mean_lookup[Q_var_mask]]
        #Q_var_contrib = (data.meanQ[mask][Q_var_mask] - Q_mean_center)**2 + (data.dq_para[mask][Q_var_mask])**2
        #Q_var, _ = np.histogram(data.meanQ[mask][Q_var_mask], bins=q_bins, weights=Q_var_contrib)
        #Q_var[Q_mean_norm > 0] /= Q_mean_norm[Q_mean_norm > 0]

        canonical_output = VSans1dData(Q, I, dx, np.sqrt(I_var), xlabel="Q", vlabel="I", xunits="1/Ang", vunits="arb.", xscale="log", vscale="log", metadata={"title": sn})
        output.append(canonical_output)

    return output

def circular_average(qspace_data):
    """
    Calculates I vs Q from qpace coordinate data
     **Inputs**

    qspace_data (qspace[]): datafiles in qspace X,Y coordinates

    **Returns**

    I_Q (v1d[]): VSANS 1d data

    2018-04-27 Brian Maranville
    """
    from reductus.sansred.sansdata import Sans1dData
    from collections import OrderedDict

def calculate_IQ(realspace_data):
    """
    Calculates I vs Q from realspace coordinate data
     **Inputs**

    realspace_data (realspace[]): datafiles in qspace X,Y coordinates

    **Returns**

    I_Q (iqdata[]): datafiles with Q information

    2018-04-27 Brian Maranville
    """
    from reductus.sansred.sansdata import Sans1dData
    from collections import OrderedDict

@cache
@module
def geometric_shadow(realspace_data, border_width=4.0, inplace=False):
    """
    Calculate the overlap shadow from upstream panels on VSANS detectors
    Outputs will still be realspace data, but with shadow_mask updated to
    include these overlap regions

     **Inputs**

    realspace_data (realspace): datafiles in qspace X,Y coordinates

    border_width (float): extra width (in pixels on original detector) to exclude
        as a margin.  Note that if the data has been oversampled, this number
        still refers to original pixel widths (oversampling is divided out)
    
    inplace (bool): do the calculation in-place, modifying the input dataset

    **Returns**

    shadowed (realspace): datafiles in qspace X,Y coordinates with updated
        shadow mask

    2019-11-01 Brian Maranville
    """

    detector_angles = calculate_angles(realspace_data)

    if not inplace:
        realspace_data = realspace_data.copy()

    # assume that detectors are in decreasing Z-order
    for dnum, (detname, det) in enumerate(detector_angles.items()):
        rdet = realspace_data.detectors[detname]
        shadow_mask = rdet.get('shadow_mask', np.ones_like(rdet['data'].x, dtype=bool))
        for udet in list(detector_angles.values())[dnum+1:]:
            #final check: is detector in the same plane?
            if udet['Z'] < det['Z'] - 1:
                x_min_index = int(round((udet['theta_x_min'] - det['theta_x_min'])/det['theta_x_step'] - border_width))
                x_max_index = int(round((udet['theta_x_max'] - det['theta_x_min'])/det['theta_x_step'] + border_width))
                y_min_index = int(round((udet['theta_y_min'] - det['theta_y_min'])/det['theta_y_step'] - border_width))
                y_max_index = int(round((udet['theta_y_max'] - det['theta_y_min'])/det['theta_y_step'] + border_width))
                dimX = rdet['data'].shape[0]
                dimY = rdet['data'].shape[1]
                x_applies = (x_min_index < dimX and x_max_index >= 0)
                y_applies = (y_min_index < dimY and y_max_index >= 0)
                if x_applies and y_applies:
                    x_min_index = max(x_min_index, 0)
                    x_max_index = min(x_max_index, dimX)
                    y_min_index = max(y_min_index, 0)
                    y_max_index = min(y_max_index, dimY)
                    shadow_mask[x_min_index:x_max_index, y_min_index:y_max_index] = False
        rdet['shadow_mask'] = shadow_mask
    
    return realspace_data

def calculate_angles(rd):
    from collections import OrderedDict
    from .vsansdata import short_detectors

    detector_angles = OrderedDict()
    for sn in short_detectors:
        detname = 'detector_{short_name}'.format(short_name=sn)
        if not detname in rd.detectors:
            continue
        det = rd.detectors[detname]
        X = det['X']
        dX = det['dX']
        Y = det['Y']
        dY = det['dY']
        z = det['Z']

        dobj = OrderedDict()

        # small angle approximation
        dobj['theta_x_min'] = X.min() / z
        dobj['theta_x_max'] = X.max() / z
        dobj['theta_x_step'] = dX / z

        dobj['theta_y_min'] = Y.min() / z
        dobj['theta_y_max'] = Y.max() / z
        dobj['theta_y_step'] = dY / z
        dobj['Z'] = det['Z']

        detector_angles[detname] = dobj

    return detector_angles

@cache
@module
def sector_cut(qspace_data, sector=[0.0, 90.0], mirror=True):
    """
    Calculate an additional shadow mask for defining a sector cut

    **Inputs**

        qspace_data (qspace): input datafile in q-space coordinates

        sector (range:sector_centered): angle and opening of sector cut (degrees)

        mirror (bool): extend sector cut on both sides of origin
    
    **Returns**

        sector_masked (qspace): datafile with mask updated with angular sector cut
    
    | 2020-11-02 Brian Maranville
    """
    angle_offset, opening = sector
    if angle_offset is None:
        angle_offset = 0.0
    if opening is None:
        opening = 90.0

    x_offset = np.cos(np.radians(angle_offset))
    y_offset = np.sin(np.radians(angle_offset))
    cos_theta_min = np.cos(np.radians(opening/2.0))

    for detname in qspace_data.detectors:
        det = qspace_data.detectors[detname]
        # theta is the distance in angle from the offset_vector to the datapoints
        Q_normsq = det['Qx']**2 + det['Qy']**2
        nonzero = Q_normsq > 0
        Q_normsq[Q_normsq == 0] = 1.0
        cos_theta = (det['Qx'] * x_offset + det['Qy'] * y_offset) / np.sqrt(Q_normsq)
        shadow_mask = det.get('shadow_mask', np.ones_like(det['data'].x, dtype=bool))
        sector_mask = np.zeros_like(det['data'].x, dtype=bool)
        sector_mask[np.logical_and(nonzero, cos_theta >= cos_theta_min)] = True
        if mirror:
            sector_mask[np.logical_and(nonzero, cos_theta <= -cos_theta_min)] = True

        det['shadow_mask'] = np.logical_and(shadow_mask, sector_mask)
    
    return qspace_data

@cache
@module
def top_bottom_shadow(realspace_data, width=3, inplace=True):
    """
    Calculate the overlap shadow from upstream panels on VSANS detectors
    Outputs will still be realspace data, but with shadow_mask updated to
    include these overlap regions

     **Inputs**

    realspace_data (realspace): datafiles in qspace X,Y coordinates

    width (float): width to mask on the top of the L,R detectors 
        (middle and front).  Note that if the data has been oversampled, this number
        still refers to original pixel widths (oversampling is divided out)
    
    inplace (bool): do the calculation in-place, modifying the input dataset

    **Returns**

    shadowed (realspace): datafiles in qspace X,Y coordinates with updated
        shadow mask
    
    2019-11-01 Brian Maranville
    """
    from .vsansdata import short_detectors

    rd = realspace_data if inplace else realspace_data.copy()

    for det in rd.detectors.values():
        orientation = det.get(
            'tube_orientation', {}
        ).get(
            'value', [b"NONE"]
        )[0].decode().upper()

        if orientation == 'VERTICAL':
            oversampling = det.get('oversampling', 1)
            shadow_mask = det.get('shadow_mask', np.ones_like(det['data'].x, dtype=bool))
            effective_width = int(width * oversampling)
            shadow_mask[:,0:effective_width] = False
            shadow_mask[:,-effective_width:] = False
            det['shadow_mask'] = shadow_mask
    
    return rd