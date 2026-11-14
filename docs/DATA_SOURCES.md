# Fuentes de datos y referencias

Registro de **todo lo que usamos**: datos, código, imágenes y herramientas. Es obligatorio para la entrega (campos "NASA Data" y "Otros datos y referencias"), y el jurado preguntará **dónde interviene cada recurso NASA y qué cambiaría si se retirara**.

Quien añada una fuente rellena una fila. Las URLs de la sección 2 son candidatas **por verificar**.

## 1. Recursos oficiales del reto

| Recurso | Para qué sirve | URL |
|---|---|---|
| JPL Mars Trek | Portal con capas de Marte (relieve, mosaicos...); candidato a fuente de capas | https://trek.nasa.gov/mars/ |
| USGS-NASA Planetary Geologic Mapping | Mapas geológicos estandarizados de Marte | https://astrogeology-usgs.hub.arcgis.com/pages/interactive-maps-mars |
| Ruta propuesta de Curiosity en Mount Sharp | Ejemplo visual de mapa de ruta | https://science.nasa.gov/resource/curiositys-proposed-path-up-mount-sharp/ |
| Perseverance Raw Images | Imágenes en primera persona | https://mars.nasa.gov/mars2020/multimedia/raw-images/ |
| NASA Worldview | Solo inspiración (es de la Tierra) | https://worldview.earthdata.nasa.gov/ |
| Enunciado del reto | Texto oficial | https://www.spaceappschallenge.org/2026/challenges/interplanetary-survival-guide-martian-map/ |

## 2. Candidatas a capas (por verificar)

| Dato | Instrumento / misión | Tipo | Uso previsto | Dónde buscar |
|---|---|---|---|---|
| Topografía global | MOLA (Mars Global Surveyor) | Topográfico | Relieve base | Mars Trek, USGS Astrogeology |
| Modelos de elevación de alta resolución | HiRISE DTM (MRO) | Topográfico | Pendiente y rugosidad en la zona elegida | https://www.uahirise.org/dtm/ |
| Imagen de contexto | CTX (MRO) | Óptico | Capa visual de fondo | PDS / Mars Trek |
| Inercia térmica | THEMIS (Mars Odyssey) | Térmico | Terreno suelto o roca firme | Mars Trek, PDS |
| Mineralogía | CRISM (MRO) | Espectral | Interés científico (arcillas, sulfatos...) | PDS Geosciences |
| Radiación | RAD (Curiosity) | Radiación | Exposición, ventanas de riesgo | PDS |
| Meteorología de superficie | MEDA (Perseverance), REMS (Curiosity) | Atmosférico | Temperatura y polvo | PDS |
| Geología | Mapas USGS | Geológico | Tipo de terreno e interés | Enlace del punto 1 |

Portales de datos útiles: https://ode.rsl.wustl.edu/mars/ (Mars Orbital Data Explorer) y https://pds-geosciences.wustl.edu/ (PDS Geosciences Node).

## 3. Registro de datos realmente usados

Rellenar al incorporar cada capa.

| Capa | Fuente y enlace | Versión o fecha de consulta | Licencia / condiciones | Resolución y cobertura | Procesado aplicado | Quién |
|---|---|---|---|---|---|---|
| _ejemplo: elevation_ | _HiRISE DTM XXXX_ | | | | _reproyectado, remuestreado a N m_ | |
| elevation (`elev_ctx`, `slope_ctx`, `tri_ctx`, `tpi_ctx_500m`, `aspect_ctx`, `hillshade_ctx`) | USGS Mars 2020 TRN, DTM de MRO CTX, https://planetarymaps.usgs.gov/mosaic/mars2020_trn/CTX/ (doi:10.5066/P9GV1ND3) | consultado 2026-11-14 | Dominio público (USGS) | 20 m, todo el bbox | Pendiente, rugosidad TRI, TPI, orientación y sombreado calculados por nosotros | data |
| elevación HRSC (`elev_hrsc`) | ESA Mars Express HRSC h0988, incluido en USGS SIM 3464 (https://pubs.usgs.gov/sim/3464/) | 2026-11-14 | ESA/DLR/FU Berlin, atribución | 75 m, todo el bbox | Reproyectado a la rejilla de 20 m | data |
| ortoimagen CTX | USGS Mars 2020 TRN CTX orthomosaic 6 m | 2026-11-14 | Dominio público (USGS) | 6 m, todo el bbox (`assets/`) | Teselas para el visor | data |
| thermal_inertia | Edwards & Buz 2021, THEMIS-derived thermal inertia of Jezero, https://zenodo.org/records/4931348 | 2026-11-14 | CC-BY-4.0 (citar) | 100 m, 96,1 % del bbox (falta franja oeste de 1,2 km) | Remuestreo bilineal a 20 m | data |
| themis_day_ir, themis_night_ir | USGS THEMIS controlled mosaics MC-13 Syrtis Major (STAC `mo_themis_controlled_mosaics`) | 2026-11-14 | Dominio público (NASA/JPL/ASU) | 100 m, todo el bbox; DN cualitativos | Recorte y remuestreo a 20 m | data |
| insolation_rel, atm_column_pct | Cálculo propio sobre `elev_ctx` | 2026-11-14 | n/a | 20 m | Insolación media sin sombras; proxy de columna atmosférica (no es radiación) | data |
| geología (`geo_unit` y vectores) | Sun & Stack 2020, USGS SIM 3464, https://doi.org/10.3133/sim3464 | 2026-11-14 | Dominio público (USGS) | 1:75 000, 95,8 % del bbox | Rasterizado a 20 m; vectores simplificados a 5 m | data |

Para cada capa responder: ¿qué mide y en qué unidades?, ¿hay valores ausentes?, ¿qué NO permite concluir?, ¿qué es observación y qué es transformación o inferencia nuestra?

## 4. Código, librerías y herramientas

| Recurso | Uso | Licencia |
|---|---|---|
| _por rellenar_ | | |

## 5. Uso de IA

Declarar aquí qué herramientas de IA se usan en el desarrollo y cómo (la entrega exige declararlo y marcar el contenido generado):

- Asistente de código: _por rellenar_
- LLM local del producto: _modelo y runtime por rellenar_

## 6. Capas procesadas y descartadas de la base (Jezero)

Descartadas por no cubrir todo el recuadro, aunque están procesadas y documentadas en [JEZERO_LAYERS.md](JEZERO_LAYERS.md): DTM y ortoimagen HiRISE (USGS Mars 2020 TRN y STAC, 32-37 %), mineralogía CRISM (Parente, Saranathan & Itoh 2021, Zenodo 5575824, CC-BY-4.0, 41 %) y la inercia térmica global cuantitativa de USGS (100 %, pero con bandas entre pasadas).
