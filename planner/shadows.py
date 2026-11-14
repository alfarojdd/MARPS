"""Hourly shadows and illumination for the planner, based on `mars_shadows.py` and `SunAngle.csv`.

- Reads the solar ephemeris (Time UTC, Elevation, Azimuth) and converts it to local solar time (LTST): noon is
  the elevation maximum and one LTST hour lasts 3698.9 s (1/24 of a sol).
- For each sunlit instant it runs `mars_shadows.classify` on the 20 m DTM: cast shadow and self-shadow.
- Stores per instant `illum` = cos(incidence) on lit cells (0 in shadow or at night), as uint8.
  It is the fraction of peak solar power received by a panel lying on the terrain.

Cached in data/jezero/planner_shadows_20m.npz (rebuilt if the CSV changes).
"""
import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

MARS_HOUR_S = 3698.9
HERE = Path(__file__).resolve().parent


def _find(name, extra=()):
    for d in (*extra, HERE, HERE.parent, HERE.parent / "assets"):
        if d and (Path(d) / name).exists():
            return Path(d) / name
    return None


def _import_mars_shadows(data_dir):
    os.environ.setdefault("JEZERO_DATA", str(data_dir))  # keeps the script from searching the disk for the stack
    path = _find("mars_shadows.py", [os.environ.get("MARS_SHADOWS_DIR")])
    if path is None:
        raise FileNotFoundError("mars_shadows.py not found (repo root or MARS_SHADOWS_DIR)")
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    import mars_shadows
    return mars_shadows


def ltst_of(rows):
    """Local solar time of each CSV row (noon is fitted with a parabola around the maximum)."""
    t = [datetime.strptime(r["time"].split(".")[0], "%Y-%jT%H:%M:%S") for r in rows]
    s = np.array([(x - t[0]).total_seconds() for x in t])
    el = np.array([r["elevation"] for r in rows])
    i = int(np.clip(el.argmax(), 1, len(el) - 2))
    a, b, _ = np.polyfit(s[i - 1:i + 2], el[i - 1:i + 2], 2)
    noon = -b / (2 * a)
    return (12 + (s - noon) / MARS_HOUR_S) % 24, el


class SunShadows:
    def __init__(self, dem, res, data_dir, csv_path=None):
        csv_path = Path(csv_path) if csv_path else _find("SunAngle.csv", [os.environ.get("SUN_CSV_DIR"), data_dir])
        if csv_path is None:
            raise FileNotFoundError("SunAngle.csv not found (repo assets/ or SUN_CSV_DIR)")
        ms = _import_mars_shadows(data_dir)
        rows = ms.read_sun_csv(csv_path)
        ltst, el = ltst_of(rows)
        order = np.argsort(ltst)
        self.source = f"{csv_path.name} ({rows[0]['time'][:8]})"
        self.all_hours, self.all_elev = ltst[order], el[order]
        self.sunrise, self.sunset = self._crossings()
        day = [k for k in order if el[k] > 0]
        self.hours = ltst[day]
        self.step_h = float(np.median(np.diff(self.all_hours)))
        key = hashlib.md5(csv_path.read_bytes()).hexdigest()[:10]
        cache = Path(data_dir) / f"planner_shadows_20m_{key}.npz"
        if cache.exists():
            self.illum = np.load(cache)["illum"]
        else:
            ill = np.zeros((len(day), *dem.shape), np.uint8)
            for j, k in enumerate(day):
                cls, cosi = ms.classify(dem.astype(np.float64), res, rows[k]["azimuth"], rows[k]["elevation"])
                ill[j] = np.round(np.clip(cosi, 0, 1) * (cls == ms.LIT) * 255).astype(np.uint8)
            np.savez_compressed(cache, illum=ill)
            self.illum = ill

    def _crossings(self):
        h, e = self.all_hours, self.all_elev
        up = [h[i] - e[i] * (h[i + 1] - h[i]) / (e[i + 1] - e[i]) for i in range(len(h) - 1) if e[i] <= 0 < e[i + 1]]
        down = [h[i] - e[i] * (h[i + 1] - h[i]) / (e[i + 1] - e[i]) for i in range(len(h) - 1) if e[i] > 0 >= e[i + 1]]
        return float(up[0]) if up else 6.0, float(down[-1]) if down else 18.0

    def index(self, hours):
        """Index of the nearest sunlit instant for each hour (-1 at night)."""
        hours = np.asarray(hours, np.float64)
        i = np.clip(np.searchsorted(self.hours, hours), 1, len(self.hours) - 1)
        i = np.where(np.abs(self.hours[i - 1] - hours) <= np.abs(self.hours[i] - hours), i - 1, i)
        night = (hours < self.sunrise) | (hours > self.sunset)
        return np.where(night, -1, i)

    def is_day(self, hours):
        hours = np.asarray(hours)
        return (hours >= self.sunrise) & (hours <= self.sunset)

    def at(self, hours, r, c):
        """0-1 illumination at cells (r, c) at the given hours (arrays of the same size)."""
        idx = self.index(hours)
        out = self.illum[np.maximum(idx, 0), r, c].astype(np.float32) / 255
        return np.where(idx < 0, 0.0, out).astype(np.float32)

    def map_at(self, hours_map):
        """0-1 illumination of the whole grid, each cell at its own hour (hour map of the same size)."""
        H, W = hours_map.shape
        r, c = np.indices((H, W))
        return self.at(hours_map.ravel(), r.ravel(), c.ravel()).reshape(H, W)

    def window_mean(self, h0, h1):
        """Mean illumination of each cell between h0 and h1 (to choose where to charge)."""
        hs = np.arange(h0, h1 + 1e-9, self.step_h)
        idx = self.index(hs)
        idx = idx[idx >= 0]
        if not len(idx):
            return np.zeros(self.illum.shape[1:], np.float32)
        return self.illum[idx].mean(0).astype(np.float32) / 255
