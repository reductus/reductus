from posixpath import basename, join
from copy import copy, deepcopy
from io import BytesIO
import sys
import numpy as np

from dataflow.lib.uncertainty import Uncertainty

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

@cache
@module
def LoadVSANS(filelist=None, check_timestamps=True):
    """
    loads a data file into a VSansData obj and returns that.

    **Inputs**

    filelist (fileinfo[]): Files to open.
    
    check_timestamps (bool): verify that timestamps on file match request

    **Returns**

    output (raw[]): all the entries loaded.

    2018-04-29 Brian Maranville
    """
    from dataflow.fetch import url_get
    from .loader import readVSANSNexuz
    if filelist is None:
        filelist = []
    data = []
    for fileinfo in filelist:
        path, mtime, entries = fileinfo['path'], fileinfo.get('mtime', None), fileinfo.get('entries', None)
        name = basename(path)
        fid = BytesIO(url_get(fileinfo, mtime_check=check_timestamps))
        entries = readVSANSNexuz(name, fid)
        data.extend(entries)

    return data

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
    from dataflow.fetch import url_get
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

@cache
@module
def LoadVSANSHe3Parallel(filelist=None, check_timestamps=True):
    """
    loads a data file into a VSansData obj and returns that.

    **Inputs**

    filelist (fileinfo[]): Files to open.
    
    check_timestamps (bool): verify that timestamps on file match request

    **Returns**

    output (raw[]): all the entries loaded.

    2018-04-29 Brian Maranville
    """

    from dataflow.calc import process_template
    from dataflow.core import Template

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
        config = {"0": {"filelist": [{"path": fi["path"], "source": fi["source"], "mtime": fi["mtime"]}]}}
        nodenum = 0
        terminal_id = "output"
        retval = process_template(template, config, target=(nodenum, terminal_id))
        output.extend(retval.values)

    return output

@cache
@module
def He3_transmission(he3data, trans_panel="auto"):
    """
    Calculate transmissions

    **Inputs**

    he3data (raw[]): datafiles with he3 transmissions

    trans_panel (opt:MB|MT|ML|MR|FT|FB|FL|FR|auto): panel to use for transmissions

    **Returns**

    annotated (raw[]): datafiles grouped by cell

    transmissions (v1d[]): 1d transmissions per cell

    mappings (params[]): cell parameters

    2018-04-30 Brian Maranville
    """
    from .vsansdata import short_detectors, Parameters, VSans1dData,  _toDictItem
    import dateutil.parser
    from collections import OrderedDict
    
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
    for d in he3data:
        tstart = d.metadata.get("he3_back.starttime", None)
        if tstart is None:
            tstart = 0
        tstart = int(tstart) # coerce strings
        tstartstr = "{ts:d}".format(ts=tstart)
        tend = dateutil.parser.parse(d.metadata.get("end_time", "1969")).timestamp()
        count_time =  d.metadata['run.rtime']
        monitor_counts = d.metadata['run.moncnt']
        detector_counts = get_transmission_sum(d.detectors, panel_name=trans_panel)
        filename = d.metadata.get("run.filename", "unknown_file")
        m_det_dis_desired = d.metadata.get("m_det.dis_des", 0)
        f_det_dis_desired = d.metadata.get("f_det.dis_des", 0)
        num_attenuators = d.metadata.get("run.atten", 0)
        middle_timestamp = (tend - (count_time * 1000.0 / 2.0)) # in milliseconds
        mappings.setdefault(tstartstr, {
            "Insert_time": tstart,
            "Cell_name": d.metadata.get("he3_back.name", "unknown"),
            "Transmissions": []
        })

        # assume that He3 OUT is measured before He3 IN
        mapping_trans = mappings[tstartstr]["Transmissions"]
        t_key = (m_det_dis_desired, f_det_dis_desired, num_attenuators)
        if d.metadata.get("he3_back.inbeam", 0) > 0:
            p = previous_transmission
            #print('previous transmission: ', p)
            #print(p.get("CellTimeIdentifier", None), tstart,
            #        p.get("m_det_dis_desired", None),  m_det_dis_desired, 
            #        p.get("f_det_dis_desired", None), f_det_dis_desired,
            #        p.get("num_attenuators", None),  num_attenuators)
            if p.get("CellTimeIdentifier", None) == tstart and \
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
                mapping_trans.append(deepcopy(p))
        else:
            previous_transmission = {
                "CellTimeIdentifier": tstart,
                "HE3_OUT_file": filename,
                "HE3_OUT_counts": detector_counts,
                "HE3_OUT_count_time": count_time,
                "HE3_OUT_mon": monitor_counts,
                "m_det_dis_desired": m_det_dis_desired,
                "f_det_dis_desired": f_det_dis_desired,
                "num_attenuators": num_attenuators
            }
        # catch back-to-back 

    bb_out = _toDictItem(list(BlockedBeams.values()))
    trans_1d = []
    for m in mappings.values():
        transmissions = []
        timestamps = []
        for c in m["Transmissions"]:
            t = c['transmission']
            if t > 0:
                transmissions.append(t)
                timestamps.append(c['HE3_IN_timestamp'])
        x = np.array(timestamps)
        dx = np.zeros_like(x)
        v = np.array(transmissions)
        dv = np.zeros_like(v)
        trans_1d.append(VSans1dData(x, v, dx=dx, dv=dv, xlabel="timestamp", vlabel="Transmission", metadata={"title": m["Cell_name"]}))

    return he3data, trans_1d, [Parameters({"cells": mappings, "blocked_beams": bb_out})]

def get_transmission_sum(detectors, panel_name="auto"):
    from .vsansdata import short_detectors
    total_counts = -np.inf
    if panel_name == 'auto':
        for sn in short_detectors:
            detname = "detector_{sn}".format(sn=sn)
            counts = detectors[detname]['data']['value'].sum()
            if counts > total_counts:
                total_counts = counts
    else:
        detname = "detector_{sn}".format(sn=panel_name)
        total_counts = detectors[detname]['data']['value'].sum()
    return total_counts

@cache
@module
def patch(data, key="run.filename", patches=None):
    """
    loads a data file into a VSansData obj and returns that.

    **Inputs**

    data (raw[]): datafiles with metadata to patch

    key (str): unique field for identifying a metadata dict from a list

    patches (patch_metadata[]): patches to be applied

    **Returns**

    patched (raw[]): datafiles with patched metadata

    2018-04-27 Brian Maranville
    """
    if patches is None:
        return data
    
    from jsonpatch import JsonPatch

    # make a master dict of metadata from provided key:
    #from collections import OrderedDict
    #master = OrderedDict([(d.metadata[key], d.metadata) for d in data])
    
    metadatas = [d.metadata for d in data]
    to_apply = JsonPatch(patches)

    to_apply.apply(metadatas, in_place=True)

    #patched_master = to_apply.apply(master)
    #patched = list(patched_master.values())

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
def calculate_XY(raw_data):
    """
    from embedded detector metadata, calculates the x,y,z values for each detector.

    **Inputs**

    raw_data (raw[]): raw datafiles

    **Returns**

    realspace_data (realspace[]): datafiles with realspace information

    2018-04-27 Brian Maranville
    """
    from .vsansdata import VSansDataRealSpace, short_detectors
    from collections import OrderedDict

    output = []
    for r in raw_data:
        metadata = deepcopy(r.metadata)
        new_detectors = OrderedDict()
        for sn in short_detectors:
            detname = 'detector_{short_name}'.format(short_name=sn)
            det = deepcopy(r.detectors[detname])
            z_offset = det.get('setback', {"value": [0.0]})['value'][0]
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

            dimX = int(det['pixel_num_x']['value'][0])
            dimY = int(det['pixel_num_y']['value'][0])
            z = det['distance']['value'][0] + z_offset
            #solid_angle_correction = z*z / 1e6
            data = det['data']['value']
            udata = Uncertainty(data, data)
            
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
            det['norm'] = x_pixel_size * y_pixel_size / z**2

            new_detectors[detname] = det
        output.append(VSansDataRealSpace(metadata=metadata, detectors=new_detectors))

    return output

@nocache
@module   
def calculate_Q(realspace_data):
    """
    Calculates Q values (Qx, Qy) from realspace coordinates and wavelength
     **Inputs**

    realspace_data (realspace[]): datafiles in realspace X,Y coordinates

    **Returns**

    QxQy_data (qspace[]): datafiles with Q information

    2018-04-27 Brian Maranville
    """
    from .vsansdata import VSansDataQSpace, short_detectors
    from collections import OrderedDict

    output = []
    for rd in realspace_data:
        metadata = deepcopy(rd.metadata)
        wavelength = metadata['resolution.lmda']
        delta_wavelength = metadata['resolution.dlmda']
        new_detectors = OrderedDict()
        #print(r.detectors)
        for sn in short_detectors:
            detname = 'detector_{short_name}'.format(short_name=sn)
            det = deepcopy(rd.detectors[detname])
            X = det['X']
            Y = det['Y']
            z = det['Z']
            r = np.sqrt(X**2+Y**2)
            theta = np.arctan2(r, z)/2 #remember to convert L2 to cm from meters
            q = (4*np.pi/wavelength)*np.sin(theta)
            alpha = np.arctan2(Y, X)
            qx = q*np.cos(alpha)
            qy = q*np.sin(alpha)

            det['Qx'] = qx
            det['Qy'] = qy
            det['Q'] = q
            new_detectors[detname] = det

        output.append(VSansDataQSpace(metadata=metadata, detectors=new_detectors))

    return output

def circular_average(qspace_data):
    """
    Calculates I vs Q from qpace coordinate data
     **Inputs**

    qspace_data (qspace[]): datafiles in qspace X,Y coordinates

    **Returns**

    QxQy_data (qspace[]): datafiles with Q information

    2018-04-27 Brian Maranville
    """
    from sansred.sansdata import Sans1dData
    from collections import OrderedDict