# Planner: mission-aware route planner

Code in `planner/`:
- `planner.py`: cost model, A*, science and metrics.
- `report.py`: **JSON report** for the helmet LLM summary (comparison with the classic A*, battery, daylight and charging stop).
- `shadows.py`: shadows and illumination by hour, using `mars_shadows.py` (repo root) and `assets/SunAngle.csv`.
- `api.py`: FastAPI endpoint `POST /plan-route` for the backend. Full contract in [PLANNER_INTEGRATION.md](PLANNER_INTEGRATION.md).
- `live.py`: interactive test bench.
- `demo.py` and `scenarios.json`: scenario figure and table.
- `examples/`: real API request and response, and a report with a charging stop.
- `test_planner.py`: tests (14).

This is a spike: only the basics are tested and it has not gone through the subagent and review workflow. If it is taken into the product (MARPS `planner/`), it will need to be reviewed with that workflow.

```bash
python planner/live.py      # http://127.0.0.1:8766
cd planner
python demo.py             # → out/demo.png + out/demo.md
python -m pytest -q
```
Dependencies: `pip install -r planner/requirements.txt`. **Data**: the files in `data/jezero/` (Drive, see `data/jezero/README.md`): `stack/jezero_stack_20m.tif`, `extra/geo_unit.tif` and `extra/crism_class.tif`. For another location, set `JEZERO_DATA`. The first run creates `data/jezero/planner_cache_20m.npz` (not versioned). A sample report is in `planner/examples/report_example.json`.

## Input: two blocks

```json
{
  "mission": { ...what the LLM extracts from the astronaut's text... },
  "system":  { "start_hour": 9.0, "battery_kwh": 30, "battery_capacity_kwh": 40, "reserve_pct": 20 }
}
```
`system` is not set by the LLM. The vehicle provides it: the time from its link or clock, and the battery from its power manager.

### `mission` schema (for the LLM prompt and validation)
```python
class Mission(BaseModel):
    human: bool = True                       # crew on board (does not mean "on foot"); same as the backend LLM
    safety: Literal["low", "normal", "high"] = "normal"   # people or fragile cargo → "high"
    power: bool = False                      # prioritise energy saving
    route_preference: Literal["shortest", "fastest"] | None = None
    origin: str | None = None                # known place name or "lon,lat"
    destination: str | None = None
    science_targets: list[ScienceTarget] = []
    science_detour: Literal["low", "medium", "high"] = "medium"  # detour accepted for science: +20/50/100 %
    return_to_origin: bool = False           # round trip

class ScienceTarget(BaseModel):
    target: Literal["aqueous", "carbonates", "clays", "smectites", "kaolinite",
                    "olivine", "pyroxene", "delta", "crater_floor"]
    priority: float = Field(1.0, ge=0.1, le=1.0)   # 1 = main target, 0.3 = "if it's on the way"
```
**The parameter for what is to be investigated is `science_targets`.** It is a list because a mission can have several targets with different priorities. The LLM only picks names from a closed list; the code maps each name to map zones. Prompt guide:

| What the astronaut says | `science_targets` |
|---|---|
| "evidence of water", "ancient lake", "habitability" | `[{"target": "aqueous"}]` (= carbonates + clays + delta) |
| "carbonates" | `[{"target": "carbonates"}]` |
| "clays", "phyllosilicates" | `[{"target": "clays"}]` |
| "smectites" / "kaolinite" | `smectites` / `kaolinite` |
| "igneous rock", "basalt", "olivine" / "pyroxene" | `olivine` / `pyroxene` |
| "delta sediments", "fan" | `delta` |
| "crater floor" | `crater_floor` |
| "mainly carbonates, and clays if they're on the way" | `[{"target": "carbonates", "priority": 1}, {"target": "clays", "priority": 0.3}]` |
| "we have plenty of time" / "time is tight" | `science_detour: "high"` / `"low"` |

Through the API, an invalid value returns 422 and an unknown place 400, both with the reason, so the backend can ask the LLM to correct it. Accepted places: `GET /places` (names such as "Octavia E. Butler Landing" or "Belva crater", or coordinates "77.45,18.44" or "18.44N, 77.45E").

## Model
**Native 20 m grid** (the CTX DTM grid, 1512 × 1596 = 2.4 M cells) with 16 neighbours. Going below 20 m makes no sense: slope and roughness come from the 20 m CTX DTM, and thermal inertia is 100 m. HiRISE at 1 m only covers the central 32 % (see improvements).

```
cost(u→v) = mult · [w_dist·L + w_time·t·v0 + w_E·E/e_ref] + L · Σ w_k · risk_k
```
- **Direction-dependent:** longitudinal slope comes from Δh (uphill ≠ downhill). Cross slope is the gradient perpendicular to the direction of travel.
- **Speed:** `v0 / (1 + 0.08·|slope| + 0.06·cross + 1.5·roughness + 1.0·sand)`, with v0 = 2.5 m/s. "Sand" is the maximum of soft ground (thermal inertia) and dunes.
- **Energy:** rolling resistance (Crr 0.08 on firm ground, up to 0.20 in sand) + climbing + fixed load (800 W, plus 1.5 kW life support if crewed) − solar. Generic 3 t vehicle; figures are orders of magnitude and are not calibrated (this is a minimum viable product).
- **Risk:** roughness (TRI), soft ground (thermal inertia < 260), **dunes** ("Eolian bedform" unit from SIM 3464, 119 km²; their thermal inertia is almost normal, so this is the only way to detect them), (slope/max)², (cross/max)², unknown data and exposure (if crewed). `dist_traverse` is not used.
- **`mult`:** science discount `1 − 0.5·interest`, applied **only to distance, time and energy, never to risk**. Going to look at minerals must not make a dune look safer.
- **Hard constraints** (the JSON cannot relax them): maximum slope and cross slope, buffer around hazardous cells and, with `safety=high`, cells with no data.

| `safety` | low | normal | high |
|---|---|---|---|
| Max slope / cross slope | 25° / 15° | 20° / 12° | 15° / 8° |
| Buffer | 0 | 40 m | 100 m |
| Roughness / soft / dune weights | 0.3 / 0.3 / 0.5 | 1 / 1 / 2 | 3 / 3 / 5 |

### Heuristic
`h(n) = hflat · euclidean_distance(n, goal) + c_climb · max(h_goal − h_n, 0)`:
- **First term:** `hflat` is the lowest cost per metre over the whole grid, excluding climbing.
- **Second term:** any route must climb at least the elevation gain to the goal, and that costs energy.

It is admissible and consistent. The tests compare the result with Dijkstra, on both random problems and the real grid. Measured on crater_floor_south → delta_top:

| Scenario | No heuristic | Previous heuristic | New |
|---|---|---|---|
| Classic A* | 1 632 357 nodes | 105 510 | 105 293 (0.05 s) |
| power | 1 304 552 | 605 659 | **511 623 (−15 %)** |
| fastest | 1 314 328 | 817 554 | 802 223 |

The search now takes 0.05–0.4 s. The bottleneck is building the cost grid (≈2.5 s per weight profile), which is cached (4 profiles).

### science_targets → zones
1. Fixed name → mask dictionary: CRISM classes with confidence 1 / 0.6, and SIM 3464 geology with weight 0.5.
2. Interest map: Σ priority × mask, smoothed at 120 m and normalised.
3. Candidate patches: ≥ 2.4 ha, more than 500 m from A and B, the 10 highest-value ones.
4. Exact cost matrix between candidates: Dijkstra from each one, stopping as soon as it has reached all of them.
5. Greedy insertion with budget `(1 + science_detour) × cost(A→B)`, and A* leg by leg.
6. Each stop adds 20 min to time and energy.

## Output: report for the helmet LLM (`report.py`)
Full example in `planner/examples/report_example.json`. Blocks:
- `feasible`: false if there is any critical warning.
- `route`:
  - physical metrics: distance, time, total and traction energy, ascent and descent, maximum slopes, km over rough, soft, dune or no-data terrain, and mean exposure;
  - schedule: departure, arrival, daylight limit and margin;
  - battery at departure and arrival;
  - `science_stops` (lon, lat, minerals and stop minutes);
  - `charging_stop`;
  - `waypoints_lonlat` (~60 points).
- `classic_astar`: the same metrics for the route of a pure-distance A*, **measured with the same vehicle and crew** (only the path changes).
- `comparison`: what the LLM needs for sentences like "you saved X % battery":
  - `energy_saved_pct`, `drive_energy_saved_pct`, `time_saved_pct`, `extra_distance_pct`;
  - reduction in maximum slope and cross slope;
  - rough, soft and dune km avoided;
  - `on_<target>_km_gained`.
- `why`: which cost terms the route avoids compared with the classic A*, measured with this mission's weights (e.g. energy 39 %, time 20 %, soft ground 14 %), and the km gained over each science target.
- `warnings` (code, severity and message in English) and `suggestions`.

### Daylight and battery warnings
- **Daylight:** sunrise and sunset from `SunAngle.csv` (06:00–18:00 if there is no shadow map), with a 30 min margin.
  - `NO_DAYLIGHT_AT_DEPARTURE`: departure falls outside the daylight window.
  - `ARRIVAL_AFTER_DAYLIGHT`: arrival is past the limit. It is **critical when crewed** and a warning when not.
- **Battery:** the route energy is needed, plus stops, plus a reserve (20 % of capacity).
  - `BATTERY_BELOW_RESERVE`: arrival with less than the reserve.
  - `SWITCH_TO_POWER_SAVING` (suggestion): if the battery is not enough and `power` was off, the power-saving route is computed and the report says whether it is enough.
  - `CHARGING_STOP_REQUIRED`: if it is still not enough, the planner looks for a sunny, flat, firm, dune-free site within 1 km of the part of the route reachable with the current battery. It replans through that site and computes how long to stop. Charging is estimated with a deployed 3 kW peak panel × the site's actual direct light (shadow map) hour by hour, minus the idle load (and life support if crewed). Details in "Shadows".
  - `BATTERY_INSUFFICIENT`: the charging stop cannot even be reached.
  - `CHARGING_DOES_NOT_FIT_DAYLIGHT`: there is not enough daylight to charge.

## Live tool (`live.py`)
- **Controls:** mission parameters, `science_targets` with priority, `science_detour`, round trip, and system state (time and battery). Origin and destination from a list or by clicking on the map.
- **Map:** context-aware route, classic A*, science stops and charging stop. Optional "Sombras a la hora de salida" (shadows at departure time) background.
- **Panel:** warnings, comparison table and a "Ver JSON" button with the full report.
- **Timings:** 0.5 s with an already cached profile, 3–8 s with a new one and 10–17 s with science.

It is not the product frontend.

## Shadows (`shadows.py`, with Pablo's `mars_shadows.py`)
- **Ephemeris:** `SunAngle.csv` gives the Sun's elevation and azimuth in Earth UTC time (one day, 2026-318). It is converted to **local true solar time (LTST)**: noon is the elevation maximum (parabolic fit) and an LTST hour lasts 3698.9 s. Result: sunrise 05:48, sunset 18:12, Sun at 80° at noon.
- **Illumination:** for each of the 26 sunlit instants, `mars_shadows.classify` computes on the 20 m DTM the cast shadow (terrain blocks the Sun) and the self-shadow (slope facing away). `illum = cos(incidence)` is stored in illuminated cells (0 in shadow), as uint8. It takes about 7 s the first time and is then cached (`data/jezero/planner_shadows_20m_<hash>.npz`).
- **In the cost**, if `start_hour` is given:
  - Each cell takes the light at its estimated pass time (`start_hour` + distance to origin / 1.2 m/s).
  - Light changes the **solar charging while driving** in the energy term (for all profiles, so the physics is the same and the comparison is fair).
  - It adds a terrain **shadow risk** term (not night), weighted by `safety` (0 / 0.2 / 0.5) + 0.5 if crewed + 1.0 with `power`.
- **In the metrics:** the final route is evaluated with its actual pass time on each leg, which gives `shadow_km`, `shadow_pct` and `night_km`. `comparison` includes `shadow_km_avoided`.
- **Daylight window:** sunrise and sunset come from the CSV instead of the fixed 06–18 window.
- **Charging stop:**
  - Each candidate (flat, firm, dune-free, within 1 km of the reachable leg) is reached at its own time.
  - The one that **finishes charging first** is chosen: arrival + missing energy / (3 kW × mean actual direct light over the next 3 h − idle load).
  - Charging time is integrated with the actual light at that point hour by hour. This avoids shaded sites; in a test from the western rim at 06:00, without shadows a fully shaded site was chosen (light 0.00), and with shadows one with light 0.49.
- **Finding:** on the crater floor there are hardly any shadows during the day; they only appear in the first and last hour and near the rim and the delta scarps. That is where they change the route and, above all, the charging site.
- **Without `mars_shadows.py` or the CSV,** the planner works the same with `insolation_rel` and the 06–18 window (`/planner/health` reports whether shadows are available).

## Open issues / improvements
- **Shadows:** the pass time is estimated in a straight line from the origin (it does not follow the route or the stops). Missing: season (the CSV covers one day), cold and heating in shadow, and terrain shadows from outside the bounding box (the script extends the edge).
- **Performance:** build the cost grid (2.5 s) in parallel with Numba. Science (11 Dijkstras at 20 m) could select stops at 40 m and trace at 20 m.
- **Finer explanation:** `why` measures cost terms; it could add *where* (specific legs that are avoided).
- **HiRISE 1 m** in the centre: refine the route inside a corridor of about 200 m.
- **Route smoothing**, Theta*-style.
- Each science patch's value still favours large patches, and outside CRISM the interest is 0 (not "unknown").
