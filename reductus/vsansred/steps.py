from posixpath import basename, join
from copy import copy, deepcopy
from io import BytesIO
import sys
import numpy as np

from .vsansdata import VSansData

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
def LoadVSANS(filelist=None, check_timestamps=True, load_data=True, apply_attenuation=False, apply_monitor_norm=False,apply_dead_time=False,mon0=1e8):
    """
    loads a data file into a VSansData obj and returns that. (uses cached values)

    **Inputs**

    filelist (fileinfo[]): Files to open.
    
    check_timestamps (bool): verify that timestamps on file match request

    load_data (bool): include the data in the load

    apply_attenuation (bool): whether to apply attenuation correction

    apply_monitor_norm (bool): whether to normalize data to monitor counts

    apply_dead_time (bool): whether to apply dead time correction

    mon0 (float): target monitor value for normalization (default: 1e8)

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

        loaded_entries = retval.values

        for sample in loaded_entries:
            if load_data and sample is not None:
                if apply_dead_time:
                    sample = correct_dead_time(sample)

                if apply_attenuation:
                    sample = correct_attenuation(sample)

                if apply_monitor_norm:
                    target_mon0 = 1e8 if mon0 is None else float(mon0)
                    sample = monitor_normalize_raw(sample, mon0=target_mon0)

            output.append(sample)


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

    data (raw[]): datafiles with metadata to patch

    patches (patch_metadata[]:run.filename): patches to be applied, with run.filename used as unique key

    **Returns**

    patched (raw[]): datafiles with patched metadata

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
    | 2026-10-08 Jonathan Gaudet adapted how to read variance if set prior to calculate_xy
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
            if 'variance' in det['data']:
                data_variance = det['data']['variance']
            elif 'linear_data_error' in det and 'value' in det['linear_data_error']:
                data_variance = det['linear_data_error']['value']  #it was np.sqrt here before, but not correct?
            else:
                data_variance = data.copy()
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
            if 'variance' in det['data']:
                data_variance = det['data']['variance']
            elif 'linear_data_error' in det and 'value' in det['linear_data_error']:
                data_variance = det['linear_data_error']['value']  # it was np.sqrt here before, but not correct?
            else:
                data_variance = data.copy()
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

@module
def monitor_normalize_raw(rawdata, mon0=1e8):
    """"
    Given a SansData object, normalize the data to the provided monitor

    **Inputs**

    rawdata (raw): data in

    mon0 (float): provided monitor

    **Returns**

    output (raw): corrected for monitor counts
    2026-10-08  Jonathan Gaudet
    """
    output = deepcopy(rawdata)

    monitor = float(output.metadata['run.moncnt'])
    scale_factor = mon0 / monitor

    for det_name, det in output.detectors.items():
        if "data" not in det:
            continue

        #Read detector counts of that detector
        raw_counts = np.array(det["data"]["value"], dtype=float)

        #Read variance or create if not set
        if "variance" in det["data"] and det["data"]["variance"] is not None:
            raw_variance = np.array(det["data"]["variance"], dtype=float)
        else:
            raw_variance = np.copy(raw_counts)

        #normalizing intensity
        det["data"]["value"] = raw_counts * scale_factor
        det["data"]["variance"] = raw_variance * (scale_factor ** 2)

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

def get_panel_data(data_obj, PANEL_KEY):

    detectors = data_obj.detectors
    det_map = {k.lower(): v for k, v in detectors.items()}

    if PANEL_KEY.lower() in det_map:
        det = det_map[PANEL_KEY.lower()]
    else:
        raise KeyError(
            f"Panel '{PANEL_KEY}' not found in detectors. Available: {list(detectors.keys())}"
        )

    panel_udata = det["data"] if isinstance(det, dict) else det.data
    raw_array = (
        panel_udata.x if hasattr(panel_udata, "x") else panel_udata
    )

    return panel_udata, raw_array

def get_panel_data_raw(rawdata, PANEL_KEY):
    """Extract value and error arrays from a raw dataset panel and wrap in Uncertainty."""
    det = rawdata.detectors[PANEL_KEY]
    vals = np.array(det["data"]["value"], dtype=float)

    if "linear_data_error" in det and "value" in det["linear_data_error"]:
        vars_ = np.array(det["linear_data_error"]["value"], dtype=float)
    else:
        vars_ = np.copy(vals)  # Poisson error variance = N

    return Uncertainty(vals, vars_), vals


@module
def calculate_vsans_transmission(in_beam, empty_beam, margin=5, PANEL_KEY = "detector_B"):
    """
    Calculate transmission from two data sets given the input detector (panel_key). It uses the moments routine to extract the integrated box (ROI).
    Then it calculates the sum of intensity inside that box for both in_beam and empty_beam, and divides the value of in_beam by empty_beam.

     **Inputs**

    in_beam (raw): in_beam real spac, X, Y coordiantes

    empty_beam (raw): empty_beam real spac, X, Y coordinates

    margin {Box margin, width = 4*gauss_width + 2*margin:} (int): Extra margin
    to add to automatically calculated peak width in x and y

    PANEL_KEY (str): detector choice for transmission

    **Returns**

    output (params[]): calculated transmission for the integration area

    2026-08-13 Jonathan Gaudet
    """
    from collections import OrderedDict
    import numpy as np
    from .vsansdata import Parameters

    in_udata, in_array = get_panel_data_raw(in_beam, PANEL_KEY)
    empty_udata, empty_array = get_panel_data_raw(empty_beam, PANEL_KEY)

    # find ROI using same routine as SANS
    _, x, y, width_x, width_y = moments(empty_array)
    center_x = x + 0.5
    center_y = y + 0.5

    xmin = int(max(0, np.floor(center_x - width_x * 2.0) - margin))
    xmax = int(
        min(
            empty_array.shape[0] - 1, np.ceil(center_x + width_x * 2.0) + margin
        )
    )
    ymin = int(max(0, np.floor(center_y - width_y * 2.0) - margin))
    ymax = int(
        min(
            empty_array.shape[1] - 1, np.ceil(center_y + width_y * 2.0) + margin
        )
    )

    # Sum the intensities pixel inside the ROI
    I_in_beam = np.sum(in_udata[xmin: xmax + 1, ymin: ymax + 1])
    I_empty_beam = np.sum(empty_udata[xmin: xmax + 1, ymin: ymax + 1])

    # Calculate transmission
    ratio = I_in_beam / I_empty_beam

    # Extract scalar values from Uncertainty or float
    ratio_val = float(ratio.x) if hasattr(ratio, "x") else float(ratio)
    ratio_var = (
        float(ratio.variance) if hasattr(ratio, "variance") else 0.0
    )
    ratio_err = np.sqrt(ratio_var)

    # 5. Build and return Parameters object
    params_dict = OrderedDict(
        [
            ("factor", ratio_val),
            ("factor_variance", ratio_var),
            ("factor_err", ratio_err),
            ("panel_used", PANEL_KEY),
            (
                "run.configuration",
                in_beam.metadata.get("run.configuration", ""),
            ),
            (
                "sample.description",
                in_beam.metadata.get("sample.description", ""),
            ),
            ("det.des_dis", in_beam.metadata.get("det.des_dis", 0.0)),
            ("resolution.lmda", in_beam.metadata.get("resolution.lmda", 0.0)),
            ("run.guide", in_beam.metadata.get("run.guide", "")),
            (
                "box_used",
                {"xmin": xmin, "xmax": xmax, "ymin": ymin, "ymax": ymax},
            ),
        ]
    )

    result = Parameters(params=params_dict)
    output = [result]

    return output

def moments(data):
    """Returns (height, x, y, width_x, width_y)
    the gaussian parameters of a 2D distribution by calculating its
    moments. Copied from sans steps """
    total = data.sum()
    X, Y = np.indices(data.shape)
    x = (X*data).sum()/total
    y = (Y*data).sum()/total
    col = data[:, int(round(y))]
    width_x = np.sqrt(np.abs((np.arange(col.size)-x)**2*col).sum()/col.sum())
    row = data[int(round(x)), :]
    width_y = np.sqrt(np.abs((np.arange(row.size)-y)**2*row).sum()/row.sum())
    height = data.max()
    return height, x, y, width_x, width_y

@module
def subtract_raw(sample, background):
    """
     Algebraic subtraction of two single dataset pixel by pixel. Assumed to be normalized by monitor prior!!!!

     **Inputs**

     sample (raw): a in (a-b) = c

     background (raw): b in (a-b) = c, defaults to zero

     **Returns**

     output (raw): c in (a-b) = c

     | 2026-08-19 Jonathan Gaudet
     """

    if sample is None:
        return None

    if background is None:
        return deepcopy(sample)

    output = deepcopy(sample)

    for det_name, det in output.detectors.items():
        if det_name in background.detectors:
            bg_det = background.detectors[det_name]

            if "data" not in det or "data" not in bg_det:
                continue

            sample_vals = np.array(det["data"]["value"], dtype=float)
            bg_vals = np.array(bg_det["data"]["value"], dtype=float)


            det["data"]["value"] = sample_vals - bg_vals

    return output

@module
def multiply_raw(sample, factor_param):
    """
     Algebraic subtraction of two single dataset pixel by pixel. Assumed to be normalized by monitor prior!!!!

     **Inputs**

     sample (raw): matrix to multiply, defaults to 1.0

     factor_param (params[]?): factor to multiply matrix to

     **Returns**

     output (raw): factor * sample

     | 2026-08-19 Jonathan Gaudet
     """
    if sample is None:
        return None

    if not factor_param:
        return deepcopy(sample)

    output=deepcopy(sample)

    # 1. Extract factor and variance from parameter object
    p_obj = factor_param[0]
    params = getattr(p_obj, "params", p_obj) if p_obj is not None else {}

    val = float(params.get("factor", 1.0))
    var = float(params.get("factor_variance", 0.0))

    # 2. Multiply raw arrays and propagate errors for each detector panel
    for det_name, det in output.detectors.items():
        if "data" in det and "value" in det["data"]:
            vals = np.array(det["data"]["value"], dtype=float)

            if "linear_data_error" in det and "value" in det["linear_data_error"]:
                vars_ = np.array(det["linear_data_error"]["value"], dtype=float)
            else:
                vars_ = np.copy(vals)

            net_vars = (val ** 2) * vars_ + (vals ** 2) * var

            det["data"]["value"] = vals * val

            if "linear_data_error" not in det:
                det["linear_data_error"] = {}

            det["linear_data_error"]["value"] = np.copy(net_vars)

    return output

@module
def absolute_scaling(sample, open_beam, trans_sample, margin=5, PANEL_KEY='detector_B'):
    """
     perform absolute scaling of a particular data, which is assumed to have an empty already subtracted. 
     Both sample and open_beam should be already on the same monitor count.
     Open_beam is also assumed to be corrected for attenuation.
     Open beam should remain the raw and not pixel space unless you do not correct for solid angle.

      **Inputs**

     sample (realspace): in_beam real spac, X, Y coordiantes

     open_beam (raw): empty_beam real spac, X, Y coordinates

     trans_sample (params[]?): parameter dictionnary for transmission of the sample

     margin {Box margin, width = 4*gauss_width + 2*margin:} (int): Extra margin
     to add to automatically calculated peak width in x and y

     PANEL_KEY (str): detector panel to do absolute scaling (transmission of open beam)

     **Returns**

     abs_data (realspace): calculated transmission for the integration area

     2026-08-18 Jonathan Gaudet
    """

    if sample is None:
        return None

    if open_beam is None:
        return sample

    p_obj = trans_sample[0]
    params = getattr(p_obj, "params", p_obj) if p_obj is not None else {}

    T_sample = float(params.get("factor", 1.0))
    #T_sample_var = float(params.get("factor_variance", 0.0))

    #Extract panel data and find direct beam center and its bounds
    open_udata, open_array = get_panel_data_raw(open_beam, PANEL_KEY)

    _, x, y, width_x, width_y = moments(open_array)
    center_x = x + 0.5
    center_y = y + 0.5

    xmin = int(max(0, np.floor(center_x - width_x * 2.0) - margin))
    xmax = int(
        min(
            open_array.shape[0] - 1, np.ceil(center_x + width_x * 2.0) + margin
        )
    )
    ymin = int(max(0, np.floor(center_y - width_y * 2.0) - margin))
    ymax = int(
        min(
            open_array.shape[1] - 1, np.ceil(center_y + width_y * 2.0) + margin
        )
    )

    #integratation
    flux_slice = open_udata[xmin: xmax + 1, ymin: ymax + 1]
    flux = np.sum(flux_slice)

    if hasattr(flux, "x"):
        flux_val = float(flux.x)
        flux_var = float(getattr(flux, "variance", flux_val))
    else:
        flux_val = float(flux)
        flux_var = flux_val  # Poisson estimate if variance absent

    if flux_val <= 0:
        raise ValueError("Integrated open beam flux must be greater than zero.")

    # sample thickness
    raw_thk = sample.metadata.get("sample.thk", 1.0) #already converted in cm
    dsam_cm = (float(raw_thk) if raw_thk else 1.0)

    if dsam_cm <= 0:
        dsam_cm = 0.1  # Default to 1 mm if input thickness = 0

    # Compute flux with Uncertainty
    u_flux = Uncertainty(flux_val, flux_var)
    u_kappa = u_flux
    u_factor_abs = 1.0 / (u_kappa * dsam_cm * T_sample)

    # multiply data by scaling factor
    abs_data = sample * u_factor_abs

    return abs_data

@cache
@module
def correct_attenuation(sample):
    """
    Divide by the attenuation factor from the lookup tables for the VSANS instrument

    **Inputs**

    sample (raw): VSANS measurement dataset

    **Returns**

    result (raw): attenuation-corrected measurement

    | 2026-10-08 Jonathan Gaudet
    """
    if sample is None:
        return None

    result = deepcopy(sample)
    attenNo = int(sample.metadata.get("run.atten", 0))

    #shortcut if attenuator = 0
    if attenNo == 0:
        result.metadata.update({"run.attenuation_factor": 1.0, "run.attenuation_err": 0.0})
        return result

    #read attenuator table
    table = sample.metadata["run.attenuatortable"]
    wavelength = float(sample.metadata["resolution.lmda"])

    table_arr = np.asarray(table, dtype=float)
    w_key = table_arr[:, 0]

    att_curve = table_arr[:, attenNo+1]

    # Interpolate attenuation factor and its error
    att = float(np.interp(wavelength, w_key, att_curve))

    scale_factor = 1.0 / att

    # Apply inverse scale factor to detector panels
    for det_name, det in result.detectors.items():
        if "data" in det and "value" in det["data"]:
            data = np.array(det["data"]["value"], dtype=float)

            #Read if variance was added if not create it so uncertainty can be propagated
            if "variance" in det["data"] and det["data"]["variance"] is not None:
                var = np.array(det["data"]["variance"], dtype=float)
            else:
                var = np.copy(data)

            det["data"]["value"] = data * scale_factor
            det["data"]["variance"] = var * (scale_factor ** 2)

    return result


@module
def correct_dead_time(sample):
    """
    Correct for the detector recovery time after each detected event
    (suppresses counts as count rate increases)

    **Inputs**

    sample (raw): data in

    **Returns**

    result (raw): corrected for dead time

    2026-08-14 Jonathan Gaudet
    """
    from .vsansdata import short_detectors

    if sample is None:
        return None

    result = sample.copy()

    # extract counting time (seconds)
    rtime = result.metadata["run.rtime"]
    run_time = float(rtime["value"] if isinstance(rtime, dict) else rtime)


    for sn in short_detectors:
        detname = f"detector_{sn}"
        if detname not in result.detectors:
            continue

        det = result.detectors[detname]

        if "data" not in det or "dead_time" not in det:
            continue


        deadtime = det["dead_time"]["value"]

        data = np.array(det["data"]["value"], dtype=float)

        #Read or set variance so it can be propagated properly before calculate_XY
        if "variance" in det["data"] and det["data"]["variance"] is not None:
            var = np.array(det["data"]["variance"], dtype=float)
        else:
            var = np.copy(data)

        if sn =="B":
            total_counts = np.sum(data)
            panel_count_rate = total_counts / run_time

            tau_r = deadtime[0] * panel_count_rate

            dscale = 1.0 / (1.0 - tau_r)
            det["data"]["value"] = data * dscale
            det["data"]["variance"] = var * (dscale ** 2)

        else:

            tube_orientation = det['tube_orientation']['value'][0].decode().upper()
            dimX, dimY = data.shape[-2:]

            if tube_orientation == "VERTICAL":
                for t in range(dimX):
                    tube_sum = np.sum(data[t,:])
                    tau_r = deadtime[t] * (tube_sum/ run_time)
                    dscale = 1.0 / (1.0 - tau_r)
                    data[t,:] = data[t,:] * dscale
                    var[t, :] = var[t, :] * (dscale ** 2)



            else:
                for t in range(dimY):
                    tube_sum = np.sum(data[:,t])
                    tau_r = deadtime[t] * (tube_sum/ run_time)
                    dscale = 1.0 / (1.0 - tau_r)
                    data[:,t] = data[:,t] * dscale
                    var[:, t] = var[:, t] * (dscale ** 2)

            det["data"]["value"] = data
            det["data"]["variance"] = var

    return result

@module
def sum_raw(data):
    """
        Naive addition of counts and monitor from different datasets,
        assuming all datasets were taken under identical conditions
        (except for count time)

        Just adds together count time, counts and monitor.

        Use metadata from first dataset for output.

        **Inputs**

        data (raw[]): measurements to be added together

        **Returns**

        sum (raw): sum of inputs

        2026-08-31  Jonathan Gaudet
        """

    if not data:
        return None

    output = deepcopy(data[0])

    for d in data[1:]:
        # Sum detector panel values pixel by pixel
        for det_name, det in output.detectors.items():
            if det_name in d.detectors and "data" in det and "data" in d.detectors[det_name]:
                target_data = det["data"]
                source_data = d.detectors[det_name]["data"]

                #needed if one detector is off (such as the back detector)
                if "value" in target_data and "value" in source_data:
                    target_data["value"] = np.asarray(target_data["value"], dtype=float) + np.asarray(source_data["value"], dtype=float)

        # Sum monitor and runtime metadata
        for key in ["run.moncnt", "run.rtime", "run.detcnt"]:
            if key in output.metadata and key in d.metadata:
                output.metadata[key] += d.metadata[key]

    return output

def calculate_analyzer_properties(rho0, delta_t, gamma, mu, t_glass):
    """Calculate analyzer efficiency (Pol_eff) and 3He polarization (rho3He) at a given time t.

    **Inputs**
        mu (float): cell opacity

        rho0 (float): initial 3He polarization at insertion time of the cell

        Gamma (float):

        deltaT (float): time difference from time for which rho_0 was determined ()

        t_glass (float) : transmission of the empty glass cell

    **Returns**
        rho3he (float): The 3He polarization at given time

        pol_eff (float): The analyzer efficiency at given time

        t_unpolarized (float): Transmission of the cell for unpolarized beam
    | 2026-09-23 Jonathan Gaudet
    """
    rho3he = rho0 * np.exp(-delta_t / gamma)
    pol_eff = np.tanh(mu * rho3he)
    t_unpolarized = t_glass * np.exp(-mu) * np.cosh(mu * rho3he)

    return rho3he, pol_eff, t_unpolarized


@module
def flipper_sm_efficiency(trans_uu, trans_ud, trans_du, trans_dd, helium_par, block_beam, panel_key="detector_MR"):
    """function calculates flipper and super-mirror efficiency

    **Inputs**
    trans_uu (raw): Transmission up-up

    trans_ud (raw): Transmission up-down

    trans_du (raw): Transmission down-up

    trans_dd (raw): Transmission down-down

    helium_par (params): List of parameters related to the He3 cells time decay (given by He_3Transmission routine)

    block_beam (raw): block beam transmission

    panel_key (str): detector panel choice

    **Returns**

    result(params): output parameters

    | 2026-09-24 Jonathan Gaudet
    """

    from collections import OrderedDict
    from .vsansdata import Parameters

    # Subtract blocked beam to all data
    trans_uu_bgd = subtract_raw(trans_uu, block_beam)
    trans_ud_bgd = subtract_raw(trans_ud, block_beam)
    trans_du_bgd = subtract_raw(trans_du, block_beam)
    trans_dd_bgd = subtract_raw(trans_dd, block_beam)


    # Generate transmission between uu/ud and dd/du to use to determine Psm and Psm_f
    ratio_uu_ud = calculate_vsans_transmission(trans_uu_bgd, trans_ud_bgd, margin=5, PANEL_KEY=panel_key)
    ratio_dd_du = calculate_vsans_transmission(trans_dd_bgd, trans_du_bgd, margin=5, PANEL_KEY=panel_key)

    #extract the dictionary parameters for the cell (assumed only 1)
    cells_dict = helium_par.params['cells']
    cell_info = list(cells_dict.values())[0]
    init_rho = cell_info['P0']
    gamma = cell_info['Gamma']

    #read the time that rho_0 was determined for the Cell and convert into hours
    init_time = (cell_info['Insert_time'] / 1000.0) / 3600.0

    # Calculate average time of a run relative to the initial He3 cell measurement (t0)
    time_uu = get_avg_run_time(trans_uu) - init_time
    time_ud = get_avg_run_time(trans_ud) - init_time
    time_du = get_avg_run_time(trans_du) - init_time
    time_dd = get_avg_run_time(trans_dd) - init_time

    # extract He3 cell parameters
    opacity1ang = float(_s(trans_uu.metadata['he3_back.opacity']))
    wavelength = float(_s(trans_uu.metadata['resolution.lmda']))
    mu = opacity1ang * wavelength
    trans_glass = float(_s(trans_uu.metadata['he3_back.te']))


    rhot_uu, pol_uu, t_uu = calculate_analyzer_properties(init_rho, time_uu, gamma, mu, trans_glass)
    rhot_ud, pol_ud, t_ud = calculate_analyzer_properties(init_rho, time_ud, gamma, mu, trans_glass)
    rhot_du, pol_du, t_du = calculate_analyzer_properties(init_rho, time_du, gamma, mu, trans_glass)
    rhot_dd, pol_dd, t_dd = calculate_analyzer_properties(init_rho, time_dd, gamma, mu, trans_glass)


    ratio_1 = ratio_uu_ud[0].params['factor'] * (t_ud / t_uu)
    ratio_2 = ratio_dd_du[0].params['factor'] * (t_du / t_dd)

    p_sm = (ratio_1 - 1.0) / (pol_uu + (ratio_1 * pol_ud))
    p_sm_f = (ratio_2 - 1.0) / (pol_dd + (ratio_2 * pol_du))

    params_dict = OrderedDict(
        [
            ("eff_sm_up", p_sm),
            ("eff_sm_down", p_sm_f)
        ]
    )

    output = Parameters(params=params_dict)


    return output


def get_avg_run_time(data):
    """function that provide average timestamp of a scan run

        ***Inputs***

        data (raw)  : scattering file

        ***Returns***

        avg time (params) : avg time of the scan run in hours

    |      2026-09-23 Jonathan Gaudet
    """
    from datetime import datetime

    t_start = datetime.fromisoformat(_s(data.metadata['start_time'])).timestamp()
    t_end = datetime.fromisoformat(_s(data.metadata['end_time'])).timestamp()

    return ((t_end + t_start) / 2) / 3600.0

@module
def spin_leakage_corr(data_uu, data_ud, data_du, data_dd, blocked_beam, flipper_par, helium_par):
    """function that provides spin leakage correction to the 4 polarized cross-sections of a pol. sans experiment

        **Inputs**

        data_uu(raw[])  : scattering uu file(s)

        data_ud(raw[])  : scattering ud file(s)

        data_du(raw[])  : scattering du file(s)

        data_dd(raw[])  : scattering dd file(s)

        blocked_beam(raw)  : blocked beam scattering file

        flipper_par(params) : dictionary object containing eff_sm_up, eff_sm_down, gamma,rho0 and t0_cell (see flipper_sm_efficiency method)

        helium_par(params) : dictionary object containing 3He cell parameters obtained from he3_transmission

        **Returns**

        corr_uu(raw)  : correct scattering uu file

        corr_ud(raw) : corrected scattering ud file

        corr_du(raw) : corrected scattering du file

        corr_dd(raw) : corrected scattering dd file

        | 2026-10-07 Jonathan Gaudet
        """

    # check that all list lengths are identical, which is what is assumed here for the workflow
    if not (len(data_uu) == len(data_ud) == len(data_du) == len(data_dd)):
        raise ValueError(
            f"Input dataset list lengths must match! Got lengths: "
            f"uu={len(data_uu)}, ud={len(data_ud)}, du={len(data_du)}, dd={len(data_dd)}"
        )

    p_sm = flipper_par.params['eff_sm_up']
    p_sm_f = flipper_par.params['eff_sm_down']

    epsilon_uu = (1.0 + p_sm) / 2.0
    epsilon_ud = (1.0 - p_sm) / 2.0
    epsilon_dd = (1.0 + p_sm_f) / 2.0
    epsilon_du = (1.0 - p_sm_f) / 2.0

    # 2. Extract He3 cell parameters from helium_par, which doesn't change with time
    cell = helium_par.params['cells']
    cell_info = list(cell.values())[0]
    rho0 = cell_info['P0']
    gamma = cell_info['Gamma']
    t0_cell = (cell_info['Insert_time'] / 1000.0) / 3600.0


    opacity1ang = float(_s(data_uu[0].metadata['he3_back.opacity']))
    wavelength = float(_s(data_uu[0].metadata['resolution.lmda']))
    mu = opacity1ang * wavelength
    trans_glass = float(_s(data_uu[0].metadata['he3_back.te']))

    corr_uu_list = []
    corr_ud_list = []
    corr_du_list = []
    corr_dd_list = []

    for i in range(len(data_uu)):
        curr_uu = data_uu[i]
        curr_ud = data_ud[i]
        curr_du = data_du[i]
        curr_dd = data_dd[i]

        time_avg = (get_avg_run_time(curr_uu) + get_avg_run_time(curr_ud) + get_avg_run_time(curr_du) + get_avg_run_time(curr_dd)) / 4.0
        time_avg = time_avg - t0_cell

        rho3he, pol_eff, t_unpolarized = calculate_analyzer_properties(rho0, time_avg, gamma, mu, trans_glass)

        t_maj  = trans_glass * np.exp(- mu * (1.0 - rho3he))
        t_min = trans_glass * np.exp(-mu * (1.0 + rho3he))

        matrix_corr = set_pol_corr_matrix(epsilon_uu,epsilon_ud,epsilon_dd,epsilon_du,t_maj,t_min)


        d_corr_uu = subtract_raw(curr_uu, blocked_beam)
        d_corr_ud = subtract_raw(curr_ud, blocked_beam)
        d_corr_du = subtract_raw(curr_du, blocked_beam)
        d_corr_dd = subtract_raw(curr_dd, blocked_beam)

        corr_datasets = [d_corr_uu, d_corr_ud, d_corr_du, d_corr_dd]

        #Looping over all detector panels in VSANS datasets
        for det_name, det_info in d_corr_uu.detectors.items():
            all_present = all(
                det_name in d.detectors and
                "data" in d.detectors[det_name] and
                "value" in d.detectors[det_name]["data"]
                for d in corr_datasets
            )

            if not all_present:
                continue

            # Extract panel pixel intensity arrays for each cross-section
            int_obs = [
                np.asarray(d.detectors[det_name]["data"]["value"], dtype=float)
                for d in corr_datasets
            ]

            # Calculate corrected intensities from the spin leakage correction matrix
            int_corr = [
                sum(matrix_corr[k, j] * int_obs[j] for j in range(4))
                for k in range(4)
            ]

            # Assign corrected panel data back to each VSANS cross-section
            for idx, d in enumerate(corr_datasets):
                d.detectors[det_name]["data"]["value"] = int_corr[idx]

        corr_uu_list.append(d_corr_uu)
        corr_ud_list.append(d_corr_ud)
        corr_du_list.append(d_corr_du)
        corr_dd_list.append(d_corr_dd)

    # Average time runs for each corrected cross-section
    corr_uu = average_raw(corr_uu_list)
    corr_ud = average_raw(corr_ud_list)
    corr_du = average_raw(corr_du_list)
    corr_dd = average_raw(corr_dd_list)

    return corr_uu, corr_ud, corr_du, corr_dd

def set_pol_corr_matrix(eps_uu, eps_ud, eps_dd, eps_du, tmaj, tmin):
    """function returning matrix applied to correct for spin leakage at a fixed time
       2026-09-23 Jonathan Gaudet"""

    matrix_corr = np.array([
                   [eps_uu * tmaj, eps_uu * tmin, eps_ud * tmaj, eps_ud * tmin],
                   [eps_uu * tmin, eps_uu * tmaj, eps_ud * tmin, eps_ud * tmaj],
                   [eps_du * tmaj, eps_du * tmin, eps_dd * tmaj, eps_dd * tmin],
                   [eps_du * tmin, eps_du * tmaj, eps_dd * tmin, eps_dd * tmaj]
                ], dtype=float)

    det = np.linalg.det(matrix_corr)

    return np.linalg.inv(matrix_corr)


@module
def extract_mag_nuc_components(data_uu, data_ud, data_du, data_dd, angle_width=30.0, q_step=0.001):
    # TODO: absolute scaling to add
    """
    given the 4 spin-leakage corrected full pol crossections in pixels space, this routine extracts the nuclear and magnetic scattering components.
    The magnetic components are separated in parallel and perpendicular to an applied (or only guide) field direction, which is assumed to be the x-axis,
    lying horizontally within the detector. Uses PixelstoQ and Div routines. AngleWidth is a free parameter??

    **Inputs**

    data_uu(realspace)  : scattering uu file

    data_ud(realspace)  : scattering ud file

    data_du(realspace)  : scattering du file

    data_dd(realspace)  : scattering dd file

    angle_width (float) : angular width (in degrees) of the sector cuts performed to extract Mpar, Mperp, and N^2

    q_step (float): step size in Q of the 1D intensity vs Q cuts obtained for different scattering components

    **Returns**

    data_uu_q (qspace): QxQy data files after spin leakage correction for Up-Up

    data_ud_q (qspace): QxQy data files after spin leakage correction for Up-Up

    data_du_q (qspace): QxQy data files after spin leakage correction for Up-Up

    data_dd_q (qspace): QxQy data files after spin leakage correction for Up-Up

    nuclear(v1d[])  : 1D I vs Q nuclear scattering (N^2)

    mag_par(v1d[]) : 1D I vs Q magnetic parallel to field scattering component (M_par^2)

    mag_perp(v1d[]) : 1D I vs Q magnetic perpendicular to field scattering component (M_perp^2)

    2026-09-23 Jonathan Gaudet
    """

    data_uu_xy = calculate_XY(data_uu, True)
    data_ud_xy = calculate_XY(data_ud, True)
    data_du_xy = calculate_XY(data_du, True)
    data_dd_xy = calculate_XY(data_dd, True)

    data_uu_xy_sha = geometric_shadow(data_uu_xy, border_width=4.0, inplace=False)
    data_ud_xy_sha = geometric_shadow(data_ud_xy, border_width=4.0, inplace=False)
    data_du_xy_sha = geometric_shadow(data_du_xy, border_width=4.0, inplace=False)
    data_dd_xy_sha = geometric_shadow(data_dd_xy, border_width=4.0, inplace=False)

    data_uu_xy_sha2 = top_bottom_shadow(data_uu_xy_sha, width=3, inplace=True)
    data_ud_xy_sha2 = top_bottom_shadow(data_ud_xy_sha, width=3, inplace=True)
    data_du_xy_sha2 = top_bottom_shadow(data_du_xy_sha, width=3, inplace=True)
    data_dd_xy_sha2 = top_bottom_shadow(data_dd_xy_sha, width=3, inplace=True)

    data_uu_q = calculate_Q(data_uu_xy_sha2)
    data_ud_q = calculate_Q(data_ud_xy_sha2)
    data_du_q = calculate_Q(data_du_xy_sha2)
    data_dd_q = calculate_Q(data_dd_xy_sha2)

    nuc1_mean_mask = sector_cut(data_uu_q.copy(), [0.0, angle_width], mirror=False)
    nuc2_mean_mask = sector_cut(data_dd_q.copy(), [0.0, angle_width], mirror=False)

    nuc1_mean = circular_av_new(nuc1_mean_mask)
    nuc2_mean = circular_av_new(nuc2_mean_mask)

    mperp1_mean_mask = sector_cut(data_ud_q.copy(), [0.0, angle_width], mirror=False)
    mperp2_mean_mask = sector_cut(data_du_q.copy(), [0.0, angle_width], mirror=False)
    mperp3_mean_mask = sector_cut(data_ud_q.copy(), [90.0, angle_width], mirror=False)
    mperp4_mean_mask = sector_cut(data_du_q.copy(), [90.0, angle_width], mirror=False)

    mperp1_v1d = circular_av_new(mperp1_mean_mask)
    mperp2_v1d = circular_av_new(mperp2_mean_mask)
    mperp3_v1d = circular_av_new(mperp3_mean_mask)
    mperp4_v1d = circular_av_new(mperp4_mean_mask)

    mpar1_mean = circular_av_new(sector_cut(data_uu_q.copy(), [90.0, angle_width]))
    mpar2_mean = circular_av_new(sector_cut(data_dd_q.copy(), [90.0, angle_width]))


    # Determine global Q range across all cuts to guarantee matching array shapes
    all_cuts = [
        nuc1_mean,
        nuc2_mean,
        mperp1_v1d,
        mperp2_v1d,
        mperp3_v1d,
        mperp4_v1d,
        mpar1_mean,
        mpar2_mean,
    ]
    q_all, _, _ = v1d_list_to_point_cloud(
        [item for cut in all_cuts for item in cut]
    )

    q_min = q_all.min()
    q_max = q_all.max()

    nuclear = combine_sector_cuts_to_1d(
        [nuc1_mean, nuc2_mean],
        q_min=q_min,
        q_max=q_max,
        q_step=q_step,
        title="Nuclear (N^2)",
    )

    mag_perp = combine_sector_cuts_to_1d(
        [mperp1_v1d, mperp2_v1d, mperp3_v1d, mperp4_v1d],
        scales=[0.5, 0.5, 1, 1],
        q_min=q_min,
        q_max=q_max,
        q_step=q_step,
        title="Magnetic Perpendicular (M_perp^2)",
    )

    uu_90_1d = combine_sector_cuts_to_1d(
        [mpar1_mean],
        scales=[1.0],
        q_min=q_min,
        q_max=q_max,
        q_step=q_step,
        title="UU 90 deg",
    )
    dd_90_1d = combine_sector_cuts_to_1d(
        [mpar2_mean],
        scales=[1.0],
        q_min=q_min,
        q_max=q_max,
        q_step=q_step,
        title="DD 90 deg",
    )

    #Calculate mag_par
    mag_par = compute_mag_cross_term(uu_90_1d, dd_90_1d, nuclear)

    return data_uu_q, data_ud_q, data_du_q, data_dd_q, nuclear, mag_par, mag_perp

def v1d_list_to_point_cloud(v1d_list, scale=1.0):
    """
    Loops through each detector panel in circular_av_new output,
    applies a scalar multiplier to intensity and variance, and returns flat 1D arrays.
    """
    q_pts, i_pts, var_pts = [], [], []

    for panel in v1d_list:
        q = panel.x
        i = panel.v * scale
        var = ((panel.dv) ** 2) * (scale ** 2)  # Var(c*I) = c^2 * Var(I)

        valid = np.isfinite(q) & np.isfinite(i) & np.isfinite(var) & (var > 0)

        q_pts.append(q[valid])
        i_pts.append(i[valid])
        var_pts.append(var[valid])

    return np.concatenate(q_pts), np.concatenate(i_pts), np.concatenate(var_pts)

def bin_data_cloud(
    q_cloud,
    i_cloud,
    var_cloud,
    q_min=None,
    q_max=None,
    q_step=0.001,
    num_bins=100,
):
    q_min = q_cloud.min() if q_min is None else q_min
    q_max = q_cloud.max() if q_max is None else q_max

    bin_edges = np.arange(q_min, q_max + q_step, q_step)
    q_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])

    weights = 1.0 / var_cloud

    weighted_i_sum, _ = np.histogram(
        q_cloud, bins=bin_edges, weights=i_cloud * weights
    )
    weight_sum, _ = np.histogram(q_cloud, bins=bin_edges, weights=weights)

    nonzero = weight_sum > 0

    i_binned = np.full_like(q_centers, np.nan)
    di_binned = np.full_like(q_centers, np.nan)

    i_binned[nonzero] = weighted_i_sum[nonzero] / weight_sum[nonzero]
    di_binned[nonzero] = np.sqrt(1.0 / weight_sum[nonzero])

    # RETURN THE FULL ALIGNED GRID (Do not drop NaNs here!)
    return q_centers, i_binned, di_binned

def combine_sector_cuts_to_1d(
    v1d_cuts_list,
    scales=None,
    q_min=None,
    q_max=None,
    q_step=0.001,
    title="Combined",
):
    if scales is None:
        scales = [1.0] * len(v1d_cuts_list)

    q_clouds, i_clouds, var_clouds = [], [], []

    for v1d_list, scale in zip(v1d_cuts_list, scales):
        q_c, i_c, var_c = v1d_list_to_point_cloud(v1d_list, scale=scale)
        q_clouds.append(q_c)
        i_clouds.append(i_c)
        var_clouds.append(var_c)

    q_master = np.concatenate(q_clouds)
    i_master = np.concatenate(i_clouds)
    var_master = np.concatenate(var_clouds)

    q_final, i_final, di_final = bin_data_cloud(
        q_master, i_master, var_master, q_min=q_min, q_max=q_max, q_step=q_step
    )

    template_panel = v1d_cuts_list[0][0]
    result = template_panel._copy_with(i_final, di_final)
    result.x = q_final
    result.dx = np.zeros_like(q_final)
    result.metadata["title"] = title

    return [result]

def compute_mag_cross_term(uu_90_1d, dd_90_1d, nuclear_1d):
    uu_obj = uu_90_1d[0]
    dd_obj = dd_90_1d[0]
    nuc_obj = nuclear_1d[0]

    A = np.asarray(dd_obj.v)
    var_A = np.asarray(dd_obj.dv) ** 2

    B = np.asarray(uu_obj.v)
    var_B = np.asarray(uu_obj.dv) ** 2

    N = np.asarray(nuc_obj.v)
    var_N = np.asarray(nuc_obj.dv) ** 2


    diff = A - B
    num = diff**2
    den = 16.0 * N

    # Filter invalid/NaN points across A, B, and N simultaneously
    valid = (N > 0) & np.isfinite(A) & np.isfinite(B) & np.isfinite(N)

    y = np.full_like(A, np.nan)
    dy = np.full_like(A, np.nan)

    y[valid] = num[valid] / den[valid]

    diff_sq = diff[valid] ** 2
    nonzero_diff = diff_sq > 0

    rel_var_num = np.zeros_like(diff_sq)
    rel_var_num[nonzero_diff] = (
        4.0 * (var_A[valid][nonzero_diff] + var_B[valid][nonzero_diff])
    ) / diff_sq[nonzero_diff]

    rel_var_den = var_N[valid] / (N[valid] ** 2)

    dy[valid] = y[valid] * np.sqrt(rel_var_num + rel_var_den)

    # Clean up NaNs from final result array before returning
    final_mask = np.isfinite(y)

    res_obj = nuc_obj._copy_with(y[final_mask], dy[final_mask])
    res_obj.x = nuc_obj.x[final_mask]
    res_obj.dx = np.zeros_like(res_obj.x)
    res_obj.metadata["title"] = "Magnetic Cross-Term (M_cross^2)"

    return [res_obj]


from scipy.interpolate import griddata


def export_vsans_2d_matrix_grid(sans_qspace, num_points=128, file_suffix=".2d.dat"):
    """
    Grids multi-detector VSansDataQSpace data into a single uniform 2D matrix (Qx, Qy, I, dI)
    compatible with SasView 2D ASCII format, explicitly applying detector masks.

    Unsampled or masked areas are assigned NaN.
    """
    qx_all = []
    qy_all = []
    i_all = []
    var_all = []

    # 1. Gather pixel values from all detector panels
    for detname, det in sans_qspace.detectors.items():
        if "data" not in det or "Qx" not in det or "Qy" not in det:
            continue

        qx_panel = det["Qx"].ravel('C')
        qy_panel = det["Qy"].ravel('C')
        i_panel = det["data"].x.ravel('C')
        var_panel = det["data"].variance.ravel('C')

        # Start with standard validity check (finite values)
        valid = np.isfinite(i_panel) & np.isfinite(qx_panel) & np.isfinite(qy_panel)

        # --- MASK CHECKING ---
        # 1) Check for shadow/detector mask in detector dict
        if 'shadow_mask' in det:
            mask = det['shadow_mask'].astype(bool).ravel('C')
            valid &= ~mask  # Exclude masked pixels (where mask is True)
        elif 'mask' in det:
            mask = det['mask'].astype(bool).ravel('C')
            valid &= ~mask

        # 2) Check for mask inside the Uncertainty object if present
        if hasattr(det['data'], 'mask') and det['data'].mask is not None:
            unc_mask = np.asarray(det['data'].mask).astype(bool).ravel('C')
            valid &= ~unc_mask
        # ----------------------

        qx_all.append(qx_panel[valid])
        qy_all.append(qy_panel[valid])
        i_all.append(i_panel[valid])
        var_all.append(var_panel[valid])

    if not qx_all:
        raise ValueError("No valid unmasked detector data found to export.")

    qx_pts = np.concatenate(qx_all)
    qy_pts = np.concatenate(qy_all)
    i_pts = np.concatenate(i_all)
    err_pts = np.sqrt(np.maximum(0, np.concatenate(var_all)))

    # 2. Define uniform 2D Qx, Qy grid boundaries
    qx_min, qx_max = np.min(qx_pts), np.max(qx_pts)
    qy_min, qy_max = np.min(qy_pts), np.max(qy_pts)

    qx_1d = np.linspace(qx_min, qx_max, num_points)
    qy_1d = np.linspace(qy_min, qy_max, num_points)
    grid_qx, grid_qy = np.meshgrid(qx_1d, qy_1d)

    # 3. Interpolate Intensity and Error onto 2D Grid
    # Linear interpolation leaves unmeasured/masked regions as NaN
    grid_i = griddata((qx_pts, qy_pts), i_pts, (grid_qx, grid_qy), method='linear', fill_value=np.nan)
    grid_di = griddata((qx_pts, qy_pts), err_pts, (grid_qx, grid_qy), method='linear', fill_value=np.nan)

    # 4. Format header and data matrix for SasView
    filename = str(sans_qspace.metadata.get("run.filename", "vsans_2d"))
    title = str(sans_qspace.metadata.get("sample.description", "VSANS 2D Grid"))

    lines = [
        f"ASCII DATA 2D - {title}",
        f"DATA FOR {filename}",
        f"Qx_min = {qx_min:.6e}, Qx_max = {qx_max:.6e}",
        f"Qy_min = {qy_min:.6e}, Qy_max = {qy_max:.6e}",
        f"Qx_bins = {num_points}, Qy_bins = {num_points}",
        "Qx (1/A)   Qy (1/A)   I (1/cm)   dI (1/cm)"
    ]

    for row in range(num_points):
        for col in range(num_points):
            qx_val = grid_qx[row, col]
            qy_val = grid_qy[row, col]
            val_i = grid_i[row, col]
            val_di = grid_di[row, col]

            s_i = f"{val_i:.6e}" if np.isfinite(val_i) else "NaN"
            s_di = f"{val_di:.6e}" if np.isfinite(val_di) else "NaN"

            lines.append(f"{qx_val:14.6e} {qy_val:14.6e} {s_i:>14} {s_di:>14}")

    content = "\n".join(lines)

    return {
        "name": filename,
        "entry": str(sans_qspace.metadata.get("entry", "entry")),
        "file_suffix": file_suffix,
        "value": content,
    }


@module
def export_vsans_2d_matrix_grid(data, num_points=128, output_dir=None, filename_out="vsans_2d_reduced.dat"):
    """
    Grids multi-detector VSansDataQSpace data into a single uniform 2D matrix (Qx, Qy, I, dI)
    compatible with SasView 2D ASCII format using direct index mapping and bincounting
    (matching Reductus mag_extract_components pattern).

    **Inputs**

    data(qspace)  : data 2D to output

    num_points(int) : number of points to output

    output_dir(str) : output directory

    filename_out(str) : optional file path/name to save the output directly to disk

    **Returns**

    result(params): output parameters

    2026-09-23 Jonathan Gaudet
    """

    from collections import OrderedDict
    import numpy as np
    from .vsansdata import Parameters, short_detectors
    import os

    sans_qspace = data
    qx_all = []
    qy_all = []
    i_all = []
    var_all = []

    # 1. Collect valid data using Reductus short_detectors & shadow_mask convention
    for sn in short_detectors:
        detname = f'detector_{sn}'
        if detname not in sans_qspace.detectors:
            continue

        det = sans_qspace.detectors[detname]
        if "data" not in det or "Qx" not in det or "Qy" not in det:
            continue

        qx_panel = det["Qx"].ravel('C')
        qy_panel = det["Qy"].ravel('C')
        i_panel = det["data"].x.ravel('C')
        var_panel = det["data"].variance.ravel('C')

        # Reductus shadow_mask: True = VALID/UNMASKED DATA, False = MASKED
        if 'shadow_mask' in det and det['shadow_mask'] is not None:
            valid_mask = np.asarray(det['shadow_mask']).astype(bool).ravel('C')
        elif 'mask' in det and det['mask'] is not None:
            # Fallback for standard boolean mask arrays (where True = masked)
            valid_mask = ~np.asarray(det['mask']).astype(bool).ravel('C')
        else:
            valid_mask = np.ones_like(i_panel, dtype=bool)

        # Baseline finite check + Reductus valid_mask
        valid = valid_mask & np.isfinite(i_panel) & np.isfinite(qx_panel) & np.isfinite(qy_panel)

        # Check secondary data-level numpy boolean mask if present
        if hasattr(det['data'], 'mask') and det['data'].mask is not None:
            valid &= ~np.asarray(det['data'].mask).astype(bool).ravel('C')

        qx_all.append(qx_panel[valid])
        qy_all.append(qy_panel[valid])
        i_all.append(i_panel[valid])
        var_all.append(var_panel[valid])

    if not qx_all:
        raise ValueError("No valid unmasked detector data found to export.")

    qx_pts = np.concatenate(qx_all)
    qy_pts = np.concatenate(qy_all)
    i_pts = np.concatenate(i_all)
    var_pts = np.concatenate(var_all)

    # 2. Setup grid extents using nan-safe min/max
    qx_min, qx_max = np.nanmin(qx_pts), np.nanmax(qx_pts)
    qy_min, qy_max = np.nanmin(qy_pts), np.nanmax(qy_pts)

    if not (np.isfinite(qx_min) and np.isfinite(qx_max) and np.isfinite(qy_min) and np.isfinite(qy_max)):
        raise ValueError("Calculated Q grid extents contain NaN/Inf. Check detector Qx/Qy arrays.")

    dqx = (qx_max - qx_min) / num_points
    dqy = (qy_max - qy_min) / num_points

    # 3. Calculate discrete bin indices
    ix = np.floor((qx_pts - qx_min) / dqx).astype(int)
    iy = np.floor((qy_pts - qy_min) / dqy).astype(int)

    ix = np.clip(ix, 0, num_points - 1)
    iy = np.clip(iy, 0, num_points - 1)

    flat_indices = iy * num_points + ix
    total_bins = num_points * num_points

    # 4. Perform vector bincounting
    counts = np.bincount(flat_indices, minlength=total_bins)
    i_sum = np.bincount(flat_indices, weights=i_pts, minlength=total_bins)
    var_sum = np.bincount(flat_indices, weights=var_pts, minlength=total_bins)

    # 5. Compute mean intensity and uncertainty with 0.0 default initialization
    grid_i_flat = np.zeros(total_bins, dtype=float)
    grid_di_flat = np.zeros(total_bins, dtype=float)

    valid_bins = counts > 0
    grid_i_flat[valid_bins] = i_sum[valid_bins] / counts[valid_bins]

    # Safe square root for variance propagation
    safe_var = np.maximum(0.0, var_sum[valid_bins])
    grid_di_flat[valid_bins] = np.sqrt(safe_var) / counts[valid_bins]

    grid_i = grid_i_flat.reshape((num_points, num_points))
    grid_di = grid_di_flat.reshape((num_points, num_points))

    # Grid coordinate centers
    qx_centers = qx_min + (np.arange(num_points) + 0.5) * dqx
    qy_centers = qy_min + (np.arange(num_points) + 0.5) * dqy
    grid_qx, grid_qy = np.meshgrid(qx_centers, qy_centers)

    # 6. Format standard NIST 2D ASCII text output with absolute NaN protection
    filename = str(sans_qspace.metadata.get("run.filename", "vsans_2d"))
    title = str(sans_qspace.metadata.get("sample.description", "VSANS 2D Grid"))

    lines = [
        f"FILE: {filename}   CREATED: XXXX-XX-XX",
        f"LABEL: {title}",
        "MON CNT    LAMBDA (A)   DET_OFF(cm)   DET_DIST(cm)   TRANS   THICK(cm)",
        "1e+08      6.0          0.0           100.0          1.0     0.1",
        "BCENT(X,Y)(cm)   A1(mm)   A2(mm)   A1A2DIST(m)   DL/L   BSTOP(mm)",
        "0.0   0.0   10.0 mm   10.0   1.0   0.12   50",
        f"SAM: {filename}",
        "BGD: none",
        "EMP: none",
        "DIV: none",
        "MASK: none",
        "ABS Parameters (3-6): TSTAND=1;DSTAND=1;IZERO=1e+08;XSECT=1;SDEV=1e+05;",
        "Average Choices: AVTYPE=QxQy_ASCII;SAVE=Yes;NAME=Auto;PLOT=Yes;BINTYPE=F1-M1-B;",
        "Collimation type: pinhole",
        "Panel=FL",
        f"NumXPixels={num_points}",
        "XPixelSize_mm=8.0",
        f"NumYPixels={num_points}",
        "YPixelSize_mm=8.0",
        "Duration (s)=1800",
        "reserved for future file definition changes",
        "reserved for future file definition changes",
        "reserved for future file definition changes",
        "reserved for future file definition changes",
        "reserved for future file definition changes",
        "reserved for future file definition changes",
        "*** Data written from ABS folder and may not be a fully corrected data file ***",
        "Data columns are Qx - Qy - I(Qx,Qy) - err(I) - Qz - SigmaQ_parall - SigmaQ_perp - fSubS(beam stop shadow) - Mask",
        "The 2D error need to be checked",
        "ASCII data created XXXX-XX-XX",
        ""
    ]

    for row in range(num_points):
        for col in range(num_points):
            qx_val = grid_qx[row, col]
            qy_val = grid_qy[row, col]
            val_i = grid_i[row, col]
            val_di = grid_di[row, col]
            bin_idx = row * num_points + col

            # Strictly sanitize Qx and Qy
            if not np.isfinite(qx_val):
                qx_val = 0.0
            if not np.isfinite(qy_val):
                qy_val = 0.0

            # Set Column 8 (fSubS) and Column 9 (Mask) per SasView convention
            if counts[bin_idx] > 0 and np.isfinite(val_i) and np.isfinite(val_di):
                fSubS_flag = 1.0  # 1.0 = Clear / Unshadowed pixel
                mask_flag = 0  # 0 = Valid / Unmasked pixel in SasView
            else:
                val_i = 0.0
                val_di = 0.0
                fSubS_flag = 0.0  # 0.0 = Shadowed / Ignored pixel
                mask_flag = 1  # 1 = Masked pixel in SasView

            # Columns: Qx | Qy | I | dI | Qz | SigmaQ_parall (0.0) | SigmaQ_perp (0.0) | fSubS | Mask
            lines.append(
                f"{qx_val:.8e}\t{qy_val:.8e}\t{val_i:.8e}\t{val_di:.8e}\t0.0\t0.00000000e+00\t0.00000000e+00\t{fSubS_flag:.1f}\t{mask_flag}"
            )

    content = "\n".join(lines)

    params_dict = OrderedDict(
        [
            ("name", _s(sans_qspace.metadata.get("name", filename))),
            ("entry", _s(sans_qspace.metadata.get("entry", "entry"))),
            ("file_suffix", ".2d.dat")
        ]
    )

    output = Parameters(params=params_dict)

    # 7. File path resolution and directory auto-creation
    if filename_out:
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            full_path = os.path.join(output_dir, os.path.basename(filename_out))
        else:
            full_path = filename_out
            parent_dir = os.path.dirname(full_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

        with open(full_path, "w") as f:
            f.write(content)

    return output


def average_raw(data_list):
    """
    Averages normalized SANS datasets across multiple time runs and propagates
    uncertainties (errors) in quadrature.
    """
    if not data_list:
        return None

    # Use the first dataset as a base template for metadata and structure
    output = deepcopy(data_list[0])
    num_runs = len(data_list)

    if num_runs == 1:
        return output

    # Average intensity values across detector panels
    for det_name, det in output.detectors.items():
        if "data" in det and "value" in det["data"]:
            # Stack intensity arrays: shape (N_runs, panel_pixels)
            values_stack = np.array([
                d.detectors[det_name]["data"]["value"]
                for d in data_list
            ], dtype=float)

            # Compute mean intensity
            det["data"]["value"] = np.mean(values_stack, axis=0)

            # Propagate errors if present: sigma_avg = sqrt(sum(sigma_i^2)) / N
            if "error" in det["data"]:
                errors_stack = np.array([
                    d.detectors[det_name]["data"]["error"]
                    for d in data_list
                ], dtype=float)
                det["data"]["error"] = np.sqrt(np.sum(errors_stack ** 2, axis=0)) / num_runs

    # Average monitor count and run time metadata
    for key in ["run.moncnt", "run.rtime", "run.detcnt"]:
        if key in output.metadata:
            total_val = sum(d.metadata.get(key, 0.0) for d in data_list)
            output.metadata[key] = total_val / num_runs

    return output

@module
def export_vsans_1d(data_list, save_path=None, filename="output.dat"):
    """
    Combines multi-detector VSANS 1D datasets into a single Q-sorted 1D
    profile (Q, I, dI, dQ) preserving overlapping Q points for overplotting,
    and optionally exports to disk in a SasView-compatible ASCII format.

    **Inputs**

    data_list (v1d[]) : List of VSans1dData objects (one per detector panel)

    save_path (str)   : Optional output directory path

    filename (str)    : Optional file name. If None, derives from dataset metadata.

    **Returns**

    combined_1d (v1d) : Single combined VSans1dData object

    2026-10-07 Jonathan Gaudet
    """

    import os
    from .vsansdata import VSans1dData

    valid_data = [d for d in data_list if len(d.x) > 0]
    if not valid_data:
        return None

    # 1. Combine all arrays from every detector panel
    all_q = np.concatenate([d.x for d in valid_data])
    all_v = np.concatenate([d.v for d in valid_data])
    all_dv = np.concatenate([d.dv for d in valid_data])
    all_dx = np.concatenate([d.dx for d in valid_data])

    # 2. Sort by Q so the output profile is monotonically increasing in Q
    sort_idx = np.argsort(all_q)
    sorted_q = all_q[sort_idx]
    sorted_v = all_v[sort_idx]
    sorted_dv = all_dv[sort_idx]
    sorted_dx = all_dx[sort_idx]

    # 3. Preserve base metadata
    merged_meta = valid_data[0].metadata.copy() if valid_data[0].metadata else {}
    merged_meta['title'] = "Overplotted Detectors"

    combined_1d = VSans1dData(
        x=sorted_q,
        v=sorted_v,
        dx=sorted_dx,
        dv=sorted_dv,
        xlabel=valid_data[0].xlabel,
        vlabel=valid_data[0].vlabel,
        xunits=valid_data[0].xunits,
        vunits=valid_data[0].vunits,
        xscale=valid_data[0].xscale,
        vscale=valid_data[0].vscale,
        metadata=merged_meta
    )

    # 4. Save to directory if a save_path is provided
    if save_path is not None:
        os.makedirs(save_path, exist_ok=True)

        # Fallback if an empty string or None is passed
        out_filename = filename if filename else "output.dat"

        # Ensure the filename ends with .dat if no extension was provided
        base, ext = os.path.splitext(out_filename)
        if not ext:
            out_filename = f"{base}.dat"

        full_filepath = os.path.join(save_path, out_filename)

        # Get exported dictionary payload from VSans1dData method
        export_dict = combined_1d.to_column_text()

        with open(full_filepath, "w", encoding="utf-8") as f:
            f.write(export_dict["value"])

    return combined_1d