"""MARPS server: map viewer, local LLM and route planner behind one port.

Run from the repository root:
    python3 backend/app.py [--port 8765] [--host 127.0.0.1] [--dataset /path/MARPS_Jezero_3D]

Environment:
    OLLAMA_HOST          Ollama server (default http://127.0.0.1:11434; see backend/llm/README.md for tfm-lab)
    MARPS_LLM_MODEL      extraction model (default jezero-extractor, built from backend/llm/Modelfile)
    MARPS_SUMMARY_MODEL  summary model (default jezero-summarizer, from backend/llm/Modelfile.summary)
    JEZERO_DATA          planner layers (default data/jezero)
"""
import argparse
import os
import sys
import threading
from contextlib import asynccontextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# planner/ goes first: its api.py is the planner router (backend/llm/api.py is reached as llm.api).
for path in (ROOT / "planner", ROOT / "backend"):
    if str(path) not in sys.path:
        sys.path.insert(0 if path.name == "planner" else 1, str(path))

from fastapi import APIRouter, Depends, FastAPI, HTTPException  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel, Field, field_validator  # noqa: E402

import api as planner_api  # noqa: E402  (planner/api.py)
from llm import mission as M  # noqa: E402
from reconstructions import DEFAULT_DATASET, build_catalog, build_route  # noqa: E402
from viewer import map_config, terrain_sources  # noqa: E402  (also registers the .mjs/.spz MIME types)

DATASET = Path(os.getenv("MARPS_DATASET", str(DEFAULT_DATASET))).resolve()

def warm_up():
    """Load the planner layers and the two LLMs before the first visitor (Vercel's proxy times out ~30 s)."""
    try:
        planner_api.planner()
        llm = get_llm()
        for model in (M.EXTRACT_MODEL, M.SUMMARY_MODEL):
            llm.chat(model=model, messages=[{"role": "user", "content": "ping"}], options={"num_predict": 1})
        print("MARPS warm-up done (planner + LLM loaded)", flush=True)
    except Exception as e:  # the server still works; the first request will just be slower
        print(f"MARPS warm-up incomplete: {e}", flush=True)


@asynccontextmanager
async def lifespan(_app):
    if os.getenv("MARPS_WARMUP", "1") == "1":
        threading.Thread(target=warm_up, daemon=True).start()
    yield


app = FastAPI(title="MARPS", lifespan=lifespan)
llm_router = APIRouter()

_client = None


def get_llm():
    global _client
    if _client is None:
        _client = M.make_client()
    return _client


class PromptRequest(BaseModel):
    prompt: str = Field(max_length=2000)

    @field_validator("prompt")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("prompt is empty")
        return value


class SummaryRequest(BaseModel):
    report: dict


@llm_router.post("/parse-mission", response_model=M.JezeroMissionRequirements)
def parse_mission(req: PromptRequest, llm=Depends(get_llm)):
    try:
        return M.parse_mission(llm, req.prompt)
    except M.LLMUnavailable as e:
        raise HTTPException(503, str(e))
    except M.LLMBadOutput as e:
        raise HTTPException(502, str(e))


@llm_router.post("/summarize-route")
def summarize_route(req: SummaryRequest, llm=Depends(get_llm)):
    try:
        return {"summary": M.summarize(llm, req.report)}
    except M.LLMUnavailable as e:
        raise HTTPException(503, str(e))
    except (TypeError, KeyError, AttributeError, ValueError) as e:
        raise HTTPException(422, f"report does not look like a /plan-route report: {e}")


@llm_router.get("/llm/health")
def llm_health(llm=Depends(get_llm)):
    try:
        models = [m.model for m in llm.list().models]
    except Exception as e:  # health check: report the failure instead of raising
        return dict(reachable=False, host=M.OLLAMA_HOST, error=str(e))
    return dict(reachable=True, host=M.OLLAMA_HOST, models=models,
                extract_model=M.EXTRACT_MODEL, summary_model=M.SUMMARY_MODEL)


# Same endpoints at the root (documented API) and under /api (what the React frontend calls).
for prefix in ("", "/api"):
    app.include_router(planner_api.router, prefix=prefix)
    app.include_router(llm_router, prefix=prefix)


@app.get("/api/map-config")
def api_map_config():
    return map_config()


@app.get("/api/terrain-sources")
def api_terrain_sources():
    return terrain_sources()


@app.get("/api/reconstructions")
def api_reconstructions():
    return build_catalog(DATASET)


@app.get("/api/traverse")
def api_traverse():
    return build_route(DATASET)


VIEWER = ROOT / "platform/viewer"
WEB_DIST = ROOT / "platform/web/dist"
app.mount("/assets/ctx", StaticFiles(directory=ROOT / "assets/zones/public/layers/ctx"), name="ctx")
for scene in ("cheyava_falls", "ejemplo_malla_NASA"):
    if (DATASET / scene).is_dir():
        app.mount(f"/reconstructions/files/{scene}", StaticFiles(directory=DATASET / scene), name=scene)
# Legacy Leaflet viewer (3D reconstructions, thematic layers): /viewer/. Its absolute paths are mounted too.
for path in ("terrain3d", "data"):
    if (VIEWER / path).is_dir():
        app.mount(f"/{path}", StaticFiles(directory=VIEWER / path), name=f"viewer-{path}")
app.mount("/viewer", StaticFiles(directory=VIEWER, html=True), name="viewer")
# React frontend (npm run build in platform/web); without a build, "/" serves the legacy viewer.
app.mount("/", StaticFiles(directory=WEB_DIST if WEB_DIST.is_dir() else VIEWER, html=True), name="web")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    import uvicorn
    print(f"MARPS · http://{args.host}:{args.port} · LLM at {M.OLLAMA_HOST}", flush=True)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
