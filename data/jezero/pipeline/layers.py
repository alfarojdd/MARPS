"""Layer catalog: what each layer is, where it comes from and how the viewer renders it.

`src`: file under data/jezero (layers20m/<id>.tif by default).
`kind`: 'image' (grayscale), 'continuous' (color ramp) or 'categorical' (per-class palette).
`maxzoom`: native viewer zoom (z7 = 1 m/px, z5 = 4 m/px, z4 = 8 m/px).
"""

L20 = "layers20m/{}.tif"

LAYERS = [
    # ---------------- base imagery (covers 100 % of the bbox)
    dict(id="ctx_ortho_6m", group="Imagen", title="Ortomosaico CTX (6 m)", kind="image",
         src="raw/JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0.tif", maxzoom=5, vmin=1, vmax=255, stretch="percent", obs=True,
         source="USGS Mars 2020 TRN CTX orthomosaic 6 m (doi:10.5066/P9GV1ND3)"),
    dict(id="hillshade_ctx", group="Imagen", title="Sombreado CTX (20 m)", kind="image", src=L20.format("hillshade_ctx"),
         maxzoom=4, vmin=0, vmax=1, obs=False, source="Derivado del DTM CTX 20 m"),

    # ---------------- topography
    dict(id="elev_ctx", group="Topografía", title="Elevación CTX (20 m)", units="m", kind="continuous", cmap="terrain",
         vmin=-2700, vmax=-1500, maxzoom=4, obs=True, src=L20.format("elev_ctx"),
         source="USGS Mars 2020 TRN CTX DTM 20 m (doi:10.5066/P9GV1ND3)"),
    dict(id="elev_hrsc", group="Topografía", title="Elevación HRSC h0988 (75 m)", units="m", kind="continuous",
         cmap="terrain", vmin=-2700, vmax=-1500, maxzoom=3, obs=True, src=L20.format("elev_hrsc"),
         source="ESA Mars Express HRSC DTM h0988 (incluido en USGS SIM 3464)"),
    dict(id="slope_ctx", group="Topografía", title="Pendiente CTX (20 m)", units="°", kind="continuous", cmap="slope",
         vmin=0, vmax=35, maxzoom=4, obs=False, src=L20.format("slope_ctx"), source="Derivada del DTM CTX 20 m"),
    dict(id="tri_ctx", group="Topografía", title="Índice de rugosidad TRI (CTX)", units="m", kind="continuous",
         cmap="magma", vmin=0, vmax=6, maxzoom=4, obs=False, src=L20.format("tri_ctx"), source="Derivado del DTM CTX 20 m"),
    dict(id="tpi_ctx_500m", group="Topografía", title="Posición topográfica TPI (500 m)", units="m", kind="continuous",
         cmap="RdBu_r", vmin=-40, vmax=40, maxzoom=4, obs=False, src=L20.format("tpi_ctx_500m"),
         source="Derivado del DTM CTX 20 m"),
    dict(id="aspect_ctx", group="Topografía", title="Orientación de ladera (CTX)", units="°", kind="continuous",
         cmap="twilight", vmin=0, vmax=360, maxzoom=4, obs=False, src=L20.format("aspect_ctx"),
         source="Derivada del DTM CTX 20 m"),

    # ---------------- thermal
    dict(id="thermal_inertia", group="Térmico", title="Inercia térmica THEMIS (100 m)", units="J m⁻² K⁻¹ s⁻½",
         kind="continuous", cmap="inferno", vmin=120, vmax=420, maxzoom=3, obs=True, src=L20.format("thermal_inertia"),
         source="Edwards & Buz 2021, THEMIS-derived TI of Jezero (Zenodo 4931348, CC-BY-4.0); sin dato en 1,2 km del borde oeste"),
    dict(id="themis_day_ir", group="Térmico", title="THEMIS IR diurno (100 m)", units="DN", kind="image",
         vmin=1, vmax=255, stretch="percent", maxzoom=3, obs=True, src=L20.format("themis_day_ir"),
         source="USGS THEMIS controlled mosaic MC-13 Syrtis Major, day IR (STAC mo_themis_controlled_mosaics)"),
    dict(id="themis_night_ir", group="Térmico", title="THEMIS IR nocturno (100 m)", units="DN", kind="image",
         vmin=1, vmax=255, stretch="percent", maxzoom=3, obs=True, src=L20.format("themis_night_ir"),
         source="USGS THEMIS controlled mosaic MC-13 Syrtis Major, night IR (STAC mo_themis_controlled_mosaics)"),

    # ---------------- inferred for the mission
    dict(id="insolation_rel", group="Misión (inferido)", title="Insolación directa media relativa", units="× llano",
         kind="continuous", cmap="RdYlBu_r", vmin=0.9, vmax=1.05, maxzoom=4, obs=False, src=L20.format("insolation_rel"),
         source="Modelo propio a partir de pendiente y orientación CTX"),
    dict(id="atm_column_pct", group="Misión (inferido)", title="Blindaje atmosférico extra", units="%",
         kind="continuous", cmap="viridis", vmin=0, vmax=11, maxzoom=4, obs=False, src=L20.format("atm_column_pct"),
         source="Proxy propio: columna atmosférica relativa (H = 11.1 km) sobre el DTM CTX"),

    # ---------------- supplementary: not in the base stack because it does not cover the whole bbox
    dict(id="geo_unit", group="Complementaria (no cubre todo)", title="Unidades geológicas (SIM 3464)", kind="categorical",
         maxzoom=4, obs=True, src=L20.format("geo_unit"), base=False,
         source="Sun & Stack 2020, USGS SIM 3464 (doi:10.3133/sim3464)"),
    dict(id="crism_class", group="Complementaria (no cubre todo)", title="Mineralogía CRISM (clases)", kind="categorical",
         maxzoom=4, obs=True, src=L20.format("crism_class"), base=False, valid_min=0,
         source="Parente, Itoh & Saranathan 2021, CRISM mineral map of Jezero (Zenodo 5575824, CC-BY-4.0); 4 escenas, 41 % del bbox"),
]

# Layers downloaded and processed but dropped for not covering the whole bbox (files remain in data/jezero).
DISCARDED = [
    dict(id="ortho_hirise", file="hires/ortho_hirise_1m.tif", coverage=37, why="Mosaico de 6 ortos HiRISE: solo la franja central"),
    dict(id="slope_hirise_1m", file="hires/slope_hirise_1m.tif", coverage=32, why="DTM HiRISE TRN solo cubre el centro"),
    dict(id="hillshade_hirise", file="hires/hillshade_hirise_1m.tif", coverage=32, why="Igual que el DTM HiRISE"),
    dict(id="thermal_inertia_global", file="layers20m/thermal_inertia_global.tif", coverage=100,
         why="TI global cuantitativa USGS: cubre todo pero tiene bandas entre pasadas THEMIS; se prefirió la de Jezero"),
]

# 20 m stack bands for the planner (fixed order).
STACK_BANDS = [
    dict(id="elev_ctx", units="m", desc="Elevación DTM CTX (areoide)"),
    dict(id="elev_hrsc", units="m", desc="Elevación DTM HRSC h0988"),
    dict(id="slope_ctx", units="deg", desc="Pendiente sobre DTM CTX"),
    dict(id="tri_ctx", units="m", desc="Terrain Ruggedness Index sobre CTX"),
    dict(id="tpi_ctx_500m", units="m", desc="Topographic Position Index, ventana 1 km"),
    dict(id="aspect_ctx", units="deg", desc="Orientación de la ladera (0 = N)"),
    dict(id="hillshade_ctx", units="0-1", desc="Sombreado (sol 315°, 45°)"),
    dict(id="insolation_rel", units="ratio", desc="Insolación directa media relativa al llano (sin sombras)"),
    dict(id="atm_column_pct", units="%", desc="Columna atmosférica extra respecto a la cota máxima"),
    dict(id="thermal_inertia", units="TIU", desc="Inercia térmica THEMIS de Jezero (Edwards & Buz 2021)",
         min_coverage=0.95),  # accepted exception: the 1.2 km western strip is missing (NaN)
    dict(id="themis_day_ir", units="DN", desc="THEMIS IR diurno (cualitativo)"),
    dict(id="themis_night_ir", units="DN", desc="THEMIS IR nocturno (cualitativo)"),
    dict(id="ctx_ortho", units="DN", desc="Ortoimagen CTX promediada a 20 m"),
]

# What each layer is for when planning a traverse and which mission context makes it important.
WHY = {
    "ctx_ortho_6m": "Contexto regional: delta, borde del cráter, campos de dunas. Útil para rutas largas fuera de la huella HiRISE.",
    "hillshade_ctx": "Relieve regional en toda la zona.",
    "elev_ctx": "Desnivel acumulado = energía y tiempo. Importa con batería limitada, carga pesada o EVA a pie.",
    "elev_hrsc": "Tercera fuente independiente de cota para comprobar consistencia de los DTM.",
    "slope_ctx": "Pendiente fuera de la huella HiRISE (subestima pendientes cortas).",
    "tri_ctx": "Rugosidad regional en toda la zona.",
    "tpi_ctx_500m": "Lomas (+) frente a vaguadas (−): las lomas dan línea de vista para comunicaciones; las vaguadas abrigan del viento pero acumulan arena y polvo.",
    "aspect_ctx": "Orientación al sol: térmica de equipos, paneles solares y sombras para la cámara.",
    "thermal_inertia": "Alta = roca o suelo consolidado (buena tracción). Baja = arena y polvo sueltos (riesgo de atasco). Importa en rutas largas o con carga pesada.",
    "themis_day_ir": "Diferencias de temperatura diurna (material suelto se calienta más). Complementa a la inercia térmica.",
    "themis_night_ir": "De noche la roca conserva calor: zonas brillantes = roca expuesta y firme.",
    "geo_unit": "Unidad geológica: tipo de terreno esperado y contexto científico de cada parada (delta, suelo del cráter, dunas).",
    "crism_class": "Minerales que indican agua antigua: carbonatos y esmectitas Fe/Mg (delta y margen del lago), caolinita (alteración intensa); olivino y piroxeno, roca ígnea. Objetivos del contexto científico; solo existe en el centro de la zona.",
    "insolation_rel": "Energía solar disponible y carga térmica según la ladera. Importa en misiones largas con paneles o con ventanas horarias estrictas.",
    "atm_column_pct": "Las zonas bajas tienen más atmósfera encima y reciben algo menos de radiación. Es un proxy grosero; importa en EVA largas o durante eventos solares.",
}
