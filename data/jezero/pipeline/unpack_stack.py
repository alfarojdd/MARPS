"""Rebuild layers20m/<layer>.tif from the published stack, to regenerate the viewer without the raw data.

Usage (from the cloned repo):  python unpack_stack.py
Requires: stack/jezero_stack_20m.tif, extra/geo_unit.tif and, for the background image, assets/JEZ_ctx_B_soc_008_orthoMosaic_6m_*.tif.
"""
import shutil

import rasterio

import build_layers as bl

ORTHO = "JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0.tif"


def main():
    bl.L20.mkdir(parents=True, exist_ok=True)
    with rasterio.open(bl.STACK / "jezero_stack_20m.tif") as s:
        for i, name in enumerate(s.descriptions, start=1):
            prof = s.profile.copy()
            prof.update(count=1)
            with rasterio.open(bl.L20 / f"{name}.tif", "w", **prof) as d:
                d.write(s.read(i), 1)
        print(f"{s.count} capas -> {bl.L20}")
    extra = bl.DATA / "extra/geo_unit.tif"
    if extra.exists():
        shutil.copy(extra, bl.L20 / "geo_unit.tif")
    ortho = bl.ROOT / "assets" / ORTHO
    if ortho.exists() and not (bl.RAW / ORTHO).exists():
        bl.RAW.mkdir(parents=True, exist_ok=True)
        shutil.copy(ortho, bl.RAW / ORTHO)
        print("ortoimagen CTX copiada de assets/")


if __name__ == "__main__":
    main()
