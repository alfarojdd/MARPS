# Jezero: map layers

Area: 77.1604655–77.6991776 °E, 18.2110274–18.7211945 °N, on a common equirectangular grid (`+proj=eqc +R=3396190`), 20 m/pixel, 1596 × 1512 cells.

The rasters are too large for Git (the base stack alone is 85 MB) and are not versioned. Everything is **reproducible** from public NASA, ESA and USGS products with the code in `pipeline/`:

```bash
pip install -r data/jezero/pipeline/requirements.txt
cd data/jezero/pipeline
python build_layers.py base      # downloads/clips CTX, HRSC, THEMIS, CRISM and geology onto the grid
python build_layers.py stack     # merges everything into stack/jezero_stack_20m.tif + layers.json
```

The manual downloads that `build_layers.py` expects in `data/jezero/raw/` are listed in [docs/JEZERO_LAYERS.md](../../docs/JEZERO_LAYERS.md#4-reproduce).

## Layout

| Path | Contents |
|---|---|
| `stack/jezero_stack_20m.tif`, `stack/layers.json` | **Base stack**: 13 float32 bands (NaN = no data) and the unit and description of each band. All bands cover 100 % of the bounding box except `thermal_inertia` (96.1 %; no data along 1.2 km of the western edge, to be treated as unknown, not as 0). |
| `vectors/` | GeoJSON in metres in the same projection (SIM 3464 geology) |
| `extra/` | `geo_unit.tif` (geologic units, 95.8 %) and `crism_class.tif` (CRISM mineralogy, 41 %), kept outside the stack because they do not cover the whole area; the planner uses them for science targets |
| `reconstructions/` | Metadata of the surface reconstructions (catalogue, scene manifests, rover positions). The two heavy local models are downloaded and verified by `python3 backend/prepare_reconstructions.py` |
| `pipeline/` | Code that generates every layer, the viewer tiles and the 3D relief, with its tests |

Read a band by name:

```python
import rasterio
with rasterio.open("data/jezero/stack/jezero_stack_20m.tif") as s:
    slope = s.read(s.descriptions.index("slope_ctx") + 1)
```

The planner looks for the data in `data/jezero` or in the folder given by the `JEZERO_DATA` environment variable.

Details of each layer, sources, caveats and discarded layers: [docs/JEZERO_LAYERS.md](../../docs/JEZERO_LAYERS.md). Provenance and licences: [docs/DATA_SOURCES.md](../../docs/DATA_SOURCES.md).
