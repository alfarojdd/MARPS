"""Traverse report for the helmet SLM summary.

Input: mission parameters (produced by the SLM) + system state (known by the vehicle: time, battery).
Output: a JSON with the route, the comparison against the classic A*, the "why" and light and battery warnings.
If the battery is not enough, it proposes the energy-saving route and, if needed, a solar charging stop in the
sunniest area near the route (and replans through it).

With the shadow map (`shadows.py`), the daylight window comes from SunAngle.csv, the charging site is the one
receiving the most direct light during charging (no shadow) and the charging time uses that light hour by hour.
Report times are local solar time (LTST); `time_h`/`duration_h` are Earth hours.
"""
from dataclasses import dataclass, asdict

import numpy as np
from scipy import ndimage

import planner as P

SUNRISE, SUNSET, DAYLIGHT_MARGIN_H = 6.0, 18.0, 0.5   # LTST; only if there is no shadow map
EARTH_TO_LTST = 3600 / 3698.9                         # Earth hours → local solar hours
DWELL_H = 1 / 3                                       # time per science stop
P_PARKED = 150.0                                      # W with the vehicle stopped (excluding life support)
P_SOLAR_PARKED = 3000.0                               # peak W with the panel deployed while charging
CHARGE_SEARCH_M = 1000                                # look for a charging site within 1 km of the route


@dataclass
class SystemState:
    start_hour: float = 9.0              # local solar departure time (system clock)
    battery_kwh: float = 30.0            # current charge
    battery_capacity_kwh: float = 40.0
    reserve_pct: float = 20.0            # minimum margin on arrival

    @classmethod
    def from_dict(cls, d):
        return cls(**{k: v for k, v in (d or {}).items() if k in cls.__dataclass_fields__})


def sun_factor(h):
    """Fraction of peak solar power by time of day (no shadows or season)."""
    return np.clip(np.sin(np.pi * (np.asarray(h) - SUNRISE) / (SUNSET - SUNRISE)), 0, None)


def hhmm(h):
    h = max(h, 0)
    return f"{int(h):02d}:{int(round((h % 1) * 60)) % 60:02d}"


def _public(m):
    return {k: (round(v, 3) if isinstance(v, float) else v) for k, v in m.items()
            if not k.startswith("cum_") and k != "cost_breakdown"}


def _timeline(m, n_stops, sysst, p):
    p_parked = P_PARKED + (P.VEHICLE["p_life_support"] if p.human else 0)
    dwell_h = n_stops * DWELL_H
    duration = m["time_h"] + dwell_h
    energy = m["energy_kwh"] + p_parked * dwell_h / 1000
    return duration, energy


def _window(pl):
    if pl.sun is not None:
        return pl.sun.sunrise, pl.sun.sunset, pl.sun.source
    return SUNRISE, SUNSET, "fixed 06:00-18:00 window (no shadow map)"


def _charge_hours(pl, deficit_kwh, start_h, spot, p):
    """Stationary charging hours to recover deficit_kwh starting at start_h. None if there is not enough daylight."""
    p_parked = P_PARKED + (P.VEHICLE["p_life_support"] if p.human else 0)
    _, sunset, _ = _window(pl)
    got, h, dt = 0.0, start_h, 0.05
    r, c = spot["rc"]
    while got < deficit_kwh:
        if h > sunset - DAYLIGHT_MARGIN_H:
            return None
        light = (float(pl.sun.at([h], [r], [c])[0]) if pl.sun is not None
                 else spot["insol"] * float(sun_factor(h)))
        got += (P_SOLAR_PARKED * light - p_parked) * dt / 1000
        h += dt
    return h - start_h


def _charge_spot(pl, path, cum_e, cum_t, battery_kwh, start_hour, deficit_kwh, p):
    """Flat, firm, dune-free charging site within 1 km of the route segment reachable with the battery.

    Each candidate is reached at its own time (that of the nearest route point) and the one that finishes charging
    deficit_kwh first is chosen: arrival + deficit / (solar power with that site's actual light over the next 3 h − consumption).
    With the shadow map this avoids shaded sites; without it the mean insolation and a solar curve are used.
    """
    F, W = pl.F, pl.W
    r, c = path // W, path % W
    reach = np.where(cum_e <= battery_kwh * 0.9)[0]
    if not len(reach):
        return None
    on_path = np.zeros(F["h"].shape, bool)
    on_path[r[reach], c[reach]] = True
    idx_grid = np.full(F["h"].shape, -1, np.int64)
    idx_grid[r[reach], c[reach]] = reach
    dist, (nr, nc) = ndimage.distance_transform_edt(~on_path, return_indices=True)
    ok = (dist * P.RES <= CHARGE_SEARCH_M) & (F["slope"] < 5) & (F["dune"] == 0) & (F["unknown"] == 0)
    cr, cc = np.where(ok)
    if not len(cr):
        return None
    pi = idx_grid[nr[cr, cc], nc[cr, cc]]
    t_c = start_hour + cum_t[pi] * EARTH_TO_LTST  # arrival time of each candidate (excluding the detour)
    if pl.sun is not None:
        hrs = pl.sun.hours[:, None]
        win = (hrs >= t_c[None]) & (hrs <= t_c[None] + 3)
        light = (pl.sun.illum[:, cr, cc] * win).sum(0) / np.maximum(win.sum(0), 1) / 255
    else:
        light = F["insol"][cr, cc] * sun_factor(t_c + 1.5)
    p_parked = P_PARKED + (P.VEHICLE["p_life_support"] if p.human else 0)
    net_kw = (P_SOLAR_PARKED * light - p_parked) / 1000
    finish = np.where(net_kw > 0.05, t_c + max(deficit_kwh, 0.1) / np.maximum(net_kw, 0.05), np.inf)
    k = int(np.argmin(finish))
    if not np.isfinite(finish[k]):
        k = int(np.argmax(light))
    cell = (int(cr[k]), int(cc[k]))
    return dict(rc=cell, insol=float(F["insol"][cell]), light=float(light[k]), path_index=int(pi[k]))


def _why(pl, route, classic_route, p, h):
    """Which cost terms the route avoids compared to the classic A*, measured with this mission's weights."""
    ours = pl.evaluate(route["path"], p, start_hour=h)["cost_breakdown"]
    theirs = pl.evaluate(classic_route["path"], p, start_hour=h)["cost_breakdown"]
    diff = {k: theirs[k] - ours[k] for k in ours}
    gain = sum(v for v in diff.values() if v > 0)
    items = sorted(((k, v) for k, v in diff.items() if v > 0), key=lambda kv: -kv[1])
    return [dict(factor=k, share_pct=round(100 * v / gain, 1)) for k, v in items[:4]] if gain > 0 else []


def build_report(pl, mission: dict, system: dict, classic_route=None):
    p = P.Params.from_dict(mission)
    s = SystemState.from_dict(system)
    h0 = s.start_hour
    route = pl.plan(p, start_hour=h0)
    if not route["ok"]:
        return dict(feasible=False, warnings=[dict(code="NO_ROUTE", severity="critical", message=route["reason"])],
                    mission=asdict(p), system=asdict(s)), route, None
    classic_route = classic_route or pl.plan(P.classic(p), start_hour=h0)
    warnings, suggestions = [], []
    n_stops = len(route["pois"])
    duration, energy = _timeline(route["metrics"], n_stops, s, p)
    sunrise, sunset, sun_source = _window(pl)
    limit = sunset - DAYLIGHT_MARGIN_H
    reserve = s.battery_capacity_kwh * s.reserve_pct / 100

    if not sunrise <= s.start_hour < limit:
        warnings.append(dict(code="NO_DAYLIGHT_AT_DEPARTURE", severity="critical",
                             message=f"Departure at {hhmm(s.start_hour)} is outside the daylight window "
                                     f"({hhmm(sunrise)}-{hhmm(limit)})."))

    charge = None
    if s.battery_kwh - energy < reserve:
        alt = None
        if not p.power:  # is the energy-saving route enough?
            alt_p = P.Params.from_dict({**asdict(p), "power": True})
            alt_r = pl.plan(alt_p, start_hour=h0)
            if alt_r["ok"]:
                _, alt_e = _timeline(alt_r["metrics"], len(alt_r["pois"]), s, p)
                alt = dict(energy_kwh=round(alt_e, 2), battery_end_kwh=round(s.battery_kwh - alt_e, 2),
                           fits_reserve=bool(s.battery_kwh - alt_e >= reserve))
                suggestions.append(dict(code="SWITCH_TO_POWER_SAVING", **alt))
        if alt is None or not alt["fits_reserve"]:
            spot = _charge_spot(pl, route["path"], route["metrics"]["cum_energy_kwh"], route["metrics"]["cum_time_h"],
                                s.battery_kwh, h0, energy + reserve - s.battery_kwh, p)
            if spot is None:
                warnings.append(dict(code="BATTERY_INSUFFICIENT", severity="critical",
                                     message="Battery cannot complete the route and no reachable sunny "
                                             "charging spot was found near it."))
            else:
                rerouted = pl.plan(p, via=[spot["rc"]], stops=route["stops"], pois=route["pois"], start_hour=h0)
                if rerouted["ok"]:  # go through the sunny area and recompute with the new route
                    route = rerouted
                    duration, energy = _timeline(route["metrics"], len(route["pois"]), s, p)
                W = pl.W
                i = int(np.argmin((route["path"] // W - spot["rc"][0]) ** 2 + (route["path"] % W - spot["rc"][1]) ** 2))
                arrive_h = float(s.start_hour + route["metrics"]["cum_time_h"][i] * EARTH_TO_LTST)
                reach_kwh = float(route["metrics"]["cum_energy_kwh"][i])
                deficit = energy + reserve - s.battery_kwh
                hours = _charge_hours(pl, deficit, arrive_h, spot, p)
                lon, lat = P.rc_to_lonlat(pl.grid, *spot["rc"])
                charge = dict(lon=round(float(lon), 5), lat=round(float(lat), 5), rc=spot["rc"], arrive=hhmm(arrive_h),
                              battery_on_arrival_kwh=round(float(s.battery_kwh - reach_kwh), 2),
                              energy_needed_kwh=round(float(deficit), 2),
                              mean_direct_light=round(spot["light"], 3),
                              charge_hours=None if hours is None else round(float(hours), 2))
                if reach_kwh > s.battery_kwh:
                    warnings.append(dict(code="BATTERY_INSUFFICIENT", severity="critical",
                                         message="Battery runs out before reaching the nearest sunny charging spot."))
                elif hours is None:
                    warnings.append(dict(code="CHARGING_DOES_NOT_FIT_DAYLIGHT", severity="critical",
                                         message=f"Needs {deficit:.1f} kWh of solar charge but daylight ends "
                                                 f"before it can be collected."))
                else:
                    duration += hours / EARTH_TO_LTST  # charging was measured in LTST hours
                    energy -= deficit  # the recharged energy
                    warnings.append(dict(code="CHARGING_STOP_REQUIRED", severity="warning",
                                         message=f"Stop {hours:.1f} h at a sunny spot ({lon:.4f}E, {lat:.4f}N), "
                                                 f"arriving {hhmm(arrive_h)}, to recharge {deficit:.1f} kWh."))
    battery_end = s.battery_kwh - energy
    if battery_end < 0 and not any(w["code"] == "BATTERY_INSUFFICIENT" or "CHARGING" in w["code"] and
                                   w["severity"] == "critical" for w in warnings):
        warnings.append(dict(code="BATTERY_INSUFFICIENT", severity="critical",
                             message=f"Battery runs out ({battery_end:.1f} kWh at arrival)."))
    elif battery_end < reserve and charge is None:
        warnings.append(dict(code="BATTERY_BELOW_RESERVE", severity="warning",
                             message=f"Arrives with {battery_end:.1f} kWh, below the {reserve:.1f} kWh reserve."))
    arrival = s.start_hour + duration * EARTH_TO_LTST
    if arrival > limit:
        warnings.append(dict(code="ARRIVAL_AFTER_DAYLIGHT", severity="critical" if p.human else "warning",
                             message=f"Estimated arrival {hhmm(arrival)} is after the daylight limit "
                                     f"{hhmm(limit)} ({arrival - limit:.1f} h late)."))

    m = route["metrics"]
    per_target = P.interest_map(pl.grid, p.science_targets)[1] if p.science_targets else {}
    mc = pl.evaluate(classic_route["path"], p, per_target, h0)  # same vehicle and crew; only the path changes
    if p.human and m.get("shadow_pct", 0) > 15:
        warnings.append(dict(code="ROUTE_IN_SHADOW", severity="warning",
                             message=f"{m['shadow_pct']:.0f}% of the route is in terrain shadow (cold, low visibility)."))
    pct = lambda a, b: round(100 * (b - a) / b, 1) if b else 0.0
    comparison = dict(
        energy_saved_pct=pct(m["energy_kwh"], mc["energy_kwh"]),
        drive_energy_saved_pct=pct(m["drive_kwh"], mc["drive_kwh"]),
        time_saved_pct=pct(m["time_h"], mc["time_h"]),
        extra_distance_pct=round(-pct(m["distance_km"], mc["distance_km"]), 1),
        max_pitch_reduction_deg=round(mc["max_pitch_deg"] - m["max_pitch_deg"], 1),
        max_cross_slope_reduction_deg=round(mc["max_cross_deg"] - m["max_cross_deg"], 1),
        rough_km_avoided=round(mc["rough_km"] - m["rough_km"], 2),
        soft_km_avoided=round(mc["soft_km"] - m["soft_km"], 2),
        dunes_km_avoided=round(mc["dunes_km"] - m["dunes_km"], 2),
    )
    if "shadow_km" in m:
        comparison["shadow_km_avoided"] = round(mc["shadow_km"] - m["shadow_km"], 2)
    for k in (k for k in m if k.startswith("on_")):
        comparison[f"{k[:-3]}_km_gained"] = round(m[k] - mc.get(k, 0.0), 2)
    W = pl.W
    step = max(1, len(route["path"]) // 60)
    waypoints = [[round(v, 5) for v in P.rc_to_lonlat(pl.grid, n // W, n % W)] for n in route["path"][::step]]
    report = dict(
        feasible=not any(w["severity"] == "critical" for w in warnings),
        mission={k: v for k, v in asdict(p).items() if k != "context_free"}, system=asdict(s),
        sun=dict(source=sun_source, sunrise=hhmm(sunrise), sunset=hhmm(sunset), daylight_limit=hhmm(limit)),
        route=dict(_public(m), duration_h=round(duration, 2), departure=hhmm(s.start_hour), arrival=hhmm(arrival),
                   daylight_limit=hhmm(limit), daylight_margin_h=round(limit - arrival, 2),
                   battery_start_kwh=s.battery_kwh, battery_end_kwh=round(battery_end, 2),
                   battery_end_pct=round(100 * battery_end / s.battery_capacity_kwh, 1),
                   science_stops=[dict(zip(("lon", "lat"), (round(x, 5) for x in P.rc_to_lonlat(pl.grid, *q["rc"]))),
                                       targets=q["targets"], dwell_min=round(DWELL_H * 60)) for q in route["pois"]],
                   charging_stop=charge, waypoints_lonlat=waypoints),
        classic_astar=_public(mc),
        comparison=comparison,
        why=_why(pl, route, classic_route, p, h0) + [
            dict(factor=k[:-10], km_gained=v) for k, v in comparison.items() if k.endswith("_km_gained") and v > 0],
        warnings=warnings, suggestions=suggestions,
    )
    return report, route, classic_route
