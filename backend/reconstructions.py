"""Adapter for the MARPS_Jezero_3D package (without downloading or copying its binaries)."""
import csv
import json
import math
from pathlib import Path

RADIUS = 3396190.0
ROOT = Path(__file__).resolve().parents[1]
BUNDLED_DATASET = ROOT / "data/jezero/reconstructions"
LEGACY_DATASET = ROOT / "MARPS_Jezero_3D_datos/MARPS_Jezero_3D"
# Keep existing installations; a fresh clone includes the lightweight metadata.
DEFAULT_DATASET = LEGACY_DATASET if (LEGACY_DATASET / "catalogos/modelos_curados.csv").is_file() else BUNDLED_DATASET


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def mesh_anchor(dataset):
    # The public waypoints do not include every RMC. Prefer the corrected localization.
    for filename in ("PLACES_best_interp.csv", "PLACES_telemetry.csv"):
        path = dataset / "geografia" / filename
        if path.exists():
            with path.open(encoding="utf-8-sig", newline="") as stream:
                row = next((row for row in csv.DictReader(stream)
                            if row.get("frame") == "ROVER" and row.get("site") == "6" and row.get("drive") == "2684"), None)
            if row:
                return [float(row["longitude"]), float(row["planetocentric_latitude"])], filename
    path = dataset / "geografia/perseverance_waypoints_mars.geojson"
    if path.exists():
        waypoint = next((f for f in read_json(path)["features"]
                         if f["properties"].get("site") == 6 and f["properties"].get("drive") == 2684), None)
        if waypoint:
            return waypoint["geometry"]["coordinates"][:2], "NASA MMGIS"
    return None, "Sin localización RMC verificada"


def build_catalog(dataset=DEFAULT_DATASET):
    dataset = Path(dataset)
    scenes = []
    warnings = []
    catalog = dataset / "catalogos/modelos_curados.csv"
    if catalog.exists():
        with catalog.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                coords = None
                try:
                    lon, lat = float(row["anchor_lon"]), float(row["anchor_lat"])
                    if math.isfinite(lon) and math.isfinite(lat) and 0 <= lon <= 360 and -90 <= lat <= 90:
                        coords = [lon, lat]
                except (ValueError, KeyError):
                    pass
                kind = row.get("kind", "")
                scenes.append(dict(
                    id=row["uid"], title=row["name"], author=row["author"],
                    kind="detail" if "detalle" in kind else "aerial" if "aére" in kind else "landscape",
                    category=kind, renderer="sketchfab", coordinates=coords,
                    anchor=row.get("anchor_type", "Sin ubicación verificada"),
                    sol=int(row["sol_in_title"]) if row.get("sol_in_title", "").isdigit() else None,
                    license=row.get("license") or "No informada", source=row["url"],
                    description=row.get("description", ""), available=True,
                ))
    else:
        warnings.append("No se encontró el catálogo. Ejecuta python3 backend/prepare_reconstructions.py --dataset \""
                        + str(dataset) + "\" o indica la carpeta extraída con --dataset.")

    manifest = dataset / "cheyava_falls/scene_original.json"
    if manifest.exists():
        original = read_json(manifest)
        origin = original["site_origin_map"]
        k = 180 / (math.pi * RADIUS)
        scenes.insert(0, dict(
            id="cheyava-falls", title="Cheyava Falls · Neretva Vallis", author="Planetary Scene Studio",
            kind="landscape", category="Gaussian Splatting local", renderer="spz",
            coordinates=[origin["x"] * k, origin["y"] * k],
            anchor="Origen de la escena publicado por sus autores; no es la posición exacta de la roca.",
            sol=1195, solEnd=1210, license="Redistribución pendiente de confirmar con los autores",
            source="https://github.com/Matusvec/spaceX-Mhacks-Challenge",
            description="241 imágenes de Perseverance, 972.047 gaussianas. Entorno parcial de radio 9 m; hay huecos y menor nitidez fuera de las vistas originales. Altura de ojos aproximada, sin colisiones físicas.",
            available=(manifest.parent / "splat.spz").is_file(),
            asset="/reconstructions/files/cheyava_falls/splat.spz",
            # The SPZ is already in the site frame (+Z up); do not reapply train_to_site_shift.
            frame="site-z-up", radius=original["splat"]["crop_radius_m"],
            eye=[0, 1.65, 3.8], target=[-2.56, 0.1, 0.58],
        ))

    mesh_dir = dataset / "ejemplo_malla_NASA"
    obj = next(mesh_dir.glob("*.obj"), None)
    if obj is None:
        # The PDS label is versioned so its POI exists before the heavy OBJ download.
        label = next(mesh_dir.glob("*.obj.xml"), None)
        obj = label.with_suffix("") if label else None
    if obj:
        coords, anchor_source = mesh_anchor(dataset)
        scenes.insert(1 if manifest.exists() else 0, dict(
                id="nasa-navcam-sol180", title="Citadelle · Navcam NASA · sol 180", author="NASA/JPL-Caltech",
                kind="landscape", category="Malla estéreo local", renderer="obj",
                coordinates=coords,
                anchor=f"{anchor_source}: posición del rover, site 6, drive 2684; no huella de la malla.",
                sol=180, license="NASA/PDS · consultar la procedencia del producto",
                source="https://pds.nasa.gov/ds-view/pds/viewCollection.jsp?identifier=urn:nasa:pds:mars2020_navcam_ops_mesh:data",
                description="Malla estéreo texturizada parcial. Marco NASA SITE_FRAME (+X norte, +Y este, +Z abajo). Vista inicial sobre la superficie; sin continuidad ni colisiones garantizadas.",
                available=obj.is_file() and obj.with_suffix(".png").is_file(), asset=f"/reconstructions/files/ejemplo_malla_NASA/{obj.name}",
                texture=f"/reconstructions/files/ejemplo_malla_NASA/{obj.stem}.png",
                frame="nasa-ned", radius=20,
        ))

    if any(not scene["available"] for scene in scenes if scene["renderer"] != "sketchfab"):
        warnings.append("Faltan archivos de reconstrucciones locales. Ejecuta python3 backend/prepare_reconstructions.py"
                        + ("" if dataset.resolve() == DEFAULT_DATASET.resolve() else ' --dataset "' + str(dataset) + '"')
                        + ". Comprueba la instalación con --check.")

    return dict(version=1, body="Mars", radius=RADIUS, scenes=scenes, warnings=warnings,
                counts=dict(total=len(scenes), placed=sum(s["coordinates"] is not None for s in scenes),
                            local=sum(s["renderer"] != "sketchfab" for s in scenes)))


def build_route(dataset=DEFAULT_DATASET):
    path = Path(dataset) / "geografia/perseverance_waypoints_mars.geojson"
    features = read_json(path)["features"] if path.exists() else []
    return dict(type="Feature", properties=dict(body="Mars", source="NASA MMGIS · Perseverance"),
                geometry=dict(type="LineString", coordinates=[f["geometry"]["coordinates"][:2] for f in features]))
