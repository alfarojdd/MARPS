"""Export the viewer's tiled layers as one image per layer for the React frontend (platform/web).

Input: platform/viewer/data/config.json + tiles/ (from make_viewer_data.py).
Output: platform/web/public/layers/thematic/<id>.webp and layers.json, with bounds in CTX 6 m pixels
(the React map uses Leaflet CRS.Simple with lat = -row, lng = col).

Usage: python3 data/jezero/pipeline/export_web_layers.py [--zoom 3]
"""
import argparse
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "platform/viewer/data"
OUT = ROOT / "platform/web/public/layers/thematic"
CTX_RES = 6.0

TITLES = {
    "hillshade_ctx": ("Hillshade", "Basemap", "CTX DTM shaded relief, 20 m"),
    "elev_ctx": ("Elevation", "Topography", "CTX DTM, 20 m"),
    "elev_hrsc": ("Elevation (HRSC)", "Topography", "HRSC h0988 DTM, 75 m"),
    "slope_ctx": ("Slope", "Topography", "From CTX DTM, 20 m"),
    "tri_ctx": ("Roughness (TRI)", "Topography", "Terrain ruggedness index"),
    "tpi_ctx_500m": ("Topographic position", "Topography", "TPI, 500 m window"),
    "aspect_ctx": ("Aspect", "Topography", "Slope orientation"),
    "thermal_inertia": ("Thermal inertia", "Thermal", "THEMIS, 100 m (soft sand is low)"),
    "themis_day_ir": ("THEMIS day IR", "Thermal", "Daytime infrared, 100 m"),
    "themis_night_ir": ("THEMIS night IR", "Thermal", "Night-time infrared, 100 m"),
    "insolation_rel": ("Sunlight", "Mission", "Mean relative direct insolation"),
    "atm_column_pct": ("Radiation shielding", "Mission", "Extra atmospheric column (low ground = more shielding)"),
    "geo_unit": ("Geologic units", "Science", "USGS SIM 3464"),
    "crism_class": ("Mineralogy (CRISM)", "Science", "Carbonates, clays, olivine... (central 41 %)"),
}

def stitch(layer, zoom, cfg):
    tile = cfg["tile"]
    res = cfg["res0"] / 2 ** zoom
    width = round((cfg["right"] - cfg["left"]) / res)
    height = round((cfg["top"] - cfg["bottom"]) / res)
    canvas = Image.new("RGBA", (width, height))
    folder = SRC / "tiles" / layer["id"] / str(zoom)
    for x in range(-(-width // tile)):
        for y in range(-(-height // tile)):
            path = folder / str(x) / f"{y}.{layer['ext']}"
            if path.is_file():
                canvas.paste(Image.open(path).convert("RGBA"), (x * tile, y * tile))
    return canvas


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--zoom", type=int, default=3, help="tile zoom to stitch (3 = 16 m/px)")
    args = ap.parse_args()
    cfg = json.loads((SRC / "config.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    cols, rows = (cfg["right"] - cfg["left"]) / CTX_RES, (cfg["top"] - cfg["bottom"]) / CTX_RES
    entries = []
    for layer in cfg["layers"]:
        if layer["id"] not in TITLES:
            continue
        zoom = min(args.zoom, layer["maxzoom"])
        image = stitch(layer, zoom, cfg)
        lossless = layer.get("kind") == "categorical"
        image.save(OUT / f"{layer['id']}.webp", "WEBP", lossless=lossless, quality=82, method=6)
        title, group, subtitle = TITLES[layer["id"]]
        entries.append(dict(id=layer["id"], title=title, group=group, subtitle=subtitle, kind=layer.get("kind"),
                            url=f"/layers/thematic/{layer['id']}.webp", coverage=layer.get("coverage"),
                            observed=layer.get("observed"), legend=layer.get("legend") or {},
                            bounds=[[-rows, 0], [0, cols]]))
        print(f"{layer['id']}: {image.size[0]}x{image.size[1]} z{zoom}")
    (OUT / "layers.json").write_text(json.dumps(entries, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
