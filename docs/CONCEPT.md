# Concept: a mission-aware route planner

## Summary
MARPS is a multi-layer map of an area of Mars on which a route planner computes the path between two points taking into account **the terrain and also the mission objectives**. A **local small language model (SLM)** translates the mission description, written in natural language, into the parameters that shape the path cost.

## The problem
Classic planners (A*, Dijkstra, D*...) optimise an almost always geometric cost: distance, slope, obstacles. On a real Mars excursion the best path depends on **why** the crew goes out:

- A geological mission benefits from passing near outcrops with certain minerals, even if the path is longer.
- With a low battery, the route must save energy and include a sunlit stop to recharge.
- Fragile cargo or injured crew call for the gentlest terrain, with wide margins around hazards.
- A rover and a crew on foot have different slope and roughness limits.

MARPS makes **the cost function depend on the mission context**.

## User flow
1. The user opens the platform and sees the map of Jezero crater.
2. They switch **layers** on and off (relief, slope, roughness, thermal inertia, sunlight, radiation shielding, geology, mineralogy).
3. They describe the mission in a text box, for example:
   > "Two astronauts carrying fragile sample tubes must go from the landing site to Belva crater. Take the safest, gentlest route possible."
4. A **local SLM** converts the text into a JSON of mission parameters validated against a schema.
5. The planner combines the layers into a cost map, enforces the safety limits and computes the route, together with a comparison against a classic shortest-path A*.
6. The route appears on the 2D map or over the 3D relief, with its metrics, warnings and stops (charging, science).
7. A second SLM, **Bellona**, writes a short briefing that justifies the route using only verified figures.

## Key principle: the SLM parametrises, it does not plan
The SLM translates intent into parameters. The routing algorithm is deterministic and the safety limits (maximum slope, cross slope, hazard buffers, daylight and battery checks) are always applied by the planner, whatever the model outputs. This keeps the result reproducible, explainable and safe, and means that an SLM mistake can only change preferences, never remove a safety constraint.

The briefing model is protected the same way: it does not read the raw report but a list of verified facts, in which only real improvements are listed as gains and the trade-offs are stated separately.

## Cost model (summary)
Each edge of the 20 m grid costs

```
cost(u→v) = mult · [ w_dist·L + w_time·t + w_energy·E ] + L · Σ w_k · risk_k
```

with energy `E` (rolling resistance on sand and dunes, climbing, life support, solar income), risks for roughness, soft ground, dunes, slope, cross slope, unknown data, radiation exposure and terrain shadow, and a science discount `mult` near the requested targets. Weights depend on the mission parameters and the vehicle state. See [PLANNER.md](PLANNER.md).

## Data layers
| Layer | Source | Use in the cost |
|---|---|---|
| Elevation | MRO CTX DTM (20 m), HRSC (75 m) | Basis for slope and elevation gain |
| Slope, roughness (TRI, TPI), aspect | Derived from the DTM | Penalty and hard constraints |
| Thermal inertia, day/night infrared | Mars Odyssey THEMIS | Loose sand vs. firm ground |
| Mineralogy | MRO CRISM | Science targets |
| Geology | USGS SIM 3464 | Dune avoidance and science targets |
| Sunlight, radiation shielding | Derived (terrain shadows, atmospheric column) | Energy, shadow and exposure |
| Surface imagery | Mars 2020 | First-person reconstructions along the route |

The challenge requires at least three data types; MARPS combines topographic, thermal, spectral, geologic and derived solar and radiation data. Layer details: [JEZERO_LAYERS.md](JEZERO_LAYERS.md).

## Study area
**Jezero crater**, Perseverance's landing site, with its delta and high-resolution elevation models.

## What sets MARPS apart
- Mars Trek and similar tools display layers; MARPS **reasons over them** to plan.
- The same origin and destination give **different routes depending on the mission**.
- Explicit mission parameters in JSON make the decision **transparent and editable**.
- The models run **locally**: no connection to Earth is needed, which matters with a 4–24 minute communication delay.
