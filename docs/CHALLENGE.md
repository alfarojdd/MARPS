# The challenge: "Interplanetary Survival Guide: Martian Map"

- **Event:** NASA Space Apps Challenge 2026 (hackathon, 14-15 November 2026).
- **Official page:** https://www.spaceappschallenge.org/2026/challenges/interplanetary-survival-guide-martian-map/
- **Difficulty:** Intermediate.
- **Subjects:** Human Exploration, Mars, Planets & Moons, Software, Space Exploration.

## What it asks for

Build a **map, tool or interface** that an astronaut on Mars can use during a surface excursion (a "Marswalk"). It must be a **layered, integrated view** of a specific area or route that combines data from several NASA science missions and helps plan and carry out the excursion safely while doing science.

### Why the challenge exists
Tools such as JPL Mars Trek or the USGS geologic maps already let you overlay layers on Mars, but they are designed for a **regional or global scale**. A specific astronaut excursion needs a **hyperlocal** map, centred on their route and objectives.

### Explicit objectives
1. Choose the mission's **science objectives** and a **location** (example from the statement: studying the *boxwork* formations on Mount Sharp, where Curiosity observed them in 2025).
2. An area heavily explored by rovers is recommended (more data and images), although a less-studied one can be chosen.
3. Integrate **at least three data types**: optical, thermal, spectral, topographic, geophysical, atmospheric, radiation, chemical...
4. **Astronaut safety first:** space weather and radiation, reduced mobility due to the suit and the load.
5. If possible, a **route map** showing where the astronaut goes to meet their science objectives **while avoiding obstacles** (large rocks, etc.).

### Optional considerations
- Any format: a screen in the habitat, a tablet app, a HUD on the helmet visor...
- It can be static, interactive, or **a system that generates maps** of different places or with different data.
- Draw inspiration from maps of other missions (Earth, Moon, other planets).
- Any time frame: past data, forecast conditions or stable data (topography, geology).
- Include **first-person images** from the rovers so the astronaut knows what to expect.
- Consider support rovers or astronauts working in pairs.

## Official challenge resources
| Resource | What it is for | URL |
|---|---|---|
| JPL Mars Trek | Web portal with Mars data layers (DEM, mosaics, etc.) and WMTS services | https://trek.nasa.gov/mars/ |
| USGS-NASA Planetary Geologic Mapping | Standardised geologic maps of Mars | https://astrogeology-usgs.hub.arcgis.com/pages/interactive-maps-mars |
| Curiosity's proposed path up Mount Sharp | Visual example of a route map | https://science.nasa.gov/resource/curiositys-proposed-path-up-mount-sharp/ |
| NASA Worldview | Inspiration (it covers Earth) | https://worldview.earthdata.nasa.gov/ |
| Perseverance Raw Images | More than 1 million surface images | https://mars.nasa.gov/mars2020/multimedia/raw-images/ |

Other relevant sources: HiRISE (DTMs and high-resolution images), CTX, THEMIS (thermal inertia), CRISM (mineralogy), MOLA (global topography), MEDA/REMS (surface weather) and Curiosity's RAD (radiation).

## How MARPS answers it

| Requirement | MARPS |
|---|---|
| Hyperlocal, layered map of a specific area | 14 layers of Jezero crater on a common 20 m grid, switchable in the interface and draped over a 3D relief |
| At least three data types | Topographic (CTX/HRSC DTM), thermal (THEMIS), spectral (CRISM), geologic (USGS), derived solar and radiation exposure |
| Astronaut safety first | Hard slope, cross-slope and hazard-buffer limits, daylight and battery checks, shadow avoidance, charging stops; the safety constraints cannot be relaxed by the language model |
| Route that meets science objectives while avoiding obstacles | The mission text sets science targets (carbonates, clays, olivine...) and the planner detours through them within a time budget |
| First-person images | 3D reconstructions of Perseverance imagery, reachable from the map and from the 3D relief |
| Works in any format and time frame | Web interface; the models run locally, so it works without a link to Earth |
