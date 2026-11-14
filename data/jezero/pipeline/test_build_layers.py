import numpy as np

import build_layers as bl


def test_classify_crism_tolerates_compression_noise():
    rgb = np.array([[[255, 152, 0, 255, 1, 120]],
                    [[0, 76, 154, 255, 0, 200]],
                    [[0, 68, 0, 255, 0, 40]]], np.uint8)
    cls, conf = bl.classify_crism(rgb)
    # olivino alta, olivino+esmectita media, carbonato media, fuera, sin identificar, ambiguo
    assert cls[0].tolist() == [1, 4, 2, -1, 0, 0]
    assert conf[0].tolist() == [2, 1, 1, -1, 0, 0]


def test_grid_matches_agreed_bbox():
    w, s, e, n = bl.BOUNDS
    m_per_deg = np.pi * 3396190 / 180
    assert abs(w / m_per_deg - 77.1604655) < 1e-3
    assert abs(e / m_per_deg - 77.6991776) < 1e-3
    assert abs(s / m_per_deg - 18.2110274) < 1e-3
    assert abs(n / m_per_deg - 18.7211945) < 1e-3


def test_tile_range_covers_bbox_at_each_zoom():
    import make_viewer_data as mv
    for z in range(8):
        xs, ys = mv.tile_range(z, bl.BOUNDS)
        span = mv.TILE * mv.res_at(z)
        assert xs.start == 0 and ys.start == 0
        assert mv.LEFT + len(xs) * span >= bl.BOUNDS[2] > mv.LEFT + (len(xs) - 1) * span
        assert mv.TOP - len(ys) * span <= bl.BOUNDS[1] < mv.TOP - (len(ys) - 1) * span


def test_base_stack_covers_whole_bbox():
    import pytest
    import rasterio
    path = bl.STACK / "jezero_stack_20m.tif"
    if not path.exists():
        pytest.skip("stack sin generar")
    from layers import STACK_BANDS
    required = {b["id"]: b.get("min_coverage", bl.MIN_BASE_COVERAGE) for b in STACK_BANDS}
    with rasterio.open(path) as s:
        assert (s.width, s.height) == (bl.GRID["width"], bl.GRID["height"])
        for i, name in enumerate(s.descriptions, start=1):
            assert np.isfinite(s.read(i)).mean() >= required[name], name


def test_grid_matches_ctx_dtm():
    import pytest
    import rasterio
    if not bl.CTX_DTM.exists():
        pytest.skip("DTM CTX sin descargar")
    with rasterio.open(bl.CTX_DTM) as s:
        assert tuple(s.transform)[:6] == pytest.approx(tuple(bl.GRID["transform"])[:6])
        assert (s.width, s.height) == (bl.GRID["width"], bl.GRID["height"])
        assert s.crs == bl.GRID["crs"]
