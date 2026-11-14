"""Descarga bibliotecas web fijadas por versión y SHA-256 (sólo biblioteca estándar).

Uso: python3 backend/prepare_viewer.py [--check]
"""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path(__file__).with_name("viewer_dependencies.json")
VENDOR = ROOT / "platform/viewer/vendor"


def valid(path, digest):
    return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest


def prepare(check=False):
    missing = []
    for item in json.loads(MANIFEST.read_text()):
        path = VENDOR / item["path"]
        if valid(path, item["sha256"]):
            continue
        if check:
            missing.append(item["path"])
            continue
        print(f"Descargando {item['path']}…", flush=True)
        with urlopen(item["url"], timeout=60) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise ValueError(f"SHA-256 inesperado: {item['path']}. No se ha instalado.")
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(data)
        temporary.replace(path)
    if missing:
        raise SystemExit("Faltan bibliotecas o su hash no coincide: " + ", ".join(missing) + ". Ejecuta python3 backend/prepare_viewer.py")
    print("Bibliotecas del visor verificadas.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verificar sin usar la red")
    args = parser.parse_args()
    prepare(args.check)
