import copy
import numpy as np

from reductus.reflred.steps import subtract_background, divide_intensity, rescale, mask_points, join, divergence, normalize, abinitio_footprint, fit_footprint, correct_footprint, fit_background_field, subtract_background_field

from reductus.dataflow.automod import module
from reductus.reflred.gansref import _convert_slitrotation_to_aperture


@module
def load(filelist=None,
        intent='auto',
        Qz_basis='detector',
        sample_width=None,
        slit1_distance=None,
        slit1_aperture=None,
        slit1_rotary=True,
        slit2_distance=None,
        slit2_aperture=None,
        slit2_rotary=True,
        slit3_distance=None,
        slit3_aperture=None,
        slit3_rotary=False,
        slit4_distance=None,
        slit4_aperture=None,
        slit4_rotary=False        
        ):
    r"""
    Load a list of GANS Reflectivity files.

    *Qz_basis* uses one of the following values:

        **detector**
            ignores the sample angle and calculates Qz
            as $(4\pi/\lambda \sin(\theta_\text{detector}/2))$,
        **sample**
            ignores the detector angle and calculates Qz
            as $(4\pi/\lambda \sin(\theta_\text{sample}))$
        **actual**
            calculates Qx and Qz as (x,z)-components of
            $(\vec k_{\text{out}} - \vec k_\text{in})$ in sample coordinates,

    **Inputs**

    filelist (fileinfo[]): List of files to open.

    intent (opt:auto|specular|background+\|background-\|intensity|rock sample|rock detector|rock chi|slit align|scan)
    : Measurement intent (specular, background+, background-, slit, rock),
    auto or infer.  If intent is 'scan', then use the first scanned variable.

    Qz_basis (opt:detector|sample|actual)
    : How to calculate Qz from instrument angles.

    sample_width {Sample width (mm)} (float?)
    : Width of the sample along the beam direction in mm, used for
    calculating the effective resolution when the sample is smaller
    than the beam.  Leave blank to use value from data file.

    slit1_distance {override slit1 distance} (float?)
    : if specified, will override the value found in the file for
    the distance from the sample to slit 1

    slit1_aperture {override slit1 aperture} (float?)
    : if specified, will override the value found in the file for
    the opening of slit 1 in mm

    slit1_rotary {slit1 rotary?} (bool)
    : designates slit 1 as a rotary slit and converts its value from
    slit rotation to a slit aperture in mm

    slit2_distance {override slit2 distance} (float?)
    : if specified, will override the value found in the file for
    the distance from the sample to slit 2

    slit2_aperture {override slit2 aperture} (float?)
    : if specified, will override the value found in the file for
    the opening of slit 2 in mm

    slit2_rotary {slit2 rotary?} (bool)
    : designates slit 2 as a rotary slit and converts its value from
    slit rotation to a slit aperture in mm    

    slit3_distance {override slit3 distance} (float?)
    : if specified, will override the value found in the file for
    the distance from the sample to slit 3

    slit3_aperture {override slit3 aperture} (float?)
    : if specified, will override the value found in the file for
    the opening of slit 3 in mm

    slit3_rotary {slit3 rotary?} (bool)
    : designates slit 3 as a rotary slit and converts its value from
    slit rotation to a slit aperture in mm

    slit4_distance {override slit4 distance} (float?)
    : if specified, will override the value found in the file for
    the distance from the sample to slit 4

    slit4_aperture {override slit4 aperture} (float?)
    : if specified, will override the value found in the file for
    the opening of slit 4 in mm    

    slit4_rotary {slit4 rotary?} (bool)
    : designates slit 4 as a rotary slit and converts its value from
    slit rotation to a slit aperture in mm

    **Returns**

    output (refldata[]): All entries of all files in the list.

    | 2024-11-26 David Hoogerheide
    """
    from reductus.reflred.load import url_load_list
    from reductus.reflred import gansref
    
    # TODO: sample_width is ignored if datafile defines angular_divergence
    auto_divergence = True
    enforce_specular = True

    datasets = []
    for data in url_load_list(filelist, loader=gansref.load_entries):
        data.Qz_basis = Qz_basis
        if intent not in [None, 'auto']:
            data.intent = intent
        if data.intent == 'specular' and enforce_specular:
            if data.Qz_basis == 'detector':
                data.sample.angle_x = data.sample.angle_x_target = data.detector.angle_x / 2.0
            elif data.Qz_basis == 'sample':
                data.detector.angle_x = data.detector.angle_x_target = data.sample.angle_x * 2.0
        if data.intent.startswith('background'):
            if data.Qz_basis == 'detector':
                data.Qz_target = 4 * np.pi / data.monochromator.wavelength * np.sin(np.radians(data.detector.angle_x_target / 2.0))
            elif data.Qz_basis == 'sample':
                data.Qz_target = 4 * np.pi / data.monochromator.wavelength * np.sin(np.radians(data.sample.angle_x_target))
            else:
                data.Qz_target = data.Qz
      
        if slit1_distance is not None:
            data.slit1.distance = slit1_distance
        if slit1_aperture is not None:
            data.slit1.x = data.slit1.x_target = slit1_aperture
        if slit1_rotary:
            data.slit1.x = _convert_slitrotation_to_aperture(data.slit1.x)
            data.slit1.x_target = copy.copy(data.slit1.x)
        if slit2_distance is not None:
            data.slit2.distance = slit2_distance
        if slit2_aperture is not None:
            data.slit2.x = data.slit2.x_target = slit2_aperture
        if slit2_rotary:
            data.slit2.x = _convert_slitrotation_to_aperture(data.slit2.x)
            data.slit2.x_target = copy.copy(data.slit2.x)            
        if slit3_distance is not None:
            data.slit3.distance = slit3_distance
        if slit3_aperture is not None:
            data.slit3.x = data.slit3.x_target = slit3_aperture
        if slit3_rotary:
            data.slit3.x = _convert_slitrotation_to_aperture(data.slit3.x)
            data.slit3.x_target = copy.copy(data.slit3.x)
        if slit4_distance is not None:
            data.slit4.distance = slit4_distance
        if slit4_aperture is not None:
            data.slit4.x = data.slit4.x_target = slit4_aperture
        if slit4_rotary:
            data.slit4.x = _convert_slitrotation_to_aperture(data.slit4.x)
            data.slit4.x_target = copy.copy(data.slit4.x)                        
        if auto_divergence:
            data = divergence(data, sample_width)
        
        data = normalize(data, base='time')
        print("data loaded and normalized")
        datasets.append(data)

    return datasets

@module
def fit_rocking_curve(rock, A0=None, x00=None, sigma0=None, bkg0=None):
    """
    Fit a rocking curve to a Gaussian plus background model.

    The rocking curve datasets are fit using a Levenberg-Marquardt algorithm to a model
    involving four parameters:
     o A, the (possibly negative) Gaussian amplitude
     o x0, the center of the Gaussian
     o sigma, the width of the Gaussian
     o bkg, the background level of the Gaussian

    **Inputs**

    rock (refldata) : single rocking curve

    A0 {Amplitude guess} (float) : initial guess for amplitude

    x00 {Gaussian center guess} (float) : initial guess for center

    sigma0 {width guess} (float) : initial guess for width

    bkg0 {background guess} (float) : initial guess for background
    
    **Returns**

    fitparams (gans.fitters.gaussianparams) : fit parameters, errors, and chi-squared

    fit (refldata) : ReflData structure containing fit outputs (for plotting against
    inputs to inspect fit)

    2024-12-04 David P. Hoogerheide
    """

    from .alignfit import fit_gaussian_background

    bff, rock2 = fit_gaussian_background(rock, A0, sigma0, x00, bkg0)

    return bff, rock2


@module
def fit_slit_alignment(slit_align, m0=None, x00=None):
    """
    Fit a slit alignment curve to a linear model with x-intercept.

    The slit alignment datasets are fit using a Levenberg-Marquardt algorithm to a model
    involving four parameters:
     o m, the linear slope
     o x0, the x-intercept of the line

    **Inputs**

    slit_align (refldata) : slit alignment curve

    m0 {slope guess} (float) : initial guess for slope

    x00 {x-intercept guess} (float) : initial guess for x intercept
    
    **Returns**

    fitparams (gans.fitters.linearparams) : fit parameters, errors, and chi-squared

    fit (refldata) : ReflData structure containing fit outputs (for plotting against
    inputs to inspect fit)

    2024-12-04 David P. Hoogerheide
    """

    from .alignfit import fit_line_xintercept

    bff, slit_align2 = fit_line_xintercept(slit_align, m0, x00)

    return bff, slit_align2
