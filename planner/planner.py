"""Planificador de rutas consciente de la misión (spike de demostración).

Rejilla nativa de 20 m (la del DTM CTX), 16 vecinos, A* con coste por arista en "metros equivalentes":

    coste(u→v) = mult · [ w_dist·L + w_time·t·v0 + w_E·E/e_ref ] + L·Σ w_k·riesgo_k

- E: rodadura (más en arena y dunas) + subida + consumo fijo (soporte vital si hay tripulación) − solar.
- riesgo: rugosidad, suelo blando (inercia térmica), dunas (SIM 3464), (pendiente/máx)², (lateral/máx)²,
  dato desconocido y, con tripulación, exposición a radiación.
- mult: descuento científico (1 − 0,5·interés) sobre distancia, tiempo y energía (no sobre el riesgo);
  nunca baja de 0,5.
- restricciones duras (el JSON no las relaja): pendiente y lateral máximas, margen alrededor de celdas
  peligrosas y, con safety=high, celdas sin dato.
- heurística admisible y consistente: h = hflat·distancia + c_subida·max(h_meta − h_nodo, 0). Toda ruta
  tiene que recorrer al menos la distancia en línea recta y subir al menos el desnivel hasta la meta.

El mismo modelo físico (`edge_terms`) sirve para construir la rejilla y para evaluar cualquier ruta, así se
puede medir una ruta con los pesos de otra (de ahí sale el "por qué" del informe).
"""
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json
import math
import os

import numpy as np
from numba import njit
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
# Datos grandes fuera del repo: se apunta a ellos con JEZERO_DATA (si no, data/jezero del repo).
DATA = Path(os.environ["JEZERO_DATA"]).resolve() if os.environ.get("JEZERO_DATA") else ROOT / "data/jezero"
CACHE = DATA / "planner_cache_20m.npz"
R_MARS = 3396190.0
G_MARS = 3.71
RES = 20.0

# ---------------------------------------------------------------- parámetros de misión (los saca el LLM)

DETOUR = {"low": 0.2, "medium": 0.5, "high": 1.0}


@dataclass
class Params:
    human: bool = False
    safety: str = "normal"                 # low | normal | high
    power: bool = False
    route_preference: str | None = None    # shortest | fastest | None
    origin: str | None = None              # nombre de PLACES o "lon,lat"
    destination: str | None = None
    science_targets: list = field(default_factory=list)  # [{"target": "carbonates", "priority": 1.0}]
    science_detour: float | str = "medium"  # low | medium | high (o un número: +50 % = 0.5)
    return_to_origin: bool = False
    context_free: bool = False             # solo para el A* clásico de referencia: distancia pura

    @classmethod
    def from_dict(cls, d):
        p = cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
        if p.safety not in SAFETY:
            raise ValueError(f"safety desconocido: {p.safety}")
        if p.route_preference not in (None, "shortest", "fastest"):
            raise ValueError(f"route_preference desconocido: {p.route_preference}")
        for t in p.science_targets:
            if t.get("target") not in TARGETS and t.get("target") != "aqueous":
                raise ValueError(f"science_target desconocido: {t.get('target')}")
        if isinstance(p.science_detour, str) and p.science_detour not in DETOUR:
            raise ValueError(f"science_detour desconocido: {p.science_detour}")
        return p

    @property
    def detour(self):
        return DETOUR[self.science_detour] if isinstance(self.science_detour, str) else float(self.science_detour)


SAFETY = {
    "low":    dict(max_pitch=25, max_cross=15, margin=0,   rough=0.3, soft=0.3, dune=0.5, pitch=0.3, cross=0.3,
                   unknown=0.2, forbid_unknown=False),
    "normal": dict(max_pitch=20, max_cross=12, margin=40,  rough=1.0, soft=1.0, dune=2.0, pitch=1.0, cross=1.5,
                   unknown=0.5, forbid_unknown=False),
    "high":   dict(max_pitch=15, max_cross=8,  margin=100, rough=3.0, soft=3.0, dune=5.0, pitch=2.5, cross=4.0,
                   unknown=0.0, forbid_unknown=True),
}
RISK_TERMS = ["rough", "soft", "dune", "pitch", "cross", "unknown", "exposure"]

# Vehículo genérico presurizado (orden de magnitud, no un rover concreto).
VEHICLE = dict(mass=3000.0, v0=2.5, crr_firm=0.08, crr_sand_extra=0.12, eff=0.7,
               p_hotel=800.0, p_life_support=1500.0, p_solar=600.0)

PLACES = {
    "landing_site": (77.4508, 18.4447),       # Octavia E. Butler, aterrizaje de Perseverance
    "delta_carbonates": (77.3637, 18.5458),   # núcleo de carbonatos y esmectitas (CRISM)
    "north_carbonates": (77.3034, 18.6687),
    "delta_top": (77.3900, 18.6000),
    "crater_floor_south": (77.5000, 18.3000),
    "western_rim": (77.2200, 18.4000),
    "north_plains": (77.5500, 18.6600),
}

# science_targets: nombre → (fuente, valores). Lo fija el código, no el LLM.
TARGETS = {
    "carbonates": ("crism", [2, 6]),
    "clays": ("crism", [3, 4, 5, 9, 10]),
    "smectites": ("crism", [3, 4, 5, 10]),
    "kaolinite": ("crism", [9]),
    "olivine": ("crism", [1, 4, 5]),
    "pyroxene": ("crism", [7, 8]),
    "delta": ("geo", [2, 3]),          # Jezero fan 1 y 2 (SIM 3464)
    "crater_floor": ("geo", [4]),
}
AQUEOUS = ["carbonates", "clays", "delta"]
DUNE_UNIT = 1  # "Eolian bedform unit" en SIM 3464

MOVES = np.array([(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1),
                  (1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)], np.int64)
MOVES_NB = MOVES  # Numba la congela como constante al compilar


# ---------------------------------------------------------------- datos

def load_grid():
    """Capas en la rejilla común de 20 m. Se cachea en data/jezero/planner_cache_20m.npz."""
    if CACHE.exists():
        z = np.load(CACHE)
        return {k: z[k] for k in z.files}
    import rasterio
    out = {}
    for n in ["elev_ctx", "tri_ctx", "thermal_inertia", "insolation_rel", "atm_column_pct", "hillshade_ctx"]:
        with rasterio.open(DATA / f"layers20m/{n}.tif") as s:
            left, top = s.transform.c, s.transform.f
            a = s.read(1).astype(np.float32)
            if s.nodata is not None and not np.isnan(s.nodata):
                a[a == s.nodata] = np.nan
            out[n] = a
    for n in ["crism_class", "crism_conf", "geo_unit"]:
        with rasterio.open(DATA / f"layers20m/{n}.tif") as s:
            out[n] = s.read(1).astype(np.int16)
    out["origin_xy"] = np.array([left, top])
    np.savez_compressed(CACHE, **out)
    return out


def lonlat_to_rc(grid, lon, lat):
    k = math.pi * R_MARS / 180
    left, top = grid["origin_xy"]
    return int((top - lat * k) // RES), int((lon * k - left) // RES)


def rc_to_lonlat(grid, r, c):
    k = math.pi * R_MARS / 180
    left, top = grid["origin_xy"]
    return (left + (c + 0.5) * RES) / k, (top - (r + 0.5) * RES) / k


def resolve_place(grid, s):
    if s in PLACES:
        return lonlat_to_rc(grid, *PLACES[s])
    lon, lat = (float(v) for v in s.split(","))
    return lonlat_to_rc(grid, lon, lat)


def cell_fields(grid):
    """Campos físicos por celda (float32), independientes de los parámetros."""
    f32 = lambda a: a.astype(np.float32)
    h = grid["elev_ctx"].astype(np.float64)
    h = np.where(np.isfinite(h), h, np.nanmean(h))
    dr, dc = np.gradient(h, RES)
    ti = grid["thermal_inertia"]
    return dict(
        h=f32(h), dr=f32(dr), dc=f32(dc),
        slope=f32(np.degrees(np.arctan(np.hypot(dr, dc)))),
        rough=f32(np.clip(np.nan_to_num(grid["tri_ctx"], nan=0) / 3.0, 0, 1)),   # TRI 3 m ≈ muy rugoso
        soft=f32(np.clip((260 - np.nan_to_num(ti, nan=260)) / 120, 0, 1)),       # TI < 140 = arena suelta
        dune=f32(grid["geo_unit"] == DUNE_UNIT),
        unknown=f32(~np.isfinite(ti)),
        exposure=f32(1 - np.clip(np.nan_to_num(grid["atm_column_pct"], nan=0) / 11, 0, 1)),
        insol=f32(np.nan_to_num(grid["insolation_rel"], nan=1.0)),
    )


def interest_map(grid, targets):
    """Mapa de interés 0-1 y máscara por objetivo. Fuera de la huella CRISM vale 0."""
    total = np.zeros(grid["crism_class"].shape, np.float32)
    per_target, expanded = {}, []
    for t in targets:
        names = AQUEOUS if t["target"] == "aqueous" else [t["target"]]
        expanded += [(n, float(t.get("priority", 1.0))) for n in names]
    for name, prio in expanded:
        src, vals = TARGETS[name]
        if src == "crism":
            conf = np.where(grid["crism_conf"] == 2, 1.0, np.where(grid["crism_conf"] == 1, 0.6, 0.0))
            m = np.isin(grid["crism_class"], vals) * conf
        else:
            m = np.isin(grid["geo_unit"], vals) * 0.5  # la geología es menos específica que CRISM
        per_target[name] = m > 0
        total += prio * m.astype(np.float32)
    if not expanded:
        return None, {}
    total = ndimage.uniform_filter(total, int(120 / RES))  # premia manchas de ~120 m, no píxeles sueltos
    return np.clip(total / max(total.max(), 1e-9), 0, 1).astype(np.float32), per_target


# ---------------------------------------------------------------- modelo de coste

def profile(p: Params):
    """Pesos efectivos de una petición."""
    S = dict(SAFETY["normal" if (p.human and p.safety == "low") else p.safety])  # con tripulación, mínimo normal
    V = VEHICLE
    p_hotel = V["p_hotel"] + (V["p_life_support"] if p.human else 0)
    w = dict(zip(("dist", "time"), {"shortest": (1.0, 0.0), "fastest": (0.0, 1.0), None: (0.5, 0.5)}[p.route_preference]))
    w["energy"] = 1.5 if p.power else 0.15
    w.update({k: S[k] for k in RISK_TERMS if k in S})
    w["exposure"] = 1.0 if p.human else 0.0
    if p.context_free:
        w = {k: 0.0 for k in w} | {"dist": 1.0}
    e_ref = V["mass"] * G_MARS * V["crr_firm"] / V["eff"] / 3600 + p_hotel / V["v0"] / 3600  # Wh/m en llano firme
    return S, w, p_hotel, e_ref


def edge_terms(at_u, at_v, mr, mc, p: Params, p_hotel):
    """Física de la arista u→v. at_u/at_v(nombre) devuelven el campo en el origen/destino (slices o índices)."""
    V = VEHICLE
    n = np.hypot(mr, mc)
    L = RES * n
    avg = lambda k: 0.5 * (at_u(k) + at_v(k))
    dh = at_v("h") - at_u("h")
    pitch = np.degrees(np.arctan(dh / L))
    cross = np.degrees(np.arctan(np.abs(avg("dr") * (-mc / n) + avg("dc") * (mr / n))))
    rough, soft, dune = avg("rough"), avg("soft"), avg("dune")
    sand = np.maximum(soft, dune)
    t = L / (V["v0"] / (1 + 0.08 * np.abs(pitch) + 0.06 * cross + 1.5 * rough + 1.0 * sand))
    k = V["mass"] * G_MARS / V["eff"] / 3600  # Wh por metro·(adimensional)
    p_net = np.maximum(p_hotel - V["p_solar"] * (avg("insol") if p.power else 1.0), 0)
    return dict(L=L, dh=dh, pitch=pitch, cross=cross, t=t, rough=rough, soft=soft, dune=dune,
                unknown=np.maximum(at_u("unknown"), at_v("unknown")), exposure=avg("exposure"),
                e_roll=k * (V["crr_firm"] + V["crr_sand_extra"] * sand) * L, e_climb=k * np.maximum(dh, 0),
                e_hotel=p_net * t / 3600)


def components(T, p: Params, S, w, e_ref):
    """Coste de cada término en metros equivalentes (antes del descuento científico)."""
    L = T["L"]
    return dict(
        distance=w["dist"] * L, time=w["time"] * T["t"] * VEHICLE["v0"],
        energy=w["energy"] * (T["e_roll"] + T["e_climb"] + T["e_hotel"]) / e_ref,
        rough=L * w["rough"] * T["rough"], soft=L * w["soft"] * T["soft"], dune=L * w["dune"] * T["dune"],
        pitch=L * w["pitch"] * (T["pitch"] / S["max_pitch"]) ** 2,
        cross=L * w["cross"] * (T["cross"] / S["max_cross"]) ** 2,
        unknown=L * w["unknown"] * T["unknown"], exposure=L * w["exposure"] * T["exposure"])


def build_costs(F, p: Params, interest=None):
    """Coste (16, H·W) float32 + constantes de la heurística (hflat, c_climb)."""
    S, w, p_hotel, e_ref = profile(p)
    H, W = F["h"].shape
    hazard = F["slope"] > S["max_pitch"]
    if S["margin"]:
        hazard = ndimage.binary_dilation(hazard, ndimage.generate_binary_structure(2, 1),
                                         iterations=int(round(S["margin"] / RES)))
    if S["forbid_unknown"]:
        hazard |= F["unknown"] > 0
    Fx = dict(F, interest=interest) if interest is not None else F
    cost = np.full((16, H, W), np.inf, np.float32)
    k_climb = VEHICLE["mass"] * G_MARS / VEHICLE["eff"] / 3600
    mult_min = 0.5 if interest is not None else 1.0
    hflat = np.inf
    for d, (mr, mc) in enumerate(MOVES):
        r0, r1, c0, c1 = max(0, -mr), H - max(0, mr), max(0, -mc), W - max(0, mc)
        U = (slice(r0, r1), slice(c0, c1))
        Vv = (slice(r0 + mr, r1 + mr), slice(c0 + mc, c1 + mc))
        T = edge_terms(lambda k: Fx[k][U], lambda k: Fx[k][Vv], mr, mc, p, p_hotel)
        comp = components(T, p, S, w, e_ref)
        mult = 1 - 0.5 * 0.5 * (Fx["interest"][U] + Fx["interest"][Vv]) if interest is not None else 1.0
        # la ciencia abarata recorrer (distancia, tiempo, energía), nunca el riesgo
        o = mult * (comp["distance"] + comp["time"] + comp["energy"]) + sum(comp[k] for k in RISK_TERMS)
        bad = hazard[U] | hazard[Vv] | (np.abs(T["pitch"]) > S["max_pitch"]) | (T["cross"] > S["max_cross"])
        if abs(mr) + abs(mc) == 3:  # salto de caballo: también las dos celdas que roza
            touched = ((0, mc // 2), (mr, mc // 2)) if abs(mc) == 2 else ((mr // 2, 0), (mr // 2, mc))
            for ar, ac in touched:
                bad |= hazard[r0 + ar: r1 + ar, c0 + ac: c1 + ac]
        o = np.where(bad, np.inf, o)
        flat = (o - mult_min * w["energy"] * k_climb * np.maximum(T["dh"], 0) / e_ref) / T["L"]
        hflat = min(hflat, float(np.min(flat[np.isfinite(flat)], initial=np.inf)))
        cost[d][U] = o
    c_climb = mult_min * w["energy"] * k_climb / e_ref  # metros equivalentes por metro de subida
    return cost.reshape(16, -1), max(hflat, 0.0), c_climb


# ---------------------------------------------------------------- búsqueda (Numba)

@njit(cache=True)
def _search(cost, H, W, start, goal, hflat, c_climb, elev, res, stop_nodes):
    """A* (goal >= 0) o Dijkstra (goal < 0; para cuando ha cerrado todos los stop_nodes, si se dan)."""
    N = H * W
    g = np.full(N, np.inf)
    parent = np.full(N, -1, np.int64)
    closed = np.zeros(N, np.bool_)
    want = np.zeros(N, np.bool_)
    remaining = 0
    for s in stop_nodes:
        if not want[s]:
            want[s] = True
            remaining += 1
    cap = 1 << 16
    hk = np.empty(cap)
    hn = np.empty(cap, np.int64)
    gr, gc, ge = 0, 0, 0.0
    if goal >= 0:
        gr, gc, ge = goal // W, goal % W, elev[goal]
    g[start] = 0.0
    hk[0], hn[0] = 0.0, start
    size, expanded = 1, 0
    while size > 0:
        node = hn[0]
        size -= 1
        if size > 0:
            k, n = hk[size], hn[size]
            i = 0
            while True:
                l = 2 * i + 1
                if l >= size:
                    break
                if l + 1 < size and hk[l + 1] < hk[l]:
                    l += 1
                if hk[l] >= k:
                    break
                hk[i], hn[i] = hk[l], hn[l]
                i = l
            hk[i], hn[i] = k, n
        if closed[node]:
            continue
        closed[node] = True
        expanded += 1
        if node == goal:
            break
        if want[node]:
            remaining -= 1
            if remaining == 0:
                break
        r, c = node // W, node % W
        for d in range(16):
            w = cost[d, node]
            if not np.isfinite(w):
                continue
            nr, nc = r + MOVES_NB[d, 0], c + MOVES_NB[d, 1]
            nb = nr * W + nc
            ng = g[node] + w
            if ng < g[nb]:
                g[nb] = ng
                parent[nb] = node
                f = ng
                if goal >= 0:
                    f += hflat * res * math.hypot(nr - gr, nc - gc) + c_climb * max(ge - elev[nb], 0.0)
                if size == cap:
                    cap *= 2
                    hk2, hn2 = np.empty(cap), np.empty(cap, np.int64)
                    hk2[:size], hn2[:size] = hk[:size], hn[:size]
                    hk, hn = hk2, hn2
                i = size
                size += 1
                while i > 0:
                    pa = (i - 1) // 2
                    if hk[pa] <= f:
                        break
                    hk[i], hn[i] = hk[pa], hn[pa]
                    i = pa
                hk[i], hn[i] = f, nb
    return g, parent, expanded


NO_STOPS = np.zeros(0, np.int64)


def _path(parent, start, goal):
    out = [goal]
    while out[-1] != start:
        nxt = parent[out[-1]]
        if nxt < 0:
            return None
        out.append(nxt)
    return out[::-1]


def _nearest_free(cost, H, W, rc):
    free = np.isfinite(cost).any(0).reshape(H, W)
    rc = (min(max(rc[0], 0), H - 1), min(max(rc[1], 0), W - 1))
    if free[rc]:
        return rc
    _, (ir, ic) = ndimage.distance_transform_edt(~free, return_indices=True)
    return int(ir[rc]), int(ic[rc])


# ---------------------------------------------------------------- planificación

class Planner:
    def __init__(self):
        self.grid = load_grid()
        self.F = cell_fields(self.grid)
        self.H, self.W = self.F["h"].shape
        self.elev = self.F["h"].astype(np.float64).ravel()
        self._cache = {}  # rejillas de coste por perfil de pesos (cada una ~150 MB)

    def costs(self, p: Params, interest):
        key = (p.human, p.safety, p.power, p.route_preference, p.context_free,
               json.dumps(p.science_targets, sort_keys=True))
        if key not in self._cache:
            if len(self._cache) >= 4:
                self._cache.pop(next(iter(self._cache)))
            self._cache[key] = build_costs(self.F, p, interest)
        return self._cache[key]

    def astar(self, cost, a, b, hflat, c_climb):
        return _search(cost, self.H, self.W, a, b, hflat, c_climb, self.elev, RES, NO_STOPS)

    def plan(self, p: Params, via=(), stops=None, pois=None):
        """Ruta A→(paradas científicas)→B[→A].

        via: celdas (fila, col) obligatorias (p. ej. una parada de carga); se insertan donde menos alargan.
        stops/pois: reutilizar las paradas de una planificación anterior (evita repetir la selección científica).
        """
        H, W = self.H, self.W
        interest, per_target = interest_map(self.grid, p.science_targets) if p.science_targets else (None, {})
        cost, hflat, c_climb = self.costs(p, interest)
        o = _nearest_free(cost, H, W, resolve_place(self.grid, p.origin))
        dst = _nearest_free(cost, H, W, resolve_place(self.grid, p.destination))
        start, goal = o[0] * W + o[1], dst[0] * W + dst[1]
        expanded = 0
        if stops is None:
            stops, pois = [start, goal], []
            if interest is not None:
                stops, pois, expanded = self._science_stops(cost, interest, per_target, start, goal, p.detour)
            if p.return_to_origin:
                stops.append(start)
        stops = list(stops)
        for rc in via:
            v = _nearest_free(cost, H, W, rc)
            v = v[0] * W + v[1]
            d = lambda a, b: math.hypot(a // W - b // W, a % W - b % W)
            k = min(range(len(stops) - 1), key=lambda i: d(stops[i], v) + d(v, stops[i + 1]) - d(stops[i], stops[i + 1]))
            stops.insert(k + 1, v)
        path = []
        for a, b in zip(stops[:-1], stops[1:]):
            _, parent, ex = self.astar(cost, a, b, hflat, c_climb)
            expanded += ex
            seg = _path(parent, a, b)
            if seg is None:
                return dict(ok=False, reason="no traversable route under these constraints", params=asdict(p))
            path += seg if not path else seg[1:]
        path = np.array(path)
        return dict(ok=True, params=asdict(p), path=path, stops=stops, pois=pois or [], expanded=expanded,
                    via=[tuple(v) for v in via], metrics=self.evaluate(path, p, per_target))

    def _science_stops(self, cost, interest, per_target, start, goal, detour, max_pois=10):
        """Orienteering voraz sobre una matriz de costes exacta (Dijkstra que para al cerrar todos los candidatos)."""
        H, W = self.H, self.W
        free = np.isfinite(cost).any(0).reshape(H, W)
        lab, n = ndimage.label(interest > 0.15)
        areas = ndimage.sum_labels(np.ones_like(lab), lab, index=np.arange(1, n + 1))
        sums = ndimage.sum_labels(interest, lab, index=np.arange(1, n + 1))
        cands = []
        sr, sc = divmod(start, W)
        gr, gc = divmod(goal, W)
        for i in np.argsort(-sums):
            if areas[i] * RES * RES < 24000 or len(cands) >= max_pois:  # < 2,4 ha: ruido
                continue
            vals = np.where((lab == i + 1) & free, interest, -1)
            cell = int(np.argmax(vals))
            r, c = divmod(cell, W)
            if vals.flat[cell] <= 0 or min(math.hypot(r - sr, c - sc), math.hypot(r - gr, c - gc)) * RES < 500:
                continue  # sin celda transitable, o pegado a A o B (no aporta parada)
            kinds = [k for k, m in per_target.items() if m[r, c]]
            cands.append((float(sums[i]), cell, kinds))
        if not cands:
            return [start, goal], [], 0
        nodes = [start, goal] + [c for _, c, _ in cands]
        value = [0.0, 0.0] + [v for v, _, _ in cands]
        C = np.full((len(nodes), len(nodes)), np.inf)
        expanded = 0
        stop_nodes = np.array(nodes, np.int64)
        for i, a in enumerate(nodes):
            if i == 1:
                continue
            g, _, ex = _search(cost, H, W, a, -1, 0.0, 0.0, self.elev, RES, stop_nodes)
            expanded += ex
            C[i] = g[nodes]
        route, total = [0, 1], C[0, 1]
        budget = (1 + detour) * total
        left = set(range(2, len(nodes)))
        while left:
            best = None
            for j in left:
                for k in range(len(route) - 1):
                    a, b = route[k], route[k + 1]
                    extra = C[a, j] + C[j, b] - C[a, b]
                    if total + extra <= budget:
                        score = value[j] / max(extra, 1.0)
                        if best is None or score > best[0]:
                            best = (score, j, k + 1, extra)
            if best is None:
                break
            _, j, pos, extra = best
            route.insert(pos, j)
            total += extra
            left.discard(j)
        pois = [dict(rc=divmod(nodes[j], W), value=value[j], targets=cands[j - 2][2]) for j in route[1:-1]]
        return [nodes[j] for j in route], pois, expanded

    def evaluate(self, path, p: Params, per_target=None):
        """Métricas físicas y desglose de coste de cualquier ruta, medidas con los pesos de `p`."""
        F, W = self.F, self.W
        path = np.asarray(path)
        r, c = path // W, path % W
        u, v = (r[:-1], c[:-1]), (r[1:], c[1:])
        S, w, p_hotel, e_ref = profile(p)
        T = edge_terms(lambda k: F[k][u], lambda k: F[k][v], np.diff(r), np.diff(c), p, p_hotel)
        comp = {k: float(x.sum()) for k, x in components(T, p, S, w, e_ref).items()}
        L = T["L"]
        e = T["e_roll"] + T["e_climb"] + T["e_hotel"]
        m = dict(
            distance_km=float(L.sum() / 1000), time_h=float(T["t"].sum() / 3600),
            energy_kwh=float(e.sum() / 1000), drive_kwh=float((T["e_roll"] + T["e_climb"]).sum() / 1000),
            ascent_m=float(T["dh"][T["dh"] > 0].sum()), descent_m=float(-T["dh"][T["dh"] < 0].sum()),
            max_pitch_deg=float(np.abs(T["pitch"]).max()), max_cross_deg=float(T["cross"].max()),
            rough_km=float(L[T["rough"] > 0.5].sum() / 1000), soft_km=float(L[T["soft"] > 0.5].sum() / 1000),
            dunes_km=float(L[T["dune"] > 0].sum() / 1000), unknown_km=float(L[T["unknown"] > 0].sum() / 1000),
            mean_exposure=float((T["exposure"] * L).sum() / L.sum()),
            cost_breakdown=comp,
        )
        for name, mask in (per_target or {}).items():
            m[f"on_{name}_km"] = float(L[mask[u] | mask[v]].sum() / 1000)
        m["cum_energy_kwh"] = np.concatenate([[0.0], np.cumsum(e) / 1000])  # para la batería (no va al JSON)
        m["cum_time_h"] = np.concatenate([[0.0], np.cumsum(T["t"]) / 3600])
        return m


def classic(p: Params) -> Params:
    """A* clásico de referencia: distancia pura con los límites físicos mínimos, sin contexto de misión."""
    return Params(origin=p.origin, destination=p.destination, route_preference="shortest", safety="low",
                  return_to_origin=p.return_to_origin, context_free=True)


if __name__ == "__main__":
    import sys
    pl = Planner()
    r = pl.plan(Params.from_dict(json.loads(sys.argv[1])))
    m = {k: v for k, v in r.get("metrics", {}).items() if not k.startswith("cum_")}
    print(json.dumps(m or r, indent=1, default=float))
