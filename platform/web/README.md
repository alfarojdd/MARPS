# MARPS web application

React, Vite, Tailwind CSS, Leaflet and Three.js interface of the Mars Adaptive Route Planning System, for Jezero crater.

## Features

- **Mission panel.** Natural-language mission text, three demo missions that also set the vehicle state, and a briefing from the local small language model (SLM) with the planner's figures, stops and warnings.
- **2D map** over the 6 m CTX mosaic (`L.CRS.Simple`, 1 unit = 1 pixel of the 5322 × 5040 raster) with the planned route, the classic shortest-path A* (dashed), stops and named places.
- **Layers.** Basemap (CTX mosaic or shaded relief) and one of 14 data layers (elevation, slope, roughness, thermal inertia, sunlight, radiation shielding, geology, mineralogy...) with legend and opacity.
- **3D relief.** Three.js view of the CTX DTM (vertical exaggeration ×3) with the route drawn over the terrain, the selected layer draped on it and a *Replay route* button.
- **3D surface reconstructions.** Located scenes appear as `3D` points in 2D and 3D and open in a viewer where local scenes can be explored in first person.
- **Telemetry.** Departure time, battery, capacity and reserve are editable to explore how the vehicle state changes the route.

## Development

```bash
cd platform/web
npm ci
npm run dev          # http://localhost:5173
```

The development server proxies `/api`, `/viewer`, `/reconstructions`, `/assets/ctx`, `/data` and `/terrain3d` to the MARPS server (`python3 backend/app.py` or `backend/run.sh`, port 8765 by default). Use `MARPS_API=http://host:port npm run dev` to point it elsewhere.

| Command | Description |
|---|---|
| `npm run dev` | Development server |
| `npm run build` | Type-check and production build in `dist/` (served by `backend/app.py` when present) |
| `npm run preview` | Preview the production build |

## Structure

```
src/App.tsx                 State and layout
src/components/MapView.tsx  Leaflet map, layers, route, 3D view integration
src/components/MissionPanel.tsx, VehiclePanel.tsx, LayersPopover.tsx, SceneViewer.tsx, Brand.tsx
src/lib/                    API client, types, route conversion, 3D viewer helpers
public/layers/ctx/          CTX mosaic tiles
public/layers/thematic/     One image per data layer (data/jezero/pipeline/export_web_layers.py)
public/brand/               Logos
vercel.json                 Proxy of the API and data paths to the MARPS server
```

The 3D engine is loaded at run time from the MARPS server (`/viewer/terrain3d/terrain3d.mjs`, with Three.js resolved through the import map in `index.html`). See [../../docs/DEPLOY.md](../../docs/DEPLOY.md) for deployment.
