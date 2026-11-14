# Arquitectura y contratos entre áreas

**Estado: borrador para discutir.** Lo importante es que las tres áreas se pongan de acuerdo pronto en estos tres formatos para poder trabajar en paralelo. Quien cambie uno debe actualizar este fichero en el mismo PR.

```
 Capas (data/) ───────────────────────────────┐
                                               ▼
 Texto de misión ─► LLM (llm/) ─► [B] JSON ─► Planificador (planner/) ─► [C] Ruta ─► Interfaz (platform/)
                                               ▲
                                       [A] rejilla de capas
```

## [A] Capas de mapa: `data/` → `planner/` y `platform/`

Todas las capas de una zona comparten **la misma rejilla**: mismo sistema de coordenadas, misma resolución y mismas dimensiones. Así el planificador puede combinarlas celda a celda.

Propuesta inicial:
- Formato: GeoTIFF (una banda por capa) o arrays NumPy `.npy` con un `metadata.json` al lado.
- `metadata.json` por zona: nombre de la zona, CRS, resolución (m/píxel), esquina de origen, tamaño (filas × columnas), y por capa: nombre, unidad, valor de "sin dato" y fuente.
- Nombres de capa estándar: `elevation`, `slope`, `roughness`, `thermal_inertia`, `mineralogy_<objetivo>`, `geology`, `radiation`, `rock_abundance`.
- Valores normalizados a 0-1 en una versión aparte para el planificador (`*_norm`), manteniendo los valores físicos para mostrarlos en la interfaz.

**Estado (2026-11-14):** zona Jezero y rejilla de 20 m decididas. Las capas se publican como un único GeoTIFF multibanda en `data/jezero/stack/` con `layers.json` (ver [CAPAS_JEZERO.md](CAPAS_JEZERO.md)). Los nombres de banda son los reales (`elev_ctx`, `slope_ctx`, `tri_ctx`, `thermal_inertia`, ...) y no los estándar propuestos arriba; no hay mineralogía, radiación ni abundancia de rocas en la base. Normalización 0-1 y `metadata.json` por zona: sin hacer.

Decisiones por tomar: zona (Gale/Monte Sharp o Jezero), resolución (HiRISE es mucho más fina que CTX/MOLA) y qué capas llegan a tiempo.

## [B] Parámetros de misión: `llm/` → `planner/`

**Estado (2026-11-14): acordado e implementado** en `planner/api.py` (`POST /plan-route`). La entrada son dos bloques: `mission`, que rellena el LLM (los 5 campos actuales de `backend/llm/api.py` más `safety`, `science_targets`, `science_detour` y `return_to_origin`), y `system` (hora solar local y batería, que pone el vehículo). Contrato exacto en [INTEGRACION_PLANIFICADOR.md](INTEGRACION_PLANIFICADOR.md). La propuesta inicial de abajo queda como histórico.

El LLM convierte el texto de misión en este JSON. **Se valida contra un esquema**; si falla, se reintenta o se usan pesos por defecto. El planificador nunca recibe texto libre.

```json
{
  "travel_mode": "on_foot",
  "payload_kg": 15,
  "max_duration_min": 240,
  "hard_constraints": {
    "max_slope_deg": 15,
    "avoid_high_roughness": true
  },
  "weights": {
    "distance": 1.0,
    "slope": 2.0,
    "roughness": 1.5,
    "radiation_exposure": 3.0,
    "science_interest": 2.5
  },
  "science_targets": ["clays", "phyllosilicates"],
  "waypoints": []
}
```

- `travel_mode`: `on_foot` o `rover`.
- `hard_constraints`: celdas que quedan **prohibidas** (el planificador las trata como intransitables).
- `weights`: pesos relativos, mayores o iguales a 0. El planificador los normaliza.
- `science_targets`: qué buscar; el planificador lo cruza con la capa de mineralogía o geología.
- El modelo **solo traduce**; los límites de seguridad por defecto (por ejemplo, pendiente máxima absoluta) los impone el planificador aunque el LLM no los mencione.

Idea de coste por celda: `coste = Σ peso_i · capa_i  −  peso_interés · afinidad(celda, objetivos)`, manteniéndolo siempre positivo para que A* siga siendo válido.

## [C] Ruta: `planner/` → `platform/`

**Estado (2026-11-14): implementado.** La respuesta de `POST /plan-route` tiene tres partes: `report` (métricas, comparación con un A* clásico, avisos de luz y batería, parada de carga y `why`, para el resumen del LLM y el panel), `geojson` (ruta, A* clásico y paradas en lon/lat planetocéntricas) y `ctx_px` (las líneas en píxeles del mapa base CTX de 6 m para Leaflet `CRS.Simple`). Detalle en [INTEGRACION_PLANIFICADOR.md](INTEGRACION_PLANIFICADOR.md). La propuesta inicial de abajo queda como histórico.

```json
{
  "path": [[x0, y0], [x1, y1]],
  "waypoints_visited": [],
  "metrics": {
    "distance_m": 0,
    "elevation_gain_m": 0,
    "max_slope_deg": 0,
    "est_duration_min": 0,
    "radiation_exposure": 0,
    "science_points_passed": []
  },
  "explanation": "texto corto de por qué se eligió esta ruta",
  "feasible": true
}
```

- `path`: lista de coordenadas en la rejilla [A] (o lon/lat; decidirlo y fijarlo aquí).
- `feasible: false` con un motivo cuando las restricciones duras no permiten llegar.

## Stack tentativo

| Pieza | Propuesta | Estado |
|---|---|---|
| Planificador | Python + NumPy + Numba; A* sobre la rejilla de 20 m, sombras con `mars_shadows.py` | hecho (`planner/`) |
| API | FastAPI | por confirmar |
| LLM local | Ollama o llama.cpp con salida JSON y validación (Pydantic / JSON Schema) | por confirmar |
| Interfaz | Mapa web (Leaflet, OpenLayers o deck.gl) | por confirmar |

Cada área anota aquí qué ha elegido y por qué.

## [D] Reconstrucciones de superficie → visor

Implementación local en `backend/viewer.py` y `backend/reconstructions.py`, con biblioteca estándar Python. No depende de la API del LLM. Arranque y preparación: [visor](../platform/viewer/README.md).

- `GET /api/map-config`: configuración del pipeline si existe; en su ausencia, fondo CTX con las teselas versionadas.
- `GET /api/reconstructions`: `{version:1, body:"Mars", radius:3396190, counts, warnings, scenes}`. Cada escena incluye `id`, `title`, `author`, `kind` (`landscape`, `detail`, `aerial`), `renderer` (`spz`, `obj`, `sketchfab`), `coordinates` (`[lon_E, lat_planetocéntrica]` o `null`), `anchor`, `sol`, `license`, `source` y `available`. Las locales añaden `asset`, `frame` y `radius`; la OBJ añade `texture`.
- `GET /api/traverse`: una línea GeoJSON con coordenadas de **Marte**, sólo para mostrar contexto.
- `/assets/ctx/…`: teselas orbitales del repositorio. `/reconstructions/files/cheyava_falls/…` y `/reconstructions/files/ejemplo_malla_NASA/…`: archivos locales del paquete configurado con `--dataset`.

El mapa proyecta las anclas con la misma equirectangular marciana que [A]. Abrir una escena conserva el estado del mapa en un diálogo; cerrarla destruye su iframe y libera el visor WebGL. Los modelos sin ubicación nunca reciben coordenadas inventadas. La cámara local usa suelo estimado y movimiento limitado, sin garantizar colisiones ni cobertura continua.
