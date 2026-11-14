# MARPS: Mars Aerial Route Pairing System

> Mission-aware route planning on a multi-layer map of Mars.
> Project for the **NASA Space Apps Challenge 2026 (Málaga)**, challenge **"Interplanetary Survival Guide: Martian Map"**.

## What is this?

The first astronauts on Mars will walk and drive across terrain that no map describes at the scale of a single excursion. Tools like JPL Mars Trek show layers of data for regional or global views, but not the hyperlocal view a crew needs for one outing.

MARPS is a web platform that:

1. Shows a **multi-layer map** of a patch of Mars built from NASA mission data (elevation, slope, roughness, thermal, mineralogy, geology, radiation...).
2. Lets the user pick an **origin** and a **destination**.
3. Lets the user describe the **mission context** in plain language: scientific goals, who is going, what they carry, how long, which risks apply.
4. Uses a **small local LLM** to translate that text into a **JSON of weights and constraints**.
5. Computes the **best route** with a planner whose cost function combines the map layers using those weights.

Classic planners such as A* optimize geometry only (distance, slope, obstacles). MARPS also optimizes for **why** the crew is going: the same origin and destination produce different routes for a geology sampling trip, a trip with a solar storm forecast, or a heavily loaded traverse.

**Design principle: the LLM only parametrizes, it never plans.** Route search is deterministic and safety constraints are always enforced, so results are reproducible and explainable.

## Challenge objectives we address

- A layered, integrated, hyperlocal map combining **at least three kinds of NASA data**.
- Astronaut **safety first**: slope limits, rough terrain, radiation exposure.
- A **route map** that reaches scientific targets while avoiding obstacles.
- A tool that works for **different locations and different mission contexts**, not a single static map.

## How it works

```
 Map layers (data/)  ──────────────────────────────┐
                                                    ▼
 Mission text ──► LLM (llm/) ──► JSON weights ──► Planner (planner/) ──► Route + metrics ──► UI (platform/)
```

The three interfaces between components are described in [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md).

## Repository layout

| Folder | Area | Contents |
|---|---|---|
| [`platform/`](platform) | Interface and LLM integration | Web app, map viewer, layer selector, mission text box, results panel |
| [`llm/`](llm) | Language model | Prompts, JSON schema, validation and local model setup |
| [`planner/`](planner) | Route planning | Cost map, A* (or alternatives), constraints, metrics, tests |
| [`data/`](data) | Maps and data | Scripts to fetch and preprocess layers; small samples only |
| [`docs/`](docs) | Documentation | Challenge, idea, architecture, sources, submission checklist |

How we work together (branches, pull requests, who owns what): [CONTRIBUTING.md](CONTRIBUTING.md).

## Status

Early stage, started at the hackathon (14-15 November 2026). See [docs/PROGRESO.md](docs/PROGRESO.md) for the running log.

## NASA data and tools

Sources, versions and licenses are tracked in [docs/FUENTES.md](docs/FUENTES.md). Main starting points: [JPL Mars Trek](https://trek.nasa.gov/mars/), the [USGS-NASA Planetary Geologic Mapping Program](https://astrogeology-usgs.hub.arcgis.com/pages/interactive-maps-mars) and the [Perseverance raw images](https://mars.nasa.gov/mars2020/multimedia/raw-images/).

## Use of AI

AI assistants are used during development, and a local LLM is part of the product. Generated code and text are reviewed by the team. Details are declared in the project submission.

## License

To be decided by the team before submission (see [CONTRIBUTING.md](CONTRIBUTING.md)).
