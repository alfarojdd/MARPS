# platform

Web interface: layered map, origin and destination, mission box and results panel. See [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).

The implemented viewer is in `viewer/`: example planned route, comparison against classic A*, stops, optional tilted relief with elevation profile, and access to surface reconstructions from both 2D and 3D points. The existing floating-card route map (`viewer/terrain3d/demo.html`) uses the same route/POI integration. Setup and current scope: [viewer/README.md](viewer/README.md). Mission text → LLM → a new route is not wired into this browser interface yet.
