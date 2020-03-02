"""
Support for different export types.

See :class:`dataflow.core.DataType` for details.
"""
from functools import wraps

def text(datasets, export_method=None, template_data=None, concatenate=False):
    import json

    header_string = "#" + json.dumps(template_data, separators=(',', ':'))[1:-1] + "\n"
    outputs = []
    if len(datasets) > 0:
        exports = [getattr(d, export_method)() for d in datasets]
        if concatenate:
            first = exports[0]
            name = first.get("name", "default_name")
            entry = first.get("entry", "entry")
            file_suffix = first.get("file_suffix", ".dat")
            filename = "%s_%s%s" % (name, entry, file_suffix)
            export_strings = [e['value'] for e in exports]
            export_string = header_string + "\n\n".join(export_strings)
            outputs.append({"filename": filename, "value": export_string})
        else:
            for i, e in enumerate(exports):
                export_string = header_string + e["value"]
                name = e.get("name", "default_name_%d" %(i,))
                entry = e.get("entry", "entry")
                file_suffix = e.get("file_suffix", ".dat")
                filename = "%s_%s%s" % (name, entry, file_suffix)
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
    import json
    import io
    import h5py

    header_string = json.dumps(template_data, separators=(',', ':'))
    outputs = []
    if len(datasets) > 0:
        exports = [getattr(d, export_method)() for d in datasets]
        if concatenate:
            first = exports[0]
            name = first.get("name", "default_name")
            entry = first.get("entry", "entry")
            file_suffix = first.get("file_suffix", ".hdf5")
            filename = "%s_%s%s" % (name, entry, file_suffix)
            fid = io.BytesIO()
            container = h5py.File(fid)
            _set_nexus_attrs(container, filename)
            container.attrs["template_def"] = header_string
            for e in exports:
                h5_item = e["value"]
                group_to_copy = list(h5_item.values())[0]
                group_name = "%s_%s" % (e["name"], e["entry"])
                container.copy(group_to_copy, group_name)
                h5_item.close()
            container.close()
            fid.seek(0)
            outputs.append({"filename": filename, "value": fid.read()})
        else:
            for e in exports:
                name = e.get("name", "default_name")
                entry = e.get("entry", "entry")
                file_suffix = e.get("file_suffix", ".hdf5")
                filename = "%s_%s%s" % (name, entry, file_suffix)

                h5_item = e["value"]
                _set_nexus_attrs(h5_item, filename)
                h5_item.attrs["template_def"] = header_string
                h5_item.flush()
                value = h5_item.id.get_file_image()
                h5_item.close()
                outputs.append({"filename": filename, "value": value})

    return outputs


def png(datasets, export_method=None, template_data=None, concatenate=False):
    # NOTE: concatenate not supported for PNG - keyword ignored.
    import json
    import io
    from PIL import PngImagePlugin

    header_string = json.dumps(template_data, separators=(',', ':'))

    exports = [getattr(d, export_method)() for d in datasets]
    outputs = []
    for e in exports:
        name = e.get("name", "default_name")
        entry = e.get("entry", "entry")
        file_suffix = e.get("file_suffix", ".png")
        filename = "%s_%s%s" % (name, entry, file_suffix)

        image = PngImagePlugin.PngImageFile(e["value"])
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
        outputs.append({"filename": filename, "value": value})

    return outputs


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
