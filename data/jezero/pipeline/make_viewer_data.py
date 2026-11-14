"""Generate the viewer data: per-layer tiles, vectors, legends and the value probe.

Tiles use a custom metric CRS (the common grid's equirectangular):
zoom z -> 128 / 2**z m/px; tile (x, y) starts at (LEFT + 256*x*res, TOP - 256*y*res).

Usage: python make_viewer_data.py [layer_id ...]   (no arguments: all)
"""
import json
import os
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import matplotlib
import numpy as np
import rasterio
import rasterio.warp
from matplotlib.colors import LinearSegmentedColormap
from PIL import Image
from rasterio.enums import Resampling
from rasterio.windows import from_bounds

import build_layers as bl
from layers import LAYERS, STACK_BANDS, WHY

DATA = bl.DATA
_viewer = next((bl.ROOT / d for d in ("platform/viewer", "viewer") if (bl.ROOT / d).exists()), bl.ROOT / "viewer")
OUT = Path(os.environ["JEZERO_VIEWER_DATA"]) if os.environ.get("JEZERO_VIEWER_DATA") else _viewer / "data"
TILE = 256
RES0 = 128.0
W_, S_, E_, N_ = bl.BOUNDS
LEFT, TOP = W_, N_

SLOPE_CMAP = LinearSegmentedColormap.from_list(
    "slope", [(0, "#1a9850"), (10 / 35, "#d9ef8b"), (15 / 35, "#fee08b"), (20 / 35, "#fc8d59"),
              (30 / 35, "#d73027"), (1, "#7b3294")])

CRISM_COLORS = {i: c[1] for i, c in enumerate(bl.CRISM_CLASSES, start=1)}

GEO_COLORS = {  # by unit symbol (SIM 3464)
    "Aeb": "#e6c88a", "Hnpf": "#8fb3d9", "NHjf1": "#4f7fbf", "NHjf2": "#2c5a9e", "Njf": "#c9a27e",
    "Nle": "#e39b5b", "Nue": "#f2c08a", "Nnp1": "#d98ca0", "Nnp2": "#b8607a", "Nrb": "#b0b0b0",
    "ce": "#8cc68c", "ci": "#5fa35f", "cr": "#3d7d3d", "su": "#f0e06a",
}


def res_at(z):
    return RES0 / 2 ** z


def tile_range(z, bounds):
    w, s, e, n = bounds
    span = TILE * res_at(z)
    x0, x1 = int((max(w, W_) - LEFT) // span), int((min(e, E_) - LEFT - 1e-6) // span)
    y0, y1 = int((TOP - min(n, N_)) // span), int((TOP - max(s, S_) - 1e-6) // span)
    return range(x0, x1 + 1), range(y0, y1 + 1)


def rgba_hex(h, a=255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def geo_palette():
    leg = json.loads((DATA / "vectors/geo_units_legend.json").read_text())
    return {d["code"]: (d["symbol"], d["name"], GEO_COLORS.get(d["symbol"], "#888888")) for d in leg}


# ------------------------------------------------------------ render

_ds = {}


def _open(path):
    if path not in _ds:
        _ds[path] = rasterio.open(path)
    return _ds[path]


def read_tile(layer, z, x, y, path=None, categorical=False):
    src = _open(path or str(DATA / layer["src"]))
    span = TILE * res_at(z)
    w, n = LEFT + x * span, TOP - y * span
    win = from_bounds(w, n - span, w + span, n, transform=src.transform)
    nod = layer.get("nodata", src.nodata)
    a = src.read(1, window=win, out_shape=(TILE, TILE), boundless=True,
                 fill_value=nod if nod is not None and not np.isnan(nod) else 0,
                 resampling=Resampling.nearest if categorical else Resampling.bilinear).astype(np.float32)
    if nod is not None:
        a[a == nod] = np.nan
    # outside the file extent or the bbox: transparent
    r = span / TILE
    xs = w + (np.arange(TILE) + 0.5) * r
    ys = n - (np.arange(TILE) + 0.5) * r
    sb = src.bounds
    out_x = (xs < max(sb.left, W_)) | (xs > min(sb.right, E_))
    out_y = (ys < max(sb.bottom, S_)) | (ys > min(sb.top, N_))
    a[out_y, :] = np.nan
    a[:, out_x] = np.nan
    if src.nodata is None and layer["kind"] == "image":
        a[a == 0] = np.nan
    return a


def render(layer, z, x, y, extra):
    kind = layer["kind"]
    if kind == "categorical":
        a = read_tile(layer, z, x, y, categorical=True)
        rgba = np.zeros(a.shape + (4,), np.uint8)
        if layer["id"] == "crism_class":
            conf = read_tile(layer, z, x, y, path=str(DATA / "layers20m/crism_conf.tif"), categorical=True)
            for v, col in CRISM_COLORS.items():
                for c, alpha in ((2, 235), (1, 150)):
                    rgba[(a == v) & (conf == c)] = col + (alpha,)
        else:
            for v, (_, _, col) in extra["geo"].items():
                rgba[a == v] = rgba_hex(col, 210)
    else:
        a = read_tile(layer, z, x, y)
        lo, hi = extra["range"]
        t = np.clip((a - lo) / (hi - lo), 0, 1)
        if kind == "image":
            g = (np.nan_to_num(t) * 255).astype(np.uint8)
            rgba = np.dstack([g, g, g, np.where(np.isnan(a), 0, 255).astype(np.uint8)])
        else:
            cmap = SLOPE_CMAP if layer["cmap"] == "slope" else matplotlib.colormaps[layer["cmap"]]
            rgba = (cmap(np.nan_to_num(t)) * 255).astype(np.uint8)
            rgba[..., 3] = np.where(np.isnan(a), 0, 255)
    if rgba[..., 3].max() == 0:
        return False
    d = OUT / "tiles" / layer["id"] / str(z) / str(x)
    d.mkdir(parents=True, exist_ok=True)
    img = Image.fromarray(rgba, "RGBA")
    if kind == "image":
        img.save(d / f"{y}.webp", quality=82, method=4)
    else:
        img.save(d / f"{y}.png", optimize=False, compress_level=6)
    return True


def _job(args):
    layer, z, xs, ys, extra = args
    return sum(render(layer, z, x, y, extra) for x in xs for y in ys)


def image_range(layer):
    if layer.get("stretch") != "percent":
        return layer["vmin"], layer["vmax"]
    with rasterio.open(DATA / layer["src"]) as s:
        ov = s.overviews(1)
        f = ov[-1] if ov else 4
        a = s.read(1, out_shape=(max(1, s.height // f), max(1, s.width // f))).astype(np.float32)
        nod = s.nodata if s.nodata is not None else 0
        v = a[(a != nod) & np.isfinite(a) & (a > 0)]
    return tuple(np.percentile(v, [1, 99]).tolist())


def build_tiles(layer, pool):
    out = OUT / "tiles" / layer["id"]
    if out.exists():
        shutil.rmtree(out)
    extra = {}
    if layer["kind"] in ("image", "continuous"):
        extra["range"] = image_range(layer) if layer["kind"] == "image" else (layer["vmin"], layer["vmax"])
    if layer["id"] == "geo_unit":
        extra["geo"] = geo_palette()
    with rasterio.open(DATA / layer["src"]) as s:
        b = rasterio.warp.transform_bounds(s.crs, bl.GRID["crs"], *s.bounds)
    jobs = []
    for z in range(0, layer["maxzoom"] + 1):
        xs, ys = tile_range(z, b)
        for x in xs:  # one task per column
            jobs.append((layer, z, [x], list(ys), extra))
    n = sum(pool.map(_job, jobs, chunksize=4))
    print(f"  {layer['id']}: {n} teselas")
    extra["bounds"] = [max(b[0], W_), max(b[1], S_), min(b[2], E_), min(b[3], N_)]
    return extra


# ------------------------------------------------------------ legends, vectors, probe

def legend(layer, extra):
    k = layer["kind"]
    if k == "continuous":
        cmap = SLOPE_CMAP if layer["cmap"] == "slope" else matplotlib.colormaps[layer["cmap"]]
        stops = [matplotlib.colors.to_hex(cmap(t)) for t in np.linspace(0, 1, 9)]
        return dict(type="ramp", stops=stops, vmin=layer["vmin"], vmax=layer["vmax"], units=layer.get("units", ""))
    if layer["id"] == "crism_class":
        return dict(type="classes", items=[dict(value=i, color="#%02x%02x%02x" % c[1], label=c[0])
                                           for i, c in enumerate(bl.CRISM_CLASSES, start=1)],
                    note="Color intenso: confianza alta. Atenuado: confianza media.")
    if layer["id"] == "geo_unit":
        return dict(type="classes", items=[dict(value=v, color=col, label=f"{sym}: {name}")
                                           for v, (sym, name, col) in sorted(extra["geo"].items())])
    return dict(type="image")


def coverage_pct(layer):
    """Percentage of the bbox with data, measured on the common 20 m grid."""
    a = np.full((bl.GRID["height"], bl.GRID["width"]), np.nan, np.float32)
    with rasterio.open(DATA / layer["src"]) as s:
        rasterio.warp.reproject(rasterio.band(s, 1), a, src_nodata=layer.get("nodata", s.nodata if s.nodata is not None else 0),
                                dst_transform=bl.GRID["transform"], dst_crs=bl.GRID["crs"], dst_nodata=np.nan,
                                resampling=Resampling.nearest)
    valid = np.isfinite(a) & ((a >= layer.get("valid_min", 1)) if layer["kind"] == "categorical" else True)
    return round(float(valid.mean()) * 100, 1)


def copy_vectors():
    d = OUT / "vectors"
    d.mkdir(parents=True, exist_ok=True)
    for f in d.glob("*.geojson"):
        f.unlink()
    for f in (DATA / "vectors").glob("*.geojson"):
        shutil.copy(f, d / f.name)


def build_probe():
    """Values of all stack bands at 40 m, quantized to int16, for the viewer inspector."""
    d = OUT / "probe"
    d.mkdir(parents=True, exist_ok=True)
    meta = []
    with rasterio.open(DATA / "stack/jezero_stack_20m.tif") as s:
        names = list(s.descriptions)
        for b in STACK_BANDS:
            if b["id"] not in names:
                continue
            a = s.read(names.index(b["id"]) + 1)
            cat = b["units"] in ("clase", "nivel")
            a = a[::2, ::2] if cat else bl.terrain.block_reduce(a, 2, "mean")
            lo, hi = float(np.nanmin(a)), float(np.nanmax(a))
            scale = max(hi - lo, 1e-6) / 65000.0 if not cat else 1.0
            off = lo if not cat else 0.0
            q = np.where(np.isfinite(a), np.round((a - off) / scale) - 32500 * (not cat), -32768)
            q.astype("<i2").tofile(d / f"{b['id']}.bin")
            meta.append(dict(id=b["id"], units=b["units"], desc=b["desc"], scale=scale,
                             offset=off + (32500 * scale if not cat else 0.0), categorical=cat))
        h, w = a.shape
    return dict(width=w, height=h, res=bl.RES * 2, left=LEFT, top=TOP, bands=meta)


def main(only):
    OUT.mkdir(parents=True, exist_ok=True)
    cfg_path = OUT / "config.json"
    keep = {l["id"] for l in LAYERS}
    old = {l["id"]: l for l in json.loads(cfg_path.read_text())["layers"]} if cfg_path.exists() else {}
    old = {k: v for k, v in old.items() if k in keep}
    for d in (OUT / "tiles").glob("*") if (OUT / "tiles").exists() else []:
        if d.name not in keep:
            shutil.rmtree(d)
            print(f"  retirada del visor: {d.name}")
    todo = [l for l in LAYERS if (DATA / l["src"]).exists() and (not only or l["id"] in only)]
    missing = [l["id"] for l in LAYERS if not (DATA / l["src"]).exists()]
    if missing:
        print("sin datos todavía:", missing)
    with ProcessPoolExecutor(max_workers=10) as pool:
        for layer in todo:
            extra = build_tiles(layer, pool)
            old[layer["id"]] = dict(
                id=layer["id"], group=layer["group"], title=layer["title"], kind=layer["kind"],
                units=layer.get("units", ""), maxzoom=layer["maxzoom"], observed=layer["obs"],
                source=layer["source"], why=WHY[layer["id"]], legend=legend(layer, extra), bounds=extra["bounds"],
                coverage=coverage_pct(layer), base=layer.get("base", True),
                ext="webp" if layer["kind"] == "image" else "png")
    copy_vectors()
    probe = build_probe() if (DATA / "stack/jezero_stack_20m.tif").exists() else None
    ordered = [old[l["id"]] for l in LAYERS if l["id"] in old]
    cfg = dict(left=LEFT, top=TOP, right=E_, bottom=S_, res0=RES0, tile=TILE, radius=3396190.0,
               layers=ordered, probe=probe)
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=1))
    print(f"config: {len(ordered)} capas")


if __name__ == "__main__":
    main(set(sys.argv[1:]))
