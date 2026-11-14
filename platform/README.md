# platform

User interfaces.

| Directory | Contents |
|---|---|
| [`web/`](web/README.md) | **The MARPS application** (React, Leaflet, Three.js): mission panel, 2D map with 14 data layers, 3D relief view with the route, surface reconstructions, editable telemetry and Bellona's briefing. Deployed on Vercel. |
| [`viewer/`](viewer/README.md) | The Three.js terrain engine (`terrain3d/terrain3d.mjs`) and the surface-reconstruction viewer (`surface.html`) used by the application, plus a standalone Leaflet layer viewer served at `/viewer/` for inspecting the layers and reconstructions without the planner. |

Architecture and API contracts: [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).
