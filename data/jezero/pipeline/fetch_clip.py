"""Download only the bbox window (plus a margin) of a remote GeoTIFF (COG) and save it to raw/."""
import sys
import rasterio
from rasterio.windows import from_bounds
import build_layers as bl

MARGIN_M = 2000


def fetch(url, name):
    w, s, e, n = bl.BOUNDS
    with rasterio.open("/vsicurl/" + url) as src:
        b = rasterio.warp.transform_bounds(bl.GRID["crs"], src.crs, w - MARGIN_M, s - MARGIN_M, e + MARGIN_M, n + MARGIN_M)
        win = from_bounds(*b, transform=src.transform).round_offsets().round_lengths()
        data = src.read(window=win)
        prof = src.profile.copy()
        prof.update(width=win.width, height=win.height, transform=src.window_transform(win), driver="GTiff",
                    compress="deflate", tiled=True, blockxsize=256, blockysize=256)
        with rasterio.open(bl.RAW / name, "w", **prof) as d:
            d.write(data)
    print(name, data.shape, f"{(data[0] != (prof['nodata'] or 0)).mean() * 100:.1f}% with data")


if __name__ == "__main__":
    import rasterio.warp  # noqa: F401
    fetch(sys.argv[1], sys.argv[2])
