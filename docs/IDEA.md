# Our idea: a mission-aware route planner

## One-sentence summary
A multi-layer map of an area of Mars on which a route planner computes the path between two points taking into account **the terrain and also the mission objectives**. A **small local LLM** translates the mission description, written in natural language, into a **JSON of weights** that modifies the path cost.

## The problem we solve
Classic planners (A*, Dijkstra, D*...) optimise an almost always geometric cost function: distance, slope, obstacles. On a real Mars outing, the "best" path depends on **why** you are going out:

- If the mission is geological, it pays to pass close to outcrops with certain minerals, even if the path is longer.
- If a solar storm is forecast, it pays to minimise exposure time and stay close to shelter.
- If the astronaut is carrying heavy instruments, slopes are penalised much more.
- If travelling by rover, the slope and roughness limits change.

Our tool makes **the cost function depend on the mission context**.

## How it works (user flow)
1. The user opens the platform and sees the map of the chosen area.
2. They switch **layers** on or off (relief, slope, roughness, mineralogy, thermal inertia, geology, radiation...).
3. They mark an **origin** and a **destination** on the map.
4. They write the **mission context** in a text box. Example:
   > "4-hour outing to collect clay samples. Two astronauts on foot with a drill (15 kg). Risk of a solar particle event in the afternoon. Avoid slopes steeper than 15°."
5. A **local LLM** converts that text into a **JSON of parameters** validated against a schema.
6. The planner combines the layers with those weights into a **cost map** and computes the route.
7. The route is shown on the map with its metrics (distance, elevation gain, estimated time, exposure, points of interest it passes through) and, if possible, an explanation of why it was chosen.

## Key piece: from text to a JSON of weights
The LLM **does not plan the route**: it only translates intent into parameters. This keeps the result reproducible, explainable and safe (the routing algorithm is deterministic and the safety limits are always enforced).

Draft schema (details to be defined):

```json
{
  "travel_mode": "on_foot",          // on_foot | rover
  "load_kg": 15,
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
    "scientific_interest": 2.5
  },
  "science_targets": ["clays", "phyllosilicates"],
  "desired_waypoints": []
}
```

Cost of each map cell (initial idea):

```
cost(cell) = Σ weight_i · normalised_layer_i(cell)  − interest_weight · affinity(cell, targets)
```

Hard constraints (maximum slope, forbidden zones) mark cells as impassable. "Scientific interest" acts as a bonus (lower cost) near what the mission is looking for. The cost is always kept positive so that A* remains valid.

## Candidate data layers
| Layer | Likely source | Use in the cost |
|---|---|---|
| Elevation (DEM) | HiRISE DTM / CTX / MOLA via Mars Trek | Basis for slope and elevation gain |
| Slope | Derived from the DEM | Penalty and hard constraint |
| Roughness / rocks | Derived from the DEM, HiRISE rock maps | Penalty |
| Thermal inertia | THEMIS | Indicator of loose ground vs. firm rock |
| Mineralogy | CRISM | Scientific interest |
| Geology | USGS maps | Scientific interest and terrain type |
| Radiation and weather | RAD (Curiosity), MEDA (Perseverance), models | Exposure and time windows |
| Surface images | Rover raw images | First-person view along the route |

To meet the challenge requirement, **at least three data types** are enough.

## Tentative architecture (not decided)
- **Data:** offline preprocessing of the chosen area onto a common grid (same CRS and resolution) → GeoTIFF / NumPy arrays.
- **Backend:** Python (FastAPI) with the planner (A* on a grid) and the endpoint that calls the LLM.
- **Local LLM:** small model (e.g. via Ollama or llama.cpp) with structured JSON output and validation (Pydantic/JSON Schema). If validation fails, it retries or falls back to default weights.
- **Frontend:** web map (Leaflet / OpenLayers / deck.gl) with a layer selector, click to set origin and destination, a context box and a results panel.

## Candidate area
To be decided. Options with plenty of data: **Gale / Mount Sharp** (Curiosity, boxwork, the challenge statement's own example) or **Jezero crater** (Perseverance, delta, HiRISE DTMs available).

## What sets us apart
- Maps like Mars Trek display layers; we **reason over them** to plan.
- Same origin and destination → **different routes depending on the mission**, a very visual demo.
- Explicit weights in JSON → the decision is **transparent and editable** by the astronaut or mission control.
- **Local** LLM: works without a connection to Earth (with a 4 to 24 minute communication delay, this matters).
