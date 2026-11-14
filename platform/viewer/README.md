# Visor de Jezero y reconstrucciones de superficie

Reutiliza el mapa Leaflet del proyecto y añade accesos a reconstrucciones 3D. No necesita Ollama, FastAPI, Node ni instalar paquetes Python: el servidor usa Python 3.10+ y su biblioteca estándar.

## Abrir el mapa

Desde la raíz de MARPS:

```bash
python3 backend/prepare_viewer.py
python3 backend/viewer.py
```

Abrir **http://127.0.0.1:8765**. El primer comando descarga Leaflet 1.9.4, Three.js 0.178.0 y Spark 0.1.10 a `platform/viewer/vendor/` y verifica SHA-256. Se reutilizan las descargas válidas; `--check` sólo comprueba los archivos sin acceder a internet. Las versiones, URLs y hashes se conservan en `backend/viewer_dependencies.json`. Licencias: [Leaflet BSD-2-Clause](https://github.com/Leaflet/Leaflet/blob/v1.9.4/LICENSE), [Three.js MIT](https://github.com/mrdoob/three.js/blob/r178/LICENSE), [Spark MIT](https://github.com/sparkjsdev/spark/blob/main/LICENSE).

La ubicación predeterminada de los datos es `MARPS_Jezero_3D_datos/MARPS_Jezero_3D/`. Para otra ubicación:

```bash
python3 backend/viewer.py --dataset /ruta/a/MARPS_Jezero_3D --port 8765
```

El servidor escucha sólo en `127.0.0.1` por defecto. Sirve la interfaz, las teselas CTX y los dos directorios de modelos locales sin copiar los binarios. Los modelos y las bibliotecas descargadas se excluyen de Git. Si falta el paquete, el mapa sigue disponible y muestra cómo indicar la ruta.

## Uso

- Pulsar un punto **3D** del mapa y **Entrar en la reconstrucción**, o usar directamente **Entrar en Cheyava Falls**.
- Buscar un lugar, autor o sol y filtrar por archivos locales, escenas, detalles o modelos sin ubicación. **Situar en mapa** centra y abre el punto correspondiente.
- En las escenas locales, arrastrar para mirar y usar **W A S D / flechas** o los botones de desplazamiento para caminar. Altura de ojos: 1,65 m sobre una superficie estimada a partir de la geometría.
- **Vista orbital** permite inspeccionar el modelo; **A pie** y **Restablecer vista** recuperan la cámara inicial. **Esc** o **Volver al mapa** cierran la escena.
- La calidad automática conserva las gaussianas completas con GPU y usa una muestra del 5 % con renderizado por software. **Detalle completo** fuerza el modelo original; **Calidad ligera** reduce el detalle para equipos lentos. La malla NASA conserva su geometría original.
- El recorrido de Perseverance es una capa opcional de contexto.

## Datos integrados y límites

En el paquete entregado hay **242 modelos curados**. Se conservan todos en el catálogo, con autor, licencia y enlace de procedencia. **92** tienen ancla; **150** sólo se muestran en el catálogo para no inventar su posición. Se añaden dos archivos locales: **Cheyava Falls** (SPZ, 16,3 MB, 972.047 gaussianas) y **Navcam sol 180 / Citadelle** (OBJ y textura, unos 54 MB). Resultado: **244 entradas y 94 accesos en el mapa**.

Los modelos externos se abren dentro de la aplicación usando el visor de Sketchfab, con navegación de primera persona para escenas y navegación orbital para detalles y vistas aéreas. Requieren internet y que el autor mantenga habilitada la visualización. El enlace **Fuente original** permite acceder al modelo si el servicio bloquea el iframe. No se descargan ni redistribuyen esos modelos.

Los conjuntos de imágenes de sites 87/91 son material para entrenar reconstrucciones futuras: no se presentan como modelos ya terminados. Tampoco se presentan los 87.284 fragmentos del inventario PDS como paisajes independientes ni los enlaces de Landform como archivos descargados.

Las reconstrucciones son parciales, con huecos y zonas menos nítidas. No hay un Street View continuo del cráter. El movimiento local se limita a celdas con geometría observada, a un entorno acotado y a cambios pequeños de altura. El suelo se estima en una rejilla de 0,5 m: **no es una simulación física, un sistema de colisiones ni un producto para medir el terreno**. Las posiciones del rover son referencias de búsqueda, no huellas exactas de los afloramientos.

Cheyava conserva el origen marciano publicado por Planetary Scene Studio. La licencia de redistribución del SPZ no está confirmada en el paquete: se usa el archivo local aportado y no se publica. Consultar `LEEME.md` del paquete antes de distribuir los datos.

## Marcos de coordenadas

- Mapa: equirectangular marciana, esfera de radio **3.396.190 m**, longitud positiva hacia el este. Conversión `x = R · lon · π/180`, `y = R · lat · π/180`, compatible con las capas existentes. No se usa Web Mercator ni EPSG:4326 terrestre para medir.
- Cheyava: origen `site_origin_map` del manifest, **77,30519089° E, 18,49748444° N**. El SPZ ya está en marco local con Z arriba: sólo se rota −90° sobre X para Three.js. No se repite `train_to_site_shift_m` ni se inventan los rásteres ausentes del manifest.
- Malla NASA: **SITE_FRAME, site 6**, X norte/Y este/Z abajo, transformado a Three.js como `(y, −z, −x)` y recentrado para el visor. Su ancla es la posición PLACES best_interp para **site 6, drive 2684**, **77,444311622° E, 18,430825802° N**, no una georreferenciación global de cada vértice.

## Capas temáticas existentes

Si existe `platform/viewer/data/config.json`, se usan las capas del pipeline: cambio con ←/→, comparación por cortinilla, vectores e inspector. Si no existe, el fondo se construye directamente con `assets/zones/public/layers/ctx/meta.json` y sus 110 imágenes de teselas, ya incluidas en el repositorio.

Para generar las capas temáticas, recuperar primero los datos indicados en `data/jezero/README.md` y ejecutar:

```bash
pip install -r data/jezero/pipeline/requirements.txt
cd data/jezero/pipeline
python3 unpack_stack.py
python3 make_viewer_data.py
```

Después arrancar `python3 backend/viewer.py` desde la raíz. El antiguo `python3 -m http.server --directory platform/viewer` no sirve las rutas del paquete 3D ni la API del visor.

## Verificación

```bash
python3 -m unittest discover -s backend -p 'test_*.py' -v
python3 backend/prepare_viewer.py --check
node --check platform/viewer/reconstructions.mjs
node --check platform/viewer/surface.mjs
```

Las pruebas cubren conservación de modelos sin ubicación, detalles frente a paisajes, origen SPZ, preferencia de PLACES corregido, ausencia de datos, límites del montaje de archivos y correspondencia entre el fondo CTX y su proyección.

Con el servidor activo y Playwright instalado, `node platform/viewer/test_viewer.cjs` comprueba mapa, filtros, apertura/cierre, modelos locales, movimiento y diseño móvil. `MARPS_PLAYWRIGHT` permite indicar una instalación externa de Playwright; `MARPS_SCREENSHOTS` permite guardar capturas. La prueba intercepta el iframe externo para no depender de Sketchfab; no verifica la disponibilidad de ese servicio.
