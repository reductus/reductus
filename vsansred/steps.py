from posixpath import basename, join
from copy import copy, deepcopy
from io import BytesIO

# Action names
__all__ = [] # type: List[str]

# Action methods
ALL_ACTIONS = [] # type: List[Callable[Any, Any]]

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

@module
def patch(data, key="filename", patches=None):
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
def calculate_Q(raw_data):
    """
    from embedded detector metadata, calculates the Qx, Qy and Qz values for each detector.

    **Inputs**

    raw_data (raw[]): raw datafiles

    **Returns**

    vsansdata (vsansdata[]): datafiles with Q information

    2018-04-27 Brian Maranville
    """
    from .vsansdata import VSansData
    from collections import OrderedDict

    output = []
    for r in raw_data:
        metadata = deepcopy(r.metadata)
        new_detectors = OrderedDict()
        for dname in r.detectors:
            short_name = dname.replace('detector_', '')
            if dname == 'detector_B':
                # don't process the back detector
                continue
            det = deepcopy(r.detectors[dname])
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
            size_x = dimX * x_pixel_size
            size_y = dimY * y_pixel_size
            z = det['distance']['value'][0] + z_offset
            #solid_angle_correction = z*z / 1e6
            data = det['data']['value']
            
            
            position_key = dname[-1]
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
            
            new_detectors[dname] = det
        output.append(VSansData(metadata=metadata, detectors=new_detectors))

    return output
    

