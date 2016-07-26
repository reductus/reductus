from posixpath import basename, join
import StringIO

ALL_ACTIONS = []

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
    
    2016-04-09 Brian Maranville    
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

#@cache
#@module
def ItoQ(sansdata=None):
    """
    generate a q_map for sansdata. Each pixel will have 4 values: (qx,qy,q,theta)

        
    **Inputs**
    
    data (sans2d): data in
    
    **Returns**
    
    output (sans1d): converted to I vs. Q
    
    2016-04-06 Brian Maranville    
    """
    
    L2=sansdata.metadata['det.dis']
    x0=sansdata.metadata['det.beamx'] #should be close to 64
    y0=sansdata.metadata['det.beamy'] #should be close to 64
    wavelength=sansdata.metadata['resolution.lmda']
    shape=sansdata.data.x.shape
# theta=np.empty(shape,'Float64')
# q=np.empty(shape,'Float64')
    qx=np.empty(shape,'Float64')
    qy=np.empty(shape,'Float64')
    #vectorize this loop, it will be slow at 128x128
    #test against this simpleminded implentation
    
    ### switching to vectorized form - bbm
# for x in range(0,shape[0]):
# for y in range(0,shape[1]):
# X=PIXEL_SIZE_X_CM*(x-x0)
# Y=PIXEL_SIZE_Y_CM*(y-y0)
# r=np.sqrt(X**2+Y**2)
# theta[x,y]=np.arctan2(r,L2)/2
# q[x,y]=(4*np.pi/wavelength)*np.sin(theta[x,y])
# alpha=np.arctan2(Y,X)
# qx[x,y]=q[x,y]*np.cos(alpha)
# qy[x,y]=q[x,y]*np.sin(alpha)
    x,y = np.indices(shape)
    X = PIXEL_SIZE_X_CM*(x-x0)
    Y=PIXEL_SIZE_Y_CM*(y-y0)
    r=np.sqrt(X**2+Y**2)
    theta=np.arctan2(r,L2*100)/2 #remember to convert L2 to cm from meters
    q=(4*np.pi/wavelength)*np.sin(theta)
    alpha=np.arctan2(Y,X)
    qx=q*np.cos(alpha)
    qy=q*np.sin(alpha)
    res=SansData()
    res.data=copy(sansdata.data)
    res.metadata=deepcopy(sansdata.metadata)
    #Adding res.q
    res.q = q
    res.qx=qx
    res.qy=qy
    res.theta=theta
    return res
