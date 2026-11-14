"""Tests for the unified MARPS server (backend/app.py) with a fake LLM client.

Run: python3 -m pytest backend/test_app.py -q
"""
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import os

os.environ["MARPS_WARMUP"] = "0"

import app as A  # noqa: E402
from llm import mission as M  # noqa: E402


class FakeLLM:
    def __init__(self, reply=None, error=None):
        self.reply, self.error, self.calls = reply, error, []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        content = self.reply if isinstance(self.reply, str) else json.dumps(self.reply)
        return SimpleNamespace(message=SimpleNamespace(content=content))


@pytest.fixture
def client():
    yield TestClient(A.app)
    A.app.dependency_overrides.clear()


def use_llm(fake):
    A.app.dependency_overrides[A.get_llm] = lambda: fake
    return fake


def test_parse_mission_returns_full_schema_with_defaults(client):
    fake = use_llm(FakeLLM({"human": True, "origin": "landing_site", "destination": "delta_top",
                            "power": False, "route_preference": None,
                            "science_targets": [{"target": "carbonates", "priority": 1}]}))
    r = client.post("/parse-mission", json={"prompt": "Go from the landing site to the delta looking for carbonates"})
    assert r.status_code == 200
    body = r.json()
    assert body["destination"] == "delta_top"
    assert body["science_targets"] == [{"target": "carbonates", "priority": 1.0}]
    assert body["safety"] == "normal" and body["science_detour"] == "medium" and body["return_to_origin"] is False
    assert fake.calls[0]["model"] == M.EXTRACT_MODEL
    assert fake.calls[0]["format"] == M.JezeroMissionRequirements.model_json_schema()


def test_parse_mission_unreachable_llm_is_503(client):
    use_llm(FakeLLM(error=ConnectionError("refused")))
    r = client.post("/parse-mission", json={"prompt": "anything"})
    assert r.status_code == 503
    assert "LLM" in r.json()["detail"]


def test_parse_mission_invalid_llm_output_is_502(client):
    use_llm(FakeLLM('{"human": "maybe"'))
    r = client.post("/parse-mission", json={"prompt": "anything"})
    assert r.status_code == 502


def test_parse_mission_rejects_empty_prompt(client):
    use_llm(FakeLLM({}))
    assert client.post("/parse-mission", json={"prompt": "  "}).status_code == 422


EXAMPLE = {"feasible": True,
           "mission": {"human": True, "origin": "landing_site", "destination": "delta_top", "safety": "high",
                       "science_targets": [{"target": "carbonates", "priority": 1.0}], "power": False},
           "route": {"distance_km": 16.4, "duration_h": 3.55, "arrival": "12:28", "battery_end_pct": 24.9,
                     "science_stops": [{}, {}], "charging_stop": None, "waypoints_lonlat": [[77.4, 18.4]] * 60},
           "comparison": {"energy_saved_pct": -9.3, "time_saved_pct": -4.3, "extra_distance_pct": 63.4,
                          "max_pitch_reduction_deg": 11.5, "max_cross_slope_reduction_deg": 9.7,
                          "rough_km_avoided": 3.19, "soft_km_avoided": 0.0, "dunes_km_avoided": 0.67,
                          "shadow_km_avoided": 0.0, "on_carbonates_km_gained": 7.89},
           "warnings": []}


def test_summary_facts_keep_only_real_gains_and_state_costs():
    facts = M.summary_facts(EXAMPLE)
    assert facts["distance_km"] == 16.4 and facts["arrival"] == "12:28" and facts["science_stops"] == 2
    gains = " | ".join(facts["gains_vs_classic_astar"])
    assert "11.5" in gains and "9.7" in gains and "3.2 km" in gains and "7.9 km" in gains and "carbonates" in gains
    assert "soft" not in gains and "shadow" not in gains and "energy" not in gains
    assert facts["costs_vs_classic_astar"] == ["63% longer distance", "9% more energy", "4% more time"]
    assert "waypoints_lonlat" not in json.dumps(facts)


def test_summarize_route_uses_summary_model_and_facts(client):
    fake = use_llm(FakeLLM("  Safe 16 km route with 9.7 deg less cross slope.  "))
    r = client.post("/summarize-route", json={"report": EXAMPLE})
    assert r.status_code == 200
    assert r.json() == {"summary": "Safe 16 km route with 9.7 deg less cross slope."}
    assert fake.calls[0]["model"] == M.SUMMARY_MODEL
    sent = json.loads(fake.calls[0]["messages"][-1]["content"])
    assert sent["gains_vs_classic_astar"] and "waypoints_lonlat" not in fake.calls[0]["messages"][-1]["content"]


def test_summarize_route_llm_down_is_503(client):
    use_llm(FakeLLM(error=ConnectionError("refused")))
    assert client.post("/summarize-route", json={"report": EXAMPLE}).status_code == 503


def test_summarize_route_malformed_report_is_422(client):
    use_llm(FakeLLM("x"))
    bad = {"comparison": {"energy_saved_pct": None}, "warnings": [{}]}
    assert client.post("/summarize-route", json={"report": bad}).status_code == 422


def test_parse_mission_rejects_huge_prompt(client):
    use_llm(FakeLLM({}))
    assert client.post("/parse-mission", json={"prompt": "x" * 5000}).status_code == 422


def test_llm_health_reports_unreachable(client):
    use_llm(FakeLLM(error=ConnectionError("refused")))
    r = client.get("/llm/health")
    assert r.status_code == 200
    assert r.json()["reachable"] is False


def test_legacy_viewer_is_served_under_viewer(client):
    r = client.get("/viewer/")
    assert r.status_code == 200 and "mission.mjs" in r.text
    assert client.get("/viewer/mission.mjs").headers["content-type"].startswith("text/javascript")
    assert client.get("/api/map-config").json()["radius"] == 3396190


def test_places_endpoint_comes_from_planner_at_root_and_api(client):
    for path in ("/places", "/api/places"):
        places = client.get(path).json()["places"]
        assert "landing_site" in places and "delta_top" in places


def test_frontend_calls_api_prefix_for_llm(client):
    use_llm(FakeLLM({"destination": "delta_top"}))
    r = client.post("/api/parse-mission", json={"prompt": "go to the delta"})
    assert r.status_code == 200 and r.json()["destination"] == "delta_top"
