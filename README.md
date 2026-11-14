# MARPS

Mars Aerial Route Pairing System: a route planner for surface excursions on Mars that accounts for both the terrain **and** the mission's objectives.

Challenge: *Interplanetary Survival Guide: Martian Map* (NASA Space Apps Challenge 2026, Málaga).

## Concept

- A multi-layered map of a region on Mars, incorporating data from NASA missions (topography, slope, surface roughness, thermal properties, mineralogy, radiation, etc.).
- Definition of a starting point and a destination on the map.
- A text field for describing the mission in natural language.
- A local LLM converts this description into a set of weights and constraints (in JSON format).
- The route planner calculates the path based on these weights. The LLM handles translation only; it does not perform any planning.

See details in [docs/IDEA.md](docs/IDEA.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Directories

- `platform/`: interface and API
- `llm/`: translation of the mission description into JSON
- `planner/`: route-finding algorithm
- `data/`: map downloading and preprocessing
- `docs/`: challenge details, concept, sources, and progress

How we work: [CONTRIBUTING.md](CONTRIBUTING.md).

## Map and 3D reconstructions

With `MARPS_Jezero_3D_datos/MARPS_Jezero_3D` extracted at the repository root:

```bash
python3 backend/prepare_viewer.py  # download/update and verify the web libraries
python3 backend/viewer.py
```

Open **http://127.0.0.1:8765**. The map combines the existing example trajectory, classic A* comparison, stops and **3D reconstruction points**. The floating-card route view at **http://127.0.0.1:8765/terrain3d/demo.html** has the same points and surface viewer. Both share the route and relief controls.

Select a **3D** marker or **Entrar en Cheyava Falls** to enter a local scene in first person. Drag to look around and use **W A S D / arrow keys** to walk. Closing the scene returns to the same map, trajectory and camera. With a generated relief, the map's **3D** button tilts the terrain and keeps reconstruction points clickable above it, alongside the elevation profile. See [TERRAIN_3D.md](docs/TERRAIN_3D.md) to prepare the real DTM; without it, the 2D route and surface reconstructions remain available.

The CTX basemap, generated relief and local models work offline once prepared. Sketchfab models require an internet connection. The catalog distinguishes approximate locations and scenes without verified coordinates. See [platform/viewer/README.md](platform/viewer/README.md) for usage and [RECONSTRUCTIONS.md](docs/RECONSTRUCTIONS.md) for the integration, data and current limitations. The displayed trajectory is a saved planner example; it is not a live mission request.

## License

To be determined.
