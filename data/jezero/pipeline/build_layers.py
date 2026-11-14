"""Clip, reproject and derive all Jezero layers onto a common grid.

Common grid: the Mars 2020 TRN CTX DTM grid (equirectangular, sphere R=3396190 m, 20 m/px),
whose extent matches the agreed bbox 77.1605E-77.6992E, 18.2110N-18.7212N.

Usage:
    python build_layers.py base     # layers that do not depend on HiRISE
    python build_layers.py hirise   # 1 m HiRISE products (DTM and orthoimage)
    python build_layers.py stack    # merge everything into stack/jezero_stack_20m.tif + layers.json
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pyogrio
import rasterio
from pyproj import CRS, Transformer
from rasterio import features
from rasterio.enums import Resampling
from rasterio.warp import reproject
from rasterio.windows import Window
from scipy import ndimage

import terrain

HERE = Path(__file__).resolve().parent
# Two layouts: in the MARPS repo the pipeline lives in data/jezero/pipeline/ and the data in data/jezero/;
# in a standalone checkout it lives in tools/jezero/ and the data in data/jezero/. JEZERO_DATA overrides it.
if os.environ.get("JEZERO_DATA"):
    DATA = Path(os.environ["JEZERO_DATA"]).resolve()
elif (HERE.parent / "stack").exists():
    DATA = HERE.parent
else:
    DATA = HERE.parents[1] / "data/jezero"
ROOT = DATA.parents[1]
RAW = DATA / "raw"
L20 = DATA / "layers20m"
HR = DATA / "hires"
STACK = DATA / "stack"
VEC = DATA / "vectors"
SIM = RAW / "sim3464/sim3464_JezeroNili_FINAL"

CTX_DTM = RAW / "JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif"
CTX_ORTHO = RAW / "JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0.tif"
HI_DTM = RAW / "JEZ_hirise_soc_006_DTM_MOLAtopography_DeltaGeoid_1m_Eqc_latTs0_lon0_blend40.tif"

MARS_LONLAT = CRS.from_proj4("+proj=longlat +R=3396190 +no_defs")
CENTER_LAT = 18.466
SCALE_H_M = 11100.0  # Martian atmosphere scale height
MIN_BASE_COVERAGE = 0.999  # base layers must cover the whole bbox

# Common grid = the Mars 2020 TRN CTX DTM grid (hardcoded here to avoid depending on the downloaded file;
# test_grid_matches_ctx_dtm checks it when the file exists).
GRID = dict(crs=CRS.from_proj4("+proj=eqc +lat_ts=0 +lat_0=0 +lon_0=0 +x_0=0 +y_0=0 +R=3396190 +units=m +no_defs"),
            transform=rasterio.Affine(20.0, 0.0, 4573663.250853, 0.0, -20.0, 1109693.140188), width=1596, height=1512)
RES = GRID["transform"].a
BOUNDS = rasterio.transform.array_bounds(GRID["height"], GRID["width"], GRID["transform"])  # (w, s, e, n)


def to_grid(src_path, band=1, resampling=Resampling.bilinear, src_nodata=None):
    """Reproject one band onto the common grid; return float32 with NaN outside the data."""
    out = np.full((GRID["height"], GRID["width"]), np.nan, np.float32)
    with rasterio.open(src_path) as s:
        nod = s.nodata if src_nodata is None else src_nodata
        reproject(rasterio.band(s, band), out, src_nodata=nod, dst_transform=GRID["transform"],
                  dst_crs=GRID["crs"], dst_nodata=np.nan, resampling=resampling)
    return out


def save20(name, arr, nodata=np.nan, dtype="float32"):
    L20.mkdir(parents=True, exist_ok=True)
    prof = dict(driver="GTiff", count=1, dtype=dtype, nodata=nodata, compress="deflate",
                tiled=True, blockxsize=256, blockysize=256, **GRID)
    with rasterio.open(L20 / f"{name}.tif", "w", **prof) as d:
        d.write(arr.astype(dtype), 1)
    print(f"  {name}: min={np.nanmin(arr):.3f} max={np.nanmax(arr):.3f} "
          f"cobertura={np.isfinite(arr).mean() * 100:.0f}%")


def load20(name):
    with rasterio.open(L20 / f"{name}.tif") as s:
        return s.read(1)


def to_grid_xy(crs_from):
    return Transformer.from_crs(crs_from, GRID["crs"], always_xy=True)


# ---------------------------------------------------------------- base

def build_terrain_ctx():
    print("CTX DTM and derivatives")
    dem = to_grid(CTX_DTM, resampling=Resampling.nearest)
    save20("elev_ctx", dem)
    slope = terrain.slope_deg(dem, RES)
    aspect = terrain.aspect_deg(dem, RES)
    save20("slope_ctx", slope)
    save20("aspect_ctx", aspect)
    save20("tri_ctx", terrain.tri(dem))
    save20("tpi_ctx_500m", terrain.tpi(dem, 25))
    save20("hillshade_ctx", terrain.hillshade(dem, RES))
    ins = terrain.mean_direct_insolation(np.nan_to_num(slope), np.nan_to_num(aspect), CENTER_LAT)
    ins[~np.isfinite(dem)] = np.nan
    save20("insolation_rel", ins)
    # Atmospheric shielding proxy: atmosphere column relative to the highest elevation in the area (%).
    col = 100.0 * (np.exp(-(dem - np.nanmax(dem)) / SCALE_H_M) - 1.0)
    save20("atm_column_pct", col)
    save20("ctx_ortho", to_grid(CTX_ORTHO, resampling=Resampling.average, src_nodata=0))


def build_hrsc():
    print("HRSC DTM h0988 (75 m)")
    save20("elev_hrsc", to_grid(SIM / "Rasters/HRSC/h0988_0000.da4.53.tif"))


THEMIS_BASE = "https://astrogeo-ard.s3.us-west-2.amazonaws.com/mars/mo/themis/controlled_mosaics"
TI_GLOBAL = ("https://asc-astropedia.s3.us-west-2.amazonaws.com/Mars/Odyssey/THEMIS-Global-Thermal-Inertia-Mosaic/"
             "Quantitative-32-Bit/THEMIS_TI_Mosaic_Quant_00N060E_100mpp.cub")


def build_thermal():
    """THEMIS at 100 m with full bbox coverage (clips of USGS global/regional mosaics)."""
    print("THEMIS")
    from fetch_clip import fetch
    clips = {"themis_ti_quant_global_clip.tif": TI_GLOBAL,
             "themis_mc13_day_ir_clip.tif": f"{THEMIS_BASE}/mc13_syrtis_major_dir/mc13_syrtis_major_dir.tif",
             "themis_mc13_night_ir_clip.tif": f"{THEMIS_BASE}/mc13_syrtis_major_nir/mc13_syrtis_major_nir.tif"}
    for name, url in clips.items():
        if not (RAW / name).exists():
            fetch(url, name)
    # Thermal inertia: use the Jezero product (better quality) even though it lacks the western strip;
    # the quantitative global one covers everything but has striping between passes and is kept only as reference.
    save20("thermal_inertia", to_grid(RAW / "Jezero_Thermal_Inertia_v1.tiff", src_nodata=0))
    ti = to_grid(RAW / "themis_ti_quant_global_clip.tif")
    ti[ti <= 0] = np.nan
    save20("thermal_inertia_global", ti)
    save20("themis_day_ir", to_grid(RAW / "themis_mc13_day_ir_clip.tif", src_nodata=0))
    save20("themis_night_ir", to_grid(RAW / "themis_mc13_night_ir_clip.tif", src_nodata=0))


# Color key from Parente, Itoh and Saranathan (Jezero_readme.pdf): (high confidence, medium confidence)
CRISM_CLASSES = [
    ("Olivine", (255, 0, 0), (153, 0, 0)),
    ("Mg carbonate", (0, 255, 0), (0, 153, 0)),
    ("Fe/Mg smectite", (0, 255, 255), (0, 153, 153)),
    ("Olivine + smectite", (255, 128, 114), (153, 77, 68)),
    ("Olivine/smectite + 2.2 µm", (128, 128, 0), (77, 77, 0)),
    ("Carbonate + 2.2 µm", (255, 215, 0), (153, 129, 0)),
    ("High-Ca pyroxene", (255, 128, 0), (153, 77, 0)),
    ("Low-Ca pyroxene", (218, 165, 32), (130, 99, 19)),
    ("Kaolinite", (139, 69, 19), (83, 41, 11)),
    ("Mg smectite 2", (0, 0, 255), (0, 0, 153)),
]


CRISM_MAX_COLOR_DIST = 40.0  # the published TIFF has compression noise in its colors


def classify_crism(rgb):
    """RGB (3,H,W) -> (class, confidence).

    class: 1..10 per CRISM_CLASSES, 0 = unidentified (black or ambiguous color), -1 = outside the scene (white).
    confidence: 2 high, 1 medium, 0 none, -1 outside.
    """
    codes = [((0, 0, 0), 0, 0), ((255, 255, 255), -1, -1)]
    for i, (_, hi, mid) in enumerate(CRISM_CLASSES, start=1):
        codes += [(hi, i, 2), (mid, i, 1)]
    pal = np.array([c[0] for c in codes], np.float32)
    px = rgb.reshape(3, -1).T.astype(np.float32)
    d = np.linalg.norm(px[:, None, :] - pal[None, :, :], axis=2)
    best = d.argmin(1)
    ok = d[np.arange(len(best)), best] <= CRISM_MAX_COLOR_DIST
    cls = np.where(ok, np.array([c[1] for c in codes])[best], 0).astype(np.int16)
    conf = np.where(ok, np.array([c[2] for c in codes])[best], 0).astype(np.int16)
    shape = rgb.shape[1:]
    return cls.reshape(shape), conf.reshape(shape)


def build_crism():
    print("CRISM (mineral classes)")
    src = RAW / "jezeroFinal.tif"
    with rasterio.open(src) as s:
        rgb = np.zeros((3, GRID["height"], GRID["width"]), np.uint8)
        for b in range(3):
            reproject(rasterio.band(s, b + 1), rgb[b], dst_transform=GRID["transform"], dst_crs=GRID["crs"],
                      resampling=Resampling.nearest)
        cover = np.zeros((GRID["height"], GRID["width"]), np.uint8)
        reproject(np.ones((s.height, s.width), np.uint8), cover, src_transform=s.transform, src_crs=s.crs,
                  dst_transform=GRID["transform"], dst_crs=GRID["crs"], dst_nodata=0, resampling=Resampling.nearest)
    cls, conf = classify_crism(rgb)
    outside = (cover == 0) | (cls == -1)
    ambiguous = ~outside & (cls == 0) & (rgb.astype(int).sum(0) > 3 * CRISM_MAX_COLOR_DIST)
    print(f"  pixels with ambiguous color (marked as unidentified): {ambiguous.sum()}")
    save20("crism_class", np.where(outside, -1, cls), nodata=-1, dtype="int16")
    save20("crism_conf", np.where(outside, -1, conf), nodata=-1, dtype="int16")


def _clip_box_gdf(gdf):
    from shapely.geometry import box
    w, s, e, n = BOUNDS
    gdf = gdf.clip(box(w, s, e, n))
    return gdf[~(gdf.geometry.isna() | gdf.geometry.is_empty)]


def build_geology():
    print("SIM 3464 geologic map")
    VEC.mkdir(parents=True, exist_ok=True)
    gdb = SIM / "Geodatabase/Nili.gdb"
    units = pyogrio.read_dataframe(gdb, layer="GeoUnits_v1").to_crs(GRID["crs"])
    units = _clip_box_gdf(units)
    names = sorted(units["symbol"].dropna().unique())
    code = {s: i + 1 for i, s in enumerate(names)}
    units["code"] = units["symbol"].map(code).fillna(0).astype(int)
    ras = features.rasterize(((g, c) for g, c in zip(units.geometry, units.code)), out_shape=(GRID["height"], GRID["width"]),
                             transform=GRID["transform"], fill=0, dtype="int16")
    save20("geo_unit", ras, nodata=0, dtype="int16")
    legend = (units.drop_duplicates("symbol")[["symbol", "name", "unit", "code"]]
              .sort_values("code").to_dict("records"))
    (VEC / "geo_units_legend.json").write_text(json.dumps(legend, ensure_ascii=False, indent=1))
    units = units[["symbol", "name", "code", "geometry"]].copy()
    units["geometry"] = units.geometry.simplify(5.0)
    units.to_file(VEC / "geo_units.geojson", driver="GeoJSON")
    for layer, out in (("SurfaceFeatures", "geo_surface_features"), ("LinearFeatures", "geo_linear_features"),
                       ("LocationFeatures", "geo_location_features")):
        g = _clip_box_gdf(pyogrio.read_dataframe(gdb, layer=layer).to_crs(GRID["crs"]))
        keep = [c for c in ("TYPE", "name") if c in g.columns]
        g[keep + ["geometry"]].to_file(VEC / f"{out}.geojson", driver="GeoJSON")
        print(f"  {out}: {len(g)} features")


# ---------------------------------------------------------------- HiRISE 1 m

def _hires_profile(src, dtype, nodata):
    p = src.profile.copy()
    p.update(driver="GTiff", dtype=dtype, nodata=nodata, count=1, compress="deflate", tiled=True,
             blockxsize=512, blockysize=512, predictor=2, BIGTIFF="IF_SAFER")
    return p


def build_hirise_dtm(chunk=1000):
    """Slope and hillshade at 1 m, plus 20 m aggregates (mean elevation, max/mean slope, roughness)."""
    print("HiRISE DTM 1 m (in blocks)")
    HR.mkdir(parents=True, exist_ok=True)
    f = 20
    with rasterio.open(HI_DTM) as s:
        H, W = s.height, s.width
        Hc, Wc = H // f, W // f
        agg = {k: np.full((Hc, Wc), np.nan, np.float32) for k in ("elev", "slope_max", "slope_mean", "rough")}
        with rasterio.open(HR / "slope_hirise_1m.tif", "w", **_hires_profile(s, "uint8", 255)) as ds, \
                rasterio.open(HR / "hillshade_hirise_1m.tif", "w", **_hires_profile(s, "uint8", 0)) as dh:
            for r0 in range(0, Hc * f, chunk):
                r1 = min(r0 + chunk, Hc * f)
                a0, a1 = max(r0 - 1, 0), min(r1 + 1, H)
                dem = s.read(1, window=Window(0, a0, W, a1 - a0)).astype(np.float32)
                dem[(dem < -1e4) | (dem > 1e4)] = np.nan
                sl = terrain.slope_deg(dem, 1.0).astype(np.float32)[r0 - a0:r0 - a0 + (r1 - r0)]
                hs = terrain.hillshade(dem, 1.0).astype(np.float32)[r0 - a0:r0 - a0 + (r1 - r0)]
                core = dem[r0 - a0:r0 - a0 + (r1 - r0)]
                win = Window(0, r0, W, r1 - r0)
                ds.write(np.where(np.isfinite(sl), np.clip(np.round(sl), 0, 90), 255).astype(np.uint8), 1, window=win)
                dh.write(np.where(np.isfinite(hs), 1 + np.round(hs * 254), 0).astype(np.uint8), 1, window=win)
                rr = slice(r0 // f, r1 // f)
                agg["elev"][rr] = terrain.block_reduce(core, f, "mean")
                agg["slope_max"][rr] = terrain.block_reduce(sl, f, "max")
                agg["slope_mean"][rr] = terrain.block_reduce(sl, f, "mean")
                agg["rough"][rr] = terrain.block_reduce(sl, f, "std")
                print(f"  rows {r1}/{H}", end="\r")
        t20 = s.transform * rasterio.Affine.scale(f)
        crs = s.crs
    print()
    for k, name in (("elev", "elev_hirise"), ("slope_max", "slope_hirise_max"),
                    ("slope_mean", "slope_hirise_mean"), ("rough", "rough_hirise")):
        out = np.full((GRID["height"], GRID["width"]), np.nan, np.float32)
        reproject(agg[k], out, src_transform=t20, src_crs=crs, src_nodata=np.nan, dst_transform=GRID["transform"],
                  dst_crs=GRID["crs"], dst_nodata=np.nan, resampling=Resampling.nearest)
        save20(name, out)
    for p in ("slope_hirise_1m.tif", "hillshade_hirise_1m.tif"):
        with rasterio.open(HR / p, "r+") as d:
            d.build_overviews([2, 4, 8, 16, 32, 64, 128], Resampling.average)


STAC_URL = "https://stac.astrogeology.usgs.gov/api/"


def hirise_ortho_assets():
    """Controlled 1 m HiRISE orthoimages (*_RED_C_01_ORTHO variant) of the DTMs that touch the bbox."""
    from pystac_client import Client
    w, s, e, n = BOUNDS
    m = 180 / (np.pi * 3396190)
    items = Client.open(STAC_URL).search(collections=["mro_hirise_socet_dtms"],
                                         bbox=[w * m, s * m, e * m, n * m]).items()
    hrefs = []
    for it in items:
        cs = sorted(a.href for k, a in it.assets.items() if a.href.endswith("_RED_C_01_ORTHO.tif"))
        hrefs += cs[:1]
    return hrefs


def build_hirise_ortho():
    """1 m mosaic of controlled HiRISE orthoimages (USGS, COG on S3) over the whole bbox.

    Replaces the 25 cm TRN orthoimage (3.4 GB) when the download from planetarymaps is slow.
    Each image is stretched to 8 bits with its 0.5-99.5 percentiles; earlier images take priority.
    """
    print("HiRISE ortho 1 m from COG")
    HR.mkdir(parents=True, exist_ok=True)
    w, s, e, n = BOUNDS
    tr = rasterio.Affine(1.0, 0, w, 0, -1.0, n)
    W, H = int(round(e - w)), int(round(n - s))
    prof = dict(driver="GTiff", count=1, dtype="uint8", nodata=0, crs=GRID["crs"], transform=tr, width=W, height=H,
                compress="deflate", tiled=True, blockxsize=512, blockysize=512, predictor=2, BIGTIFF="IF_SAFER")
    out_path = HR / "ortho_hirise_1m.tif"
    with rasterio.open(out_path, "w", **prof):
        pass
    for href in hirise_ortho_assets():
        with rasterio.open("/vsicurl/" + href) as src:
            win = rasterio.windows.from_bounds(*src.bounds, transform=tr).round_offsets().round_lengths()
            win = win.intersection(Window(0, 0, W, H))
            data = src.read(1)
            valid = data[data > 0]
            lo, hi = np.percentile(valid, [0.5, 99.5]) if valid.size else (0, 1)
            img = np.where(data > 0, 1 + np.clip((data - lo) / max(hi - lo, 1) * 254, 0, 254), 0).astype(np.uint8)
            dst = np.zeros((int(win.height), int(win.width)), np.uint8)
            reproject(img, dst, src_transform=src.transform, src_crs=src.crs, src_nodata=0,
                      dst_transform=rasterio.windows.transform(win, tr), dst_crs=GRID["crs"], dst_nodata=0,
                      resampling=Resampling.bilinear)
        with rasterio.open(out_path, "r+") as d:
            cur = d.read(1, window=win)
            d.write(np.where(cur == 0, dst, cur), 1, window=win)
        print(f"  {href.split('/')[-1]}: {(dst > 0).mean() * 100:.0f}% of its window")
    with rasterio.open(out_path, "r+") as d:
        d.build_overviews([2, 4, 8, 16, 32, 64, 128], Resampling.average)


# ---------------------------------------------------------------- stack

def build_stack():
    from layers import STACK_BANDS
    STACK.mkdir(parents=True, exist_ok=True)
    present = [b for b in STACK_BANDS if (L20 / f"{b['id']}.tif").exists()]
    missing = [b["id"] for b in STACK_BANDS if b not in present]
    if missing:
        sys.exit(f"faltan capas base: {missing}")
    prof = dict(driver="GTiff", count=len(present), dtype="float32", nodata=np.nan, compress="deflate",
                tiled=True, blockxsize=256, blockysize=256, predictor=3, **GRID)
    with rasterio.open(STACK / "jezero_stack_20m.tif", "w", **prof) as d:
        for i, b in enumerate(present, start=1):
            a = load20(b["id"]).astype(np.float32)
            with rasterio.open(L20 / f"{b['id']}.tif") as s:
                if s.nodata is not None and not np.isnan(s.nodata):
                    a[a == s.nodata] = np.nan
            cov = float(np.isfinite(a).mean())
            if cov < b.get("min_coverage", MIN_BASE_COVERAGE):
                sys.exit(f"{b['id']} solo cubre el {cov * 100:.1f} % del bbox; no puede ir al stack base")
            d.write(a, i)
            d.set_band_description(i, b["id"])
    w, s, e, n = BOUNDS
    manifest = dict(
        crs=GRID["crs"].to_proj4(), transform=list(GRID["transform"])[:6], width=GRID["width"],
        height=GRID["height"], resolution_m=RES, bounds_m=dict(west=w, south=s, east=e, north=n),
        bbox_lonlat=[77.1604655, 18.2110274, 77.6991776, 18.7211945],
        bands=[dict(index=i, **b) for i, b in enumerate(present, start=1)],
    )
    (STACK / "layers.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    print(f"stack: {len(present)} bands -> {STACK / 'jezero_stack_20m.tif'}")


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "base"
    if stage == "base":
        build_terrain_ctx(); build_hrsc(); build_thermal(); build_crism(); build_geology()
    elif stage == "hirise":
        build_hirise_dtm(); build_hirise_ortho()
    elif stage == "hirise_dtm":
        build_hirise_dtm()
    elif stage == "hirise_ortho":
        build_hirise_ortho()
    elif stage == "stack":
        build_stack()
    else:
        sys.exit(f"unknown stage: {stage}")
