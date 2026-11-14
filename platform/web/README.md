# MARPS Web Frontend

React + Vite + Tailwind + Leaflet frontend for the Mars Aerial Route Pairing System (Jezero Crater).

## Features

- Operations UI: full-bleed Jezero mosaic, numbered brief, translation, and path readout
- CTX orthomosaic basemap (6 m/px tiles)
- Natural-language mission → LLM extraction (`POST /parse-mission`)
- Mock planner that draws a route + realistic metrics
- Responsive (works on laptop + phone)
- Known places only for the demo (see below)

## Known places (demo)

The LLM can return these names (fuzzy matching is applied):

- **Octavia E. Butler Landing (Perseverance)**
- **Belva (crater)**
- **Neretva Vallis**
- **Jezero (crater centre)**

## Quick start

```bash
cd platform/web

# Install (once)
npm install

# Make sure the backend LLM is running on :8000
# (from repo root)
# uvicorn backend.llm.api:app --host 0.0.0.0 --port 8000

# Start frontend
npm run dev
```

Open http://localhost:5173

The Vite dev server proxies `/api/*` → `http://localhost:8000/*`.

### Environment

Optional:

```
VITE_API_URL=http://localhost:8000
```

If you set this, the proxy is bypassed.

## Tiles

Tiles live in `public/layers/ctx/` (already present from the repo assets).

They were generated from the CTX orthomosaic. See `assets/zones/public/layers/ctx/README.md` for regeneration.

## Architecture notes

- Map uses `L.CRS.Simple` (1 unit = 1 pixel of the 5322×5040 raster).
- Origin / Destination come **only** from the LLM JSON response.
- Planner is currently mocked (`src/lib/mockPlanner.ts`). Replace with a real call when the planner endpoint is ready.
- No multi-layer thematic switching yet (focus was on the core planning flow). Can be added later on top of the existing 20 m stack.

## Scripts

| Command        | Description              |
|----------------|--------------------------|
| `npm run dev`  | Development server       |
| `npm run build`| Production build         |
| `npm run preview` | Preview production build |

