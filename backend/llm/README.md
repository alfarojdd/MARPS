# Jezero Crater Mission Extractor (Backend)

Natural-language to structured JSON extractor built on **Ollama (`gemma4:e2b`)** and **FastAPI** for Mars mission pathfinding inside Jezero Crater (MRO CTX bbox: `77.16°E–77.70°E, 18.21°N–18.72°N`).

## Prerequisites

- **Ollama** installed and running (`ollama --version`)
- **Python 3.10+**
- **Cloudflared** (optional, required only if exposing your local server to the hosted Vercel frontend)

---

## Setup and run (from the `marps/` root)

1. **Build the custom Ollama model**
   This automatically pulls `gemma4:e2b` if not already cached and bakes the system prompt, parameters, and few-shot examples from `Modelfile`:
   ```bash
   ollama create jezero-extractor -f backend/Modelfile
   ```

2. **Create a virtual environment and install Python dependencies**

   **Windows (PowerShell):**
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r backend\requirements.txt
   ```

   **macOS / Linux:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r backend/requirements.txt
   ```

3. **Start the FastAPI server**
   ```bash
   uvicorn backend.api:app --host 0.0.0.0 --port 8000
   ```
   *(If running from inside `marps/backend/`, use `uvicorn api:app --host 0.0.0.0 --port 8000` instead).*

---

## Expose the local backend to Vercel (Cloudflare Quick Tunnel)

To allow the hosted Vercel web app (and multiple devices/users) to reach your locally running model:

1. Keep `uvicorn` running in your first terminal.
2. Open a second terminal and run:
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```
3. Copy the generated `https://*.trycloudflare.com` URL and set it as your API base URL in Vercel's Environment Variables (e.g., `NEXT_PUBLIC_API_URL` or `VITE_API_URL`), then redeploy if needed.

> **Tip for multi-user demos:** Start Ollama with `OLLAMA_NUM_PARALLEL=4 OLLAMA_KEEP_ALIVE=-1 ollama serve` to keep the model warm in memory and handle concurrent requests from multiple devices smoothly.

---

## API reference

### `POST /parse-mission`

Extracts mission routing requirements from natural language into strict, schema-validated JSON.

**Schema fields:**
- `human` (`boolean`): Defaults to `true`. Set to `false` only when an uncrewed/robotic asset (e.g., rover, drone, autonomous) is explicitly specified.
- `origin` (`string | null`): Starting Jezero Crater landmark name or coordinates, or `null` if omitted.
- `destination` (`string | null`): Target Jezero Crater landmark name or coordinates, or `null` if omitted.
- `power` (`boolean`): `true` if the pathfinder must include a solar-rich/sunlit surface for charging along the route; `false` otherwise.
- `route_preference` (`"shortest" | "fastest" | null`): Route optimization preference, or `null` if unspecified/neutral.

**Request body:**
```json
{
  "prompt": "Dispatch an autonomous rover from Octavia E. Butler Landing to Three Forks on the Western Delta, low battery so it needs solar exposure to charge, take the fastest traverse."
}
```

**Response (`200 OK`):**
```json
{
  "human": false,
  "origin": "Octavia E. Butler Landing",
  "destination": "Three Forks",
  "power": true,
  "route_preference": "fastest"
}
```

**Quick test with cURL:**
```bash
curl -X POST http://localhost:8000/parse-mission \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Route a team from 18.44N, 77.45E to Belva Crater rim, minimal distance to conserve oxygen."}'
```
