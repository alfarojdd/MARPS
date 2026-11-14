"""Planner demo: runs several parameter JSONs with the same A→B, draws the routes and compares metrics.

    python demo.py                                   # scenarios from scenarios.json
    python demo.py scenarios.json out/mi_prueba      # another scenarios file / another output prefix
    python demo.py --json '{"power": true}' --origin landing_site --destination delta_top

Output: <prefix>.png (map + routes) and <prefix>.md (metrics table against the baseline route).
"""
import argparse
import json
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import planner as P

HERE = Path(__file__).parent
COLORS = ["#222222", "#e4572e", "#2e86ab", "#f3a712", "#7d3c98", "#3bb273", "#c0392b"]
CRISM_RGB = {1: (255, 0, 0), 2: (0, 255, 0), 3: (0, 255, 255), 4: (255, 128, 114), 5: (128, 128, 0),
             6: (255, 215, 0), 7: (255, 128, 0), 8: (218, 165, 32), 9: (139, 69, 19), 10: (0, 0, 255)}
ROWS = [("distance_km", "Distancia (km)", "{:.2f}"), ("time_h", "Tiempo (h)", "{:.2f}"),
        ("drive_kwh", "Energía de tracción (kWh)", "{:.2f}"), ("energy_kwh", "Energía total (kWh)", "{:.1f}"), ("ascent_m", "Subida acumulada (m)", "{:.0f}"),
        ("max_pitch_deg", "Pendiente máx. (°)", "{:.1f}"), ("max_cross_deg", "Pendiente lateral máx. (°)", "{:.1f}"),
        ("rough_km", "Tramo rugoso (km)", "{:.2f}"), ("soft_km", "Tramo de suelo blando (km)", "{:.2f}"),
        ("unknown_km", "Tramo sin dato TI (km)", "{:.2f}"), ("on_carbonates_km", "Sobre carbonatos (km)", "{:.2f}"),
        ("on_clays_km", "Sobre arcillas (km)", "{:.2f}"), ("on_delta_km", "Sobre el delta (km)", "{:.2f}")]


def run(pl, base, scenarios):
    out = {}
    for name, d in scenarios.items():
        p = P.Params.from_dict({**base, **d})
        t = time.perf_counter()
        r = pl.plan(p)
        r["seconds"] = time.perf_counter() - t
        out[name] = r
        print(f"{name:20s} {'ok' if r['ok'] else r['reason']}  {r['seconds']:.1f} s  nodos expandidos {r.get('expanded', 0):,}")
    return out


def table(results):
    names = list(results)
    ref = next((results[n] for n in names if n.startswith("base")), results[names[0]])
    sci = {k for r in results.values() if r["ok"] for k in r["metrics"] if k.startswith("on_")}
    lines = ["| Métrica | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for key, label, fmt in ROWS:
        if key.startswith("on_") and key not in sci:
            continue
        cells = []
        for n in names:
            m = results[n].get("metrics", {})
            if key not in m:
                cells.append("–")
                continue
            v, b = m[key], ref["metrics"].get(key)
            s = fmt.format(v)
            if results[n] is not ref and b and key in ("distance_km", "time_h", "drive_kwh", "energy_kwh", "ascent_m"):
                s += f" ({(v - b) / b * 100:+.0f} %)"
            cells.append(s)
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    lines.append("| Puntos de interés visitados | " + " | ".join(
        str(len(results[n].get("pois", []))) for n in names) + " |")
    return "\n".join(lines)


def figure(pl, results, path):
    g = pl.grid
    hs = np.nan_to_num(g["hillshade_ctx"], nan=0.5)
    H, W = hs.shape
    fig, axes = plt.subplots(1, 2, figsize=(17, 8.5), gridspec_kw=dict(width_ratios=[1, 1]))
    for ax, title in zip(axes, ["Rutas sobre relieve + mineralogía CRISM", "Rutas sobre pendiente"]):
        if "pendiente" in title:
            ax.imshow(pl.F["slope"], cmap="magma_r", vmin=0, vmax=25)
        else:
            ax.imshow(hs, cmap="gray")
            ov = np.zeros((H, W, 4))
            for v, rgb in CRISM_RGB.items():
                ov[g["crism_class"] == v] = (*(np.array(rgb) / 255), 0.45)
            ax.imshow(ov)
        for (name, r), col in zip(results.items(), COLORS):
            if not r["ok"]:
                continue
            rr, cc = r["path"] // W, r["path"] % W
            ax.plot(cc, rr, color=col, lw=2.2 if name.startswith("base") else 2.6,
                    ls="--" if name.startswith("base") else "-", label=name)
            for poi in r.get("pois", []):
                ax.plot(poi["rc"][1], poi["rc"][0], "o", mec="white", mfc=col, ms=8)
        r0 = next(r for r in results.values() if r["ok"])
        for i, node in ((0, r0["path"][0]), (1, r0["path"][-1])):
            ax.plot(node % W, node // W, marker="*", color="white", mec="black", ms=18)
            ax.annotate("A" if i == 0 else "B", (node % W, node // W), xytext=(8, 8), textcoords="offset points",
                        color="white", weight="bold", fontsize=14)
        ax.set_title(title)
        ax.set_xticks([]); ax.set_yticks([])
    axes[0].legend(loc="lower left", fontsize=10, framealpha=0.85)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenarios", nargs="?", default=str(HERE / "scenarios.json"))
    ap.add_argument("out", nargs="?", default=str(HERE / "out/demo"))
    ap.add_argument("--json", help="un único JSON de parámetros; se compara con la ruta base")
    ap.add_argument("--origin")
    ap.add_argument("--destination")
    a = ap.parse_args()
    cfg = json.loads(Path(a.scenarios).read_text())
    base = dict(origin=a.origin or cfg["origin"], destination=a.destination or cfg["destination"])
    scen = cfg["scenarios"]
    if a.json:
        scen = {"base_mas_corta": {"route_preference": "shortest", "safety": "low", "context_free": True}, "consulta": json.loads(a.json)}
    pl = P.Planner()
    res = run(pl, base, scen)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    figure(pl, res, out.with_suffix(".png"))
    md = f"A = {base['origin']}, B = {base['destination']}\n\n" + table(res) + "\n"
    out.with_suffix(".md").write_text(md)
    print("\n" + md)
    print(f"figura: {out.with_suffix('.png')}")


if __name__ == "__main__":
    main()
