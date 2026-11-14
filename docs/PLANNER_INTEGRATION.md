# Planner integration with the backend and frontend

Contract between `planner/` (routes), `backend/` (LLM + API) and the frontend (React + Leaflet). If it changes, update this file and `ARCHITECTURE.md` in the same PR.

## Flow

```
Astronaut (text)
   │
   ▼
POST /parse-mission  (backend/llm, Ollama)         → mission  (LLM JSON)
   │
   ▼  + system (time and battery, known by the vehicle)
POST /plan-route     (planner/api.py, same FastAPI) → report + geojson + ctx_px
   │                                   │
   ▼                                   ▼
LLM: natural-language summary       Frontend: draws the route, stops and warnings
("you saved 14 % battery…")
from `report`
```

The LLM **does not plan**: it only fills in `mission` and then writes the summary from `report`. Everything numeric (savings, warnings, times) is computed by the planner.

## Requirements

| What | Details |
|---|---|
| Python | 3.10+; `pip install -r planner/requirements.txt` (numpy, scipy, numba, rasterio, matplotlib, pillow) + `fastapi` from the backend |
| Data | `data/jezero/stack/jezero_stack_20m.tif`, `data/jezero/extra/geo_unit.tif`, `data/jezero/extra/crism_class.tif` (Drive). Other path: `JEZERO_DATA` |
| Shadows | `mars_shadows.py` (repo root) and `assets/SunAngle.csv`. Other paths: `MARS_SHADOWS_DIR`, `SUN_CSV_DIR`. Without them it works the same with mean insolation and a fixed 06–18 h daylight window |
| Memory | ~2 GB (1512 × 1596 grid with 16 neighbours; cache of 4 profiles of ~150 MB) |
| Startup | The first `POST /plan-route` takes ~10 s (layers + 26 shadow maps; then cached in `data/jezero/planner_*.npz`) |
| Time per request | 1–6 s; with `science_targets` 10–17 s. Show a "computing" indicator |
| Concurrency | One computation at a time (lock). Enough for the demo |

Mounting in the backend FastAPI app:
```python
import sys; sys.path.insert(0, "planner")
from api import router as planner_router
app.include_router(planner_router)
```

## Input: `POST /plan-route`

```json
{
  "mission": { "human": true, "origin": "Octavia E. Butler Landing", "destination": "delta_top",
               "power": true, "route_preference": null, "safety": "normal",
               "science_targets": [{"target": "carbonates", "priority": 1.0}],
               "science_detour": "medium", "return_to_origin": false },
  "system":  { "start_hour": 9.0, "battery_kwh": 24, "battery_capacity_kwh": 40, "reserve_pct": 20 }
}
```
Full example: [../planner/examples/plan_route_request.json](../planner/examples/plan_route_request.json).

### `mission` (filled in by the LLM)
| Field | Type | Default | Meaning |
|---|---|---|---|
| `human` | bool | `true` | Crew on board. Raises safety to at least `normal`, adds life support (+1.5 kW), penalises exposure and shadow, and arriving at night becomes critical |
| `origin`, `destination` | str | required | Place name or coordinates (see below) |
| `power` | bool | `false` | Save energy and make use of the sun: more weight on energy, avoids shadow and, if the battery is not enough, looks for a sunny place to charge |
| `route_preference` | `"shortest"` \| `"fastest"` \| `null` | `null` | Distance, time or balanced |
| `safety` | `"low"` \| `"normal"` \| `"high"` | `"normal"` | People or fragile cargo → `high` (max slope 15°, cross slope 8°, 100 m buffer, avoids dunes, sand and no-data cells) |
| `science_targets` | list of `{target, priority}` | `[]` | What is to be investigated (next table). `priority` from 0.1 to 1 |
| `science_detour` | `"low"` \| `"medium"` \| `"high"` | `"medium"` | Detour accepted for science: +20 / +50 / +100 % cost |
| `return_to_origin` | bool | `false` | Round trip |

**Places** (listed by `GET /places`):
- Names: `landing_site` ("Octavia E. Butler Landing"), `belva_crater` ("Belva", "Belva crater rim"), `neretva_vallis`, `jezero_centre`, `delta_top`, `delta_carbonates`, `north_carbonates`, `crater_floor_south`, `western_rim` and `north_plains`. Case, spaces and parentheses are ignored.
- Coordinates: `"77.45,18.44"` or `"18.44N, 77.45E"`.
- An unknown or off-map place returns **400** with the list of valid places. The backend can ask the LLM to correct it. "Three Forks" is not there yet, because verified coordinates are missing.

**`science_targets`: options for the demo**
| `target` | What it is | Data | Where on the map |
|---|---|---|---|
| `aqueous` | Shortcut: signs of ancient water = `carbonates` + `clays` + `delta` | CRISM + SIM 3464 | Delta and lake margin |
| `carbonates` | Mg carbonates (formed in water) | CRISM classes 2 and 6 | ~48 km², mostly the western delta and margin (core at 77.364 °E, 18.546 °N) |
| `clays` | Clays / phyllosilicates (smectites, kaolinite) | CRISM 3, 4, 5, 9 and 10 | ~91 km², spread across the centre |
| `smectites` | Fe/Mg smectites only | CRISM 3, 4, 5 and 10 | Subset of `clays` |
| `kaolinite` | Kaolinite (intense aqueous alteration) | CRISM 9 | ~15 km² |
| `olivine` | Olivine (igneous rock; with smectite it indicates alteration) | CRISM 1, 4 and 5 | Crater floor |
| `pyroxene` | Pyroxene (igneous rock) | CRISM 7 and 8 | ~23 km² |
| `delta` | Delta fan sediments | SIM 3464 (Jezero fan 1 and 2) | Western delta |
| `crater_floor` | Crater floor unit | SIM 3464 (Jezero floor) | Centre and south |

CRISM only covers the **central 41 %**. For the demo, A and B should be near that area (for example, from `landing_site` or `crater_floor_south` to `delta_top`). Phrase guide for the LLM prompt: [PLANNER.md](PLANNER.md) (section "`mission` schema").

### `system` (set by the vehicle, not the LLM)
| Field | Default | Meaning |
|---|---|---|
| `start_hour` | 9.0 | Jezero local solar time (LTST, 0–24) of departure |
| `battery_kwh` | 30 | Current charge |
| `battery_capacity_kwh` | 40 | Capacity |
| `reserve_pct` | 20 | Minimum reserve on arrival |

## Output: `200 OK`

```json
{ "report": { … }, "geojson": { "type": "FeatureCollection", "features": [ … ] }, "ctx_px": { "route": [[c, r], …], "classic_astar": [[c, r], …] } }
```
Full example: [../planner/examples/plan_route_response.json](../planner/examples/plan_route_response.json).

### `report`: for the LLM summary and the frontend panel
| Block | Contents |
|---|---|
| `feasible` | `false` if there is any critical warning |
| `mission`, `system` | What was received, already validated |
| `sun` | `source`, `sunrise`, `sunset` and `daylight_limit` (LTST, from `SunAngle.csv`) |
| `route` | See details below the table |
| `classic_astar` | The same metrics for a pure-distance A*, with the same vehicle |
| `comparison` | See details below the table |
| `why` | List of `{factor, share_pct}`: which share of the cost avoided compared with the classic A* is due to each factor (`energy`, `time`, `soft`, `rough`, `cross`, `dune`, `shadow`…), plus `{factor: "on_<target>", km_gained}` |
| `warnings` | `{code, severity: "warning" \| "critical", message}` in English (see the warnings table) |
| `suggestions` | For example `SWITCH_TO_POWER_SAVING` with the resulting energy and remaining battery |

`route` details:
- **Distance and time:** `distance_km` and `time_h` / `duration_h` (Earth hours; `duration_h` includes stops and charging).
- **Schedule:** `departure` and `arrival` (LTST, "HH:MM"), `daylight_margin_h`.
- **Energy:** `energy_kwh`, `drive_kwh`, `battery_start_kwh`, `battery_end_kwh` and `battery_end_pct`.
- **Relief:** `ascent_m`, `descent_m`, `max_pitch_deg` and `max_cross_deg`.
- **Terrain:** `rough_km`, `soft_km`, `dunes_km` and `unknown_km`.
- **Light:** `shadow_km`, `shadow_pct` and `night_km`.
- **Science:** `on_<target>_km` and `science_stops` (`[{lon, lat, targets, dwell_min}]`).
- **Charging:** `charging_stop` (`{lon, lat, arrive, charge_hours, energy_needed_kwh, battery_on_arrival_kwh, mean_direct_light}` or `null`).
- **Path:** `waypoints_lonlat` (~60 points).

`comparison` details (positive = better than the classic A*):
- **Percentages:** `energy_saved_pct`, `drive_energy_saved_pct`, `time_saved_pct` and `extra_distance_pct`.
- **Slopes:** `max_pitch_reduction_deg` and `max_cross_slope_reduction_deg`.
- **Terrain avoided:** `rough_km_avoided`, `soft_km_avoided`, `dunes_km_avoided` and `shadow_km_avoided`.
- **Science:** `on_<target>_km_gained`.

**Warnings**
| `code` | Severity | When |
|---|---|---|
| `NO_ROUTE` | critical | No route meets the constraints |
| `NO_DAYLIGHT_AT_DEPARTURE` | critical | Departure at night |
| `ARRIVAL_AFTER_DAYLIGHT` | critical when crewed / warning when not | Arrival after `daylight_limit` (sunset − 30 min) |
| `BATTERY_BELOW_RESERVE` | warning | Arrival below the reserve |
| `CHARGING_STOP_REQUIRED` | warning | The battery is not enough: stop X h to charge at a sunny spot (already included in the route) |
| `CHARGING_DOES_NOT_FIT_DAYLIGHT` | critical | Even with charging, there is not enough daylight |
| `BATTERY_INSUFFICIENT` | critical | The charging spot cannot even be reached |
| `ROUTE_IN_SHADOW` | warning | When crewed, more than 15 % of the route in terrain shadow |

Example summary prompt (backend): *"You are the helmet assistant. Using only the numbers in this JSON, tell the astronaut in 3 short sentences: the route, what it saves versus a classic shortest path (comparison/why), and any warnings first if feasible is false."* + `report`.

### `geojson`: for drawing on the map
**Planetocentric lon/lat, east positive** coordinates, in the Mars 2000 system (the same as the base map `meta.json`). Each feature has `properties.kind`:
- `route`: route LineString (every 20 m cell).
- `classic_astar`: reference LineString (draw dashed).
- `origin`, `destination`: Point with `name`.
- `science_stop`: Point with `order`, `targets` and `dwell_min`.
- `charging_stop`: Point with `charge_hours` and `arrive`.

### `ctx_px`: shortcut for Leaflet `CRS.Simple`
The same lines in pixels of the 6 m CTX mosaic (`[col, row]`). The mosaic shares its north-west corner with the 20 m grid, so the conversion is exact.

## What the frontend does (React + Leaflet)

1. Sends the text to `/parse-mission` and shows the resulting `mission` so the astronaut can correct it (optional, but it builds trust).
2. Calls `/plan-route` with `mission` and `system`, and shows "computing" (1–17 s).
3. Draws with `ctx_px` on the CTX base map (`L.CRS.Simple`, `lat = -row`, `lng = col`):
   ```tsx
   const toLatLng = ([c, r]: number[]) => [-r, c] as [number, number];
   <Polyline positions={data.ctx_px.classic_astar.map(toLatLng)} pathOptions={{ dashArray: "8 6", color: "#fff" }} />
   <Polyline positions={data.ctx_px.route.map(toLatLng)} pathOptions={{ color: "#ff8a3d", weight: 4 }} />
   ```
   For points (stops, charging), use their lon/lat from `geojson`, converted to base-map pixels with `meta.json` (`col = (R·lon·π/180 − x0)/6`, `row = (y0 − R·lat·π/180)/6`), or with the team's `ctxTiles.ts` helper.
4. Panel with:
   - `feasible` and `warnings` (critical ones first, in red);
   - three or four figures from `comparison` (energy saved, cross slope reduced, sand or dune km avoided, km over the science target);
   - departure, arrival and daylight (`route.departure`, `route.arrival`, `sun`);
   - battery on arrival;
   - the charging stop, if any.
5. Shows the LLM summary generated from `report`.

## Open integration work
- Bring the `Mission` schema into `backend/llm/api.py` (`JezeroMissionRequirements`), with `safety`, `science_targets`, `science_detour` and `return_to_origin`, and add examples to the `Modelfile`. Today the LLM only extracts 5 fields; the rest take their default values.
- Unify place names: the frontend `places.json`, the planner `PLACES` and the `Modelfile` examples ("Three Forks" has no coordinates in any of them).
- `SunAngle.csv` covers a single day (2026-318). For another day, generate another CSV with the same shape.
