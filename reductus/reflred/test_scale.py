import numpy as np
import pytest

from reductus.reflred.refldata import ReflData
from reductus.reflred.steps import divide_intensity


def _scan(values, errors, normbase, units):
    data = ReflData(
        angular_resolution=np.array([0.1, 0.2]),
        normbase=normbase,
        vunits=units,
    )
    data.v = np.array(values)
    data.dv = np.array(errors)
    return data


@pytest.mark.parametrize(
    ("normbase", "units"),
    [
        ("time", "counts per second"),
        ("monitor", "counts per monitor"),
        ("none", "counts"),
    ],
)
def test_divide_intensity_reports_a_dimensionless_ratio(normbase, units):
    sample = _scan([20.0, 10.0], [2.0, 1.0], normbase, units)
    incident = _scan([40.0, 40.0], [4.0, 4.0], normbase, units)

    divided = divide_intensity(sample, incident)

    np.testing.assert_allclose(divided.v, [0.5, 0.25])
    np.testing.assert_allclose(divided.dv, np.array([0.5, 0.25]) * np.sqrt(0.02))
    assert divided.columns["v"]["units"] == "unitless"
    assert sample.columns["v"]["units"] == incident.columns["v"]["units"] == units
    np.testing.assert_array_equal(sample.v, [20.0, 10.0])
    np.testing.assert_array_equal(incident.v, [40.0, 40.0])


def test_divide_intensity_keeps_input_units_without_incident_scan():
    sample = _scan([20.0, 10.0], [2.0, 1.0], "time", "counts per second")

    unchanged = divide_intensity(sample, None)

    assert unchanged is sample
    assert unchanged.columns["v"]["units"] == "counts per second"
