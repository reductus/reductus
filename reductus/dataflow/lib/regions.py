"""
Region masks for 2D detector data.

A *region* is a shape drawn on a 2D plot, in the plot's own (x, y)
coordinates.  Pixels whose centers fall inside any region are excluded from
the reduction.  Three shapes are supported, each a plain JSON-able dict:

    {"type": "rectangle", "xmin": .., "xmax": .., "ymin": .., "ymax": ..}
    {"type": "circle", "cx": .., "cy": .., "r": ..}
    {"type": "polygon", "points": [[x, y], [x, y], ...]}

The polygon covers free-form drawing: the GUI records the path that was
traced and the server tests pixel centers against it (even-odd rule, so
self-intersecting outlines behave as expected).  Edges are inclusive for
rectangles and circles.
"""
from __future__ import annotations

import numpy as np

REGION_TYPES = ("rectangle", "circle", "polygon")

# Upper bound on polygon vertices, to keep a hand-drawn path from producing
# a pathologically large configuration.
MAX_POLYGON_POINTS = 5000


def _number(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not np.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return value


def validate_region(region):
    """
    Check one region and return a normalized copy (floats, ordered limits).

    Raises ValueError if the region is malformed.
    """
    if not isinstance(region, dict):
        raise ValueError("region must be an object, got %r" % (region,))
    kind = region.get("type")
    if kind == "rectangle":
        x1 = _number("xmin", region.get("xmin"))
        x2 = _number("xmax", region.get("xmax"))
        y1 = _number("ymin", region.get("ymin"))
        y2 = _number("ymax", region.get("ymax"))
        return {"type": "rectangle",
                "xmin": min(x1, x2), "xmax": max(x1, x2),
                "ymin": min(y1, y2), "ymax": max(y1, y2)}
    elif kind == "circle":
        radius = _number("r", region.get("r"))
        if radius < 0:
            raise ValueError("circle radius must not be negative, got %r" % radius)
        return {"type": "circle",
                "cx": _number("cx", region.get("cx")),
                "cy": _number("cy", region.get("cy")),
                "r": radius}
    elif kind == "polygon":
        points = region.get("points")
        if not isinstance(points, (list, tuple)):
            raise ValueError("polygon points must be a list")
        if len(points) < 3:
            raise ValueError("polygon needs at least 3 points, got %d" % len(points))
        if len(points) > MAX_POLYGON_POINTS:
            raise ValueError("polygon has %d points; limit is %d"
                             % (len(points), MAX_POLYGON_POINTS))
        clean = []
        for p in points:
            if not isinstance(p, (list, tuple)) or len(p) != 2:
                raise ValueError("polygon point must be [x, y], got %r" % (p,))
            clean.append([_number("x", p[0]), _number("y", p[1])])
        return {"type": "polygon", "points": clean}
    raise ValueError("region type must be one of %s, got %r"
                     % (", ".join(REGION_TYPES), kind))


def validate_regions(regions):
    """Validate a list of regions (None means no regions)."""
    if regions is None:
        return []
    if not isinstance(regions, (list, tuple)):
        raise ValueError("regions must be a list")
    return [validate_region(r) for r in regions]


def _in_polygon(x, y, points):
    """Vectorized even-odd point-in-polygon test (ray cast toward +x)."""
    px = np.asarray([p[0] for p in points], dtype=float)
    py = np.asarray([p[1] for p in points], dtype=float)
    px_next = np.roll(px, -1)
    py_next = np.roll(py, -1)
    inside = np.zeros(x.shape, dtype=bool)
    for x1, y1, x2, y2 in zip(px, py, px_next, py_next):
        if y1 == y2:
            continue  # horizontal edges never cross a horizontal ray
        crosses = (y1 > y) != (y2 > y)
        # x position where the edge crosses the ray's height
        x_cross = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
        inside ^= crosses & (x < x_cross)
    return inside


def region_mask(x, y, regions):
    """
    Return a boolean array, True where (x, y) lies inside any region.

    *x* and *y* are arrays of pixel-center coordinates with the same shape.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.shape != y.shape:
        raise ValueError("x and y must have the same shape")
    hit = np.zeros(x.shape, dtype=bool)
    for r in validate_regions(regions):
        if r["type"] == "rectangle":
            hit |= ((x >= r["xmin"]) & (x <= r["xmax"])
                    & (y >= r["ymin"]) & (y <= r["ymax"]))
        elif r["type"] == "circle":
            hit |= (x - r["cx"])**2 + (y - r["cy"])**2 <= r["r"]**2
        else:
            hit |= _in_polygon(x, y, r["points"])
    return hit


def keep_mask(x, y, regions):
    """Boolean array, True for pixels to keep (outside every region)."""
    return ~region_mask(x, y, regions)


def pixel_centers(shape, xmin, xmax, ymin, ymax):
    """
    Coordinates of pixel centers for an array of *shape* = (nx, ny) that is
    drawn spanning [xmin, xmax] x [ymin, ymax], as the 2D plotter does.
    Returns (x, y) arrays of that shape, indexed [ix, iy].
    """
    nx, ny = shape
    xs = xmin + (np.arange(nx) + 0.5) * (xmax - xmin) / nx
    ys = ymin + (np.arange(ny) + 0.5) * (ymax - ymin) / ny
    return np.meshgrid(xs, ys, indexing="ij")
