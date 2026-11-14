# MARPS

Mars Aerial Route Pairing System: a route planner for surface excursions on Mars that accounts for both the terrain **and** the mission's objectives.

Challenge: *Interplanetary Survival Guide: Martian Map* (NASA Space Apps Challenge 2026, Málaga).

## Concept

- A multi-layered map of a region on Mars, incorporating data from NASA missions (topography, slope, surface roughness, thermal properties, mineralogy, radiation, etc.).
- Definition of a starting point and a destination on the map.
- A text field for describing the mission in natural language.
- A local LLM converts this description into a set of weights and constraints (in JSON format).
- The route planner calculates the path based on these weights. The LLM handles translation only; it does not perform any planning.

See details in [docs/IDEA.md](docs/IDEA.md) and [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md).

## Directories

- `platform/`: interface and API
- `llm/`: translation of the mission description into JSON
- `planner/`: route-finding algorithm
- `data/`: map downloading and preprocessing
- `docs/`: challenge details, concept, sources, and progress

How we work: [CONTRIBUTING.md](CONTRIBUTING.md).

## License

To be determined.
