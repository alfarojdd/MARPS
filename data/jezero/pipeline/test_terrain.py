import numpy as np
import pytest

import terrain


def plane(dx_per_m=0.0, dy_per_m=0.0, n=20, res=10.0):
    """Plano con pendiente hacia el este (dx) y hacia el norte (dy); fila 0 = norte."""
    x = np.arange(n) * res
    y = (n - 1 - np.arange(n)) * res
    X, Y = np.meshgrid(x, y)
    return dx_per_m * X + dy_per_m * Y


def test_slope_of_45_degree_plane():
    s = terrain.slope_deg(plane(dx_per_m=1.0), 10.0)
    assert np.allclose(s, 45.0)


def test_aspect_points_downhill():
    # sube hacia el este -> la ladera mira al oeste (270)
    assert np.allclose(terrain.aspect_deg(plane(dx_per_m=0.5), 10.0), 270.0)
    # sube hacia el norte -> mira al sur (180)
    assert np.allclose(terrain.aspect_deg(plane(dy_per_m=0.5), 10.0), 180.0)


def test_hillshade_flat_equals_sin_altitude():
    hs = terrain.hillshade(np.zeros((5, 5)), 1.0, altitude=30.0)
    assert np.allclose(hs, 0.5)


def test_tri_and_tpi_zero_on_flat_and_positive_on_peak():
    flat = np.zeros((9, 9))
    assert np.allclose(terrain.tri(flat), 0)
    peak = flat.copy(); peak[4, 4] = 8.0
    assert terrain.tri(peak)[4, 4] == pytest.approx(8.0)
    assert terrain.tpi(peak, 1)[4, 4] == pytest.approx(8.0 - 8.0 / 9.0)


def test_box_mean_ignores_nan():
    a = np.ones((5, 5)); a[2, 3] = np.nan
    m = terrain._box_mean(a, 1)
    assert m.shape == a.shape
    assert m[2, 2] == pytest.approx(1.0)
    assert np.isnan(m[2, 3])


def test_block_reduce():
    a = np.arange(16, dtype=float).reshape(4, 4)
    assert terrain.block_reduce(a, 2, "max").tolist() == [[5, 7], [13, 15]]
    assert terrain.block_reduce(a, 2, "mean")[0, 0] == pytest.approx(2.5)


def test_insolation_flat_is_one_and_sun_facing_slope_gets_more():
    flat = terrain.mean_direct_insolation(np.zeros((1, 1)), np.zeros((1, 1)), 18.4)
    assert flat[0, 0] == pytest.approx(1.0)
    south = terrain.mean_direct_insolation(np.full((1, 1), 20.0), np.full((1, 1), 180.0), 18.4)
    north = terrain.mean_direct_insolation(np.full((1, 1), 20.0), np.full((1, 1), 0.0), 18.4)
    assert south[0, 0] > 1.0 > north[0, 0]
