import numpy as np
from uncertainty import Measurement

IGNORE_CORNER_PIXELS = True

class SansData(object):
    """SansData object used for storing values from a sample file (not div/mask).               
       Stores the array of data as a Measurement object (detailed in uncertainty.py)
       Stores all metadata
       q,qx,qy,theta all get updated with values throughout the reduction process
       Tsam and Temp are just used for storage across modules (in wireit)
    """
    def __init__(self,data=None,metadata=None,q=None,qx=None,qy=None,theta=None,Tsam=None,Temp=None):
        self.data=Measurement(data,data)
        self.metadata=metadata
        self.q=q #There are many places where q was not set, i think i fixed most, but there might be more; be wary
        self.qx=qx
        self.qy=qy
        self.theta=theta
        
        self.Tsam = None #Tsam and Temp are used to store the transmissions for later use
        self.Temp = None
    # Note that I have not defined an inplace subtraction
    def __sub__(self,other):
        if isinstance(other,SansData):
            return SansData(self.data-other.data,deepcopy(self.metadata),q=copy(self.q),qx=copy(self.qx),qy=copy(self.qy),theta=copy(self.theta))
        else:
            return SansData(data=self.data-other,metadata=deepcopy(self.metadata),q=copy(self.q),qx=copy(self.qx),qy=copy(self.qy),theta=copy(self.theta))
    #Actual subtraction
    def __sub1__(self,other):
        if isinstance(other,SansData):
            return SansData(self.data.x-other.data.x,deepcopy(self.metadata),q=copy(self.q),qx=copy(self.qx),qy=copy(self.qy),theta=copy(self.theta))
        else:
            return SansData(data=self.data.x-other.data.x,metadata=deepcopy(self.metadata),q=copy(self.q),qx=copy(self.qx),qy=copy(self.qy),theta=copy(self.theta))
    def __add__(self,other):
        if isinstance(other,SansData):
            return SansData(self.data.x+other.data.x,deepcopy(self.metadata),q=copy(self.q),qx=copy(self.qx),qy=copy(self.qy),theta=copy(self.theta))
        else:
            return SansData(data=self.data.x+other.data.x,metadata=deepcopy(self.metadata),q=copy(self.q),qx=copy(self.qx),qy=copy(self.qy),theta=copy(self.theta))
    def __rsub__(self, other):
        return SansData(data=other-self.data, metadata=deepcopy(self.metadata),q=copy(self.q),qx=copy(self.qx),qy=copy(self.qy),theta=copy(self.theta))
    def __truediv__(self,other):
        if isinstance(other,SansData):
            return SansData(Measurement(*err1d.div(self.data.x,self.data.variance,other.data.x,other.data.variance)).x,deepcopy(self.metadata),q=copy(self.q),qx=copy(self.qx),qy=copy(self.qy),theta=copy(self.theta))
        else:
            return SansData(data=Measurement(self.data.x/other, self.data.variance/other**2).x,metadata=deepcopy(self.metadata),q=copy(self.q),qx=copy(self.qx),qy=copy(self.qy),theta=copy(self.theta))
    def __mul__(self,other):
        if isinstance(other,SansData):
            return SansData(Measurement(*err1d.mul(self.data.x,self.data.variance,other.data.x,other.data.variance)).x,deepcopy(self.metadata),q=copy(self.q),qx=copy(self.qx),qy=copy(self.qy),theta=copy(self.theta))
        else:
            return SansData(data = self.data.__mul__(other).x,metadata=deepcopy(self.metadata),q=copy(self.q),qx=copy(self.qx),qy=copy(self.qy),theta=copy(self.theta))
        
    #def __str__(self):
        #return self.data.x.__str__()
    #def __repr__(self):
        #return self.__str__()
    def get_plottable(self): 
        data = self.data.x.astype("int")
        if not (np.abs(data) > 1e-10).any():
            zmin = 0.0
            zmax = 1.0
        else: 
            zmin = data[data > 1e-10].min()
            if IGNORE_CORNER_PIXELS == True:
                mask = np.ones(data.shape, dtype='bool')
                mask[0,0] = mask[-1,0] = mask[-1,-1] = mask[0,-1] = 0.0
                zmax = data[mask].max()
            else:
                zmax = data.max()
        plottable_data = {
            'type': '2d',
            'z':  [data.T.tolist()],
            'title': self.metadata['run.filename']+': ' + self.metadata['sample.labl'],
            #'metadata': self.metadata,
            'options': {
                'fixedAspect': {
                    'fixAspect': True,
                    'aspectRatio': 1.0
                }
            },
            'dims': {
                'xmax': 128,
                'xmin': 0.0, 
                'ymin': 0.0, 
                'ymax': 128,
                'xdim': 128,
                'ydim': 128,
                'zmin': zmin,
                'zmax': zmax,
                },
            'xlabel': 'X',
            'ylabel': 'Y',
            'zlabel': 'Intensity (I)',
            };
        return plottable_data
    
    def get_metadata(self):
        metadata = {}
        metadata.update(self.metadata)
        metadata['plottable'] = self.get_plottable()
        return metadata
    
    def dumps(self):
        return pickle.dumps(self)
    @classmethod
    def loads(cls, str): 
        return pickle.loads(str)
