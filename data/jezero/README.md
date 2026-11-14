# Jezero: capas del mapa

Zona: 77.1604655-77.6991776 °E, 18.2110274-18.7211945 °N (misma que `backend/`). Rejilla común: equirectangular (`+proj=eqc +R=3396190`), 20 m/píxel, 1596 × 1512.

**Los datos no están en GitHub** (pesan demasiado). Están en la carpeta de Google Drive del equipo: **[Mapas Jezero (Drive)](PENDIENTE: enlace de la carpeta)**.

Descargad y colocad así:
- `data/jezero/stack/`: `jezero_stack_20m.tif` (**13 bandas** float32, NaN = sin dato) y `layers.json` (unidad y descripción de cada banda). Todas cubren el 100 % del recuadro salvo `thermal_inertia` (96,1 %, sin dato en 1,2 km del borde oeste: tratadlo como desconocido, no como 0).
- `data/jezero/vectors/`: GeoJSON en metros de esa proyección (geología SIM 3464).
- `data/jezero/extra/`: `geo_unit.tif` (unidades geológicas, 95,8 %) y `crism_class.tif` (mineralogía CRISM, 41 %), fuera del stack.
- `pipeline/`: código que genera todo y sus pruebas (sí está en GitHub).

Detalle de cada capa, fuentes, avisos y capas descartadas: [../../docs/CAPAS_JEZERO.md](../../docs/CAPAS_JEZERO.md).

Leer una banda por nombre:
```python
import rasterio
with rasterio.open("data/jezero/stack/jezero_stack_20m.tif") as s:
    slope = s.read(s.descriptions.index("slope_ctx") + 1)
```
