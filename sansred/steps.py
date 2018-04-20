"""
SANS reduction steps
====================

Set of reduction steps for SANS reduction.
"""

from __future__ import print_function

from posixpath import basename, join
from copy import copy, deepcopy
from io import BytesIO

import numpy as np

from dataflow.lib.uncertainty import Uncertainty
from dataflow.lib import uncertainty

from .sansdata import SansData, Sans1dData, Parameters

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
    from dataflow.fetch import url_get

    path, mtime, entries = fileinfo['path'], fileinfo['mtime'], fileinfo['entries']
    name = basename(path)
    fid = BytesIO(url_get(fileinfo))
    nx_entries = LoadMAGIKPSD.load_entries(name, fid, entries=entries)
    fid.close()
    return nx_entries

@cache
@module
def LoadSANS(filelist=None, flip=False, transpose=False, check_timestamps=True):
    """
    loads a data file into a SansData obj and returns that.
    Checks to see if data being loaded is 2D; if not, quits

    **Inputs**

    filelist (fileinfo[]): Files to open.

    flip (bool): flip the data up and down

    transpose (bool): transpose the data
    
    check_timestamps (bool): verify that timestamps on file match request

    **Returns**

    output (sans2d[]): all the entries loaded.

    2018-04-20 Brian Maranville
    """
    from dataflow.fetch import url_get
    from .loader import readSANSNexuz
    if filelist is None:
        filelist = []
    data = []
    for fileinfo in filelist:
        path, mtime, entries = fileinfo['path'], fileinfo.get('mtime', None), fileinfo.get('entries', None)
        name = basename(path)
        fid = BytesIO(url_get(fileinfo, mtime_check=check_timestamps))
        entries = readSANSNexuz(name, fid)
        for entry in entries:
            if flip:
                entry.data.x = np.fliplr(entry.data.x)
            if transpose:
                entry.data.x = entry.data.x.T
        data.extend(entries)

    return data

"""
    Variable vz_1 = 3.956e5		//velocity [cm/s] of 1 A neutron
	Variable g = 981.0				//gravity acceleration [cm/s^2]
	Variable m_h	= 252.8			// m/h [=] s/cm^2
////	//
	Variable yg_d,acc,sdd,ssd,lambda0,DL_L,sig_l
	Variable var_qlx,var_qly,var_ql,qx,qy,sig_perp,sig_para, sig_para_new

	G = 981.  //!	ACCELERATION OF GRAVITY, CM/SEC^2
	acc = vz_1 		//	3.956E5 //!	CONVERT WAVELENGTH TO VELOCITY CM/SEC
	SDD = L2		//1317
	SSD = L1		//1627 		//cm
	lambda0 = lambda		//		15
	DL_L = lambdaWidth		//0.236
	SIG_L = DL_L/sqrt(6)
	YG_d = -0.5*G*SDD*(SSD+SDD)*(LAMBDA0/acc)^2
/////	Print "DISTANCE BEAM FALLS DUE TO GRAVITY (CM) = ",YG
//		Print "Gravity q* = ",-2*pi/lambda0*2*yg_d/sdd

	sig_perp = kap*kap/12 * (3*(S1/L1)^2 + 3*(S2/LP)^2 + (proj_DDet/L2)^2)
	sig_perp = sqrt(sig_perp)


	FindQxQy(inQ,phi,qx,qy)

// missing a factor of 2 here, and the form is different than the paper, so re-write
//	VAR_QLY = SIG_L^2 * (QY+4*PI*YG_d/(2*SDD*LAMBDA0))^2
//	VAR_QLX = (SIG_L*QX)^2
//	VAR_QL = VAR_QLY + VAR_QLX  //! WAVELENGTH CONTRIBUTION TO VARIANCE
//	sig_para = (sig_perp^2 + VAR_QL)^0.5

	// r_dist is passed in, [=]cm
	// from the paper
	a_val = 0.5*G*SDD*(SSD+SDD)*m_h^2 * 1e-16		//units now are cm /(A^2)

    r_dist = sqrt(  (pixSize*((p+1)-xctr))^2 +  (pixSize*((q+1)-yctr)+(2)*yg_d)^2 )		//radial distance from ctr to pt

	var_QL = 1/6*(kap/SDD)^2*(DL_L)^2*(r_dist^2 - 4*r_dist*a_val*lambda0^2*sin(phi) + 4*a_val^2*lambda0^4)
	sig_para_new = (sig_perp^2 + VAR_QL)^0.5


///// return values PBR
	SigmaQX = sig_para_new
	SigmaQy = sig_perp

////

	results = "success"
	Return results
End
"""

#@cache
#@module
def calculateDQ(data):
    """
    Add the dQ column to the data, based on slit apertures and gravity
    r_dist is the real-space distance from ctr of detector to QxQy pixel location

    From `NCNR_Utils.ipf` (Steve R. Kline) in which the math is in turn from:

    | D.F.R Mildner, J.G. Barker & S.R. Kline J. Appl. Cryst. (2011). 44, 1127-1129.
    | *The effect of gravity on the resolution of small-angle neutron diffraction peaks*
    | [ doi:10.1107/S0021889811033322 ]

    **Inputs**

    data (sans2d): data in

    **Returns**

    output (sans2d): data in with dQ column filled in

    2017-06-16  Brian Maranville
    """

    G = 981.  #!    ACCELERATION OF GRAVITY, CM/SEC^2
    acc = vz_1 = 3.956e5 # velocity [cm/s] of 1 A neutron
    m_h	= 252.8			# m/h [=] s/cm^2
    # the detector pixel is square, so correct for phi
    DDetX = data.metadata["det.pixelsizex"]
    DDetY = data.metadata["det.pixelsizey"]
    x_offset = data.metadata["det.pixeloffsetx"]
    y_offset = data.metadata["det.pixeloffsety"]
    xctr = data.metadata["det.beamx"]
    yctr = data.metadata["det.beamy"]

    shape = data.data.x.shape
    x, y = np.indices(shape)
    X = DDetX * (x-xctr)
    Y = DDetY * (y-yctr)

    apOff = data.metadata["sample.position"]
    S1 = data.metadata["resolution.ap1"]
    S2 = data.metadata["resolution.ap2"]
    L1 = data.metadata["resolution.ap12dis"] - apOff
    L2 = data.metadata["det.dis"] + apOff
    LP = 1.0/( 1.0/L1 + 1.0/L2)
    SDD = L2
    SSD = L1
    lambda0 = data.metadata["resolution.lmda"]    #  15
    DL_L = data.metadata["resolution.dlmda"]    # 0.236
    YG_d = -0.5*G*SDD*(SSD+SDD)*(lambda0/acc)**2
    kap = 2.0*np.pi/lambda0
    phi = np.mod(np.arctan2(Y + 2.0*YG_d, X), 2.0*np.pi) # from x-axis, from 0 to 2PI
    proj_DDet = np.abs(DDetX*np.cos(phi)) + np.abs(DDetY*np.sin(phi))
    r_dist = np.sqrt(X**2 + (Y + 2.0*YG_d)**2)  #radial distance from ctr to pt

    sig_perp = kap*kap/12.0 * (3.0*(S1/L1)**2 + 3.0*(S2/LP)**2 + (proj_DDet/L2)**2)
    sig_perp = np.sqrt(sig_perp)

    a_val = 0.5*G*SDD*(SSD+SDD)*m_h**2 * 1e-16		# units now are cm /(A^2)

    var_QL = 1.0/6.0*((kap/SDD)**2)*(DL_L**2)*(r_dist**2 - 4.0*r_dist*a_val*(lambda0**2)*np.sin(phi) + 4.0*(a_val**2)*(lambda0**4))
    sig_para_new = np.sqrt(sig_perp**2 + var_QL)

    data.dq_perp = sig_perp
    data.dq_para = sig_para_new
    return data

@nocache
@module
def PixelsToQ(data, beam_center=[None,None], correct_solid_angle=True):
    """
    generate a q_map for sansdata. Each pixel will have 4 values: (qx, qy, q, theta)


    **Inputs**

    data (sans2d): data in

    beam_center {Beam Center Override} (coordinate?): If not blank, will override the beamx and beamy from the datafile.

    correct_solid_angle {Correct solid angle} (bool): Apply correction for mapping
        curved Ewald sphere to flat detector

    **Returns**

    output (sans2d): converted to I vs. Qx, Qy

    2016-04-16 Brian Maranville
    """

    L2 = data.metadata['det.dis']
    beamx_override, beamy_override = beam_center
    x0 = beamx_override if beamx_override is not None else data.metadata['det.beamx'] #should be close to 64
    y0 = beamy_override if beamy_override is not None else data.metadata['det.beamy'] #should be close to 64
    wavelength = data.metadata['resolution.lmda']
    shape = data.data.x.shape

    qx = np.empty(shape, 'float')
    qy = np.empty(shape, 'float')

    x, y = np.indices(shape) + 0.5 # left, bottom edge of first pixel is 0.5, 0.5 pix.
    X = data.metadata['det.pixelsizex']*(x-x0) # in mm in nexus, but converted by loader
    Y = data.metadata['det.pixelsizey']*(y-y0)
    r = np.sqrt(X**2+Y**2)
    theta = np.arctan2(r, L2)/2 #remember to convert L2 to cm from meters
    q = (4*np.pi/wavelength)*np.sin(theta)
    alpha = np.arctan2(Y, X)
    qx = q*np.cos(alpha)
    qy = q*np.sin(alpha)
    if correct_solid_angle:
        data.data.x = data.data.x * (np.cos(theta)**3)
    res = data.copy()
    #Adding res.q
    res.q = q
    res.qx = qx
    res.qy = qy
    res.metadata['det.beamx'] = x0
    res.metadata['det.beamy'] = y0
    q0 = (4*np.pi/wavelength)
    res.qx_min = q0/2.0 * data.metadata['det.pixelsizex']*(0.5 - x0)/ L2
    res.qy_min = q0/2.0 * data.metadata['det.pixelsizex']*(0.5 - y0)/ L2
    res.qx_max = q0/2.0 * data.metadata['det.pixelsizex']*(128.5 - x0)/ L2
    res.qy_max = q0/2.0 * data.metadata['det.pixelsizex']*(128.5 - y0)/ L2
    res.xlabel = "Qx (inv. Angstroms)"
    res.ylabel = "Qy (inv. Angstroms)"
    res.theta = theta
    return res

@cache
@module
def circular_av(data):
    """
    Using a circular average, it converts data to 1D (Q vs. I)


    **Inputs**

    data (sans2d): data in

    **Returns**

    nominal_output (sans1d): converted to I vs. nominal Q

    mean_output (sans1d): converted to I vs. mean Q within integrated region

    2016-04-11 Brian Maranville
    """
    from .draw_annulus_aa import annular_mask_antialiased

    #annular_mask_antialiased(shape, center, inner_radius, outer_radius,
    #                         background_value=0.0, mask_value=1.0, oversampling=8)

    # calculate the change in q that corresponds to a change in pixel of 1
    if data.qx is None:
        raise ValueError("Q is not defined - convert pixels to Q first")

    q_per_pixel = data.qx[1, 0]-data.qx[0, 0] / 1.0

    # for now, we'll make the q-bins have the same width as a single pixel
    step = q_per_pixel
    shape1 = data.data.x.shape
    x0 = data.metadata['det.beamx'] # should be close to 64
    y0 = data.metadata['det.beamy'] # should be close to 64
    L2 = data.metadata['det.dis']
    wavelength = data.metadata['resolution.lmda']

    center = (x0, y0)
    Qmax = data.q.max()
    Q = np.arange(step, Qmax, step) # start at first pixel out.
    Q_edges = np.zeros((Q.shape[0] + 1,), dtype="float")
    Q_edges[1:] = Q
    Q_edges += step/2.0 # get a range from step/2.0 to (Qmax + step/2.0)
    r_edges = L2 * np.tan(2.0*np.arcsin(Q_edges * wavelength/(4*np.pi))) / data.metadata['det.pixelsizex']
    Q_mean = []
    Q_mean_error = []
    I = []
    I_error = []
    dx = np.zeros_like(Q, dtype="float")
    for i, qq in enumerate(Q):
        # inner radius is the q we're at right now, converted to pixel dimensions:
        inner_r = r_edges[i]
        # outer radius is the q of the next bin, also converted to pixel dimensions:
        outer_r = r_edges[i+1]
        #print(i, qq, inner_r, outer_r)
        mask = annular_mask_antialiased(shape1, center, inner_r, outer_r)
        if IGNORE_CORNER_PIXELS:
            mask[0, 0] = mask[-1, 0] = mask[-1, -1] = mask[0, -1] = 0.0
        #print("Mask: ", mask)
        integrated_q = uncertainty.sum(data.q*mask.T)
        integrated_intensity = uncertainty.sum(data.data*mask.T)
        #error = getPoissonUncertainty(integrated_intensity)
        #error = np.sqrt(integrated_intensity)
        mask_sum = np.sum(mask)
        if mask_sum > 0.0:
            norm_integrated_intensity = integrated_intensity / mask_sum
            norm_integrated_q = integrated_q / mask_sum
            #error /= mask_sum
        else:
            norm_integrated_intensity = integrated_intensity
            norm_integrated_q = integrated_q

        I.append(norm_integrated_intensity.x) # not multiplying by step anymore
        I_error.append(norm_integrated_intensity.variance)
        Q_mean.append(norm_integrated_q)
        Q_mean_error.append(0.0)

    I = np.array(I, dtype="float")
    I_error = np.array(I_error, dtype="float")
    Q_mean = np.array(Q_mean, dtype="float")
    Q_mean_error = np.array(Q_mean_error, dtype="float")

    nominal_output = Sans1dData(Q, I, dx=dx, dv=I_error, xlabel="Q", vlabel="I",
                        xunits="inv. A", vunits="neutrons")
    nominal_output.metadata = deepcopy(data.metadata)
    nominal_output.metadata['extra_label'] = "_circ"

    mean_output = Sans1dData(Q_mean, I, dx=Q_mean_error, dv=I_error, xlabel="Q", vlabel="I",
                        xunits="inv. A", vunits="neutrons")
    mean_output.metadata = deepcopy(data.metadata)
    mean_output.metadata['extra_label'] = "_circ"

    return nominal_output, mean_output

@cache
@module
def sector_cut(data, angle=0.0, width=90.0, mirror=True):
    """
    Using annular averging, it converts data to 1D (Q vs. I)
    over a particular angle range


    **Inputs**

    data (sans2d): data in

    angle (float): center angle of sector cut (degrees)

    width (float): width of cut (degrees)

    mirror (bool): extend sector cut on both sides of origin
        (when false, integrates over a single cone centered at angle)

    **Returns**

    nominal_output (sans1d): converted to I vs. nominal Q

    mean_output (sans1d): converted to I vs. mean Q within integrated region

    2016-04-15 Brian Maranville
    """
    from .draw_annulus_aa import sector_cut_antialiased

    #annular_mask_antialiased(shape, center, inner_radius, outer_radius,
    #                         background_value=0.0, mask_value=1.0, oversampling=8)

    # calculate the change in q that corresponds to a change in pixel of 1
    q_per_pixel = data.qx[1, 0]-data.qx[0, 0] / 1.0

    # for now, we'll make the q-bins have the same width as a single pixel
    step = q_per_pixel
    shape1 = data.data.x.shape
    x0 = data.metadata['det.beamx'] # should be close to 64
    y0 = data.metadata['det.beamy'] # should be close to 64
    L2 = data.metadata['det.dis']
    wavelength = data.metadata['resolution.lmda']

    center = (x0, y0)
    Qmax = data.q.max()
    Q = np.arange(step, Qmax, step) # start at first pixel out.
    Q_edges = np.zeros((Q.shape[0] + 1,), dtype="float")
    Q_edges[1:] = Q
    Q_edges += step/2.0 # get a range from step/2.0 to (Qmax + step/2.0)
    r_edges = L2 * np.tan(2.0*np.arcsin(Q_edges * wavelength/(4*np.pi))) / data.metadata['det.pixelsizex']
    Q_mean = []
    Q_mean_error = []
    I = []
    I_error = []
    dx = np.zeros_like(Q, dtype="float")
    start_angle = np.radians(angle - width/2.0)
    end_angle = np.radians(angle + width/2.0)
    for i, qq in enumerate(Q):
        # inner radius is the q we're at right now, converted to pixel dimensions:
        inner_r = r_edges[i]
        # outer radius is the q of the next bin, also converted to pixel dimensions:
        outer_r = r_edges[i+1]
        #print(i, qq, inner_r, outer_r)
        mask = sector_cut_antialiased(shape1, center, inner_r, outer_r, start_angle=start_angle, end_angle=end_angle, mirror=mirror)
        if IGNORE_CORNER_PIXELS:
            mask[0, 0] = mask[-1, 0] = mask[-1, -1] = mask[0, -1] = 0.0
        #print("Mask: ", mask)
        integrated_q = uncertainty.sum(data.q*mask.T)
        integrated_intensity = uncertainty.sum(data.data*mask.T)
        #error = getPoissonUncertainty(integrated_intensity)
        #error = np.sqrt(integrated_intensity)
        mask_sum = np.sum(mask)
        if mask_sum > 0.0:
            norm_integrated_intensity = integrated_intensity / mask_sum
            norm_integrated_q = integrated_q / mask_sum
            #error /= mask_sum
        else:
            norm_integrated_intensity = integrated_intensity
            norm_integrated_q = integrated_q

        I.append(norm_integrated_intensity.x) # not multiplying by step anymore
        I_error.append(norm_integrated_intensity.variance)
        Q_mean.append(norm_integrated_q)
        Q_mean_error.append(0.0)

    I = np.array(I, dtype="float")
    I_error = np.array(I_error, dtype="float")
    Q_mean = np.array(Q_mean, dtype="float")
    Q_mean_error = np.array(Q_mean_error, dtype="float")

    nominal_output = Sans1dData(Q, I, dx=dx, dv=I_error, xlabel="Q", vlabel="I",
                        xunits="inv. A", vunits="neutrons")
    nominal_output.metadata = deepcopy(data.metadata)
    nominal_output.metadata['extra_label'] = "_%.1f" % (angle,)

    mean_output = Sans1dData(Q_mean, I, dx=Q_mean_error, dv=I_error, xlabel="Q", vlabel="I",
                        xunits="inv. A", vunits="neutrons")
    mean_output.metadata = deepcopy(data.metadata)
    mean_output.metadata['extra_label'] = "_%.1f" % (angle,)

    return nominal_output, mean_output

@module
def correct_detector_efficiency(sansdata):
    """
    Given a SansData object, corrects for the efficiency of the detection process

    **Inputs**

    sansdata (sans2d): data in

    **Returns**

    output (sans2d): corrected for efficiency

    2016-08-04 Brian Maranville and Andrew Jackson
    """

    L2 = sansdata.metadata['det.dis']
    lambd = sansdata.metadata["resolution.lmda"]
    shape = sansdata.data.x.shape
    (x0, y0) = np.shape(sansdata.data.x)
    x, y = np.indices(shape)
    X = sansdata.metadata['det.pixelsizex']/10.0*(x-x0/2)
    Y = sansdata.metadata['det.pixelsizey']/10.0*(y-y0/2)
    r = np.sqrt(X**2+Y**2)
    theta_det = np.arctan2(r, L2*100)/2

    stAl = 0.00967*lambd*0.8 # dimensionless, constants from JGB memo
    stHe = 0.146*lambd*2.5

    ff = (np.exp(-stAl/np.cos(theta_det))/np.exp(-stAl)
          * np.expm1(-stHe/np.cos(theta_det))/np.expm1(-stHe))

    res = sansdata.copy()
    res.data = res.data/ff

    # note that the theta calculated for this correction is based on the
    # center of the detector and NOT the center of the beam. Thus leave
    # the q-relevant theta alone.
    res.theta = copy(sansdata.theta)

    return res

@module
def correct_dead_time(sansdata, deadtime=1.0e-6):
    """
    Correct for the detector recovery time after each detected event
    (suppresses counts as count rate increases)

    **Inputs**

    sansdata (sans2d): data in

    deadtime (float): detector dead time (nonparalyzing?)

    **Returns**

    output (sans2d): corrected for dead time

    2010-01-03 Andrew Jackson?
    """

    dscale = 1.0/(1.0-deadtime*(np.sum(sansdata.data)/sansdata.metadata["run.rtime"]))

    result = sansdata.copy()
    result.data *= dscale
    return result

@module
def monitor_normalize(sansdata, mon0=1e8):
    """"
    Given a SansData object, normalize the data to the provided monitor

    **Inputs**

    sansdata (sans2d): data in

    mon0 (float): provided monitor

    **Returns**

    output (sans2d): corrected for dead time

    2010-01-01 Andrew Jackson?
    """
    monitor = sansdata.metadata['run.moncnt']
    res = sansdata.copy()
    res.data *= mon0/monitor
    return res

@module
def generate_transmission(in_beam, empty_beam, integration_box=[55, 74, 53, 72]):
    """
    To calculate the transmission, we integrate the intensity in a box
    for a measurement with the substance in the beam and with the substance
    out of the beam and take their ratio. The box is definied by xmin, xmax
    and ymin, ymax, I start counting at (0, 0).

    Coords are taken with reference to bottom left of the image.

    **Inputs**

    in_beam (sans2d): measurement with sample in the beam

    empty_beam (sans2d): measurement with no sample in the beam

    integration_box (range:xy): region over which to integrate

    **Returns**

    output (params): calculated transmission for the integration area

    2017-02-29 Brian Maranville
    """
    #I_in_beam = 0.0
    #I_empty_beam = 0.0
    #xmax, ymax = np.shape(in_beam.data.x)
    #print(xmax, ymax)
    # Vectorize this loop, it's quick, but could be quicker
    # test against this simple minded implementation
    #print(ymax-coords_bottom_left[1], ymax-coords_upper_right[1])

    #for x in range(coords_bottom_left[0], coords_upper_right[0]+1):
    #    for y in range(ymax-coords_upper_right[1], ymax-coords_bottom_left[1]+1):
    #        I_in_beam = I_in_beam+in_beam.data.x[x, y]
    #        I_empty_beam = I_empty_beam+empty_beam.data.x[x, y]

    xmin, xmax, ymin, ymax = map(int, integration_box)
    I_in_beam = np.sum(in_beam.data[xmin:xmax+1, ymin:ymax+1])
    I_empty_beam = np.sum(empty_beam.data[xmin:xmax+1, ymin:ymax+1])

    ratio = I_in_beam/I_empty_beam
    result = Parameters(factor=ratio.x, factor_variance=ratio.variance,
                        factor_err=np.sqrt(ratio.variance))

    return result

@module
def subtract(subtrahend, minuend):
    """
    Algebraic subtraction of datasets pixel by pixel

    **Inputs**

    subtrahend (sans2d): a in (a-b) = c

    minuend (sans2d?): b in (a-b) = c, defaults to zero

    **Returns**

    output (sans2d): c in (a-b) = c

    2010-01-01 unknown
    """
    if minuend is not None:
        return subtrahend - minuend
    else:
        return subtrahend

@module
def product(data, factor_param, propagate_error=True):
    """
    Algebraic multiplication of dataset

    **Inputs**

    data (sans2d): data in (a)

    factor_param (params?): multiplication factor (b), defaults to 1

    propagate_error {Propagate error} (bool): if factor_error is passed in, use it

    **Returns**

    output (sans2d): result (c in a*b = c)

    2010-01-02 unknown
    """
    if factor_param is not None:
        if propagate_error:
            variance = factor_param.get('factor_variance', 0.0)
        return data * Uncertainty(factor_param.get('factor', 1.0), variance)
    else:
        return data

@module
def divide(data, factor_param):
    """
    Algebraic multiplication of dataset

    **Inputs**

    data (sans2d): data in (a)

    factor_param (params): denominator factor (b), defaults to 1

    **Returns**

    output (sans2d): result (c in a*b = c)

    2010-01-01 unknown
    """
    if factor_param is not None:
        return data.__truediv__(factor_param['factor'])
    else:
        return data

def correct_solid_angle(sansdata):
    """
    Given a SansData with q, qx, qy, and theta images defined,
    correct for the fact that the detector is flat and the Ewald sphere
    is curved. Need to calculate theta first, so do PixelsToQ before this.

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
def correct_detector_sensitivity(sansdata, sensitivity):
    """"
    Given a SansData object and an sensitivity map generated from a div,
    correct for the efficiency of the detector. Recall that sensitivities are
    generated by taking a measurement of plexiglass and dividing by the
    mean value

    **Inputs**

    sansdata (sans2d): data in (a)

    sensitivity (sans2d): data in (b)

    **Returns**

    output (sans2d): result c in a/b = c

    2017-01-04 unknown
    """
    res = sansdata.copy()
    res.data /= sensitivity.data

    return res

def lookup_attenuation(instrument_name, attenNo, wavelength):
    from .attenuation_constants import attenuation
    if attenNo == 0:
        return {"att": 1.0, "att_err": 0.0}

    ai = attenuation[instrument_name]
    attenNoStr = format(int(attenNo), 'd')
    att = ai['att'][attenNoStr]
    att_err = ai['att_err'][attenNoStr]
    wavelength_key = ai['lambda']

    wmin = np.min(wavelength_key)
    wmax = np.max(wavelength_key)
    if wavelength < wmin or wavelength > wmax:
        raise ValueError("Wavelength out of calibration range (%f, %f). You must manually enter the absolute parameters" % (wmin, wmax))

    w = np.array([wavelength], dtype="float")
    att_interp = np.interp(w, wavelength_key, att, 1.0, np.nan)
    att_err_interp = np.interp(w, wavelength_key, att_err)
    return {"att": att_interp[0], "att_err": att_err_interp[0]} # err here is percent error

@cache
@module
def correct_attenuation(sample, instrument="NG7"):
    """
    Divide by the attenuation factor from the lookup tables for the instrument

    **Inputs**

    sample (sans2d): measurement

    instrument (opt:NG7|NGB|NGB30): instrument name

    **Returns**

    atten_corrected (sans2d): corrected measurement
    """
    attenNo = sample.metadata['run.atten']
    wavelength = sample.metadata['resolution.lmda']
    attenuation = lookup_attenuation(instrument, attenNo, wavelength)
    att = attenuation['att']
    percent_err = attenuation['att_err']
    att_variance = (att*percent_err/100.0)**2
    denominator = Uncertainty(att, att_variance)
    atten_corrected = sample.copy()
    atten_corrected.attenuation_corrected = True
    atten_corrected.data /= denominator
    return atten_corrected

@cache
@module
def absolute_scaling(sample, empty, div, Tsam, instrument="NG7", integration_box=[55, 74, 53, 72]):
    """
    Calculate absolute scaling

    Coords are taken with reference to bottom left of the image.

    **Inputs**

    sample (sans2d): measurement with sample in the beam

    empty (sans2d): measurement with no sample in the beam

    div (sans2d): DIV measurement

    Tsam (params): sample transmission

    instrument (opt:NG7|NGB|NGB30): instrument name, should be NG7 or NG3

    integration_box (range:xy): region over which to integrate

    **Returns**

    abs (sans2d): data on absolute scale

    2017-01-13 Andrew Jackson
    """
    # data (that is going through reduction), empty beam,
    # div, Transmission of the sample, instrument(NG3.NG5, NG7)
    # ALL from metadata
    detCnt = empty.metadata['run.detcnt']
    countTime = empty.metadata['run.rtime']
    monCnt = empty.metadata['run.moncnt']
    sdd = empty.metadata['det.dis'] # already in cm
    pixel = empty.metadata['det.pixelsizex'] # already in cm
    lambd = wavelength = empty.metadata['resolution.lmda']

    if not empty.attenuation_corrected:
        attenNo = empty.metadata['run.atten']
        # Need attenTrans - AttenuationFactor - need to know whether NG3, NG5 or NG7 (acctStr)
        attenuation = lookup_attenuation(instrument, attenNo, wavelength)
        att = attenuation['att']
        percent_err = attenuation['att_err']
        att_variance = (att*percent_err/100.0)**2
        attenTrans = Uncertainty(att, att_variance)
    else:
        # If empty is already corrected for attenuation, don't do it here:
        attenTrans = Uncertainty(1.0, 0.0)

    #-------------------------------------------------------------------------------------#

    # Correct empty beam by the sensitivity
    data = empty.__truediv__(div.data)
    # Then take the sum in XY box, including stat. error
    xmin, xmax, ymin, ymax = map(int, integration_box)
    detCnt = np.sum(data.data[xmin:xmax+1, ymin:ymax+1])
    print("DETCNT: ", detCnt)

    #------End Result-------#
    # This assumes that the data is has not been normalized at all.
    # Thus either fix this or pass un-normalized data.
    # Compute kappa = incident intensity * solid angle of the pixel
    kappa = detCnt / attenTrans * 1.0e8 / monCnt * (pixel/sdd)**2
    #print("Kappa: ", kappa)

    #utc_datetime = date.datetime.utcnow()
    #print(utc_datetime.strftime("%Y-%m-%d %H:%M:%S"))

    Tsam_factor = Uncertainty(Tsam['factor'], Tsam['factor_variance'])

    #-----Using Kappa to Scale data-----#
    Dsam = sample.metadata['sample.thk']
    ABS = sample.__mul__(1/(kappa*Dsam*Tsam_factor))
    #------------------------------------
    return ABS

@cache
@module
def patchData(data1, data2, xmin=55, xmax=74, ymin=53, ymax=72):
    """
    Copies data from data2 to data1 within the defined patch region
    (often used for processing DIV files)

    **Inputs**

    data1 (sans2d): measurement to be patched

    data2 (sans2d): measurement to get the patch from

    xmin (int): left pixel of patch box

    xmax (int): right pixel of patch box

    ymin (int): bottom pixel of patch box

    ymax (int): top pixel of patch box

    **Returns**

    patched (sans2d): data1 with patch applied from data2

    """

    patch_slice = (slice(xmin, xmax+1), slice(ymin, ymax+1))
    output = data1.copy()
    output.data[patch_slice] = data2.data[patch_slice]
    return output

@cache
@module
def addSimple(data):
    """
    Naive addition of counts and monitor from different datasets,
    assuming all datasets were taken under identical conditions
    (except for count time)

    Just adds together count time, counts and monitor.

    Use metadata from first dataset for output.

    **Inputs**

    data (sans2d[]): measurements to be added together

    **Returns**

    sum (sans2d): sum of inputs

    2017-06-29  Brian Maranville
    """

    output = data[0].copy()
    for d in data[1:]:
        output.data += d.data
        output.metadata['run.moncnt'] += d.metadata['run.moncnt']
        output.metadata['run.rtime'] += d.metadata['run.rtime']
        output.metadata['run.detcnt'] += d.metadata['run.detcnt']
    return output


@cache
@module
def makeDIV(data1, data2, patchbox=(55, 74, 53, 72)):
    """
    Use data2 to patch the beamstop from data1 within the defined box, then
    divide by total counts and multiply by number of pixels.

    **Inputs**

    data1 (sans2d): base measurement (to be patched and normalized)

    data2 (sans2d): measurement to get the patch from

    patchbox (range:xy): box to apply the patch in

    **Returns**

    DIV (sans2d): data1 with patch applied from data2 and normalized

    2016-04-20 Brian Maranville
    """

    print("patchbox:", patchbox)
    xmin, xmax, ymin, ymax = map(int, patchbox)

    DIV = patchData(data1, data2, xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax)

    DIV.data = DIV.data / np.sum(DIV.data) * DIV.data.x.size

    return DIV

@module
def radialToCylindrical(data, theta_offset = 0.0, oversample_th = 2.0, oversample_r = 2.0):
    """
    Convert radial data to cylindrical coordinates

    **Inputs**

    data (sans2d): data to be transformed

    theta_offset (float): move the bounds of the output from the default (0 to 360 deg)

    oversample_th (float): oversampling in theta (to increase fidelity of output)

    oversample_r (float): oversampling in r

    **Returns**

    cylindrical (sans2d): transformed data

    mask (sans2d): normalization array

    2017-05-26 Brian Maranville
    """

    from .cylindrical import ConvertToCylindrical

    if data.qx is None or data.qy is None:
        xmin = -data.metadata['det.beamx']
        xmax = xmin + 128
        ymin = -data.metadata['det.beamy']
        ymax = ymin + 128
    else:
        xmin = data.qx.min()
        xmax = data.qx.max()
        ymin = data.qy.min()
        ymax = data.qy.max()

    print(xmin, xmax, ymin, ymax)
    _, normalization, normalized, extent = ConvertToCylindrical(data.data.x.T, xmin, xmax, ymin, ymax, theta_offset=theta_offset, oversample_th=oversample_th, oversample_r=oversample_r)

    output = data.copy()
    output.aspect_ratio = None
    output.data = Uncertainty(normalized.T, normalized.T)

    mask = data.copy()
    mask.aspect_ratio = None
    mask.data = Uncertainty(normalization.T, normalization.T)

    if data.qx is not None:
        output.qx = np.linspace(extent[0], extent[1], normalized.shape[1])
        # abusing the qx property here to mean "other x"
        mask.qx = output.qx.copy()
        output.xlabel = mask.xlabel = "theta (degrees)"

    if data.qy is not None:
        output.qy = np.linspace(extent[2], extent[3], normalized.shape[0])
        # abusing the qy property here to mean "other y"
        mask.qy = output.qy.copy()
        output.ylabel = mask.ylabel = "Q (inv. Angstrom)"

    return output, mask

@module
def sliceData(data, slicebox=[None,None,None,None]):
    """
    Sum 2d data along both axes and return 1d datasets

    **Inputs**

    data (sans2d) : data in
    
    slicebox (range?:xy): region over which to integrate (in data coordinates)

    **Returns**

    xout (sans1d) : xslice

    yout (sans1d) : yslice

    2018-04-20 Brian Maranville
    """
    
    if slicebox is None:
        slicebox = [None, None, None, None]
    xmin, xmax, ymin, ymax = slicebox
    
    res = data.copy()
    if data.qx is None or data.qy is None:
        # then use pixels
        xslice = slice(int(np.ceil(xmin)) if xmin is not None else None, int(np.floor(xmax)) if xmax is not None else None)
        yslice = slice(int(np.ceil(ymin)) if ymin is not None else None, int(np.floor(ymax)) if ymax is not None else None)
        x_in = np.arange(data.data.x.shape[0])
        y_in = np.arange(data.data.x.shape[1])
        x_out = x_in[xslice]
        y_out = y_in[yslice]
        dx = np.zeros_like(x_out)
        dy = np.zeros_like(y_out)
        
    else:
        # then use q-values
        qxmin = data.qx_min if data.qx_min is not None else data.qx.min()
        qxmax = data.qx_max if data.qx_max is not None else data.qx.max()
        qx_in = np.linspace(qxmin, qxmax, data.data.x.shape[0])
        qymin = data.qy_min if data.qy_min is not None else data.qy.min()
        qymax = data.qy_max if data.qy_max is not None else data.qy.max()
        qy_in = np.linspace(qymin, qymax, data.data.x.shape[1])
        
        xslice = slice(get_index(qx_in, xmin), get_index(qx_in, xmax))
        yslice = slice(get_index(qy_in, ymin), get_index(qy_in, ymax))
        x_out = qx_in[xslice]
        y_out = qy_in[yslice]
        dx = np.zeros_like(x_out)
        dy = np.zeros_like(y_out)
        
    dataslice = (xslice, yslice)
    x_sum = uncertainty.sum(data.data[dataslice], axis=1)
    y_sum = uncertainty.sum(data.data[dataslice], axis=0)
    
    x_output = Sans1dData(x_out, x_sum.x, dx=dx, dv=x_sum.variance, xlabel=data.xlabel, vlabel="I",
                    xunits="", vunits="neutrons", metadata=data.metadata)
    y_output = Sans1dData(y_out, y_sum.x, dx=dy, dv=y_sum.variance, xlabel=data.ylabel, vlabel="I",
                    xunits="", vunits="neutrons", metadata=data.metadata)
                        
    return x_output, y_output


@cache
@module
def SuperLoadSANS(filelist=None, do_det_eff=True, do_deadtime=True,
                  deadtime=1.0e-6, do_mon_norm=True, do_atten_correct=False, mon0=1e8,
                  check_timestamps=True):
    """
    loads a data file into a SansData obj, and performs common reduction steps
    Checks to see if data being loaded is 2D; if not, quits


    **Inputs**

    filelist (fileinfo[]): Files to open.

    do_det_eff {Detector efficiency corr.} (bool): correct detector efficiency

    do_deadtime {Dead time corr.} (bool): correct for detector efficiency drop due to detector dead time

    deadtime {Dead time value} (float): value of the dead time in the calculation above

    do_atten_correct {Attenuation correction} (bool): correct intensity for the attenuators in the beam

    do_mon_norm {Monitor normalization} (bool): normalize data to a provided monitor value

    mon0 (float): provided monitor
    
    check_timestamps (bool): verify that timestamps on file match request

    **Returns**

    output (sans2d[]): all the entries loaded.

    2018-04-20 Brian Maranville
    """
    data = LoadSANS(filelist, flip=False, transpose=False, check_timestamps=check_timestamps)

    if do_det_eff:
        data = [correct_detector_efficiency(d) for d in data]
    if do_deadtime:
        data = [correct_dead_time(d, deadtime=deadtime) for d in data]
    if do_mon_norm:
        data = [monitor_normalize(d, mon0=mon0) for d in data]
    if do_atten_correct:
        data = [correct_attenuation(d) for d in data]

    return data

def get_index(t, x):
    if (x == "" or x == None):
        return None
    if float(x) > t.max():
        return None
    if float(x) < t.min():
        return None
    tord = np.argsort(t)
    return tord[np.searchsorted(t, float(x), sorter=tord)]

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
    hi = 0.5+np.sqrt(y+0.25)
    lo = -0.5+np.sqrt(y+0.25)
    #return {"yupper": y+hi, "ylower": y-lo, "hi": hi, "lo": lo}
    return {"yupper": y+hi, "ylower": y-lo}
