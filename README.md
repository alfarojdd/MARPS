<p align="center">
  <img src="platform/web/public/brand/marps-bellona.svg" alt="MARPS Bellona" height="64">
</p>

<h1 align="center">MARPS · Mars Adaptive Route Planning System</h1>

<p align="center">
  <strong>Tell the crew's mission. Get the route that fits it.</strong><br>
  A mission-aware route planner for surface excursions on Mars, built on NASA data.<br>
  <sub>NASA Space Apps Challenge 2026 · <em>Interplanetary Survival Guide: Martian Map</em></sub>
</p>

<p align="center">
  <a href="docs/media/product/mission-to-route.mp4">
    <img src="docs/media/product/mission-to-route.gif" alt="A mission is written to Bellona, the terrain is scanned and the route appears on the map of Jezero crater" width="860">
  </a>
</p>

<p align="center">
  <a href="docs/media/product/demo.mp4"><strong>▶ Watch the full product tour (MP4, 1 min)</strong></a>
</p>

---

## The problem

A walk on Mars is not a hike. The crew has a suit with a limited battery, sample tubes that must not be shaken, a daylight window, radiation to dodge and a science plan that only makes sense in certain places.

Route planners we know optimise **geometry**: shortest distance, lowest slope. But the best path depends on **why the crew is going out**. The same two points on the map need a different route for a rushed run with a nearly flat battery, for a careful carry of fragile cargo, or for a geology trip to carbonate-rich outcrops.

## The product

MARPS is a map of Jezero crater, a planner and an assistant in one screen.

1. **You describe the mission** in plain language to **Bellona**, the on-board assistant.
2. **MARPS understands it**: crew, cargo, battery, risk appetite, science targets.
3. **It computes the route** over a stack of NASA map layers, respecting hard safety limits.
4. **Bellona briefs the crew**: why this path, what it saves, where to stop and recharge.
5. **You inspect it** in 2D, in 3D over the real relief, and even from the ground with reconstructions of Perseverance imagery.

> “Two astronauts drive from the landing site to the top of the delta. The battery is low, so save as much energy as possible and plan a sunlit stop on the way to recharge.”

![The full MARPS screen after a mission: route on the orbital map, metrics and Bellona's briefing](docs/media/product/route-low-battery.jpg)

---

## One destination, three missions, three routes

Same origin (Octavia E. Butler landing site), same destination (top of the western delta). Only the mission changes.

| 🔋 Low battery | 🧪 Fragile cargo | 🔬 Science stops |
|---|---|---|
| [![Low-battery route with a sunlit charging stop](docs/media/product/route-low-battery.jpg)](docs/media/product/route-low-battery.jpg) | [![Gentle route for fragile cargo](docs/media/product/route-fragile-cargo.jpg)](docs/media/product/route-fragile-cargo.jpg) | [![Route detouring through carbonate-rich terrain](docs/media/product/route-science.jpg)](docs/media/product/route-science.jpg) |
| Saves energy and includes a **sunlit stop** where the crew recharges. | Takes the **gentlest, safest terrain** with wide margins around hazards. | Detours through **carbonate and clay-rich terrain** with timed science stops. |
| **12.2 km** · 5.1 h · max slope 18.3° · arrives with 20 % battery | **14.0 km** · 2.5 h · max slope 10.3° · arrives with 47 % battery | **14.3 km** · 3.6 h · two 20-minute science stops |

The dashed blue line on every map is a classic shortest-path A\*. MARPS shows it so the crew can see exactly what the mission context changed, and Bellona states the trade-off: where the route is longer, it says what the extra distance buys.

---

## See the route come to life in 3D

One tap on **3D view** tilts the map into the real Martian relief. The route draws itself across the terrain and the camera can be orbited freely.

<p align="center">
  <img src="docs/media/product/route-3d.gif" alt="The map tilts into 3D and the route is drawn over the Jezero relief" width="760">
</p>

| Orbit around the route | Any data layer draped on the relief |
|---|---|
| [![3D relief seen from the delta with the route drawn over it](docs/media/product/route-3d-orbit.jpg)](docs/media/product/route-3d-orbit.jpg) | [![Slope layer draped over the 3D relief with a route](docs/media/product/route-3d-slope.jpg)](docs/media/product/route-3d-slope.jpg) |

## A map with many layers, not just a picture

Switch layers on and off, in 2D or draped over the 3D relief. Slope, roughness, thermal inertia, sunlight, radiation shielding, geology and mineralogy come from several NASA, ESA and USGS missions and share one 20 m grid, so they can be combined.

<p align="center">
  <img src="docs/media/product/layers.gif" alt="Switching between slope, roughness, thermal inertia, sunlight and radiation layers" width="760">
</p>

| Slope | Radiation shielding |
|---|---|
| [![Slope layer](docs/media/product/layers-slope.jpg)](docs/media/product/layers-slope.jpg) | [![Radiation shielding layer](docs/media/product/layers-radiation.jpg)](docs/media/product/layers-radiation.jpg) |

## Step off the map and onto the surface

Every **3D marker** is a reconstruction built from real Perseverance imagery. Click one and walk through it in first person, or orbit it, so the crew knows what the ground looks like before they leave.

<p align="center">
  <img src="docs/media/product/surface.gif" alt="Walking and orbiting inside the Cheyava Falls reconstruction" width="680">
</p>

| On foot at Cheyava Falls | Orbit view |
|---|---|
| [![First-person view of the Cheyava Falls reconstruction](docs/media/product/surface-onfoot.jpg)](docs/media/product/surface-onfoot.jpg) | [![Orbit view of the reconstruction](docs/media/product/surface-orbit.jpg)](docs/media/product/surface-orbit.jpg) |

## Works on a tablet or phone

The interface adapts to small screens: Bellona folds behind the logo and the route briefing becomes a collapsible card.

<p align="center">
  <img src="docs/media/product/mobile-route.jpg" alt="MARPS on a phone with a route and a compact briefing" width="260">
</p>

---

## What sets MARPS apart

| | Typical route planner | **MARPS** |
|---|---|---|
| **What decides the route** | Terrain geometry | Terrain **and the purpose of the mission** |
| **How you give the mission** | Menus and sliders | A sentence in natural language |
| **Safety** | A parameter that can be tuned away | **Hard limits that are always enforced**: slope, cross slope, hazard buffers, daylight and battery |
| **Role of AI** | Black box that picks the path | The language model only **sets preferences**. A deterministic planner draws the path, so results are reproducible and explainable |
| **Explanation** | A line on a map | Bellona's briefing, written from **verified planner figures only** |
| **Comparison** | None | Every route is shown against the classic shortest path |
| **Energy and sun** | Ignored | Battery reserve, terrain shadows and **sunlit charging stops** |
| **Connectivity** | Cloud services | Small models that can **run locally**, with no link to Earth |
| **Context** | A top-down map | 2D, 3D relief and **first-person surface reconstructions** |

### Safety comes first

The language model can change what the crew *prefers*, never what is *allowed*. Whatever the model outputs, the planner refuses slopes, cross slopes and hazard margins beyond the limits for the crew and vehicle, and checks the battery reserve and the daylight window.

---

## How it answers the challenge

| The challenge asks for | MARPS |
|---|---|
| A hyperlocal, layered map of one area | 14 layers of Jezero crater on a common 20 m grid |
| At least three NASA data types | Topography (MRO CTX, Mars Express HRSC), thermal (Mars Odyssey THEMIS), spectral (MRO CRISM), geology (USGS) and derived sunlight and radiation exposure |
| Astronaut safety first | Enforced slope, hazard, daylight and battery constraints |
| A route that meets the science goals and avoids obstacles | Science targets in the mission text bend the route through carbonates, clays and more |
| First-person imagery from rovers | 3D reconstructions of Perseverance imagery, walkable from the map |

## Built on public NASA, ESA and USGS data

MRO CTX · Mars Express HRSC · Mars Odyssey THEMIS · MRO CRISM · USGS geologic map SIM 3464 · Mars 2020 Perseverance imagery. Provenance, licences and processing of every layer are in [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md). The use of NASA data does not imply endorsement by NASA.

## Want to know more?

| | |
|---|---|
| [docs/CHALLENGE.md](docs/CHALLENGE.md) | The challenge and how MARPS answers it |
| [docs/CONCEPT.md](docs/CONCEPT.md) | Concept and design principles |
| [docs/TECHNICAL.md](docs/TECHNICAL.md) | Architecture, how it is built and how to run it locally |
| [docs/PLANNER.md](docs/PLANNER.md) | The route cost model |
| [docs/media/product/README.md](docs/media/product/README.md) | How the videos and images above were recorded |

The live demo ([marps-bellona.vercel.app](https://marps-bellona.vercel.app)) is hosted for the event and may be offline afterwards; everything it does is shown above.

## Licence

The original code and documentation of MARPS are released under the [Apache License 2.0](LICENSE). Attribution and third-party terms are in [NOTICE](NOTICE). The licence does not cover third-party material: NASA and USGS data are in the public domain in the United States, other datasets keep their own terms and must be cited, surface reconstructions keep the terms of their authors, and the language models follow the Gemma model terms.
