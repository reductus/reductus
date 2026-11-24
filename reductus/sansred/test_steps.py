"""Regression tests for SANS calibration loaders."""

import numpy as np
import pytest

from reductus.sansred.sansdata import RawSANSData, SansData
from reductus.sansred.steps import (
    LoadDIV,
    LoadRawSANS,
    LoadSANS,
    correct_detector_sensitivity,
)


@pytest.fixture
def div_file(tmp_path):
    # Synthetic VAX REAL*4 sensitivity map, including the record separators.
    values = (1 + np.arange(128 * 128, dtype=np.float32) / 16384).reshape(128, 128)
    ieee = values.astype('<f4').view(np.uint8).reshape(-1, 4)
    vax = ieee[:, [2, 3, 0, 1]].copy()
    vax[:, 1] += 1
    records = []
    for start in range(0, 16 * 1021, 1021):
        records.extend((vax[start:start + 511].tobytes(), b'\0\0',
                        vax[start + 511:start + 1021].tobytes(), b'\0\0'))
    records.append(vax[16 * 1021:].tobytes())
    path = tmp_path / 'sensitivity.DIV'
    path.write_bytes(b'\0' * 516 + b''.join(records))
    return {'source': 'local', 'path': path.as_posix()}, values.T


@pytest.mark.parametrize('filelist', [None, []])
def test_load_div_without_files(filelist):
    assert LoadDIV(filelist) == []


@pytest.mark.parametrize('variance', [0.0001, 0.0025])
def test_load_div_for_correction(div_file, variance):
    info, expected = div_file
    loaded = LoadDIV([info, info], variance=variance)
    assert len(loaded) == 2
    for sensitivity in loaded:
        assert isinstance(sensitivity, SansData)
        np.testing.assert_array_equal(sensitivity.data.x, expected)
        np.testing.assert_allclose(sensitivity.data.variance, expected * variance)
        assert sensitivity.metadata['analysis.intent'] == 'DIV'
        assert sensitivity.metadata['run.filename'] == 'sensitivity.DIV'
        assert sensitivity.get_plottable()['type'] == '2d'
        sample = SansData(np.full(expected.shape, 100.0))
        corrected = correct_detector_sensitivity(sample, sensitivity)
        np.testing.assert_allclose(corrected.data.x, 100 / expected)
        np.testing.assert_array_equal(sample.data.x, 100)
    assert loaded[0] is not loaded[1]


def test_load_raw_div_is_flat(div_file):
    info, expected = div_file
    loaded = LoadRawSANS([info, info])
    assert len(loaded) == 2
    for raw in loaded:
        assert isinstance(raw, RawSANSData)
        np.testing.assert_array_equal(raw.detectors['detector']['data']['value'].x, expected)
        assert raw.metadata['analysis.filepurpose'] == 'Sensitivity'


@pytest.mark.parametrize('flip,transpose', [(False, False), (False, True), (True, False), (True, True)])
def test_load_sans_div_orientation(div_file, flip, transpose):
    info, expected = div_file
    loaded = LoadSANS([info], flip=flip, transpose=transpose)
    assert len(loaded) == 1
    assert isinstance(loaded[0], SansData)
    if flip:
        expected = np.fliplr(expected)
    if transpose:
        expected = expected.T
    np.testing.assert_array_equal(loaded[0].data.x, expected)
    np.testing.assert_allclose(loaded[0].data.variance, expected * 0.0001)


@pytest.fixture
def nexus_file(tmp_path):
    import h5py

    path = tmp_path / 'sample.nxs'
    values = np.arange(1, 7, dtype=float).reshape(2, 3)
    with h5py.File(path, 'w') as handle:
        entry = handle.create_group('entry')
        entry['instrument/detector/data'] = values
        entry['DAS_logs/sample/description'] = np.array([b'sample'])
        entry['DAS_logs/configuration/key'] = np.array([b'config'])
        entry['DAS_logs/trajectoryData/fileName'] = np.array([b'sample.nxs'])
    return {'source': 'local', 'path': path.as_posix()}, values


@pytest.mark.parametrize('flip,transpose', [(False, False), (False, True), (True, False), (True, True)])
def test_load_sans_nexus_orientation(nexus_file, flip, transpose):
    info, expected = nexus_file
    loaded = LoadSANS([info], flip=flip, transpose=transpose)
    assert len(loaded) == 1
    if flip:
        expected = np.fliplr(expected)
    if transpose:
        expected = expected.T
    np.testing.assert_array_equal(loaded[0].data.x, expected)
    np.testing.assert_array_equal(loaded[0].data.variance, expected)


def test_load_mixed_sans_files(div_file, nexus_file):
    div_info, div_values = div_file
    nexus_info, nexus_values = nexus_file
    loaded = LoadSANS([div_info, nexus_info, div_info])
    assert len(loaded) == 3
    for item, expected in zip(loaded, [div_values, nexus_values, div_values]):
        assert isinstance(item, SansData)
        np.testing.assert_array_equal(item.data.x, expected)


def _border_mask():
    mask = np.zeros((128, 128), dtype=np.uint8)
    mask[:3] = mask[-3:] = 1
    mask[:, :3] = mask[:, -3:] = 1
    return mask


@pytest.fixture
def vax_mask_file(tmp_path):
    mask = _border_mask()
    path = tmp_path / 'DEFAULT.MASK'
    path.write_bytes(b'\x7f\x00\x7f\x00' + mask.tobytes() + b'\0' * 508)
    return {'source': 'local', 'path': path.as_posix()}, mask


@pytest.fixture
def nexus_mask_file(tmp_path):
    import h5py

    mask = _border_mask()
    path = tmp_path / 'DefaultNexus_SANS_MASK_file.MASK.h5'
    with h5py.File(path, 'w') as handle:
        entry = handle.create_group('entry')
        entry['title'] = 'This is a MASK file for NGB 10m SANS: SANS_MASK'
        entry['instrument/detector/data'] = mask.astype('int32')
    return {'source': 'local', 'path': path.as_posix()}, mask


@pytest.mark.parametrize('fixture_name', ['vax_mask_file', 'nexus_mask_file'])
def test_load_raw_mask(request, fixture_name):
    info, expected = request.getfixturevalue(fixture_name)
    loaded = LoadRawSANS([info])
    assert len(loaded) == 1
    raw = loaded[0]
    assert isinstance(raw, RawSANSData)
    np.testing.assert_array_equal(raw.detectors['detector']['data']['value'].x, expected)
    # These fields determine how the file is listed in the data tree
    assert raw.metadata['run.configuration'] == 'MASK'
    assert raw.metadata['analysis.intent'] == 'MASK'
    assert raw.metadata['sample.name'] == info['path'].rsplit('/', 1)[-1]


@pytest.mark.parametrize('fixture_name', ['vax_mask_file', 'nexus_mask_file'])
def test_mask_is_viewable(request, fixture_name):
    info, expected = request.getfixturevalue(fixture_name)
    loaded = LoadSANS([info])
    assert len(loaded) == 1
    assert loaded[0].get_plottable()['type'] == '2d'
    np.testing.assert_array_equal(loaded[0].data.x, expected)
