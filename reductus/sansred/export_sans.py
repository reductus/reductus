import io
import numpy as np

from reductus.dataflow.lib.uncertainty import Uncertainty


def _sans_types():
    """Import the SANS data classes lazily to avoid a circular import with sansdata."""
    from reductus.sansred.sansdata import Sans1dData, SansIQData, SansData
    return Sans1dData, SansIQData, SansData


def _name_and_entry(data) -> dict:
    metadata = getattr(data, "metadata", None) or {}
    return {
        "name": metadata.get("name", getattr(data, "name", "default_name")),
        "entry": metadata.get("entry", "default_entry"),
    }


def _set_if_present(group, key, value):
    """h5py cannot store None, so skip metadata values that are missing."""
    if value is not None:
        group[key] = value


def export_to_csv(data) -> dict:
    """Exports a data set to a csv formatted file. This call """
    return export_to_ascii(data, delimiter=',', extension='.csv')


def export_to_ascii(data, delimiter: str = " ", extension: str = ".txt") -> dict:
    Sans1dData, SansIQData, SansData = _sans_types()
    # Determine the data type (1D reduced, 2D reduced, 2D pixel space, etc.) and assign headers/locations for each data
    if isinstance(data, SansData):
        # 2D data can only be output into the .DAT format - do this
        extension = ".dat"
        intensity = data.data.x if isinstance(data.data, Uncertainty) else np.asarray(data.data)
        columns = [np.ravel(data.qx), np.ravel(data.qy), np.ravel(intensity), np.ravel(np.sqrt(intensity))]
        header = 'Data columns are Qx - Qy - I(Qx,Qy) - err(I)'
    elif isinstance(data, Sans1dData):
        columns = [data.x, data.v, data.dv, data.dx]
        header = delimiter.join(['<X>', '<Y>', '<dY>', '<dsigQ>'])
    elif isinstance(data, SansIQData):
        columns = [data.Q, data.I, data.dI, data.dQ]
        header = delimiter.join(['<X>', '<Y>', '<dY>', '<dsigQ>'])
    else:
        header = ''
        columns = [[], [], [], []]

    with io.StringIO() as fid:
        fid.write(header + "\n")
        if len(columns[0]):
            np.savetxt(fid, np.vstack(columns).T, fmt="%.10e", delimiter=delimiter)
        value = fid.getvalue()

    return {**_name_and_entry(data), "value": value, "file_suffix": extension}


def export_to_nxcansas(data) -> dict:
    """
    Build an NXcanSAS structure for *data*.

    Returns an export block for :func:`reductus.dataflow.lib.exporters.hdf`
    (use with the ``exports_HDF5`` decorator). The "value" is an *open*
    h5py.File; the hdf exporter adds the NeXus root attributes and template,
    extracts the file image, and closes it.
    """
    Sans1dData, SansIQData, SansData = _sans_types()
    if not isinstance(data, (Sans1dData, SansIQData, SansData)):
        return {}

    import h5py

    fid = io.BytesIO()
    h5_item = h5py.File(fid, 'w')  # left open: the hdf exporter closes it

    # Create Base SASentry
    entry_name = data.metadata.get("entry", "SASentry")
    nxentry = h5_item.create_group(entry_name)
    nxentry.attrs.update({
        "NX_class": "NXentry",
        "canSAS_class": "SASentry",
        "version": "1.1"
    })

    # Add required information
    nxentry["definition"] = "NXcanSAS"
    nxentry["run"] = data.metadata.get("run.instrumentScanID", 0)
    nxentry["title"] = data.metadata["sample.description"]

    # Add data
    data_group = nxentry.create_group("data")
    if isinstance(data, SansData):
        data_group.attrs.update({
            "NX_class": "NXdata",
            "canSAS_class": "SASdata",
            "signal": "I",
            "I_axes": "Qx, Qy",
            "Q_indices": [0,1]
        })
        if isinstance(data.data, Uncertainty):
            data_group["I"] = data.data.x
            data_group["Idev"] = data.data.dx
        else:
            data_group["I"] = data.data
        data_group["I"].attrs.update({
            "units": "1/cm",
            "uncertainties": "Idev"
        })
        data_group["Q"] = [data.qx, data.qy]
        if hasattr(data, "qz"):
            data_group["Q"].append(data.qz)
            data_group.attrs["I_axes"] = "Qx, Qy, Qz"
            data_group.attrs["Q_indices"] = [0, 1, 2]
        data_group["Q"].attrs.update({
            "units": "1/A",
            "resolutions": "dQ"
        })
        data_group["dQ"] = [data.dq_perp, data.dq_para]
        data_group["dQ"].attrs["units"] = "1/A"
        data_group["Idev"].attrs["units"] = "1/cm"
        data_group["Qmean"] = data.meanQ
        data_group["ShadowFactor"] = data.shadow_factor
    else:
        data_group.attrs.update({
            "NX_class": "NXdata",
            "canSAS_class": "SASdata",
            "signal": "I",
            "I_axes": "Q",
            "Q_indices": [0]
        })
        if isinstance(data, Sans1dData):
            # Sans1dData stores generic x/v columns rather than Q/I
            I, dI, Q, dQ = data.v, data.dv, data.x, data.dx
            meanQ = shadow_factor = None
        else:
            I, dI, Q, dQ = data.I, data.dI, data.Q, data.dQ
            meanQ, shadow_factor = data.meanQ, data.ShadowFactor
        data_group["I"] = I
        data_group["I"].attrs.update({
            "units": "1/cm",
            "uncertainties": "Idev"
        })
        data_group["Q"] = Q
        data_group["Q"].attrs.update({
            "units": "1/A",
            "resolutions": "dQ"
        })
        if dQ is not None:
            data_group["dQ"] = dQ
            data_group["dQ"].attrs["units"] = "1/A"
        if dI is not None:
            data_group["Idev"] = dI
            data_group["Idev"].attrs["units"] = "1/cm"
        if meanQ is not None:
            data_group["Qmean"] = meanQ
        if shadow_factor is not None:
            data_group["ShadowFactor"] = shadow_factor

    # Add sample information
    sample_entry = nxentry.create_group('sassample')
    sample_entry.attrs.update({
        'canSAS_class': 'SASsample',
        'NX_class': "NXsample"
    })
    sample_entry['ID'] = data.metadata.get('sample.labl', 'sample')
    sample_attrs = ['thk', 'temp', 'trans']
    sample_units = ['mm', 'K', '%']
    sample_nxcansas = ['thickness', 'temperature', 'transmission']
    for key, cansas_key, unit in zip(sample_attrs, sample_nxcansas, sample_units):
        if (value := data.metadata.get(f'sample.{key}', None)) is not None:
            sample_entry.create_dataset(cansas_key, data=value)
            sample_entry[cansas_key].attrs['units'] = unit

    # Add instrument
    instrument_group = nxentry.create_group("instrument")
    instrument_group.attrs.update({
        "NX_class": "NXinstrument",
        "canSAS_class": "SASinstrument"
    })
    instrument_group['name'] = data.metadata["run.instrument"]

    # Add source aperture
    source_aperture = instrument_group.create_group('aperture1')
    source_aperture.attrs.update({
        "NX_class": "NXaperture",
        "canSAS_class": "SASaperture"
    })
    source_aperture['shape'] = 'pinhole'
    _set_if_present(source_aperture, 'x_gap', data.metadata.get('resolution.ap1'))
    _set_if_present(source_aperture, 'y_gap', data.metadata.get('resolution.ap1'))

    # Add sample aperture
    sample_aperture = instrument_group.create_group('aperture2')
    sample_aperture.attrs.update({
        "NX_class": "NXaperture",
        "canSAS_class": "SASaperture"
    })
    sample_aperture['shape'] = 'pinhole'
    _set_if_present(sample_aperture, 'x_gap', data.metadata.get('resolution.ap2'))
    _set_if_present(sample_aperture, 'y_gap', data.metadata.get('resolution.ap2'))

    # Add collimation settings
    collimation = instrument_group.create_group('collimator')
    collimation.attrs.update({
        "NX_class": "NXcollimation",
        "canSAS_class": "SAScollimation"
    })
    _set_if_present(collimation, 'distance', data.metadata.get('resolution.ap12dis'))

    # Add detector settings
    detector = instrument_group.create_group('detector')
    detector.attrs.update({
        "NX_class": "NXdetector",
        "canSAS_class": "SASdetector"
    })
    detector['name'] = 'detector'
    _set_if_present(detector, 'SDD', data.metadata.get('det.dis'))
    _set_if_present(detector, 'beam_center_x', data.metadata.get('det.beamx'))
    _set_if_present(detector, 'beam_center_y', data.metadata.get('det.beamy'))
    _set_if_present(detector, 'x_pixel_size', data.metadata.get('det.pixelsizex'))
    _set_if_present(detector, 'y_pixel_size', data.metadata.get('det.pixelsizey'))

    # Add source information
    source = instrument_group.create_group('source')
    source.attrs.update({
        "NX_class": "NXsource",
        "canSAS_class": "SASsource"
    })
    source['type'] = 'Reactor Neutron Source'
    _set_if_present(source, 'incident_wavelength', data.metadata.get('resolution.lmda'))
    _set_if_present(source, 'incident_wavelength_spread', data.metadata.get('resolution.dlmda'))

    return {
        **_name_and_entry(data),
        "entry": entry_name,
        "file_suffix": ".nxs.h5",
        "value": h5_item,
    }
