# This code is public domain
# Author: Paul Kienzle
"""
Translate coordinates between real and reciprical space.
"""
import numpy
from numpy import sin, cos, pi, arcsin, sqrt, arctan2, degrees, radians


def ABL_to_QxQz(sample_angle, detector_angle, wavelength):
    """
    Compute Qx,Qz given incident and reflected angles and wavelength

    Returns (Qx,Qz)

    If all inputs are scalars the result will be a scalar.
    """
    A,B = sample_angle, detector_angle
    Qz = 2*pi/wavelength * ( sin(radians(B - A)) + sin(radians(A)))
    Qx = 2*pi/wavelength * ( cos(radians(B - A)) - cos(radians(A)))
    return Qx,Qz

def QxQzL_to_AB(Qx, Qz, wavelength):
    """
    Guess incident and reflected angles given Qx, Qz and wavelength.

    This transform is not invertible: for any Qx, Qz there are two
    separate choices for sample angle and detector angle which
    give the same Q.  We choose the one for which detector angle
    matches the sign of Qz.

    Returns sample angle, detector angle

    Sample angle is also called the incident angle, theta_i.
    Dectector angle is incident angle plus reflected angle,
    or theta_i + theta_f.

    If all inputs are scalars the result will be a scalar.

    Error is in the order of 1e-12 for off-specular coordinates.
    """
    # Algorithm for converting Qx-Qz-lambda to alpha-beta:
    #   beta = 2 asin(L/(2 pi) sqrt(Qx^2+Qz^2)/2) * 180/pi
    #        = asin(L/(4 pi) sqrt(Qx^2+Qz^2)) * 360/pi
    #   if Qz < 0, negate beta
    #   theta = atan2(Qx,Qz) * 180/pi
    #   if theta > 90, theta -= 360
    #   alpha = theta + beta/2
    #   if Qz < 0, alpha += 180
    beta = 2*degrees(arcsin(wavelength/(4*pi) * sqrt(Qx**2+Qz**2)))
    beta *= -2*(Qz<0)+1 # -2+1=-1, 0+1=1, so -2*(cond)+1 = +/-1
    theta = degrees(arctan2(Qx,Qz))
    theta -= 360*(theta>90)
    alpha = theta + beta/2
    alpha += 180*(Qz<0)
    return alpha,beta

def QxQzA_to_BL(Qx,Qz,alpha):
    """
    Guess detector angle and wavelength given Qx, Qz and sample angle.

    The detector angle is branch cut between -180 and 180 degrees.

    Returns detector angle, wavelength

    Sample angle is also called the incident angle, theta_i.
    Dectector angle is incident angle plus reflected angle,
    or theta_i + theta_f.

    If all inputs are scalars the result will be a scalar.

    Error is in the order of 1e-12 for off-specular.
    """
    theta = degrees(arctan2(Qx,Qz))
    theta -= 360*(theta>90)
    beta = 2*(alpha-theta)
    beta += 360*(beta<-180)
    beta -= 360*(beta>=180)
    beta -= 360*(beta>=180)
    wavelength = 4*pi*sin(radians(abs(beta))/2) / sqrt(Qx**2 +Qz**2)
    return beta,wavelength

def _errchk(err,tol=1e-15):
    chk = (numpy.abs(err) < tol).all()
    if not chk:
        print err
        print "norm",numpy.linalg.norm(err)
    return chk

def _test1(A,B,L,X,Z):
    msg=", ".join(["%g"%numpy.asarray(v).flatten()[0] for v in A,B,L,X,Z])
    x,z = ABL_to_QxQz(A,B,L)
    mx,mz=["%g"%numpy.asarray(v).flatten()[0] for v in x,z]
    assert _errchk(z-Z),"%s -> %s"%(msg,mz)
    assert _errchk(x-X),"%s -> %s"%(msg,mx)

    a,b2 = QxQzL_to_AB(X,Z,L)
    ma,mb2=["%g"%numpy.asarray(v).flatten()[0] for v in a,b2]

    if numpy.any(Z<0):
        # Full test; make sure the forward transform from the
        # inverted transform is correct even if it doesn't
        # happen to match the choice of detector angle.
        x,z=ABL_to_QxQz(a,b2,L)
        assert _errchk(x-X,1e-12),"incorrect inverse Qx"
        assert _errchk(z-Z,1e-12),"incorrect inverse Qz"
        assert _errchk(numpy.sign(Z)-numpy.sign(b2),1.5),"incorrect branch"
        idx = (numpy.abs(a-A)<1e-12)|(numpy.abs(b2-B)<1e-12)
        if False:
            import pylab
            #print 1*idx
            Bs = B*(1+a-a)
            As = A*(1+a-a)
            pylab.quiver(Bs[~idx],As[~idx],(b2-B)[~idx],(a-A)[~idx])
            pylab.plot(Bs[idx],As[idx],'o')
            pylab.show()
        assert _errchk((A-a)[idx],1e-12),"incorrect sample angle"
        assert _errchk((B-b2)[idx],1e-12),"incorrect detector angle"
    else:
        assert _errchk(b2-B,1e-12),"%s -> %s"%(msg,mb2)
        assert _errchk(a-A,1e-12),"%s -> %s"%(msg,ma)

    b,l = QxQzA_to_BL(X,Z,A)
    mb,ml=["%g"%numpy.asarray(v).flatten()[0] for v in b,l]
    if False and not _errchk(b-B, 1e-12):
        # Debug problems with BL; should be less since results are
        # not ambiguous.
        idx = abs(b-B)>1e-12
        Bs = B*(1+b-b)
        Ls = L*(1+b-b)
        import pylab
        pylab.quiver(Bs[idx],Ls[idx],(b-B)[idx],(l-L)[idx])
        pylab.plot(Bs[~idx],Ls[~idx],'o')
        pylab.plot(Bs[idx],Ls[idx],'o')
        pylab.plot(b[idx],l[idx],'x')
        pylab.show()
    assert _errchk(b-B, 1e-12),"%s -> %s"%(msg,mb)
    assert _errchk(l-L, 1e-12),"%s -> %s"%(msg,ml)



def test():
    A,B,L = 3,6,4.5
    X,Z = 0,4*pi/L*sin(radians(A))
    vec = numpy.ones((2,3,4))

    # Check combos of scalar/vector for Qx=0
    _test1(A,B,L,X,Z)
    _test1(vec*A,B,L,X,Z)
    _test1(A,vec*B,L,X,Z)
    _test1(A,B,vec*L,X,Z)
    _test1(A,B,L,vec*X,Z)
    _test1(A,B,L,X,vec*Z)
    _test1(vec*A,vec*B,vec*L,vec*X,vec*Z)
    _test1(vec[:,0:1,0:1]*A,vec[0:1,:,0:1]*B,vec[0:1,0:1,:]*L,X,Z)

    # Check combos of scalar/vector for Qx!=0
    A,B,L = 3,2,4.5
    ti,tf = radians(A),radians(B-A)
    X,Z = 2*pi/L*(cos(tf)-cos(ti)),2*pi/L*(sin(tf)+sin(ti))
    _test1(A,B,L,X,Z)
    _test1(A,B,vec*L,X,Z)
    _test1(vec*A,B,L,X,Z)
    _test1(A,vec*B,L,X,Z)
    _test1(A,B,vec*L,X,Z)
    _test1(A,B,L,vec*X,Z)
    _test1(A,B,L,X,vec*Z)
    _test1(vec*A,vec*B,vec*L,vec*X,vec*Z)
    _test1(vec[:,0:1,0:1]*A,vec[0:1,:,0:1]*B,vec[0:1,0:1,:]*L,X,Z)

    # Check the whole coordinate space, avoiding Qz=0.
    A = numpy.linspace(-170,170,5).reshape((1,1,5))
    B = numpy.linspace(-170,170,6).reshape((1,6,1))
    L = numpy.linspace(0.1,7.1,4).reshape((4,1,1))
    #L=4
    X,Z = ABL_to_QxQz(A,B,L)
    _test1(A,B,L,X,Z)

if __name__ == "__main__":
    test()
