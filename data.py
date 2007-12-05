import numpy as N

def edges_from_centers(x):
    """
    Given a series of bin centers, compute the bin edges corresponding
    to those centers assuming the edeges are mid-way between the centers.
    Note: assumes the bins are the same width.  If this is not the case,
    there is insufficient information to uniquely reconstruct the edges
    given the centers.
    """
    z = N.zeros(len(x)+1)
    z[1:-1] = centers_from_edges(x)
    z[0] = x[0] - (z[1]-x[0])
    z[-1] = x[-1] + (x[-1]-z[-2])
    return z

def centers_from_edges(x):
    """
    Given a series of bin edges, return the bin centers.
    """
    return (x[:-1]+x[1:])/2

class Data(object):
    """
    Data object.

    For one-dimensional data use x,v.
    For two and three dimensional data use x,y,z,v.

    Multi-dimensional data can be regular or irregular.  If it is irregular,
    the size of x,y,z must match the size of z.  If it is regular,
    the size of each vector x,y,z must match the corresponding dimension of v.
    
    Note: for reflectivity the natural dimensions are x='Qz',y='Qx',z='Qy'
    """
    _x,_xedges,dx = None,None,None
    _y,_yedges,dy = None,None,None
    _z,_zedges,dz = None,None,None
    v,variance = None,None
    xlabel,xunits='x',None
    ylabel,yunits='y',None
    zlabel,zunits='z',None
    vlabel,vunits='v',None
    def add(self, **kw):
        """
        Set a value for an attribute, creating a new one if it is
        not already present.
        """
        for (key,val) in kw.iteritems: setattr(self,key,val)

    def set(self, **kw):
        """
        Set a value for an attribute.  Raise an AttributeError if
        the attribute is not already present.
        
        See help(Data) for details.
        """
        for (key,val) in kw.iteritems():
            if hasattr(self,key):
                setattr(self,key,val)
            else:
                raise AttributeError,"unknown attribute "+key

    # Store variance but allow 1-sigma uncertainty interface
    def _getdv(self): return N.sqrt(self.variance)
    def _setdv(self,dv): self.variance = dv**2
    dv = property(_getdv,_setdv,'1-sigma uncertainty')

    # Store centers and retrieve edges
    def _getx(self): return self._x
    def _setx(self,t):
        self._x = t
        self._xedges = edges_from_centers(t)
    x = property(_getx,_setx,'x centers')
    def _gety(self): return self._y
    def _sety(self,t):
        self._y = t
        self._yedges = edges_from_centers(t)
    y = property(_gety,_sety,'y centers')
    def _getz(self): return self._x
    def _setz(self,t):
        self._z = t
        self._zedges = edges_from_centers(t)
    z = property(_getz,_setz,'z centers')


    # Store edges and retrieve centers
    def _getxedges(self): return self._xedges
    def _setxedges(self,t):
        self._x = centers_from_edges(t)
        self._xedges = t
    xedges = property(_getxedges,_setxedges,'x edges')
    def _getyedges(self): return self._yedges
    def _setyedges(self,t):
        self._y = centers_from_edges(t)
        self._yedges = t
    yedges = property(_getyedges,_setyedges,'y edges')
    def _getzedges(self): return self._zedges
    def _setzedges(self,t):
        self._z = centers_from_edges(t)
        self._zedges = t
    zedges = property(_getzedges,_setzedges,'z edges')

    # Set attributes on initialization
    def __init__(self, **kw): 
        self.set(**kw)

    def __str__(self):
        dims = "%d"%(len(self.x))
        if self.y is not None: 
            dims += "x%d"%(len(self.y))
        if self.z is not None:
            dims += "x%d"%(len(self.z))
        return "Data(%s)"%(dims)

class PolarizedData(object):
    """
    Polarized data object.  This holds all four cross sections of a
    polarized measurement, and provides operations for aligning and
    transforming the cross sections.
    """

    xlabel,xunits='Qz','inv A'
    ylabel,yunits='Qx','inv A'
    zlabel,zunits='Qy','inv A'
    vlabel,vunits='Reflectivity',None

    def __init__(self):
        self.pp,self.pm,self.mp,self.mm = Data(),Data(),Data(),Data()

    def ispolarized(self):
        return True
    
    def isaligned(self):
        """Return true if all four cross sections are aligned."""
        # TODO: perform the check (monoref only)
        return True

    def apply(self, correction):
        """Apply a correction to the data."""
        correction(self)

    def spin_asymmetry(self):
        """
        Return the spin asymmetry for the pp and mm crosssections.
        This is a Data object with one data line.

        TODO: support multidimensional data
        """
        if self.isaligned():
            pp, Vpp = self.pp.v, self.pp.variance
            mm, Vmm = self.mm.v, self.mm.variance
        else:
            # TODO: implement matching and interpolation
            x = match_ordinal(self.pp,self.mm)
            pp, Vpp = interp(x,self.pp)
            mm, Vmm = interp(x,self.mm)
        v = (pp-mm)/(pp+mm)
        V = v**2 * ( (1/(pp-mm) - 1/(pp+mm))**2 * Vpp 
                     + (1/(pp-mm) + 1/(pp+mm))**2 * Vmm )
        result = Data(x,v,variance=V,
                      xlabel=self.xlabel, xunits=self.xunits,
                      vlabel="Spin asymmetry", vunits=None)
        return result

def refl(n=100,noise=0.02):
    """
    Example 1D data: fresnel reflectivity for neutrons off silicon
    n = number of data points
    noise = relative error in simulated data points
    """
    Q = N.linspace(0.,0.5,n)
    dQ = N.ones(Q)*0.001
    f = N.sqrt(Q**2 - 16*N.pi*2.07e-6 + 0j)
    R = N.abs( (Q-f)/(Q+f) )**2
    dR = noise*R
    R = R + dR*N.random.randn(n)
    data = Data(x=Q,dx=dQ,v=R,dv=dR,xlabel='Q',xunits='inv A',vlabel='R')
    return data

def peaks(n=40,noise=0.02):
    """Example 2D data: peaks function"""
    nr,nc = n,n+5
    x = N.linspace(-3,3,nr)
    y = N.linspace(-3,3,nc)
    [X,Y] = N.meshgrid(x,y)
    v = 3*(1-X)**2*N.exp(-X**2 - (Y+1)**2) \
          - 10*(X/5 - X**3 - Y**5)*N.exp(-X**2-Y**2) \
          - 1/3*N.exp(-(X+1)**2 - Y**2)
    v = v + noise*N.random.randn(nc,nr)
    data = Data(x=x,y=y,v=v)
    return data

def noise2d(n=40,noise=0.02,bkg=1e-10):
    """Example 2D data: positive noise"""
    nr,nc = n,n+1
    x = N.linspace(0,1,nr)
    y = N.linspace(0,1,nc)
    v = N.abs(noise*N.random.randn(nc,nr))+bkg
    data = Data(x=x,y=y,v=v)
    return data

def noisepol2d(n=40):
    pp = noise2d(n,noise=0.05)
    pm = noise2d(n,noise=0.3); pm.v *= 0.2;
    mp = noise2d(n,noise=0.3); mp.v *= 0.2;
    mm = noise2d(n,noise=0.05)
    data = PolarizedData()
    data.pp,data.mm = pp,mm
    data.pm,data.mp = pm,mp
    return data

def peakspol(n=40):
    pp = peaks(n,noise=0.05)
    pm = peaks(n,noise=0.3); pm.v *= 0.4;
    mp = peaks(n,noise=0.3); mp.v *= 0.4;
    mm = peaks(n,noise=0.05)
    data = PolarizedData()
    data.pp,data.mm = pp,mm
    data.pm,data.mp = pm,mp
    return data

def demo():
    """Smoke test demo"""
    d = noise2dpol(n=3)
    print "polarized 2D noise:",d
    print "++",d.pp,d.pp.v
    print "--",d.mm,d.mm.v
    print "+-",d.pm,d.pm.v
    print "-+",d.mp,d.mp.v
    print "x,y",d.mp.x,d.mp.y
    print "edges x,y",d.mp.xedges,d.mp.yedges

if __name__ == "__main__": demo()
