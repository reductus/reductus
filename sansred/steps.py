from posixpath import basename, join
from copy import copy, deepcopy
import numpy as np
from sansdata import SansData, Sans1dData, Parameters
import StringIO

ALL_ACTIONS = []
IGNORE_CORNER_PIXELS = True

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

    # This is a decorator, so return the original function
    return action
    
#################
# Loader stuff   
################# 

def url_load(fileinfo):
    from dataflow.modules.load import url_get
    path, mtime, entries = fileinfo['path'], fileinfo['mtime'], fileinfo['entries']
    name = basename(path)
    fid = StringIO.StringIO(url_get(fileinfo))
    nx_entries = LoadMAGIKPSD.load_entries(name, fid, entries=entries)
    fid.close()
    return nx_entries

@cache
@module
def LoadSANS(filelist=None, flip=False, transpose=False):
    """ 
    loads a data file into a SansData obj and returns that.
    Checks to see if data being loaded is 2D; if not, quits
        
    **Inputs**
    
    filelist (fileinfo[]): Files to open.
    
    flip (bool): flip the data up and down
    
    transpose (bool): transpose the data
    
    **Returns**
    
    output (sans2d[]): all the entries loaded.
    
    2016-04-17 Brian Maranville    
    """
    from dataflow.modules.load import url_get
    from .loader import readSANSNexuz
    if filelist is None:
        filelist =[]
    data = []
    for fileinfo in filelist:
        path, mtime, entries = fileinfo['path'], fileinfo['mtime'], fileinfo['entries']
        name = basename(path)
        fid = StringIO.StringIO(url_get(fileinfo))
        entries = readSANSNexuz(name, fid)
        for entry in entries:
            if flip:
                entry.data.x = np.fliplr(entry.data.x)
            if transpose:
                entry.data.x = entry.data.x.T
        data.extend(entries)
    
    return data

@cache
@module
def PixelsToQ(data, correct_solid_angle=True):
    """
    generate a q_map for sansdata. Each pixel will have 4 values: (qx,qy,q,theta)

        
    **Inputs**
    
    data (sans2d): data in
    
    correct_solid_angle {Correct solid angle} (bool): Apply correction for mapping
        curved Ewald sphere to flat detector
    
    **Returns**
    
    output (sans2d): converted to I vs. Qx, Qy
    
    2016-04-06 Brian Maranville  
    """
    L2=data.metadata['det.dis']
    x0=data.metadata['det.beamx'] #should be close to 64
    y0=data.metadata['det.beamy'] #should be close to 64
    wavelength=data.metadata['resolution.lmda']
    shape=data.data.x.shape

    qx=np.empty(shape,'Float64')
    qy=np.empty(shape,'Float64')
    
    x,y = np.indices(shape)
    X=data.metadata['det.pixelsizex']/10.0*(x-x0) # in mm in nexus
    Y=data.metadata['det.pixelsizey']/10.0*(y-y0)
    r=np.sqrt(X**2+Y**2)
    theta=np.arctan2(r,L2*100)/2 #remember to convert L2 to cm from meters
    q=(4*np.pi/wavelength)*np.sin(theta)
    alpha=np.arctan2(Y,X)
    qx=q*np.cos(alpha)
    qy=q*np.sin(alpha)
    if correct_solid_angle:
        data.data.x = data.data.x * (np.cos(theta)**3)
    res=SansData()
    res.data=copy(data.data)
    res.metadata=deepcopy(data.metadata)
    #Adding res.q
    res.q = q
    res.qx=qx
    res.qy=qy
    res.theta=theta
    return res

@cache
@module
def annular_av(data):
    """
    Using annular averging, it converts data to 1D (Q vs. I)

        
    **Inputs**
    
    data (sans2d): data in
    
    **Returns**
    
    output (sans1d): converted to I vs. Q
    
    2016-04-08 Brian Maranville    
    """
    """ """
    from draw_annulus_aa import annular_mask_antialiased
    
    #annular_mask_antialiased(shape, center, inner_radius, outer_radius, background_value=0.0, mask_value=1.0, oversampling=8)
    # calculate the change in q that corresponds to a change in pixel of 1
    q_per_pixel = data.qx[1,0]-data.qx[0,0] / 1.0
   
    # for now, we'll make the q-bins have the same width as a single pixel
    step = q_per_pixel
    shape1 = data.data.x.shape
    x0=data.metadata['det.beamx'] #should be close to 64
    y0=data.metadata['det.beamy'] #should be close to 64
    
    center = (x0, y0)
    Qmax = data.q.max()
    Q = np.arange(0,Qmax,step)
    I = []
    I_error = []
    for i in Q:
        # inner radius is the q we're at right now, converted to pixel dimensions:
        inner_r = i * (1.0/q_per_pixel)
        # outer radius is the q of the next bin, also converted to pixel dimensions:
        outer_r = (i + step) * (1.0/q_per_pixel)
        mask = annular_mask_antialiased(shape1,center,inner_r,outer_r)
        if IGNORE_CORNER_PIXELS == True:
            mask[0,0] = mask[-1,0] = mask[-1,-1] = mask[0,-1] = 0.0
        #print "Mask: ",mask
        integrated_intensity = np.sum(mask.T*data.data.x)
        #error = getPoissonUncertainty(integrated_intensity)
        error = np.sqrt(integrated_intensity)
        mask_sum = np.sum(mask)
        if (integrated_intensity != 0.0):
            norm_integrated_intensity = integrated_intensity / mask_sum
            #error['yupper'] /= mask_sum
            #error['ylower'] /= mask_sum
            error /= mask_sum
        else:
            norm_integrated_intensity = integrated_intensity
            
        I.append(norm_integrated_intensity) # not multiplying by step anymore
        I_error.append(error)
    
    output = Sans1dData(Q, I, dx=0, dv=I_error, xlabel="Q", vlabel="I", xunits="inv. A", vunits="neutrons")
    output.metadata=deepcopy(data.metadata) 
    return output

@module
def correct_detector_efficiency(sansdata):
    """
    Given a SansData object, corrects for the efficiency of the detection process 
    
    **Inputs**
    
    sansdata (sans2d): data in
    
    **Returns**
    
    output (sans2d): corrected for efficiency
    
    2016-08-03 Brian Maranville and Andrew Jackson
    """
    
    L2=sansdata.metadata['det.dis']
    lambd = sansdata.metadata["resolution.lmda"]
    shape=sansdata.data.x.shape
    (x0,y0) = np.shape(sansdata.data.x)
    x,y = np.indices(shape)
    X = sansdata.metadata['det.pixelsizex']/10.0*(x-x0/2)
    Y = sansdata.metadata['det.pixelsizey']/10.0*(y-y0/2)
    r=np.sqrt(X**2+Y**2)
    theta_det=np.arctan2(r,L2*100)/2
    
    stAl = 0.00967*lambd*0.8 #dimensionless, constants from JGB memo
    stHe = 0.146*lambd*2.5
    
    ff = np.exp(-stAl/np.cos(theta_det))*(1-np.exp(-stHe/np.cos(theta_det))) / ( np.exp(-stAl)*(1-np.exp(-stHe)) )

    res=SansData()
    res.data.x=sansdata.data.x/ff
    #if not sansdata.data.variance==None:
            #res.data.variance=sansdata.data.variance/ff

    res.metadata=deepcopy(sansdata.metadata)
    res.q = copy(sansdata.q)
    res.qx=copy(sansdata.qx)
    res.qy=copy(sansdata.qy)
    #note that the theta calculated for this correction is based on the center of the
    #detector and NOT the center of the beam. Thus leave the q-relevant theta alone.
    res.theta=copy(sansdata.theta)

    return res

@module
def correct_dead_time(sansdata,deadtime=3.4e-6):
    """\
    Correct for the detector recovery time after each detected event
    (suppresses counts as count rate increases)
    
    **Inputs**
    
    sansdata (sans2d): data in
    
    deadtime (float): detector dead time (nonparalyzing?)
    
    **Returns**
    
    output (sans2d): corrected for dead time
    
    2010-01-01 Andrew Jackson?
    """
    
    dscale = 1/(1-deadtime*(np.sum(sansdata.data.x)/sansdata.metadata["run.rtime"]))
    
    result = SansData()
    result.data.x = sansdata.data.x*dscale
    result.metadata=deepcopy(sansdata.metadata)
    result.q = copy(sansdata.q)
    result.qx = copy(sansdata.qx)
    result.qy = copy(sansdata.qy)
    result.theta = copy(sansdata.theta)
    
    return result

@module
def monitor_normalize(sansdata,mon0=1e8):
    """"\
    Given a SansData object, normalize the data to the provided monitor
    
    **Inputs**
    
    sansdata (sans2d): data in
    
    mon0 (float): provided monitor
    
    **Returns**
    
    output (sans2d): corrected for dead time
    
    2010-01-01 Andrew Jackson?
    """    
    monitor=sansdata.metadata['run.moncnt']
    result=sansdata.data.x*mon0/monitor
    res=SansData()
    res.data.x=result
    res.metadata=deepcopy(sansdata.metadata)
    #added res.q
    res.q=copy(sansdata.q)
    res.qx=copy(sansdata.qx)
    res.qy=copy(sansdata.qy)
    res.theta=copy(sansdata.theta)
    return res

@module
def generate_transmission(in_beam,empty_beam,xmin=55,xmax=74,ymin=53,ymax=72):
    """\
    To calculate the transmission, we integrate the intensity in a box for a measurement
    with the substance in the beam and with the substance out of the beam and take their ratio.
    The box is definied by xmin, xmax and ymin, ymax, I start counting at (0,0).

    Coords are taken with reference to bottom left of the image.
    
    **Inputs**
    
    in_beam (sans2d): measurement with sample in the beam
    
    empty_beam (sans2d): measurement with no sample in the beam
    
    xmin (int): left pixel of integration box
    
    xmax (int): right pixel of integration box
    
    ymin (int): bottom pixel of integration box
    
    ymax (int): top pixel of integration box
    
    **Returns**
    
    output (params): calculated transmission for the integration area
    
    2016-08-04 Brian Maranville    
    """
    #I_in_beam=0.0
    #I_empty_beam=0.0
    #(xmax,ymax) = np.shape(in_beam.data.x)
    #print xmax,ymax
    #Vectorize this loop, it's quick, but could be quicker
    #test against this simple minded implementation
    #print ymax-coords_bottom_left[1],ymax-coords_upper_right[1]

    #for x in range(coords_bottom_left[0],coords_upper_right[0]+1):
    #    for y in range(ymax-coords_upper_right[1],ymax-coords_bottom_left[1]+1):
    #        I_in_beam=I_in_beam+in_beam.data.x[x,y]
    #        I_empty_beam=I_empty_beam+empty_beam.data.x[x,y]
    I_in_beam = np.sum(in_beam.data.x[xmin:xmax+1, ymin:ymax+1])
    I_empty_beam = np.sum(empty_beam.data.x[xmin:xmax+1, ymin:ymax+1])
    result=Parameters(transmission=I_in_beam/I_empty_beam)
    
    return result

@module
def subtract(subtrahend, minuend):
    """
    Algebraic subtraction of datasets pixel by pixel
    
    **Inputs**
    
    subtrahend (sans2d): a in (a-b) = c
    
    minuend (sans2d): b in (a-b) = c
    
    **Returns**
    
    output (sans2d): c in (a-b) = c
    
    2010-01-01 unknown
    """
    return subtrahend.__sub1__(minuend)
    
@module
def product(data, factor_param):
    """
    Algebraic multiplication of dataset
    
    **Inputs**
    
    data (sans2d): data in (a)
    
    factor_param (params): multiplication factor (b)
    
    **Returns**
    
    output (sans2d): result (c in a*b = c)
    
    2010-01-01 unknown
    """
    return data.__mul__(factor_param['factor'])
    
def correct_solid_angle(sansdata):
    """\
    given a SansData with q,qx,qy,and theta images defined,
    correct for the fact that the detector is flat and the Ewald sphere is curved.
    Need to calculate theta first, so do PixelsToQ before this.
    
    **Inputs**
    
    data (sans2d): data in
    
    **Returns**
    
    output (sans2d): corrected for mapping to Ewald
    
    2016-08-03 Brian Maranville    
    """
    
    sansdata.data.x = sansdata.data.x*(np.cos(sansdata.theta)**3)
    return sansdata

@cache
@module
def correct_detector_sensitivity(sansdata,sensitivity):
    """"
    Given a SansData object and an sensitivity map generated from a div,
    correct for the efficiency of the detector. Recall that sensitivities are
    generated by taking a measurement of plexiglass and dividing by the mean value
    
    **Inputs**
    
    sansdata (sans2d): data in (a)
    
    sensitivity (sans2d): data in (b)
    
    **Returns**
    
    output (sans2d): result c in a/b = c
    
    2010-01-01 unknown
    """
    #result=sansdata.data/sensitivity #Could be done more elegantly by defining a division method on SansData
    #res=SansData()
    #res.data=result
    #res.metadata=deepcopy(sansdata.metadata)
    ##added res.q
    #res.q=copy(sansdata.q)
    #res.qx=copy(sansdata.qx)
    #res.qy=copy(sansdata.qy)
    #res.theta=copy(sansdata.theta)
    
    #Used SansData operation to make more efficient
    result = sansdata.__truediv__(sensitivity.data)
    
    return result

@cache
@module
def SuperLoadSANS(filelist=None, do_solid_angle=True, do_det_eff=True, do_deadtime=True, deadtime=3.4e-6, do_mon_norm=True, mon0=1e8):
    """ 
    loads a data file into a SansData obj, and performs common reduction steps
    Checks to see if data being loaded is 2D; if not, quits
    
        
    **Inputs**
    
    filelist (fileinfo[]): Files to open.
    
    do_solid_angle {Solid angle corr.} (bool): correct for mapping of Ewald sphere to flat detector
        
    do_det_eff {Detector efficiency corr.} (bool): correct detector efficiency
    
    do_deadtime {Dead time corr.} (bool): correct for detector efficiency drop due to detector dead time
    
    deadtime {Dead time value} (float): value of the dead time in the calculation above
    
    do_mon_norm {Monitor normalization} (bool): normalize data to a provided monitor value
    
    mon0 (float): provided monitor
        
    **Returns**
    
    output (sans2d[]): all the entries loaded.
    
    2016-04-17 Brian Maranville    
    """
    data = LoadSANS(filelist, flip=False, transpose=False)
    
    data = [PixelsToQ(d, correct_solid_angle=do_solid_angle) for d in data]
    
    if do_det_eff:
        data = [correct_detector_efficiency(d) for d in data]
    if do_deadtime:
        data = [correct_dead_time(d, deadtime=deadtime) for d in data]
    if do_mon_norm:
        data = [monitor_normalize(d, mon0=mon0) for d in data]
        
    return data

        
def getPoissonUncertainty(y):
    """ for a poisson-distributed observable, get the range of 
     expected actual values for a particular measured value.
     As described in the documentation for the error analysis
     on the BaBar experiment: 
    
    4)      An alternative with some nice properties is +-0.5 + sqrt(n+0.25)
    i.e upper error = 0.5 + sqrt(n+0.25), lower error = -0.5 + sqrt(n+0.25).
    These produce the following intervals:  
    n    low      high     cred.        
    0 0.000000  1.000000 0.632121
    1 0.381966  2.618034 0.679295
    2 1.000000  4.000000 0.681595
    3 1.697224  5.302776 0.682159
    4 2.438447  6.561553 0.682378
    5 3.208712  7.791288 0.682485
    6 4.000000  9.000000 0.682545
    7 4.807418 10.192582 0.682582
    8 5.627719 11.372281 0.682607
    9 6.458619 12.541381 0.682624
    """
    hi =  0.5+np.sqrt(y+0.25);
    lo = -0.5+np.sqrt(y+0.25);
    #return {"yupper": y+hi, "ylower": y-lo, "hi": hi, "lo": lo}
    return {"yupper": y+hi, "ylower": y-lo}                
