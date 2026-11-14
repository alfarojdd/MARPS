"""Local SLM (Ollama) for MARPS: mission text → planner parameters, planner report → astronaut summary.

The SLM never plans: it fills in the `mission` block of POST /plan-route and rewords the numbers the
planner already computed.
"""
import json
import os
from typing import Literal

from pydantic import BaseModel, Field

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
EXTRACT_MODEL = os.getenv("MARPS_EXTRACT_MODEL", "jezero-extractor")
SUMMARY_MODEL = os.getenv("MARPS_SUMMARY_MODEL", "jezero-summarizer")

ScienceName = Literal["aqueous", "carbonates", "clays", "smectites", "kaolinite", "olivine", "pyroxene",
                      "delta", "crater_floor"]


class ScienceTarget(BaseModel):
    target: ScienceName
    priority: float = Field(1.0, ge=0.1, le=1.0)


class JezeroMissionRequirements(BaseModel):
    """Same fields as planner/api.py `Mission`, but origin and destination may be missing from the text."""
    human: bool = True
    origin: str | None = None
    destination: str | None = None
    power: bool = False
    route_preference: Literal["shortest", "fastest"] | None = None
    safety: Literal["low", "normal", "high"] = "normal"
    science_targets: list[ScienceTarget] = []
    science_detour: Literal["low", "medium", "high"] = "medium"
    return_to_origin: bool = False


class SLMUnavailable(RuntimeError):
    """Ollama could not be reached."""


class SLMBadOutput(RuntimeError):
    """The model answered something that does not fit the schema."""


def make_client():
    import ollama
    return ollama.Client(host=OLLAMA_HOST, timeout=120)


def _transport_errors():
    errors = [ConnectionError, OSError]
    try:
        import httpx
        import ollama
        errors += [httpx.HTTPError, ollama.ResponseError]  # timeouts, model not pulled, ...
    except ImportError:
        pass
    return tuple(errors)


def _chat(client, **kwargs):
    try:
        return client.chat(**kwargs).message.content
    except _transport_errors() as e:
        raise SLMUnavailable(f"SLM server unavailable at {OLLAMA_HOST}: {e}") from e


def parse_mission(client, text: str) -> JezeroMissionRequirements:
    content = _chat(client, model=EXTRACT_MODEL, messages=[{"role": "user", "content": text}],
                    format=JezeroMissionRequirements.model_json_schema(), options={"temperature": 0})
    try:
        return JezeroMissionRequirements.model_validate_json(content)
    except ValueError as e:
        raise SLMBadOutput(f"SLM output does not match the mission schema: {e}") from e


_TARGET_NAMES = {"aqueous": "water-related terrain", "carbonates": "carbonates", "clays": "clays",
                 "smectites": "smectites", "kaolinite": "kaolinite", "olivine": "olivine",
                 "pyroxene": "pyroxene", "delta": "delta sediments", "crater_floor": "the crater floor"}


def _pct(value):
    return f"{abs(round(value))}%"


def summary_facts(report: dict) -> dict:
    """Grounded facts for the summariser: only improvements that are real (> 0) are listed as gains, and
    the trade-offs against the classic shortest-path A* are listed separately, so the model cannot oversell."""
    route, comp = report.get("route") or {}, report.get("comparison") or {}
    mission = report.get("mission") or {}
    gains = []
    for key, label in (("max_pitch_reduction_deg", "max slope {:.1f} deg lower"),
                       ("max_cross_slope_reduction_deg", "cross slope {:.1f} deg lower")):
        if comp.get(key, 0) >= 0.5:
            gains.append(label.format(comp[key]))
    for key, label in (("rough_km_avoided", "{:.1f} km less rough terrain"), ("soft_km_avoided", "{:.1f} km less soft sand"),
                       ("dunes_km_avoided", "{:.1f} km fewer dunes"), ("shadow_km_avoided", "{:.1f} km less shadow")):
        if comp.get(key, 0) >= 0.05:
            gains.append(label.format(comp[key]))
    for key, value in comp.items():
        if key.startswith("on_") and key.endswith("_km_gained") and value >= 0.1:
            name = key[3:-len("_km_gained")]
            gains.append(f"{value:.1f} km more over {_TARGET_NAMES.get(name, name)}")
    for key, label in (("energy_saved_pct", "{} less energy"), ("time_saved_pct", "{} less time")):
        if comp.get(key, 0) >= 1:
            gains.append(label.format(_pct(comp[key])))
    costs = []
    if comp.get("extra_distance_pct", 0) >= 1:
        costs.append(f"{_pct(comp['extra_distance_pct'])} longer distance")
    for key, label in (("energy_saved_pct", "more energy"), ("time_saved_pct", "more time")):
        if comp.get(key, 0) <= -1:
            costs.append(f"{_pct(comp[key])} {label}")
    return {
        "feasible": report.get("feasible", True),
        "crewed": mission.get("human"),
        "safety": mission.get("safety"),
        "origin": mission.get("origin"), "destination": mission.get("destination"),
        "science_targets": [_TARGET_NAMES.get(t["target"], t["target"]) for t in mission.get("science_targets", [])],
        "distance_km": route.get("distance_km"), "duration_h": route.get("duration_h", route.get("time_h")),
        "arrival": route.get("arrival"), "battery_end_pct": route.get("battery_end_pct"),
        "science_stops": len(route.get("science_stops") or []),
        "charging_stop": None if not route.get("charging_stop") else {
            "stop_at": route["charging_stop"].get("arrive"), "charge_hours": route["charging_stop"].get("charge_hours")},
        "science_stop_minutes": sum(s.get("dwell_min", 0) for s in route.get("science_stops") or []),
        "gains_vs_classic_astar": gains, "costs_vs_classic_astar": costs,
        "warnings": [w["message"] for w in report.get("warnings", [])][:3],
    }


def summarize(client, report: dict) -> str:
    facts = json.dumps(summary_facts(report), separators=(",", ":"))
    return _chat(client, model=SUMMARY_MODEL, think=False, options={"temperature": 0.2, "num_predict": 120},
                 messages=[{"role": "user", "content": facts}]).strip()
