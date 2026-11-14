# Capas de Jezero

Qué capas tiene el mapa, de dónde salen, cómo se generan y qué se descartó. Quien cambie las capas actualiza este fichero y `docs/FUENTES.md`.

## Zona de trabajo
- **Bbox (lon/lat, esfera Mars 2000 R = 3 396 190 m)**: 77.1604655–77.6991776 °E, 18.2110274–18.7211945 °N. Unos 32 × 30 km en el borde oeste del cráter Jezero: delta, suelo del cráter, Séítah, borde oeste y elipse de aterrizaje de Perseverance.
- Coincide exactamente con la extensión del DTM CTX que USGS preparó para la navegación TRN de Mars 2020; esa es la **rejilla común**: equirectangular (`+proj=eqc +R=3396190`), 20 m/px, 1596 × 1512 px, esquina NO en (4 573 663.25, 1 109 693.14) m.
- **Regla de la base (decidida el 2026-11-14)**: solo entran en la base las capas con dato en todo el bbox (≥ 99,9 %). `pipeline/build_layers.py stack` y la prueba `test_base_stack_covers_whole_bbox` lo hacen cumplir. **Única excepción aceptada por el usuario: `thermal_inertia` (96,1 %)**, marcada con `min_coverage` en `layers.STACK_BANDS`. Todo se recorta exactamente al bbox; el visor no deja salir del recuadro.

## Dónde está cada cosa en el repo
| Ruta | Contenido |
|---|---|
| `data/jezero/stack/jezero_stack_20m.tif` + `layers.json` | **Stack base** para el planificador: 14 bandas float32 (NaN = sin dato), 90 MB |
| `data/jezero/vectors/` | GeoJSON en metros de la misma proyección (traza, waypoints, elipse, geología) |
| `data/jezero/extra/geo_unit.tif` | Unidades geológicas (capa complementaria, 95,8 %) |
| `data/jezero/pipeline/` | Código que genera todo y sus pruebas |
| `platform/viewer/index.html` | Visor Leaflet; las teselas no se versionan, se generan con `make_viewer_data.py` |
| `assets/JEZ_ctx_B_soc_008_orthoMosaic_6m_…tif` | Ortoimagen CTX de 6 m (subida por el equipo); es la imagen de fondo |

Las descargas originales, las capas intermedias y las capas descartadas (HiRISE, CRISM) no se suben: se regeneran con el pipeline.

## 1. Capas base (en el stack; todas al 100 % salvo la inercia térmica)

| Banda | Fuente | Res. nativa | Tipo | Qué aporta a la ruta | Contexto en que pesa más |
|---|---|---|---|---|---|
| `ctx_ortho` (y teselas a 6 m) | MRO CTX, ortomosaico USGS Mars 2020 TRN | 6 m | Obs. | Imagen de fondo: delta, borde, dunas | Siempre; validación visual |
| `elev_ctx` | MRO CTX DTM, USGS Mars 2020 TRN | 20 m | Obs. | Desnivel acumulado → energía y tiempo | Batería limitada, carga, EVA a pie |
| `elev_hrsc` | Mars Express HRSC h0988 (en SIM 3464) | 75 m | Obs. | Segunda cota independiente (control de calidad) | Detectar artefactos del DTM |
| `slope_ctx` | Derivada de `elev_ctx` | 20 m | Der. | Restricción de seguridad (vuelco, deslizamiento) | Rover cargado, terreno suelto |
| `tri_ctx` | Terrain Ruggedness Index sobre CTX | 20 m | Der. | Rugosidad: desgaste y vibración | Muestras frágiles, velocidad |
| `tpi_ctx_500m` | Topographic Position Index (ventana 1 km) | 20 m | Der. | Lomas (línea de vista) frente a vaguadas (abrigo, arena) | Comunicaciones, viento y polvo |
| `aspect_ctx` | Orientación de ladera (0 = N) | 20 m | Der. | Exposición al sol | Paneles, térmica, iluminación |
| `hillshade_ctx` | Sombreado (sol 315°, 45°) | 20 m | Der. | Lectura del relieve | Visual |
| `insolation_rel` | Modelo propio: cos(incidencia) medio anual / llano, sin sombras | 20 m | Der. | Energía solar y carga térmica | Misiones largas con paneles |
| `atm_column_pct` | Proxy propio: columna atmosférica extra (H = 11,1 km) | 20 m | Der. | Más atmósfera encima en zonas bajas (hasta ~11 %) | EVA largas, eventos solares |
| `thermal_inertia` (**96,1 %**) | THEMIS, Edwards & Buz 2021 (Zenodo 4931348) | 100 m | Obs.* | Alta = roca firme; baja = arena o polvo (atasco) | Carga pesada, rutas largas |
| `themis_day_ir` | THEMIS IR diurno, mosaico controlado USGS MC-13 | 100 m | Obs. | Contraste térmico diurno | Complemento de la inercia térmica |
| `themis_night_ir` | THEMIS IR nocturno, mosaico controlado USGS MC-13 | 100 m | Obs. | De noche la roca conserva calor → roca firme | Igual |
| `dist_traverse` | Derivada de la traza M20 (NASA/JPL MMGIS, hasta sol 2022) | 20 m | Der. | Distancia a terreno ya recorrido con éxito | Misiones conservadoras |

Obs. = observado; Obs.* = producto científico ya interpretado; Der. = derivado o inferido por nosotros.

### Complementaria (en el visor, fuera del stack)
| Capa | Cobertura | Por qué se mantiene |
|---|---|---|
| `geo_unit` + vectores geológicos (USGS SIM 3464, Sun & Stack 2020, 1:75 000) | 95,8 % (el mapa acaba en 18,70 °N; falta una franja de 1,3 km al norte) | Es el único mapa geológico a esta escala y aporta el tercer tipo de dato (geológico) |

### Vectores (dentro del bbox)
Traza de Perseverance (555 tramos), waypoints (708), elipse de aterrizaje, contactos geológicos, crestas, frentes de delta, canales, mantos oscuros y cráteres pequeños.

### Avisos sobre los datos
- **Inercia térmica: se eligió la de Jezero (decisión del usuario, 2026-11-14).** No tiene dato en una franja de 1,2 km del borde oeste (77.160–77.181 °E): ahí la banda vale NaN y el planificador debe tratarla como "desconocido", no como cero. La alternativa global cuantitativa de USGS cubre el 100 %, pero tiene bandas verticales entre pasadas de THEMIS; comparada con la de Jezero, la correlación es de 0,41 y da +106 TIU de media. Se guarda en `layers20m/thermal_inertia_global.tif`.
- **`atm_column_pct` no es radiación.** No existe un mapa orbital de dosis a esta escala.
- **`insolation_rel`** ignora las sombras proyectadas y el polvo.
- **THEMIS IR (DN)** es cualitativo: sirve para comparar zonas, no como temperatura absoluta.

## 2. Descartadas por no cubrir todo el bbox
Los ficheros se conservan en `data/jezero/` por si se usan como detalle más adelante (catálogo en `layers.DISCARDED`).

| Capa | Cobertura | Motivo |
|---|---|---|
| Ortoimagen HiRISE 1 m (6 ortos controladas USGS) | 37 % | Solo la franja central |
| DTM HiRISE TRN 1 m y derivadas (pendiente 1 m, pendiente máx./media en 20 m, rugosidad, sombreado, cota) | 32 % | Solo el centro (zona de aterrizaje) |
| Mineralogía CRISM (Parente et al. 2021, Zenodo 5575824) | 41 % | 4 escenas sobre la elipse |
| Inercia térmica global cuantitativa USGS (00N060E, 100 m) | 100 % | Bandas entre pasadas THEMIS; se prefirió la de Jezero |
| THEMIS IR día/noche de SIM 3464 (oct 2018) | 96 % | Falta la franja norte; sustituidos por MC-13 |

Consecuencia: **la base no tiene mineralogía ni pendiente a escala de metro**. Si se necesitan, las opciones son usar las capas HiRISE/CRISM como detalle solo en el centro, o buscar mineralogía de cobertura completa (p. ej. MOCAAS, 100 m).

## 3. Fuentes encontradas y no descargadas
| Fuente | Por qué no |
|---|---|
| Ortomosaico HiRISE TRN 25 cm (3,4 GB) | Descarga a <0,5 MB/s; además solo cubre el centro |
| ~200 observaciones HiRISE y 54 DTM CTX individuales (STAC USGS) | Ya integradas en los mosaicos TRN; cobertura parcial |
| MOLA 463 m, HRSC-MOLA 200 m, TES (7,4 km) | Más gruesos que CTX/HRSC |
| MOCAAS (OMEGA/CRISM, 100–500 m) | No revisado; candidato para mineralogía completa |
| Zastrow & Glotch 2021 (Zenodo 4673066, 6,7 GB) | Muy pesado |
| MEDA, RAD | Series temporales, no mapas |

## 4. Reproducir
Solo ver o regenerar el visor (no hace falta descargar nada crudo):
```bash
pip install -r data/jezero/pipeline/requirements.txt
cd data/jezero/pipeline
python unpack_stack.py                 # layers20m/ a partir del stack publicado
python make_viewer_data.py             # teselas, leyendas y sonda en platform/viewer/data (~2 min)
cd ../../.. && python3 -m http.server 8765 --directory platform/viewer   # http://localhost:8765
python -m pytest -q data/jezero/pipeline
```

Regenerar el stack desde los datos originales (descargas abajo en `data/jezero/raw/`):
```bash
python build_layers.py base            # CTX, HRSC, THEMIS (descarga recortes), CRISM, geología, traza
python build_layers.py stack           # falla si alguna banda base no cubre todo el bbox
```
`build_layers.py hirise_dtm` / `hirise_ortho` regeneran las capas HiRISE descartadas. Cada regeneración del stack añade ~90 MB al historial de git: no lo subáis por cada cambio pequeño.

Descargas manuales a `data/jezero/raw/`:
| Fichero | URL |
|---|---|
| `JEZ_ctx_B_soc_008_DTM_…_20m_….tif`, `JEZ_ctx_B_soc_008_orthoMosaic_6m_….tif` | https://planetarymaps.usgs.gov/mosaic/mars2020_trn/CTX/ |
| `JEZ_hirise_soc_006_DTM_…_1m_….tif` (solo para capas descartadas) | https://planetarymaps.usgs.gov/mosaic/mars2020_trn/HiRISE/ |
| `Jezero_Thermal_Inertia_v1.tiff` | https://zenodo.org/records/4931348 |
| `jezeroFinal.tif`, `Jezero_readme.pdf` | https://zenodo.org/records/5575824 |
| `sim3464_database.zip` → `raw/sim3464/` | https://pubs.usgs.gov/sim/3464/sim3464_database.zip |
| `M20_traverse.json`, `M20_waypoints.json` | https://mars.nasa.gov/mmgis-maps/M20/Layers/json/ |

Los recortes THEMIS (`themis_*_clip.tif`) los descarga solo `build_layers.py`, desde los COG de USGS en S3.

## 5. Licencias y citas
- USGS (TRN, SIM 3464, mosaicos THEMIS, inercia térmica global): dominio público / CC0.
- Edwards & Buz 2021 y Parente et al. 2021: CC-BY-4.0, citar.
- HiRISE: NASA/JPL/University of Arizona. CTX: NASA/JPL/MSSS. HRSC: ESA/DLR/FU Berlin. THEMIS: NASA/JPL/ASU. Uso libre con atribución.
