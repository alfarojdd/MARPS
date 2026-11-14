"""Mission-aware route planner.

Native 20 m grid (the CTX DTM grid), 16-neighbour connectivity, A* with per-edge cost in "equivalent metres":

    cost(u→v) = mult · [ w_dist·L + w_time·t·v0 + w_E·E/e_ref ] + L·Σ w_k·risk_k

- E: rolling (higher on sand and dunes) + climbing + fixed load (life support if crewed) − solar.
- risk: roughness, soft ground (thermal inertia), dunes (SIM 3464), (slope/max)², (cross-slope/max)²,
  unknown data and, if crewed, radiation exposure.
- mult: science discount (1 − 0.5·interest) on distance, time and energy (not on risk);
  never below 0.5.
- hard constraints (the JSON cannot relax them): max slope and cross-slope, buffer around hazardous
  cells and, with safety=high, no-data cells.
- admissible and consistent heuristic: h = hflat·distance + c_climb·max(h_goal − h_node, 0). Every route
  must cover at least the straight-line distance and climb at least the height difference to the goal.

The same physical model (`edge_terms`) builds the grid and evaluates any route, so a route can be
measured with another route's weights (this is where the report's "why" comes from).
"""
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json
import math

import numpy as np
from numba import njit
from scipy import ndimage

import os

HERE = Path(__file__).resolve().parent


def _find_data():
    """data/jezero from the MARPS repo (planner/../data/jezero) or from a sibling checkout layout (tools/planner/../../data/jezero)."""
    cands = [os.environ.get("JEZERO_DATA"), HERE.parent / "data/jezero", HERE.parents[1] / "data/jezero"]
    for c in cands:
        if c and ((Path(c) / "stack").exists() or (Path(c) / "layers20m").exists()):
            return Path(c).resolve()
    raise FileNotFoundError("data/jezero not found (stack/ or layers20m/). Set JEZERO_DATA.")


DATA = _find_data()
CACHE = DATA / "planner_cache_20m.npz"
R_MARS = 3396190.0
G_MARS = 3.71
RES = 20.0

# ---------------------------------------------------------------- mission parameters (produced by the SLM)

DETOUR = {"low": 0.2, "medium": 0.5, "high": 1.0}


@dataclass
class Params:
    human: bool = False
    safety: str = "normal"                 # low | normal | high
    power: bool = False
    route_preference: str | None = None    # shortest | fastest | None
    origin: str | None = None              # name from PLACES or "lon,lat"
    destination: str | None = None
    science_targets: list = field(default_factory=list)  # [{"target": "carbonates", "priority": 1.0}]
    science_detour: float | str = "medium"  # low | medium | high (or a number: +50 % = 0.5)
    return_to_origin: bool = False
    context_free: bool = False             # only for the classic reference A*: pure distance

    @classmethod
    def from_dict(cls, d):
        p = cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
        if p.safety not in SAFETY:
            raise ValueError(f"unknown safety: {p.safety}")
        if p.route_preference not in (None, "shortest", "fastest"):
            raise ValueError(f"unknown route_preference: {p.route_preference}")
        for t in p.science_targets:
            if t.get("target") not in TARGETS and t.get("target") != "aqueous":
                raise ValueError(f"unknown science_target: {t.get('target')}")
        if isinstance(p.science_detour, str) and p.science_detour not in DETOUR:
            raise ValueError(f"unknown science_detour: {p.science_detour}")
        return p

    @property
    def detour(self):
        return DETOUR[self.science_detour] if isinstance(self.science_detour, str) else float(self.science_detour)


SAFETY = {
    "low":    dict(max_pitch=25, max_cross=15, margin=0,   rough=0.3, soft=0.3, dune=0.5, pitch=0.3, cross=0.3,
                   unknown=0.2, shadow=0.0, forbid_unknown=False),
    "normal": dict(max_pitch=20, max_cross=12, margin=40,  rough=1.0, soft=1.0, dune=2.0, pitch=1.0, cross=1.5,
                   unknown=0.5, shadow=0.2, forbid_unknown=False),
    "high":   dict(max_pitch=15, max_cross=8,  margin=100, rough=3.0, soft=3.0, dune=5.0, pitch=2.5, cross=4.0,
                   unknown=0.0, shadow=0.5, forbid_unknown=True),
}
RISK_TERMS = ["rough", "soft", "dune", "pitch", "cross", "unknown", "exposure", "shadow"]

# Generic pressurised vehicle (order of magnitude, not a specific rover).
VEHICLE = dict(mass=3000.0, v0=2.5, crr_firm=0.08, crr_sand_extra=0.12, eff=0.7,
               p_hotel=800.0, p_life_support=1500.0, p_solar=600.0)

PLACES = {
    "landing_site": (77.4508, 18.4447),       # Octavia E. Butler, Perseverance landing site (ESA SPICE)
    "belva_crater": (77.38, 18.48),           # IAU Gazetteer 15872
    "neretva_vallis": (77.20, 18.55),         # IAU Gazetteer 15879 (feature centre)
    "jezero_centre": (77.69, 18.41),          # IAU Gazetteer 14300 (crater centre, east edge of the map)
    "delta_carbonates": (77.3637, 18.5458),   # carbonate and smectite core (CRISM)
    "north_carbonates": (77.3034, 18.6687),
    "delta_top": (77.3900, 18.6000),
    "crater_floor_south": (77.5000, 18.3000),
    "western_rim": (77.2200, 18.4000),
    "north_plains": (77.5500, 18.6600),
}

# science_targets: name → (source, values). Set by the code, not by the SLM.
TARGETS = {
    "carbonates": ("crism", [2, 6]),
    "clays": ("crism", [3, 4, 5, 9, 10]),
    "smectites": ("crism", [3, 4, 5, 10]),
    "kaolinite": ("crism", [9]),
    "olivine": ("crism", [1, 4, 5]),
    "pyroxene": ("crism", [7, 8]),
    "delta": ("geo", [2, 3]),          # Jezero fan 1 and 2 (SIM 3464)
    "crater_floor": ("geo", [4]),
}
AQUEOUS = ["carbonates", "clays", "delta"]
DUNE_UNIT = 1  # "Eolian bedform unit" in SIM 3464

MOVES = np.array([(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1),
                  (1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)], np.int64)
MOVES_NB = MOVES  # Numba freezes it as a constant at compile time


# ---------------------------------------------------------------- data

def _read_layer(name):
    """One layer on the common grid: layers20m/<name>.tif, stack band <name> or extra/<name>.tif."""
    import rasterio
    for f in (DATA / f"layers20m/{name}.tif", DATA / f"extra/{name}.tif"):
        if f.exists():
            with rasterio.open(f) as s:
                a = s.read(1).astype(np.float32)
                if s.nodata is not None and not np.isnan(s.nodata):
                    a[a == s.nodata] = np.nan
                return a, (s.transform.c, s.transform.f)
    stack = DATA / "stack/jezero_stack_20m.tif"
    if stack.exists():
        with rasterio.open(stack) as s:
            if name in s.descriptions:
                return s.read(s.descriptions.index(name) + 1).astype(np.float32), (s.transform.c, s.transform.f)
    return None, None


def load_grid():
    """Layers on the common 20 m grid. Cached in data/jezero/planner_cache_20m.npz."""
    if CACHE.exists():
        z = np.load(CACHE)
        return {k: z[k] for k in z.files}
    out = {}
    for n in ["elev_ctx", "tri_ctx", "thermal_inertia", "insolation_rel", "atm_column_pct", "hillshade_ctx",
              "crism_class", "crism_conf", "geo_unit"]:
        a, origin = _read_layer(n)
        if a is None:
            if n in ("crism_class", "crism_conf", "geo_unit"):
                continue  # optional: without them there is no science (or confidence) from that source
            raise FileNotFoundError(f"Missing layer {n} in {DATA}")
        out[n] = np.nan_to_num(a, nan=-1).astype(np.int16) if n in ("crism_class", "crism_conf", "geo_unit") else a
        out["origin_xy"] = np.array(origin)
    shape = out["elev_ctx"].shape
    out.setdefault("crism_class", np.full(shape, -1, np.int16))
    out.setdefault("geo_unit", np.zeros(shape, np.int16))
    if "crism_conf" not in out:  # the repo only publishes the class: medium confidence is assumed
        out["crism_conf"] = np.where(out["crism_class"] > 0, 1, 0).astype(np.int16)
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


# Names the SLM or the frontend may write (platform places.json) → PLACES key
ALIASES = {
    "octaviaebutlerlanding": "landing_site", "octaviaebutlerlandingperseverance": "landing_site",
    "octaviaebutler": "landing_site", "landing": "landing_site", "landingsite": "landing_site",
    "belva": "belva_crater", "belvacrater": "belva_crater", "belvacraterrim": "belva_crater",
    "neretva": "neretva_vallis", "jezero": "jezero_centre", "jezerocratercentre": "jezero_centre",
    "jezerocrater": "jezero_centre",
}


def _norm(s):
    return "".join(ch for ch in s.lower() if ch.isalnum())


def resolve_lonlat(s):
    """Place name or coordinates ("lon,lat", "18.44N, 77.45E"...) → (lon, lat). ValueError if not understood."""
    import re
    if s is None:
        raise ValueError("origin/destination is required")
    key = _norm(s)
    key = _norm(ALIASES.get(key, key))
    for k, ll in PLACES.items():
        if _norm(k) == key:
            return ll
    nums = re.findall(r"-?\d+(?:\.\d+)?\s*[NSEW]?", s.upper())
    if len(nums) == 2:
        vals = {}
        for n in nums:
            v, tag = float(re.match(r"-?\d+(?:\.\d+)?", n).group()), n.strip()[-1]
            vals.setdefault("lat" if tag in "NS" else "lon" if tag in "EW" else None, []).append(-v if tag in "SW" else v)
        if vals.get("lat") and vals.get("lon"):
            return vals["lon"][0], vals["lat"][0]
        a, b = (float(re.match(r"-?\d+(?:\.\d+)?", n).group()) for n in nums)
        return (a, b) if a > b else (b, a)  # at Jezero the longitude (~77) is larger than the latitude (~18)
    raise ValueError(f"unknown place '{s}'. Known: {sorted(PLACES)} or coordinates 'lon,lat'")


def resolve_place(grid, s):
    lon, lat = resolve_lonlat(s)
    r, c = lonlat_to_rc(grid, lon, lat)
    H, W = grid["elev_ctx"].shape
    if not (0 <= r < H and 0 <= c < W):
        raise ValueError(f"'{s}' ({lon:.4f}E, {lat:.4f}N) is outside the Jezero map")
    return r, c


def cell_fields(grid):
    """Per-cell physical fields (float32), independent of the parameters."""
    f32 = lambda a: a.astype(np.float32)
    h = grid["elev_ctx"].astype(np.float64)
    h = np.where(np.isfinite(h), h, np.nanmean(h))
    dr, dc = np.gradient(h, RES)
    ti = grid["thermal_inertia"]
    return dict(
        h=f32(h), dr=f32(dr), dc=f32(dc),
        slope=f32(np.degrees(np.arctan(np.hypot(dr, dc)))),
        rough=f32(np.clip(np.nan_to_num(grid["tri_ctx"], nan=0) / 3.0, 0, 1)),   # TRI 3 m ≈ very rough
        soft=f32(np.clip((260 - np.nan_to_num(ti, nan=260)) / 120, 0, 1)),       # TI < 140 = loose sand
        dune=f32(grid["geo_unit"] == DUNE_UNIT),
        unknown=f32(~np.isfinite(ti)),
        exposure=f32(1 - np.clip(np.nan_to_num(grid["atm_column_pct"], nan=0) / 11, 0, 1)),
        insol=f32(np.nan_to_num(grid["insolation_rel"], nan=1.0)),
    )


def interest_map(grid, targets):
    """0-1 interest map and mask per target. Outside the CRISM footprint it is 0."""
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
            m = np.isin(grid["geo_unit"], vals) * 0.5  # geology is less specific than CRISM
        per_target[name] = m > 0
        total += prio * m.astype(np.float32)
    if not expanded:
        return None, {}
    total = ndimage.uniform_filter(total, int(120 / RES))  # rewards ~120 m patches, not isolated pixels
    return np.clip(total / max(total.max(), 1e-9), 0, 1).astype(np.float32), per_target


# ---------------------------------------------------------------- cost model

def profile(p: Params):
    """Effective weights of a request."""
    S = dict(SAFETY["normal" if (p.human and p.safety == "low") else p.safety])  # crewed: at least normal
    V = VEHICLE
    p_hotel = V["p_hotel"] + (V["p_life_support"] if p.human else 0)
    w = dict(zip(("dist", "time"), {"shortest": (1.0, 0.0), "fastest": (0.0, 1.0), None: (0.5, 0.5)}[p.route_preference]))
    w["energy"] = 1.5 if p.power else 0.15
    w.update({k: S[k] for k in RISK_TERMS if k in S})
    w["exposure"] = 1.0 if p.human else 0.0
    # shadow (only with the shadow map): cold and poor visibility if crewed, no solar charging with power
    w["shadow"] = S["shadow"] + (0.5 if p.human else 0.0) + (1.0 if p.power else 0.0)
    if p.context_free:
        w = {k: 0.0 for k in w} | {"dist": 1.0}
    e_ref = V["mass"] * G_MARS * V["crr_firm"] / V["eff"] / 3600 + p_hotel / V["v0"] / 3600  # Wh/m on flat firm ground
    return S, w, p_hotel, e_ref


def edge_terms(at_u, at_v, mr, mc, p: Params, p_hotel, sun=False):
    """Physics of edge u→v. at_u/at_v(name) return the field at the origin/destination (slices or indices)."""
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
    k = V["mass"] * G_MARS / V["eff"] / 3600  # Wh per metre·(dimensionless)
    # solar charging while driving: with the shadow map, the actual illumination at the passing time; otherwise the annual mean
    solar = avg("illum") if sun else (avg("insol") if p.power else 1.0)
    p_net = np.maximum(p_hotel - V["p_solar"] * solar, 0)
    return dict(L=L, dh=dh, pitch=pitch, cross=cross, t=t, rough=rough, soft=soft, dune=dune,
                unknown=np.maximum(at_u("unknown"), at_v("unknown")), exposure=avg("exposure"),
                e_roll=k * (V["crr_firm"] + V["crr_sand_extra"] * sand) * L, e_climb=k * np.maximum(dh, 0),
                e_hotel=p_net * t / 3600, shadow=avg("shadow") if sun else np.zeros_like(L * dh))


def components(T, p: Params, S, w, e_ref):
    """Cost of each term in equivalent metres (before the science discount)."""
    L = T["L"]
    return dict(
        distance=w["dist"] * L, time=w["time"] * T["t"] * VEHICLE["v0"],
        energy=w["energy"] * (T["e_roll"] + T["e_climb"] + T["e_hotel"]) / e_ref,
        rough=L * w["rough"] * T["rough"], soft=L * w["soft"] * T["soft"], dune=L * w["dune"] * T["dune"],
        pitch=L * w["pitch"] * (T["pitch"] / S["max_pitch"]) ** 2,
        cross=L * w["cross"] * (T["cross"] / S["max_cross"]) ** 2,
        unknown=L * w["unknown"] * T["unknown"], exposure=L * w["exposure"] * T["exposure"],
        shadow=L * w["shadow"] * T["shadow"])


def build_costs(F, p: Params, interest=None, sun_fields=None):
    """Cost (16, H·W) float32 + heuristic constants (hflat, c_climb)."""
    S, w, p_hotel, e_ref = profile(p)
    H, W = F["h"].shape
    hazard = F["slope"] > S["max_pitch"]
    if S["margin"]:
        hazard = ndimage.binary_dilation(hazard, ndimage.generate_binary_structure(2, 1),
                                         iterations=int(round(S["margin"] / RES)))
    if S["forbid_unknown"]:
        hazard |= F["unknown"] > 0
    Fx = dict(F, interest=interest) if interest is not None else dict(F)
    if sun_fields is not None:
        Fx.update(sun_fields)
    cost = np.full((16, H, W), np.inf, np.float32)
    k_climb = VEHICLE["mass"] * G_MARS / VEHICLE["eff"] / 3600
    mult_min = 0.5 if interest is not None else 1.0
    hflat = np.inf
    for d, (mr, mc) in enumerate(MOVES):
        r0, r1, c0, c1 = max(0, -mr), H - max(0, mr), max(0, -mc), W - max(0, mc)
        U = (slice(r0, r1), slice(c0, c1))
        Vv = (slice(r0 + mr, r1 + mr), slice(c0 + mc, c1 + mc))
        T = edge_terms(lambda k: Fx[k][U], lambda k: Fx[k][Vv], mr, mc, p, p_hotel, sun=sun_fields is not None)
        comp = components(T, p, S, w, e_ref)
        mult = 1 - 0.5 * 0.5 * (Fx["interest"][U] + Fx["interest"][Vv]) if interest is not None else 1.0
        # science makes travel cheaper (distance, time, energy), never risk
        o = mult * (comp["distance"] + comp["time"] + comp["energy"]) + sum(comp[k] for k in RISK_TERMS)
        bad = hazard[U] | hazard[Vv] | (np.abs(T["pitch"]) > S["max_pitch"]) | (T["cross"] > S["max_cross"])
        if abs(mr) + abs(mc) == 3:  # knight move: also the two cells it grazes
            touched = ((0, mc // 2), (mr, mc // 2)) if abs(mc) == 2 else ((mr // 2, 0), (mr // 2, mc))
            for ar, ac in touched:
                bad |= hazard[r0 + ar: r1 + ar, c0 + ac: c1 + ac]
        o = np.where(bad, np.inf, o)
        flat = (o - mult_min * w["energy"] * k_climb * np.maximum(T["dh"], 0) / e_ref) / T["L"]
        hflat = min(hflat, float(np.min(flat[np.isfinite(flat)], initial=np.inf)))
        cost[d][U] = o
    c_climb = mult_min * w["energy"] * k_climb / e_ref  # equivalent metres per metre climbed
    return cost.reshape(16, -1), max(hflat, 0.0), c_climb


# ---------------------------------------------------------------- search (Numba)

@njit(cache=True)
def _search(cost, H, W, start, goal, hflat, c_climb, elev, res, stop_nodes):
    """A* (goal >= 0) or Dijkstra (goal < 0; stops once all stop_nodes are closed, if given)."""
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


# ---------------------------------------------------------------- planning

V_ETA = 1.2  # m/s in a straight line from the origin: estimates when each cell is passed


class Planner:
    def __init__(self, use_sun=True):
        self.grid = load_grid()
        self.F = cell_fields(self.grid)
        self.H, self.W = self.F["h"].shape
        self.elev = self.F["h"].astype(np.float64).ravel()
        self._cache = {}  # cost grids per weight profile (~150 MB each)
        self.sun, self.sun_error = None, None
        if use_sun:
            try:
                from shadows import SunShadows
                self.sun = SunShadows(self.F["h"], RES, DATA)
            except (FileNotFoundError, ImportError, ValueError) as e:  # without shadows: insolation_rel is used
                self.sun_error = str(e)
                print(f"warning: no shadow map ({e}); using mean insolation")

    def sun_fields(self, origin_rc, start_hour):
        """Illumination and shadow of each cell at the estimated passing time (distance to origin / V_ETA)."""
        r, c = np.indices((self.H, self.W))
        eta = start_hour + np.hypot(r - origin_rc[0], c - origin_rc[1]) * RES / V_ETA / 3698.9
        illum = self.sun.map_at(eta)
        return dict(illum=illum, shadow=((illum < 0.02) & self.sun.is_day(eta)).astype(np.float32))

    def costs(self, p: Params, interest, origin_rc=None, start_hour=None):
        use_sun = self.sun is not None and start_hour is not None
        key = (p.human, p.safety, p.power, p.route_preference, p.context_free,
               json.dumps(p.science_targets, sort_keys=True),
               (round(start_hour, 2), tuple(origin_rc)) if use_sun else None)
        if key not in self._cache:
            if len(self._cache) >= 4:
                self._cache.pop(next(iter(self._cache)))
            sf = self.sun_fields(origin_rc, start_hour) if use_sun else None
            self._cache[key] = build_costs(self.F, p, interest, sf)
        return self._cache[key]

    def astar(self, cost, a, b, hflat, c_climb):
        return _search(cost, self.H, self.W, a, b, hflat, c_climb, self.elev, RES, NO_STOPS)

    def plan(self, p: Params, via=(), stops=None, pois=None, start_hour=None):
        """Route A→(science stops)→B[→A].

        via: mandatory (row, col) cells (e.g. a charging stop); inserted where they add the least length.
        stops/pois: reuse the stops of a previous plan (avoids repeating the science selection).
        start_hour: local solar departure time; with the shadow map, the cost uses the light at the passing time.
        """
        H, W = self.H, self.W
        interest, per_target = interest_map(self.grid, p.science_targets) if p.science_targets else (None, {})
        o_rc = resolve_place(self.grid, p.origin)
        cost, hflat, c_climb = self.costs(p, interest, o_rc, start_hour)
        o = _nearest_free(cost, H, W, o_rc)
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
                    via=[tuple(v) for v in via], start_hour=start_hour,
                    metrics=self.evaluate(path, p, per_target, start_hour))

    def _science_stops(self, cost, interest, per_target, start, goal, detour, max_pois=10):
        """Greedy orienteering over an exact cost matrix (Dijkstra that stops once all candidates are closed)."""
        H, W = self.H, self.W
        free = np.isfinite(cost).any(0).reshape(H, W)
        lab, n = ndimage.label(interest > 0.15)
        areas = ndimage.sum_labels(np.ones_like(lab), lab, index=np.arange(1, n + 1))
        sums = ndimage.sum_labels(interest, lab, index=np.arange(1, n + 1))
        cands = []
        sr, sc = divmod(start, W)
        gr, gc = divmod(goal, W)
        for i in np.argsort(-sums):
            if areas[i] * RES * RES < 24000 or len(cands) >= max_pois:  # < 2.4 ha: noise
                continue
            vals = np.where((lab == i + 1) & free, interest, -1)
            cell = int(np.argmax(vals))
            r, c = divmod(cell, W)
            if vals.flat[cell] <= 0 or min(math.hypot(r - sr, c - sc), math.hypot(r - gr, c - gc)) * RES < 500:
                continue  # no traversable cell, or right next to A or B (not a useful stop)
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

    def evaluate(self, path, p: Params, per_target=None, start_hour=None):
        """Physical metrics and cost breakdown of any route, measured with the weights of `p`.

        With start_hour and the shadow map, the light of each segment is that of its actual passing time.
        """
        F, W = self.F, self.W
        path = np.asarray(path)
        r, c = path // W, path % W
        u, v = (r[:-1], c[:-1]), (r[1:], c[1:])
        S, w, p_hotel, e_ref = profile(p)
        T = edge_terms(lambda k: F[k][u], lambda k: F[k][v], np.diff(r), np.diff(c), p, p_hotel)
        sun = self.sun is not None and start_hour is not None
        if sun:  # time does not depend on light: first the passing times, then the light at those times
            hours = start_hour + np.concatenate([[0.0], np.cumsum(T["t"])]) / 3698.9
            il = self.sun.at(hours, r, c)
            sh = ((il < 0.02) & self.sun.is_day(hours)).astype(np.float32)  # terrain shadow, not night
            get = lambda idx, sl: (lambda k: il[sl] if k == "illum" else sh[sl] if k == "shadow" else F[k][idx])
            T = edge_terms(get(u, slice(None, -1)), get(v, slice(1, None)), np.diff(r), np.diff(c), p, p_hotel, sun=True)
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
        if sun:
            m["shadow_km"] = float(L[T["shadow"] > 0.5].sum() / 1000)
            m["shadow_pct"] = float(100 * m["shadow_km"] / max(m["distance_km"], 1e-9))
            night = ~self.sun.is_day(0.5 * (hours[:-1] + hours[1:]))
            m["night_km"] = float(L[night].sum() / 1000)
        for name, mask in (per_target or {}).items():
            m[f"on_{name}_km"] = float(L[mask[u] | mask[v]].sum() / 1000)
        m["cum_energy_kwh"] = np.concatenate([[0.0], np.cumsum(e) / 1000])  # for the battery (not sent in the JSON)
        m["cum_time_h"] = np.concatenate([[0.0], np.cumsum(T["t"]) / 3600])
        return m


def classic(p: Params) -> Params:
    """Classic reference A*: pure distance with the minimum physical limits, no mission context."""
    return Params(origin=p.origin, destination=p.destination, route_preference="shortest", safety="low",
                  return_to_origin=p.return_to_origin, context_free=True)


if __name__ == "__main__":
    import sys
    pl = Planner()
    r = pl.plan(Params.from_dict(json.loads(sys.argv[1])))
    m = {k: v for k, v in r.get("metrics", {}).items() if not k.startswith("cum_")}
    print(json.dumps(m or r, indent=1, default=float))
