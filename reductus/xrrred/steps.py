from reductus.reflred.steps import ncnr_load, subtract_background, divide_intensity, rescale, mask_points, join, divergence, normalize, abinitio_footprint, fit_footprint, correct_footprint

from reductus.dataflow.automod import module


@module
def load(filelist=None,
        intent='auto',
        Qz_basis='detector',
        sample_width=None,
        slit1_distance=None,
        slit1_aperture=None,
        slit2_distance=None,
        slit2_aperture=None
        ):
    r"""
    Load a list of X-ray Reflectivity files.

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

    **Returns**

    output (refldata[]): All entries of all files in the list.

    | 2022-01-31 Brian Maranville
    | 2022-04-27 Brian Maranville fix count time for Rigaku in sweep mode
    """
    from reductus.reflred.load import url_load_list
    from reductus.reflred import xrawref
    
    # TODO: sample_width is ignored if datafile defines angular_divergence
    auto_divergence = True
    enforce_specular = True

    datasets = []
    for data in url_load_list(filelist, loader=xrawref.load_entries):
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
        if auto_divergence:
            data = divergence(data, sample_width)
        
        data = normalize(data, base='time')
        #print "data loaded and normalized"
        datasets.append(data)

    return datasets
