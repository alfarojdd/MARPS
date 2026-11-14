"""Catalog and file-mount contracts, without network or heavy data."""
import csv
import json
import math
import tempfile
import unittest
from pathlib import Path

from reconstructions import RADIUS, build_catalog, build_route, mesh_anchor
from viewer import ROOT, ViewerHandler, map_config


class ReconstructionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dataset = Path(self.temp.name)

    def write_json(self, name, value):
        path = self.dataset / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))

    def write_csv(self, name, fields, rows):
        path = self.dataset / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def test_catalog_preserves_unlocated_and_detail_models(self):
        fields = ["uid", "name", "author", "kind", "anchor_lon", "anchor_lat", "sol_in_title", "license", "url"]
        common = dict(author="NASA", license="CC Attribution", url="https://sketchfab.com/3d-models/example")
        rows = [dict(common, uid="terrain", name="Terreno", kind="escena/afloramiento", anchor_lon="77.3", anchor_lat="18.4", sol_in_title="180"),
                dict(common, uid="rock", name="Roca", kind="detalle de roca/abrasión", anchor_lon="", anchor_lat="", sol_in_title=""),
                dict(common, uid="invalid", name="Sin ancla", kind="escena/afloramiento", anchor_lon="nan", anchor_lat="18", sol_in_title="")]
        self.write_csv("catalogos/modelos_curados.csv", fields, rows)
        result = build_catalog(self.dataset)
        self.assertEqual(result["counts"], dict(total=3, placed=1, local=0))
        self.assertEqual(result["scenes"][0]["coordinates"], [77.3, 18.4])
        self.assertEqual(result["scenes"][1]["kind"], "detail")
        self.assertIsNone(result["scenes"][1]["coordinates"])
        self.assertIsNone(result["scenes"][2]["coordinates"])

    def test_splat_uses_published_mars_origin_and_reports_missing_binary(self):
        k = math.pi * RADIUS / 180
        self.write_json("cheyava_falls/scene_original.json", dict(site_origin_map=dict(x=77.3*k, y=18.5*k, z=-2000), splat=dict(crop_radius_m=9)))
        scene = build_catalog(self.dataset)["scenes"][0]
        self.assertAlmostEqual(scene["coordinates"][0], 77.3)
        self.assertAlmostEqual(scene["coordinates"][1], 18.5)
        self.assertFalse(scene["available"])
        (self.dataset / "cheyava_falls/splat.spz").touch()
        self.assertTrue(build_catalog(self.dataset)["scenes"][0]["available"])

    def test_nasa_anchor_uses_corrected_rmc_before_telemetry(self):
        fields = ["frame", "site", "drive", "longitude", "planetocentric_latitude"]
        row = dict(frame="ROVER", site="6", drive="2684", longitude="77.444311622", planetocentric_latitude="18.430825802")
        self.write_csv("geografia/PLACES_best_interp.csv", fields, [dict(row, drive="2666"), row])
        self.write_csv("geografia/PLACES_telemetry.csv", fields, [dict(row, longitude="77.444426956")])
        coords, source = mesh_anchor(self.dataset)
        self.assertEqual(source, "PLACES_best_interp.csv")
        self.assertEqual(coords, [77.444311622, 18.430825802])
        self.assertEqual(mesh_anchor(self.dataset / "absent")[0], None)

    def test_missing_dataset_is_actionable(self):
        result = build_catalog(self.dataset)
        self.assertEqual(result["counts"]["total"], 0)
        self.assertIn("--dataset", result["warnings"][0])

    def test_traverse_keeps_martian_lonlat_without_terrestrial_projection(self):
        points = [[77.3, 18.4, -2500], [77.31, 18.41, -2501]]
        self.write_json("geografia/perseverance_waypoints_mars.geojson", dict(features=[dict(geometry=dict(coordinates=p)) for p in points]))
        self.assertEqual(build_route(self.dataset)["geometry"]["coordinates"], [p[:2] for p in points])

    def test_mounts_do_not_allow_parent_or_encoded_path_escape(self):
        handler = object.__new__(ViewerHandler)
        handler.dataset = self.dataset
        handler.directory = str(ROOT / "platform/viewer")
        good = handler.translate_path("/reconstructions/files/cheyava_falls/splat.spz")
        self.assertEqual(good, str(self.dataset / "cheyava_falls/splat.spz"))
        for path in ["/reconstructions/files/cheyava_falls/../../secret", "/reconstructions/files/cheyava_falls/%2e%2e/secret", "/assets/ctx/%2e%2e/secret"]:
            self.assertEqual(Path(handler.translate_path(path)).name, "__missing__")

    def test_ctx_fallback_agrees_with_raster_bounds(self):
        cfg = map_config()
        if "ctx" not in cfg:
            self.skipTest("Hay capas generadas: el visor usa su configuración")
        self.assertEqual(cfg["radius"], RADIUS)
        self.assertAlmostEqual(cfg["left"], 4573663.250853, places=4)
        self.assertAlmostEqual(cfg["top"], 1109693.140188, places=4)


if __name__ == "__main__":
    unittest.main()
