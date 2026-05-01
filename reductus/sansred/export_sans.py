import csv
import pathlib
import os

from io import BytesIO

import h5py
import numpy as np

from reductus.sansred.sansdata import Sans1dData, SansIQData, SansData

Path_Like = os.path, pathlib.Path, str


def _get_full_path(f_path: Path_Like, data: SansData, ext: str):
    f_path = pathlib.Path(f_path)
    if f_path.is_dir():
        file_name = data.metadata.get("run.filename", b"default_name").decode('UTF-8') + ext
        full_path = f_path / file_name
    else:
        full_path = f_path
    print(f"DEBUG: Full path: {full_path}")
    return full_path


def export_to_csv(data, file_path: Path_Like) -> bool:
    """Exports a data set to a csv formatted file. This call """
    return export_to_ascii(data, file_path, ".csv", ",")


def export_to_ascii(data, file_path: Path_Like = "", extension: str = ".txt", delimiter: str = " ") -> dict:
    print("Am I getting here?")
    data_as_str = ''
    header = ''
    columns = [[],[],[],[]]
    # Ensure a file path is supplied and construct the path, if needed
    if not file_path:
        return {}
    # Determine the data type (1D reduced, 2D reduced, 2D pixel space, etc.) and assign headers/locations for each data
    # TODO: Include all columns in each file
    if isinstance(data, SansData):
        # 2D data can only be output into the .DAT format - do this
        extension = ".dat"
        columns = [data.qx, data.qy, data.data, np.sqrt(data.data)]
        delimiter = " "
        header = 'Data columns are Qx - Qy - I(Qx,Qy) - err(I) - Qz - SigmaQ_parall - SigmaQ_perp - fSubS(beam stop shadow)'
    elif isinstance(data, Sans1dData):
        columns = [data.x, data.v, data.dv, data.dx]
        header = delimiter.join(['<X>', '<Y>', '<dY>', '<dsigQ>'])
    elif isinstance(data, SansIQData):
        columns = [data.Q, data.I, data.dI, data.dQ]
        header = delimiter.join(['<X>', '<Y>', '<dY>', '<dsigQ>'])

    # Set the file path to a common format
    full_path = _get_full_path(file_path, data, extension)
    transposed_data = list(zip(*columns))
    print(f"DEBUG: transposed_data: {transposed_data}")
    # Write to the file
    try:
        with open(full_path, "w") as f:
            f.write(header)
            writer = csv.writer(f, delimiter=delimiter)
            writer.writerows(transposed_data)
    except (PermissionError, OSError, FileExistsError):
        return {}
    return {}


def export_to_nxcansas(data: SansIQData, f_path: Path_Like) -> dict:
    # TODO: Allow for 2D data to be exported
    # Ensure data is in Q-space (reduced data only!) and if it is 1D or 2D data
    if not isinstance(data, SansIQData):
        return {}

    full_path = _get_full_path(f_path, data, '.h5')

    with h5py.File(full_path, 'w') as h5_item:

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
        nxentry["run"] = data.metadata.get("run.pointnum", 0)
        nxentry["title"] = data.metadata["sample.description"]

        # TODO: Differentiate 1D vs. 2D data here
        # Add data
        data_group = nxentry.create_group("data")
        data_group.attrs.update({
            "NX_class": "NXdata",
            "canSAS_class": "SASdata",
            "signal": "I",
            "I_axes": "Q",
            "Q_indices": [0]
        })
        data_group["I"] = data.I
        data_group["I"].attrs.update({
            "units": "1/cm",
            "uncertainties": "Idev"
        })
        data_group["Q"] = data.Q
        data_group["Q"].attrs.update({
            "units": "1/nm",
            "resolutions": "dQ"
        })
        data_group["dQ"] = data.dQ
        data_group["dQ"].attrs["units"] = "1/nm"
        data_group["Idev"] = data.dI
        data_group["Idev"].attrs["units"] = "1/cm"
        data_group["Qmean"] = data.meanQ
        data_group["ShadowFactor"] = data.ShadowFactor

        # Add sample information
        sample_entry = nxentry.create_group('sassample')
        sample_entry.attrs.update({
            'canSAS_class': 'SASsample',
            'NX_class': "NXsample"
        })
        sample_entry['ID'] = data.metadata.get('sample.name', 'sample')
        sample_attrs = ['thk', 'temp', 'trans']
        sample_nxcansas = ['thickness', 'temperature', 'transmission']
        for key, cansas_key in zip(sample_attrs, sample_nxcansas):
            if (value := data.metadata.get(f'sample.{key}', None)) is not None:
                sample_entry.create_dataset(cansas_key, data=value)

        # Add instrument
        instrument_group = nxentry.create_group("instrument")
        instrument_group.attrs.update({
            "NX_class": "NXinstrument",
            "canSAS_class": "SASinstrument"
        })
        instrument_group['name'] = data.metadata["sample.description"]

    return {}
