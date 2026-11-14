import json
import struct

import numpy as np
import pytest

import build_terrain3d as B


def write_grid_stl(path, z):
    """Binary STL of a grid: vertex (x=col, y=row, z)."""
    h, w = z.shape
    tris = []
    for r in range(h - 1):
        for c in range(w - 1):
            a, b = (c, r, z[r, c]), (c + 1, r, z[r, c + 1])
            d, e = (c, r + 1, z[r + 1, c]), (c + 1, r + 1, z[r + 1, c + 1])
            tris += [(a, b, d), (b, e, d)]
    with open(path, "wb") as f:
        f.write(b"\0" * 80 + struct.pack("<I", len(tris)))
        for t in tris:
            f.write(struct.pack("<3f", 0, 0, 1))
            for v in t:
                f.write(struct.pack("<3f", *v))
            f.write(b"\0\0")


def synthetic_dtm(h=120, w=130):
    y, x = np.mgrid[0:h, 0:w]
    return (-2000 + 300 * np.sin(x / 9.0) * np.cos(y / 13.0) + 2.0 * x - 1.5 * y).astype(np.float32)


def test_read_stl_heightmap_rebuilds_grid(tmp_path):
    z = np.arange(12, dtype=np.float32).reshape(3, 4)
    write_grid_stl(tmp_path / "g.stl", z)
    np.testing.assert_array_equal(B.read_stl_heightmap(tmp_path / "g.stl"), z)


def test_fit_recovers_orientation_window_and_scale():
    dtm = synthetic_dtm()
    win = (10, 110, 5, 105)  # col0, col1, row0, row1 (exclusive)
    sub = dtm[win[2]:win[3], win[0]:win[1]]
    stl = ((sub - sub.max()) / 25.0)[:, ::-1]  # arbitrary scale and a horizontal mirror
    fit = B.fit_to_dtm(stl, dtm)
    assert fit["orientation"] == "fliplr"
    assert fit["corr"] > 0.99
    for got, want in zip(fit["window"], win):
        assert abs(got - want) <= 2
    assert abs(fit["z_scale"] - 25.0) < 1.0


def test_crop_to_dtm_keeps_inside_part():
    h = np.arange(100, dtype=np.float32).reshape(10, 10)
    # window sticks out 2 columns to the left of an 8x8 DTM with 1:1 cells
    out, win = B.crop_to_dtm(h, (-2, 8, 0, 10), (8, 8))
    assert win == (0, 8, 0, 8)
    np.testing.assert_array_equal(out, h[0:8, 2:10])


def test_write_outputs_meta_and_bin(tmp_path):
    hm = np.array([[1, 2], [3, 4]], dtype=np.float32)
    meta = B.write_terrain(tmp_path, "t", hm, bounds=(0.0, 10.0, 20.0, 0.0), source="x")
    data = np.fromfile(tmp_path / "t.f32", dtype="<f4").reshape(2, 2)
    np.testing.assert_array_equal(data, hm)
    saved = json.loads((tmp_path / "t.json").read_text())
    assert saved == meta
    assert saved["width"] == 2 and saved["height"] == 2
    assert saved["bounds"] == {"left": 0.0, "top": 10.0, "right": 20.0, "bottom": 0.0}
    assert saved["min"] == 1 and saved["max"] == 4


def test_write_terrain_rejects_nan(tmp_path):
    hm = np.array([[1, np.nan], [3, 4]], dtype=np.float32)
    with pytest.raises(ValueError):
        B.write_terrain(tmp_path, "t", hm, bounds=(0.0, 10.0, 20.0, 0.0), source="x")


def test_main_creates_missing_output_dir(tmp_path, monkeypatch):
    # write_texture runs before write_terrain: the output folder must already exist
    out = tmp_path / "new" / "dir"
    seen = {}

    def fake_texture(path, bounds, max_px=4096):
        seen["exists"] = out.exists()
        return {}
    monkeypatch.setattr(B, "write_texture", fake_texture)
    monkeypatch.setattr(B, "DTM", tmp_path / "dtm.tif")
    import sys
    import rasterio
    from rasterio.transform import from_origin
    with rasterio.open(tmp_path / "dtm.tif", "w", driver="GTiff", height=4, width=4, count=1,
                       dtype="float32", transform=from_origin(0, 0, 20, 20)) as d:
        d.write(np.arange(16, dtype=np.float32).reshape(4, 4), 1)
    monkeypatch.setattr(sys, "argv", ["x", "--source", "dtm", "--dtm-width", "2", "--out", str(out)])
    B.main()
    assert seen["exists"] is True
