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

Decisiones por tomar: zona (Gale/Monte Sharp o Jezero), resolución (HiRISE es mucho más fina que CTX/MOLA) y qué capas llegan a tiempo.

## [B] Parámetros de misión: `llm/` → `planner/`

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
| Planificador | Python + NumPy; A* sobre rejilla | por confirmar |
| API | FastAPI | por confirmar |
| LLM local | Ollama o llama.cpp con salida JSON y validación (Pydantic / JSON Schema) | por confirmar |
| Interfaz | Mapa web (Leaflet, OpenLayers o deck.gl) | por confirmar |

Cada área anota aquí qué ha elegido y por qué.
