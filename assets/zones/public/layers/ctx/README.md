# CTX basemap tiles (Jezero)

Turns the CTX orthomosaic into full-resolution PNG tiles for the MARPS frontend.

## Input
`JEZ_ctx_B_soc_008_orthoMosaic_6m_Eqc_latTs0_lon0.tif`: 5322 × 5040 px, 1 band `uint8`, 6 m/px.
CRS: Equirectangular, Mars 2000 sphere (R = 3,396,190 m), lon 0, planetocentric east-positive.
Bounds: 77.160–77.699°E, 18.211–18.721°N. No nodata pixels.

## Output (`platform/web/public/layers/ctx/`)
- `tiles/rYY_cXX.png`: 110 grayscale tiles, 512 px (11 × 10), each under 0.2 MB
- `meta.json`: grid, CRS, stretch, and per-tile pixel and lon/lat bounds
- `places.json`: named sites with global pixel, tile and pixel in tile
- `overview.png`: 1024 px preview, the only resampled file (don't pick coordinates on it)

Also: `src/lib/ctxTiles.ts` (lookup + Leaflet helpers), `data/scripts/export_ctx_tiles.py`, `data/scripts/_tile_index_map.jpg` (grid with tile ids and sites).

## Process
1. Read band 1 and its mask with rasterio.
2. Global 2–98% contrast stretch (DN 93–207 → 0–255), so no seams between tiles.
3. Slice into 512 px tiles, scale 1: no resampling, flips or padding. Edge tiles are smaller (col 10: 202 px wide; row 9: 432 px tall).
4. Convert sites from lon/lat with pyproj using the file's Mars CRS (`crs.geodetic_crs`, never EPSG:4326), then `ds.index(x, y)`, which returns **(row, col)**. Sites outside the raster are dropped.

## Find a tile
```
tile    = r{floor(row/512):02d}_c{floor(col/512):02d}
local_x = col % 512,  local_y = row % 512
```
In TS: `tileFor(meta, col, row)`.

## Leaflet (`L.CRS.Simple`)
1 unit = 1 px. `lat = -row`, `lng = col`. Tile bounds `[[-(row0+height), col0], [-row0, col0+width]]`. Cell centre `(col+0.5, row+0.5)`.

```ts
const meta = await (await fetch("/layers/ctx/meta.json")).json();
const map = L.map("map", { crs: L.CRS.Simple, minZoom: -4, maxZoom: 2 });
addCtxTiles(map, meta);
map.fitBounds([[-meta.rows, 0], [0, meta.cols]]);
```

## Sites
| Place | lat, lon | col, row | Tile | In tile | Source |
|---|---|---|---|---|---|
| Octavia E. Butler Landing | 18.4447, 77.4508 | 2868, 2731 | r05_c05 | 308, 171 | ESA SPICE `MEX_RELAY_LOCATIONS_V03.TF` |
| Belva crater | 18.48, 77.38 | 2168, 2382 | r04_c04 | 120, 334 | IAU Gazetteer #15872 |
| Neretva Vallis | 18.55, 77.20 | 390, 1691 | r03_c00 | 390, 155 | IAU Gazetteer #15879 |
| Jezero (centre) | 18.41, 77.69 | 5231, 3074 | r06_c10 | 111, 2 | IAU Gazetteer #14300 |

Dropped (outside): Hartwell, Nili Planum. Neretva and Jezero are feature centre points. Sites from `docs/` still need adding to `PLACES` in the script.

## Verified
Tiles stitch back identical to the stretched TIF; each site's tile pixel matches the TIF; landing site and Belva sit where expected (no flip or shift); no tile over 3 MB.

## Regenerate
```bash
pip install rasterio pyproj numpy pillow
python data/scripts/export_ctx_tiles.py <tif> --out platform/web/public/layers/ctx  # --tile 512 --no-stretch
```
Idempotent: the output folder is rewritten.

## Agree with backend
- Basemap grid is 6 m, 5322 × 5040, scale 1; the 20 m stack is a different grid. Exchange lon/lat or projected metres, not raw pixels.
- Confirm the stack uses the same CRS.
- Longitudes are planetocentric, east-positive.
