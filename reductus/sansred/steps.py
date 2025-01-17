"""
SANS reduction steps
====================

Set of reduction steps for SANS reduction.
"""

from __future__ import print_function

from posixpath import basename, join
from copy import copy, deepcopy
from io import BytesIO
from collections import OrderedDict

import numpy as np

from reductus.dataflow.lib.uncertainty import Uncertainty
from reductus.dataflow.lib import uncertainty

from .sansdata import RawSANSData, SansData, Sans1dData, SansIQData, Parameters
from .sans_vaxformat import readNCNRSensitivity

from reductus.vsansred.steps import _s, _b

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

@cache
@module
def LoadDIV(filelist=None, variance=0.0001):
    """
    loads a DIV file (VAX format) into a SansData obj and returns that.

    **Inputs**

    filelist (fileinfo[]): Files to open.

    variance (float): Target variance of DIV measurement (default 0.0001, i.e. 1% error)
    
    **Returns**

    output (sans2d[]): all the entries loaded.

    2018-04-21 Brian Maranville
    """
    from reductus.dataflow.fetch import url_get
    from .sans_vaxformat import readNCNRSensitivity

    output = []
    if filelist is not None:
        for fileinfo in filelist:
            path, mtime, entries = fileinfo['path'], fileinfo.get('mtime', None), fileinfo.get('entries', None)
            name = basename(path)
            fid = BytesIO(url_get(fileinfo, mtime_check=False))
            sens_raw = readNCNRSensitivity(fid)
            sens = SansData(Uncertainty(sens_raw, sens_raw * variance))
            sens.metadata = OrderedDict([
                ("run.filename", name),
                ("analysis.groupid", -1),
                ("analysis.intent", "DIV"),
                ("analysis.filepurpose", "Sensitivity"),
                ("run.experimentScanID", name), 
                ("sample.description", "PLEX"),
                ("entry", "entry"),
                ("sample.labl", "PLEX"),
                ("run.configuration", "DIV"),
            ])
            output.append(sens)
    return output

@cache
@module
def LoadRawSANS(filelist=None, check_timestamps=True):
    """
    loads a data file into a RawSansData obj and returns that.

    **Inputs**

    filelist (fileinfo[]): Files to open.
    
    check_timestamps (bool): verify that timestamps on file match request

    **Returns**

    output (raw[]): all the entries loaded.

    2018-04-23 Brian Maranville
    """
    from reductus.dataflow.fetch import url_get
    from .loader import readSANSNexuz
    if filelist is None:
        filelist = []
    data = []
    for fileinfo in filelist:
        path, mtime, entries = fileinfo['path'], fileinfo.get('mtime', None), fileinfo.get('entries', None)
        name = basename(path)
        fid = BytesIO(url_get(fileinfo, mtime_check=check_timestamps))
        if name.upper().endswith(".DIV"):
            sens_raw = readNCNRSensitivity(fid)
            detectors = [{"detector": {"data": {"value": Uncertainty(sens_raw, sens_raw * 0.0001)}}}]
            metadata = OrderedDict([
                ("run.filename", name),
                ("analysis.groupid", -1),
                ("analysis.intent", "DIV"),
                ("analysis.filepurpose", "Sensitivity"),
                ("run.experimentScanID", name), 
                ("sample.description", "PLEX"),
                ("entry", "entry"),
                ("sample.labl", "PLEX"),
                ("run.configuration", "DIV"),
            ])
            sens = RawSANSData(metadata=metadata, detectors=detectors)
            entries = [sens]
        else:
            entries = readSANSNexuz(name, fid)
        
        data.extend(entries)

    return data

@cache
@module
def patch(data, patches=None):
    """
    loads a data file into a VSansData obj and returns that.

    **Inputs**

    data (raw[]): datafiles with metadata to patch

    patches (patch_metadata[]:run.filename): patches to be applied, with run.filename used as unique key

    **Returns**

    patched (raw[]): datafiles with patched metadata

    2019-07-26 Brian Maranville
    """
    if patches is None:
        return data
    
    from jsonpatch import JsonPatch
        # make a master dict of metadata from provided key:

    key="run.filename"

    master = OrderedDict([(_s(d.metadata[key]), d.metadata) for d in data])
    to_apply = JsonPatch(patches)
    to_apply.apply(master, in_place=True)

    return data

@cache
@module
def autosort(rawdata, subsort="det.des_dis", add_scattering=True):
    """
    redirects a batch of files to different outputs based on metadata in the files

    **Inputs**

    rawdata (raw[]): datafiles with metadata to allow sorting

    subsort (str): key on which to order subitems within output lists

    add_scattering {Add sample scatterings together} (bool): Add sample scatterings, within
    group defined by subsort key

    **Returns**

    sample_scatt (sans2d[]): Sample Scattering

    blocked_beam (sans2d[]): Blocked Beam

    empty_scatt (sans2d[]): Empty Cell Scattering

    sample_trans (sans2d[]): Sample Transmission

    empty_trans (sans2d[]): Empty Cell Transmission

    2019-07-24 Brian Maranville
    """

    sample_scatt = []
    blocked_beam = []
    empty_scatt = []
    sample_trans = []
    empty_trans = []

    print(rawdata)

    for r in rawdata:
        purpose = _s(r.metadata['analysis.filepurpose'])
        intent = _s(r.metadata['analysis.intent'])
        if intent.lower().strip().startswith('blo'):
            blocked_beam.extend(to_sansdata(r))
        elif purpose.lower() == 'scattering' and intent.lower() == 'sample':
            sample_scatt.extend(to_sansdata(r))
        elif purpose.lower() == 'scattering' and intent.lower().startswith('empty'):
            empty_scatt.extend(to_sansdata(r))
        elif purpose.lower() == 'transmission' and intent.lower() == 'sample':
            sample_trans.extend(to_sansdata(r))
        elif purpose.lower() == 'transmission' and intent.lower().startswith('empty'):
            empty_trans.extend(to_sansdata(r))

    def keyFunc(l):
        return l.metadata.get(subsort, 0)

    for output in [sample_scatt, blocked_beam, empty_scatt, sample_trans, empty_trans]:
        output.sort(key=keyFunc)
    
    if add_scattering:
        added_samples = OrderedDict()
        for s in sample_scatt:
            key = keyFunc(s)
            added_samples.setdefault(key, [])
            added_samples[key].append(s)
        for key in added_samples:
            added_samples[key] = addSimple(added_samples[key])
        sample_scatt = list(added_samples.values())

    return sample_scatt, blocked_beam, empty_scatt, sample_trans, empty_trans


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

    output (raw[]): all the entries loaded.

    | 2019-07-26 Brian Maranville
    | 2019-08-09 Brian Maranville adding new stripped sample description
    """

    rawdata = LoadRawSANS(filelist, check_timestamps=check_timestamps)
    sansdata = []
    for r in rawdata:
        sansdata.extend(to_sansdata(r, flip=flip, transpose=transpose))
    return sansdata

def to_sansdata(rawdata, flip=False, transpose=False):
    areaDetector = rawdata.detectors['detector']['data']['value']
    shape = areaDetector.shape
    if len(shape) < 2 or len(shape) > 3:
        raise ValueError("areaDetector data must have dimension 2 or 3")
        return
    if len(shape) == 2:
        # add another dimension at the front
        shape = (1,) + shape
        areaDetector = areaDetector.reshape(shape)
    datasets = []
    for i in range(shape[0]):
        subset = areaDetector[i].copy()
        if flip:
            subset = np.fliplr(subset)
        if transpose:
            subset = subset.T
        datasets.append(SansData(data=subset, metadata=rawdata.metadata))
    return datasets

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

#@module
def draw_ellipse(data, ellipse=[0,0,0.01,0.01]):
    """
    draw an ellipse on the data

    **Inputs**

    data (sans2d): data in

    ellipse (range:ellipse): ellipse to draw

    **Returns**

    output (sans2d): the same data

    2019-07-31  Brian Maranville
    """

    return data

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
    xctr = data.metadata["det.beamx"]
    yctr = data.metadata["det.beamy"]

    shape = data.data.x.shape
    x, y = np.indices(shape) + 1.0 # detector indexing starts at 1...
    X = DDetX * (x-xctr)
    Y = DDetY * (y-yctr)

    sampleOff = data.metadata["sample.position"]
    apOff = data.metadata["resolution.ap2Off"]
    S1 = data.metadata["resolution.ap1"] / 2.0 # use radius
    S2 = data.metadata["resolution.ap2"] / 2.0 # use radius
    L1 = data.metadata["resolution.ap12dis"]
    L2 = data.metadata["det.dis"] + sampleOff + apOff
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

def calculateMeanQ(data):
    """ calculate the overlap of the beamstop with the pixel """
    from scipy.special import erf

    BS = data.metadata['det.bstop'] / 2.0 # diameter to radius, already in cm

    DDetX = data.metadata["det.pixelsizex"]
    DDetY = data.metadata["det.pixelsizey"]
    sampleOff = data.metadata["sample.position"]
    apOff = data.metadata["resolution.ap2Off"]
    wavelength = data.metadata['resolution.lmda']
    L1 = data.metadata["resolution.ap12dis"]
    L2 = data.metadata["det.dis"] + sampleOff + apOff
    LB = 20.1 + 1.61*BS # empirical formula from NCNR_Utils.ipf, line 123 in "getResolution"
    BS_prime = BS + (BS * LB / (L2 - LB)) # adding triangular shadow from LB to L2

    r0 = data.r
    r0_mean = r0.copy()
    # width of the resolution function, on average
    # could be corrected for phi if taking into account non-square pixels...
    v_d = ((DDetX + DDetY) / (2.0 * np.sqrt(np.log(256.0))))**2

    # cutoff_weight ~ integral[-inf, r0-BS_prime]1/sqrt(2*pi*dq**2) * exp(-r**2 / (2*dq**2))
    #               = 0.5 * (1.0 + erf((r0 - BS_prime)/(2.0 * dq)))
    shadow_factor = 0.5 * (1.0 + erf((r0 - BS_prime) / np.sqrt(2.0 * v_d)))
    shadow_factor[shadow_factor<1e-16] = 1e-16

    #inside_mask = (r0 <= BS_prime)
    #outside_mask = np.logical_not(inside_mask)
    # inside the beamstop, the center of mass of the distribution is displaced by 
    # the center of the cutoff tail (relative to r0) on the high side, approx. 
    # cutoff_weighted_integral ~ integral[BS_prime - r0, inf] 1/sqrt(2*pi*dq**2) * r * exp(-r**2 / (2*dq**2))
    #               = 1.0/sqrt(2*pi*dq**2) * 1.0/dq**2 * exp(-(BS_prime - r0)**2 / (2 * dq**2))
    #  
    # then new_center = r0 + cutoff_weighted_integral / cutoff_integral
    # but the cutoff_integral = shadow_factor, so :
    #
    # cutoff_weighted_integral_inside = 1.0/(np.sqrt(2.0 * np.pi) * dq[inside_mask]**3) * np.exp(-(BS_prime - r0[inside_mask])**2 / (2 * dq[inside_mask]**2))
    # cutoff_center_inside = cutoff_weighted_integral_inside / shadow_factor[inside_mask]
    # r0_mean[inside_mask] += cutoff_center_inside

    # outside the beamstop, the center of mass of the distribution is displaced by the center
    # of what is left after subtracting the cutoff tail, but the weighted sum of 
    # cutoff_center * cutoff_integral + remainder_center * remainder_integral == 0!
    # (equivalent to saying cutoff_weighted_integral + remainder_weighted_integral = 0)
    # and also we know that cutoff_integral + remainder_integral = 1 (normalized gaussian)
    # cutoff_weighted_integral ~ integral[-inf, r0-BS_prime] 1/sqrt(2*pi*dq**2) r exp(-r**2 / (2*dq**2))
    #               = -1.0/sqrt(2*pi*dq**2) * 1.0/dq**2 * exp(-(r0 - BS_prime)**2 / (2 * dq**2))
    # remainder_weighted_integral = -(cutoff_weighted_integral)
    # 
    # remainder_center = remainder_weighted_integral / remainder_integral
    #                  = remainder_weighted_integral / (1 - cutoff_integral)
    #                  = -cutoff_weighted_integral / (1 - cutoff_integral)
    # then new_center *  = r0 - cutoff_weighted_integral / shadow_factor
    # but the cutoff_weight = shadow_factor and total_weight = 1.0, so:
    #
    ## cutoff_weighted_integral_outside = -1.0/(np.sqrt(2.0 * np.pi) * dq[outside_mask]**3) * np.exp(-(r0[outside_mask] - BS_prime)**2 / (2 * dq[outside_mask]**2))

    # but noticing that the expression for cutoff_weighted_integral_inside is the same numerically 
    # (swapping positions of r0 and BS_prime has no effect) then this gets easier:

    cutoff_weighted_integral = np.sqrt(v_d / (2.0 * np.pi)) * np.exp(-(r0 - BS_prime)**2 / (2 * v_d))
    r0_mean += cutoff_weighted_integral / shadow_factor
    
    meanTheta = np.arctan2(r0_mean, L2)/2.0 #remember to convert L2 to cm from meters
    data.meanQ = (4*np.pi/wavelength)*np.sin(meanTheta)
    # TODO: shadow factor is calculated, but shouldn't the normalization to solid angle
    # include the reduction from the shadow factor?  This will greatly increase the intensity
    # of pixels near or below the beam stop!
    data.shadow_factor = shadow_factor
    return data


def calculateDQ_IGOR(data, inQ, del_r=None):
    """
    Add the dQ column to the data, based on slit apertures and gravity
    r_dist is the real-space distance from ctr of detector to QxQy pixel location

    From `NCNR_Utils.ipf` (Steve R. Kline) in which the math is in turn from:

    | D.F.R Mildner, J.G. Barker & S.R. Kline J. Appl. Cryst. (2011). 44, 1127-1129.
    | *The effect of gravity on the resolution of small-angle neutron diffraction peaks*
    | [ doi:10.1107/S0021889811033322 ]

    | J. Appl. Cryst. (1995). 28, 105-114
    | https://doi.org/10.1107/S0021889894010095 (Cited by 90)
    | Instrumental Smearing Effects in Radially Symmetric Small-Angle Neutron Scattering by Numerical and Analytical Methods
    | J. G. Barker and J. S. Pedersen

    **Inputs**

    data (sans2d): data in

    del_r (float): width of circular slice in realspace (cm)

    **Returns**

    output (sans2d): data in with dQ column filled in

    2017-06-16  Brian Maranville
    """
    from scipy.special import gammaln, gammainc, erf

    G = 981.  #!    ACCELERATION OF GRAVITY, CM/SEC^2
    vz_1 = 3.956e5 # velocity [cm/s] of 1 A neutron
    # the detector pixel is square, so correct for phi
    DDet = data.metadata["det.pixelsizex"]
    if del_r is None:
        del_r = DDet

    apOff = data.metadata["resolution.ap2Off"]
    sampleOff = data.metadata["sample.position"]
    S1 = data.metadata["resolution.ap1"] * 0.5 # convert to radius, already cm
    S2 = data.metadata["resolution.ap2"] * 0.5 # to radius
    # no need to subtract apOff below - this is done in device model
    # but for comparison with IGOR, leave it in:
    L1 = data.metadata["resolution.ap12dis"] - apOff 
    L2 = data.metadata["det.dis"] + sampleOff + apOff
    LP = 1.0/( 1.0/L1 + 1.0/L2)
    
    BS = data.metadata['det.bstop'] / 2.0 # diameter to radius, already in cm
    LB = 20.1 + 1.61*BS # empirical formula from NCNR_Utils.ipf, line 123 in "getResolution"
    BS_prime = BS + (BS * LB / (L2 - LB)) # adding triangular shadow from LB to L2

    lambda0 = data.metadata["resolution.lmda"]    #  15
    labmdaWidth = data.metadata["resolution.dlmda"]    # 0.236

    # these are defined in the IGOR code, but never get used therein...
    ##a2 = S1*L2/L1 + S2*(L1+L2)/L1
    ##q_small = 2.0*np.pi*(BS_prime-a2)*(1.0-lambdaWidth)/(lambda*L2)
    LP = 1.0/( 1.0/L1 + 1.0/L2)
    v_lambda = labmdaWidth**2/6.0

    if 'LENS' in _s(data.metadata['run.guide'].upper()):
        # NOTE: this might need adjustment.  Ticket #677 filed in trac to change to:
        # v_b = 0.25*(S1*L2/L1)**2 +0.25*(2/3)*(labmdaWidth)**2*(S2*L2/LP)**2	
        v_b = 0.25*(S1*L2/L1)**2 +0.25*(2/3)*(labmdaWidth/lambda0)**2*(S2*L2/LP)**2		# correction to 2nd term
    else:
        v_b = 0.25*(S1*L2/L1)**2 +0.25*(S2*L2/LP)**2		# original form

    v_d = (DDet/2.3548)**2 + del_r**2/12.0	# the 2.3548 is a conversion from FWHM->Gauss, see https://mathworld.wolfram.com/GaussianFunction.html
    vz = vz_1 / lambda0
    yg = 0.5*G*L2*(L1+L2)/vz**2
    v_g = 2.0*(2.0*yg**2*v_lambda)					# factor of 2 correction, B. Hammouda, 2007

    r0 = L2*np.tan(2.0*np.arcsin(lambda0*inQ/(4.0*np.pi) ))
    delta = 0.5*(BS_prime - r0)**2/v_d

    #if (r0 < BS_prime):
    #    inc_gamma=np.exp(gammaln(1.5))*(1-gammainc(1.5,delta))
    #else:
    #    inc_gamma=np.exp(gammaln(1.5))*(1+gammainc(1.5,delta))
    inc_gamma = np.ones_like(r0)
    r0_less = (r0 < BS_prime)
    r0_more = (r0 >= BS_prime)
    inc_gamma[r0_less] = np.exp(gammaln(1.5))*(1-gammainc(1.5,delta[r0_less]))
    inc_gamma[r0_more] = np.exp(gammaln(1.5))*(1+gammainc(1.5,delta[r0_more]))
 

    fSubS = 0.5*(1.0+erf( (r0-BS_prime)/np.sqrt(2.0*v_d) ) )
    #if (fSubS <= 0.0):
    #    fSubS = 1.e-10
    fSubS[fSubS <= 0.0] = 1.e-10

    fr = 1.0 + np.sqrt(v_d)*np.exp(-1.0*delta) /(r0*fSubS*np.sqrt(2.0*np.pi))
    fv = inc_gamma/(fSubS*np.sqrt(np.pi)) - r0**2*(fr-1.0)**2/v_d

    rmd = fr*r0
    v_r1 = v_b + fv*v_d +v_g

    rm = rmd + 0.5*v_r1/rmd
    v_r = v_r1 - 0.5*(v_r1/rmd)**2
    #if (v_r < 0.0):
    #    v_r = 0.0
    v_r[v_r < 0.0] = 0.0

    QBar = (4.0*np.pi/lambda0)*np.sin(0.5*np.arctan(rm/L2))
    SigmaQ = QBar*np.sqrt(v_r/rmd**2 + v_lambda)

    return QBar, SigmaQ

def _calculate_Q(X, Y, Z, q0):
    r"""
    Detector pixels in SAS measurements have a small $q_z$ component.

    Using the definition $q = k_f - k_i$ with the beam along $z$ then::

        k_i = 2 pi/lambda_i [0, 0, 1]
        k_f = 2 pi/lambda_f [sin 2theta cos phi, sin 2theta sin phi, cos 2theta]

    Assume elastic scattering so $\lambda_i = \lamda_f = \lambda$. Therefore::

        q_x = 2 pi/lambda (sin 2theta cos phi)
            = 4 pi/lambda sin theta cos theta cos phi
            = |q| cos theta cos phi
        q_y = 2 pi/lambda (sin 2theta sin phi)
            = 4 pi/lambda sin theta cos theta sin phi
            = |q| cos theta sin phi
        q_z = 2 pi/lambda (1 - cos 2theta)
            = 4 pi/lambda sin^2 theta = |q| sin theta
    """
    r = np.sqrt(X**2+Y**2)
    theta = np.arctan2(r, Z)/2 #remember to convert Z to cm from meters
    q = q0*np.sin(theta)
    phi = np.arctan2(Y, X)
    qx = q*np.cos(theta)*np.cos(phi)
    qy = q*np.cos(theta)*np.sin(phi)
    qz = q*np.sin(theta)

    return r, theta, q, phi, qx, qy, qz

def FX(xx,sx3,xcenter,sx):
    return sx3*np.tan((xx-xcenter)*sx/sx3)

@cache
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

    2016-04-17 Brian Maranville
    """

    sampleOffset = data.metadata["sample.position"]
    Z = data.metadata["det.dis"] + sampleOffset
    beamx_override, beamy_override = beam_center
    x0 = beamx_override if beamx_override is not None else data.metadata['det.beamx'] #should be close to 64
    y0 = beamy_override if beamy_override is not None else data.metadata['det.beamy'] #should be close to 64
    wavelength = data.metadata['resolution.lmda']
    q0 = (4*np.pi/wavelength)
    shape = data.data.x.shape

    x, y = np.indices(shape) + 1.0 # center of first pixel is 1, 1 (Detector indexing)
    xcenter, ycenter = [(dd + 1.0)/2.0 for dd in shape] # = 64.5 for 128x128 array
    sx = data.metadata['det.pixelsizex'] # cm
    sy = data.metadata['det.pixelsizey']
    sx3 = 1000.0 # constant, = 10000(mm) = 1000 cm; not in the nexus file for some reason.
    sy3 = 1000.0 # (cm) also not in the nexus file 
    # centers of pixels:
    dxbm = sx3*np.tan((x0-xcenter)*sx/sx3)
    dybm = sy3*np.tan((y0-ycenter)*sy/sy3)

    X = sx3*np.tan((x-xcenter)*sx/sx3) - dxbm # in mm in nexus, but converted by loader
    Y = sy3*np.tan((y-ycenter)*sy/sy3) - dybm
    r, theta, q, phi, qx, qy, qz = _calculate_Q(X, Y, Z, q0)
    
    if correct_solid_angle:
        """
        rad = sqrt(dtdis2 + xd^2 + yd^2)
		domega = rad/dtdist
		ratio = domega^3
		xy = xx[ii]*yy[jj]

		data[ii][jj] *= xy*ratio
        """
        xx = (np.cos((x-xcenter)*sx/sx3))**2
        yy = (np.cos((y-ycenter)*sy/sy3))**2
        #data.data.x = data.data.x / (np.cos(theta)**3)
        data.data.x = data.data.x * xx * yy / (np.cos(2*theta)**3)

    # bin corners:
    X_low = sx3*np.tan((x - 0.5 - xcenter)*sx/sx3) - dxbm # in mm in nexus, but converted by loader
    X_high = sx3*np.tan((x + 0.5 - xcenter)*sx/sx3) - dxbm # in mm in nexus, but converted by loader
    Y_low = sy3*np.tan((y - 0.5 - ycenter)*sy/sy3) - dybm
    Y_high = sy3*np.tan((y + 0.5 - ycenter)*sy/sy3) - dybm

    r_low, theta_low, q_low, phi_low, qx_low, qy_low, qz_low = _calculate_Q(X_low, Y_low, Z, q0)
    r_high, theta_high, q_high, phi_high, qx_high, qy_high, qz_high = _calculate_Q(X_high, Y_high, Z, q0)

    res = data.copy()
    #Adding res.q
    res.q = q
    res.qx = qx
    res.qy = qy
    res.qz = qz
    # bin edges:
    res.qx_low = qx_low
    res.qy_low = qy_low
    res.qx_high = qx_high
    res.qy_high = qy_high

    res.X = X
    res.Y = Y
    res.Z = Z
    res.r = r
    res.metadata['det.beamx'] = x0
    res.metadata['det.beamy'] = y0
    res.qx_min = q0/2.0 * data.metadata['det.pixelsizex']*(0.5 - x0)/ Z
    res.qy_min = q0/2.0 * data.metadata['det.pixelsizex']*(0.5 - y0)/ Z
    res.qx_max = q0/2.0 * data.metadata['det.pixelsizex']*(128.5 - x0)/ Z
    res.qy_max = q0/2.0 * data.metadata['det.pixelsizex']*(128.5 - y0)/ Z
    res.xlabel = "Qx (inv. Angstroms)"
    res.ylabel = "Qy (inv. Angstroms)"
    res.theta = theta

    calculateDQ(res)
    calculateMeanQ(res)
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

    2016-04-13 Brian Maranville
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
    sampleOffset = data.metadata["sample.position"]
    L2 = data.metadata["det.dis"] + sampleOffset
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

def oversample_2d(input_array, oversampling):
    return np.repeat(np.repeat(input_array, oversampling, 0), oversampling, 1)

@nocache
@module
def circular_av_new(data, q_min=None, q_max=None, q_step=None, mask_width=3, dQ_method='none'):
    """
    Using a circular average, it converts data to 1D (Q vs. I)


    **Inputs**

    data (sans2d): data in

    q_min (float): minimum Q value for binning (defaults to q_step)

    q_max (float): maxiumum Q value for binning (defaults to max of q values in data)

    q_step (float): step size for Q bins (defaults to minimum qx step)

    mask_width (int): number of pixels to mask around the perimeter of the detector

    dQ_method (opt:none|IGOR|statistical) : method for calculating dQ

    **Returns**

    nominal_output (sans1d): converted to I vs. nominal Q

    mean_output (sans1d): converted to I vs. mean Q within integrated region

    output (sansIQ): canonical I vs Q output for sans data.

    | 2019-01-01 Brian Maranville
    | 2019-09-05 Adding mask_width as a temporary way to handle basic masking
    | 2019-12-11 Brian Maranville adding dQ_method opts
    """

    # adding simple width-based mask around the perimeter:
    mask = np.zeros_like(data.q, dtype=bool)
    mask_width = abs(mask_width)
    if (mask_width > 0):
        mask[mask_width:-mask_width, mask_width:-mask_width] = True
    else:
        mask[:] = True

    # calculate the change in q that corresponds to a change in pixel of 1
    if data.qx is None:
        raise ValueError("Q is not defined - convert pixels to Q first")

    if q_step is None:
        q_step = data.qx[1, 0]-data.qx[0, 0] / 1.0

    if q_min is None:
        q_min = q_step
    
    if q_max is None:
        q_max = data.q[mask].max()

    q_bins = np.arange(q_min, q_max+q_step, q_step)
    Q = (q_bins[:-1] + q_bins[1:])/2.0

    oversampling = 3

    o_mask = oversample_2d(mask, oversampling)
    #o_q = oversample_2d(data.q, oversampling)
    o_qxi, o_qyi = np.indices(o_mask.shape)
    o_qx_offsets = ((o_qxi % oversampling) + 0.5) / oversampling
    o_qy_offsets = ((o_qyi % oversampling) + 0.5) / oversampling
    qx_width = oversample_2d(data.qx_high - data.qx_low, oversampling)
    qy_width = oversample_2d(data.qy_high - data.qy_low, oversampling)
    original_lookups = (np.floor_divide(o_qxi, oversampling), np.floor_divide(o_qyi, oversampling))
    o_qx = data.qx_low[original_lookups] + (qx_width * o_qx_offsets)
    o_qy = data.qy_low[original_lookups] + (qy_width * o_qy_offsets)
    o_qz = oversample_2d(data.qz, oversampling)
    o_q = np.sqrt(o_qx**2 + o_qy**2 + o_qz**2)
    o_data = oversample_2d(data.data, oversampling) # Uncertainty object...
    o_meanQ = oversample_2d(data.meanQ, oversampling)
    o_shadow_factor = oversample_2d(data.shadow_factor, oversampling)
    o_dq_para = oversample_2d(data.dq_para, oversampling)

    # dq = data.dq_para if hasattr(data, 'dqpara') else np.ones_like(data.q) * q_step
    I, _bins_used = np.histogram(o_q[o_mask], bins=q_bins, weights=o_data.x[o_mask])
    I_norm, _ = np.histogram(o_q[o_mask], bins=q_bins, weights=np.ones_like(o_data.x[o_mask]))
    I_var, _ = np.histogram(o_q[o_mask], bins=q_bins, weights=o_data.variance[o_mask])
    #Q_ave, _ = np.histogram(o_q[o_mask], bins=q_bins, weights=o_q[o_mask])
    #Q_var, _ = np.histogram(data.q, bins=q_bins, weights=data.dq_para**2)
    Q_mean, _ = np.histogram(o_q[o_mask], bins=q_bins, weights=o_meanQ[o_mask])
    ShadowFactor, _ = np.histogram(o_q[o_mask], bins=q_bins, weights=o_shadow_factor[o_mask])

    nonzero_mask = I_norm > 0

    I[nonzero_mask] /= I_norm[nonzero_mask]
    I_var[nonzero_mask] /= (I_norm[nonzero_mask]**2)
    Q_mean[nonzero_mask] /= I_norm[nonzero_mask]
    #Q_ave[nonzero_mask] /= I_norm[nonzero_mask]
    ShadowFactor[nonzero_mask] /= I_norm[nonzero_mask]

    # calculate Q_var...
    # remarkably, the variance of a sum of normalized gaussians 
    # with variances v_i, displaced from the mean center by xc_i
    # is the sum of (xc_i**2 + v_i).   Gaussians are weird.

    
    if dQ_method == 'IGOR':
        Q_mean, Q_mean_error = calculateDQ_IGOR(data, Q)
    elif dQ_method == 'statistical':
        # exclude Q_mean_lookups that overflow the length of the calculated Q_mean:
        Q_lookup = np.digitize(o_q[o_mask], bins=q_bins)
        Q_lookup_mask = (Q_lookup < len(Q))
        Q_mean_center = Q_mean[Q_lookup[Q_lookup_mask]]
        Q_var_contrib = (o_meanQ[o_mask][Q_lookup_mask] - Q_mean_center)**2 + (o_dq_para[o_mask][Q_lookup_mask])**2
        Q_var, _ = np.histogram(o_meanQ[o_mask][Q_lookup_mask], bins=q_bins, weights=Q_var_contrib)
        Q_var[nonzero_mask] /= I_norm[nonzero_mask]
        Q_mean_error = np.sqrt(Q_var)
    else:
        # 'none' is the default
        Q_mean_error = np.zeros_like(Q)

    nominal_output = Sans1dData(Q, I, dx=Q_mean_error, dv=I_var, xlabel="Q", vlabel="I",
                        xunits="inv. A", vunits="neutrons")
    nominal_output.metadata = deepcopy(data.metadata)
    nominal_output.metadata['extra_label'] = "_circ"

    mean_output = Sans1dData(Q_mean, I, dx=Q_mean_error, dv=I_var, xlabel="Q", vlabel="I",
                        xunits="inv. A", vunits="neutrons")
    mean_output.metadata = deepcopy(data.metadata)
    mean_output.metadata['extra_label'] = "_circ"

    canonical_output = SansIQData(I, np.sqrt(I_var), Q, Q_mean_error, Q_mean, ShadowFactor, metadata=deepcopy(data.metadata))
    
    return nominal_output, mean_output, canonical_output

@cache
@module
def sector_cut(data, sector=[0.0, 90.0], mirror=True):
    """
    Using annular averging, it converts data to 1D (Q vs. I)
    over a particular angle range


    **Inputs**

    data (sans2d): data in

    sector (range:sector_centered): angle and opening of sector cut (radians)

    mirror (bool): extend sector cut on both sides of origin
        (when false, integrates over a single cone centered at angle)

    **Returns**

    nominal_output (sans1d): converted to I vs. nominal Q

    mean_output (sans1d): converted to I vs. mean Q within integrated region

    2016-04-15 Brian Maranville
    """
    from .draw_annulus_aa import sector_cut_antialiased

    if sector is None:
        sector = [0.0, 90.0]

    #annular_mask_antialiased(shape, center, inner_radius, outer_radius,
    #                         background_value=0.0, mask_value=1.0, oversampling=8)

    # calculate the change in q that corresponds to a change in pixel of 1
    q_per_pixel = data.qx[1, 0]-data.qx[0, 0] / 1.0

    # for now, we'll make the q-bins have the same width as a single pixel
    step = q_per_pixel
    shape1 = data.data.x.shape
    x0 = data.metadata['det.beamx'] # should be close to 64
    y0 = data.metadata['det.beamy'] # should be close to 64
    apOff = data.metadata["sample.position"]
    L2 = data.metadata["det.dis"] + apOff
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
    angle, width = sector
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
def rescale_1d(data, scale=1.0, dscale=0.0):
    """
    Multiply 1d data by a scale factor

    **Inputs**

    data (sans1d): data in

    scale (scale*) : amount to scale, one for each dataset

    dscale {Scale err} (float*:<0,inf>) : scale uncertainty for gaussian error propagation

    **Returns**

    output (sans1d) : scaled data

    2016-04-17 Brian Maranville
    """
    from reductus.dataflow.lib import err1d

    I, varI = err1d.mul(data.v, data.dv, scale, dscale**2)
    data.v, data.dv = I, varI
    
    return data

@module
def correct_detector_efficiency(sansdata):
    """
    Given a SansData object, corrects for the efficiency of the detection process

    **Inputs**

    sansdata (sans2d): data in

    **Returns**

    output (sans2d): corrected for efficiency

    | 2016-08-04 Brian Maranville and Andrew Jackson
    | 2019-12-13 updated to detector coordinates
    """

    sampleOff = sansdata.metadata["sample.position"]
    Z = sansdata.metadata["det.dis"] + sampleOff # cm
    lambd = sansdata.metadata["resolution.lmda"]
    shape = sansdata.data.x.shape
    x0 = sansdata.metadata['det.beamx'] #should be close to 64
    y0 = sansdata.metadata['det.beamy'] #should be close to 64
    xcenter, ycenter = [(dd + 1.0)/2.0 for dd in shape]

    x, y = np.indices(shape) + 1.0 # detector coordinates

    sx = sansdata.metadata['det.pixelsizex'] # cm
    sy = sansdata.metadata['det.pixelsizey']
    sx3 = 1000.0 # constant, = 10000(mm) = 1000 cm; not in the nexus file for some reason.
    sy3 = 1000.0 # (cm) also not in the nexus file 
    # centers of pixels:
    dxbm = sx3*np.tan((x0-xcenter)*sx/sx3)
    dybm = sy3*np.tan((y0-ycenter)*sy/sy3)

    X = sx3*np.tan((x-xcenter)*sx/sx3) - dxbm # in mm in nexus, but converted by loader
    Y = sy3*np.tan((y-ycenter)*sy/sy3) - dybm
    r = np.sqrt(X**2+Y**2)
    theta_det = np.arctan2(r, Z)/2

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
def generate_transmission(in_beam, empty_beam, integration_box=[55, 74, 53, 72], align_by="run.configuration", auto_integrate=True, margin=5):
    """
    To calculate the transmission, we integrate the intensity in a box
    for a measurement with the substance in the beam and with the substance
    out of the beam and take their ratio. The box is definied by xmin, xmax
    and ymin, ymax, I start counting at (0, 0).

    Coords are taken with reference to bottom left of the image.

    **Inputs**

    in_beam (sans2d[]): measurement with sample in the beam

    empty_beam (sans2d[]): measurement with no sample in the beam

    integration_box (range:xy): region over which to integrate

    align_by (str): for multiple in_beam and empty_beam, line up by this metadata key
    use "none" to align by positional order

    auto_integrate (bool): automatically select integration region

    margin {Box margin, width = 4*gauss_width + 2*margin:} (int): Extra margin 
    to add to automatically calculated peak width in x and y

    **Returns**

    output (params[]): calculated transmission for the integration area

    | 2017-02-29 Brian Maranville
    | 2019-06-03 Adding auto-integrate, Brian Maranville
    | 2019-08-14 Adding metadata for grouping later, Brian Maranville
    | 2019-08-22 Adding align_by for inputs, Brian Maranville
    """
    
    if align_by == "none":
        if len(in_beam) != len(empty_beam):
            raise ValueError("number of in_beam must match number of empty_beam when align_by is none")
        output = []
        for ib, eb in zip(in_beam, empty_beam):
            output.append(_generate_transmission(ib, eb, integration_box=integration_box, auto_integrate=auto_integrate, margin=margin))
        return output
    else:
        eb_lookup = dict([(get_compound_key(eb.metadata, align_by), eb) for eb in empty_beam])
        output = []
        for ib in in_beam:
            eb = eb_lookup.get(get_compound_key(ib.metadata, align_by), None)
            if eb is None:
                raise ValueError("no matching empty was found for configuration: " + get_compound_key(ib.metadata, align_by))
            output.append(_generate_transmission(ib, eb, integration_box=integration_box, auto_integrate=auto_integrate, margin=margin))
        return output        
        
def _generate_transmission(in_beam, empty_beam, integration_box=None, auto_integrate=True, margin=5):
    if auto_integrate:
        height, x, y, width_x, width_y = moments(empty_beam.data.x)
        center_x = x + 0.5
        center_y = y + 0.5

        xmin = int(max(0, np.floor(center_x - width_x*2.0) - margin))
        xmax = int(min(empty_beam.data.shape[0], np.ceil(center_x + width_x*2.0) + margin))
        ymin = int(max(0, np.floor(center_y - width_y*2.0) - margin))
        ymax = int(min(empty_beam.data.shape[1], np.ceil(center_y + width_y*2.0) + margin))
    
    else:
        xmin, xmax, ymin, ymax = map(int, integration_box)
    
    I_in_beam = np.sum(in_beam.data[xmin:xmax+1, ymin:ymax+1])
    I_empty_beam = np.sum(empty_beam.data[xmin:xmax+1, ymin:ymax+1])

    ratio = I_in_beam/I_empty_beam
    result = Parameters(OrderedDict([
        ("factor", ratio.x), 
        ("factor_variance", ratio.variance),
        ("factor_err", np.sqrt(ratio.variance)),
        ("run.configuration", in_beam.metadata['run.configuration']),
        ("sample.description", in_beam.metadata['sample.description']),
        ("det.des_dis", in_beam.metadata['det.des_dis']),
        ("resolution.lmda", in_beam.metadata['resolution.lmda']),
        ("run.guide", in_beam.metadata['run.guide']),
        ("box_used", {"xmin": xmin, "xmax": xmax, "ymin": ymin, "ymax": ymax})
    ]))

    return result

def moments(data):
    """Returns (height, x, y, width_x, width_y)
    the gaussian parameters of a 2D distribution by calculating its
    moments """
    total = data.sum()
    X, Y = np.indices(data.shape)
    x = (X*data).sum()/total
    y = (Y*data).sum()/total
    col = data[:, int(round(y))]
    width_x = np.sqrt(np.abs((np.arange(col.size)-x)**2*col).sum()/col.sum())
    row = data[int(round(x)), :]
    width_y = np.sqrt(np.abs((np.arange(row.size)-y)**2*row).sum()/row.sum())
    height = data.max()
    return height, x, y, width_x, width_y

@module
def subtract(subtrahend, minuend, align_by='run.configuration'):
    """
    Algebraic subtraction of datasets pixel by pixel

    **Inputs**

    subtrahend (sans2d[]): a in (a-b) = c

    minuend (sans2d[]?): b in (a-b) = c, defaults to zero

    align_by (str): for multiple inputs, subtract minuend that matches subtrahend
    for this metadata value 
    (use "none" to align each subtrahend and minuend by position in the data list)

    **Returns**

    output (sans2d[]): c in (a-b) = c

    | 2010-01-01 unknown
    | 2019-08-14 Brian Maranville adding group by config
    """

    if not minuend or len(minuend) == 0:
        return subtrahend
    elif len(minuend) == 1:
        return [s - minuend[0] for s in subtrahend]
    elif align_by.lower() != "none":
        # make lookup:
        align_lookup = dict([(get_compound_key(m.metadata, align_by), m) for m in minuend])
        return [(s - align_lookup[get_compound_key(s.metadata, align_by)]) for s in subtrahend]
    else:
        return [(s - m) for s,m in zip(subtrahend, minuend)]

@module
def product(data, factor_param, align_by="det.des_dis,resolution.lmda,run.guide"):
    """
    Algebraic multiplication of dataset

    **Inputs**

    data (sans2d[]): data in (a)

    factor_param (params[]?): multiplication factor (b), defaults to 1

    align_by (str): for multiple inputs, multiply data that matches factor_param with this 
    metadata value

    **Returns**

    output (sans2d[]): result (c in a*b = c)

    | 2010-01-02 unknown
    | 2019-07-27 Brian Maranville
    """
    # follow broadcast rules:
    if not factor_param or len(factor_param) == 0:
        return data
    elif len(factor_param) == 1:
        f = factor_param[0]
        return [(d * Uncertainty(f.params.get('factor', 1.0), f.params.get('factor_variance', 0.0))) for d in data]
    elif align_by.lower() != "none":
        # make lookup:
        align_lookup = dict([(get_compound_key(f.params, align_by), Uncertainty(f.params.get('factor', 1.0), f.params.get('factor_variance', 0.0))) for f in factor_param])
        return [(d * align_lookup[get_compound_key(d.metadata, align_by)]) for d in data]
    else:
        return [d * Uncertainty(f.params.get('factor', 1.0), f.params.get('factor_variance', 0.0)) for d,f in zip(data, factor_param)]

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
        return data.__truediv__(factor_param.params['factor'])
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
def absolute_scaling(empty, sample, Tsam, div, instrument="NG7", integration_box=[55, 74, 53, 72], auto_box=True, margin=5):
    """
    Calculate absolute scaling

    Coords are taken with reference to bottom left of the image.

    **Inputs**

    empty (sans2d): measurement with no sample in the beam

    sample (sans2d): measurement with sample in the beam

    Tsam (params): sample transmission

    div (sans2d): DIV measurement

    instrument (opt:NG7|NGB|NGB30): instrument name, should be NG7 or NG3

    integration_box (range:xy): region over which to integrate

    auto_box (bool): automatically select integration region

    margin {Box margin, width = 4*gauss_width + 2*margin:} (int): Extra margin 
    to add to automatically calculated peak width in x and y

    **Returns**

    abs (sans2d): data on absolute scale

    params (params): parameter outputs

    | 2017-01-13 Andrew Jackson
    | 2019-07-04 Brian Maranville
    | 2019-07-14 Brian Maranville
    """
        # data (that is going through reduction), empty beam,
    # div, Transmission of the sample, instrument(NG3.NG5, NG7)
    # ALL from metadata
    detCnt = empty.metadata['run.detcnt']
    countTime = empty.metadata['run.rtime']
    monCnt = empty.metadata['run.moncnt']
    sampleOff = empty.metadata["sample.position"]
    sdd = empty.metadata["det.dis"] + sampleOff # already in cm
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
    data = empty.data/div.data
    # Then take the sum in XY box, including stat. error
    if auto_box:
        height, x, y, width_x, width_y = moments(empty.data.x)
        center_x = x + 0.5
        center_y = y + 0.5

        xmin = int(max(0, np.floor(center_x - width_x*2.0) - margin))
        xmax = int(min(empty.data.shape[0], np.ceil(center_x + width_x*2.0) + margin))
        ymin = int(max(0, np.floor(center_y - width_y*2.0) - margin))
        ymax = int(min(empty.data.shape[1], np.ceil(center_y + width_y*2.0) + margin))
    
    else:
        xmin, xmax, ymin, ymax = map(int, integration_box)

    detCnt = np.sum(data[xmin:xmax+1, ymin:ymax+1])
    print("DETCNT: ", detCnt)
    print('attentrans: ', attenTrans)
    print('monCnt: ', monCnt)

    #------End Result-------#
    # This assumes that the data is has not been normalized at all.
    # Thus either fix this or pass un-normalized data.
    # Compute kappa = incident intensity * solid angle of the pixel
    kappa = detCnt / attenTrans * 1.0e8 / monCnt * (pixel/sdd)**2
    print("Kappa: ", kappa.x, "+/-", np.sqrt(kappa.variance))

    #utc_datetime = date.datetime.utcnow()
    #print(utc_datetime.strftime("%Y-%m-%d %H:%M:%S"))

    Tsam_factor = Uncertainty(Tsam.params['factor'], Tsam.params['factor_variance'])
    print('Tsam_factor: ', Tsam_factor.x)

    #-----Using Kappa to Scale data-----#
    Dsam = sample.metadata['sample.thk']
    ABS = sample.__mul__(1/(kappa*Dsam*Tsam_factor))

    params = OrderedDict([
        ("DETCNT", detCnt.x),
        ("attentrans", attenTrans.x),
        ("monCnt", monCnt),
        ("kappa", kappa.x),
        ("Dsam", Dsam),
        ("box_used", {"xmin": xmin, "xmax": xmax, "ymin": ymin, "ymax": ymax})
    ])
    #------------------------------------
    return ABS, Parameters(params)

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

def get_compound_key(data_dict, compound_key, separator=","):
    subkeys = [s.strip() for s in compound_key.split(separator)]
    key = separator.join([_s(data_dict.get(sk, 'unknown')) for sk in subkeys])
    return key

@module
def groupAddData(data, group_by="run.configuration,sample.description"):
    """
    Addition of counts and monitor from different datasets,
    assuming all datasets were taken under identical conditions
    (except for count time)

    Groups by the metadata fields in "group_by" (comma-separated)
    e.g. all data with the same sample.description and run.configuration
    will be added together for group_by="run.configuration,sample.description"

    Use "group_by" = "none" to just add all together (like addSimple)

    Use metadata from first dataset in each group for output.

    **Inputs**

    data (sans2d[]): measurements to be added together

    group_by {Group by} (str): grouping key from metadata

    **Returns**

    sum (sans2d[]): sum of inputs, grouped

    2017-06-29  Brian Maranville
    """

    groups = OrderedDict()
    for d in data:
        key = get_compound_key(d.metadata, group_by)
        groups.setdefault(key, [])
        groups[key].append(d)
    
    output = [addSimple(g) for g in groups.values()]
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

@nocache
@module
def transmissionDecay(data, slicebox=[None,None,None,None], autosort=True):
    """
    Sum 2d data along in the box and return intensity vs time

    **Inputs**

    data (sans2d[]) : data in
    
    slicebox (range?:xy): region over which to integrate (in data coordinates)

    autosort (bool): sort results by time

    **Returns**

    sum (sans1d) : integrated counts vs. middle of count time (average of start and end times)

    2018-04-24 Brian Maranville
    """
    import datetime, iso8601
    if slicebox is None:
        slicebox = [None, None, None, None]
    xmin, xmax, ymin, ymax = slicebox
    
    times = []
    sums = []
    sums_variance = []
    for dataset in data:
        box_sum = sumBox(dataset, xmin, xmax, ymin, ymax)
        sums.append(box_sum.x)
        sums_variance.append(box_sum.variance)
        start_time = iso8601.parse_date(_s(dataset.metadata['start_time']))
        end_time = iso8601.parse_date(_s(dataset.metadata['end_time']))
        avg_time = (end_time - start_time)/2.0 + start_time
        times.append(avg_time.timestamp())
    
    xdata = np.array(times)
    dxdata = np.zeros_like(xdata)

    ydata = np.array(sums)
    dydata = np.array(sums_variance)
    if autosort:
        sorting_indices = np.argsort(xdata)
        xdata = xdata[sorting_indices]
        dxdata = dxdata[sorting_indices]
        ydata = ydata[sorting_indices]
        dydata = dydata[sorting_indices]


    output = Sans1dData(xdata, ydata, dx=dxdata, dv=dydata, xlabel='time', vlabel="I",
                    xunits="s", vunits="neutrons", xscale="time", metadata=data[0].metadata)
    
    return output
    

def sumBox(data, xmin, xmax, ymin, ymax):
    res = data.copy()
    if data.qx is None or data.qy is None:
        # then use pixels
        xslice = slice(int(np.ceil(xmin)) if xmin is not None else None, int(np.floor(xmax)) if xmax is not None else None)
        yslice = slice(int(np.ceil(ymin)) if ymin is not None else None, int(np.floor(ymax)) if ymax is not None else None)
        
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
        
    dataslice = (xslice, yslice)
    box_sum = uncertainty.sum(data.data[dataslice])
    return box_sum
    
@cache
@module
def SuperLoadSANS(filelist=None, do_det_eff=True, do_deadtime=True,
                  deadtime=1.0e-6, do_mon_norm=True, do_atten_correct=True, mon0=1e8,
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

    | 2018-04-21 Brian Maranville
    | 2019-12-11 Changed loader to include sample aperture offset position
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
