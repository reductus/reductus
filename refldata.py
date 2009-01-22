# This program is public domain
"""
Reflectometry data representation.

Need to support collections of data from TOF, monochromatic
and white beam instruments.

Conceptually each data point is a tuple::

    incident angles (sample tilt and rotation)
    reflected angles (polar angle of detector pixel)
    slit distances and openings
    detector pixel distance and size
    incident/reflected polarization
    wavelength distribution
    measurement start and duration
    monitor and detector counts
    sample environment

Reflectometers are either vertical or horizontal geometry.
For vertical geometry (sample surface parallel to gravity),
x refers to horizontal slit opening and horizontal detector
pixels.  For horizontal geometry (sample surface perpendicular
to gravity) x refers to vertical slit opening and vertical
detector pixels. Other than gravitational corrections to
resolution and detector pixels, the analysis for the two
instrument types should be identical.

Monochromatic reflectometers have a single wavelength per
measurement but scan the measurements.  Time-of-flight and
polychromatic reflectometers have multiple wavelengths per
measurement but perform one measurement.  In either case
a dataset consists of detector frames versus Q.  We will
ignore scans on multichannel instruments since these can
be treated as combined independent scans with non-overlapping
data, and handled outside this data structure.

Data points are gathered together into measurements.  Some
files may have multiple measurements, and other measurements
may be spread over multiple files.  Files may be local or
remote, ascii or binary.  It is up to the individual format
reader to assign map measurements to files.

Different polarization states will be treated as belonging
to different measurements.  These will need to be aligned
before polarization correction can be performed.  Multiple
measurements may occur on the same detector.  In this
case each measurement should have a separate 'region of
interest' to isolate it from the others, presenting a virtual
detector to the reduction and analysis program.

Some information about the measurements may be missing
from the files, or recorded incorrectly.  Changes and
additions to the metadata must be recorded in any reduced
data file format, along with a list of transformations
that went into the reduction.

See notes in properties.py regarding dated values.
"""
__all__ = ['ReflData']

import datetime
import weakref

import numpy
from numpy import inf, pi, sin, cos, arcsin, arctan2, sqrt

from qxqz import ABL_to_QxQz

# TODO: attribute documentation and units should be integrated with the
# TODO: definition of the attributes.  Value attributes should support
# TODO: unit conversion
class Slit(object):
    """
    Define a slit for the instrument.  This is needed for correct resolution
    calculations and for ab initio footprint calculations.

    distance (inf millimetre)
        Distance from sample.  Positive numbers are after the sample,
        negative numbers are before the sample along the beam path.
    offset (4 x 0 millimetre)
        Offset of the slit blades relative to the distance from the sample.
        For vertical geometry, this is left, right, up, down.  For horizontal
        geometry this is up, down, left, right.  Offset + distance gives the
        distances of the individual blades from the sample, with negative
        numbers occurring before the sample position and positive numbers
        after.
    shape (shape='rectangular')
        Whether we have slit blades ('rectangular') or a circular
        aperature ('circular').
    x (n x inf millimetre)
        Slit opening in the primary direction.  For vertical geometry
        this is the horizontal opening, for horizontal geometry this is
        the vertical opening.  This may be a constant (fixed slits) or
        of length n for the number of measurements.
    y (n x inf millimetre)
        Slit opening in the secondary direction.  This may be a constant
        (fixed slits) or of length n for the number of measurements.
    """
    properties = ['distance','offset','x','y','shape']
    distance = inf
    offset = [0.]*4
    x = inf
    y = inf
    shape = "rectangular" # rectangular or circular

    def __init__(self, **kw): _set(self,kw)
    def __str__(self): return _str(self)

class Sample(object):
    """
    Define the sample geometry.  Size and shape areneeded for correct
    resolution calculations and for ab initio footprint calculations.
    Angles are needed for correct calculation of Q.  Rotation and
    environment are for display to the user.

    description ("")
        Sample description, if available from the file.
    width (inf millimetre)
        Width of the sample in the primary direction.  For fixed slits
        the footprint of the beam on the sample decreases with angle
        in this direction.
    length (inf millimetre)
        Width of the sample in the secondary direction.  The footprint
        is independent of angle in this direction.
    thickness (inf millimetre)
        Thickness of the sample.
    substrate_sld (10^-6 Angstrom^-2)
        To plot Fresnel reflectivity we need to know the substrate
        scattering length density.  The default is to assume silicon.
    shape ('rectangular')
        Shape is 'circular' or 'rectangular'
    angle_x (n x 0 degree)
        Angle between neutron beam and sample surface in the primary
        direction.  This may be constant or an array of length n for
        the number of measurements.
    angle_y (n x 0 degree)
        Angle between the neutron beam and sample surface in the
        secondary direction.  This may be constant or an array of
        length n for the number of measurements.  This is known as
        tilt on some instruments.
    rotation (n x 0 degree)
        For off-specular reflectivity the orientation of the patterned
        array on the surface of the sample affects the computed theory.
        This value is not needed for data reduction, but it should be
        reported to the user during reduction and carried through to
        the reduced file for correct analysis.
    environment ({})
        Sample environment data.  See Environment class for a list of
        common environment data.
    """
    properties = ['description','width','length','thickness','shape',
                  'angle_x','angle_y','rotation','substrate_sld']
    description = ''
    width = inf  # mm
    length = inf  # mm
    thickness = inf # mm
    shape = 'rectangular' # rectangular or circular or irregular
    angle_x = 0 # degree
    angle_y = 0 # degree
    rotation = 0 # degree
    substrate_sld = 2.07 # inv A  (silicon substrate for neutrons)

    def __init__(self, **kw):
        self.environment = {}
        _set(self,kw)
    def __str__(self): return _str(self)



class Environment(object):
    """
    Define sample environment data for the measurements such as
        temperature (kelvin)
        pressure (pascal)
        relative_humidity (%)
        electric_field (V/m)
        magnetic_field (tesla)
        stress_field (pascal)

    The data may be a constant, a series of values equal to
    the number of scan points, or a series of values and times.
    The average, max and min over all scan points, and the
    value, max and min for a particular scan point may be
    available.

    Some measurements are directional, and will have a polar
    and azimuthal angle associated with them.  This may be
    constant for the entire scan, or stored separately with
    each magnitude measurement.

    name
        Name of environment variable
    units
        Units to report on graphs
    average, minimum, maximum
        Statistics on all measurements
    value
        Magnitude of the measurement
    start
        Start time for log
    time (seconds)
        Measurement time relative to start
    polar_angle (degree)
    azimuthal_angle (degree)
        Provide orientation relative to the sample surface for
        directional parameters:
        * x is polar 0, azimuthal 0
        * y is polar 90, azimuthal 0
        * z is azimuthal 90
    """
    pass


class Beamstop(object):
    """
    Define the geometry of the beamstop.  This is used by the
    detector class to compute the shadow of the beamstop on the
    detector.  The beamstop is assumed to be centered on the
    direct beam regardless of the position of the detector.

    distance (0 millimetre)
        Distance from sample to beamstop.  Note: this will need to
        be subtracted from the distance from detector to beamstop.
    shape ('rectangular')
        Shape is 'circular' or 'rectangular'
    width (0 millimetre)
        Width of the beamstop in the primary direction.  For circular
        beamstops, this is the diameter.
    length (0 millimetre)
        Width of the beamstop in the secondary direction.  For circular
        beamstops, this is the diameter.
    offset (2 x millimetre)
        Offset of the beamstop from the center of the beam.
    ispresent (False)
        True if beamstop is present in the experiment.
    """
    properties = ['distance','width','length','shape',
                  'x_offset','y_offset','ispresent']
    distance = 0 # mm
    width = 0 # mm
    length = 0 # mm
    shape = 'rectangular' # rectangular or circular
    offset = [0,0] # mm
    ispresent = False

    def __init__(self, **kw): _set(self,kw)
    def __str__(self): return _str(self)

class Detector(object):
    """
    Define the detector properties.  Note that this defines a virtual
    detector.  The real detector may have e.g., multiple beam paths
    incident upon it, and be split into two virtual detectors when
    the file is loaded.

    Direction x refers to the primary direction,  and direction y to
    the secondary direction.  For vertical geometry, the primary
    direction is in the horizontal plane and the secondary direction
    is in the vertical plane.  For horizontal geometry these are
    reversed.  This allows the reduction software to be simpler,
    but may complicate file loading from formats which store values
    in absolute geometry.

    Geometry
    ========
    dims (2 x pixels)
        Dimensions of the detector, [nx,ny].  For pencil detectors this
        should be [1,1].  For position sensitive detectors, this should be
        [nx,1].  For area detectors, this should be [nx,ny].
    distance (millimetre)
        Distance from the sample to the detector.
    size (2 x millimetre)
        Detector size, [x,y].  Default is 1 mm x 1 mm.
    solid_angle (2 x radian)
        Detector solid angle [x,y], calculated from distance and size.
    center (2 x millimetre)
        Location of the center pixel [x,y] relative to the detector arm.
    widths_x (nx x millimetre)
    widths_y (ny x millimetre)
        Pixel widths in x and y.  We assume no space between the pixels.
    angle_x (n x degree)
    angle_y (n x degree)
        Angle of the detector arm relative to the main beam in x and y.
        This may be constant or an array of length n for the number of
        measurements in the scan.
    rotation (degree)
        Angle of rotation of the detector relative to the beam.  This
        will affect how vertical integration in the region of interest
        is calculated.  Ideally the detector would not be rotated, though
        misalignment can sometimes occur.

    Efficiency
    ==========
    efficiency (nx x ny %)
        Efficiency of the individual pixels; this is an array of the same
        shape as the detector, giving the relative efficiency of each pixel,
        or 1 if the efficiency is unknown.
        TODO: do we need variance?
    saturation (k [%, counts/second, uncertainty])
        Given a measurement of a given number of counts versus expected
        number of counts on the detector (e.g., as estimated by scanning
        a narrow slit across the detector to measure the beam profile,
        then measuring increasingly large portions of the beam profile),
        this can be converted to an efficiency correction per count rate
        which can be applied to all data read with this detector.  The
        value for deadtime should be a tuple of three vectors: efficiency,
        uncertainty and count rate.  Below the lowest count rate the
        detector is considered to be 100% efficient (any baseline
        inefficiency will be normalized when comparing the measured
        reflection to the measured beam).  Beyond the highest count
        rate, the detector is considered saturated.  The uncertainty
        is just the sqrt(counts)/time.


        Note: Given the nature of the detectors (detecting ionization
        caused by neutron capture) there is undoubtably a local
        saturation level, but this is likely masked by the usual
        detector electronics which can only detect one event at a
        time regardless of where it occurs on the detector.

    Measurement
    ===========
    wavelength (k nanometre)
        Wavelength for each channel
    wavelength_resolution (k %)
        Wavelength resolution of the beam for each channel using 1-sigma
        gaussian approximation dL, expressed as 100*dL/L.  The actual
        wavelength distribution is considerably more complicated, being
        approximately square for multi-sheet monochromators and highly
        skewed on TOF machines.
    time_of_flight (k+1 millisecond)
        Time boundaries for time-of-flight measurement
    counts (nx x ny x k counts OR n x nx x ny counts)
        nx x ny detector pixels
        n number of measurements
        k time/wavelength channels

    Runtime Facilities
    ==================
    loadcounts (function returning counts)
        Counts can be assigned using
            data.detector.counts = weakref.ref(counts)
        When the counts field is accessed, the reference will be resolved.
        If it yields None, then loadcounts will be called and assigned to
        counts as a weak reference.  In this way large datasets can be
        removed from memory when not in active use.
    """
    properties=["dims",'distance','size','center','widths_x','widths_y',
                'angle_x','angle_y','rotation','efficiency','saturation',
                'wavelength','time_of_flight','counts']
    dims = [1,1] # i,j
    distance = None # mm
    size = [1,1]  # mm
    center = [0,0] # mm
    widths_x = 1 # mm
    widths_y = 1 # mm
    angle_x = 0  # degree
    angle_y = 0  # degree
    rotation = 0 # degree
    efficiency = 1 # proportion
    saturation = inf # counts/sec
    wavelength = 1 # angstrom
    time_of_flight = None  # ms

    def _solid_angle(self):
        """Detector solid angle [x,y] (radians)"""
        return 2*arctan2(numpy.asarray(self.size)/2.,self.distance)
    solid_angle = property(_solid_angle,doc=_solid_angle.__doc__)


    # Raw counts are cached in memory and loaded on demand.
    # Rebinned and integrated counts for the region of interest
    # are stored in memory.
    #_pcounts = lambda:None
    def loadcounts(self):
        """Load the data"""
        raise NotImplementedError,\
           "Data format must set detector.counts or detector.loadcounts"
    def _pcounts(self):
        """Simulated empty weak reference"""
        return None
    def _getcounts(self):
        counts = self._pcounts()
        if counts is None:
            counts = self.loadcounts()
            self._pcounts = weakref.ref(counts)
        return counts
    def _setcounts(self, value):
        # File formats which are small do not need to use weak references,
        # however, for convenience the should use the same interface, which
        # is value() rather than value.
        if isinstance(value,weakref.ref):
            self._pcounts = value
        else:
            def static(): return value
            self._pcounts = static
        #self._pcounts = lambda:value
    def _delcounts(self):
        _pcounts = lambda:None
    counts = property(_getcounts,_setcounts,_delcounts)


    def __init__(self, **kw): _set(self,kw)
    def __str__(self): return _str(self)


class ROI(object):
    """
    Detector region of interest.

    Defines a rectangular region of interest on the detector which
    is used for defining frames.  This can be used for example to
    split a single detector with both polarization states (via
    transmission and reflection off a supermirror) into two virtual
    detectors.

    xlo, xhi (pixels)
    ylo, yhi (pixels)
    """
    properties = ['xlo','xhi','ylo','yhi']
    xlo = None
    xhi = None
    ylo = None
    yhi = None

    def __init__(self, **kw): _set(self,kw)
    def __str__(self): return _str(self)

class Monitor(object):
    """
    Define the monitor properties.

    The monitor is essential to the normalization of reflectometry data.
    Reflectometry is the number of neutrons detected divided by the
    number of neutrons incident on the sample.  To compute this ratio,
    the incident and detected neutrons must be normalized to the neutron
    rate, either counts per monitor count, counts per second or counts
    per unit of source power (e.g., coulombs of protons incident on the
    detector, or megawatt hours of reactor power).

    counts (n x k counts)
        Number of counts measured.  For scanning instruments there is
        a separate count for each of the n measurements.  For TOF
        instruments there is a separate count for each of k time
        channels.  Counts may be absent, in which case normalization
        must be by time or by monitor.  In some circumstances the
        user may generate a counts vector, for example by estimating
        the count rate by other means, in order to combine data
        measured by time with data measured by monitor when the
        monitor values are otherwise unreliable.  Variance is assumed
        to be the number of counts, after any necessary rebinning.
    count_time (n seconds)
        Duration of the measurement.  For scanning instruments, there is
        a separate duration for each measurement.  For TOF, this is a
        single value equal to the duration of the entire measurement.
    source_power (n source_power_units)
        The source power for each measurement.  For situations when the
        monitor cannot be trusted (which can happen from time to time on
        some instruments), we can use the number of protons incident on
        the target (proton charge) or the energy of the source (reactor
        power integrated over the duration of each measurement) as a proxy
        for the monitor.  So long as the we normalize both the slit
        measurement and the reflectivity measurement by the power, this
        should give us a reasonable estimate of the reflectivity.  If
        the information is available, this will be a better proxy for
        monitor than measurement duration.
    base ('time' | 'counts' | 'power')
        The measurement rate basis which should be used to normalize
        the data.  This is initialized by the file loader, but may
        be overridden during reduction.
    time_step (seconds)
        The count_time timer has a reporting unit, e.g. second, or
        millisecond, or in the case of NCNR ICP files, hundredths of
        a minute.  The measurement uncertainty for the count time
        is assumed to be uniform over the time_step, centered on
        the reported time, with a gaussian approximation of uncertainty
        being sqrt(time_step/12).
    start_time (n seconds)
        For scanning instruments the start of each measurement relative
        to start of the scan.  Note that this is not simply sum of the
        count times because there may be motor movement between
        measurements.  The start time is required to align the measurement
        values with environment parameters, and for calculation of He3
        polarization.  For TOF, this should be zero.
    distance (metre)
        Distance from the sample.  This is not used by reduction but
        may be of interest to the user.
    sampled_fraction ([0,1])
        Portion of the neutrons that are sampled by the monitor.  If the
        monitor is after the second slit, the monitor value can be used to
        estimate the the counts on the detector, scaled by the sampled
        fraction.   Otherwise a full slit scan is required to normalize
        the reflectivity.  This is the inverse of the detector to monitor
        ratio used to normalize data on some instruments.
    time_of_flight (k+1 millisecond)
        Time boundaries for the time-of-flight measurement
    source_power_units ('coulombs' | 'megawatthours')
        Units for source power.
    source_power_variance (n source_power_units)
        Variance in the measured source power
    monitor_rate (counts/second)
        For normalizing by counts when only count time is recorded, we
        need an estimate of the monitor rate during the measurement.
    """
    properties = ['distance','sampled_fraction','counts','start_time',
                  'count_time','time_step','time_of_flight','base',
                  'monitor_rate','source_power','source_power_units']
    distance = None
    sampled_fraction = None
    counts = None
    start_time = None
    count_time = None
    time_step = 1 # Default to nearest second
    time_of_flight = None
    base = 'counts'
    source_power = 1 # Default to 1 MW power
    source_power_units = "MW"
    source_power_variance = 0
    monitor_rate = 0 # counts/sec

    def __init__(self, **kw): _set(self,kw)
    def __str__(self): return _str(self)

class Moderator(object):
    """
    Time of flight calculations require information about the moderator.
    Primarily this is the length of the flight path from moderator to
    monitor or detector required to compute wavelength.

    Moderator temperature is also recorded.  The user should probably
    be warned when working with datasets with different moderator
    temperatures since this is likely to affect the wavelength
    spectrum of the beam.

    distance (metre)
        Distance from moderator to sample.  This is negative since the
        monitor is certainly before the sample.
    temperature (kelvin)
        Temperature of the moderator
    type (string)
        For information only at this point.
    """
    properties = ['distance','temperature','type']
    distance = None
    temperature = None
    type = 'Unknown'

    def __init__(self, **kw): _set(self, kw)
    def __str__(self): return _str(self)

class Warning(object):
    """
    A warning is an information message and a possible set of actions to
    take in response to the warning.

    The user interface can query the message and the action list, generate
    a dialog on the basis of the information.  Actions may have associated
    attributes that need to be set for the action to complete.
    """
    pass

class WarningWavelength(Warning):
    """
    Unexpected wavelength warning.

    This warning is attached to any dataset which has an unexpected
    wavelength stored in the file (more than 1% different from the
    default wavelength for the instrument).

    Various actions can be done in response to the warning, including
    always taking the default value for this instrument, overriding for
    every value in the dataset
    """
    pass

class ReflData(object):
    """
    slit1,slit2 (Slit)
        Presample slits
    slit3,slit4 (Slit)
        Post sample slits
    sample
        Sample geometry
    detector
        Detector geometry, efficiency and counts
    monitor
        Counts and/or durations
    polarization
        '' unpolarized
        '+' spin up
        '-' spin down
        '++','--'  non-spin-flip
        '-+','+-'  spin flip
    points
        For scanning instruments, the number of measurements.
    channels
        For time of flight, the number of time channels.  For white
        beam instruments, the number of analysers.
    reversed (False)
        True if the measurement is reversed, in which case sample
        and detector angles need to be negated and pixel directions
        reversed when computing pixel coordinates.
    roi
        Region of interest on the detector.
    display_monitor (counts)
        Default monitor to use when displaying data from this dataset

    File details
    ============
    instrument (string)
        Name of a particular instrument
    probe ('neutron' or 'xray')
        Type of radiation used to probe the sample.
    path (string)
        Location of the datafile
    entry (string)
        Entry identifier if more than one entry per file
    name (string)
        Name of the dataset.  This may be a combination of filename and
        entry number.
    description (string)
        Description of the entry.
    date (timestamp)
        Starting date and time of the measurement.
    duration (second)
        Duration of the measurement.
    warnings
        List of warnings generated when the file was loaded
    intent (string)
        Purpose of the measurement.
        intensity: Normalization scan for computing absolute reflection
        specular: Specular intensity measurement
        q_offset: Background measurement, offset from Qx=0 in Q
        sample_offset: Background measurement, sample rotated
        detector_offset: Background measurement, detector moved
        slice: Slice through Qx-Qz
        area: Measurement of a region of Qx-Qz plane
        alignment: Sample alignment measurement
        other: Some other kind of measurement

    Format specific fields (ignored by reduction software)
    ======================
    file (handle)
        Format specific file handle, for actions like showing the summary,
        updating the data and reading the frames.
    """
    properties = ['instrument','geometry','probe','points','channels',
                  'name','description','date','duration','attenuator',
                  'polarization','reversed','warnings','path','entry']
    geometry = "vertical"
    probe = "unknown"
    format = "unknown"
    path = "unknown"
    entry = ""
    points = 1
    channels = 1
    name = ""
    description = ""
    date = datetime.datetime(1970,1,1)
    duration = 0
    file = None
    attenuator = 1.
    polarization = ''
    reversed = False
    warnings = None
    messages = None

    def _getdR(self): return sqrt(self.varR)
    def _setdR(self, dR): self.varR = dR**2
    dR = property(_getdR,_setdR)

    # Data representation for generic plotter as (x,y,z,v)
    # TODO: subclass Data so we get pixel edges calculations
    def _getx(self): return self.Qz
    def _gety(self): return self.Qx
    def _getz(self): return self.Qy
    def _getv(self): return self.R
    def _getdv(self): return sqrt(self.varR)
    x,xlabel,xunits = property(_getx),"Qx","inv A"
    y,ylabel,yunits = property(_gety),"Qy","inv A"
    z,zlabel,zunits = property(_getz),"Qz","inv A"
    v,dv = property(_getv),property(_getdv)
    # vlabel and vunits depend on monitor normalization

    def __init__(self, **kw):
        # Note: because _set is ahead of the following, the caller will not
        # be able to specify sample, slit, detector or monitor on creation,
        # but will instead have to use those items provided by the class.
        _set(self,kw)
        self.sample = Sample()
        self.slit1 = Slit()
        self.slit2 = Slit()
        self.slit3 = Slit()
        self.slit4 = Slit()
        self.detector = Detector()
        self.monitor = Monitor()
        self.moderator = Moderator()
        self.warnings = []
        self.roi = ROI()
        self.messages = []

    def __str__(self):
        base = [_str(self)]
        others = [str(s) for s in [self.slit1,self.slit2,self.slit3,self.slit4,
                                   self.sample,self.detector,self.monitor,
                                   self.roi]]
        return "\n".join(base+others)

    def warn(self,msg):
        """Record a warning that should be displayed to the user"""
        self.warnings.append(msg)

    def log(self,msg):
        """Record corrections that have been applied to the data"""
        self.messages.append(msg)

    def apply(self,correction):
        """Allow alternative syntax: data.apply(correction)"""
        self.log(str(correction))
        correction.apply(self)

    def resetQ(self):
        """Recompute Qx,Qz from geometry and wavelength"""
        A,B = self.sample.angle_x,self.detector.angle_x
        L = self.detector.wavelength
        Qx,Qz = ABL_to_QxQz(A,B,L)
        self.Qx,self.Qz = Qx,Qz

def _str(object):
    """
    Helper function: document data object by convert attributes listed in
    properties into a string.
    """
    cls = object.__class__.__name__
    props = [a+"="+str(getattr(object,a)) for a in object.properties]
    return "%s %s"%(cls,"\n  ".join(props))


def _set(object,kw):
    '''
    Helper function: distribute the __init__ keyward paramters to
    individual attributes of an object, raising AttributeError if
    the class does not define the given attribute.

    Example:

        def __init__(self, **kw): _set(self,kw)
    '''
    for k,v in kw.iteritems():
        if hasattr(self,k):
            setattr(object,k,v)
        else:
            raise AttributeError, "Unknown attribute %s"%(k)

# Ignore the remainder of this file --- I don't yet have the computational
# interface set up.

    """
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
        xlo,xhi,ylo,yhi = self.roi
        counts = self.detector.counts
        nq = zhi-zlo+1
        nx = self.detector.shape[0]
        ny = self.detector.shape[1]
        if ny == 1:
            self.zx = counts[zlo:zhi+1,:]
        else:
            xy = numpy.zeros((nx,ny),dtype='float32')
            zx = numpy.zeros((nq,nx),dtype='float32')
            self.framerange = Limits() # Keep track of total range
            for i in range(zlo,zhi):
                v = self.frame(i)
                self.framerange.add(v,dv=sqrt(v))
                xy += v
                zx[i-zlo,:] = numpy.sum(v[:,ylo:yhi],axis=1)
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
    mask = numpy.ones(self.detector.shape,'int8')
    if beamstop.ispresent:
        # calculate location of the beamstop centre relative to
        # the detector.
        pass
    return mask
