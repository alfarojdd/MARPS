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
python3 backend/prepare_viewer.py  # first run only; downloads the web libraries
python3 backend/viewer.py
```

Open **http://127.0.0.1:8765**. Select a **3D** marker to enter a reconstruction, or use **Entrar en Cheyava Falls** to open the local scene in first person. Drag to look around and use **W A S D / arrow keys** to walk. Touch controls, an orbital view and a return-to-map button are also available.

The CTX basemap and local models work offline once the libraries are prepared. Sketchfab models require an internet connection. The catalog distinguishes approximate locations and scenes without verified coordinates. See [platform/viewer/README.md](platform/viewer/README.md) for details and limitations.

## License

To be determined.
