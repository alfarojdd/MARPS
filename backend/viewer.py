"""Local server for the map and the reconstructions. Standard library only.

Run: python3 backend/viewer.py [--port 8765] [--dataset /path/to/MARPS_Jezero_3D]
"""
import argparse
import json
import mimetypes
import math
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from reconstructions import DEFAULT_DATASET, RADIUS, build_catalog, build_route, read_json

ROOT = Path(__file__).resolve().parents[1]
mimetypes.add_type("text/javascript", ".mjs")
mimetypes.add_type("application/octet-stream", ".spz")


def map_config():
    generated = ROOT / "platform/viewer/data/config.json"
    if generated.is_file():
        return read_json(generated)
    ctx = read_json(ROOT / "assets/zones/public/layers/ctx/meta.json")
    b, k = ctx["bounds_lonlat"], math.pi * RADIUS / 180
    return dict(left=b["west"] * k, right=b["east"] * k, bottom=b["south"] * k, top=b["north"] * k,
                radius=RADIUS, res0=128, tile=256, ctx=ctx, probe=None,
                layers=[dict(id="ctx_mosaic", group="Imagery", title="CTX orthomosaic · 6 m/pixel",
                             observed=True, coverage=100, legend=dict(type="image"))])


def terrain_sources():
    """List generated reliefs; no placeholder heights or implicit downloads."""
    sources = []
    directory = ROOT / "platform/viewer/data/terrain3d"
    for name, title in (("terrain_dtm", "CTX DTM (40 m)"), ("terrain_stl", "Mars Trek STL")):
        manifest = directory / f"{name}.json"
        if not manifest.is_file():
            continue
        try:
            meta = read_json(manifest)
            files = [meta["heights"]] + ([meta["texture"]] if meta.get("texture") else [])
            if not all((directory / file).resolve().is_relative_to(directory.resolve())
                       and (directory / file).is_file() for file in files):
                continue
            sources.append(dict(id=name, title=title, url=f"/data/terrain3d/{name}.json"))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return dict(sources=sources)


class ViewerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, dataset=DEFAULT_DATASET, **kwargs):
        self.dataset = Path(dataset).resolve()
        super().__init__(*args, directory=str(ROOT / "platform/viewer"), **kwargs)

    def translate_path(self, path):
        path = unquote(urlsplit(path).path)
        mounts = {
            "/assets/ctx/": ROOT / "assets/zones/public/layers/ctx",
            "/reconstructions/files/cheyava_falls/": self.dataset / "cheyava_falls",
            "/reconstructions/files/ejemplo_malla_NASA/": self.dataset / "ejemplo_malla_NASA",
        }
        for prefix, base in mounts.items():
            if path.startswith(prefix):
                base = base.resolve()
                target = (base / path[len(prefix):]).resolve()
                if target.is_relative_to(base):
                    return str(target)
                return str(ROOT / "platform/viewer/__missing__")
        return super().translate_path(path)

    def _api(self, head=False):
        path = urlsplit(self.path).path
        if path not in ("/api/reconstructions", "/api/traverse", "/api/map-config", "/api/terrain-sources"):
            return False
        try:
            if path == "/api/map-config":
                value = map_config()
            elif path == "/api/terrain-sources":
                value = terrain_sources()
            else:
                value = build_catalog(self.dataset) if path.endswith("reconstructions") else build_route(self.dataset)
            body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        except (OSError, ValueError, KeyError) as error:
            self.send_error(500, f"Could not read the 3D package: {error}")
            return True
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if not head:
            self.wfile.write(body)
        return True

    def do_GET(self):
        if not self._api():
            super().do_GET()

    def do_HEAD(self):
        if not self._api(head=True):
            super().do_HEAD()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    args = parser.parse_args()
    catalog = build_catalog(args.dataset)
    server = ThreadingHTTPServer((args.host, args.port), partial(ViewerHandler, dataset=args.dataset))
    print(f"MARPS · http://{args.host}:{args.port} · {catalog['counts']['placed']} scenes on the map", flush=True)
    for warning in catalog["warnings"]:
        print(warning, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
