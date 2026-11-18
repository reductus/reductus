"""
NXcanSAS export for VSANS data
==============================

Builds NXcanSAS structures for the :mod:`reductus.vsansred.vsansdata` types.
Like :mod:`reductus.sansred.export_sans`, the builders return an export block
whose "value" is an *open* h5py.File; the shared
:func:`reductus.dataflow.lib.exporters.hdf` exporter adds the NeXus root
attributes and the active template, extracts the file image and closes it.

* 1D data (circular averages) are written as a single SASdata group per run,
  with the per-panel I(Q) merged and sorted by Q. See :func:`hdf_1d`.
* 2D (Q-space) data are written as one SASentry with a separate SASdata group
  for each detector panel.

In both cases the SASinstrument holds one SASdetector per panel, and the full
reduction metadata is kept as JSON in a SASnote so nothing is lost.
"""
import io
import json
from collections import OrderedDict

import numpy as np

from reductus.sansred.export_sans import _add_sasprocess

#: Default intensity units when the data are not on an absolute scale.
ARBITRARY_UNITS = "arbitrary"
#: Metadata key recording the intensity units (set by absolute_scaling).
INTENSITY_UNITS_KEY = "intensity.units"
#: Metadata key holding the panel geometry list (see :func:`panel_geometry`).
DETECTORS_KEY = "detectors"
Q_UNITS = "1/angstrom"

_CANSAS_I_UNITS = {"1/m", "1/cm", "m2/g", "cm2/g", ARBITRARY_UNITS}


# ---------------------------------------------------------------------------
# Value helpers
# ---------------------------------------------------------------------------

def _s(value):
    return value.decode("utf-8") if isinstance(value, bytes) else value


def _clean(value):
    """Return *value* in a form h5py can store, or None if it can't be stored."""
    if value is None:
        return None
    if isinstance(value, (str, bytes)):
        return _s(value)
    arr = np.asarray(value)
    if arr.dtype.kind in "biuf":
        return arr[()] if arr.ndim == 0 else arr
    if arr.dtype.kind == "U":
        return str(arr[()]) if arr.ndim == 0 else np.char.encode(arr, "utf-8")
    if arr.dtype.kind == "S":
        return _s(arr[()]) if arr.ndim == 0 else arr
    return None


def _is_number(value):
    value = _clean(value)
    return value is not None and np.asarray(value).dtype.kind in "biuf"


def _set(group, key, value, units=None, numeric=False):
    """Write *value* to group[key] (with optional units); skip missing values."""
    value = _clean(value)
    if value is None or (numeric and not _is_number(value)):
        return None
    group[key] = value
    if units:
        group[key].attrs["units"] = units
    return group[key]


def _scalar(value):
    arr = np.asarray(value)
    return arr.ravel()[0] if arr.size == 1 else arr


def _intensity_units(metadata, vunits=None):
    units = _s(metadata.get(INTENSITY_UNITS_KEY)) if metadata else None
    if units in _CANSAS_I_UNITS:
        return units
    if vunits in _CANSAS_I_UNITS:
        return vunits
    return ARBITRARY_UNITS


def _json_metadata(metadata):
    from reductus.dataflow.lib.exporters import json_dumps
    from .vsansdata import _toDictItem
    return json_dumps(_toDictItem(dict(metadata), convert_bytes=True), compact=False)


def name_and_entry(metadata):
    metadata = metadata or {}
    name = _s(metadata.get("run.filename") or metadata.get("name") or "default_name")
    name = str(name).split(".nxs")[0]  # sans33722.nxs.ngv -> sans33722
    entry = _s(metadata.get("entry") or "sasentry01")
    return {"name": name, "entry": str(entry)}


# ---------------------------------------------------------------------------
# Panel geometry
# ---------------------------------------------------------------------------

def _raw(det, key):
    """Value and units of a field copied from the raw NeXus detector group."""
    item = det.get(key, None)
    if not isinstance(item, dict) or "value" not in item:
        return None, None
    units = _s(item.get("attrs", {}).get("units", None))
    return _scalar(item["value"]), units


def panel_geometry(short_name, det):
    """
    Summarize the geometry of one detector panel as a JSON-friendly dict.

    *det* is a detector entry from a VSansData object after calculate_XY,
    i.e. it holds the raw NeXus fields plus Z, dX and dY (cm).
    """
    info = OrderedDict(name=short_name)

    def put(key, value, units):
        if value is not None:
            info[key] = {"value": _scalar(value), "units": units}

    if "Z" in det:
        put("SDD", det["Z"], "cm")
    value, units = _raw(det, "beam_center_x")
    put("beam_center_x", value, units or ("pixels" if short_name == "B" else "cm"))
    value, units = _raw(det, "beam_center_y")
    put("beam_center_y", value, units or ("pixels" if short_name == "B" else "cm"))
    if "dX" in det:
        put("x_pixel_size", det["dX"], "cm")
    if "dY" in det:
        put("y_pixel_size", det["dY"], "cm")
    value, units = _raw(det, "lateral_offset")
    put("x_position", value, units or "cm")
    value, units = _raw(det, "vertical_offset")
    put("y_position", value, units or "cm")
    value, _ = _raw(det, "tube_orientation")
    if value is not None:
        info["tube_orientation"] = str(_s(value))
    return info


# ---------------------------------------------------------------------------
# NXcanSAS group builders
# ---------------------------------------------------------------------------

def _create_file_and_entry(metadata):
    import h5py

    fid = io.BytesIO()
    h5_item = h5py.File(fid, "w")  # left open: the hdf exporter closes it
    entry_name = name_and_entry(metadata)["entry"]
    nxentry = h5_item.create_group(entry_name)
    nxentry.attrs.update({
        "NX_class": "NXentry",
        "canSAS_class": "SASentry",
        "version": "1.1",
    })
    nxentry["definition"] = "NXcanSAS"
    run = metadata.get("run.instFileNum", None)
    if run is None:
        run = metadata.get("run.filename", None)
    nxentry["run"] = str(_s(run)) if _clean(run) is not None else ""
    title = metadata.get("sample.labl", None) or metadata.get("sample.name", None) or metadata.get("title", "")
    nxentry["title"] = str(_s(title))
    return h5_item, nxentry, entry_name


def _add_sassample(nxentry, metadata):
    sample = nxentry.create_group("sassample")
    sample.attrs.update({"NX_class": "NXsample", "canSAS_class": "SASsample"})
    sample["name"] = str(_s(metadata.get("sample.name", None) or metadata.get("sample.labl", None) or "sample"))
    _set(sample, "details", metadata.get("sample.labl", None))
    _set(sample, "thickness", metadata.get("sample.thk", None), units="cm", numeric=True)
    # The temperature log carries no units in the loaded metadata.
    _set(sample, "temperature", metadata.get("sample.temp", None), numeric=True)
    _set(sample, "transmission", metadata.get("sample.trans", None), numeric=True)
    return sample


def _add_sasdetector(instrument, panel):
    detector = instrument.create_group("sasdetector_%s" % panel["name"])
    detector.attrs.update({"NX_class": "NXdetector", "canSAS_class": "SASdetector"})
    detector["name"] = panel["name"]
    for key in ("SDD", "beam_center_x", "beam_center_y", "x_pixel_size",
                "y_pixel_size", "x_position", "y_position"):
        if key in panel:
            _set(detector, key, panel[key]["value"], units=panel[key]["units"], numeric=True)
    return detector


def _add_sasinstrument(nxentry, metadata, panels):
    instrument = nxentry.create_group("sasinstrument")
    instrument.attrs.update({"NX_class": "NXinstrument", "canSAS_class": "SASinstrument"})
    instrument["name"] = "NCNR VSANS"

    source = instrument.create_group("sassource")
    source.attrs.update({"NX_class": "NXsource", "canSAS_class": "SASsource"})
    source["type"] = "Reactor Neutron Source"
    source["probe"] = "neutron"
    wavelength = metadata.get("resolution.lmda", None)
    spread = metadata.get("resolution.dlmda", None)  # fractional FWHM (dL/L)
    _set(source, "incident_wavelength", wavelength, units="angstrom", numeric=True)
    if _is_number(wavelength) and _is_number(spread):
        _set(source, "incident_wavelength_spread",
             float(_clean(wavelength)) * float(_clean(spread)), units="angstrom")

    collimation = instrument.create_group("sascollimation")
    collimation.attrs.update({"NX_class": "NXcollimator", "canSAS_class": "SAScollimation"})
    _set(collimation, "distance", metadata.get("resolution.ap12dis", None), units="cm", numeric=True)
    _set(collimation, "guide", metadata.get("resolution.guide", None))
    for group_name, key in (("source_aperture", "resolution.ap1"),
                            ("sample_aperture", "resolution.ap2")):
        aperture = collimation.create_group(group_name)
        aperture.attrs.update({"NX_class": "NXaperture", "canSAS_class": "SASaperture"})
        value = metadata.get(key, None)
        if _is_number(value):
            aperture["shape"] = "pinhole"
            _set(aperture, "x_gap", value, units="cm")
            _set(aperture, "y_gap", value, units="cm")
        else:
            # e.g. 'OUT' for a source aperture that is not in the beam
            aperture["shape"] = str(_s(_clean(value))) if _clean(value) is not None else "unknown"

    for panel in panels:
        _add_sasdetector(instrument, panel)
    return instrument


def _add_sasnote(nxentry, metadata):
    """Keep every metadata value (polarization, logs, ...) as JSON."""
    note = nxentry.create_group("sasnote")
    note.attrs.update({"NX_class": "NXnote", "canSAS_class": "SASnote"})
    note["type"] = "application/json"
    note["description"] = "reductus metadata for this measurement"
    note["data"] = _json_metadata(metadata)
    return note


def _finish(h5_item, nxentry, entry_name, metadata, panels, file_suffix):
    _add_sassample(nxentry, metadata)
    _add_sasinstrument(nxentry, metadata, panels)
    _add_sasnote(nxentry, metadata)
    _add_sasprocess(nxentry)
    return {
        **name_and_entry(metadata),
        "entry": entry_name,
        "file_suffix": file_suffix,
        "value": h5_item,
    }


# ---------------------------------------------------------------------------
# 1D export
# ---------------------------------------------------------------------------

def export_1d_to_nxcansas(data):
    """NXcanSAS export block for a single VSans1dData (one SASdata group)."""
    metadata = data.metadata or {}
    panels = list(metadata.get(DETECTORS_KEY, None) or [])
    h5_item, nxentry, entry_name = _create_file_and_entry(metadata)

    datagroup = nxentry.create_group("sasdata01")
    nxentry.attrs["default"] = "sasdata01"
    datagroup.attrs.update({
        "NX_class": "NXdata",
        "canSAS_class": "SASdata",
        "signal": "I",
        "I_axes": "Q",
        "Q_indices": [0],
    })
    i_units = _intensity_units(metadata, getattr(data, "vunits", None))
    datagroup["I"] = np.asarray(data.v, dtype=float)
    datagroup["I"].attrs["units"] = i_units
    datagroup["Q"] = np.asarray(data.x, dtype=float)
    datagroup["Q"].attrs["units"] = Q_UNITS
    if data.dv is not None and np.size(data.dv) == np.size(data.v):
        datagroup["Idev"] = np.asarray(data.dv, dtype=float)
        datagroup["Idev"].attrs["units"] = i_units
        datagroup["I"].attrs["uncertainties"] = "Idev"
    if data.dx is not None and np.size(data.dx) == np.size(data.x):
        datagroup["Qdev"] = np.asarray(data.dx, dtype=float)
        datagroup["Qdev"].attrs["units"] = Q_UNITS
        datagroup["Q"].attrs["resolutions"] = "Qdev"

    return _finish(h5_item, nxentry, entry_name, metadata, panels, ".vsans1d.nxs.h5")


def _run_key(data):
    metadata = data.metadata or {}
    return (_s(metadata.get("run.filename", None)), _s(metadata.get("entry", None)))


def combine_panels(data_list, title="Overplotted Detectors"):
    """
    Merge the per-panel VSans1dData from one measurement into a single Q-sorted
    VSans1dData. Empty bins (dv == 0) are dropped; overlapping Q points are kept.
    The panel geometry of every input is kept in metadata["detectors"].

    Returns None if no data points remain.
    """
    from .vsansdata import VSans1dData

    valid = [d for d in data_list if d is not None and len(d.x) > 0]
    parts = []
    for d in valid:
        mask = np.asarray(d.dv) > 0
        if np.any(mask):
            parts.append((np.asarray(d.x)[mask], np.asarray(d.v)[mask],
                          np.asarray(d.dv)[mask], np.asarray(d.dx)[mask]))
    if not parts:
        return None

    x, v, dv, dx = (np.concatenate(columns) for columns in zip(*parts))
    order = np.argsort(x, kind="stable")

    first = valid[0]
    metadata = dict(first.metadata) if first.metadata else {}
    metadata["title"] = title
    panels = []
    for d in valid:
        for panel in (d.metadata or {}).get(DETECTORS_KEY, None) or []:
            if all(p.get("name") != panel.get("name") for p in panels):
                panels.append(panel)
    metadata[DETECTORS_KEY] = panels

    return VSans1dData(
        x=x[order], v=v[order], dx=dx[order], dv=dv[order],
        xlabel=first.xlabel, vlabel=first.vlabel,
        xunits=first.xunits, vunits=first.vunits,
        xscale=first.xscale, vscale=first.vscale,
        metadata=metadata,
    )


def hdf_1d(datasets, export_method=None, template_data=None, concatenate=False):
    """
    Exporter for VSans1dData: panels from the same measurement are merged into a
    single data set before being written with the shared hdf exporter, so the
    circular average of all panels lands in one SASdata group.
    """
    from reductus.dataflow.lib.exporters import hdf

    groups = OrderedDict()
    for d in datasets:
        groups.setdefault(_run_key(d), []).append(d)
    merged = [g[0] if len(g) == 1 else combine_panels(g) for g in groups.values()]
    merged = [d for d in merged if d is not None]
    return hdf(merged, export_method=export_method, template_data=template_data,
               concatenate=concatenate)


def exports_vsans_1d_nxcansas(name="NXcanSAS"):
    def inner_function(f):
        f.exporter = hdf_1d
        f.export_name = name
        return f
    return inner_function


# ---------------------------------------------------------------------------
# 2D export
# ---------------------------------------------------------------------------

def export_2d_to_nxcansas(data):
    """NXcanSAS export block for VSansDataQSpace: one SASdata group per panel."""
    from .vsansdata import short_detectors

    metadata = data.metadata or {}
    h5_item, nxentry, entry_name = _create_file_and_entry(metadata)
    i_units = _intensity_units(metadata)

    panels = []
    for sn in short_detectors:
        det = data.detectors.get("detector_%s" % sn, None)
        if det is None or "Qx" not in det:
            continue
        panels.append(panel_geometry(sn, det))

        group_name = "sasdata_%s" % sn
        if "default" not in nxentry.attrs:
            nxentry.attrs["default"] = group_name
        datagroup = nxentry.create_group(group_name)
        datagroup.attrs.update({
            "NX_class": "NXdata",
            "canSAS_class": "SASdata",
            "signal": "I",
            "I_axes": "Qx,Qy",
            "Q_indices": [0, 1],
            "detector": "sasdetector_%s" % sn,
        })
        udata = det["data"]
        datagroup["I"] = np.asarray(udata.x, dtype=float)
        datagroup["I"].attrs["units"] = i_units
        datagroup["I"].attrs["uncertainties"] = "Idev"
        datagroup["Idev"] = np.sqrt(np.asarray(udata.variance, dtype=float))
        datagroup["Idev"].attrs["units"] = i_units
        for qn in ("Qx", "Qy", "Qz"):
            if qn in det:
                datagroup[qn] = np.asarray(det[qn], dtype=float)
                datagroup[qn].attrs["units"] = Q_UNITS
        for qn in ("Qx", "Qy"):
            dqn = "d" + qn
            if dqn in det and np.shape(det[dqn]) == np.shape(det[qn]):
                datagroup[dqn] = np.asarray(det[dqn], dtype=float)
                datagroup[dqn].attrs["units"] = Q_UNITS
                datagroup[qn].attrs["resolutions"] = dqn
        if "shadow_mask" in det:
            # shadow_mask is True for pixels that are used; NXcanSAS masks are True where excluded
            datagroup["Mask"] = ~np.asarray(det["shadow_mask"], dtype=bool)
            datagroup.attrs["mask"] = "Mask"

    return _finish(h5_item, nxentry, entry_name, metadata, panels, ".vsans2d.nxs.h5")


# ---------------------------------------------------------------------------
# 2D ASCII export (gridded QxQy, NIST/SasView format)
# ---------------------------------------------------------------------------

#: Number of Qx and Qy bins in the gridded 2D ASCII export.
GRID_POINTS = 128


def _num(metadata, key, default=0.0, scale=1.0):
    """Numeric metadata value (scaled), or *default* if missing or not a number."""
    value = metadata.get(key, None)
    if not _is_number(value):
        return default
    return float(np.ravel(_clean(value))[0]) * scale


def grid_qspace(data, num_points=GRID_POINTS):
    """
    Grid all detector panels of a VSansDataQSpace onto a single uniform
    *num_points* x *num_points* Qx, Qy matrix by binning the pixels.

    Pixels are excluded if they are masked by ``shadow_mask`` (True = valid),
    a boolean ``mask`` (True = masked) or a mask on the data, or if they are
    non-finite or have I <= 0.

    Returns a dict of flattened arrays: Qx, Qy, Qz, I, dI and valid (bool),
    plus the list of panel names that contributed.
    """
    from .vsansdata import short_detectors

    qx_all, qy_all, qz_all, i_all, var_all, panels = [], [], [], [], [], []
    for sn in short_detectors:
        det = data.detectors.get("detector_%s" % sn, None)
        if det is None or "data" not in det or "Qx" not in det or "Qy" not in det:
            continue

        qx = np.asarray(det["Qx"]).ravel("C")
        qy = np.asarray(det["Qy"]).ravel("C")
        qz = np.asarray(det["Qz"]).ravel("C") if "Qz" in det else np.zeros_like(qx)
        intensity = np.asarray(det["data"].x).ravel("C")
        variance = np.asarray(det["data"].variance).ravel("C")

        if det.get("shadow_mask", None) is not None:
            valid = np.asarray(det["shadow_mask"]).astype(bool).ravel("C")
        elif det.get("mask", None) is not None:
            valid = ~np.asarray(det["mask"]).astype(bool).ravel("C")
        else:
            valid = np.ones_like(intensity, dtype=bool)
        if getattr(det["data"], "mask", None) is not None:
            valid &= ~np.asarray(det["data"].mask).astype(bool).ravel("C")
        valid &= (intensity > 0.0) & np.isfinite(intensity) & np.isfinite(qx) & np.isfinite(qy)

        if np.any(valid):
            panels.append(sn)
        qx_all.append(qx[valid])
        qy_all.append(qy[valid])
        qz_all.append(qz[valid])
        i_all.append(intensity[valid])
        var_all.append(variance[valid])

    if not panels:
        raise ValueError("No valid unmasked detector data found to export.")

    qx_pts, qy_pts, qz_pts, i_pts, var_pts = (
        np.concatenate(v) for v in (qx_all, qy_all, qz_all, i_all, var_all))

    qx_min, qx_max = np.nanmin(qx_pts), np.nanmax(qx_pts)
    qy_min, qy_max = np.nanmin(qy_pts), np.nanmax(qy_pts)
    dqx = (qx_max - qx_min) / num_points
    dqy = (qy_max - qy_min) / num_points
    if not (dqx > 0 and dqy > 0):
        raise ValueError("Q grid has zero width; check detector Qx/Qy arrays.")

    ix = np.clip(np.floor((qx_pts - qx_min) / dqx).astype(int), 0, num_points - 1)
    iy = np.clip(np.floor((qy_pts - qy_min) / dqy).astype(int), 0, num_points - 1)
    flat = ix * num_points + iy
    total = num_points * num_points

    counts = np.bincount(flat, minlength=total)
    i_sum = np.bincount(flat, weights=i_pts, minlength=total)
    var_sum = np.bincount(flat, weights=var_pts, minlength=total)
    qz_sum = np.bincount(flat, weights=qz_pts, minlength=total)

    grid_i = np.zeros(total)
    grid_di = np.zeros(total)
    grid_qz = np.zeros(total)
    filled = counts > 0
    grid_i[filled] = i_sum[filled] / counts[filled]
    grid_di[filled] = np.sqrt(np.maximum(0.0, var_sum[filled])) / counts[filled]
    grid_qz[filled] = qz_sum[filled] / counts[filled]

    qx_centers = qx_min + (np.arange(num_points) + 0.5) * dqx
    qy_centers = qy_min + (np.arange(num_points) + 0.5) * dqy
    grid_qx, grid_qy = np.meshgrid(qx_centers, qy_centers, indexing="ij")

    valid = filled & (grid_i > 0.0) & np.isfinite(grid_i) & np.isfinite(grid_di)
    grid_i[~valid] = 0.0
    grid_di[~valid] = 0.0
    grid_qz[~valid] = 0.0

    return {
        "Qx": grid_qx.ravel("C"), "Qy": grid_qy.ravel("C"), "Qz": grid_qz,
        "I": grid_i, "dI": grid_di, "valid": valid, "panels": panels,
        "dQx": dqx, "dQy": dqy,
    }


def export_2d_to_ascii(data, num_points=GRID_POINTS):
    """
    Text export block for VSansDataQSpace: all panels gridded onto one QxQy
    matrix, written in the NIST 2D ASCII (QxQy_ASCII) format read by SasView.

    Columns: Qx - Qy - I(Qx,Qy) - err(I) - Qz - SigmaQ_parall - SigmaQ_perp -
    fSubS(beam stop shadow) - Mask. The Q resolution columns are written as 0.
    """
    from reductus.dataflow.lib import iso8601

    metadata = data.metadata or {}
    grid = grid_qspace(data, num_points=num_points)
    ids = name_and_entry(metadata)
    created = iso8601.now()

    # Header values come from the measurement metadata (VSANS lengths are in cm)
    panels = [panel_geometry(sn, data.detectors["detector_%s" % sn]) for sn in grid["panels"]]
    sdd = _num(metadata, "m_det.dis", default=None)
    if sdd is None:
        sdd = float(panels[0]["SDD"]["value"]) if panels and "SDD" in panels[0] else 0.0
    filename = str(_s(metadata.get("run.filename", None) or ids["name"]))
    title = str(_s(metadata.get("sample.labl", None) or metadata.get("sample.name", None) or "VSANS 2D Grid"))

    header = [
        "FILE: %s   CREATED: %s" % (filename, created),
        "LABEL: %s" % title,
        "MON CNT    LAMBDA (A)   DET_OFF(cm)   DET_DIST(cm)   TRANS   THICK(cm)",
        "%g   %g   %g   %g   %g   %g" % (
            _num(metadata, "run.moncnt"), _num(metadata, "resolution.lmda"), 0.0, sdd,
            _num(metadata, "sample.trans", default=1.0), _num(metadata, "sample.thk")),
        "BCENT(X,Y)(cm)   A1(mm)   A2(mm)   A1A2DIST(m)   DL/L   BSTOP(mm)",
        "%g   %g   %g   %g   %g   %g   %g" % (
            0.0, 0.0,  # the grid is in Q, centred on the beam
            _num(metadata, "resolution.ap1", scale=10.0), _num(metadata, "resolution.ap2", scale=10.0),
            _num(metadata, "resolution.ap12dis", scale=0.01), _num(metadata, "resolution.dlmda"), 0.0),
        "SAM: %s" % filename,
        "BGD: none",
        "EMP: none",
        "DIV: none",
        "MASK: none",
        "ABS Parameters (3-6): TSTAND=1;DSTAND=1;IZERO=1;XSECT=1;SDEV=1;",
        "Average Choices: AVTYPE=QxQy_ASCII;SAVE=Yes;NAME=Auto;PLOT=Yes;BINTYPE=F1-M1-B;",
        "Collimation type: pinhole",
        "Panel=%s" % ",".join(grid["panels"]),
        "NumXPixels=%d" % num_points,
        "XPixelSize_mm=0",  # not meaningful for data gridded in Q
        "NumYPixels=%d" % num_points,
        "YPixelSize_mm=0",
        "Duration (s)=%g" % _num(metadata, "run.rtime"),
        "Grid spacing (1/A): dQx=%.6e dQy=%.6e" % (grid["dQx"], grid["dQy"]),
        "Intensity units: %s" % _intensity_units(metadata),
        "reserved for future file definition changes",
        "reserved for future file definition changes",
        "reserved for future file definition changes",
        "reserved for future file definition changes",
        "*** Data written from reductus ***",
        "Data columns are Qx - Qy - I(Qx,Qy) - err(I) - Qz - SigmaQ_parall - SigmaQ_perp - fSubS(beam stop shadow) - Mask",
        "The 2D error need to be checked",
        "ASCII data created %s" % created,
        "",
    ]

    valid = grid["valid"]
    zeros = np.zeros_like(grid["I"])
    columns = np.column_stack((
        grid["Qx"], grid["Qy"], grid["I"], grid["dI"], grid["Qz"],
        zeros, zeros, valid.astype(float), (~valid).astype(int),
    ))
    with io.StringIO() as fid:
        fid.write("\n".join(header) + "\n")  # blank line before the data, as in the NIST format
        np.savetxt(fid, columns, delimiter="\t",
                   fmt=["%.8e", "%.8e", "%.8e", "%.8e", "%.8e", "%.8e", "%.8e", "%.1f", "%d"])
        value = fid.getvalue()

    return {**ids, "file_suffix": ".vsans2d.dat", "value": value}
