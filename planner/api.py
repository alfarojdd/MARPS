"""Endpoint del planificador para el backend FastAPI de MARPS.

Montaje en la app del backend:
    import sys; sys.path.insert(0, "planner")
    from api import router as planner_router
    app.include_router(planner_router)

Endpoints:
    POST /plan-route   {mission, system} → {report, geojson, ctx_px}
    GET  /places       lugares que entiende el planificador (nombres y alias)
    GET  /planner/health

El primer POST carga las capas y el mapa de sombras (~10 s; luego quedan en memoria y en caché de disco).
"""
import math
import threading
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import planner as P
import report as R

ScienceName = Literal["aqueous", "carbonates", "clays", "smectites", "kaolinite", "olivine", "pyroxene",
                      "delta", "crater_floor"]


class ScienceTarget(BaseModel):
    target: ScienceName
    priority: float = Field(1.0, ge=0.1, le=1.0)


class Mission(BaseModel):
    """Lo que extrae el LLM del texto del astronauta."""
    human: bool = True
    origin: str
    destination: str
    power: bool = False
    route_preference: Literal["shortest", "fastest"] | None = None
    safety: Literal["low", "normal", "high"] = "normal"
    science_targets: list[ScienceTarget] = []
    science_detour: Literal["low", "medium", "high"] = "medium"
    return_to_origin: bool = False


class SystemState(BaseModel):
    """Lo que sabe el vehículo, no el LLM."""
    start_hour: float = Field(9.0, ge=0, lt=24, description="Hora solar local (LTST) de salida")
    battery_kwh: float = Field(30.0, ge=0)
    battery_capacity_kwh: float = Field(40.0, gt=0)
    reserve_pct: float = Field(20.0, ge=0, le=100)


class PlanRequest(BaseModel):
    mission: Mission
    system: SystemState = SystemState()


router = APIRouter()
_LOCK = threading.Lock()
_PL = None
CTX_RES = 6.0  # el mapa base del frontend (mosaico CTX de 6 m) comparte esquina con la rejilla de 20 m


def planner():
    global _PL
    if _PL is None:
        _PL = P.Planner()
    return _PL


def _lonlat(pl, n):
    lon, lat = P.rc_to_lonlat(pl.grid, n // pl.W, n % pl.W)
    return [round(float(lon), 6), round(float(lat), 6)]


def _ctx_px(pl, n):
    """[col, fila] en píxeles del mosaico CTX de 6 m (Leaflet CRS.Simple: lat = -fila, lng = col)."""
    r, c = divmod(int(n), pl.W)
    return [round((c + 0.5) * P.RES / CTX_RES, 1), round((r + 0.5) * P.RES / CTX_RES, 1)]


def _point(lon, lat, **props):
    return dict(type="Feature", geometry=dict(type="Point", coordinates=[lon, lat]), properties=props)


def build_response(pl, req: PlanRequest):
    mission = req.mission.model_dump()
    report, route, classic = R.build_report(pl, mission, req.system.model_dump())
    feats, px = [], {}
    if route and route.get("ok"):
        for kind, r in (("route", route), ("classic_astar", classic)):
            if r and r.get("ok"):
                feats.append(dict(type="Feature", properties=dict(kind=kind),
                                  geometry=dict(type="LineString", coordinates=[_lonlat(pl, n) for n in r["path"]])))
                px[kind] = [_ctx_px(pl, n) for n in r["path"]]
        feats.append(_point(*_lonlat(pl, route["path"][0]), kind="origin", name=req.mission.origin))
        feats.append(_point(*_lonlat(pl, route["stops"][-1] if not req.mission.return_to_origin else route["stops"][-2]),
                            kind="destination", name=req.mission.destination))
        for i, s in enumerate(report["route"]["science_stops"]):
            feats.append(_point(s["lon"], s["lat"], kind="science_stop", order=i + 1, targets=s["targets"],
                                dwell_min=s["dwell_min"]))
        ch = report["route"].get("charging_stop")
        if ch:
            feats.append(_point(ch["lon"], ch["lat"], kind="charging_stop", charge_hours=ch["charge_hours"],
                                arrive=ch["arrive"]))
    return dict(report=report, geojson=dict(type="FeatureCollection", features=feats), ctx_px=px)


@router.post("/plan-route")
def plan_route(req: PlanRequest):
    with _LOCK:
        pl = planner()
        try:
            return build_response(pl, req)
        except ValueError as e:  # lugar desconocido o fuera del mapa: el backend puede pedir al LLM que corrija
            raise HTTPException(status_code=400, detail=str(e))


@router.get("/places")
def places():
    return dict(places={k: dict(lon=v[0], lat=v[1]) for k, v in P.PLACES.items()},
                aliases=P.ALIASES, coordinates="also accepted: 'lon,lat' or '18.44N, 77.45E'")


@router.get("/planner/health")
def health():
    pl = _PL
    return dict(loaded=pl is not None, shadows=None if pl is None else pl.sun is not None,
                shadows_error=None if pl is None else pl.sun_error)
