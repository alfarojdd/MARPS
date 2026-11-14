#!/usr/bin/env python3
"""
mars_shadows.py — terrain shadow estimation for a Marswalk at Jezero crater.

Combines three NASA data sources on the common MARPS 20 m grid:

  * MRO CTX DTM (band ``elev_ctx`` of ``stack/jezero_stack_20m.tif``) -> real terrain heights
  * MRO CTX 6 m orthomosaic (optional)                                 -> visual backdrop
  * a sun-position CSV (Time, Elevation, Azimuth) for the site          -> illumination over time
  * optionally, a Marswalk route (GeoJSON lines) and stops (GeoJSON points) to evaluate

For every timestamp with the Sun above the horizon it computes:

  * cast shadow  — the pixel is hidden from the Sun by terrain between it and the Sun
                   (horizon test along the solar ray, exact on the DEM grid);
  * self-shadow  — the slope faces away from the Sun (incidence angle >= 90°).

Conventions (same as ``terrain.py``): DEM in metres, row 0 = north, azimuth measured
clockwise from north (90° = east), elevation in degrees above the horizon.

Outputs (in ``--out``)
----------------------
  shadow_summary.csv        % of the area in shadow per timestamp, % of the route in shadow (if
                            --traverse is given) and the state of the point of interest (if given)
  waypoints_shadow.csv      per stop (if --waypoints is given): daylight fraction in shadow + state
  shadow_masks_20m.tif      one uint8 band per daylight timestamp (0 lit, 1 self-shadow, 2 cast shadow)
  shadow_fraction_20m.tif   fraction of daylight timestamps each pixel spends in shadow
  insolation_rel_shadowed_20m.tif
                            mean direct insolation over the day, relative to flat unshadowed ground
                            (the shadow-aware counterpart of the stack's ``insolation_rel`` band)
  shadow_fraction.png       map of the above over the orthomosaic (with the route, if given)
  frames/shadow_*.png       one image per timestamp
  shadow_animation.gif      animation of the day

All GeoTIFFs share the stack's grid and projection, so they can be added to the viewer/stack.

Usage
-----
  # from data/jezero/pipeline/ (paths to the stack, vectors and ortho are found automatically)
  python mars_shadows.py --sun-csv SunAngle.csv
  python mars_shadows.py --sun-csv SunAngle.csv --lat 18.4447 --lon 77.4508
  python mars_shadows.py --sun-csv SunAngle.csv --ortho JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0.tif
  python mars_shadows.py --sun-csv SunAngle.csv --traverse my_route.geojson --waypoints my_stops.geojson

Route/stop GeoJSONs must use the map projection (metres, +proj=eqc +R=3396190), like vectors/*.geojson.

Dependencies: numpy, scipy, pillow, and either rasterio or tifffile (matplotlib optional).
No extra codec package is needed: compressed float stacks are decoded internally if required.

Limitations
-----------
  * Terrain outside the map box is unknown; it is approximated by extending the edge heights,
    so long low-sun shadows cast by distant relief (e.g. the far crater rim) are not captured.
  * The 20 m DTM cannot represent features smaller than ~40-60 m (boulders, small ridges).
  * Shadows on Mars are not black: dust scattering gives significant diffuse light. This tool
    reports direct-sunlight shadow only.
  * Times in the CSV are used as given (here they appear to be Earth UTC in year-day-of-year
    format, not local Mars solar time).
"""

import argparse
import csv
import json
import math
import os
import re
import sys
import zlib
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENV_CANDIDATES = [os.environ.get("MARS_SHADOWS_PYTHON"), "~/venv-marte/bin/python",
                   "~/venv-marte/Scripts/python.exe", HERE / ".venv/bin/python", HERE / "venv/bin/python"]


def _relaunch_in_venv(err):
    """If this interpreter has a broken numpy/scipy (e.g. system scipy built for NumPy 1.x),
    re-run the script with a virtual-environment Python that has working packages."""
    if not os.environ.get("_MARS_SHADOWS_RELAUNCHED"):
        for c in VENV_CANDIDATES:
            if not c:
                continue
            py = Path(c).expanduser()
            if py.exists() and py.absolute() != Path(sys.executable).absolute():
                print(f"[mars_shadows] numpy/scipy unusable in {sys.executable} ({type(err).__name__}); "
                      f"relaunching with {py}", file=sys.stderr)
                os.environ["_MARS_SHADOWS_RELAUNCHED"] = "1"
                os.execv(str(py), [str(py), str(Path(__file__).resolve())] + sys.argv[1:])
    sys.exit(f"ERROR: numpy/scipy cannot be imported with {sys.executable}: {err}\n"
             "Create a virtual environment and run the script with it:\n"
             "  python3 -m venv ~/venv-marte && ~/venv-marte/bin/pip install numpy scipy pillow tifffile matplotlib\n"
             "  ~/venv-marte/bin/python mars_shadows.py")


try:
    import numpy as np
    from scipy import ndimage
except (ImportError, AttributeError) as _err:
    _relaunch_in_venv(_err)
from PIL import Image, ImageDraw, ImageFont

MARS_RADIUS = 3396190.0  # m, IAU Mars 2000 sphere (projection of all MARPS layers)
STACK_REL = Path("stack/jezero_stack_20m.tif")
ORTHO_NAME = "JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0.tif"


def _search_dirs():
    """Script folder, current folder, their parents and their immediate sub-folders (no Trash)."""
    base = [HERE, Path.cwd(), HERE.parent, Path.cwd().parent]
    out = []

    def subdirs(d):
        try:
            return sorted(p for p in d.iterdir() if p.is_dir() and not p.name.startswith("."))
        except OSError:
            return []

    for d in base:  # the folder, its sub-folders and sub-sub-folders (zip extracted inside a folder)
        out.append(d)
        for s1 in subdirs(d):
            out.append(s1)
            out += subdirs(s1)
    seen, uniq = set(), []
    for d in out:
        r = d.resolve()
        if r not in seen and "/Trash/" not in str(r) + "/":
            seen.add(r)
            uniq.append(d)
    return uniq


def _newest(paths):
    paths = [p for p in paths if p.exists()]
    return max(paths, key=lambda p: p.stat().st_mtime) if paths else None


def find_data_dir():
    """Folder holding stack/jezero_stack_20m.tif (the MARPS data/jezero folder)."""
    if os.environ.get("JEZERO_DATA"):
        return Path(os.environ["JEZERO_DATA"]).resolve()
    hit = _newest([d / STACK_REL for d in _search_dirs()])
    return hit.parents[1] if hit else HERE


DATA = find_data_dir()


def find_file(patterns, extra_dirs=()):
    dirs = list(extra_dirs) + _search_dirs()
    return _newest([f for d in dirs for pat in patterns for f in d.glob(pat)])

# Shadow classes stored in the mask GeoTIFF
LIT, SELF_SHADOW, CAST_SHADOW = 0, 1, 2


# =============================================================================
# Georeferencing and raster I/O
# =============================================================================
class Grid:
    """North-up raster grid: upper-left corner (x0, y0) in metres and pixel size."""

    def __init__(self, x0, y0, px, py, width, height, geokeys=None):
        self.x0, self.y0, self.px, self.py = x0, y0, px, py
        self.width, self.height = width, height
        self.geokeys = geokeys or {}  # raw GeoTIFF key tags, copied to outputs

    @property
    def shape(self):
        return self.height, self.width

    def xy_to_rc(self, x, y):
        """Projected metres -> fractional (row, col) of pixel centres."""
        return (self.y0 - np.asarray(y)) / self.py - 0.5, (np.asarray(x) - self.x0) / self.px - 0.5

    def rc_to_xy(self, r, c):
        return self.x0 + (np.asarray(c) + 0.5) * self.px, self.y0 - (np.asarray(r) + 0.5) * self.py

    @staticmethod
    def lonlat_to_xy(lon, lat):
        """Equirectangular, lat_ts = 0, lon_0 = 0 (the MARPS projection)."""
        return MARS_RADIUS * math.radians(lon), MARS_RADIUS * math.radians(lat)


def _decode_tiff_fallback(path):
    """Minimal GeoTIFF decoder for files tifffile cannot decode without `imagecodecs`
    (deflate + floating-point predictor, as written by rasterio/GDAL). Returns (bands, H, W)."""
    import tifffile

    with tifffile.TiffFile(path) as tif, open(path, "rb") as fh:
        p = tif.pages[0]
        if p.compression not in (1, 8, 32946):
            raise ValueError(f"unsupported TIFF compression {p.compression} in {path}")
        H, W = p.shape[:2] if p.planarconfig == 1 else p.shape[1:3]
        spp, bps = p.samplesperpixel, p.bitspersample
        dtype = np.dtype(p.dtype)
        if p.planarconfig != 1 and spp > 1:
            raise ValueError("fallback decoder supports pixel-interleaved files only")
        if p.is_tiled:
            tw, tl = p.tilewidth, p.tilelength
        else:
            tw, tl = W, p.rowsperstrip
        ntx = -(-W // tw)
        out = np.empty((H, W, spp), dtype)
        nb = bps // 8
        for i, (off, n) in enumerate(zip(p.dataoffsets, p.databytecounts)):
            fh.seek(off)
            buf = fh.read(n)
            if p.compression != 1:
                buf = zlib.decompress(buf)
            rows = len(buf) // (tw * spp * nb)
            raw = np.frombuffer(buf, np.uint8)[: rows * tw * spp * nb].reshape(rows, tw * spp * nb)
            if p.predictor == 3:  # floating point: byte differencing, then byte planes MSB first
                r = np.cumsum(raw.reshape(rows, tw * nb, spp), axis=1, dtype=np.uint8)
                planes = r.reshape(rows, nb, tw * spp).transpose(0, 2, 1).copy()
                vals = planes.view(dtype.newbyteorder(">")).reshape(rows, tw, spp)
            else:
                vals = raw.view(dtype.newbyteorder("<" if tif.byteorder == "<" else ">"))
                vals = vals.reshape(rows, tw, spp)
                if p.predictor == 2:
                    vals = np.cumsum(vals, axis=1, dtype=vals.dtype)
            ty, tx = divmod(i, ntx)
            y0, x0 = ty * tl, tx * tw
            h, w = min(rows, H - y0), min(tw, W - x0)
            if h > 0 and w > 0:
                out[y0:y0 + h, x0:x0 + w] = vals[:h, :w]
    return np.moveaxis(out, -1, 0)


def _band_names_from_gdal_metadata(xml, n):
    names = [None] * n
    for m in re.finditer(r'<Item name="DESCRIPTION" sample="(\d+)" role="description">([^<]*)</Item>', xml or ""):
        k = int(m.group(1))
        if k < n:
            names[k] = m.group(2)
    return names


def read_raster(path):
    """Read a GeoTIFF -> (array (bands, H, W) float64 with NaN for nodata, Grid, band names)."""
    path = str(path)
    try:
        import rasterio  # preferred when available (MARPS pipeline environment)

        with rasterio.open(path) as s:
            arr = s.read().astype(np.float64)
            if s.nodata is not None and not np.isnan(s.nodata):
                arr[arr == s.nodata] = np.nan
            t = s.transform
            grid = Grid(t.c, t.f, t.a, -t.e, s.width, s.height)
            names = list(s.descriptions)
            grid.crs_wkt = s.crs.to_wkt() if s.crs else None
            return arr, grid, names
    except ImportError:
        pass

    import tifffile

    with tifffile.TiffFile(path) as tif:
        p = tif.pages[0]
        tags = {t.code: t.value for t in p.tags.values()}
        spp = p.samplesperpixel
    try:
        arr = tifffile.imread(path)
        if arr.ndim == 2:
            arr = arr[None]
        elif spp > 1 and arr.shape[-1] == spp:
            arr = np.moveaxis(arr, -1, 0)
    except (ValueError, RuntimeError, NotImplementedError):
        arr = _decode_tiff_fallback(path)
    arr = arr.astype(np.float64)
    nod = tags.get(42113)
    if nod is not None:
        try:
            v = float(str(nod).strip("\x00 "))
            if not np.isnan(v):
                arr[arr == v] = np.nan
        except ValueError:
            pass
    if 33550 not in tags or 33922 not in tags:
        sys.exit(f"ERROR: {path} has no georeferencing (ModelPixelScale/ModelTiepoint).")
    px, py = tags[33550][:2]
    i, j, _, x, y, _ = tags[33922][:6]
    geokeys = {c: tags[c] for c in (34735, 34736, 34737) if c in tags}
    grid = Grid(x - i * px, y + j * py, px, py, arr.shape[2], arr.shape[1], geokeys)
    return arr, grid, _band_names_from_gdal_metadata(tags.get(42112), arr.shape[0])


def write_raster(path, arr, grid, band_names=None, nodata=None):
    """Write a (bands, H, W) or (H, W) array as GeoTIFF on `grid` (same projection as the stack)."""
    arr = arr if arr.ndim == 3 else arr[None]
    names = band_names or [None] * arr.shape[0]
    try:
        import rasterio
        from rasterio.crs import CRS

        crs = CRS.from_proj4("+proj=eqc +lat_ts=0 +lat_0=0 +lon_0=0 +x_0=0 +y_0=0 +R=3396190 +units=m +no_defs")
        prof = dict(driver="GTiff", count=arr.shape[0], dtype=arr.dtype.name, width=grid.width,
                    height=grid.height, crs=crs, nodata=nodata, compress="deflate", tiled=True,
                    blockxsize=256, blockysize=256,
                    transform=rasterio.Affine(grid.px, 0, grid.x0, 0, -grid.py, grid.y0))
        with rasterio.open(path, "w", **prof) as d:
            d.write(arr)
            for k, nme in enumerate(names, start=1):
                if nme:
                    d.set_band_description(k, nme)
        return
    except ImportError:
        pass

    import tifffile

    extra = [(33550, "d", 3, (grid.px, grid.py, 0.0), True),
             (33922, "d", 6, (0.0, 0.0, 0.0, grid.x0, grid.y0, 0.0), True)]
    gk = grid.geokeys
    if 34735 in gk:
        extra.append((34735, "H", len(gk[34735]), tuple(gk[34735]), True))
    if 34736 in gk:
        extra.append((34736, "d", len(gk[34736]), tuple(gk[34736]), True))
    if 34737 in gk:
        extra.append((34737, "s", 0, gk[34737], True))
    if any(names):
        items = "".join(f'<Item name="DESCRIPTION" sample="{k}" role="description">{n}</Item>'
                        for k, n in enumerate(names) if n)
        extra.append((42112, "s", 0, f"<GDALMetadata>{items}</GDALMetadata>", True))
    if nodata is not None:
        extra.append((42113, "s", 0, str(nodata), True))
    if arr.shape[0] == 1:  # single band: plain 2-D image (newer tifffile rejects 'separate' here)
        tifffile.imwrite(path, arr[0], photometric="minisblack", compression="zlib", extratags=extra)
    else:
        tifffile.imwrite(path, arr, planarconfig="separate", photometric="minisblack",
                         compression="zlib", extratags=extra)


# =============================================================================
# Inputs: sun CSV and vectors
# =============================================================================
TIME_FORMATS = ("%Y-%jT%H:%M:%S.%f", "%Y-%jT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S")


def read_sun_csv(path):
    """-> list of dicts with keys time (str), label (str), elevation, azimuth (floats)."""
    rows = []
    with open(path, newline="") as fh:
        reader = csv.DictReader(fh)
        reader.fieldnames = [f.strip() for f in reader.fieldnames]
        for r in reader:
            if not r.get("Time"):
                continue
            t = r["Time"].strip()
            label = t.split(".")[0]
            for fmt in TIME_FORMATS:
                try:
                    datetime.strptime(t, fmt)
                    break
                except ValueError:
                    continue
            rows.append(dict(time=t, label=label, elevation=float(r["Elevation"]),
                             azimuth=float(r["Azimuth"]) % 360.0))
    if not rows:
        sys.exit(f"ERROR: no rows read from {path} (expected columns Time, Elevation, Azimuth).")
    return rows


def read_lines_geojson(path):
    """All (Multi)LineString parts of a GeoJSON in projected metres -> list of (N, 2) arrays."""
    if not path or not Path(path).exists():
        return []
    parts = []
    for f in json.load(open(path))["features"]:
        g = f.get("geometry") or {}
        if g.get("type") == "LineString":
            parts.append(np.asarray(g["coordinates"])[:, :2])
        elif g.get("type") == "MultiLineString":
            parts += [np.asarray(c)[:, :2] for c in g["coordinates"] if len(c)]
    return parts


def read_points_geojson(path):
    if not path or not Path(path).exists():
        return []
    pts = []
    for f in json.load(open(path))["features"]:
        g = f.get("geometry") or {}
        if g.get("type") == "Point":
            pts.append((g["coordinates"][0], g["coordinates"][1], f.get("properties") or {}))
    return pts


# =============================================================================
# Shadow model
# =============================================================================
def cast_shadow(dem, res, azimuth, elevation, tol=0.05):
    """Boolean mask: True where terrain between the pixel and the Sun blocks direct sunlight.

    The DEM is resampled onto a frame (u, v) whose v axis points away from the Sun. Along each
    column, pixel i is shadowed iff  max_{j<i}(h_j + j·res·tanθ) > h_i + i·res·tanθ,
    which is a single cumulative maximum: O(N) per timestamp.
    """
    if elevation <= 0:
        return np.ones(dem.shape, bool)
    A = math.radians(azimuth)
    sa, ca = math.sin(A), math.cos(A)
    t = math.tan(math.radians(elevation))
    h, w = dem.shape

    corners_r = np.array([0, 0, h, h], float)
    corners_c = np.array([0, w, 0, w], float)
    x, y = corners_c * res, -corners_r * res
    u, v = x * ca - y * sa, -x * sa - y * ca
    u0, v0 = u.min(), v.min()
    nu = int(math.ceil((u.max() - u0) / res)) + 2
    nv = int(math.ceil((v.max() - v0) / res)) + 2

    U, V = np.meshgrid(u0 + np.arange(nu) * res, v0 + np.arange(nv) * res)
    X, Y = U * ca - V * sa, -U * sa - V * ca  # the (u, v) rotation is its own inverse
    filled = np.where(np.isfinite(dem), dem, np.nanmean(dem))
    # mode="nearest": outside the map the edge heights are extended (no spurious edge shadows)
    rot = ndimage.map_coordinates(filled, [-Y / res, X / res], order=1, mode="nearest")
    del U, V, X, Y

    g = rot + (np.arange(nv) * res * t)[:, None]
    shadow_rot = (np.maximum.accumulate(g, axis=0) - g) > tol

    R, C = np.mgrid[0:h, 0:w].astype(np.float64)
    xo, yo = C * res, -R * res
    iu = ((xo * ca - yo * sa) - u0) / res
    iv = ((-xo * sa - yo * ca) - v0) / res
    back = ndimage.map_coordinates(shadow_rot.astype(np.float32), [iv, iu], order=1, mode="nearest")
    return back > 0.5


def cos_incidence(dem, res, azimuth, elevation):
    """Cosine of the angle between the surface normal and the Sun direction."""
    filled = np.where(np.isfinite(dem), dem, np.nanmean(dem))
    dz_rows, dzdx = np.gradient(filled, res)
    dzdy = -dz_rows  # row 0 = north
    A, E = math.radians(azimuth), math.radians(elevation)
    sx, sy, sz = math.cos(E) * math.sin(A), math.cos(E) * math.cos(A), math.sin(E)
    return (-dzdx * sx - dzdy * sy + sz) / np.sqrt(dzdx ** 2 + dzdy ** 2 + 1.0)


def classify(dem, res, azimuth, elevation):
    """uint8 mask: LIT, SELF_SHADOW or CAST_SHADOW (cast takes precedence), plus cos(i)."""
    cosi = cos_incidence(dem, res, azimuth, elevation)
    out = np.full(dem.shape, LIT, np.uint8)
    out[cosi <= 0] = SELF_SHADOW
    out[cast_shadow(dem, res, azimuth, elevation)] = CAST_SHADOW
    return out, cosi


# =============================================================================
# Rendering
# =============================================================================
def to_uint8(img):
    lo, hi = np.nanpercentile(img, [0.5, 99.5])
    return (np.clip((np.nan_to_num(img, nan=lo) - lo) / (hi - lo + 1e-9), 0, 1) * 255).astype(np.uint8)


def load_font(size):
    for f in ("DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "Arial Bold.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


class Renderer:
    """Draws masks from the DEM grid over a backdrop image (6 m ortho or 20 m stack band)."""

    def __init__(self, backdrop, backdrop_grid, dem_grid, width, traverse, poi_xy):
        f = min(1.0, width / backdrop.shape[1])
        self.size = (max(1, int(backdrop.shape[1] * f)), max(1, int(backdrop.shape[0] * f)))
        img8 = Image.fromarray(to_uint8(backdrop)).resize(self.size, Image.LANCZOS)
        self.base = np.asarray(img8, np.float32)
        # map each output pixel to the DEM grid (nearest)
        sx = backdrop_grid.px * backdrop.shape[1] / self.size[0]
        sy = backdrop_grid.py * backdrop.shape[0] / self.size[1]
        cols = backdrop_grid.x0 + (np.arange(self.size[0]) + 0.5) * sx
        rows = backdrop_grid.y0 - (np.arange(self.size[1]) + 0.5) * sy
        r, c = dem_grid.xy_to_rc(np.zeros_like(rows), rows)[0], dem_grid.xy_to_rc(cols, np.zeros_like(cols))[1]
        self.ri = np.clip(np.round(r).astype(int), 0, dem_grid.height - 1)
        self.ci = np.clip(np.round(c).astype(int), 0, dem_grid.width - 1)
        self.to_px = lambda x, y: ((np.asarray(x) - backdrop_grid.x0) / sx, (backdrop_grid.y0 - np.asarray(y)) / sy)
        self.traverse = [np.column_stack(self.to_px(p[:, 0], p[:, 1])) for p in traverse]
        self.poi = self.to_px(*poi_xy) if poi_xy else None

    def resample(self, arr):
        return arr[self.ri[:, None], self.ci[None, :]]

    def _decorate(self, im, title):
        d = ImageDraw.Draw(im)
        for line in self.traverse:
            if len(line) > 1:
                d.line([tuple(p) for p in line[:: max(1, len(line) // 400)]] + [tuple(line[-1])],
                       fill=(255, 200, 0), width=max(2, im.width // 600))
        if self.poi is not None:
            x, y = self.poi
            rr = max(6, im.width // 110)
            d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=(255, 60, 60), width=3)
        size = max(14, im.width // 55)
        font = load_font(size)
        d.rectangle([0, 0, im.width, size * 2 + 14], fill=(0, 0, 0))
        d.text((10, 6), title, fill=(255, 255, 255), font=font)
        return im

    def frame(self, cls, title):
        rgb = np.repeat(self.base[..., None], 3, axis=2)
        if cls is None:  # night
            rgb *= 0.15
        else:
            m = self.resample(cls)
            cast, selfs = m == CAST_SHADOW, m == SELF_SHADOW
            rgb[cast] = rgb[cast] * 0.35 + np.array([25, 55, 165], np.float32) * 0.65
            rgb[selfs] = rgb[selfs] * 0.45 + np.array([125, 40, 150], np.float32) * 0.55
        return self._decorate(Image.fromarray(rgb.clip(0, 255).astype(np.uint8)), title)


# =============================================================================
# Main
# =============================================================================
def default_path(*candidates):
    for c in candidates:
        if c and Path(c).exists():
            return str(c)
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Terrain shadow estimation on Mars from a DTM and a sun-position CSV")
    auto_csv = find_file(["*SunAngle*.csv", "*sun*angle*.csv", "*Sun*.csv"], [DATA, DATA / "pipeline"])
    auto_stack = DATA / STACK_REL if (DATA / STACK_REL).exists() else None
    auto_ortho = find_file([ORTHO_NAME, "JEZ_ctx_B_soc_008_orthoMosaic*.tif"],
                           [DATA / "raw", DATA.parent.parent / "assets", DATA, DATA / "pipeline"])
    ap.add_argument("--sun-csv", default=str(auto_csv) if auto_csv else None,
                    help="CSV with columns Time, Elevation, Azimuth (default: newest *SunAngle*.csv found "
                         "next to the script, in the current folder or in the repo)")
    ap.add_argument("--stack", default=str(auto_stack) if auto_stack else None,
                    help="multi-band stack or single-band DEM GeoTIFF (default: stack/jezero_stack_20m.tif, "
                         "searched next to the script and in the current folder)")
    ap.add_argument("--dem-band", default="elev_ctx", help="band name holding the DEM (default: elev_ctx)")
    ap.add_argument("--ortho", default=str(auto_ortho) if auto_ortho else None,
                    help="CTX 6 m orthomosaic used as backdrop (default: found automatically if present, "
                         "otherwise band ctx_ortho of the stack)")
    ap.add_argument("--traverse", default=default_path(DATA / "vectors/m20_traverse.geojson"),
                    help="Marswalk route as GeoJSON lines in projected metres (optional)")
    ap.add_argument("--waypoints", default=default_path(DATA / "vectors/m20_waypoints.geojson"),
                    help="GeoJSON points (route stops) to report individually (optional)")
    ap.add_argument("--lat", type=float, help="latitude of a point of interest (°N)")
    ap.add_argument("--lon", type=float, help="longitude of a point of interest (°E)")
    ap.add_argument("--upsample", type=int, default=1,
                    help="refine the DEM grid by this factor (bilinear) for smoother shadow edges")
    ap.add_argument("--no-self-shadow", action="store_true", help="count cast shadows only")
    ap.add_argument("--include-night", action="store_true", help="also add night frames to the animation")
    ap.add_argument("--frame-width", type=int, default=1400)
    ap.add_argument("--out", default=str(HERE / "shadow_results"),
                    help="output folder (default: shadow_results next to this script)")
    args = ap.parse_args(argv)

    if not args.sun_csv:
        sys.exit("ERROR: no sun CSV found. Put SunAngle.csv next to this script or pass --sun-csv FILE.")
    if not args.stack:
        sys.exit("ERROR: no DEM found. Put the script inside the repo (or next to it) or pass "
                 "--stack path/to/jezero_stack_20m.tif.")
    print(f"Inputs:\n  sun CSV : {args.sun_csv}\n  DEM     : {args.stack}\n"
          f"  ortho   : {args.ortho or '(none: stack band ctx_ortho)'}")
    out = Path(args.out)
    (out / "frames").mkdir(parents=True, exist_ok=True)

    # ---- DEM ---------------------------------------------------------------
    print(f"Reading DEM from {args.stack} ...")
    bands, grid, names = read_raster(args.stack)
    if bands.shape[0] == 1:
        dem = bands[0]
    elif args.dem_band in names:
        dem = bands[names.index(args.dem_band)]
    else:
        sys.exit(f"ERROR: band '{args.dem_band}' not found. Available: {names}")
    stack_ortho = bands[names.index("ctx_ortho")] if "ctx_ortho" in names else None
    del bands
    if args.upsample > 1:
        k = args.upsample
        dem = ndimage.zoom(np.where(np.isfinite(dem), dem, np.nanmean(dem)), k, order=1)
        grid = Grid(grid.x0, grid.y0, grid.px / k, grid.py / k, dem.shape[1], dem.shape[0], grid.geokeys)
    res = grid.px
    valid = np.isfinite(dem)
    print(f"  grid {grid.width} x {grid.height} px at {res:g} m/px, "
          f"elevation {np.nanmin(dem):.0f} .. {np.nanmax(dem):.0f} m")

    # ---- route, waypoints, point of interest ---------------------------------
    traverse = read_lines_geojson(args.traverse)
    trav_idx = None
    if traverse:
        pts = np.vstack(traverse)
        r, c = grid.xy_to_rc(pts[:, 0], pts[:, 1])
        r, c = np.round(r).astype(int), np.round(c).astype(int)
        ok = (r >= 0) & (c >= 0) & (r < grid.height) & (c < grid.width)
        trav_idx = np.unique(np.column_stack([r[ok], c[ok]]), axis=0)
        print(f"  route: {len(traverse)} segments, {len(trav_idx)} DEM pixels")

    waypoints = []
    for x, y, props in read_points_geojson(args.waypoints):
        r, c = grid.xy_to_rc(x, y)
        r, c = int(round(float(r))), int(round(float(c)))
        if 0 <= r < grid.height and 0 <= c < grid.width:
            waypoints.append(dict(x=x, y=y, r=r, c=c, props=props))
    if waypoints:
        print(f"  waypoints inside the map: {len(waypoints)}")

    poi_xy = poi_rc = None
    if args.lat is not None and args.lon is not None:
        poi_xy = Grid.lonlat_to_xy(args.lon, args.lat)
        r, c = grid.xy_to_rc(*poi_xy)
        if 0 <= r < grid.height and 0 <= c < grid.width:
            poi_rc = (int(round(float(r))), int(round(float(c))))
            print(f"  point of interest -> row {poi_rc[0]}, col {poi_rc[1]}, "
                  f"elevation {dem[poi_rc]:.0f} m")
        else:
            print("WARNING: the point of interest lies outside the map.")
            poi_xy = None

    # ---- backdrop ----------------------------------------------------------
    if args.ortho and Path(args.ortho).exists():
        print(f"Backdrop: {args.ortho}")
        ob, ogrid, _ = read_raster(args.ortho)
        backdrop, bgrid = ob[0], ogrid
        backdrop[backdrop <= 0] = np.nan
    elif stack_ortho is not None:
        print("Backdrop: stack band ctx_ortho (20 m). Pass --ortho for the 6 m orthomosaic.")
        backdrop, bgrid = stack_ortho, Grid(grid.x0, grid.y0, grid.px * max(1, args.upsample),
                                            grid.py * max(1, args.upsample), stack_ortho.shape[1],
                                            stack_ortho.shape[0])
    else:
        print("Backdrop: hillshade of the DEM")
        backdrop, bgrid = np.clip(cos_incidence(dem, res, 315, 45), 0, 1), grid
    renderer = Renderer(backdrop, bgrid, grid, args.frame_width, traverse, poi_xy)
    del backdrop

    # ---- time loop ---------------------------------------------------------
    sun = read_sun_csv(args.sun_csv)
    n_valid = valid.sum()
    shadow_count = np.zeros(dem.shape, np.float32)
    insol_acc = np.zeros(dem.shape, np.float64)
    flat_acc = 0.0
    masks, mask_names, summary, gif = [], [], [], []
    wp_states = [[] for _ in waypoints]

    print(f"\n{'time':<20} {'elev':>6} {'azim':>7}  {'cast%':>6} {'self%':>6} {'total%':>6} {'route%':>6}")
    for s in sun:
        el, az, label = s["elevation"], s["azimuth"], s["label"]
        row = dict(time=s["time"], elevation_deg=el, azimuth_deg=az, sun_up=el > 0)
        if el <= 0:
            row.update(cast_shadow_pct=100.0, self_shadow_pct=100.0, total_shadow_pct=100.0)
            if trav_idx is not None:
                row["route_shadow_pct"] = 100.0
            if poi_rc:
                row["poi_state"] = "night"
            for st in wp_states:
                st.append(None)
            summary.append(row)
            frame = renderer.frame(None, f"{label}   Sun below horizon (elev {el:.1f}°)")
            frame.save(out / "frames" / f"shadow_{label.replace(':', '')}.png")
            if args.include_night:
                gif.append(frame)
            continue

        cls, cosi = classify(dem, res, az, el)
        if args.no_self_shadow:
            cls[cls == SELF_SHADOW] = LIT
        shaded = (cls != LIT) & valid
        row.update(cast_shadow_pct=100 * ((cls == CAST_SHADOW) & valid).sum() / n_valid,
                   self_shadow_pct=100 * ((cls == SELF_SHADOW) & valid).sum() / n_valid,
                   total_shadow_pct=100 * shaded.sum() / n_valid)
        if trav_idx is not None and len(trav_idx):
            row["route_shadow_pct"] = 100 * shaded[trav_idx[:, 0], trav_idx[:, 1]].mean()
        if poi_rc:
            row["poi_state"] = {LIT: "lit", SELF_SHADOW: "self_shadow", CAST_SHADOW: "cast_shadow"}[int(cls[poi_rc])]
        for st, wp in zip(wp_states, waypoints):
            st.append(int(cls[wp["r"], wp["c"]]))
        summary.append(row)

        shadow_count += shaded
        insol_acc += np.clip(cosi, 0, None) * (cls == LIT)
        flat_acc += math.sin(math.radians(el))
        masks.append(cls)
        mask_names.append(label)

        route = f"{row['route_shadow_pct']:6.2f}" if "route_shadow_pct" in row else "     -"
        print(f"{label:<20} {el:6.2f} {az:7.2f}  {row['cast_shadow_pct']:6.2f} "
              f"{row['self_shadow_pct']:6.2f} {row['total_shadow_pct']:6.2f} {route}")
        title = (f"{label}   Sun elev {el:.1f}°  az {az:.1f}°   shadow {row['total_shadow_pct']:.1f}%"
                 f"   (blue: cast, purple: self)")
        frame = renderer.frame(cls, title)
        frame.save(out / "frames" / f"shadow_{label.replace(':', '')}.png")
        gif.append(frame)

    # ---- tables ------------------------------------------------------------
    cols = ["time", "elevation_deg", "azimuth_deg", "sun_up", "cast_shadow_pct", "self_shadow_pct",
            "total_shadow_pct"] + (["route_shadow_pct"] if trav_idx is not None else []) \
        + (["poi_state"] if poi_rc else [])
    with open(out / "shadow_summary.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in summary:
            w.writerow({k: (f"{v:.3f}" if isinstance(v, float) else v) for k, v in r.items()})

    day_labels = [s["label"] for s in sun if s["elevation"] > 0]
    if waypoints:
        with open(out / "waypoints_shadow.csv", "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["RMC", "sol", "x_m", "y_m", "elevation_m", "daylight_shadow_fraction"] + day_labels)
            names_cls = {LIT: "lit", SELF_SHADOW: "self", CAST_SHADOW: "cast"}
            for wp, st in zip(waypoints, wp_states):
                day = [v for v in st if v is not None]
                frac = np.mean([v != LIT for v in day]) if day else float("nan")
                w.writerow([wp["props"].get("RMC", ""), wp["props"].get("sol", ""), f"{wp['x']:.1f}",
                            f"{wp['y']:.1f}", f"{dem[wp['r'], wp['c']]:.1f}", f"{frac:.3f}"]
                           + [names_cls[v] for v in day])

    # ---- rasters -----------------------------------------------------------
    n_day = len(masks)
    if n_day:
        write_raster(out / "shadow_masks_20m.tif" if args.upsample == 1 else out / "shadow_masks.tif",
                     np.stack(masks), grid, mask_names)
        frac = (shadow_count / n_day).astype(np.float32)
        frac[~valid] = np.nan
        write_raster(out / "shadow_fraction_20m.tif", frac, grid, ["shadow_fraction"], nodata="nan")
        insol = (insol_acc / flat_acc).astype(np.float32)
        insol[~valid] = np.nan
        write_raster(out / "insolation_rel_shadowed_20m.tif", insol, grid, ["insolation_rel_shadowed"],
                     nodata="nan")
        render_fraction_map(renderer, frac, out / "shadow_fraction.png", n_day)
        print(f"\nDaylight timestamps: {n_day}.  Pixels never shadowed: "
              f"{100 * (frac[valid] == 0).mean():.1f}%   mean shadowed fraction: {np.nanmean(frac):.3f}")
    if gif:
        small = [g.resize((g.width // 2, g.height // 2)) if g.width > 900 else g for g in gif]
        small[0].save(out / "shadow_animation.gif", save_all=True, append_images=small[1:],
                      duration=400, loop=0)
    print(f"Done. Results in {out.resolve()}")


def render_fraction_map(renderer, frac, path, n_day):
    """Shadow-fraction colour map over the backdrop, with the traverse."""
    f = renderer.resample(np.nan_to_num(frac))
    vmax = float(max(0.05, np.ceil(np.nanpercentile(frac, 99.9) * 20) / 20))  # round up to 0.05
    fn = np.clip(f / vmax, 0, 1)
    try:
        import matplotlib
        matplotlib.use("Agg")
        cmap = matplotlib.colormaps["plasma"]
        rgba = cmap(fn)[..., :3] * 255
    except ImportError:
        cmap = None
        rgba = np.stack([fn * 255, fn * 80, 255 - fn * 160], -1)
    base = np.repeat(renderer.base[..., None], 3, axis=2)
    alpha = np.where(f > 0, 0.8, 0.0)[..., None]  # pixels never shadowed keep the plain image
    rgb = base * (1 - alpha) + rgba * alpha
    im = renderer._decorate(Image.fromarray(rgb.clip(0, 255).astype(np.uint8)),
                            f"Fraction of daylight in shadow ({n_day} timestamps) — CTX DTM 20 m")
    # colour bar
    d = ImageDraw.Draw(im)
    bw, bh = im.width // 4, max(12, im.height // 60)
    x0, y0 = im.width - bw - 20, im.height - bh - 40
    for i in range(bw):
        v = i / (bw - 1)
        col = (tuple(int(255 * c) for c in cmap(v)[:3]) if cmap is not None
               else (int(v * 255), int(v * 80), int(255 - v * 160)))
        d.line([(x0 + i, y0), (x0 + i, y0 + bh)], fill=col)
    font = load_font(max(12, im.width // 80))
    d.rectangle([x0 - 10, y0 - 10 - font.size, x0 + bw + 10, y0 + bh + font.size + 12], fill=(0, 0, 0))
    d.text((x0, y0 + bh + 4), ">0", fill=(255, 255, 255), font=font)
    d.text((x0 + bw - 3 * font.size, y0 + bh + 4), f"≥{vmax:.2f}", fill=(255, 255, 255), font=font)
    d.text((x0, y0 - font.size - 4), "fraction of daylight in shadow", fill=(255, 255, 255), font=font)
    im.save(path)


if __name__ == "__main__":
    main()
