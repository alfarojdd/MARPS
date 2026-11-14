# Progress log

One entry per work session, most recent first. Format: date, area, what was done, decisions made, blockers.

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

## Pending decisions
- [x] Mars area: Jezero
- [x] Specific layers and sources: see [JEZERO_LAYERS.md](JEZERO_LAYERS.md) (the planner still has to choose which ones it uses)
- [ ] Final format of the layers, the weights JSON and the route
- [ ] Local LLM model and runtime
- [ ] Web map framework
- [ ] Repository license
- [ ] Owner of each area (fill in [CONTRIBUTING.md](../CONTRIBUTING.md))
