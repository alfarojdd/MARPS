"""Layer catalog: what each layer is, where it comes from and how the viewer renders it.

`src`: file under data/jezero (layers20m/<id>.tif by default).
`kind`: 'image' (grayscale), 'continuous' (color ramp) or 'categorical' (per-class palette).
`maxzoom`: native viewer zoom (z7 = 1 m/px, z5 = 4 m/px, z4 = 8 m/px).
"""

L20 = "layers20m/{}.tif"

LAYERS = [
    # ---------------- base imagery (covers 100 % of the bbox)
    dict(id="ctx_ortho_6m", group="Imagery", title="CTX orthomosaic (6 m)", kind="image",
         src="raw/JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0.tif", maxzoom=5, vmin=1, vmax=255, stretch="percent", obs=True,
         source="USGS Mars 2020 TRN CTX orthomosaic 6 m (doi:10.5066/P9GV1ND3)"),
    dict(id="hillshade_ctx", group="Imagery", title="CTX hillshade (20 m)", kind="image", src=L20.format("hillshade_ctx"),
         maxzoom=4, vmin=0, vmax=1, obs=False, source="Derived from the CTX 20 m DTM"),

    # ---------------- topography
    dict(id="elev_ctx", group="Topography", title="CTX elevation (20 m)", units="m", kind="continuous", cmap="terrain",
         vmin=-2700, vmax=-1500, maxzoom=4, obs=True, src=L20.format("elev_ctx"),
         source="USGS Mars 2020 TRN CTX DTM 20 m (doi:10.5066/P9GV1ND3)"),
    dict(id="elev_hrsc", group="Topography", title="HRSC h0988 elevation (75 m)", units="m", kind="continuous",
         cmap="terrain", vmin=-2700, vmax=-1500, maxzoom=3, obs=True, src=L20.format("elev_hrsc"),
         source="ESA Mars Express HRSC DTM h0988 (included in USGS SIM 3464)"),
    dict(id="slope_ctx", group="Topography", title="CTX slope (20 m)", units="°", kind="continuous", cmap="slope",
         vmin=0, vmax=35, maxzoom=4, obs=False, src=L20.format("slope_ctx"), source="Derived from the CTX 20 m DTM"),
    dict(id="tri_ctx", group="Topography", title="Terrain Ruggedness Index, TRI (CTX)", units="m", kind="continuous",
         cmap="magma", vmin=0, vmax=6, maxzoom=4, obs=False, src=L20.format("tri_ctx"), source="Derived from the CTX 20 m DTM"),
    dict(id="tpi_ctx_500m", group="Topography", title="Topographic Position Index, TPI (500 m)", units="m", kind="continuous",
         cmap="RdBu_r", vmin=-40, vmax=40, maxzoom=4, obs=False, src=L20.format("tpi_ctx_500m"),
         source="Derived from the CTX 20 m DTM"),
    dict(id="aspect_ctx", group="Topography", title="CTX aspect", units="°", kind="continuous",
         cmap="twilight", vmin=0, vmax=360, maxzoom=4, obs=False, src=L20.format("aspect_ctx"),
         source="Derived from the CTX 20 m DTM"),

    # ---------------- thermal
    dict(id="thermal_inertia", group="Thermal", title="THEMIS thermal inertia (100 m)", units="J m⁻² K⁻¹ s⁻½",
         kind="continuous", cmap="inferno", vmin=120, vmax=420, maxzoom=3, obs=True, src=L20.format("thermal_inertia"),
         source="Edwards & Buz 2021, THEMIS-derived TI of Jezero (Zenodo 4931348, CC-BY-4.0); no data in the 1.2 km western strip"),
    dict(id="themis_day_ir", group="Thermal", title="THEMIS day IR (100 m)", units="DN", kind="image",
         vmin=1, vmax=255, stretch="percent", maxzoom=3, obs=True, src=L20.format("themis_day_ir"),
         source="USGS THEMIS controlled mosaic MC-13 Syrtis Major, day IR (STAC mo_themis_controlled_mosaics)"),
    dict(id="themis_night_ir", group="Thermal", title="THEMIS night IR (100 m)", units="DN", kind="image",
         vmin=1, vmax=255, stretch="percent", maxzoom=3, obs=True, src=L20.format("themis_night_ir"),
         source="USGS THEMIS controlled mosaic MC-13 Syrtis Major, night IR (STAC mo_themis_controlled_mosaics)"),

    # ---------------- inferred for the mission
    dict(id="insolation_rel", group="Mission (derived)", title="Mean relative direct insolation", units="× flat ground",
         kind="continuous", cmap="RdYlBu_r", vmin=0.9, vmax=1.05, maxzoom=4, obs=False, src=L20.format("insolation_rel"),
         source="In-house model from CTX slope and aspect"),
    dict(id="atm_column_pct", group="Mission (derived)", title="Extra atmospheric shielding", units="%",
         kind="continuous", cmap="viridis", vmin=0, vmax=11, maxzoom=4, obs=False, src=L20.format("atm_column_pct"),
         source="In-house proxy: relative atmospheric column (H = 11.1 km) over the CTX DTM"),

    # ---------------- supplementary: not in the base stack because it does not cover the whole bbox
    dict(id="geo_unit", group="Supplementary (partial coverage)", title="Geologic units (SIM 3464)", kind="categorical",
         maxzoom=4, obs=True, src=L20.format("geo_unit"), base=False,
         source="Sun & Stack 2020, USGS SIM 3464 (doi:10.3133/sim3464)"),
    dict(id="crism_class", group="Supplementary (partial coverage)", title="CRISM mineralogy (classes)", kind="categorical",
         maxzoom=4, obs=True, src=L20.format("crism_class"), base=False, valid_min=0,
         source="Parente, Itoh & Saranathan 2021, CRISM mineral map of Jezero (Zenodo 5575824, CC-BY-4.0); 4 scenes, 41 % of the bbox"),
]

# Layers downloaded and processed but dropped for not covering the whole bbox (files remain in data/jezero).
DISCARDED = [
    dict(id="ortho_hirise", file="hires/ortho_hirise_1m.tif", coverage=37, why="Mosaic of 6 HiRISE orthoimages: central strip only"),
    dict(id="slope_hirise_1m", file="hires/slope_hirise_1m.tif", coverage=32, why="HiRISE TRN DTM covers only the center"),
    dict(id="hillshade_hirise", file="hires/hillshade_hirise_1m.tif", coverage=32, why="Same footprint as the HiRISE DTM"),
    dict(id="thermal_inertia_global", file="layers20m/thermal_inertia_global.tif", coverage=100,
         why="USGS quantitative global TI: full coverage but striped between THEMIS passes; the Jezero product is preferred"),
]

# 20 m stack bands for the planner (fixed order).
STACK_BANDS = [
    dict(id="elev_ctx", units="m", desc="CTX DTM elevation (areoid)"),
    dict(id="elev_hrsc", units="m", desc="HRSC h0988 DTM elevation"),
    dict(id="slope_ctx", units="deg", desc="Slope from the CTX DTM"),
    dict(id="tri_ctx", units="m", desc="Terrain Ruggedness Index from CTX"),
    dict(id="tpi_ctx_500m", units="m", desc="Topographic Position Index, 1 km window"),
    dict(id="aspect_ctx", units="deg", desc="Slope aspect (0 = N)"),
    dict(id="hillshade_ctx", units="0-1", desc="Hillshade (sun azimuth 315°, elevation 45°)"),
    dict(id="insolation_rel", units="ratio", desc="Mean direct insolation relative to flat ground (no cast shadows)"),
    dict(id="atm_column_pct", units="%", desc="Extra atmospheric column relative to the highest elevation"),
    dict(id="thermal_inertia", units="TIU", desc="THEMIS thermal inertia of Jezero (Edwards & Buz 2021)",
         min_coverage=0.95),  # accepted exception: the 1.2 km western strip is missing (NaN)
    dict(id="themis_day_ir", units="DN", desc="THEMIS day IR (qualitative)"),
    dict(id="themis_night_ir", units="DN", desc="THEMIS night IR (qualitative)"),
    dict(id="ctx_ortho", units="DN", desc="CTX orthoimage averaged to 20 m"),
]

# What each layer is for when planning a traverse and which mission context makes it important.
WHY = {
    "ctx_ortho_6m": "Regional context: delta, crater rim, dune fields. Useful for long routes outside the HiRISE footprint.",
    "hillshade_ctx": "Regional relief across the whole area.",
    "elev_ctx": "Cumulative elevation change = energy and time. Matters with limited battery, heavy payload or EVA on foot.",
    "elev_hrsc": "Third independent elevation source for cross-checking DTM consistency.",
    "slope_ctx": "Slope outside the HiRISE footprint (underestimates short slopes).",
    "tri_ctx": "Regional roughness across the whole area.",
    "tpi_ctx_500m": "Ridges (+) versus hollows (−): ridges give line of sight for communications; hollows shelter from wind but collect sand and dust.",
    "aspect_ctx": "Orientation to the sun: equipment thermal load, solar panels and camera shadows.",
    "thermal_inertia": "High = rock or consolidated soil (good traction). Low = loose sand and dust (risk of getting stuck). Matters on long routes or with heavy payload.",
    "themis_day_ir": "Daytime temperature differences (loose material heats up more). Complements thermal inertia.",
    "themis_night_ir": "At night rock retains heat: bright areas = exposed, firm rock.",
    "geo_unit": "Geologic unit: expected terrain type and scientific context of each stop (delta, crater floor, dunes).",
    "crism_class": "Minerals indicating ancient water: carbonates and Fe/Mg smectites (delta and lake margin), kaolinite (intense alteration); olivine and pyroxene indicate igneous rock. Science targets; available only in the central part of the area.",
    "insolation_rel": "Available solar energy and thermal load depending on the slope. Matters in long missions with panels or strict time windows.",
    "atm_column_pct": "Low-lying areas have more atmosphere overhead and receive somewhat less radiation. A coarse proxy; matters in long EVAs or during solar events.",
}
