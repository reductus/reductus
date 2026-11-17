"""Tests for the rectangle / circle / free-form region masks (SANS and VSANS)."""
import numpy as np
import pytest

from reductus.dataflow.lib.regions import (
    keep_mask, pixel_centers, region_mask, validate_region, validate_regions)


def grid(n=10):
    # integer pixel centers 0..n-1, indexed [ix, iy]
    return np.meshgrid(np.arange(n, dtype=float), np.arange(n, dtype=float), indexing="ij")


def test_rectangle_inclusive_edges():
    x, y = grid()
    hit = region_mask(x, y, [dict(type="rectangle", xmin=2, xmax=4, ymin=1, ymax=3)])
    assert hit.sum() == 3 * 3
    assert hit[2, 1] and hit[4, 3] and not hit[5, 3]


def test_rectangle_corners_in_either_order():
    x, y = grid()
    a = region_mask(x, y, [dict(type="rectangle", xmin=2, xmax=4, ymin=1, ymax=3)])
    b = region_mask(x, y, [dict(type="rectangle", xmin=4, xmax=2, ymin=3, ymax=1)])
    assert np.array_equal(a, b)


def test_circle():
    x, y = grid(11)
    hit = region_mask(x, y, [dict(type="circle", cx=5, cy=5, r=2)])
    # integer points with dx^2 + dy^2 <= 4: the 13-point disc
    assert hit.sum() == 13
    assert hit[5, 5] and hit[7, 5] and not hit[7, 7]


def test_circle_zero_radius_hits_only_exact_center():
    x, y = grid()
    assert region_mask(x, y, [dict(type="circle", cx=3, cy=3, r=0)]).sum() == 1


def test_polygon_triangle_matches_hand_count():
    x, y = grid()
    tri = dict(type="polygon", points=[[0.5, 0.5], [6.5, 0.5], [0.5, 6.5]])
    hit = region_mask(x, y, [tri])
    # points with x>=1, y>=1 and x + y <= 6
    expected = (x >= 1) & (y >= 1) & (x + y <= 6)
    assert np.array_equal(hit, expected)


def test_polygon_concave_excludes_notch():
    x, y = grid()
    # "U" shape: the notch between the arms must not be masked
    u = dict(type="polygon", points=[[0.5, 0.5], [8.5, 0.5], [8.5, 8.5], [6.5, 8.5],
                                     [6.5, 2.5], [2.5, 2.5], [2.5, 8.5], [0.5, 8.5]])
    hit = region_mask(x, y, [u])
    assert hit[1, 5] and hit[7, 5] and hit[4, 1]
    assert not hit[4, 5]


def test_polygon_orientation_does_not_matter():
    x, y = grid()
    pts = [[0.5, 0.5], [6.5, 0.5], [0.5, 6.5]]
    a = region_mask(x, y, [dict(type="polygon", points=pts)])
    b = region_mask(x, y, [dict(type="polygon", points=pts[::-1])])
    assert np.array_equal(a, b)


def test_multiple_regions_are_unioned_and_keep_is_complement():
    x, y = grid()
    regions = [dict(type="rectangle", xmin=0, xmax=1, ymin=0, ymax=1),
               dict(type="circle", cx=8, cy=8, r=1)]
    hit = region_mask(x, y, regions)
    assert hit.sum() == 4 + 5
    assert np.array_equal(keep_mask(x, y, regions), ~hit)


def test_no_regions_masks_nothing():
    x, y = grid()
    assert not region_mask(x, y, None).any()
    assert not region_mask(x, y, []).any()


@pytest.mark.parametrize("bad", [
    "circle",
    {"type": "star"},
    {"type": "rectangle", "xmin": 0, "xmax": 1, "ymin": 0},
    {"type": "rectangle", "xmin": 0, "xmax": float("nan"), "ymin": 0, "ymax": 1},
    {"type": "rectangle", "xmin": "0", "xmax": 1, "ymin": 0, "ymax": 1},
    {"type": "circle", "cx": 0, "cy": 0, "r": -1},
    {"type": "circle", "cx": 0, "cy": 0},
    {"type": "polygon", "points": [[0, 0], [1, 1]]},
    {"type": "polygon", "points": [[0, 0], [1, 1], [1]]},
    {"type": "polygon", "points": "abc"},
])
def test_invalid_regions_rejected(bad):
    with pytest.raises(ValueError):
        validate_region(bad)


def test_validate_regions_requires_list():
    with pytest.raises(ValueError):
        validate_regions({"type": "circle", "cx": 0, "cy": 0, "r": 1})


def test_pixel_centers_match_plot_extent():
    x, y = pixel_centers((4, 2), 0.0, 8.0, 0.0, 4.0)
    assert np.allclose(x[:, 0], [1, 3, 5, 7])
    assert np.allclose(y[0, :], [1, 3])


def _sans_data(n=16):
    from reductus.sansred.sansdata import SansData
    meta = {"entry": "entry", "run.filename": "x", "sample.labl": "y"}
    return SansData(data=np.ones((n, n)), metadata=meta)


def test_sans_mask_step_masks_pixels_and_keeps_original():
    from reductus.sansred import steps
    data = _sans_data()
    # no Q yet: plot axes are 0..128 over 16 pixels, i.e. 8 plot units per pixel
    regions = [dict(type="circle", cx=4, cy=4, r=3)]
    out = steps.mask_2d_regions.__wrapped__([data], regions) \
        if hasattr(steps.mask_2d_regions, "__wrapped__") else steps.mask_2d_regions([data], regions)
    masked = out[0]
    assert masked.mask.shape == (16, 16)
    assert not masked.mask[0, 0]          # pixel center (4, 4) is inside
    assert masked.mask[8, 8]
    assert data.mask is None              # input untouched
    assert masked.data.x.sum() == data.data.x.sum()  # intensities unchanged


def test_sans_masks_accumulate():
    from reductus.sansred import steps
    data = _sans_data()
    first = steps.mask_2d_regions([data], [dict(type="rectangle", xmin=0, xmax=8, ymin=0, ymax=128)])
    second = steps.mask_2d_regions(first, [dict(type="rectangle", xmin=0, xmax=128, ymin=0, ymax=8)])
    m = second[0].mask
    assert not m[0, 5] and not m[5, 0] and m[5, 5]


def test_sans_copy_preserves_mask():
    data = _sans_data()
    data.mask = np.zeros((16, 16), dtype=bool)
    copied = data.copy()
    assert copied.mask is not data.mask and not copied.mask.any()


def test_vsans_mask_step_updates_shadow_mask():
    from reductus.vsansred import steps
    from reductus.vsansred.vsansdata import VSansDataRealSpace
    from reductus.dataflow.lib.uncertainty import Uncertainty

    def panel(x0):
        x, y = np.meshgrid(x0 + np.arange(4.0), np.arange(4.0), indexing="ij")
        vals = np.ones((4, 4))
        return {"data": Uncertainty(vals, vals), "X": x, "Y": y}

    detectors = {"detector_B": panel(0.0), "detector_FR": panel(10.0)}
    detectors["detector_B"]["shadow_mask"] = np.ones((4, 4), dtype=bool)
    detectors["detector_B"]["shadow_mask"][3, 3] = False  # pre-existing mask
    data = VSansDataRealSpace(metadata={}, detectors=detectors)

    regions = [dict(type="rectangle", xmin=0, xmax=1, ymin=0, ymax=1),
               dict(type="circle", cx=11, cy=1, r=1)]
    out = steps.mask_regions_realspace(data, regions)

    b = out.detectors["detector_B"]["shadow_mask"]
    assert b.sum() == 16 - 4 - 1          # rectangle (2x2) + old mask pixel
    assert not b[3, 3]
    fr = out.detectors["detector_FR"]["shadow_mask"]
    assert fr.sum() == 16 - 5             # circle of radius 1 covers 5 pixels
    # the input was not modified (inplace=False)
    assert detectors["detector_B"]["shadow_mask"].sum() == 15
    assert "shadow_mask" not in detectors["detector_FR"]
