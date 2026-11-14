# Jezero layers

Which layers the map has, where they come from, how they are generated and what was discarded. Whoever changes the layers updates this file and `docs/DATA_SOURCES.md`.

## Working area
- **Bbox (lon/lat, Mars 2000 sphere R = 3 396 190 m)**: 77.1604655–77.6991776 °E, 18.2110274–18.7211945 °N. About 32 × 30 km on the western edge of Jezero crater: delta, crater floor, Séítah and western rim.
- It matches exactly the extent of the CTX DTM that USGS prepared for Mars 2020 TRN navigation; that is the **common grid**: equirectangular (`+proj=eqc +R=3396190`), 20 m/px, 1596 × 1512 px, NW corner at (4 573 663.25, 1 109 693.14) m.
- **Base rule (decided on 2026-11-14)**: only layers with data over the whole bbox (≥ 99.9 %) go into the base. `pipeline/build_layers.py stack` and the test `test_base_stack_covers_whole_bbox` enforce it. **The only exception accepted by the user: `thermal_inertia` (96.1 %)**, flagged with `min_coverage` in `layers.STACK_BANDS`. Everything is clipped exactly to the bbox; the viewer does not allow leaving the box.

## Where everything is in the repo
| Path | Contents |
|---|---|
| `data/jezero/stack/jezero_stack_20m.tif` + `layers.json` | **Base stack** for the planner: 13 float32 bands (NaN = no data), 85 MB |
| `data/jezero/vectors/` | GeoJSON in metres in the same projection (geology) |
| `data/jezero/extra/geo_unit.tif` | Geologic units (complementary layer, 95.8 %) |
| `data/jezero/pipeline/` | Code that generates everything, plus its tests |
| `platform/viewer/index.html` | Leaflet viewer; tiles are not versioned, they are generated with `make_viewer_data.py` |
| `assets/JEZ_ctx_B_soc_008_orthoMosaic_6m_…tif` | 6 m CTX orthoimage (uploaded by the team); it is the background image |

The original downloads, intermediate layers and discarded layers (HiRISE, CRISM) are not pushed: they are regenerated with the pipeline.

## 1. Base layers (in the stack; all at 100 % except thermal inertia)

| Band | Source | Native res. | Type | What it contributes to the route | Context where it matters most |
|---|---|---|---|---|---|
| `ctx_ortho` (and 6 m tiles) | MRO CTX, USGS Mars 2020 TRN orthomosaic | 6 m | Obs. | Background image: delta, rim, dunes | Always; visual validation |
| `elev_ctx` | MRO CTX DTM, USGS Mars 2020 TRN | 20 m | Obs. | Cumulative elevation change → energy and time | Limited battery, load, EVA on foot |
| `elev_hrsc` | Mars Express HRSC h0988 (in SIM 3464) | 75 m | Obs. | Second independent elevation (quality control) | Detecting DTM artefacts |
| `slope_ctx` | Derived from `elev_ctx` | 20 m | Der. | Safety constraint (rollover, sliding) | Loaded rover, loose ground |
| `tri_ctx` | Terrain Ruggedness Index on CTX | 20 m | Der. | Roughness: wear and vibration | Fragile samples, speed |
| `tpi_ctx_500m` | Topographic Position Index (1 km window) | 20 m | Der. | Ridges (line of sight) versus hollows (shelter, sand) | Communications, wind and dust |
| `aspect_ctx` | Slope aspect (0 = N) | 20 m | Der. | Sun exposure | Panels, thermal, lighting |
| `hillshade_ctx` | Hillshade (sun 315°, 45°) | 20 m | Der. | Reading the relief | Visual |
| `insolation_rel` | Our own model: annual mean cos(incidence) / flat ground, no shadows | 20 m | Der. | Solar energy and thermal load | Long missions with panels |
| `atm_column_pct` | Our own proxy: extra atmospheric column (H = 11.1 km) | 20 m | Der. | More atmosphere overhead in low areas (up to ~11 %) | Long EVAs, solar events |
| `thermal_inertia` (**96.1 %**) | THEMIS, Edwards & Buz 2021 (Zenodo 4931348) | 100 m | Obs.* | High = firm rock; low = sand or dust (getting stuck) | Heavy load, long routes |
| `themis_day_ir` | THEMIS daytime IR, USGS MC-13 controlled mosaic | 100 m | Obs. | Daytime thermal contrast | Complements thermal inertia |
| `themis_night_ir` | THEMIS nighttime IR, USGS MC-13 controlled mosaic | 100 m | Obs. | At night rock retains heat → firm rock | Same |

Obs. = observed; Obs.* = already-interpreted science product; Der. = derived or inferred by us.

### Complementary (in the viewer, outside the stack)
| Layer | Coverage | Why it is kept |
|---|---|---|
| `geo_unit` + geologic vectors (USGS SIM 3464, Sun & Stack 2020, 1:75 000) | 95.8 % (the map ends at 18.70 °N; a 1.3 km strip is missing in the north) | It is the only geologic map at this scale and provides the third data type (geologic) |

### Vectors (inside the bbox)
Geologic contacts, ridges, delta fronts, channels, dark mantles and small craters.

### Data caveats
- **Thermal inertia: the Jezero product was chosen (user decision, 2026-11-14).** It has no data in a 1.2 km strip along the western edge (77.160–77.181 °E): there the band is NaN and the planner must treat it as "unknown", not as zero. The quantitative global USGS alternative covers 100 %, but it has vertical striping between THEMIS passes; compared with the Jezero product, the correlation is 0.41 and it gives +106 TIU on average. It is stored in `layers20m/thermal_inertia_global.tif`.
- **`atm_column_pct` is not radiation.** There is no orbital dose map at this scale.
- **`insolation_rel`** ignores cast shadows and dust.
- **THEMIS IR (DN)** is qualitative: it is useful for comparing areas, not as an absolute temperature.

## 2. Discarded because they do not cover the whole bbox
The files are kept in `data/jezero/` in case they are used as detail later (catalogue in `layers.DISCARDED`).

| Layer | Coverage | Reason |
|---|---|---|
| HiRISE 1 m orthoimage (6 USGS controlled orthos) | 37 % | Central strip only |
| HiRISE TRN 1 m DTM and derivatives (1 m slope, max/mean slope at 20 m, roughness, hillshade, elevation) | 32 % | Centre only (landing area) |
| CRISM mineralogy (Parente et al. 2021, Zenodo 5575824) | 41 % | 4 scenes over the centre of the area |
| Quantitative global USGS thermal inertia (00N060E, 100 m) | 100 % | Striping between THEMIS passes; the Jezero product was preferred |
| THEMIS day/night IR from SIM 3464 (Oct 2018) | 96 % | Northern strip missing; replaced by MC-13 |

Consequence: **the base has no mineralogy and no metre-scale slope**. If they are needed, the options are to use the HiRISE/CRISM layers as detail in the centre only, or to look for full-coverage mineralogy (e.g. MOCAAS, 100 m).

## 3. Sources found but not downloaded
| Source | Why not |
|---|---|
| HiRISE TRN 25 cm orthomosaic (3.4 GB) | Download at <0.5 MB/s; it also only covers the centre |
| ~200 HiRISE observations and 54 individual CTX DTMs (USGS STAC) | Already integrated in the TRN mosaics; partial coverage |
| MOLA 463 m, HRSC-MOLA 200 m, TES (7.4 km) | Coarser than CTX/HRSC |
| MOCAAS (OMEGA/CRISM, 100–500 m) | Not reviewed; candidate for full-coverage mineralogy |
| Zastrow & Glotch 2021 (Zenodo 4673066, 6.7 GB) | Too large |
| MEDA, RAD | Time series, not maps |

## 4. Reproduce
To view or regenerate the viewer only (no raw downloads needed):
```bash
pip install -r data/jezero/pipeline/requirements.txt
cd data/jezero/pipeline
python unpack_stack.py                 # layers20m/ from the published stack
python make_viewer_data.py             # tiles, legends and probe in platform/viewer/data (~2 min)
cd ../../.. && python3 -m http.server 8765 --directory platform/viewer   # http://localhost:8765
python -m pytest -q data/jezero/pipeline
```

Regenerate the stack from the original data (downloads below, in `data/jezero/raw/`):
```bash
python build_layers.py base            # CTX, HRSC, THEMIS (downloads clips), CRISM, geology
python build_layers.py stack           # fails if any base band does not cover the whole bbox
```
`build_layers.py hirise_dtm` / `hirise_ortho` regenerate the discarded HiRISE layers. Each regeneration of the stack adds ~90 MB to the git history: do not push it for every small change.

Manual downloads to `data/jezero/raw/`:
| File | URL |
|---|---|
| `JEZ_ctx_B_soc_008_DTM_…_20m_….tif`, `JEZ_ctx_B_soc_008_orthoMosaic_6m_….tif` | https://planetarymaps.usgs.gov/mosaic/mars2020_trn/CTX/ |
| `JEZ_hirise_soc_006_DTM_…_1m_….tif` (only for discarded layers) | https://planetarymaps.usgs.gov/mosaic/mars2020_trn/HiRISE/ |
| `Jezero_Thermal_Inertia_v1.tiff` | https://zenodo.org/records/4931348 |
| `jezeroFinal.tif`, `Jezero_readme.pdf` | https://zenodo.org/records/5575824 |
| `sim3464_database.zip` → `raw/sim3464/` | https://pubs.usgs.gov/sim/3464/sim3464_database.zip |

The THEMIS clips (`themis_*_clip.tif`) are downloaded only by `build_layers.py`, from the USGS COGs on S3.

## 5. Licenses and citations
- USGS (TRN, SIM 3464, THEMIS mosaics, global thermal inertia): public domain / CC0.
- Edwards & Buz 2021 and Parente et al. 2021: CC-BY-4.0, cite.
- HiRISE: NASA/JPL/University of Arizona. CTX: NASA/JPL/MSSS. HRSC: ESA/DLR/FU Berlin. THEMIS: NASA/JPL/ASU. Free use with attribution.
