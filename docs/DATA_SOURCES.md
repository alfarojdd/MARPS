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
| 3D relief (`terrain_stl`) | User-supplied root `trekSTL.stl`, Mars Trek export, 400 × 400 XY grid with relative Z. Export layer/extent/settings still **to be confirmed by the data owner** | supplied 2026-11-14; 16,159,584 bytes | Mars Trek terms (NASA/JPL); source export settings not independently verified | ~85 m per cell; 374 × 381 output, georeferenced against CTX DTM (r = 0.978425, RMSE 55.31 m) | Horizontal mirror, fitted 8.680059 m/unit and offset −422.4914 m, crop and CTX texture using `build_terrain3d.py --source stl`; fit stored in the generated manifest | platform/data |
| 3D relief (`terrain_dtm`) | CTX DTM (`elev_ctx`), same as above | accessed 2026-11-14 | Public domain (USGS) | 40 m per cell, whole bbox | Resampled to 800 px wide, same format, with `build_terrain3d.py --source dtm` | data |
| HRSC elevation (`elev_hrsc`) | ESA Mars Express HRSC h0988, included in USGS SIM 3464 (https://pubs.usgs.gov/sim/3464/) | 2026-11-14 | ESA/DLR/FU Berlin, attribution | 75 m, whole bbox | Reprojected to the 20 m grid | data |
| CTX orthoimage | USGS Mars 2020 TRN CTX orthomosaic 6 m | 2026-11-14 | Public domain (USGS) | 6 m, whole bbox (`assets/`) | Tiles for the viewer | data |
| thermal_inertia | Edwards & Buz 2021, THEMIS-derived thermal inertia of Jezero, https://zenodo.org/records/4931348 | 2026-11-14 | CC-BY-4.0 (cite) | 100 m, 96.1 % of the bbox (missing a 1.2 km western strip) | Bilinear resampling to 20 m | data |
| themis_day_ir, themis_night_ir | USGS THEMIS controlled mosaics MC-13 Syrtis Major (STAC `mo_themis_controlled_mosaics`) | 2026-11-14 | Public domain (NASA/JPL/ASU) | 100 m, whole bbox; qualitative DN | Clipped and resampled to 20 m | data |
| insolation_rel, atm_column_pct | Our own computation from `elev_ctx` | 2026-11-14 | n/a | 20 m | Mean insolation without shadows; atmospheric column proxy (not radiation) | data |
| geology (`geo_unit` and vectors) | Sun & Stack 2020, USGS SIM 3464, https://doi.org/10.3133/sim3464 | 2026-11-14 | Public domain (USGS) | 1:75 000, 95.8 % of the bbox | Rasterised to 20 m; vectors simplified to 5 m | data |
| Surface reconstruction catalogue | `MARPS_Jezero_3D` supplied inventory; per-model Sketchfab source/author/licence in `catalogos/modelos_curados.csv` | supplied inventory 2026-11-14 | Per-model terms; external models embedded, not redistributed | 242 entries, 92 approximate rover anchors, 150 without verified coordinates | Retained all entries; separate surface scenes, details and aerial models; no invented positions | platform |
| Cheyava Falls SPZ | Planetary Scene Studio, https://github.com/Matusvec/spaceX-Mhacks-Challenge; supplied `cheyava_falls/splat.spz` + original manifest | supplied inventory 2026-11-14 | Redistribution licence unconfirmed; local user-supplied file only | 972,047 Gaussians, radius 9 m; partial scene from 241 photos, sols 1195–1210 | Published site origin gives map anchor; local SPZ is rotated once for display, not globally surveyed onto every DTM vertex | platform |
| Navcam sol 180 mesh | NASA PDS Mars 2020 Navcam operations mesh bundle, https://pds.nasa.gov/ds-view/pds/viewCollection.jsp?identifier=urn:nasa:pds:mars2020_navcam_ops_mesh:data; supplied OBJ/PNG/XML | supplied inventory 2026-11-14 | NASA/PDS product provenance | Partial stereo observation; site 6, drive 2684 | Local SITE_FRAME conversion for display; PLACES corrected rover position used as approximate map access point | platform |
| Rover localisation / optional historical traverse | Supplied PLACES best_interp/telemetry (https://pds-geosciences.wustl.edu/missions/mars2020/places.htm) and NASA MMGIS waypoints (https://mars.nasa.gov/mmgis-maps/M20/Layers/json/M20_waypoints.json) | supplied inventory 2026-11-14 | NASA/JPL/PDS source attribution | Rover site/drive positions, not reconstruction footprints | Corrected location preferred for the NASA mesh; traverse remains a separate optional context layer | platform |

For the browser relief preparation on 2026-11-14, the 20 m DTM was downloaded directly from [the official USGS product](https://planetarymaps.usgs.gov/mosaic/mars2020_trn/CTX/JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif), which redirects to USGS's `asc-pds-services` S3 archive. It is 9,662,387 bytes, 1596 × 1512 at 20 m, equirectangular Mars sphere R=3,396,190 m. SHA-256: `16a1aa66c3f48c1bca252795827db7b417876217aff0f5e1aff18027fab2327b`. The user-supplied `trekSTL.stl` SHA-256 is `cf5b78219d74b757514c9546f5f78aa6a8d1fb590a5d75e02a0743a4b1d46e09`. The actual output bounds and fit parameters live in the locally generated manifests; raw and generated data are excluded from Git.

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
