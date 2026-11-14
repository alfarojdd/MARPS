# MARPS — Reconstrucciones de superficie de Jezero y datos para crear otras

**Consulta: 14 de noviembre de 2026.** Bbox interpretada como `[oeste, sur, este, norte]`: `77.1604655, 18.2110274, 77.6991776, 18.7211945`, en longitud este y latitud planetocéntrica de Marte. Tamaño aproximado: **30,29 × 30,24 km**.

Hay material suficiente para añadir escenas de superficie reales al mapa. La entrega contiene **242 modelos curados o de comunidad enumerados**, un inventario de **87.284 productos de malla PDS de una versión concreta**, **17 tilesets de ejemplo de NASA**, **8.647 registros de imágenes con sus enlaces originales y modelos de cámara**, **14 PNG originales de ejemplo**, una **malla NASA texturizada completa de ejemplo** y un **Gaussian Splatting descargado de Cheyava Falls**.

**Alcance:** es un inventario amplio y reproducible de las fuentes localizadas, no una certificación de que no exista ningún otro modelo. Los fragmentos PDS no equivalen a lugares distintos ni a cobertura continua. Los 8.647 registros corresponden a cinco conjuntos seleccionados, no al archivo completo de imágenes de Perseverance. La diferencia espacial exacta entre “con reconstrucción” y “sin reconstrucción” requiere calcular las huellas/visibilidad de cada malla; no se ha calculado en esta entrega. “Sin modelo curado localizado” no significa “sin imágenes” ni demuestra “sin producto PDS”.

## 1. Qué abrir primero

1. **`catalogo_modelos.html`**: catálogo legible con los 242 modelos, enlaces individuales, tipo, sol y disponibilidad de descarga.
2. **`cheyava_falls/splat.spz`**: Gaussian Splatting ya entrenado; abrir en un visor compatible con SPZ v3, por ejemplo uno basado en Spark. No es un PLY de puntos convencionales.
3. **`ejemplo_malla_NASA/… .obj`**: abrir el OBJ manteniendo en la misma carpeta el MTL y el PNG. La etiqueta `.obj.xml` conserva la referencia espacial.
4. **`catalogos/imagenes_site87_1800_1813.csv`** y **`imagenes_site91_1950_1956.csv`**: conjuntos candidatos para reconstruir nuevas escenas.
5. **`geografia/ruta_y_bbox.png`**: relación entre la bbox y los puntos realmente observados por el rover.

## 2. Reconstrucciones existentes

### A. Gaussian Splatting de Cheyava Falls — la opción más directa para una primera demostración

El proyecto de sus autores **Planetary Scene Studio** publica una reconstrucción de Cheyava Falls a partir de imágenes de Perseverance. El archivo descargado tiene **972.047 gaussianas**, SH de grado 0 y **16.267.642 bytes**. Se ha comprobado el encabezado binario SPZ v3 y el número de gaussianas; no se ha evaluado aquí su calidad renderizada.

- [Repositorio y documentación de los autores](https://github.com/Matusvec/spaceX-Mhacks-Challenge)
- [Archivo SPZ público](https://planetary-scene-studio.vercel.app/scenes/mars-hero-01/splat.spz)
- [Manifest de la escena](https://planetary-scene-studio.vercel.app/scenes/mars-hero-01/scene.json)
- [Descripción de la reconstrucción y sus limitaciones](https://github.com/Matusvec/spaceX-Mhacks-Challenge/blob/main/docs/splat-pipeline.md)

El origen publicado corresponde a **77,30519089° E, 18,49748444° N**, dentro de la bbox. Conservar el CRS y las transformaciones del manifest; no tomar el origen como la posición exacta de la roca. El recorte declarado tiene radio 9 m.

Sus autores indican que usan 241 fotos de tres paradas y advierten de huecos, sombras y pérdida de nitidez a menos de unos 2 m. No se ha localizado una licencia explícita de redistribución; confirmarla antes de publicar el modelo integrado.

### B. Catálogo Mastcam-Z / Christian Tate

[Perfil Mastcam-Z](https://sketchfab.com/Mastcam-Z). La búsqueda paginada de su API pública devolvió **224 entradas**, 207 con descarga habilitada. Se seleccionaron **206 modelos relacionados con Jezero**, **190 con descarga habilitada**, después de excluir conservadoramente 18 entradas: modelos terrestres/análogos, de Rosetta, elementos auxiliares y cinco escenas sin ubicación comprobable. El perfil indexado muestra **231 modelos**; la diferencia de siete no se pudo resolver. Por tanto, no se presenta la selección como la totalidad garantizada de la cuenta.

El catálogo abarca escenas, afloramientos, workspaces, rocas, abrasiones y algunos productos aéreos. El último sol identificado en los títulos del conjunto enumerado es **1629**; la fecha de publicación no es la fecha de adquisición. La licencia está registrada por modelo: hay CC BY y también modelos CC BY-NC-SA, además de otros con descarga deshabilitada. Una descarga de Sketchfab puede requerir iniciar sesión.

Ejemplos útiles para colocar puntos de entrada al mapa:

| Lugar/modelo | Sol | Enlace |
|---|---:|---|
| Citadelle y entorno de Rochette | 180 | [Modelo](https://sketchfab.com/3d-models/2fd3f1b2b03d4ae5b3e198ba0dbb196b) |
| Artuby | 175 | [Modelo](https://sketchfab.com/3d-models/29669d3f2b464267a7b8ac4deea82549) |
| Enchanted Lake | 422 | [Modelo](https://sketchfab.com/3d-models/36a2fe3d0758439381b7c4d94e8911a5) |
| Wildcat Ridge, cambios entre observaciones | 502–518 | [Modelo](https://sketchfab.com/3d-models/7cbc03c7bfb344f8ae6cc7a11ba52a1e) |
| Amalik y Enchanted Lake | 569 | [Modelo](https://sketchfab.com/3d-models/11bbd249b30a493086ca3950ee6077f9) |
| Kodiak, versión de largo alcance | 580 | [Modelo](https://sketchfab.com/3d-models/cb8a890bdf4d4f36aa6bc28f1293be96) |
| Bright Angel workspace | 1178 | [Modelo](https://sketchfab.com/3d-models/6bcf9c4fbc284a35bd7924b1bb6f9f36) |
| Pico Turquino South | 1326 | [Modelo](https://sketchfab.com/3d-models/84c8c98dbefc4e87afb22175dca6d9d0) |

Los 206 registros seleccionados, junto a los adicionales, están en `catalogos/modelos_curados.csv`. Los modelos de abrasiones son detalles de centímetros: no deben mostrarse como si fueran paisajes transitables.

### C. DOM científicos de Kodiak y del frente del delta

Se han añadido los dos modelos de Jezero localizados en **LPG-3D** y los ocho modelos de **alelbo / Alexander Borchert**. Estos perfiles publican modelos de Kodiak, Rockytop, Franklin Cliff, Scarp A, C y D, Whale Mountain y del aterrizaje LCAM. Sus API indican **visualización habilitada pero descarga deshabilitada** para estos diez registros.

| Modelo | Enlace |
|---|---|
| Kodiak, LPG-3D | [Ver](https://sketchfab.com/3d-models/eeb0be59069248268642ee827bddb39e) |
| Rockytop top, LPG-3D | [Ver](https://sketchfab.com/3d-models/88db65276ce24c9b8272dce9c5bb6235) |
| Franklin Cliff | [Ver](https://sketchfab.com/3d-models/c52cc193839f445eb76b27e9e79d15b3) |
| Scarp A | [Ver](https://sketchfab.com/3d-models/71bdbece18c943608d5aa34310e95418) |
| Scarp C | [Ver](https://sketchfab.com/3d-models/c975a756864d4177bb9ec74253888877) |
| Scarp D | [Ver](https://sketchfab.com/3d-models/706125b72da74804a41fbe2844947f05) |
| Whale Mountain | [Ver](https://sketchfab.com/3d-models/f7c66db1bc314052a9542d03d9960cae) |

[Caravaca et al. 2024](https://doi.org/10.1029/2023JE008205) documentan los DOM de Kodiak obtenidos con RMI y Mastcam-Z, y enlazan sus visualizaciones. [El depósito de Borchert](https://doi.org/10.17169/refubium-45082) anuncia modelos asociados a su trabajo sobre el delta. El servidor del depósito bloqueó el acceso automatizado en esta consulta: no se ha podido verificar la descarga de sus ficheros 3D. No confundir “se puede ver” con “se puede descargar e integrar”.

### D. NASA PDS: mallas estéreo operacionales

Hay tres familias oficiales particularmente útiles para MARPS:

| Bundle | Productos OBJ enumerados en el snapshot consultado | Sol mínimo–máximo de los productos |
|---|---:|---:|
| `mars2020_navcam_ops_mesh` | 29.715 | 2–1497 |
| `mars2020_hazcam_ops_mesh` | 4.753 | 0–1497 |
| `mars2020_mastcamz_ops_mesh` | 52.816 | 2–1499 |
| **Total** | **87.284** | |

Son mallas parciales por observación, no 87.284 paisajes independientes. Para reutilizarlas hacen falta el OBJ, su MTL, la textura y la etiqueta XML. No asumir que todos los OBJ tienen el mismo marco local.

- [Registro oficial del bundle Navcam](https://pds.nasa.gov/ds-view/pds/viewCollection.jsp?identifier=urn:nasa:pds:mars2020_navcam_ops_mesh:data)
- [Explorador oficial de cámaras Mars 2020](https://pds-imaging.jpl.nasa.gov/beta/archive-explorer?mission=mars_2020)
- [Archivo Navcam actual](https://pdsimage2.wr.usgs.gov/archive/mars2020/mars2020_navcam_ops_mesh/)
- [Archivo Hazcam actual](https://pdsimage2.wr.usgs.gov/archive/mars2020/mars2020_hazcam_ops_mesh/)
- [Archivo Mastcam-Z actual](https://pdsimage2.wr.usgs.gov/archive/mars2020/mars2020_mastcamz_ops_mesh/)

**Límite temporal importante:** los tres inventarios recuperados del registro son de la **release 13 / snapshot `20250922`**. La página oficial de la misión anuncia ya la **release 16**, con datos científicos hasta el sol 1859; el servidor actual de Imaging devolvió HTTP 403 en esta sesión. El mirror antiguo de JPL sólo permitió verificar partes más tempranas. Por ello, el inventario adjunto es verificable pero **no está completo hasta noviembre de 2026**, y no permite afirmar que falten mallas en sols 1500–1859.

Las filas tienen identificador PDS, sol, RMC, localización cuando se pudo emparejar y directorios de descarga. En **74.536** productos se pudo asociar una posición de rover dentro de la bbox; **12.748 Navcam** quedaron sin correspondencia exacta y están marcados como pendientes. Tampoco se han calculado ni recortado las huellas de sus geometrías. Los nombres físicos de los ficheros incluyen un sufijo de versión que no aparece igual en el LID: los enlaces del inventario apuntan al directorio para resolverlo sin inventar nombres de archivo.

Se incluye una descarga comprobada de Navcam del sol 180: OBJ de **51.954.517 bytes**, MTL, textura y XML, en `ejemplo_malla_NASA`. La etiqueta indica **SITE_FRAME, site 6**; no son coordenadas globales de Marte. Su RMC es site 6, drive 2684.

### E. NASA Landform: 3D Tiles ya preparados para visualización web

[Ejemplo oficial interactivo](https://nasa-ammos.github.io/3DTilesRendererJS/three/landformSiteOverlay.html). Se han enumerado **17 tilesets** del ejemplo **site 26, drive 1004**, generado con imágenes de los sols 477–499. Los enlaces directos están en `catalogos/landform_3dtiles.csv`.

[Datos y procedencia](https://github.com/NASA-AMMOS/3DTilesSampleData/tree/master/m20-drive-1004). Los `scene.json` describen marcos y transformaciones. Ésta es una vía muy útil si el mapa admite 3D Tiles. El [repositorio Landform](https://github.com/NASA-AMMOS/Landform) avisa de que la mayoría de sus productos operacionales aún no son públicos. **El otro ejemplo llamado Dingo Gap es de Curiosity/Gale y se ha excluido de Jezero.**

### F. PRoViP / PRo3D: nubes ordenadas de Mastcam-Z

[Paar et al. 2023, apartado Data Availability Statement](https://doi.org/10.1029/2022EA002532) publican un acceso SFTP a **Ordered Point Clouds (OPC)** calculadas con datos Mastcam-Z liberados en PDS. Es otra fuente de geometría existente; no requiere empezar desde fotografías. El artículo contiene las credenciales públicas de acceso.

No se ha enumerado el servidor SFTP ni comprobado su disponibilidad actual. Los OPC se trabajan con PRo3D; no deben tratarse como un PLY convencional ni como Gaussian Splatting. El acceso publicado es una ruta adicional, no un número de escenas auditado en esta entrega.

### G. Modelos de la comunidad

El catálogo incorpora **26 modelos adicionales** seleccionados de autores como Owl Creek Technologies, GeoLan3D, Simeon Schmauß, Spaceport3D y otros. Incluye terreno del sol 116, rocas de los sols 87/91/168, Rochette, Hogwallow–Rockytop, Neretva Vallis y reconstrucciones del descenso. Se descartaron resultados terrestres llamados “Jezero”, modelos CAD del rover aislado y otros sitios de Marte.

Comprobar la descripción: algunos añaden materiales PBR, animaciones o retoques artísticos; algunos proceden del descenso y aportan vista aérea. Son útiles como referencia o visualización, pero no todos son una geometría científica verificable a escala humana. La escala y la colocación deben validarse antes de integrarlos.

## 3. Imágenes para reconstrucciones propias

Se han consultado y paginado los registros originales del feed público de NASA, comprobando que respetaran los filtros de sol. Los ficheros `metadatos/*.json` guardan los registros completos. Los CSV incluyen **enlaces al PNG de resolución completa**, cámara, filtro, dimensiones, sol, site/drive y ubicación de rover cuando se pudo asociar.

| Conjunto | Registros originales | Mastcam-Z RGB candidatos¹ | Posiciones distintas con RGB | Uso propuesto |
|---|---:|---:|---:|---|
| **Site 87, sols 1800–1802 y 1805–1813** | 1.608 | **262** | **3** | Primera escena nueva candidata, con paradas próximas |
| **Site 91, sols 1950–1952 y 1955–1956** | 1.352 | **352** | **2** | Segunda escena nueva candidata, posterior a la release científica 16 |
| Site 91, sols 2000–2002 | 27 | 2 | 1 | Poco material RGB: baja prioridad |
| Citadelle, sols 180–198 | 2.376 | 133 | 2 | Rehacer con 3DGS y comparar con una malla existente |
| Delta, sols 566–586 | 3.284 | 782 | 1 | Estéreo local; no asumir cobertura de vuelo libre |

¹ Productos EBY de los filtros amplios `ZCAM_L0_RGB` / `ZCAM_R0_RGB`, con al menos 600 píxeles en cada dimensión. Son vistas **candidatas**, no una selección validada de solape o nitidez. Los mosaicos y las repeticiones pueden producir muchos registros desde una misma posición. El CSV conserva también Navcam como contexto y para geometría. Se ha marcado una selección inicial de RGB/Navcam, sin afirmar que cada foto sea apta para entrenar.

Para los dos conjuntos nuevos no se encontró un modelo curado en los catálogos enumerados. En el site 87 podrían existir mallas operacionales más recientes que el snapshot descargado. En el site 91 las imágenes son posteriores al sol 1859, pero tampoco se puede descartar que un tercero haya publicado una reconstrucción no localizada.

**Ubicaciones de referencia:**

| Conjunto / parada | Longitud E | Latitud planetocéntrica N |
|---|---:|---:|
| Site 87, drive 0 | 77.22666035 | 18.42772479 |
| Site 87, drive 120 | 77.226774506 | 18.427682327 |
| Site 87, drive 268 | 77.22685514 | 18.427622369 |
| Site 91, drive 0 | 77.23290872 | 18.43546757 |
| Site 91, drive 124 | 77.23287100 | 18.43559862 |

Las distintas paradas no garantizan por sí solas que se observe el mismo objeto. Hay que comprobar dirección, campo de visión y solape. Las 14 imágenes descargadas de muestra permiten inspeccionar el aspecto del terreno; **no sustituyen a los conjuntos completos** de los CSV.

### Descargar las imágenes completas con sus registros de cámara

Se necesita Python 3.10 o posterior; sólo usa la biblioteca estándar. Ejecutar desde la carpeta extraída:

```bash
# Ver la selección, sin descargar.
python3 scripts/descargar_imagenes.py --scene site87_1800_1813 --rgb-only

# Descargar las 262 imágenes RGB candidatas del site 87 y su metadata.
python3 scripts/descargar_imagenes.py --scene site87_1800_1813 --rgb-only --download --out datos

# Descargar las 352 imágenes RGB candidatas del site 91 y su metadata.
python3 scripts/descargar_imagenes.py --scene site91_1950_1956 --rgb-only --download --out datos

# Incluir también los Navcam de la selección inicial.
python3 scripts/descargar_imagenes.py --scene site91_1950_1956 --training-candidates --download --out datos
```

Los conjuntos completos pueden ocupar varios GB. El script admite `--limit`, registra errores y hashes, comprueba que lo descargado sea PNG y permite reanudar. Se ha comprobado una descarga real usando el script. También puedes abrir directamente los enlaces `full_res_url` del CSV.

**Fidelidad:** esos PNG son productos browse del feed público, útiles para empezar, y no equivalen a radiancias calibradas PDS. Para un resultado consistente, usar las imágenes calibradas originales de [Mastcam-Z](https://mastcamz.asu.edu/mastcam-z-data-for-all/) cuando estén disponibles. El PDS ofrece IMG/XML y productos estéreo; conservar la metadata al convertir a TIFF/PNG.

## 4. Datos geométricos que necesitas para NeRF o 3DGS

La latitud/longitud del rover no basta para obtener la pose de cada cámara. Hay que conservar:

- `camera_model_type` y `camera_model_component_list`: C, A, H, V y, según la cámara, O, R, E.
- Marco de referencia, site/drive y actitud del rover; transformación entre paradas con [PLACES](https://pds-geosciences.wustl.edu/missions/mars2020/places.htm).
- Zoom/filtro por imagen, dimensiones y subframe. Los intrínsecos de Mastcam-Z cambian al cambiar el zoom.
- Distorsión de Navcam/Hazcam. No reducir CAHVORE a un pinhole sin rectificar las imágenes.
- Geometría estéreo XYZ/rango, cuando exista, para escala e inicialización de la nube.

El paquete conserva `best_interp.csv`, `telemetry.csv` y la etiqueta de `best_interp`. Se prioriza best_interp, después los waypoints y, sólo para RMC restantes, telemetry; la columna `position_source` lo distingue. Telemetry no tiene la misma corrección absoluta que best_interp. La posición del rover es un anclaje, no una garantía de exactitud absoluta de la escena.

El flujo que propongo para MARPS es: elegir una región con solape real entre paradas → rectificar cada cámara → llevar las poses a un marco métrico común → inicializar con estéreo/SfM → refinar poses y entrenar el splat → comprobar vistas nuevas → situarlo sobre el DTM orbital. Mantener la malla/XYZ para colisiones y mediciones y el splat como representación visual. El resultado no reconstruirá zonas ocultas que las fotos no hayan observado.

## 5. Bases orbitales, panoramas y otros trabajos encontrados

- **Base para unir los puntos:** [DTM USGS HiRISE a 1 m](https://planetarymaps.usgs.gov/mosaic/mars2020_trn/HiRISE/JEZ_hirise_soc_006_DTM_MOLAtopography_DeltaGeoid_1m_Eqc_latTs0_lon0_blend40.tif), [ortomosaico](https://planetarymaps.usgs.gov/mosaic/mars2020_trn/HiRISE/JEZ_hirise_soc_007_orthoMosaic_25cm_Ortho_blend120.tif) y [extensión MSR hacia el oeste](https://www.usgs.gov/data/mars-sample-return-hirise-mosaics-terrain-relative-navigation). Son productos orbitales: no resuelven por sí solos el detalle a la altura de un astronauta. Verificar las huellas antes de asumir que cubren toda la bbox.
- **Panoramas reales y sintéticos:** [mapa de FU Berlin](https://maps.planet.fu-berlin.de/jezero/) y [explicación del equipo Mastcam-Z](https://mastcamz.asu.edu/take-a-virtual-hike-in-jezero-with-mastcam-z/). Permiten mirar alrededor desde un punto; no equivalen a poder caminar libremente por una reconstrucción. El mapa distingue los panoramas sintéticos orbitales de los observados por Mastcam-Z.
- **InstantSplat:** [repositorio oficial](https://github.com/NVlabs/InstantSplat) y [datos enlazados por los autores](https://huggingface.co/datasets/kairunwen/InstantSplat). Es una referencia metodológica; no se pudo identificar y geolocalizar una escena pública de Perseverance dentro de la bbox lista para usar. No se cuenta como otra reconstrucción de Jezero confirmada.
- **Mars_3D / ESGS:** [artículo](https://doi.org/10.3390/rs18142357) y [repositorio de sus autores](https://github.com/LG973641114/ESGS). El artículo anuncia un dataset, pero el repositorio consultado no tiene un enlace de descarga operativo: remite a pedir los datos por correo. Tampoco demuestra qué escenas corresponden a esta bbox. No se incluye como dataset de Jezero confirmado.
- **3DGS orbital de Jezero:** [EGU25-2216](https://meetingorganizer.copernicus.org/EGU25/EGU25-2216.html) usa HiRISE y vistas renderizadas. No es una reconstrucción desde las cámaras de superficie y no se encontró allí un modelo público para descargar.

## 6. Integración y cobertura honesta en MARPS

Usaría una base orbital continua donde haya datos y puntos de acceso a escenas reales de superficie: primero Cheyava Falls, Citadelle y Kodiak; después los sites 87/91 si las pruebas de solape y poses funcionan. Cada punto debe indicar fuente, sol, licencia, resolución aproximada, marco espacial y límites de observación. Mostrar los huecos y restringir el movimiento a zonas bien observadas evitará dar al usuario una falsa sensación de detalle medido.

**GIS de Marte:** los `.geojson` de este paquete contienen coordenadas marcianas y una nota explícita de sistema de referencia. No asignarles EPSG:4326 terrestre para medir distancias ni mezclar alturas de radio planetario con alturas sobre el geoide MOLA. Las anclas de modelos basadas en el sol son posiciones de rover aproximadas para búsqueda; no son la posición precisa de un afloramiento lejano ni su huella.

## 7. Cómo se comprobó la entrega

- Paginación completa del endpoint de búsqueda para Mastcam-Z, LPG-3D filtrado por Jezero y alelbo; exclusión de 18 entradas de Mastcam-Z fuera de alcance o sin localización confirmable; búsqueda adicional de Jezero y Perseverance. La búsqueda general de Perseverance se limitó a los primeros 240 resultados y luego se revisó por relevancia. No es una enumeración exhaustiva de toda la plataforma.
- Lectura de inventarios PDS del snapshot indicado, excluyendo nueve entradas auxiliares que no eran OBJ.
- Asociación por RMC con PLACES y waypoints; las correspondencias fallidas quedan marcadas y no se inventan coordenadas.
- Paginación de las ventanas de imágenes de la tabla y comprobación del filtro de sol.
- Descarga satisfactoria de 14 imágenes originales y de OBJ/MTL/PNG/XML del ejemplo NASA; hashes en `descargas_verificadas.json`.
- Descompresión del encabezado SPZ y comprobación del número de gaussianas. No se ha entrenado ni renderizado una reconstrucción nueva.

Los 708 waypoints del archivo NASA consultado (sols 13–2022) están dentro de la bbox. Esto confirma que el rectángulo contiene el recorrido registrado, **no** que el rover haya fotografiado toda su superficie.
