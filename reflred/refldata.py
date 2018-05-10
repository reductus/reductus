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

Monochromatic reflectometry files have a single wavelength per
angle and a series of angles.  Time-of-flight and polychromatic
reflectometers have multiple wavelengths per angle but usually
one angle per file.  In either case a file is a set of
detector frames each with its own wavelength and angles.

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

## Proposal for introspection with units
#def get_as(object,**kw):
#    if len(kw) != 1: raise Error
#    for k,v in kw.items():
#        return convert(getattr(object,k),object.__units__[k],v)
#def units(object, k):
#    return object.__units__[k]
#
#get_as(detector, distance='m')
#units(detector, 'distance')
#
#class Detector(object):
#    __units__ = dict(distance='mm',size='mm',saturation='counts/s')
#    ...
#
## Variation: use a units class to represent the units rather than a string
## This means that we save a couple of string lookups when doing conversion
#get_as(detector, distance=metre)
#def get_as(object,**kw):
#    if len(kw) != 1: raise Error
#    for k,v in kw.items():
#        return getattr(object,k)*object.__units__[k]/v
#class Detector(object):
#    __units__ = dict(distance=milli*metre,size=milli*metre,saturation=1/second)

## Something similar can be used for uncertainty, preferably stored as variance

import sys
import datetime
import warnings
import json
from io import BytesIO

import numpy as np
from numpy import inf, arctan2, sqrt, sin, cos, pi, radians

from . import resolution

IS_PY3 = sys.version_info[0] >= 3

# for sample background angle offset
QZ_FROM_SAMPLE = 'sample angle'
QZ_FROM_DETECTOR = 'detector angle'

class Group(object):
    _fields = ()
    _props = ()
    def __setattr__(self, key, value):
        # Check for class attr when setting; this is because hasattr on
        # a property will return False if getattr on that property raises
        # an exception.  This means if you really want to sneak an
        # attribute into the group from your data loader, you will have
        # to populate it from the
        if not key.startswith('_') and not hasattr(self.__class__, key):
            raise AttributeError("Cannot add attribute %s to class %s"
                                 % (key, self.__class__.__name__))
        object.__setattr__(self, key, value)
    def __init__(self, **kw):
        _set(self, kw)
    def __str__(self):
        return _str(self)
    def _toDict(self):
        return _toDict(self)


def set_fields(cls):
    groups = set(name for name, type in getattr(cls, '_groups', ()))
    properties = []
    fields = []
    for k, v in sorted((k, v) for k, v in cls.__dict__.items()):
        if k.startswith('_') or k in groups:
            pass
        elif isinstance(v, property):
            properties.append(k)
        elif not callable(v):
            fields.append(k)
    cls._fields = tuple(fields)
    cls._props = tuple(properties)
    return cls

# TODO: attribute documentation and units should be integrated with the
# TODO: definition of the attributes.  Value attributes should support
# TODO: unit conversion
@set_fields
class Slit(Group):
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
    columns = {"x": {"units": "mm"}}
    distance = inf
    offset = (0., 0., 0., 0.)
    x = inf  # type: np.ndarray
    x_target = None  # type: np.ndarray
    y = inf  # type: np.ndarray
    y_target = None  # type: np.ndarray
    shape = "rectangular" # rectangular or circular


@set_fields
class Environment(Group):
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
    """

    #: Name of environment variable
    name = ""
    #: Units to report on graphs
    units = ""
    #: Statistics on all measurements
    average = None  # type: np.ndarray
    minimum = None  # type: np.ndarray
    maximum = None  # type: np.ndarray
    #: Magnitude of the measurement
    value = None  # type: np.ndarray
    #: Start time for log (seconds)
    start = None  # type: np.ndarray
    #: Measurement time relative to start (seconds)
    time = None  # type: np.ndarray


@set_fields
class Sample(Group):
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
    angle_x_target (n x 0 degree)
        Desired angle_x, used by join to select the points that are
        nominally the same in the joined data set.
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
    name = ''
    description = ''
    columns = {"angle_x": {"units": "degrees"}}
    width = inf  # mm
    length = inf  # mm
    thickness = inf # mm
    shape = 'rectangular' # rectangular or circular or irregular
    angle_x = 0. # degree
    angle_x_target = None  # degree
    angle_y = 0. # degree
    rotation = 0. # degree
    substrate_sld = 2.07 # inv A  (silicon substrate for neutrons)
    incident_sld = 0. # inv A (air)
    broadening = 0.
    environment = None  # type: Dict[str, Environment]
    temp_setpoint = None
    temp_avg = None
    magnet_setpoint = None
    magnet_avg = None

    def __init__(self, **kw):
        self.environment = {}
        Group.__init__(self, **kw)


@set_fields
class Beamstop(Group):
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
    distance = 0. # mm
    width = 0. # mm
    length = 0. # mm
    shape = 'rectangular' # rectangular or circular
    offset = (0., 0.) # mm
    ispresent = False


@set_fields
class Detector(Group):
    """
    Define the detector properties.  Note that this defines a virtual
    detector.  The real detector may have e.g., multiple beam paths
    incident upon it, and be split into two virtual detectors when
    the file is loaded.

    Direction x refers to the primary direction and y refers to
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
    saturation (k [rate (counts/second), efficiency (%), uncertainty])
        Given a measurement of a given number of counts versus expected
        number of counts on the detector (e.g., as estimated by scanning
        a narrow slit across the detector to measure the beam profile,
        then measuring increasingly large portions of the beam profile),
        this can be converted to an efficiency correction per count rate
        which can be applied to all data read with this detector.  The
        value for deadtime should be a tuple of vectors: count rate,
        efficiency and uncertainty.  Below the lowest count rate the detector
        is considered to be 100% efficient (any baseline inefficiency will
        be normalized when comparing the measured reflection to the
        measured beam).  Beyond the highest count rate, the detector
        is considered saturated.  The normalize counts vector (v,dv) will
        be scaled by 1/(saturation +/- uncertainty).

        Note: There may be separate per pixel and per detector
        saturation levels.

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
    """
    dims = (1, 1) # i,j
    distance = None # mm
    size = (1., 1.)  # mm
    center = (0., 0.) # mm
    widths_x = 1. # mm
    widths_y = 1. # mm
    angle_x = 0.  # degree
    angle_y = 0.  # degree
    angle_x_target = 0.  # degree
    rotation = 0. # degree
    efficiency = 1. # proportion
    saturation = inf # counts/sec
    wavelength = 1. # angstrom
    wavelength_resolution = 0. # angstrom
    time_of_flight = None  # ms
    counts = None
    counts_variance = None
    deadtime = None
    deadtime_error = None
    columns = {
        "counts": {"units": "counts", "variance": "counts_variance"},
        "angle_x": {"units": "degrees"}
    }

    @property
    def solid_angle(self):
        """Detector solid angle [x,y] (radians)"""
        #return 2*arctan2(np.asarray(self.size)/2., self.distance)
        return (2*arctan2(np.asarray(self.size)/2., self.distance)
                if self.distance is not None
                else np.array([0., 0.]))


@set_fields
class ROI(Group):
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
    xlo = None
    xhi = None
    ylo = None
    yhi = None

@set_fields
class Monitor(Group):
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
    base ('time' | 'monitor' | 'power')
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

    The corrected monitor counts field will start as None, but may be
    set by a dead time correction, which scales the monitor according
    to the monitor rate.  If for some reason the monitor is flaky, then
    the corrected monitor counts could be set by multiplying time by
    the monitor rate.
    """
    distance = None
    sampled_fraction = None
    counts = None
    counts_variance = None
    start_time = None
    count_time = None
    time_step = 1 # Default to nearest second
    time_of_flight = None
    base = 'monitor'
    source_power = None # No source power recorded
    source_power_units = "MW"
    source_power_variance = 0
    saturation = None
    columns = {
        "counts": {"units": "counts", "variance": "counts_variance"},
        "count_time": {"units": "seconds"}
    }
    deadtime = None
    deadtime_error = None

class Intent(object):
    """
    Intent is one of the following:

        intensity: Normalization scan for computing absolute reflection
        specular: Specular intensity measurement
        background+: Background measurement, sample rotated
        background-: Background measurement, detector offset
        rock qx: Rocking curve with fixed Qz
        rock sample: Rocking curve with fixed detector angle
        rock detector: Rocking curve with fixed sample angle
        unknown: Some other kind of measurement

        detector efficiency: Flood fill

    Not supported:
        alignment: Sample alignment measurement
        area: Measurement of a region of Qx-Qz plane
        slice: Slice through Qx-Qz
    """
    slit = 'intensity'
    spec = 'specular'
    backp = 'background+'
    backm = 'background-'
    rockQ = 'rock qx'
    rock3 = 'rock sample'
    rock4 = 'rock detector'
    none = 'unknown'
    deff = 'detector efficiency'
    time = 'time'
    other = 'other'
    scan = 'scan'

    intents = (slit, spec, backp, backm, rockQ, rock3, rock4,
               deff, time, other, scan, none)

    @staticmethod
    def isback(intent):
        return intent.startswith('background')

    @staticmethod
    def isspec(intent):
        return intent == Intent.spec

    @staticmethod
    def isrock(intent):
        return intent.startswith('rock')

    @staticmethod
    def isslit(intent):
        return intent == Intent.slit

    @staticmethod
    def isnone(intent):
        return intent == Intent.none

    @staticmethod
    def isscan(intent):
        return intent == Intent.scan

def infer_intent(data):
    """
    Infer intent from data.

    Returns one of the Intent strings.
    """
    # TODO: doesn't handle alignment scans
    theta_i = data.sample.angle_x
    theta_f = 0.5*data.detector.angle_x
    dtheta = 0.1*data.angular_resolution
    n = len(theta_i)

    scan_i = (max(theta_i) - min(theta_i) > dtheta).any()
    scan_f = (max(theta_f) - min(theta_f) > dtheta).any()
    if (abs(theta_i) < dtheta).all() and (abs(theta_f) < dtheta).all():
        # incident and reflected angles are both 0
        intent = Intent.slit
    elif (scan_i and scan_f) or (not scan_i and not scan_f):
        # both theta_i and theta_f are moving, or neither is moving
        if (abs(theta_f - theta_i) < dtheta).all():       # all specular
            intent = Intent.spec
        elif (data.Qz.max() - data.Qz.min() < data.dQ.max()
              and data.Qx.max() - data.Qx.min()) > data.dQ.max():
            intent = Intent.rockQ
        elif np.sum(theta_f - theta_i > dtheta) > 0.9*n:  # 90% above
            intent = Intent.backp
        elif np.sum(theta_i - theta_f > dtheta) > 0.9*n:  # 90% below
            intent = Intent.backm
        else:
            intent = Intent.none
    elif scan_i:
        # only theta_i is moving
        intent = Intent.rock3
    elif scan_f:
        # only theta_f is moving
        intent = Intent.rock4
    else:
        # never gets here
        intent = Intent.scan

    return intent


@set_fields
class ReflData(Group):
    """
    Reflectometry data structure, giving a predictable name space for the
    reduction steps regardless of input file format.
    """
    _groups = (
        ("slit1", Slit), ("slit2", Slit), ("slit3", Slit), ("slit4", Slit),
        ("detector", Detector),
        ("sample", Sample),
        ("monitor", Monitor),
        ("roi", ROI),
    )

    #: Sample geometry
    sample = None     # type: Sample
    #: Presample slits
    slit1 = None      # type: Slit
    #: Presample slits
    slit2 = None      # type: Slit
    #: Post sample slits
    slit3 = None      # type: Slit
    #: Post sample slits
    slit4 = None      # type: Slit
    #: Detector geometry, efficiency and counts
    detector = None   # type: Detector
    #: Counts and/or durations
    monitor = None    # type: Monitor
    #: Region of interest on the detector.
    roi = None        # type: ROI

    #: Name of a particular instrument
    instrument = "unknown"
    #: Whether the scattering plane is horizontal or vertical.  The x-y
    #: values of the slits, detector, etc. should be relative to the
    #: scattering plane, not the lab frame.
    geometry = "vertical"
    #: Type of radiation (neutron or xray) used to probe the sample.
    probe = "unknown"
    #: Location of the datafile
    path = "unknown"
    #: Download location for the file, if available
    uri = "unknown"
    #: For scanning instruments, the number of measurements.
    points = 1
    #: For time of flight, the number of time channels.  For white
    #: beam instruments, the number of analysers.
    channels = 1
    #: Name of the dataset.  This may be a combination of filename and
    #: entry number.
    name = ""
    #: Numeric ID of the dataset.  Using "fileNum" from trajectoryData
    filenumber = 0
    #: Entry identifier if more than one entry per file
    entry = ""
    #: Description of the entry.
    description = ""
    #: Starting date and time of the measurement.
    date = datetime.datetime(1970, 1, 1)
    #: Duration of the measurement.
    duration = 0
    #: '' unpolarized
    #: '+' spin up
    #: '-' spin down
    #: '++','--'  non-spin-flip
    #: '-+','+-'  spin flip
    polarization = ""
    #: The base for normalization (e.g., 'monitor' or 'time')
    normbase = None
    #: List of warnings generated when the file was loaded
    warnings = None
    #: List of corrections that have been applied to the data
    messages = None
    #: Value label for y-axis on 1-D or colorbar on 2-D plots.
    #: Label will change when the value is normalized.
    vlabel = 'Intensity'
    #: Value units
    vunits = 'counts'
    #: Value scale ('linear', 'log' or '' for auto)
    #: Units will change when the value is normalized.
    vscale = '' # type: str
    #: X axis label
    xlabel = 'unknown intent'
    #: X axis units
    xunits = ''
    #: Value scale ('linear', 'log' or '' for auto)
    xscale = ''
    #: points excluded from reduction
    mask = None
    #: Computed 1-sigma angular resolution in degrees
    angular_resolution = None  # type: np.ndarray
    #: For background scans, the choice of Qz for the
    #: points according to theta (sample angle), 2theta (detector angle)
    #: or qz (Qz value of background computed from sample and detector angle)
    #: How to calculate Qz from instrument angles.
    #:
    #: **actual**
    #:     calculates Qx and Qz as (x,z)-components of
    #:     $(\vec k_{\text{out}} - \vec k_\text{in})$ in sample coordinates,
    #: **detector**
    #:     ignores the sample angle and calculates Qz
    #:     as $(4\pi/\lambda \sin(\theta_\text{detector}/2))$,
    #: **sample**
    #:     ignores the detector angle and calculates Qz
    #:     as $(4\pi/\lambda \sin(\theta_\text{sample}))$
    #: **target**
    #:     uses the user-supplied Qz_target values
    Qz_basis = 'actual'
    #: The target Qz value given in the data file; or NaN if not available
    Qz_target = None  # type: np.ndarray
    scan_value = None  # type: List[np.ndarray]
    scan_label = None  # type: List[str]
    scan_units = None  # type: List[str]

    _intent = Intent.none
    _v = None
    _dv = None

    ## Data representation for generic plotter as (x,y,z,v) -> (qz,qx,qy,Iq)
    ## TODO: subclass Data so we get pixel edges calculations
    #def _getx(self): return self.Qz
    #def _gety(self): return self.Qx
    #def _getz(self): return self.Qy
    #x,xlabel,xunits = property(_getx),"Qx","inv A"
    #y,ylabel,yunits = property(_gety),"Qy","inv A"
    #z,zlabel,zunits = property(_getz),"Qz","inv A"
    @property
    def intent(self):
        """Purpose of the measurement."""
        return self._intent

    @intent.setter
    def intent(self, v):
        # Note: not setting x value with the label since the returned x should
        # correspond to the underlying value even if it has been updated since
        # the measurement intent was set.
        self._intent = v
        if Intent.isspec(v) or Intent.isback(v):
            self.xlabel, self.xunits = "Qz", "1/Ang"
        elif Intent.isrock(v):
            self.xlabel, self.xunits = "Qx", "1/Ang"
        elif Intent.isslit(v):
            #self.xlabel, self.xunits = "angular resolution", "degrees 1-sigma"
            self.xlabel, self.xunits = "slit 1 opening", "mm"
        elif Intent.isscan(v):
            self.xlabel, self.xunits = self.scan_label[0], self.scan_units[0]
        else:
            self.xlabel, self.xunits = "point", ""

    @property
    def x(self):
        # Return different x depending on intent
        intent = self.intent
        if Intent.isback(intent) or Intent.isspec(intent):
            return self.Qz
        elif Intent.isrock(intent):
            return self.Qx
        elif Intent.isslit(intent):
            return self.slit1.x
            #return self.angular_resolution
        elif Intent.isscan(intent):
            return self.scan_value[0]
        else:
            return np.arange(1, len(self.v)+1)

    @property
    def dx(self):
        return self.dQ

    @property
    def v(self):
        return self.detector.counts if self._v is None else self._v

    @v.setter
    def v(self, v):
        self._v = v

    @property
    def dv(self):
        return sqrt(self.detector.counts_variance) if self._dv is None else self._dv

    @dv.setter
    def dv(self, dv):
        self._dv = dv

    @property
    def Qz(self):
        A, B, L = self.sample.angle_x, self.detector.angle_x, self.detector.wavelength
        if self.Qz_basis == 'actual':
            retval = 2*pi/L * (sin(radians(B - A)) + sin(radians(A)))
        elif self.Qz_basis == 'detector':
            retval = 4*pi/L * (sin(radians(B)/2.0))
        elif self.Qz_basis == 'sample':
            retval = 4*pi/L * (sin(radians(A)))
        elif self.Qz_basis == 'target':
            retval = self.Qz_target
        else:
            raise KeyError("Qz basis must be one of [actual, detector, sample, target]")
        return retval

    @property
    def Qx(self):
        A, B, L = self.sample.angle_x, self.detector.angle_x, self.detector.wavelength
        if self.Qz_basis == 'actual':
            return 2*pi/L * (cos(radians(B - A)) - cos(radians(A)))
        else:
            return np.zeros_like(A)

    @property
    def dQ(self):
        if self.angular_resolution is None:
            raise ValueError("Need to estimate divergence before requesting dQ")
        T, dT = self.sample.angle_x, self.angular_resolution+self.sample.broadening
        L, dL = self.detector.wavelength, self.detector.wavelength_resolution
        return resolution.dTdL2dQ(T, dT, L, dL)

    @property
    def columns(self):
        from copy import deepcopy
        from collections import OrderedDict
        data_columns = OrderedDict([
            ('x', {'label': self.xlabel, 'units': self.xunits, 'errorbars': 'dx'}),
            ('v', {'label': self.vlabel, 'units': self.vunits, 'errorbars': 'dv'}),
            ('Qz', {'label': 'Qz', 'units': "1/Ang"}),
            ('Qz_target', {'label': 'Target Qz', 'units': '1/Ang'}),
            ('Qx', {'label': 'Qx', 'units': "1/Ang"}),
            ('angular_resolution', {'label': 'Angular Resolution (1-sigma)', 'units': 'degrees'})
        ])
        for subclsnm in ['sample', 'detector', 'monitor', 'slit1', 'slit2', 'slit3', 'slit4']:
            subcls = getattr(self, subclsnm, None)
            if subcls is None:
                continue
            sub_cols = deepcopy(getattr(subcls, 'columns', {}))
            for col in sub_cols.keys():
                # units are defined for the subcolumns, but nothing else... do that here:
                sub_col = sub_cols[col]
                v = getattr(subcls, col, None)
                if v is not None and hasattr(v, 'size') and v.size > 0:
                    label = "%s/%s" % (subclsnm, col)
                    sub_col['label'] = label
                    data_columns[label] = sub_col
        if self.scan_value is not None:
            for si, sv in enumerate(self.scan_value):
                new_col = {};
                new_label = self.scan_label[si]
                new_col['label'] = new_label
                new_col['is_scan'] = True
                new_col['units'] = self.scan_units[si]
                data_columns[new_label] = new_col
            
        return data_columns

    def apply_mask(self, mask_indices):
        """in-place masking of all data that is maskable"""
        def check_array(v):
            return isinstance(v, np.ndarray)

        def make_mask(v, mask_indices):
            mask = np.ones_like(v, dtype="bool")
            mask[mask_indices] = False
            return mask

        for prop in ['_v', '_dv', 'angular_resolution', 'Qz_target']:
            v = getattr(self, prop, None)
            if check_array(v):
                setattr(self, prop, v[make_mask(v, mask_indices)])

        self.scan_value = [v[make_mask(v, mask_indices)] if check_array(v) else v for v in self.scan_value]

        for subclsnm in ['sample', 'detector', 'monitor', 'slit1', 'slit2', 'slit3', 'slit4']:
            subcls = getattr(self, subclsnm, None)
            if subcls is None:
                continue
            sub_cols = getattr(subcls, 'columns', {})
            for col in sub_cols.keys():
                v = getattr(subcls, col, None)
                if check_array(v): setattr(subcls, col, v[make_mask(v, mask_indices)])
                # handle variance
                dv_name = sub_cols[col].get('variance', None)
                if dv_name is not None:
                    dv = getattr(subcls, dv_name, None)
                    if check_array(dv): setattr(subcls, dv_name, dv[make_mask(dv, mask_indices)])

    def __init__(self, **kw):
        for attr, cls in ReflData._groups:
            setattr(self, attr, cls())
        self.warnings = []
        self.messages = []
        Group.__init__(self, **kw)

    def __str__(self):
        base = [_str(self, indent=2)]
        others = ["".join(("  ", s, "\n", str(getattr(self, s))))
                  for s, _ in ReflData._groups]
        return "\n".join(base+others+self.messages)

    def todict(self):
        state = _toDict(self)
        groups = dict((s, _toDict(getattr(self, s)))
                      for s, _ in ReflData._groups)
        state.update(groups)
        return state

    def fromdict(self, state):
        props = dict((k, v) for k, v in state.items() if k in self._fields)
        props = _fromDict(props)
        for k, v in props.items():
            setattr(self, k, v)
        for attr, cls in ReflData._groups:
            props = _fromDict(state[attr])
            setattr(self, attr, cls(**props))

    def __or__(self, pipeline):
        return pipeline(self)

    def __ior__(self, pipeline):
        return pipeline.apply_and_log(self)

    def warn(self, msg):
        """Record a warning that should be displayed to the user"""
        warnings.warn(msg)
        self.warnings.append(msg)

    def log(self, msg):
        """Record corrections that have been applied to the data"""
        #print "log:",msg
        self.messages.append(msg)

    def log_dependency(self, label, other):
        if other.messages:
            self.messages.append(label + ":")
            self.messages.extend("  "+s for s in other.messages)
        if other.warnings:
            self.warnings.append(label + ":")
            self.warnings.extend("  "+s for s in other.warnings)

    def plot(self, label=None):
        from matplotlib import pyplot as plt
        if label is None:
            label = self.name+self.polarization
        xerr = self.dx if self.angular_resolution is not None else None
        x, dx, xunits, xlabel = self.x, xerr, self.xunits, self.xlabel
        #x, dx, xunits, xlabel = self.detector.angle_x, self.angular_resolution, 'detector angle', 'deg'
        plt.errorbar(x, self.v, yerr=self.dv, xerr=xerr, label=label, fmt='.')
        plt.xlabel("%s (%s)"%(xlabel, xunits) if xunits else xlabel)
        plt.ylabel("%s (%s)"%(self.vlabel, self.vunits) if self.vunits else self.vlabel)
        if not Intent.isslit(self.intent):
            plt.yscale('log')

    def save(self, filename):
        with open(filename, 'w') as fid:
            fid.write(self.export())

    def export(self):
        fid = BytesIO()  # numpy.savetxt requires a byte stream
        for n in ['name', 'entry', 'polarization']:
            _write_key_value(fid, n, getattr(self, n))
        wavelength = getattr(self.detector, "wavelength", None)
        wavelength_resolution = getattr(self.detector, "wavelength_resolution", None)
        if wavelength is not None:
            _write_key_value(fid, "wavelength", float(wavelength[0]))
        if wavelength_resolution is not None:
            _write_key_value(fid, "wavelength_resolution", float(wavelength_resolution[0]))
        if Intent.isscan(self.intent):
            _write_key_value(fid, "columns", list(self.columns.keys()))
            _write_key_value(fid, "units", [c.get("units", "") for c in self.columns.values()])
            # add column headers
            header_string = "\t".join(list(self.columns.keys())) + "\n"
            if IS_PY3:
                header_string = header_string.encode('utf-8')
            fid.write(header_string)
            def get_item(obj, path):
                result = obj
                keylist = path.split("/")
                while len(keylist) > 0:
                    result = getattr(result, keylist.pop(0), {})
                return result
            data_arrays = [self.scan_value[self.scan_label.index(p)] if v.get('is_scan', False) else get_item(self, p) for p,v in self.columns.items()]
            data_arrays = [np.resize(d, self.points) for d in data_arrays]
            format_string = "\t".join(["%s" if d.dtype.kind in ["S", "U"] else "%.10e" for d in data_arrays]) + "\n"
            for i in range(self.points):
                datarow = format_string % tuple([d[i] for d in data_arrays])
                if IS_PY3:
                    datarow = datarow.encode('utf-8')
                fid.write(datarow)
            export_string = fid.getvalue()
            if IS_PY3:
                export_string = export_string.decode('utf-8')
            name = getattr(self, "name", "default_name")
            entry = getattr(self, "entry", "default_entry")
            return {"name": name, "entry": entry, "export_string": export_string, "file_suffix": ".dat"}
        else:
            _write_key_value(fid, "columns", [self.xlabel, self.vlabel, "uncertainty", "resolution"])
            _write_key_value(fid, "units", [self.xunits, self.vunits, self.vunits, self.xunits])
            data = np.vstack([self.x, self.v, self.dv, self.dx]).T
            np.savetxt(fid, data, fmt="%.10e")
            export_string = fid.getvalue()
            if IS_PY3:
                export_string = export_string.decode('utf-8')
            name = getattr(self, "name", "default_name")
            entry = getattr(self, "entry", "default_entry")
            return {"name": name, "entry": entry, "export_string": export_string, "file_suffix": ".refl"}

    


    def get_plottable(self):
        return self.todict()

    def get_metadata(self):
        return self.todict()

def _write_key_value(fid, key, value):
    value_str = json.dumps(value)
    if IS_PY3:
        fid.write('# "{0}": {1}\n'.format(key, value_str).encode('utf-8'))
    else:
        fid.write('# "%s": %s\n'%(key, value_str))

def _str(object, indent=4):
    """
    Helper function: document data object by convert attributes listed in
    properties into a string.
    """
    props = [a + "=" + str(getattr(object, a)) for a in object._fields]
    prefix = " "*indent
    return prefix+("\n"+prefix).join(props)

def _toDict(obj):
    props = {}
    properties = list(getattr(obj, '_fields', ()))
    properties += list(getattr(obj, '_props', ()))
    for a in properties:
        props[a] = _toDictItem(getattr(obj, a))
    return props

def _toDictItem(obj):
    if isinstance(obj, np.integer):
        obj = int(obj)
    elif isinstance(obj, np.floating):
        obj = float(obj)
    elif isinstance(obj, np.ndarray):
        obj = obj.tolist()
    elif isinstance(obj, datetime.datetime):
        obj = [obj.year, obj.month, obj.day, obj.hour, obj.minute, obj.second]
    elif isinstance(obj, list):
        obj = [_toDictItem(a) for a in obj]
    return obj

def _fromDict(props):
    # Note: timestamps must have the property named "date"
    for name, value in props.items():
        if isinstance(value, list) and value:
            if all(isinstance(v, (int, float)) for v in value):
                props[name] = np.asarray(value)
        elif name == 'date':
            props[name] = datetime.datetime(*value)
    return props


def _set(object, kw):
    """
    Helper function: distribute the __init__ keyword parameters to
    individual attributes of an object, raising AttributeError if
    the class does not define the given attribute.

    Example:

        def __init__(self, **kw): _set(self,kw)
    """
    for k, v in kw.items():
        # this will fail with an attribute error for incorrect keys
        getattr(object, k)
        setattr(object, k, v)
