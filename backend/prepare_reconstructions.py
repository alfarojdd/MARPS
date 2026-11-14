"""Install the two local surface models from their original public sources.

Usage: python3 backend/prepare_reconstructions.py [--check] [--dataset PATH]
Only the Python standard library is required. Heavy files stay outside Git.
"""
import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from urllib.request import urlopen

from reconstructions import BUNDLED_DATASET, DEFAULT_DATASET, build_catalog

MANIFEST = Path(__file__).with_name("reconstruction_assets.json")
METADATA = (
    "catalogos/modelos_curados.csv",
    "cheyava_falls/scene_original.json",
    "geografia/PLACES_best_interp.csv",
    "geografia/perseverance_waypoints_mars.geojson",
)


def valid(path, item):
    if not path.is_file() or path.stat().st_size != item["bytes"]:
        return False
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest() == item["sha256"]


def download(item, path):
    """Verify before replacement; a failed transfer never damages an existing file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".download", delete=False) as out:
            temporary = Path(out.name)
            with urlopen(item["url"], timeout=60) as response:
                shutil.copyfileobj(response, out, length=1024 * 1024)
        if not valid(temporary, item):
            raise ValueError(f"Tamaño o SHA-256 inesperado: {item['path']}; no se ha instalado")
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def prepare(dataset=DEFAULT_DATASET, check=False):
    dataset = Path(dataset).resolve()
    missing = []
    # Copy only missing metadata for a custom/legacy destination. Keep local edits.
    metadata = [BUNDLED_DATASET / name for name in METADATA]
    metadata.extend(sorted((BUNDLED_DATASET / "ejemplo_malla_NASA").glob("*.obj.xml")))
    for source in metadata:
        path = dataset / source.relative_to(BUNDLED_DATASET)
        if not path.is_file():
            if check:
                missing.append(str(source.relative_to(BUNDLED_DATASET)))
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, path)

    for item in json.loads(MANIFEST.read_text(encoding="utf-8")):
        path = (dataset / item["path"]).resolve()
        if not path.is_relative_to(dataset):
            raise ValueError(f"Ruta fuera del dataset: {item['path']}")
        if valid(path, item):
            continue
        if check:
            missing.append(item["path"])
            continue
        print(f"Descargando {item['path']} ({item['bytes'] / 1e6:.1f} MB)…", flush=True)
        download(item, path)
    if missing:
        raise ValueError("Faltan archivos o su hash no coincide:\n  " + "\n  ".join(missing)
                         + "\nEjecuta python3 backend/prepare_reconstructions.py con el mismo --dataset.")
    catalog = build_catalog(dataset)
    counts = catalog["counts"]
    print(f"Reconstrucciones verificadas en {dataset}: {counts['total']} entradas, "
          f"{counts['placed']} puntos, {counts['local']} modelos locales.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--check", action="store_true", help="Verify local files without downloading or writing")
    args = parser.parse_args()
    try:
        prepare(args.dataset, args.check)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")
