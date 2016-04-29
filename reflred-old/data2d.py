from reflred.refldata import ReflData
from .limits import Limits

# Ignore the remainder of this file --- I don't yet have the computational
# interface set up.

_ = """
    Computed values
    ===============
    edges_x (metric=['pixel'|'mm'|'degrees'|'radians'],frame=0)
        Returns the nx+1 pixel edges of the detector in the given units.
        In distance units, this is the distance relative to the center
        of the detector arm.
    edges_y (metric=['pixel'|'mm'|'degrees'|'radians'],frame=0)
        Returns the ny+1 pixel edges of the detector in the given units.

    def resolution(self):
        return
    """

# === Interaction with individual frames ===
class Reader(ReflData):
    """
    After loadframes(), *zx* is contains an image in which each frame has
    been summed over the y channels of *roi*, and *xy* contains the sum
    the individual detector frames across all z.
    """
    def __init__(self):
        raise NotImplementedError("Not yet complete")

    def numframes(self):
        """
        Return the number of detector frames available.
        """
        return self.channels*self.points

    def loadframes(self):
        """
        Convert raw frames into a form suitable for display.
        """
        # Hold a reference to the counts so that they are not purged
        # from memory during the load operation.
        zlo,zhi = 0,self.detector.shape[0]-1
        xlo,xhi,ylo,yhi = self.roi
        counts = self.detector.counts
        nq = zhi-zlo+1
        nx = xhi-xlo+1
        ny = yhi-ylo+1
        if ny == 1:
            self.zx = counts[zlo:zhi+1,xlo:xhi+1]
        else:
            xy = np.zeros((nx,ny),dtype='float32')
            zx = np.zeros((nq,nx),dtype='float32')
            self.frame_range = Limits() # Keep track of total range
            for i in range(zlo,zhi):
                v = self.frame(i)
                self.frame_range.add(v,dv=sqrt(v))
                xy += v
                zx[i-zlo,:] = np.sum(v[xlo:xhi,ylo:yhi],axis=1)
            self.xy = xy
            self.zx = zx

    def frame(self,index):
        """
        Return the 2-D detector frame for the given index k.  For
        multichannel instruments, index is the index for the channel
        otherwise index is the measurement number.

        The result is undefined if the detector is not a 2-D detector.
        """
        if self.channels > 1:
            return self.detector.counts[:,index]
        else:
            return self.detector.counts[index,:]



def shadow(f, beamstop, frame):
    """
    Construct a mask for the detector frame indicating which pixels
    are outside the shadow of the beamstop.  This pixels should not
    be used when estimating sample background.  Note that this becomes
    considerably more tricky when angular divergence and gravity
    are taken into account.  The mask should include enough of the
    penumbra that these effects can be ignored.

    Currently this function returns no shadow.
    """
    mask = np.ones(f.detector.shape,'int8')
    if beamstop.ispresent:
        # calculate location of the beamstop centre relative to
        # the detector.
        raise NotImplementedError("beamstop shadow is not implemented")
        pass
    return mask
