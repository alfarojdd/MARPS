# Architecture and contracts between areas

**Status: draft for discussion.** What matters is that the three areas agree on these three formats early so they can work in parallel. Whoever changes one must update this file in the same PR.

```
 Layers (data/) ────────────────────────────┐
                                            ▼
 Mission text ─► LLM (llm/) ─► [B] JSON ─► Planner (planner/) ─► [C] Route ─► Interface (platform/)
                                            ▲
                                    [A] layer grid
```

## [A] Map layers: `data/` → `planner/` and `platform/`

All layers of an area share **the same grid**: same coordinate system, same resolution and same dimensions. That way the planner can combine them cell by cell.

Initial proposal:
- Format: GeoTIFF (one band per layer) or NumPy `.npy` arrays with a `metadata.json` alongside.
- `metadata.json` per area: area name, CRS, resolution (m/pixel), origin corner, size (rows × columns), and per layer: name, unit, "no data" value and source.
- Standard layer names: `elevation`, `slope`, `roughness`, `thermal_inertia`, `mineralogy_<objetivo>`, `geology`, `radiation`, `rock_abundance`.
- Values normalised to 0-1 in a separate version for the planner (`*_norm`), keeping the physical values for display in the interface.

**Status (2026-11-14):** Jezero area and 20 m grid decided. The layers are published as a single multiband GeoTIFF in `data/jezero/stack/` with `layers.json` (see [JEZERO_LAYERS.md](JEZERO_LAYERS.md)). The band names are the actual ones (`elev_ctx`, `slope_ctx`, `tri_ctx`, `thermal_inertia`, ...), not the standard names proposed above; there is no mineralogy, radiation or rock abundance in the base. 0-1 normalisation and per-area `metadata.json`: not done.

Decisions to make: area (Gale/Mount Sharp or Jezero), resolution (HiRISE is much finer than CTX/MOLA) and which layers arrive in time.

## [B] Mission parameters: `llm/` → `planner/`

**Status (2026-11-14): agreed and implemented** in `planner/api.py` (`POST /plan-route`). The input has two blocks: `mission`, filled in by the LLM (the 5 current fields of `backend/llm/api.py` plus `safety`, `science_targets`, `science_detour` and `return_to_origin`), and `system` (local solar time and battery, set by the vehicle). Exact contract in [PLANNER_INTEGRATION.md](PLANNER_INTEGRATION.md). The initial proposal below is kept for reference.

The LLM converts the mission text into this JSON. **It is validated against a schema**; if validation fails, it retries or falls back to default weights. The planner never receives free text.

```json
{
  "travel_mode": "on_foot",
  "payload_kg": 15,
  "max_duration_min": 240,
  "hard_constraints": {
    "max_slope_deg": 15,
    "avoid_high_roughness": true
  },
  "weights": {
    "distance": 1.0,
    "slope": 2.0,
    "roughness": 1.5,
    "radiation_exposure": 3.0,
    "science_interest": 2.5
  },
  "science_targets": ["clays", "phyllosilicates"],
  "waypoints": []
}
```

- `travel_mode`: `on_foot` or `rover`.
- `hard_constraints`: cells that become **forbidden** (the planner treats them as impassable).
- `weights`: relative weights, greater than or equal to 0. The planner normalises them.
- `science_targets`: what to look for; the planner cross-references it with the mineralogy or geology layer.
- The model **only translates**; the default safety limits (for example, absolute maximum slope) are enforced by the planner even if the LLM does not mention them.

Per-cell cost idea: `coste = Σ peso_i · capa_i  −  peso_interés · afinidad(celda, objetivos)`, always kept positive so that A* remains valid.

## [C] Route: `planner/` → `platform/`

**Status (2026-11-14): implemented.** The `POST /plan-route` response has three parts: `report` (metrics, comparison with a classic A*, light and battery warnings, charging stop and `why`, for the LLM summary and the panel), `geojson` (route, classic A* and stops in planetocentric lon/lat) and `ctx_px` (the lines in pixels of the 6 m CTX basemap for Leaflet `CRS.Simple`). Details in [PLANNER_INTEGRATION.md](PLANNER_INTEGRATION.md). The initial proposal below is kept for reference.

```json
{
  "path": [[x0, y0], [x1, y1]],
  "waypoints_visited": [],
  "metrics": {
    "distance_m": 0,
    "elevation_gain_m": 0,
    "max_slope_deg": 0,
    "est_duration_min": 0,
    "radiation_exposure": 0,
    "science_points_passed": []
  },
  "explanation": "short text on why this route was chosen",
  "feasible": true
}
```

- `path`: list of coordinates on the [A] grid (or lon/lat; decide and fix it here).
- `feasible: false` with a reason when the hard constraints make the destination unreachable.

## Tentative stack

| Component | Proposal | Status |
|---|---|---|
| Planner | Python + NumPy + Numba; A* over the 20 m grid, shadows with `mars_shadows.py` | done (`planner/`) |
| API | FastAPI | to be confirmed |
| Local LLM | Ollama or llama.cpp with JSON output and validation (Pydantic / JSON Schema) | to be confirmed |
| Interface | Web map (Leaflet, OpenLayers or deck.gl) | to be confirmed |

Each area records here what it chose and why.

## [D] Surface reconstructions → viewer

Local implementation in `backend/viewer.py` and `backend/reconstructions.py`, using the Python standard library. It does not depend on the LLM API. Startup and setup: [viewer](../platform/viewer/README.md).

- `GET /api/map-config`: pipeline configuration if it exists; otherwise, CTX background with the versioned tiles.
- `GET /api/reconstructions`: `{version:1, body:"Mars", radius:3396190, counts, warnings, scenes}`. Each scene includes `id`, `title`, `author`, `kind` (`landscape`, `detail`, `aerial`), `renderer` (`spz`, `obj`, `sketchfab`), `coordinates` (`[lon_E, lat_planetocéntrica]` or `null`), `anchor`, `sol`, `license`, `source` and `available`. Local scenes add `asset`, `frame` and `radius`; the OBJ scene adds `texture`.
- `GET /api/traverse`: a GeoJSON line with **Mars** coordinates, for context display only.
- `/assets/ctx/…`: orbital tiles from the repository. `/reconstructions/files/cheyava_falls/…` and `/reconstructions/files/ejemplo_malla_NASA/…`: local files from the package configured with `--dataset`.

The map projects the anchors with the same Martian equirectangular projection as [A]. Opening a scene keeps the map state in a dialog; closing it destroys its iframe and releases the WebGL viewer. Models without a location never receive invented coordinates. The local camera uses an estimated ground and limited movement, with no guaranteed collision handling or continuous coverage.
