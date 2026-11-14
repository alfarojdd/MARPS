# Progress log

One entry per work session, most recent first. Format: date, area, what was done, decisions made, blockers.

## 2026-11-14: reconstruction points in the existing route map (platform)
- Integrated surface-reconstruction POIs into both `platform/viewer/index.html` and the existing floating-card `terrain3d/demo.html`, retaining the orange trajectory, dashed blue classic A*, stop colours, tilt/exaggeration controls and elevation profile. Both now share `route-view.mjs` and `reconstructions.mjs`.
- The 94 located catalogue entries appear as Leaflet markers and projected buttons above the selected relief. Catalogue positioning works in either map mode. Surface modals use the same local/external viewers and preserve the route, tilted camera and exaggeration; the terrain render loop and clock pause while a modal is open.
- Prepared the official 20 m USGS CTX DTM (9.7 MB) and generated an 800 × 758 browser relief. Also converted the root `trekSTL.stl` supplied by the user: 400 × 400 XY grid, fit `fliplr`, correlation 0.9784, 8.6801 m/unit, offset −422.49 m, RMSE 55.31 m; cropped output 374 × 381. These fit parameters apply to this file and supersede the earlier export's scaling for current use. Sources and hashes: [DATA_SOURCES.md](DATA_SOURCES.md).
- Added explicit `--dtm` / `--ortho` converter inputs and a `/api/terrain-sources` inventory listing complete local bundles, DTM first. Missing relief and WebGL failure leave the 2D trajectory and reconstruction catalogue available. The five Three.js line addons are now versioned by URL and SHA-256 for local preparation.
- The route is still a saved planner example, not a live LLM/planner call. Future planner responses can update both route views through `setRoute` / `marps:plan-route`. The Perseverance traverse remains an optional separate context layer.
- Documented actual operation, data preparation, API contracts, approximate anchors, source licences and remaining limits in [RECONSTRUCTIONS.md](RECONSTRUCTIONS.md), [TERRAIN_3D.md](TERRAIN_3D.md), the viewer README and architecture. Reconstruction binaries, the supplied STL and generated reliefs remain outside Git.

## 2026-11-14: shadows and planner API (planner)
- Integrated `mars_shadows.py` (Pablo) with `assets/SunAngle.csv` in `planner/shadows.py`. The ephemeris is converted to local solar time (sunrise 05:48, sunset 18:12) and direct light with cast shadows and self-shadowing is computed for 26 instants (cached).
- Light feeds into solar charging while moving, into a shadow risk term (higher with `power` or with crew) and into the **charging stop**: the chosen site is the one that finishes charging soonest under real light, avoiding shadow. The light window used in the warnings comes from the CSV.
- New metrics: `shadow_km`, `night_km` and `shadow_km_avoided`. Finding: during the day there are almost no shadows on the crater floor; they matter at sunrise and sunset and next to the rim and the delta.
- `planner/api.py`: `POST /plan-route` (FastAPI) with `{mission, system}` → `{report, geojson, ctx_px}`, plus `GET /places`. Accepts the LLM's place names ("Octavia E. Butler Landing", "Belva crater") and coordinates ("18.44N, 77.45E").
- Backend and frontend contract in [PLANNER_INTEGRATION.md](PLANNER_INTEGRATION.md); updated [B] and [C] in `ARCHITECTURE.md`.
- Pending for integration: extend the LLM schema (`backend/llm/api.py` and `Modelfile`) with `safety`, `science_targets`, `science_detour` and `return_to_origin`, and unify place names.

## 2026-11-14: mission-aware A* planner (planner)
- Pushed `planner/`: A* over the 20 m grid with 16 neighbours and a direction-dependent edge cost (uphill, downhill, cross slope), energy, risk (roughness, soft ground from thermal inertia, SIM 3464 dunes, unknown data, exposure) and hard constraints that the JSON cannot relax. Admissible heuristic with a climb bound. Details in [PLANNER.md](PLANNER.md).
- Mission parameters: the 5 from the LLM (`human`, `origin`, `destination`, `power`, `route_preference`) plus `safety`, `science_targets`, `science_detour` and `return_to_origin`. The vehicle state (time and battery) arrives separately in `system`.
- `report.py` generates the JSON for the helmet LLM's summary: comparison against a classic pure-distance A*, `why`, light and battery warnings, and solar charging stop.
- `live.py`: interactive test bench (not the frontend).
- Built as a spike (quick prototype), with 10 tests.

## 2026-11-14: Jezero layers (data)
- Pushed `data/jezero/`: 14-layer stack at 20 m on the same grid (CTX/HRSC elevation, slope, roughness, TPI, aspect, hillshade, thermal inertia, THEMIS day/night, insolation, atmospheric column proxy, distance to the traverse), vectors and the pipeline with tests. Details in [JEZERO_LAYERS.md](JEZERO_LAYERS.md).
- Pushed the layer viewer in `platform/viewer/` (tiles are generated with the pipeline).
- Rule: the base only includes layers that cover 100 % of the bounding box; the only exception is the Jezero thermal inertia (96.1 %).
- No metre-scale slope or mineralogy in the base: HiRISE and CRISM only cover the centre (32-41 %). They are documented as discarded.
- The stack weighs 90 MB: do not regenerate or re-push it for small changes (every version stays in the history).
- Area decided: Jezero.

## 2026-11-14: repository organisation
- Structure by area (`platform/`, `llm/`, `planner/`, `data/`, `docs/`) and area branches.
- Draft of the three contracts between areas in [ARCHITECTURE.md](ARCHITECTURE.md).

## 2026-11-14 (afternoon): maps without the traverse
- Removed the Perseverance traverse: `dist_traverse` layer, traverse vectors and waypoints, and the landing ellipse. 13-band base stack.
- Pending decision: rewrite the history of `main` to remove the traverse from earlier commits (328d796). Not done.

## 2026-11-14 (afternoon): 3D view of the route over the relief
- Demo of a **3D** button: the map tilts, the relief is exaggerated and the planner's route is drawn on top, with an elevation profile. Details and integration steps in [TERRAIN_3D.md](TERRAIN_3D.md).
- Mars Trek STL (400 × 400 grid, no georeference) georeferenced by correlation with the CTX DTM: horizontal mirror, r = 0.978, 29.04 m per unit, RMSE 55 m. Converted to a float32 heightmap + CTX texture with `data/jezero/pipeline/build_terrain3d.py`. The same format can be made from the CTX DTM.
- Module `platform/viewer/terrain3d/terrain3d.mjs` and demo `platform/viewer/terrain3d/demo.html`, with a real `/plan-route` response.
- Follow-up completed in the reconstruction-point integration above: vendored line addons, DTM default, shared route controls in the main map and reconstruction points on both relief sources. This earlier export's 29.04 m/unit fit is historical, not the fit of the currently supplied root STL.

## Pending decisions
- [x] Mars area: Jezero
- [x] Specific layers and sources: see [JEZERO_LAYERS.md](JEZERO_LAYERS.md) (the planner still has to choose which ones it uses)
- [ ] Final format of the layers, the weights JSON and the route
- [ ] Local LLM model and runtime
- [ ] Web map framework
- [ ] Repository license
- [ ] Owner of each area (fill in [CONTRIBUTING.md](../CONTRIBUTING.md))
