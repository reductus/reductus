from posixpath import basename, join
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
DETECTOR_ACTIVE = (320, 340)

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
def LoadSANS(filelist=None, flip=True, transpose=True):
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
        data.extend(entries)
    
    return data

@cache
@module
def PixelsToQ(data):
    """
    generate a q_map for sansdata. Each pixel will have 4 values: (qx,qy,q,theta)

        
    **Inputs**
    
    data (sans2d): data in
    
    **Returns**
    
    output (sans2d): converted to I vs. Qx, Qy
    
    2016-04-06 Brian Maranville    
    """
    from sansdata import SansData
    import numpy as np
    import copy
    
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
    res=SansData()
    res.data=copy.copy(data.data)
    res.metadata=copy.deepcopy(data.metadata)
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
    from sansdata import Sans1dData
    from draw_annulus_aa import annular_mask_antialiased
    import numpy as np
    import copy
    
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
    output.metadata=copy.deepcopy(data.metadata) 
    return output
    
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
    import numpy as np
    hi =  0.5+np.sqrt(y+0.25);
    lo = -0.5+np.sqrt(y+0.25);
    #return {"yupper": y+hi, "ylower": y-lo, "hi": hi, "lo": lo}
    return {"yupper": y+hi, "ylower": y-lo}                
