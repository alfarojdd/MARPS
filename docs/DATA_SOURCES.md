# Data sources and references

Record of **everything we use**: data, code, images and tools. It is required for the submission ("NASA Data" and "Other data and references" fields), and the judges will ask **where each NASA resource comes in and what would change if it were removed**.

Whoever adds a source fills in a row. The URLs in section 2 are candidates **to be verified**.

## 1. Official challenge resources

| Resource | What it is for | URL |
|---|---|---|
| JPL Mars Trek | Portal with Mars layers (relief, mosaics...); candidate layer source | https://trek.nasa.gov/mars/ |
| USGS-NASA Planetary Geologic Mapping | Standardised geologic maps of Mars | https://astrogeology-usgs.hub.arcgis.com/pages/interactive-maps-mars |
| Curiosity's proposed path up Mount Sharp | Visual example of a route map | https://science.nasa.gov/resource/curiositys-proposed-path-up-mount-sharp/ |
| Perseverance Raw Images | First-person images | https://mars.nasa.gov/mars2020/multimedia/raw-images/ |
| NASA Worldview | Inspiration only (it covers Earth) | https://worldview.earthdata.nasa.gov/ |
| Challenge statement | Official text | https://www.spaceappschallenge.org/2026/challenges/interplanetary-survival-guide-martian-map/ |

## 2. Candidate layers (to be verified)

| Data | Instrument / mission | Type | Intended use | Where to look |
|---|---|---|---|---|
| Global topography | MOLA (Mars Global Surveyor) | Topographic | Base relief | Mars Trek, USGS Astrogeology |
| High-resolution elevation models | HiRISE DTM (MRO) | Topographic | Slope and roughness in the chosen area | https://www.uahirise.org/dtm/ |
| Context image | CTX (MRO) | Optical | Visual background layer | PDS / Mars Trek |
| Thermal inertia | THEMIS (Mars Odyssey) | Thermal | Loose ground or firm rock | Mars Trek, PDS |
| Mineralogy | CRISM (MRO) | Spectral | Scientific interest (clays, sulfates...) | PDS Geosciences |
| Radiation | RAD (Curiosity) | Radiation | Exposure, risk windows | PDS |
| Surface weather | MEDA (Perseverance), REMS (Curiosity) | Atmospheric | Temperature and dust | PDS |
| Geology | USGS maps | Geologic | Terrain type and interest | Link in section 1 |

Useful data portals: https://ode.rsl.wustl.edu/mars/ (Mars Orbital Data Explorer) and https://pds-geosciences.wustl.edu/ (PDS Geosciences Node).

## 3. Record of data actually used

Fill in when adding each layer.

| Layer | Source and link | Version or access date | License / terms | Resolution and coverage | Processing applied | Who |
|---|---|---|---|---|---|---|
| _example: elevation_ | _HiRISE DTM XXXX_ | | | | _reprojected, resampled to N m_ | |
| elevation (`elev_ctx`, `slope_ctx`, `tri_ctx`, `tpi_ctx_500m`, `aspect_ctx`, `hillshade_ctx`) | USGS Mars 2020 TRN, MRO CTX DTM, https://planetarymaps.usgs.gov/mosaic/mars2020_trn/CTX/ (doi:10.5066/P9GV1ND3) | accessed 2026-11-14 | Public domain (USGS) | 20 m, whole bbox | Slope, TRI roughness, TPI, aspect and hillshade computed by us | data |
| 3D relief (`terrain_stl`) | JPL Mars Trek STL export, 400 × 400 grid with relative Z (`data/jezero/raw/trekSTL.stl`, not in Git). Export parameters (layer, extent, resolution) not recorded yet: **to be completed by the data owner** | file dated 2026-11-14 | Mars Trek terms (NASA/JPL) | ~85 m per cell, Jezero window; georeferenced by correlation with the CTX DTM (r = 0.978) | Converted to heightmap + texture with `data/jezero/pipeline/build_terrain3d.py` | data |
| 3D relief (`terrain_dtm`) | CTX DTM (`elev_ctx`), same as above | accessed 2026-11-14 | Public domain (USGS) | 40 m per cell, whole bbox | Resampled to 800 px wide, same format, with `build_terrain3d.py --source dtm` | data |
| HRSC elevation (`elev_hrsc`) | ESA Mars Express HRSC h0988, included in USGS SIM 3464 (https://pubs.usgs.gov/sim/3464/) | 2026-11-14 | ESA/DLR/FU Berlin, attribution | 75 m, whole bbox | Reprojected to the 20 m grid | data |
| CTX orthoimage | USGS Mars 2020 TRN CTX orthomosaic 6 m | 2026-11-14 | Public domain (USGS) | 6 m, whole bbox (`assets/`) | Tiles for the viewer | data |
| thermal_inertia | Edwards & Buz 2021, THEMIS-derived thermal inertia of Jezero, https://zenodo.org/records/4931348 | 2026-11-14 | CC-BY-4.0 (cite) | 100 m, 96.1 % of the bbox (missing a 1.2 km western strip) | Bilinear resampling to 20 m | data |
| themis_day_ir, themis_night_ir | USGS THEMIS controlled mosaics MC-13 Syrtis Major (STAC `mo_themis_controlled_mosaics`) | 2026-11-14 | Public domain (NASA/JPL/ASU) | 100 m, whole bbox; qualitative DN | Clipped and resampled to 20 m | data |
| insolation_rel, atm_column_pct | Our own computation from `elev_ctx` | 2026-11-14 | n/a | 20 m | Mean insolation without shadows; atmospheric column proxy (not radiation) | data |
| geology (`geo_unit` and vectors) | Sun & Stack 2020, USGS SIM 3464, https://doi.org/10.3133/sim3464 | 2026-11-14 | Public domain (USGS) | 1:75 000, 95.8 % of the bbox | Rasterised to 20 m; vectors simplified to 5 m | data |

For each layer, answer: what does it measure and in what units? Are there missing values? What does it NOT allow us to conclude? What is observation and what is our own transformation or inference?

## 4. Code, libraries and tools

| Resource | Use | License |
|---|---|---|
| _to be filled in_ | | |

## 5. Use of AI

Declare here which AI tools are used in development and how (the submission requires declaring this and marking generated content):

- Coding assistant: _to be filled in_
- Product's local LLM: _model and runtime to be filled in_

## 6. Processed layers discarded from the base (Jezero)

Discarded because they do not cover the whole bounding box, although they are processed and documented in [JEZERO_LAYERS.md](JEZERO_LAYERS.md): HiRISE DTM and orthoimage (USGS Mars 2020 TRN and STAC, 32-37 %), CRISM mineralogy (Parente, Saranathan & Itoh 2021, Zenodo 5575824, CC-BY-4.0, 41 %) and the quantitative global USGS thermal inertia (100 %, but with striping between passes).
