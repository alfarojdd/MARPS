# Jezero: map layers

Area: 77.1604655-77.6991776 °E, 18.2110274-18.7211945 °N (same as `backend/`). Common grid: equirectangular (`+proj=eqc +R=3396190`), 20 m/pixel, 1596 × 1512.

**The data is not on GitHub** (it is too large). It is in the team's Google Drive folder: **[Jezero maps (Drive)](PENDIENTE: enlace de la carpeta)**.

Download it and place it as follows:
- `data/jezero/stack/`: `jezero_stack_20m.tif` (**13 bands** float32, NaN = no data) and `layers.json` (unit and description of each band). All bands cover 100 % of the bounding box except `thermal_inertia` (96.1 %, no data along 1.2 km of the western edge: treat it as unknown, not as 0).
- `data/jezero/vectors/`: GeoJSON in metres in that projection (SIM 3464 geology).
- `data/jezero/extra/`: `geo_unit.tif` (geologic units, 95.8 %) and `crism_class.tif` (CRISM mineralogy, 41 %), outside the stack.
- `pipeline/`: code that generates everything, plus its tests (this is on GitHub).

Details of each layer, sources, caveats and discarded layers: [../../docs/JEZERO_LAYERS.md](../../docs/JEZERO_LAYERS.md).

Read a band by name:
```python
import rasterio
with rasterio.open("data/jezero/stack/jezero_stack_20m.tif") as s:
    slope = s.read(s.descriptions.index("slope_ctx") + 1)
```
