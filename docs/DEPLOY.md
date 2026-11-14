# Deployment: Vercel interface + local SLM and planner host

```
Browser ──► Vercel (platform/web, static React build)
               │  vercel.json rewrites /api, /viewer, /reconstructions, /data, /terrain3d, /assets/ctx
               ▼
        https://tfm-lab.tail9f0864.ts.net   (Tailscale Funnel: public HTTPS → host:8765)
               ▼
        host: marps.service (backend/app.py: planner + API)  ──►  ollama.service (127.0.0.1:11434, GPU)
```

The planner needs about 2 GB of RAM, Numba and ~270 MB of rasters, and the small language models need a GPU, so neither can run as a Vercel function. Vercel serves the static interface and proxies the API calls to the host (`tfm-lab`, a laptop with an RTX 3060 6 GB). The browser always talks to the Vercel domain (same origin, no CORS). Ollama is never exposed: only the MARPS server on port 8765 is.

## 1. Host setup

| What | Where |
|---|---|
| Ollama (user space, no root needed) | `~/ollama`, user service `~/.config/systemd/user/ollama.service`: `127.0.0.1:11434`, `OLLAMA_KEEP_ALIVE=-1`, `OLLAMA_MAX_LOADED_MODELS=2` |
| Models | `jezero-extractor`, `jezero-summarizer`, created from `backend/slm/Modelfile` and `Modelfile.summary` ([backend/slm/README.md](../backend/slm/README.md)) |
| Repository and virtual environment | `~/MARPS`, `~/MARPS/.venv` (Python 3.10) |
| Planner data | `~/marps-data/jezero` (stack, layers and caches), selected with `JEZERO_DATA` |
| MARPS server | [`backend/deploy/marps.service`](../backend/deploy/marps.service) → `~/.config/systemd/user/marps.service` (`127.0.0.1:8765`) |

Install the server:

```bash
cd ~/MARPS
python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt -r planner/requirements.txt
.venv/bin/python backend/prepare_viewer.py            # Three.js libraries
.venv/bin/python backend/prepare_reconstructions.py   # local surface models
cp backend/deploy/marps.service ~/.config/systemd/user/
systemctl --user enable --now marps
loginctl enable-linger $USER                          # start at boot without a login
```

The 3D relief files are not in Git. Generate them with `data/jezero/pipeline/build_terrain3d.py` ([TERRAIN_3D.md](TERRAIN_3D.md)) or copy `platform/viewer/data/terrain3d` from a machine that has them:

```bash
rsync -a platform/viewer/data/terrain3d HOST:MARPS/platform/viewer/data/
```

Without them `/api/terrain-sources` is empty and the 3D button is disabled.

Update after a push:

```bash
ssh HOST 'cd ~/MARPS && git pull && systemctl --user restart marps'
```

Logs: `journalctl --user -u marps -f`. At start-up the server loads the planner layers and both models (`MARPS_WARMUP=0` disables it), so the first request is fast.

## 2. Public HTTPS with Tailscale Funnel

1. In the Tailscale admin console, allow Funnel for the node (it offers "Enable Funnel" the first time you run the command below).
2. On the host:
   ```bash
   sudo tailscale funnel --bg 8765
   tailscale funnel status        # https://tfm-lab.tail9f0864.ts.net → http://127.0.0.1:8765
   ```
3. Check from any network: `curl https://tfm-lab.tail9f0864.ts.net/api/slm/health`.

If the node name changes, update the six destinations in [`platform/web/vercel.json`](../platform/web/vercel.json).

## 3. Vercel

From `platform/web`, with the Vercel CLI:

```bash
npx vercel login
npx vercel --prod
```

Create a new project when asked (lowercase name, for example `marps-bellona`) and accept the defaults: framework Vite, build `npm run build`, output `dist`. No environment variables are needed. To redeploy automatically on each push, connect the GitHub repository in the Vercel dashboard and set **Root Directory** to `platform/web`.

## Operational notes

- A new route takes 2–20 s (more with science targets). Vercel stops proxied requests that exceed about 30 s.
- The host must stay on, awake and connected. If it sleeps, the interface loads but planning reports that the server cannot be reached.
- The SLM endpoints have no authentication; prompts are limited to 2000 characters and the interactive API documentation is disabled. Turn the Funnel off when the demo is over: `sudo tailscale funnel --https=443 off`.
