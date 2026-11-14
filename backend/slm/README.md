# Local small language models (SLM)

MARPS uses two small language models (SLMs), both derived from **Gemma 4 E2B** (`gemma4:e2b`, about 2 billion effective parameters) and served locally by [Ollama](https://ollama.com). They run on a single 6 GB GPU and answer in 0.4–3 s once loaded, so the system works without a cloud API (on Mars the link to Earth has a 4–24 minute delay).

Neither model plans anything. The route is always computed by the deterministic planner (`planner/`) and its safety limits are always enforced. The models only translate between text and structured data:

| Model | Definition | Input → output |
|---|---|---|
| `jezero-extractor` | [Modelfile](Modelfile) | Mission text → JSON `{human, origin, destination, power, route_preference, safety, science_targets, science_detour, return_to_origin}`, the `mission` block of the planner request. Output is constrained by a JSON schema and validated with Pydantic. |
| `jezero-summarizer` | [Modelfile.summary](Modelfile.summary) | Verified facts about the planned route → one or two sentences that justify the choice (charging stop, safety, science stops) and quote the gains over a classic shortest-path A*. |

The summariser never reads the raw planner report. `summary_facts()` in [mission.py](mission.py) distils it into facts: only real improvements are listed as gains and the trade-offs (longer path, more energy) are listed separately, so the model cannot oversell the route.

## Install the models

```bash
ollama pull gemma4:e2b
ollama create jezero-extractor  -f backend/slm/Modelfile
ollama create jezero-summarizer -f backend/slm/Modelfile.summary
```

Both Modelfiles bake the system prompt and few-shot examples into the model, with `temperature` 0 (extractor) and 0.2 (summariser).

## Use

The models are called by the MARPS server ([`backend/app.py`](../app.py)), which exposes:

| Endpoint | Purpose |
|---|---|
| `POST /api/parse-mission` | `{"prompt": "..."}` → mission JSON. Prompts are limited to 2000 characters. |
| `POST /api/summarize-route` | `{"report": {...}}` (the `report` of `/plan-route`) → `{"summary": "..."}` |
| `GET /api/slm/health` | Whether Ollama is reachable and which models it has |

Errors: `503` when Ollama is unreachable, `502` when the model returns output that does not fit the schema, `422` for a malformed request.

```bash
curl -X POST http://127.0.0.1:8765/api/parse-mission -H "Content-Type: application/json" \
  -d '{"prompt": "Route a team from the landing site to Belva crater, safest path."}'
```

Configuration (environment variables): `OLLAMA_HOST` (default `http://127.0.0.1:11434`), `MARPS_EXTRACT_MODEL`, `MARPS_SUMMARY_MODEL`.

## Running the models on another machine

[`backend/run.sh`](../run.sh) opens an SSH tunnel to a host that runs Ollama (`SLM_SSH_HOST`, default `tfm-lab`) and starts the server locally. [docs/DEPLOY.md](../../docs/DEPLOY.md) describes the full deployment, where the server itself runs on that host.

## Tests

```bash
python -m pytest backend/test_app.py
```

The tests replace the model client with a fake, so Ollama is not needed.
