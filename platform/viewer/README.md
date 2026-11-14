# Terrain engine, surface viewer and standalone layer viewer

This folder holds the pieces of the 3D experience that the web application ([`platform/web`](../web/README.md)) loads from the MARPS server: the Three.js relief engine (`terrain3d/terrain3d.mjs`) and the surface-reconstruction viewer (`surface.html`). It also contains a standalone Leaflet viewer that shows the data layers and reconstructions without the planner.

Built on the project's Leaflet map, combining the planned trajectory, classic A* comparison, stops, optional tilted terrain with elevation profile, and reconstruction access points in 2D and 3D. The viewer is served by the single MARPS server (`backend/app.py`). Generating a relief is a separate step requiring NumPy, rasterio and Pillow.

## Open the map

From the MARPS root:

```bash
python3 backend/prepare_viewer.py
python3 backend/prepare_reconstructions.py
python3 backend/app.py   # or backend/run.sh
```

Open **http://127.0.0.1:8765/viewer/**. The first command downloads Leaflet 1.9.4, Three.js 0.178.0 and Spark 0.1.10 to `platform/viewer/vendor/` and verifies their SHA-256. Valid downloads are reused; `--check` only checks the files without accessing the internet. Versions, URLs and hashes are kept in `backend/viewer_dependencies.json`. Licences: [Leaflet BSD-2-Clause](https://github.com/Leaflet/Leaflet/blob/v1.9.4/LICENSE), [Three.js MIT](https://github.com/mrdoob/three.js/blob/r178/LICENSE), [Spark MIT](https://github.com/sparkjsdev/spark/blob/main/LICENSE).

The full-screen route map is at **http://127.0.0.1:8765/viewer/terrain3d/demo.html**. It uses dark floating cards, a compact reconstruction catalogue and the same surface scenes. Both pages share the route and reconstruction controllers, and the route demo needs no CDN at runtime. Re-run `prepare_viewer.py` after library changes.

For the **3D** tilt button, prepare either real relief using [TERRAIN_3D.md](../../docs/TERRAIN_3D.md). A trek STL mesh is supported through `--stl`; the official DTM can be used directly with `--dtm`, and the existing orthoimage with `--ortho`. Complete local reliefs are discovered automatically when a map is loaded, DTM first. If none are present, the tilt button is disabled while the route and surface models remain usable in 2D.

The reconstruction data lives in `data/jezero/reconstructions` and is prepared with `python3 backend/prepare_reconstructions.py`. By default the server only listens on `127.0.0.1`. It serves the interface, the CTX tiles and the local model directories without copying the binaries. The models and the downloaded libraries are excluded from Git. If the data is missing, the map is still available.

## Usage

- Click a **3D** point on the map and then **Enter the reconstruction**, or use **Enter Cheyava Falls** directly.
- The initial framing follows the example trajectory; loading reconstruction points does not move it. **Frame route** frames the planned route, while **Show 3D points** frames all verified-location access points.
- The map's **3D / 2D** control tilts the loaded relief and returns to top-down. The orange route, dashed blue A*, stops and elevation profile are retained. Reconstruction buttons follow the active relief and camera; select one to enter the same surface viewer.
- Search for a place, author or sol and filter by local files, scenes, details or models without a location. **Show on map** centres the active map on that point; in 3D it focuses the tilted camera. The route is preserved.
- In local scenes, drag to look around and use **W A S D / arrow keys** or the movement buttons to walk. Eye height: 1.65 m above a surface estimated from the geometry.
- **Orbit view** lets you inspect the model; **On foot** and **Reset view** restore the initial camera. **Esc** or **Back to map** close the scene.
- Automatic quality keeps the full Gaussians with a GPU and uses a 5 % sample with software rendering. **Full detail** forces the original model; **Light quality** reduces detail for slow machines. The NASA mesh keeps its original geometry.
- The Perseverance traverse is an optional context layer.
- Closing a reconstruction returns to the same route, camera and exaggeration. The terrain loop and its animation clock are paused while the surface modal is open. The local viewer URL works from the nested route page as well as from `/`.

The trajectory comes from the saved real planner response `terrain3d/demo_route.json`. It is explicitly labelled as an example. A caller can replace it through `initRouteView(...).setRoute(planRouteResponse)` or by dispatching `marps:plan-route` on `.mapwrap` / `#wrap`; this standalone viewer does not request missions itself; mission planning is in the web application. See [RECONSTRUCTIONS.md](../../docs/RECONSTRUCTIONS.md) for the full current integration and limits.

## Included data and limitations

The delivered package contains **242 curated models**. All of them are kept in the catalogue, with author, licence and source link. **92** have an anchor; **150** are only shown in the catalogue to avoid inventing their position. Two local files are added: **Cheyava Falls** (SPZ, 16.3 MB, 972,047 Gaussians) and **Navcam sol 180 / Citadelle** (OBJ and texture, about 54 MB). Result: **244 entries and 94 access points on the map**.

External models open inside the application using the Sketchfab viewer, with first-person navigation for scenes and orbital navigation for details and aerial views. They require internet access and the author keeping viewing enabled. The **Original source** link gives access to the model if the service blocks the iframe. These models are not downloaded or redistributed.

The image sets from sites 87/91 are material for training future reconstructions: they are not presented as finished models. Nor are the 87,284 fragments of the PDS inventory presented as standalone landscapes, or the Landform links as downloaded files.

The reconstructions are partial, with gaps and less sharp areas. There is no continuous Street View of the crater. Local movement is limited to cells with observed geometry, to a bounded area and to small height changes. The ground is estimated on a 0.5 m grid: **it is not a physics simulation, a collision system or a product for measuring terrain**. Rover positions are search references, not exact footprints of the outcrops.

Cheyava keeps the Martian origin published by Planetary Scene Studio. The redistribution licence of the SPZ is not confirmed in the package: the local file is used but not published. Check the package's licence notes before distributing the data.

## Coordinate frames

- Map: Martian equirectangular, sphere of radius **3,396,190 m**, longitude positive to the east. Conversion `x = R · lon · π/180`, `y = R · lat · π/180`, compatible with the existing layers. Web Mercator and terrestrial EPSG:4326 are not used for measuring.
- Cheyava: origin `site_origin_map` from the manifest, **77.30519089° E, 18.49748444° N**. The SPZ is already in a local Z-up frame: it is only rotated −90° about X for Three.js. `train_to_site_shift_m` is not applied again, and the rasters missing from the manifest are not invented.
- NASA mesh: **SITE_FRAME, site 6**, X north/Y east/Z down, transformed to Three.js as `(y, −z, −x)` and re-centred for the viewer. Its anchor is the PLACES best_interp position for **site 6, drive 2684**, **77.444311622° E, 18.430825802° N**, not a global georeferencing of each vertex.

## Existing thematic layers

If `platform/viewer/data/config.json` exists, the pipeline layers are used: switching with ←/→, swipe comparison, vectors and inspector. If it does not exist, the background is built directly from `assets/zones/public/layers/ctx/meta.json` and its 110 tile images, already included in the repository.

To generate the thematic layers, first retrieve the data listed in `data/jezero/README.md` and run:

```bash
pip install -r data/jezero/pipeline/requirements.txt
cd data/jezero/pipeline
python3 unpack_stack.py
python3 make_viewer_data.py
```

Then start `python3 backend/app.py` from the root. A plain static file server does not serve the 3D package paths or the viewer API.

## Verification

```bash
python3 -m unittest discover -s backend -p 'test_*.py' -v
python3 backend/prepare_viewer.py --check
node --check platform/viewer/reconstructions.mjs
node --check platform/viewer/surface.mjs
node --check platform/viewer/route-view.mjs
node --check platform/viewer/terrain3d/terrain3d.mjs
```

The tests cover keeping models without a location, details versus landscapes, the SPZ origin, preference for corrected PLACES, missing data, file-mount boundaries and the correspondence between the CTX background and its projection.

With the server running and Playwright installed, `node platform/viewer/test_viewer.cjs` checks the map, filters, opening/closing, local models, movement and mobile layout. `MARPS_PLAYWRIGHT` lets you point to an external Playwright installation; `MARPS_SCREENSHOTS` lets you save screenshots. The test intercepts the external iframe so it does not depend on Sketchfab; it does not check that service's availability.

`node platform/viewer/test_route_reconstructions.cjs` additionally checks the main map and the styled route view against a real generated relief: clickable 3D POIs, nested local scene URL, trajectory and camera retention, exaggeration, available source switching, return to 2D, missing relief, unavailable WebGL and mobile layout. It uses a lightweight scene-modal placeholder; `test_viewer.cjs` independently checks the real surface renderers. `MARPS_VIEWER_URL` overrides the default server URL for either test.
