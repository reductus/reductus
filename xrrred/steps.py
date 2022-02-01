from reflred.steps import ncnr_load, subtract_background, divide_intensity, rescale, mask_points, join, divergence, normalize

from dataflow.automod import module


@module
def load(filelist=None,
        intent='auto',
        Qz_basis='actual',
        sample_width=None,
        incident_divergence=None,
        ):
    r"""
    Load a list of X-ray Reflectivity files.

    *Qz_basis* uses one of the following values:

        **actual**
            calculates Qx and Qz as (x,z)-components of
            $(\vec k_{\text{out}} - \vec k_\text{in})$ in sample coordinates,
        **detector**
            ignores the sample angle and calculates Qz
            as $(4\pi/\lambda \sin(\theta_\text{detector}/2))$,
        **sample**
            ignores the detector angle and calculates Qz
            as $(4\pi/\lambda \sin(\theta_\text{sample}))$
        **target**
            uses the user-supplied Qz_target values

    **Inputs**

    filelist (fileinfo[]): List of files to open.

    intent (opt:auto|specular|background+\|background-\|intensity|rock sample|rock detector|rock qx|scan)
    : Measurement intent (specular, background+, background-, slit, rock),
    auto or infer.  If intent is 'scan', then use the first scanned variable.

    Qz_basis (opt:actual|detector|sample|target)
    : How to calculate Qz from instrument angles.

    sample_width {Sample width (mm)} (float?)
    : Width of the sample along the beam direction in mm, used for
    calculating the effective resolution when the sample is smaller
    than the beam.  Leave blank to use value from data file.

    incident_divergence {incident beam divergence (deg)} (float?)
    : If the incident beam divergence is a known constant, enter it here,
    and it will be used instead of trying to calculate divergence from the
    optics defined in the data file.

    **Returns**

    output (refldata[]): All entries of all files in the list.

    | 2022-01-31 Brian Maranville
    """
    from reflred.load import url_load_list
    from reflred import xrawref
    
    # TODO: sample_width is ignored if datafile defines angular_divergence
    auto_divergence = (incident_divergence is None)

    datasets = []
    for data in url_load_list(filelist, loader=xrawref.load_entries):
        data.Qz_basis = Qz_basis
        if intent not in [None, 'auto']:
            data.intent = intent
        if auto_divergence:
            data = divergence(data, sample_width)
        else:
            data.angular_resolution = incident_divergence
        
        data = normalize(data, base='time')
        #print "data loaded and normalized"
        datasets.append(data)

    return datasets
