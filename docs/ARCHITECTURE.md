# Architecture

MARPS has four parts that exchange three well-defined data formats.

```
                       ┌────────────────────── backend/app.py (FastAPI, one port) ───────────────────────┐
 Mission text ───────► │ /api/parse-mission ─► SLM "extractor"  ─► mission JSON  [B]                       │
 (React interface)     │                                              │                                    │
                       │ /api/plan-route ◄────────────────────────────┘                                    │
                       │     planner (A*) ◄── layers [A] (data/jezero)        ─► route + report [C]        │
 Route on 2D / 3D ◄─── │ /api/summarize-route ─► facts ─► SLM "summariser" ─► briefing                      │
                       │ /api/reconstructions, /api/terrain-sources, static files [D][E]                   │
                       └──────────────────────────────────────────────────────────────────────────────────┘
```

| Part | Directory | Role |
|---|---|---|
| Interface | `platform/web` (React, Leaflet) and `platform/viewer` (Three.js engine) | Map, layers, mission panel, telemetry, 3D relief, surface reconstructions |
| Server | `backend/app.py` | Joins interface, planner and SLMs behind one port; serves the interface and the data it needs |
| SLMs | `backend/slm` | Two Gemma 4 E2B models served by Ollama: mission extractor and route summariser |
| Planner | `planner` | Deterministic A* over the 20 m grid, with a cost that depends on the mission and the vehicle state |
| Data | `data` | Pipeline that builds the layers from public NASA/USGS products |

The language models never plan: they only translate text into parameters and verified figures into a briefing.

## [A] Map layers: `data/` → `planner/` and `platform/`

All layers share **one grid**: Mars 2000 sphere (R = 3 396 190 m), equirectangular projection, 20 m per pixel, 1596 × 1512 cells covering 77.160–77.699 °E and 18.211–18.721 °N.

- `data/jezero/stack/jezero_stack_20m.tif`: 13 float32 bands (NaN = no data) with `layers.json` describing each band (unit, description). All bands cover 100 % of the area except `thermal_inertia` (96.1 %), which is treated as unknown where missing.
- `data/jezero/extra/`: `geo_unit.tif` (geologic units) and `crism_class.tif` (mineralogy, central 41 % only), used by the planner for science targets.
- Band names: `elev_ctx`, `slope_ctx`, `tri_ctx`, `tpi_ctx_500m`, `aspect_ctx`, `thermal_inertia`, `insolation_rel`, `atm_column_pct`...

Layer catalogue, sources and caveats: [JEZERO_LAYERS.md](JEZERO_LAYERS.md). The web interface uses an image per layer exported with `data/jezero/pipeline/export_web_layers.py` (`platform/web/public/layers/thematic`).

## [B] Mission parameters: SLM → planner

The extractor model fills the `mission` block of `POST /plan-route`; the vehicle fills the `system` block.

```json
{
  "mission": { "human": true, "origin": "landing_site", "destination": "delta_top",
               "power": true, "route_preference": null, "safety": "normal",
               "science_targets": [{"target": "carbonates", "priority": 1.0}],
               "science_detour": "medium", "return_to_origin": false },
  "system":  { "start_hour": 9.0, "battery_kwh": 24, "battery_capacity_kwh": 40, "reserve_pct": 20 }
}
```

The SLM output is constrained by a JSON schema and validated with Pydantic (`backend/slm/mission.py`). The planner validates it again and rejects unknown values (422) or unknown places (400) with the reason. Field semantics and examples: [PLANNER_INTEGRATION.md](PLANNER_INTEGRATION.md).

## [C] Route: planner → interface

The `/plan-route` response has three parts:

- `report`: metrics, comparison with a classic shortest-path A*, daylight and battery warnings, charging stop and the reasons behind the route (`why`).
- `geojson`: route, classic A*, origin, destination and stops in planetocentric lon/lat (consumed by the 3D view).
- `ctx_px`: the same lines in pixels of the 6 m CTX mosaic, for the 2D Leaflet map (`L.CRS.Simple`).

The summariser model receives a distilled list of facts from `report` (see [backend/slm/README.md](../backend/slm/README.md)) and returns one or two sentences.

## [D] Surface reconstructions

`GET /api/reconstructions` returns the catalogue of 3D surface reconstructions (Perseverance imagery): `{version, body, radius, counts, warnings, scenes}`. Each scene has `id`, `title`, `author`, `kind` (`landscape`, `detail`, `aerial`), `renderer` (`spz`, `obj`, `sketchfab`), `coordinates` (`[lon_E, lat]` or `null`), `anchor`, `sol`, `license`, `source` and `available`. Locations are approximate rover or scene anchors; entries without a verified location stay in the catalogue but are never placed on the map. Two scenes are local (Gaussian-splat Cheyava Falls and a NASA Navcam mesh) and the rest are embedded from Sketchfab. Details and limitations: [RECONSTRUCTIONS.md](RECONSTRUCTIONS.md).

## [E] 3D relief

The 3D view loads a height grid generated from the CTX DTM (or the Mars Trek STL) and renders it with Three.js (`platform/viewer/terrain3d/terrain3d.mjs`). The route is drawn over the relief, the selected basemap and data layer are composited into its texture, and the surface-reconstruction anchors are projected on it as buttons. Data preparation and rendering details: [TERRAIN_3D.md](TERRAIN_3D.md).

## Server endpoints

| Endpoint | Purpose |
|---|---|
| `POST /api/parse-mission` | Mission text → mission JSON (extractor SLM) |
| `POST /api/plan-route` | `{mission, system}` → `{report, geojson, ctx_px}` |
| `POST /api/summarize-route` | `{report}` → `{summary}` (summariser SLM) |
| `GET /api/places` | Named places the planner understands |
| `GET /api/slm/health`, `GET /api/planner/health` | Service status |
| `GET /api/reconstructions`, `/api/traverse` | Surface-reconstruction catalogue and Perseverance traverse |
| `GET /api/terrain-sources` | Available 3D relief models |

The same planner and SLM endpoints are also served without the `/api` prefix. Interactive API documentation is disabled because the server may be exposed publicly.

## Technology choices

| Component | Choice | Why |
|---|---|---|
| Planner | Python, NumPy, Numba | A* over 2.4 million cells with 16-neighbour connectivity in 1–6 s |
| SLM runtime | Ollama with Gemma 4 E2B | Runs on a 6 GB GPU, constrained JSON output, easy local deployment |
| Server | FastAPI | Pydantic validation shared by the planner and the SLM client |
| Interface | React, Leaflet, Three.js | CRS.Simple map over the CTX mosaic and a WebGL relief with the same data |
| Hosting | Vercel (interface) and a local host (planner and SLMs) | See [DEPLOY.md](DEPLOY.md) |
