"""
Program to explore the beam profile and angular distribution for a simple
reflectometer with two front slits.
"""

from __future__ import division, print_function

import sys
import os

import numpy as np
from numpy import (sin, cos, tan, arcsin, arccos, arctan, arctan2, radians, degrees,
                   sign, sqrt, exp, log, std)
from numpy import pi, inf
import pylab

#from .nice import Instrument, Motor


# dimensions in millimeters
MONOCHROMATOR_Z = -5216.5
SOURCE_APERTURE_Z = -4600. # TODO: missing this number
SOURCE_APERTURE = 60.
SOURCE_LOUVER_Z = -4403.026
SOURCE_LOUVER_N = 4
SOURCE_LOUVER_SEPARATION = 15.5  # center-center distance for source multi-slits
SOURCE_LOUVER_MAX = 14.5  # maximum opening for source multi-slit
SOURCE_SLIT_Z = -4335.86
PRE_SAMPLE_SLIT_Z = -356.0
POST_SAMPLE_SLIT_Z = 356.0
DETECTOR_MASK_Z = 3496.
DETECTOR_MASK_HEIGHT = 30.
DETECTOR_MASK_WIDTHS = [10., 8., 6., 4.]
DETECTOR_MASK_N = 30
DETECTOR_MASK_SEPARATION = 12.84

WAVELENGTH_MIN = 4.
WAVELENGTH_MAX = 6.
WAVELENGTH_N = 54

SOURCE_LOUVER_CENTERS = np.linspace(-1.5*SOURCE_LOUVER_SEPARATION,
                                    1.5*SOURCE_LOUVER_SEPARATION,
                                    SOURCE_LOUVER_N)
SOURCE_LOUVER_ANGLES = np.arctan2(SOURCE_LOUVER_CENTERS, -SOURCE_LOUVER_Z)


def detector_mask(mask=0):
    """
    Return slit edges for candor detector mask.
    """
    edges = comb(n=DETECTOR_MASK_N,
                 width=DETECTOR_MASK_WIDTHS[mask],
                 separation=DETECTOR_MASK_SEPARATION)
    # Every 3rd channel is dead (used for cooling)
    edges = edges.reshape(-1, 3, 2)[:, :2, :].flatten()
    return edges

def choose_sample_slit(louver, sample_width, sample_angle):
    theta = radians(sample_angle)
    index = np.nonzero(louver)[0]
    k = index[-1]
    x0, y0 = SOURCE_LOUVER_Z, SOURCE_LOUVER_CENTERS[k] + louver[k]/2
    x1, y1 = sample_width/2*cos(theta), sample_width/2*sin(theta)
    top = (y1-y0)/(x1-x0)*(PRE_SAMPLE_SLIT_Z - x1) + y1
    k = index[0]
    x0, y0 = SOURCE_LOUVER_Z, SOURCE_LOUVER_CENTERS[k] - louver[k]/2
    x1, y1 = -sample_width/2*cos(theta), -sample_width/2*sin(theta)
    bottom = (y1-y0)/(x1-x0)*(PRE_SAMPLE_SLIT_Z - x1) + y1
    #print(top, bottom)
    #slit = 2*max(top, -bottom)
    slit = 2*max(abs(top), abs(bottom))
    return slit

def load_spectrum():
    """
    Return the incident spectrum
    :return:
    """
    datadir = os.path.abspath(os.path.dirname(__file__))
    L, Iin = np.loadtxt(os.path.join(datadir, 'CANDOR-incident.dat')).T
    _, Iout = np.loadtxt(os.path.join(datadir, 'CANDOR-detected.dat')).T
    return np.vstack((L, Iin, Iout/Iin))

def candor_wavelength_dispersion(L, mask=10., detector_distance=DETECTOR_MASK_Z):
    """
    Return estimated wavelength dispersion for the candor channels.

    *L* (Ang) is the wavelength measured for each channel.

    *mask* (mm) is the mask opening at the start of each detector channel.

    *detector_distance* (mm) is the distance from the center of the sample
    to the detector mask.

    Note: result is 0.01% below the value shown in Fig 9 of ref.

    **References**

    Jeremy Cook, "Estimates of maximum CANDOR detector count rates on NG-1"
    Oct 27, 2015
    """
    #: (Ang) d-spacing for graphite (002)
    dspacing = 3.354

    #: (rad) FWHM mosaic spread for graphite
    eta = radians(30./60.)  # convert arcseconds to radians

    #: (rad) FWHM incident divergence
    a0 = mask/detector_distance

    #: (rad) FWHM outgoing divergence
    a1 = a0 + 2*eta

    #: (rad) bragg angle for wavelength selector
    theta = arcsin(L/2/dspacing)
    #pylab.plot(degrees(theta))

    #: (unitless) FWHM dL/L, as given in Eqn 6 of the reference
    dLoL = (sqrt((a0**2*a1**2 + (a0**2 + a1**2)*eta**2)/(a0**2+a1**2+4*eta**2))
            / tan(theta))
    return dLoL

def plot_dLoL():
    spectrum = load_spectrum()
    L = spectrum[0]
    crystal = np.arange(1, 55)
    pylab.plot(crystal, 100*candor_wavelength_dispersion(L, 10), label="10 mm")
    pylab.plot(crystal, 100*candor_wavelength_dispersion(L, 8), label="8 mm")
    pylab.plot(crystal, 100*candor_wavelength_dispersion(L, 6), label="6 mm")
    pylab.plot(crystal, 100*candor_wavelength_dispersion(L, 4), label="4 mm")
    pylab.legend()
    pylab.xlabel("crystal #")
    pylab.ylabel(r"$\Delta\lambda/\lambda$ (FWHM) %")
    pylab.title("CANDOR wavelength dispersion")
    pylab.grid()

def plot_channels(mask=10.):
    spectrum = load_spectrum()
    L = spectrum[0]
    dL = L*candor_wavelength_dispersion(L, mask)/2.35
    x = np.linspace(4,6,10000)
    y = [exp(-0.5*(x - Li)**2/dLi**2) for Li, dLi in zip(L,dL)]
    #pylab.plot(x, np.vstack(y).T)
    pylab.plot(x, np.sum(np.vstack(y),axis=0))
    pylab.grid(True)

if False:
    #plot_dLoL()
    plot_channels(10)
    pylab.show()
    sys.exit()

def pairwise(iterable):
    "s -> (s0, s1), (s2, s3), (s4, s5), ..."
    a = iter(iterable)
    return zip(a, a)

def rotate(xy, theta):
    """
    Rotate points x,y through angle theta.
    """
    sin_theta, cos_theta = sin(theta), cos(theta)
    R = np.array([[cos_theta, -sin_theta],[sin_theta, cos_theta]])
    return np.dot(R, xy)

def comb(n, width, separation):
    """
    Return bin edges with *n* bins.

    *separation* is the distance between bin centers and *width* is the
    size of each bin.
    """
    # Form n centers from n-1 intervals between centers, with
    # center-to-center spacing set to separation.  This puts the
    # final center at (n-1)*separation away from the first center.
    # Divide by two to arrange these about zero, giving (-limit, limit).
    # Edges are +/- width/2 from the centers.
    limit = separation*(n-1)/2
    centers = np.linspace(-limit, limit, n)
    edges = np.vstack([centers-width/2, centers+width/2]).T.flatten()
    return edges

class Neutrons(object):
    #: angle of the x-axis relative to source-sample line (rad)
    beam_angle = 0.
    #: x,y position of each neutron, with 0,0 at the center of rotation (mm)
    xy = None # type: np.ndarray
    #: direction of travel relative to beam (radians)
    angle = None # type: np.ndarray
    #: neutron wavelength (Angstroms)
    wavelength = None # type: np.ndarray
    #: relative intensity of individual neutrons, which depends on spectral
    #: weight, the percentage transmitted/reflected, and the percentage
    #: detected relative to incident.
    weight = None # type: np.ndarray
    #: set of neutrons masked by slits
    active = None  # type: np.ndarray
    #: 54 x 3 array of lambda, incident intensity (n/cm^2), detected intensity
    spectrum = None # type: np.ndarray
    #: sample angle if there is a sample in the beam
    sample_angle = 0.
    #: source beam for each neutron
    source = None # type: np.ndarray

    @property
    def x(self):
        return self.xy[1]
    @x.setter
    def x(self, v):
        self.xy[1] = v

    @property
    def z(self):
        return self.xy[0]
    @z.setter
    def z(self, v):
        self.xy[0] = v

    def __init__(self, n, divergence=5., spectrum=None, trace=False):
        # type: (int, float, np.ndarray, float, Union[float, np.ndarray], bool) -> None
        self.spectrum = spectrum
        L, I, _ = spectrum
        Lmin, Lmax = np.min(L), np.max(L)
        Iweighted = I/np.sum(I)

        self.xy = np.zeros((2,n),'d')
        self.angle = (np.random.rand(n)-0.5)*radians(divergence)
        self.wavelength = np.random.rand(n)*(Lmax - Lmin) + Lmin
        self.weight = np.interp(self.wavelength, L, Iweighted)
        self.active = (self.x == self.x)

        self.history = []
        self.trace = trace
        self.elements = []

    def slit_source(self, z, width):
        n = self.xy.shape[1]
        self.z = z
        self.x = (np.random.rand(n)-0.5)*width
        # Aim the center of the divergence at the pre-sample slit position
        # rather than the sample position
        #self.angle += arctan(self.x/self.z)
        self.angle += arctan(self.x/(self.z - PRE_SAMPLE_SLIT_Z))
        self.source = 0
        self.add_trace()
        self.add_element((z, -width), (z, -width/2))
        self.add_element((z, width/2), (z, width))

    def comb_source(self, z, widths, separation):
        n = self.xy.shape[1]
        num_slits = len(widths)
        limit = separation*(num_slits-1)/2
        centers = np.linspace(-limit, limit, num_slits)
        edges = np.vstack([centers-widths/2, centers+widths/2]).T.flatten()
        break_points = np.cumsum(widths) + edges[0]
        total_width = break_points[-1] - edges[0]
        spaces = np.diff(edges)[1::2]
        shift = np.hstack([0, np.cumsum(spaces)])
        x = edges[0] + np.random.rand(n)*total_width
        index = np.searchsorted(break_points[:-1], x)
        self.source = index
        self.z = z
        self.x = x + shift[index]
        # Aim the center of the divergence at the pre-sample slit position
        # rather than the sample position
        self.angle += arctan(self.x/(self.z - PRE_SAMPLE_SLIT_Z))
        #self.angle += arctan(self.x/self.z)
        #self.angle -= SOURCE_LOUVER_ANGLES[index]
        self.add_trace()
        self.add_element((z, edges[0]-widths[0]/2), (z, edges[0]))
        for x1, x2 in pairwise(edges[1:-1]):
            self.add_element((z, x1), (z, x2))
        self.add_element((z, edges[-1]), (z, edges[-1]+widths[-1]/2))

    def trim(self):
        self.xy = self.xy[:,self.active]
        self.angle = self.angle[self.active]
        self.wavelength = self.wavelength[self.active]
        self.weight = self.weight[self.active]
        self.active = self.active[self.active]
        if self.source is not None:
            self.source = self.source[self.active]
        self.add_trace()

    def add_element(self, zx1, zx2):
        self.elements.append((rotate(zx1, -self.beam_angle),
                              rotate(zx2, -self.beam_angle)))
    def add_trace(self):
        if self.trace:
            self.history.append((rotate(self.xy, -self.beam_angle),
                                 self.active&True))

    def clear_trace(self):
        self.history = []

    def plot_trace_old(self, split=False):
        from matplotlib.lines import Line2D
        colors = 'rgby'
        for k, (zx, active) in enumerate(self.history[:-1]):
            zx_next, active_next = self.history[k+1]
            if active.shape != active_next.shape: continue
            z = np.vstack((zx[0], zx_next[0]))
            x = np.vstack((zx[1], zx_next[1]))
            # TODO: source will be the wrong length after trim
            for k, c in enumerate(colors):
                index = active & (self.source == k)
                if index.any():
                    if split:
                        pylab.subplot(2,2,k+1)
                    pylab.plot(z[:,index], x[:,index], '-', color=c, linewidth=0.1)

        entries = []
        for k, c in enumerate(colors):
            angle = degrees(SOURCE_LOUVER_ANGLES[k]) + self.sample_angle
            label = '%.3f degrees'%angle
            if split:
                pylab.subplot(2,2,k+1)
                pylab.title(label)
            else:
                line = Line2D([],[],color=c,marker=None,
                              label=label, linestyle='-')
                entries.append(line)
        if not split:
            pylab.legend(handles=entries, loc='best')
        #pylab.axis('equal')

        # draw elements, cutting slits off at the bounds of the data
        if split:
            for k, c in enumerate(colors):
                #pylab.axis('equal')
                #pylab.grid(True)
                pylab.subplot(2,2,k+1)
                for (z1, x1), (z2, x2) in self.elements:
                    pylab.plot([z1, z2], [x1, x2], 'k')
        else:
            #pylab.axis('equal')
            #pylab.grid(True)
            for (z1, x1), (z2, x2) in self.elements:
                pylab.plot([z1, z2], [x1, x2], 'k')

    def angle_hist(self):
        from scipy.stats import gaussian_kde
        pylab.figure(2)
        active_angle = self.angle[self.active] if self.active.any() else self.angle
        angles = degrees(active_angle) + self.sample_angle
        if 0:
            n = len(angles)
            x = np.linspace(angles.min(), angles.max(), 400)
            mu, sig = angles.mean(), angles.std()
            pdf = gaussian_kde((angles-mu)/sig, bw_method=0.001*n**0.2)
            pylab.plot(x, pdf(x)*sig + mu)
        else:
            pylab.hist(angles, bins=50, normed=True)
        pylab.xlabel('angle (degrees)')
        pylab.ylabel('P(angle)')
        pylab.figure(1)

    def plot_trace(self, split=None):
        from matplotlib.collections import LineCollection
        import matplotlib.colors as mcolors
        import matplotlib.cm as mcolormap

        active_angle = self.angle[self.active] if self.active.any() else self.angle
        active_angle = degrees(active_angle) + self.sample_angle
        vmin, vmax = active_angle.min(), active_angle.max()
        vpad = 0.05*(vmax-vmin)
        cnorm = mcolors.Normalize(vmin=vmin-vpad, vmax=vmax+vpad)
        cmap = mcolormap.ScalarMappable(norm=cnorm, cmap=pylab.get_cmap('jet'))
        #colors = cmap.to_rgba(degrees(self.angle) + self.sample_angle)
        colors = cmap.to_rgba(active_angle)
        for k, (zx, active) in enumerate(self.history[:-1]):
            zx_next, active_next = self.history[k+1]
            if active.shape != active_next.shape:
                continue
            if active.any():
                segs = np.hstack((zx[:, active].T, zx_next[:, active].T))
                segs = segs.reshape(-1, 2, 2)
                lines = LineCollection(segs, linewidth=0.1,
                                       linestyle='solid', colors=colors[active])
                pylab.gca().add_collection(lines)
                #pylab.plot(z[:,index], x[:,index], '-', color=c, linewidth=0.1)

        # draw elements, cutting slits off at the bounds of the data
        #pylab.axis('equal')
        #pylab.grid(True)
        for (z1, x1), (z2, x2) in self.elements:
            pylab.plot([z1, z2], [x1, x2], 'k')
        cmap.set_array(active_angle)
        h = pylab.colorbar(cmap)
        h.set_label('angle (degrees)')

    def plot_points(self):
        x, y = rotate(self.xy, -self.beam_angle)
        pylab.plot(x, y, '.')

    def detector_angle(self, angle):
        """
        Set the detector angle
        """
        self.rotate_rad(-radians(angle))

    def radial_collimator(self, z, n, w1, w2, length):
        raise NotImplementedError()

    def rotate_rad(self, angle):
        """
        Rotate the coordinate system through *angle*.
        """
        self.beam_angle += angle
        self.xy = rotate(self.xy, angle)
        self.angle += angle

    def move(self, z):
        """
        Move neutrons to position z.
        """
        # Project neutrons onto perpendicular plane at the sample position
        dz = z - self.z
        self.x = dz*tan(self.angle) + self.x
        self.z = z

    def sample(self, angle, width=100., offset=0., bow=0.):
        """
        Reflect off the sample.

        *angle* (degrees) is the angle of the sample plane relative
        to the beam.

        *width* (mm) is the width of the sample.

        *offset* (mm) is the offset of the sample from the center of rotation.

        *bow* (mm) is the amount of bowing in the sample, which is
        the height of the sample surface relative at the center of the
        sample relative to the edges. *bow* is positive for samples that
        are convex and negative for concave.
        """
        theta = radians(angle)

        # Determine where the neutrons intersect the plane through the
        # center of sample rotation (i.e., move them to z = 0)
        x = self.x - self.z * tan(self.angle)

        # Intersection of sample plane with individual neutrons
        # Note: divide by zero where self.angle == theta
        if theta == 0:
            xp = np.zeros_like(self.x)
            zp = self.z - self.x / tan(self.angle)
        else:
            xp = tan(theta) * x / (tan(theta) - tan(self.angle))
            zp = xp / tan(theta)

        # Find the location on the sample plane of the intercepted neutron.
        # The sample goes from (-w/2 - offset, w/2 - offset).  Anything with
        # position in that range has hit the sample.
        s = 2*(xp>=0)-1
        p = s*sqrt(xp**2 + zp**2) - offset
        #print("sample position", p)
        hit = (abs(p) < width/2.)

        # Update the position of the neutrons which hit the sample
        self.angle[hit] = 2*theta - self.angle[hit]
        self.x[hit] = xp[hit]
        self.z[hit] = zp[hit]
        # Move the remaining neutrons to position 0
        self.x[~hit] = x[~hit]
        self.z[~hit] = 0
        self.sample_angle = angle
        self.add_trace()

        # sample is shifted along the z axis and then rotated by theta
        z1, x1 = rotate((-width/2+offset, 0), theta)
        z2, x2 = rotate((width/2+offset, 0), theta)
        self.add_element((z1, x1), (z2, x2))

    def slit(self, z, width, offset=0.):
        """
        Send
        :param width:
        :return:
        """
        self.move(z)
        self.active &= (self.x >= -width/2+offset)
        self.active &= (self.x <= +width/2+offset)
        self.add_trace()
        self.add_element((z, -width+offset), (z, -width/2+offset))
        self.add_element((z, +width/2+offset), (z, width+offset))

    def comb_filter(self, z, n, width, separation):
        """
        Filter the neutrons through an *n* element comb filter.

        *width* is the filter opening and *separation* is the distance between
        consecutive openings. *width* can be a vector of length *n* if
        each opening is controlled independently.  The spacing between
        the centers is fixed.
        """
        self.move(z)
        self.slit_array(z, comb(n, width, separation))

    def slit_array(self, z, edges):
        # Searching the neutron x positions in the list of comb edges
        # gives odd indices if they go through the edges, and even indices
        # if they encounter the edges of the comb.
        index = np.searchsorted(edges, self.x)
        self.active &= (index%2 == 1)
        self.add_trace()
        self.add_element((z, 2*edges[0]-edges[1]), (z, edges[0]))
        for x1, x2 in pairwise(edges[1:-1]):
            self.add_element((z, x1), (z, x2))
        self.add_element((z, edges[-1]), (z, 2*edges[-1]-edges[-2]))

    def reflect(self, q, r, sample_angle):
        # type: (np.ndarray, np.ndarray, float) -> Neutron
        """
        Interpolate neutrons in packet into the R(q) curve assuming specular
        reflectivity.

        Returns a weight associated with each neutron, which is the predicted
        reflectivity.
        """
        qk = 4.*pi*sin(radians(self.angle+sample_angle))/self.wavelength
        rk = np.interp(qk, q, r)
        self.weight *= rk
        return self

def source_divergence(source_slit_z, source_slit_w,
                      sample_slit_z, sample_slit_w,
                      detector_slit_z, detector_slit_w,
                      sample_width, sample_offset,
                      sample_angle, detector_angle,
                     ):
    def angle(p1, p2):
        return arctan2(p2[1]-p1[1], p2[0]-p1[0])
    theta = radians(sample_angle)
    two_theta = radians(detector_angle)
    # source edgess
    source_lo = source_slit_z, -0.5*source_slit_w
    source_hi = source_slit_z, +0.5*source_slit_w
    # pre-sample slit edges
    pre_lo = angle(source_hi, (sample_slit_z, -0.5*sample_slit_w))
    pre_hi = angle(source_lo, (sample_slit_z, +0.5*sample_slit_w))
    # sample edges (after rotation and shift)
    r_lo = -0.5*sample_width + sample_offset
    r_hi = +0.5*sample_width + sample_offset
    sample_lo = angle(source_hi, (arccos(theta)*r_lo, arcsin(theta)*r_lo))
    sample_hi = angle(source_lo, (arccos(theta)*r_hi, arcsin(theta)*r_hi))
    # post-sample slit edges (after rotation)
    alpha = arctan2(0.5*detector_slit_w, detector_slit_z)
    beta_lo = two_theta - alpha
    beta_hi = two_theta + alpha
    r = sqrt(detector_slit_z**2 + 0.25*detector_slit_w**2)
    post_lo = angle(source_hi, (arccos(beta_lo)*r, arcsin(beta_lo)*r))
    post_hi = angle(source_lo, (arccos(beta_hi)*r, arcsin(beta_hi)*r))

    max_angle = max(pre_hi, min(sample_hi, post_hi))
    min_angle = min(pre_lo, max(sample_lo, post_lo))
    return max(abs(max_angle), abs(min_angle))

def single_point_demo(theta=2.5, count=150, trace=True, plot=True, split=False):
    source_slit = 3.  # narrow beam
    #source_slit = 50.  # wide beam
    #source_slit = 150.  # super-wide beam
    #sample_width, sample_offset = 100., 0.
    sample_width, sample_offset, source_slit = 2., 0., 0.02
    min_sample_angle = theta
    #mask = 0 # 10 mm detector
    mask = 3 # 4 mm detector

    comb_z = -1000
    comb_separation = SOURCE_LOUVER_SEPARATION*comb_z/SOURCE_LOUVER_Z
    comb_max = comb_separation - 1.
    comb_min = 0.1

    #sample_angle = min_sample_angle - degrees(SOURCE_LOUVER_ANGLES[0])
    sample_angle = min_sample_angle
    detector_angle = 2*sample_angle
    louver = (radians(sample_angle) + SOURCE_LOUVER_ANGLES)*sample_width
    louver = abs(louver)

    louver = np.maximum(np.minimum(louver, comb_max), comb_min)
    comb_width = louver

    sample_slit = choose_sample_slit(louver, sample_width, sample_angle)
    sample_slit_offset = 0.
    #sample_slit *= 0.2
    sample_slit = sample_width*sin(radians(sample_angle))

    # Convergent guides remove any effects of slit collimation, and so are
    # equivalent to sliding the source toward the sample
    source_slit_z = SOURCE_SLIT_Z  # no guides
    source_slit_z = PRE_SAMPLE_SLIT_Z - 10  # converent guides

    # Enough divergence to cover the presample slit from the source aperture
    # Make sure we get the direct beam as well.
    divergence = degrees(arctan(sample_slit/abs(source_slit_z-PRE_SAMPLE_SLIT_Z)))
    #print("divergence", divergence)
    #divergence = 5

    #detector_slit = sample_slit
    #detector_slit = 3*sample_slit
    detector_slit = sample_slit + (POST_SAMPLE_SLIT_Z - PRE_SAMPLE_SLIT_Z)*tan(radians(divergence))

    #louver[1:3] = 0.
    #sample_slit = louver[0]*2
    #sample_slit_offset = SOURCE_LOUVER_CENTERS[0]*PRE_SAMPLE_SLIT_Z/SOURCE_LOUVER_Z  # type: float

    delta_theta = source_divergence(source_slit_z, source_slit,
                      PRE_SAMPLE_SLIT_Z, sample_slit,
                      POST_SAMPLE_SLIT_Z, detector_slit,
                      sample_width, sample_offset,
                      sample_angle, detector_angle,
                      )

    spectrum = load_spectrum()
    n = Neutrons(n=count, trace=trace, spectrum=spectrum, divergence=delta_theta)
    if False:
        n.comb_source(SOURCE_LOUVER_Z, louver, SOURCE_LOUVER_SEPARATION)
    else:
        n.slit_source(source_slit_z, source_slit)
        #n.slit_source(PRE_SAMPLE_SLIT_Z-10, sample_slit)

    if False:
        n.comb_filter(z=comb_z, n=SOURCE_LOUVER_N, width=comb_width,
                      separation=comb_separation)

    n.slit(z=PRE_SAMPLE_SLIT_Z, width=sample_slit, offset=sample_slit_offset)
    #n.plot_trace(); return
    if 1:
        n.sample(angle=sample_angle, width=sample_width, offset=sample_offset)
    #else:
    #    n.move(z=0.)
    #    n.add_trace()
    n.detector_angle(angle=detector_angle)
    #n.clear_trace()
    n.slit(z=POST_SAMPLE_SLIT_Z, width=detector_slit, offset=sample_slit_offset)
    if False:
        n.comb_filter(z=-comb_z, n=SOURCE_LOUVER_N, width=comb_width,
                      separation=comb_separation)
    n.move(z=DETECTOR_MASK_Z)
    n.add_trace()
    n.slit_array(z=DETECTOR_MASK_Z, edges=detector_mask(mask=mask))
    n.move(z=DETECTOR_MASK_Z+1000)
    n.add_trace()
    #n.angle_hist()

    if plot:
        n.plot_trace(split=split)
        pylab.xlabel('z (mm)')
        pylab.ylabel('x (mm)')
        pylab.title('sample width=%g'%sample_width)
        #pylab.axis('equal')


def scan_demo(count=100):
    pylab.subplot(2, 2, 1)
    single_point_demo(0.5, count)
    pylab.subplot(2, 2, 2)
    single_point_demo(1.0, count)
    pylab.subplot(2, 2, 3)
    single_point_demo(1.7, count)
    pylab.subplot(2, 2, 4)
    single_point_demo(2.5, count)

def resolution_simulator():
    # s1, s2 are slit openings
    # theta is sample angle
    # width is sample width
    # offset is sample offset from center (horizontal)
    # beam_height is the vertical size of the beam; this is used to compute
    # the beam spill from sample disks, the effects of which can be reduced
    # by setting the beam height significantly below the disk width.

    ## Variants
    d1, d2 = SOURCE_SLIT_Z, PRE_SAMPLE_SLIT_Z
    beam_height = 8
    width=10
    #offset = -2.
    offset = 0
    theta = 3.5
    s1, s2 = .5, .5
    #s1, s2 = 5, 5
    #s1, s2 = 0.15, 0.10 # different slits
    #s1, s2 = 0.05, 0.10  # different slits
    #s1, s2, theta = 0.5, 0.5, 3.5  # far out
    #s1, s2, width = 0.1, 0.01, 4 # extreme slits
    #s1, s2 = 0.1, 0.2 # extreme slits
    #s1, s2 = 0.01, 0.1 # extreme slits

    # number of samples
    n = 1000000

    # use radians internally
    theta = radians(theta)

    # Maximum angle for any neutron is found by looking at the triangle for a
    # neutron entering at the bottom of slit 1 and leaving at the top of slit 2.
    # Simple trig gives the maximum angle we need to consider, with spread going
    # from negative of that angle to positive of that angle.  Assume all starting
    # positions and all angles are equiprobable and generate neutrons at angle
    # phi starting at position x1.
    spread = 2*arctan(0.5*(s1+s2)/(d2-d1))
    x1 = np.random.uniform(-s1/2, s1/2, size=n)
    phi = np.random.uniform(-spread/2, spread/2, size=n)

    # Determine where the neutrons intersect slit 2; tag those that make it through
    # the slits
    x2 = (d2-d1)*tan(phi) + x1
    through = (x2 > -s2/2) & (x2 < s2/2)
    n_through = np.sum(through)

    # Determine where the neutrons intersect the plane through the center of sample
    # rotation
    xs = -d1*tan(phi) + x1

    # Intersection of sample with individual neutrons
    def intersection(theta, phi, xs):
        xp = tan(theta) * xs / (tan(theta) - tan(phi))
        zp = xp / tan(theta)
        return xp, zp
    xp, zp = intersection(theta, phi, xs)

    # Find the location on the sample plane of the intercepted neutron.  Note that
    # this may lie outside the bounds of the sample, so check that it lies within
    # the sample.  The sample goes from (-w/2 - offset, w/2 - offset)
    z = sign(xp)*sqrt(xp**2 + zp**2) - offset
    hit = through & (abs(z) < width/2.)
    n_hit = np.sum(hit)

    # If phi > theta then the neutron must have come in from the back.  If it
    # hits the sample as well, then we need to deal with refraction (if it hits
    # the side) or reflection (if it is low angle and not transmitted).  Let's
    # count the number that hit the back of the sample.
    n_backside = np.sum((phi > theta)[hit])

    # For disk-shaped samples, weight according to chord length.  That is, for a
    # particular x position on the sample, r^2 = x^2 + y^2, chord length is 2*y.
    # Full intensity will be at the sample width, 2*r.
    # Ratio w = (r^2 - x^2)/r^2 = 1 - (x/r)^2.
    w = 1 - (2*z/width)**2
    # For ribbon beams (limited y), the total beam intensity only drops when
    # the ribbon width is greater than the chord length.  Rescale the chord
    # lengths to be relative to the beam height rather than the sample diameter
    # and clip anything bigger than one.  If the beam height is bigger than
    # the sample width, this will lead to beam spill even at the center.
    # Note: Could do the same for square samples.
    if np.isfinite(beam_height):
        w *= width/beam_height
        w[w>1] = 1
    #w = 1 - (np.minimum(abs(2*z), beam_height)/min(width, beam_height))**2
    w[w<0] = 0.
    weight = sqrt(w)
    n_hit_disk = np.sum(hit*weight)

    # End points of the sample
    sz1,sx1 = (-width/2+offset)*cos(theta), (-width/2+offset)*sin(theta)
    sz2,sx2 = (+width/2+offset)*cos(theta), (+width/2+offset)*sin(theta)

    # Simplified intersection: sample projects onto sample position
    hit_proj = through & (xs > sx1) & (xs < sx2)
    n_hit_proj = np.sum(hit_proj)

    # Simplified disk intersection: weight by the projection of the disk
    z_proj = xs / sin(theta) - offset
    w = 1 - (2*z_proj/width)**2
    w[w<0] = 0.
    weight_proj = sqrt(w)
    n_hit_disk_proj = np.sum(hit_proj*weight_proj)

    # beam profile is a trapezoid, 0 where a neutron entering at -s1/2 just
    # misses s2/2, and 1 where a neutron entering at s1/2 just misses s2/2.
    h1 = abs(d1/(d1-d2))*(s1+s2)/2 - s1/2
    h2 = abs(-abs(d1/(d1-d2))*(s1-s2)/2 + s1/2)
    profile = [-h1, -h2, h2, h1], [0, 1, 1, 0]

    # Compute divergence from slits and from sample
    def fwhm2sigma(s):
        return s/sqrt(8*log(2))  # gaussian
        #return s*sqrt(2/9.)       # triangular
    dT_beam = fwhm2sigma(degrees(0.5*(s1+s2)/abs(d1-d2)))
    dT_s1_sample = fwhm2sigma(degrees(0.5*(s1+width*sin(theta))))
    dT_s2_sample = fwhm2sigma(degrees(0.5*(s2+width*sin(theta))))

    dT_sample = min([dT_beam, dT_s1_sample, dT_s2_sample])
    dT_est = degrees(std(phi[hit]))
    # use resample to estimate divergence from disk-shaped sample
    resample = np.random.choice(phi[hit],p=weight[hit]/np.sum(weight[hit]),size=1000000)
    dT_disk = degrees(std(resample))

    # Hits on z_proj should match hits directly on z
    hit_proj_z = through & (abs(z_proj) < width/2.)
    assert (hit_proj == hit_proj_z).all()

    # Bins to use for intensity vs. position x at the center of rotation
    # The scale factor for the estimated counts comes from setting the
    # area of the beam trapezoid to the total number of neutrons that pass
    # through slit 2.  One should also be able to estimate this by integrating
    # the intensity at each point xs in bin k from its contribution from points
    # at x1, decreased over the distance d1 by the angular spread, but I couldn't
    # work out the details properly.
    bins = np.linspace(min(xs[through]),max(xs[through]),51)
    scale = (bins[1]-bins[0])*n_through/(h1+h2)
    beam = np.interp(bins, profile[0], profile[1], left=0, right=0) * scale
    rect = np.interp(bins, [sx1, sx2], [1, 1], left=0, right=0) * beam
    bins_z = bins / sin(theta) - offset
    bins_w = 1 - (2*bins_z/width)**2
    bins_w[bins_w < 0] = 0.
    disk = sqrt(bins_w) * beam

    phi_bins = degrees(np.linspace(min(phi[through]),max(phi[through]),51))
    phi_max = degrees(arctan(0.5*(s1+s2)/abs(d1-d2)))
    phi_flat = degrees(arctan(0.5*abs((s1-s2)/(d1-d2))))
    phi_scale = n_through/(phi_max+phi_flat)*(phi_bins[1]-phi_bins[0])
    def trapezoidal_variance(a, b):
        """
        Variance of a symmetric trapezoidal distribution.

        The trapezoid slopes up in (-b, -a), is flat in (-a, a) and slopes
        down in (a, b).
        """
        tails = (b-a)/6*(3*a**2 + 2*a*b + b**2)
        flat = (2/3)*a**3
        return (tails + flat)/(a+b)
    def trapezoidal_divergence(s1, s2, d1, d2):
        phi_max = degrees(arctan(0.5*(s1+s2)/abs(d1-d2)))
        phi_flat = degrees(arctan(0.5*abs(s1-s2)/abs(d1-d2)))
        return sqrt(trapezoidal_variance(phi_flat, phi_max))
    dT_beam_trap = sqrt(trapezoidal_variance(phi_flat, phi_max))
    dT_beam_est = np.std(degrees(phi[through]))

    print("spread: %f deg" % degrees(spread))
    print("acceptance: %.2f%%" % (n_through*100./n))
    print("footprint: %.2f%%, disk: %.2f%%" % (100*n_hit/n_through, 100*n_hit_disk/n_through))
    print("projection: %.2f%%, disk: %.2f%%" % (100*n_hit_proj/n_through, 100*n_hit_disk_proj/n_through))
    print("backside: %.2f%%" % (n_backside*100./n_through))
    print("dT beam: traditional %f  trapezoidal %f  estimated %f" % (dT_beam, dT_beam_trap, dT_beam_est))
    print("dT sample: %f  est: %f  disk: %f" % (dT_sample, dT_est, dT_disk))


    from pylab import subplot, hist, plot, legend, grid, show, xlabel

    subplot(221)
    #hist(xs[through], bins=bins, label="beam"); xlabel("x (mm)")
    #plot(bins, beam, '-r', label="_")
    #hist(x2, bins=bins, label="x2", alpha=0.5)
    #hist(xs, bins=bins, label="xs", alpha=0.5)
    hist(degrees(phi[through]), bins=phi_bins, label="beam"); xlabel("phi (deg)")
    plot([-phi_max, -phi_flat, phi_flat, phi_max], [0, phi_scale, phi_scale, 0], '-r', label="_")
    grid(True); legend()
    subplot(223)
    #hist(xs[hit], bins=bins, label="sample"); xlabel("x (mm)")
    #plot(bins, rect, '-r', label="_")
    hist(degrees(phi[hit]), bins=phi_bins, label="sample"); xlabel("phi (deg)")
    grid(True); legend()
    subplot(224)
    #hist(xs[hit], bins=bins, weights=weight[hit], label="disk"); xlabel("x (mm)")
    #plot(bins, disk, '-r', label="_")
    hist(degrees(phi[hit]), bins=phi_bins, weights=weight[hit], label="disk"); xlabel("phi (deg)")
    grid(True); legend()
    subplot(222)
    if False:  # plot collision points
        plot(zp[hit][:1000], xp[hit][:1000], '.')
        plot(zp[through&~hit][:1000], xp[through&~hit][:1000], '.', color=(0.8,0.,0.))
        #plot(zp[~through][:1000], xp[~through][:1000], '.', color=(0.5,0.5,0.5))
        plot([sz1,sz2],[sx1,sx2], '-', color=(0.0, 0.8, 0.0))  # sample edges
    else:
        # set p to position on sample of the hit
        p = z + width/2
        pmin, pmax = p[through].min(), p[through].max()
        # find beam spill from disk
        spill_weight = 1 - weight
        spill_weight[~hit] = 1
        spill_weight[~through] = 0
        bins = np.linspace(pmin, pmax, 100)
        hist(p[hit], label="sample", bins=bins)
        hist(p[hit], label="disk", weights=weight[hit], bins=bins)
        #hist(p, label="dspill", weights=spill_weight, bins=bins)
        hist(p[through&~hit], label="spill", bins=bins)
        legend()
    show()

def main():
    #resolution_simulator()
    if len(sys.argv) < 2:
        print("incident angle in degrees required")
        sys.exit(1)
    theta = float(sys.argv[1])
    single_point_demo(theta=theta, count=1500)
    #scan_demo(150)
    pylab.show()
    sys.exit()

if __name__ == "__main__":
    main()
