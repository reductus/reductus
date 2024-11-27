from reflred.steps import subtract_background, divide_intensity, rescale, mask_points, join, divergence, normalize, abinitio_footprint, fit_footprint, correct_footprint

from dataflow.automod import module


@module
def load(filelist=None,
        intent='auto',
        Qz_basis='detector',
        sample_width=None,
        slit1_distance=None,
        slit1_aperture=None,
        slit2_distance=None,
        slit2_aperture=None,
        slit3_distance=None,
        slit3_aperture=None,
        slit4_distance=None,
        slit4_aperture=None        
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

    intent (opt:auto|specular|background+\|background-\|intensity|rock sample|rock detector|rock qx|scan)
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

    slit2_distance {override slit2 distance} (float?)
    : if specified, will override the value found in the file for
    the distance from the sample to slit 2

    slit2_aperture {override slit2 aperture} (float?)
    : if specified, will override the value found in the file for
    the opening of slit 2 in mm

    slit3_distance {override slit3 distance} (float?)
    : if specified, will override the value found in the file for
    the distance from the sample to slit 3

    slit3_aperture {override slit3 aperture} (float?)
    : if specified, will override the value found in the file for
    the opening of slit 3 in mm

    slit4_distance {override slit4 distance} (float?)
    : if specified, will override the value found in the file for
    the distance from the sample to slit 4

    slit4_aperture {override slit4 aperture} (float?)
    : if specified, will override the value found in the file for
    the opening of slit 4 in mm    

    **Returns**

    output (refldata[]): All entries of all files in the list.

    | 2024-11-26 David Hoogerheide
    """
    from reflred.load import url_load_list
    from reflred import gansref
    
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
        if slit1_distance is not None:
            data.slit1.distance = slit1_distance
        if slit1_aperture is not None:
            data.slit1.x = data.slit1.x_target = slit1_aperture
        if slit2_distance is not None:
            data.slit2.distance = slit2_distance
        if slit2_aperture is not None:
            data.slit2.x = data.slit2.x_target = slit2_aperture
        if slit3_distance is not None:
            data.slit3.distance = slit3_distance
        if slit3_aperture is not None:
            data.slit3.x = data.slit3.x_target = slit3_aperture
        if slit4_distance is not None:
            data.slit4.distance = slit4_distance
        if slit4_aperture is not None:
            data.slit4.x = data.slit4.x_target = slit4_aperture            
        if auto_divergence:
            data = divergence(data, sample_width)
        
        data = normalize(data, base='time')
        print("data loaded and normalized")
        datasets.append(data)

    return datasets
