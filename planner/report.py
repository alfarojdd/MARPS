"""Informe de trayecto para el resumen del LLM del casco.

Entrada: parámetros de misión (los saca el LLM) + estado del sistema (lo sabe el vehículo: hora, batería).
Salida: un JSON con la ruta, la comparación frente al A* clásico, el "por qué" y avisos de luz y batería.
Si la batería no alcanza, propone la ruta de ahorro y, si hace falta, una parada de carga solar en la zona
más soleada cercana a la ruta (y replanifica pasando por ella).
"""
from dataclasses import dataclass, asdict

import numpy as np
from scipy import ndimage

import planner as P

SUNRISE, SUNSET, DAYLIGHT_MARGIN_H = 6.0, 18.0, 0.5   # LTST; sin estacionalidad (pendiente: mapa de sombras)
DWELL_H = 1 / 3                                       # tiempo por parada científica
P_PARKED = 150.0                                      # W con el vehículo parado (sin contar soporte vital)
P_SOLAR_PARKED = 3000.0                               # W pico con el panel desplegado al cargar
CHARGE_SEARCH_M = 1000                                # buscar sitio de carga a menos de 1 km de la ruta


@dataclass
class SystemState:
    start_hour: float = 9.0              # hora solar local de salida (reloj del sistema)
    battery_kwh: float = 30.0            # carga actual
    battery_capacity_kwh: float = 40.0
    reserve_pct: float = 20.0            # margen mínimo a la llegada

    @classmethod
    def from_dict(cls, d):
        return cls(**{k: v for k, v in (d or {}).items() if k in cls.__dataclass_fields__})


def sun_factor(h):
    """Fracción de la potencia solar pico según la hora (sin sombras ni estación)."""
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


def _charge_hours(deficit_kwh, start_h, insol, p):
    """Horas de carga parada para recuperar deficit_kwh empezando a start_h. None si no da tiempo con luz."""
    p_parked = P_PARKED + (P.VEHICLE["p_life_support"] if p.human else 0)
    got, h, dt = 0.0, start_h, 0.05
    while got < deficit_kwh:
        if h > SUNSET - DAYLIGHT_MARGIN_H:
            return None
        got += (P_SOLAR_PARKED * insol * float(sun_factor(h)) - p_parked) * dt / 1000
        h += dt
    return h - start_h


def _charge_spot(pl, path, cum_e, battery_kwh):
    """Celda soleada, llana y firme cerca de la ruta, alcanzable con la batería actual."""
    F, W = pl.F, pl.W
    r, c = path // W, path % W
    reach = cum_e <= battery_kwh * 0.9
    if not reach.any():
        return None
    near = np.zeros(F["h"].shape, bool)
    near[r[reach], c[reach]] = True
    near = ndimage.binary_dilation(near, iterations=int(CHARGE_SEARCH_M / P.RES))
    ok = near & (F["slope"] < 5) & (F["dune"] == 0) & (F["unknown"] == 0)
    if not ok.any():
        return None
    score = np.where(ok, F["insol"], -1)
    cell = np.unravel_index(int(np.argmax(score)), score.shape)
    # índice de la ruta más cercano (para estimar a qué hora se llega)
    i = int(np.argmin(np.where(reach, (r - cell[0]) ** 2 + (c - cell[1]) ** 2, np.iinfo(np.int64).max)))
    return dict(rc=(int(cell[0]), int(cell[1])), insol=float(F["insol"][cell]), path_index=i)


def _why(pl, route, classic_route, p):
    """Qué términos de coste evita la ruta frente al A* clásico, medidos con los pesos de esta misión."""
    ours = pl.evaluate(route["path"], p)["cost_breakdown"]
    theirs = pl.evaluate(classic_route["path"], p)["cost_breakdown"]
    diff = {k: theirs[k] - ours[k] for k in ours}
    gain = sum(v for v in diff.values() if v > 0)
    items = sorted(((k, v) for k, v in diff.items() if v > 0), key=lambda kv: -kv[1])
    return [dict(factor=k, share_pct=round(100 * v / gain, 1)) for k, v in items[:4]] if gain > 0 else []


def build_report(pl, mission: dict, system: dict, classic_route=None):
    p = P.Params.from_dict(mission)
    s = SystemState.from_dict(system)
    route = pl.plan(p)
    if not route["ok"]:
        return dict(feasible=False, warnings=[dict(code="NO_ROUTE", severity="critical", message=route["reason"])],
                    mission=asdict(p), system=asdict(s)), route, None
    classic_route = classic_route or pl.plan(P.classic(p))
    warnings, suggestions = [], []
    n_stops = len(route["pois"])
    duration, energy = _timeline(route["metrics"], n_stops, s, p)
    limit = SUNSET - DAYLIGHT_MARGIN_H
    reserve = s.battery_capacity_kwh * s.reserve_pct / 100

    if not SUNRISE <= s.start_hour < limit:
        warnings.append(dict(code="NO_DAYLIGHT_AT_DEPARTURE", severity="critical",
                             message=f"Departure at {hhmm(s.start_hour)} is outside the daylight window "
                                     f"({hhmm(SUNRISE)}-{hhmm(limit)})."))

    charge = None
    if s.battery_kwh - energy < reserve:
        alt = None
        if not p.power:  # ¿basta con la ruta de ahorro?
            alt_p = P.Params.from_dict({**asdict(p), "power": True})
            alt_r = pl.plan(alt_p)
            if alt_r["ok"]:
                _, alt_e = _timeline(alt_r["metrics"], len(alt_r["pois"]), s, p)
                alt = dict(energy_kwh=round(alt_e, 2), battery_end_kwh=round(s.battery_kwh - alt_e, 2),
                           fits_reserve=bool(s.battery_kwh - alt_e >= reserve))
                suggestions.append(dict(code="SWITCH_TO_POWER_SAVING", **alt))
        if alt is None or not alt["fits_reserve"]:
            spot = _charge_spot(pl, route["path"], route["metrics"]["cum_energy_kwh"], s.battery_kwh)
            if spot is None:
                warnings.append(dict(code="BATTERY_INSUFFICIENT", severity="critical",
                                     message="Battery cannot complete the route and no reachable sunny "
                                             "charging spot was found near it."))
            else:
                rerouted = pl.plan(p, via=[spot["rc"]], stops=route["stops"], pois=route["pois"])
                if rerouted["ok"]:  # pasar por la zona soleada y recalcular con la ruta nueva
                    route = rerouted
                    duration, energy = _timeline(route["metrics"], len(route["pois"]), s, p)
                W = pl.W
                i = int(np.argmin((route["path"] // W - spot["rc"][0]) ** 2 + (route["path"] % W - spot["rc"][1]) ** 2))
                arrive_h = float(s.start_hour + route["metrics"]["cum_time_h"][i])
                reach_kwh = float(route["metrics"]["cum_energy_kwh"][i])
                deficit = energy + reserve - s.battery_kwh
                hours = _charge_hours(deficit, arrive_h, spot["insol"], p)
                lon, lat = P.rc_to_lonlat(pl.grid, *spot["rc"])
                charge = dict(lon=round(float(lon), 5), lat=round(float(lat), 5), rc=spot["rc"], arrive=hhmm(arrive_h),
                              battery_on_arrival_kwh=round(float(s.battery_kwh - reach_kwh), 2),
                              energy_needed_kwh=round(float(deficit), 2),
                              charge_hours=None if hours is None else round(float(hours), 2))
                if reach_kwh > s.battery_kwh:
                    warnings.append(dict(code="BATTERY_INSUFFICIENT", severity="critical",
                                         message="Battery runs out before reaching the nearest sunny charging spot."))
                elif hours is None:
                    warnings.append(dict(code="CHARGING_DOES_NOT_FIT_DAYLIGHT", severity="critical",
                                         message=f"Needs {deficit:.1f} kWh of solar charge but daylight ends "
                                                 f"before it can be collected."))
                else:
                    duration += hours
                    energy -= deficit  # lo recargado
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
    arrival = s.start_hour + duration
    if arrival > limit:
        warnings.append(dict(code="ARRIVAL_AFTER_DAYLIGHT", severity="critical" if p.human else "warning",
                             message=f"Estimated arrival {hhmm(arrival)} is after the daylight limit "
                                     f"{hhmm(limit)} ({arrival - limit:.1f} h late)."))

    m = route["metrics"]
    per_target = P.interest_map(pl.grid, p.science_targets)[1] if p.science_targets else {}
    mc = pl.evaluate(classic_route["path"], p, per_target)  # mismo vehículo y tripulación; solo cambia el recorrido
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
    for k in (k for k in m if k.startswith("on_")):
        comparison[f"{k[:-3]}_km_gained"] = round(m[k] - mc.get(k, 0.0), 2)
    W = pl.W
    step = max(1, len(route["path"]) // 60)
    waypoints = [[round(v, 5) for v in P.rc_to_lonlat(pl.grid, n // W, n % W)] for n in route["path"][::step]]
    report = dict(
        feasible=not any(w["severity"] == "critical" for w in warnings),
        mission={k: v for k, v in asdict(p).items() if k != "context_free"}, system=asdict(s),
        route=dict(_public(m), duration_h=round(duration, 2), departure=hhmm(s.start_hour), arrival=hhmm(arrival),
                   daylight_limit=hhmm(limit), daylight_margin_h=round(limit - arrival, 2),
                   battery_start_kwh=s.battery_kwh, battery_end_kwh=round(battery_end, 2),
                   battery_end_pct=round(100 * battery_end / s.battery_capacity_kwh, 1),
                   science_stops=[dict(zip(("lon", "lat"), (round(x, 5) for x in P.rc_to_lonlat(pl.grid, *q["rc"]))),
                                       targets=q["targets"], dwell_min=round(DWELL_H * 60)) for q in route["pois"]],
                   charging_stop=charge, waypoints_lonlat=waypoints),
        classic_astar=_public(mc),
        comparison=comparison,
        why=_why(pl, route, classic_route, p) + [
            dict(factor=k[:-10], km_gained=v) for k, v in comparison.items() if k.endswith("_km_gained") and v > 0],
        warnings=warnings, suggestions=suggestions,
    )
    return report, route, classic_route
