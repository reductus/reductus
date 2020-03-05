"""
Support for different export types.

See :class:`dataflow.core.DataType` for details.
"""
import io
import json
from functools import wraps

import numpy as np

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)

def json_dumps(obj):
    return json.dumps(obj, separators=(",", ":"), cls=NumpyEncoder)

def _build_filename(export, ext="", index=None):
    index_tag = f"_{index}" if index is not None else ""
    name = export.get("name", "unknown"+index_tag)
    entry = export.get("entry", "entry")
    ext = export.get("file_suffix", ext)
    filename = f"{name}_{entry}{ext}"
    return filename

def json_writer(datasets, export_method=None, template_data=None, concatenate=False):
    exports = [getattr(d, export_method)() for d in datasets]
    outputs = []
    if concatenate and exports:
        data = {
            "template_data": template_data,
            "outputs": [export["value"] for export in exports],
        }
        export_string = json_dumps(data)
        #export_string = export_string.encode('utf-8')
        filename = _build_filename(exports[0], ext=".dat", index=None)
        outputs.append({"filename": filename, "value": export_string})
    else:
        for i, export in enumerate(exports):
            data = {
                "template_data": template_data,
                "outputs": [export["value"]],
                #"index": i,   # TODO: do we want the output index?
            }
            export_string = json_dumps(data)
            #export_string = export_string.encode('utf-8')
            filename = _build_filename(exports[0], ext=".dat", index=i)
            outputs.append({"filename": filename, "value": export_string})
    return outputs

def text(datasets, export_method=None, template_data=None, concatenate=False):
    header_string = json_dumps(template_data)
    header_string = f"#{header_string[1:-1]}\n"
    exports = [getattr(d, export_method)() for d in datasets]
    outputs = []
    if concatenate and exports:
        parts = (export['value'] for export in exports)
        export_string = header_string + "\n\n".join(parts)
        #export_string = export_string.encode('utf-8')
        filename = _build_filename(exports[0], ext=".dat")
        outputs.append({"filename": filename, "value": export_string})
    else:
        for i, export in enumerate(exports):
            export_string = header_string + export["value"]
            #export_string = export_string.encode('utf-8')
            filename = _build_filename(exports[0], ext=".dat", index=i)
            outputs.append({"filename": filename, "value": export_string})
    return outputs


NEXUS_VERSION = "4.2.1"
def _set_nexus_attrs(h5_item, filename):
    from h5py.version import hdf5_version
    from . import iso8601

    h5_item.attrs['NX_class'] = "NXroot"
    h5_item.attrs['file_name'] = filename
    h5_item.attrs['file_time'] = iso8601.now()
    h5_item.attrs['HDF5_Version'] = hdf5_version
    h5_item.attrs['NeXus_version'] = NEXUS_VERSION

def hdf(datasets, export_method=None, template_data=None, concatenate=False):
    import h5py

    header_string = json_dumps(template_data)
    exports = [getattr(d, export_method)() for d in datasets]
    outputs = []
    if concatenate and exports:
        filename = _build_filename(exports[0], ext=".hdf5", index=None)
        fid = io.BytesIO()
        container = h5py.File(fid)
        _set_nexus_attrs(container, filename)
        container.attrs["template_def"] = header_string
        for export in exports:
            h5_item = export["value"]
            group_to_copy = list(h5_item.values())[0]
            group_name = "%s_%s" % (export["name"], export["entry"])
            container.copy(group_to_copy, group_name)
            h5_item.close()
        container.close()
        fid.seek(0)
        outputs.append({"filename": filename, "value": fid.read()})
    else:
        for i, export in exports:
            filename = _build_filename(exports[0], ext=".hdf5", index=i)
            h5_item = export["value"]
            _set_nexus_attrs(h5_item, filename)
            h5_item.attrs["template_def"] = header_string
            h5_item.flush()
            value = h5_item.id.get_file_image()
            h5_item.close()
            outputs.append({"filename": filename, "value": value})

    return outputs


def png(datasets, export_method=None, template_data=None, concatenate=False):
    # NOTE: concatenate not supported for PNG - keyword ignored.
    from PIL import PngImagePlugin

    header_string = json_dumps(template_data)
    exports = [getattr(d, export_method)() for d in datasets]
    outputs = []
    for i, export in exports:
        image = PngImagePlugin.PngImageFile(export["value"])
        new_metadata = PngImagePlugin.PngInfo()
        existing_metadata = image.text
        for key, value in existing_metadata.items():
            if isinstance(value, PngImagePlugin.iTXt):
                new_metadata.add_itxt(key, value)
            elif isinstance(value, str):
                new_metadata.add_text(key, value)
        new_metadata.add_itxt("reductus_template.json", header_string)
        value = io.BytesIO()
        image.save(value, pnginfo=new_metadata)
        filename = _build_filename(exports[0], ext=".hdf5", index=i)
        outputs.append({"filename": filename, "value": value})

    return outputs


def exports_json(name="json"):
    def inner_function(f):
        f.exporter = json_writer
        f.export_name = name
        return f
    return inner_function


def exports_text(name="column"):
    def inner_function(f):
        f.exporter = text
        f.export_name = name
        return f
    return inner_function


def exports_HDF5(name="NeXus"):
    """
    Method should return a data block whose "value" key is associated with an
    open h5py File object. The object will be closed after the data is
    extracted for export.
    """
    def inner_function(f):
        f.exporter = hdf
        f.export_name = name
        return f
    return inner_function


def exports_PNG(name="PNG"):
    def inner_function(f):
        f.exporter = png
        f.export_name = name
        return f
    return inner_function
