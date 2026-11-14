# Local LLM (Ollama) and unified server

Two small models, both built from `gemma4:e2b`, run on **tfm-lab** (RTX 3060 6 GB, Ollama in user space):

| Model | Modelfile | Input → output |
|---|---|---|
| `jezero-extractor` | [Modelfile](Modelfile) | mission text → JSON `{human, origin, destination, power, route_preference, safety, science_targets, science_detour, return_to_origin}` (same as the planner `Mission`) |
| `jezero-summarizer` | [Modelfile.summary](Modelfile.summary) | grounded facts of the planned route → 1–2 sentences justifying it and quoting the gains over a classic shortest-path A* |

The summarizer does not read the raw report: `summary_facts()` in [mission.py](mission.py) lists only real improvements (> 0) and the trade-offs separately, so the model cannot oversell.

## Run everything

```bash
pip install -r backend/requirements.txt -r planner/requirements.txt
cd platform/web && npm install && npm run build && cd ../..
backend/run.sh            # opens an SSH tunnel to tfm-lab and serves http://127.0.0.1:8765
```

`run.sh` uses `LLM_SSH_HOST` (default `tfm-lab`); with `OLLAMA_HOST=http://…:11434` set it skips the tunnel. Frontend dev mode: `cd platform/web && npm run dev` (proxies `/api` to `MARPS_API`, default `http://127.0.0.1:8765`; also `/viewer`, `/reconstructions`…).

Endpoints (at the root and under `/api`): `POST /parse-mission`, `POST /plan-route`, `POST /summarize-route`, `GET /places`, `GET /llm/health`. The legacy Leaflet viewer with 3D reconstructions is at `/viewer/`.

Env: `OLLAMA_HOST`, `MARPS_LLM_MODEL`, `MARPS_SUMMARY_MODEL`, `JEZERO_DATA`.

## Install the models on a machine

```bash
# Ollama without root (tfm-lab): https://ollama.com/download/ollama-linux-amd64.tar.zst → ~/ollama
ollama pull gemma4:e2b
ollama create jezero-extractor -f backend/llm/Modelfile
ollama create jezero-summarizer -f backend/llm/Modelfile.summary
```

On tfm-lab Ollama runs as the user service `ollama.service` (127.0.0.1:11434, `OLLAMA_KEEP_ALIVE=-1`, `OLLAMA_MAX_LOADED_MODELS=2`, linger enabled). First request after a restart takes ~1.5 min (GPU load); then 0.4–2 s.

Tests: `python -m pytest backend/test_app.py` (fake LLM, no Ollama needed).
