import numpy as np
import pytest
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

import planner as P


def _random_problem(H, W, c_climb, seed=0):
    """Costes aleatorios que cumplen coste ≥ L + c_climb·max(Δh, 0), como los del planificador."""
    rng = np.random.default_rng(seed)
    elev = rng.normal(0, 30, H * W).cumsum() % 200
    cost = np.full((16, H * W), np.inf)
    for d, (mr, mc) in enumerate(P.MOVES):
        L = P.RES * np.hypot(mr, mc)
        for r in range(H):
            for c in range(W):
                if 0 <= r + mr < H and 0 <= c + mc < W and rng.random() > 0.1:
                    n, nb = r * W + c, (r + mr) * W + c + mc
                    cost[d, n] = L * (1 + 3 * rng.random()) + c_climb * max(elev[nb] - elev[n], 0)
    return cost, elev


@pytest.mark.parametrize("c_climb", [0.0, 5.0])
def test_astar_matches_scipy_dijkstra(c_climb):
    H, W = 30, 40
    cost, elev = _random_problem(H, W, c_climb)
    rows, cols, vals = [], [], []
    for d, (mr, mc) in enumerate(P.MOVES):
        for n in np.where(np.isfinite(cost[d]))[0]:
            rows.append(n); cols.append((n // W + mr) * W + n % W + mc); vals.append(cost[d, n])
    ref = dijkstra(csr_matrix((vals, (rows, cols)), shape=(H * W, H * W)), indices=0)
    for goal in (H * W - 1, 15 * W + 20, 7):
        g, parent, _ = P._search(cost, H, W, 0, goal, 1.0, c_climb, elev, P.RES, P.NO_STOPS)
        assert np.isclose(g[goal], ref[goal])
        path = P._path(parent, 0, goal)
        assert path[0] == 0 and path[-1] == goal


def test_params_validation():
    with pytest.raises(ValueError):
        P.Params.from_dict({"safety": "extreme"})
    with pytest.raises(ValueError):
        P.Params.from_dict({"science_targets": [{"target": "gold"}]})
    p = P.Params.from_dict({"human": True, "extra_field_from_llm": 1, "science_detour": "high"})
    assert p.human and p.safety == "normal" and p.detour == 1.0


@pytest.fixture(scope="module")
def planner():
    if not (P.CACHE.exists() or (P.DATA / "layers20m/elev_ctx.tif").exists()):
        pytest.skip("sin datos")
    return P.Planner()


@pytest.mark.parametrize("safety", ["low", "high"])
def test_hard_constraints_hold_on_real_grid(planner, safety):
    r = planner.plan(P.Params(origin="landing_site", destination="delta_top", safety=safety))
    assert r["ok"]
    lim = P.SAFETY[safety]
    assert r["metrics"]["max_pitch_deg"] <= lim["max_pitch"] + 1e-3
    assert r["metrics"]["max_cross_deg"] <= lim["max_cross"] + 1e-3


def test_heuristic_is_admissible_on_real_grid(planner):
    """El A* con la cota de subida da el mismo coste que sin heurística (Dijkstra)."""
    p = P.Params(origin="crater_floor_south", destination="delta_top", power=True)
    cost, hflat, c_climb = P.build_costs(planner.F, p)
    W = planner.W
    a = P.resolve_place(planner.grid, p.origin)
    b = P.resolve_place(planner.grid, p.destination)
    a, b = a[0] * W + a[1], b[0] * W + b[1]
    g1, _, ex1 = planner.astar(cost, a, b, hflat, c_climb)
    g0, _, ex0 = planner.astar(cost, a, b, 0.0, 0.0)
    assert np.isclose(g1[b], g0[b], rtol=1e-6)
    assert ex1 < ex0


def test_return_to_origin_closes_the_loop(planner):
    r = planner.plan(P.Params(origin="landing_site", destination="delta_top", return_to_origin=True))
    assert r["path"][0] == r["path"][-1]


def _report(planner, mission, system):
    import report as R
    rep, _, _ = R.build_report(planner, {"origin": "crater_floor_south", "destination": "delta_top", **mission}, system)
    return rep, {w["code"] for w in rep["warnings"]}


def test_report_ok_compares_against_classic(planner):
    rep, codes = _report(planner, {"power": True}, {"start_hour": 9, "battery_kwh": 35})
    assert rep["feasible"] and not codes
    assert rep["comparison"]["energy_saved_pct"] > 0
    assert rep["route"]["battery_end_kwh"] == pytest.approx(35 - rep["route"]["energy_kwh"], abs=0.01)


def test_report_flags_late_arrival(planner):
    rep, codes = _report(planner, {"human": True}, {"start_hour": 16.5, "battery_kwh": 40})
    assert "ARRIVAL_AFTER_DAYLIGHT" in codes and not rep["feasible"]  # con tripulación es crítico


def test_report_charging_stop_leaves_reserve(planner):
    rep, codes = _report(planner, {"power": True}, {"start_hour": 9, "battery_kwh": 14, "battery_capacity_kwh": 40})
    if "CHARGING_STOP_REQUIRED" in codes:
        assert rep["route"]["charging_stop"]["charge_hours"] > 0
        assert rep["route"]["battery_end_kwh"] >= 0.2 * 40 - 0.01
    else:
        assert not rep["feasible"]
