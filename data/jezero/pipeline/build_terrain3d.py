"""Convert a relief (Mars Trek STL or the CTX DTM) into the files used by the 3D map view.

    python build_terrain3d.py                  # Mars Trek STL -> platform/viewer/data/terrain3d/
    python build_terrain3d.py --source dtm     # same format from layers20m/elev_ctx.tif

Output (in --out, default platform/viewer/data/terrain3d/; ignored by Git):
  <name>.f32      heights in metres, float32 little-endian, row 0 = north, column 0 = west
  <name>.json     size, equirectangular bounds (m, sphere R = 3 396 190 m) and the fit
  <name>_ctx.jpg  CTX orthomosaic cropped to the same bounds (texture)

The Mars Trek STL has no georeference: it is a 400 x 400 vertex grid with X/Y as indices and
relative Z. We georeference it by searching the orientation, window and vertical scale that
best correlate with the CTX DTM (elev_ctx.tif), then crop it to the part inside the bbox.
"""
import argparse
import json
from pathlib import Path

import numpy as np

DATA = Path(__file__).resolve().parents[1]            # data/jezero
ROOT = Path(__file__).resolve().parents[3]            # repository root
DTM = DATA / "layers20m/elev_ctx.tif"
ORTHO = DATA / "raw/JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0.tif"
STL = DATA / "raw/trekSTL.stl"
OUT = ROOT / "platform/viewer/data/terrain3d"

ORIENTATIONS = {
    "id": lambda a: a,
    "flipud": lambda a: a[::-1],
    "fliplr": lambda a: a[:, ::-1],
    "rot180": lambda a: a[::-1, ::-1],
    "T": lambda a: a.T,
    "T_flipud": lambda a: a.T[::-1],
    "T_fliplr": lambda a: a.T[:, ::-1],
    "T_rot180": lambda a: a.T[::-1, ::-1],
}


def read_stl_heightmap(path):
    """Rebuild the grid Z[y, x] of a binary STL whose vertices sit on integer X/Y (Mars Trek export)."""
    raw = Path(path).read_bytes()
    n = int(np.frombuffer(raw[80:84], "<u4")[0])
    tri = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    v = np.frombuffer(raw[84:84 + n * tri.itemsize], dtype=tri)["v"].reshape(-1, 3)
    xi, yi = np.rint(v[:, 0]).astype(int), np.rint(v[:, 1]).astype(int)
    if not (np.allclose(v[:, 0], xi) and np.allclose(v[:, 1], yi)):
        raise ValueError("The STL is not a regular grid with integer X/Y")
    xi -= xi.min()
    yi -= yi.min()
    z = np.full((yi.max() + 1, xi.max() + 1), np.nan, np.float32)
    z[yi, xi] = v[:, 2]
    if np.isnan(z).any():
        raise ValueError("The STL grid has holes")
    return z


def _sample(dtm, window, shape):
    """Sample the DTM (nearest neighbour) at the centres of a `shape` grid covering `window`."""
    c0, c1, r0, r1 = window
    h, w = shape
    cols = np.floor(c0 + (np.arange(w) + 0.5) * (c1 - c0) / w).astype(int)
    rows = np.floor(r0 + (np.arange(h) + 0.5) * (r1 - r0) / h).astype(int)
    out = np.full(shape, np.nan, np.float64)
    ok_c = (cols >= 0) & (cols < dtm.shape[1])
    ok_r = (rows >= 0) & (rows < dtm.shape[0])
    out[np.ix_(ok_r, ok_c)] = dtm[np.ix_(rows[ok_r], cols[ok_c])]
    return out


def _corr(a, b):
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 0.5 * a.size:
        return -1.0
    return float(np.corrcoef(a[m], b[m])[0, 1])


def fit_to_dtm(stl, dtm):
    """Best orientation, window (col0, col1, row0, row1 in DTM pixels) and Z scale for the STL grid."""
    full = (0, dtm.shape[1], 0, dtm.shape[0])
    best = None
    for name, f in ORIENTATIONS.items():
        a = f(stl)
        c = _corr(a, _sample(dtm, full, a.shape))
        if best is None or c > best[0]:
            best = (c, name)
    corr, name = best
    grid = ORIENTATIONS[name](stl)
    win = list(full)
    step = max(dtm.shape) // 16
    while step >= 1:
        improved = True
        while improved:
            improved = False
            for k in range(4):
                for d in (-step, step):
                    cand = win.copy()
                    cand[k] += d
                    if cand[1] - cand[0] < 8 or cand[3] - cand[2] < 8:
                        continue
                    c = _corr(grid, _sample(dtm, cand, grid.shape))
                    if c > corr:
                        corr, win, improved = c, cand, True
        step //= 2
    ref = _sample(dtm, win, grid.shape)
    m = np.isfinite(ref)
    scale, offset = np.polyfit(grid[m], ref[m], 1)
    resid = ref[m] - (scale * grid[m] + offset)
    return {"orientation": name, "corr": corr, "window": tuple(int(v) for v in win),
            "z_scale": float(scale), "z_offset": float(offset), "rmse_m": float(np.sqrt(np.mean(resid ** 2))),
            "grid": grid}


def crop_to_dtm(grid, window, dtm_shape):
    """Crop the grid to the cells whose centre falls inside the DTM. Returns (grid, new window)."""
    c0, c1, r0, r1 = window
    h, w = grid.shape
    px, py = (c1 - c0) / w, (r1 - r0) / h
    cc = c0 + (np.arange(w) + 0.5) * px
    rc = r0 + (np.arange(h) + 0.5) * py
    ic = np.flatnonzero((cc >= 0) & (cc < dtm_shape[1]))
    ir = np.flatnonzero((rc >= 0) & (rc < dtm_shape[0]))
    out = grid[ir[0]:ir[-1] + 1, ic[0]:ic[-1] + 1]
    win = (c0 + ic[0] * px, c0 + (ic[-1] + 1) * px, r0 + ir[0] * py, r0 + (ir[-1] + 1) * py)
    return out, tuple(int(v) if float(v).is_integer() else round(float(v), 6) for v in win)


def write_terrain(out_dir, name, heights, bounds, source, extra=None):
    """Write <name>.f32 and <name>.json. bounds = (left, top, right, bottom) in equirectangular metres."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    heights = np.ascontiguousarray(heights, dtype="<f4")
    if not np.isfinite(heights).all():
        raise ValueError("The heightmap has holes (NaN/inf); fill them before writing")
    heights.tofile(out_dir / f"{name}.f32")
    left, top, right, bottom = bounds
    meta = {"width": int(heights.shape[1]), "height": int(heights.shape[0]),
            "bounds": {"left": left, "top": top, "right": right, "bottom": bottom},
            "radius": 3396190.0, "units": "m", "min": float(heights.min()), "max": float(heights.max()),
            "heights": f"{name}.f32", "source": source}
    if extra:
        meta.update(extra)
    (out_dir / f"{name}.json").write_text(json.dumps(meta, indent=1, allow_nan=False))
    return meta


def _window_bounds(transform, window):
    c0, c1, r0, r1 = window
    left, top = transform * (c0, r0)
    right, bottom = transform * (c1, r1)
    return float(left), float(top), float(right), float(bottom)


def write_texture(path, bounds, max_px=4096, ortho=ORTHO):
    """Crop the CTX orthomosaic to `bounds` and save it as JPEG (stretched 2-98 %)."""
    import rasterio
    from PIL import Image
    from rasterio.enums import Resampling
    from rasterio.windows import from_bounds

    left, top, right, bottom = bounds
    aspect = (right - left) / (top - bottom)
    w, h = (max_px, round(max_px / aspect)) if aspect >= 1 else (round(max_px * aspect), max_px)
    with rasterio.open(ortho) as src:
        win = from_bounds(left, bottom, right, top, src.transform)
        a = src.read(1, window=win, out_shape=(h, w), resampling=Resampling.average,
                     boundless=True, masked=True).astype(np.float64)
    vals = a.compressed()
    lo, hi = np.percentile(vals, [2, 98])
    img = np.clip((a.filled(lo) - lo) / (hi - lo), 0, 1)
    Image.fromarray((img * 255).astype(np.uint8)).save(path, quality=88)
    return {"texture": Path(path).name, "texture_size": [w, h]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--source", choices=["stl", "dtm"], default="stl")
    ap.add_argument("--stl", type=Path, default=STL)
    ap.add_argument("--dtm", type=Path, default=DTM, help="georeferenced elevation GeoTIFF")
    ap.add_argument("--ortho", type=Path, default=ORTHO, help="CTX orthoimage GeoTIFF for the texture")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--dtm-width", type=int, default=800, help="grid width when using --source dtm")
    ap.add_argument("--texture-px", type=int, default=4096)
    args = ap.parse_args()

    import rasterio
    from rasterio.enums import Resampling

    with rasterio.open(args.dtm) as src:
        dtm = src.read(1).astype(np.float64)
        transform = src.transform
        dtm[~np.isfinite(dtm)] = np.nan

    if args.source == "stl":
        name = "terrain_stl"
        fit = fit_to_dtm(read_stl_heightmap(args.stl), dtm)
        grid, win = crop_to_dtm(fit["grid"], fit["window"], dtm.shape)
        heights = fit["z_scale"] * grid + fit["z_offset"]
        extra = {"fit": {k: fit[k] for k in ("orientation", "corr", "z_scale", "z_offset", "rmse_m")},
                 "fit_window_px": list(fit["window"]), "crop_window_px": list(win)}
        print(f"STL: orientation {fit['orientation']}, r = {fit['corr']:.3f}, "
              f"Z scale {fit['z_scale']:.2f} m/unit, RMSE {fit['rmse_m']:.0f} m, window {win}")
    else:
        name = "terrain_dtm"
        h = round(args.dtm_width * dtm.shape[0] / dtm.shape[1])
        with rasterio.open(args.dtm) as src:
            heights = src.read(1, out_shape=(h, args.dtm_width), resampling=Resampling.average, masked=True)
        heights = heights.astype(np.float32).filled(np.nan)
        heights[~np.isfinite(heights)] = np.nanmin(heights)  # gaps: lowest value, no invented relief
        win, extra = (0, dtm.shape[1], 0, dtm.shape[0]), {}

    bounds = _window_bounds(transform, win)
    args.out.mkdir(parents=True, exist_ok=True)
    extra.update(write_texture(args.out / f"{name}_ctx.jpg", bounds, args.texture_px, ortho=args.ortho))
    meta = write_terrain(args.out, name, heights, bounds, source=args.source, extra=extra)
    print(f"{args.out / meta['heights']}: {meta['width']}x{meta['height']}, "
          f"{meta['min']:.0f} to {meta['max']:.0f} m")


if __name__ == "__main__":
    main()
