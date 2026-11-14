# data/: búsqueda y preparación de mapas

**Rama de área:** `area/data`

## Qué va aquí
- **Scripts** para descargar y preprocesar las capas (reproyección, recorte, remuestreo a una rejilla común, normalización).
- Derivación de capas: pendiente y rugosidad a partir del modelo de elevación.
- `metadata.json` por zona (ver [../docs/ARQUITECTURA.md](../docs/ARQUITECTURA.md), contrato **[A]**).
- **Muestras pequeñas** para tests y demo (unos pocos MB como máximo).
- Notas sobre cada fuente en [../docs/FUENTES.md](../docs/FUENTES.md).

## Qué NO va aquí
Datos pesados (GeoTIFF, DTM, imágenes). Se descargan en `data/raw/` y `data/processed/`, que están en `.gitignore`. Lo que se sube es el **script que los genera** y la anotación de su origen, versión y licencia.

## Pendiente
- [ ] Elegir la zona (Gale/Monte Sharp o Jezero) y fijar su extensión
- [ ] Localizar al menos **3 tipos de datos** (el reto lo pide) y anotarlos en FUENTES.md
- [ ] Preparar cuanto antes una versión **sintética o de baja resolución** para que `planner/` y `platform/` puedan empezar
- [ ] Imágenes de superficie de rovers para la vista en primera persona (opcional)
