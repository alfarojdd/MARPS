# planner: planificador de rutas consciente de la misión

Código en `planner/`:
- `planner.py`: modelo de coste, A*, ciencia y métricas.
- `report.py`: **informe JSON** para el resumen del LLM del casco (comparación con el A* clásico, batería, luz y parada de carga).
- `live.py`: banco de pruebas interactivo.
- `demo.py` y `scenarios.json`: figura y tabla de escenarios.
- `test_planner.py`: pruebas (10).

Es un spike: solo está probado lo básico y no ha pasado por el flujo de subagentes y revisión. Si se lleva al producto (`planner/` de MARPS), habrá que repasarlo con ese flujo.

```bash
python planner/live.py      # http://127.0.0.1:8766 
cd planner
python demo.py             # → out/demo.png + out/demo.md
python -m pytest -q
```
Dependencias: `pip install -r planner/requirements.txt`. **Datos**: los de `data/jezero/` (Drive, ver `data/jezero/README.md`): `stack/jezero_stack_20m.tif`, `extra/geo_unit.tif` y `extra/crism_class.tif`. Otra ubicación: variable `JEZERO_DATA`. La primera ejecución crea `data/jezero/planner_cache_20m.npz` (no se versiona). Un ejemplo del informe está en `planner/examples/report_example.json`.

## Entrada: dos bloques

```json
{
  "mission": { ...lo que saca el LLM del texto del astronauta... },
  "system":  { "start_hour": 9.0, "battery_kwh": 30, "battery_capacity_kwh": 40, "reserve_pct": 20 }
}
```
`system` no lo pone el LLM. Lo aporta el vehículo: la hora por su enlace o reloj y la batería por su gestor de energía.

### Esquema de `mission` (para el prompt y la validación del LLM)
```python
class Mission(BaseModel):
    human: bool = False                      # hay tripulación a bordo (no significa "a pie")
    safety: Literal["low", "normal", "high"] = "normal"   # personas o carga frágil → "high"
    power: bool = False                      # priorizar el ahorro de energía
    route_preference: Literal["shortest", "fastest"] | None = None
    origin: str | None = None                # nombre de lugar conocido o "lon,lat"
    destination: str | None = None
    science_targets: list[ScienceTarget] = []
    science_detour: Literal["low", "medium", "high"] = "medium"  # cuánto rodeo se acepta por la ciencia: +20/50/100 %
    return_to_origin: bool = False           # ida y vuelta

class ScienceTarget(BaseModel):
    target: Literal["aqueous", "carbonates", "clays", "smectites", "kaolinite",
                    "olivine", "pyroxene", "delta", "crater_floor"]
    priority: float = Field(1.0, ge=0.1, le=1.0)   # 1 = objetivo principal, 0.3 = "si pilla de camino"
```
**El parámetro de lo que se quiere investigar es `science_targets`.** Es una lista porque una misión puede tener varios objetivos con prioridad distinta. El LLM solo elige nombres de una lista cerrada; el código traduce cada nombre a zonas del mapa. Guía para el prompt:

| Lo que dice el astronauta | `science_targets` |
|---|---|
| "evidencias de agua", "antiguo lago", "habitabilidad" | `[{"target": "aqueous"}]` (= carbonatos + arcillas + delta) |
| "carbonatos" | `[{"target": "carbonates"}]` |
| "arcillas", "filosilicatos" | `[{"target": "clays"}]` |
| "esmectitas" / "caolinita" | `smectites` / `kaolinite` |
| "roca ígnea", "basalto", "olivino" / "piroxeno" | `olivine` / `pyroxene` |
| "sedimentos del delta", "abanico" | `delta` |
| "suelo del cráter" | `crater_floor` |
| "carbonatos sobre todo, y arcillas si pilla de paso" | `[{"target": "carbonates", "priority": 1}, {"target": "clays", "priority": 0.3}]` |
| "tenemos tiempo de sobra" / "lo justo" | `science_detour: "high"` / `"low"` |

Los campos desconocidos se ignoran. Los valores no válidos dan error 400 con el motivo, para que el LLM pueda reintentar.

## Modelo
**Rejilla nativa de 20 m** (la del DTM CTX, 1512 × 1596 = 2,4 M celdas) con 16 vecinos. No tiene sentido bajar de 20 m: la pendiente y la rugosidad salen del DTM CTX a 20 m, y la inercia térmica es de 100 m. HiRISE a 1 m solo cubre el 32 % central (ver mejoras).

```
coste(u→v) = mult · [w_dist·L + w_time·t·v0 + w_E·E/e_ref] + L · Σ w_k · riesgo_k
```
- **Depende de la dirección:** la pendiente longitudinal sale de Δh (subir ≠ bajar). La lateral es el gradiente perpendicular a la dirección de avance.
- **Velocidad:** `v0 / (1 + 0,08·|pendiente| + 0,06·lateral + 1,5·rugosidad + 1,0·arena)`, con v0 = 2,5 m/s. "Arena" es el máximo entre el suelo blando (inercia térmica) y las dunas.
- **Energía:** rodadura (Crr 0,08 en firme, hasta 0,20 en arena) + subida + consumo fijo (800 W, más 1,5 kW de soporte vital si hay tripulación) − solar. Vehículo genérico de 3 t; las cifras son órdenes de magnitud y no se calibran (es un producto mínimo).
- **Riesgo:** rugosidad (TRI), suelo blando (inercia térmica < 260), **dunas** (unidad "Eolian bedform" de SIM 3464, 119 km²; su inercia térmica es casi normal, así que solo así se detectan), (pendiente/máx)², (lateral/máx)², dato desconocido y exposición (si hay tripulación). No se usa `dist_traverse`.
- **`mult`:** descuento científico `1 − 0,5·interés`, que se aplica **solo a distancia, tiempo y energía, nunca al riesgo**. Ir a ver minerales no debe hacer que una duna parezca más segura.
- **Restricciones duras** (el JSON no puede relajarlas): pendiente y lateral máximas, margen alrededor de celdas peligrosas y, con `safety=high`, celdas sin dato.

| `safety` | low | normal | high |
|---|---|---|---|
| Pendiente / lateral máx. | 25° / 15° | 20° / 12° | 15° / 8° |
| Margen | 0 | 40 m | 100 m |
| Pesos rugosidad / blando / dunas | 0,3 / 0,3 / 0,5 | 1 / 1 / 2 | 3 / 3 / 5 |

### Heurística
`h(n) = hflat · distancia_euclídea(n, meta) + c_subida · max(h_meta − h_n, 0)`:
- **Primer término:** `hflat` es el menor coste por metro de toda la rejilla, sin contar la subida.
- **Segundo término:** cualquier ruta tiene que subir al menos el desnivel hasta la meta, y eso cuesta energía.

Es admisible y consistente. Las pruebas comparan el resultado con un Dijkstra, tanto en problemas aleatorios como en la rejilla real. Medido en crater_floor_south → delta_top:

| Escenario | Sin heurística | Heurística anterior | Nueva |
|---|---|---|---|
| A* clásico | 1 632 357 nodos | 105 510 | 105 293 (0,05 s) |
| power | 1 304 552 | 605 659 | **511 623 (−15 %)** |
| fastest | 1 314 328 | 817 554 | 802 223 |

La búsqueda ya tarda 0,05–0,4 s. El cuello de botella es construir la rejilla de costes (≈2,5 s por perfil de pesos), que se guarda en caché (4 perfiles).

### science_targets → zonas
1. Diccionario fijo nombre → máscara: CRISM por clases con confianza 1 / 0,6 y geología SIM 3464 con peso 0,5.
2. Mapa de interés: Σ prioridad × máscara, suavizado a 120 m y normalizado.
3. Manchas candidatas: ≥ 2,4 ha, a más de 500 m de A y de B, las 10 de más valor.
4. Matriz de costes exacta entre candidatos: Dijkstra desde cada uno, que se detiene en cuanto ha alcanzado a todos.
5. Inserción voraz con presupuesto `(1 + science_detour) × coste(A→B)`, y A* tramo a tramo.
6. Cada parada suma 20 min al tiempo y a la energía.

## Salida: informe para el LLM del casco (`report.py`)
Ejemplo completo en `planner/examples/report_example.json`. Bloques:
- `feasible`: falso si hay algún aviso crítico.
- `route`:
  - métricas físicas: distancia, tiempo, energía total y de tracción, subida y bajada, pendientes máximas, km por terreno rugoso, blando, dunas o sin dato, y exposición media;
  - horario: salida, llegada, límite de luz y margen;
  - batería al salir y al llegar;
  - `science_stops` (lon, lat, minerales y minutos de parada);
  - `charging_stop`;
  - `waypoints_lonlat` (~60 puntos).
- `classic_astar`: las mismas métricas para la ruta de un A* de distancia pura, **medida con el mismo vehículo y tripulación** (solo cambia el recorrido).
- `comparison`: lo que el LLM necesita para frases del tipo "has ahorrado un X % de batería":
  - `energy_saved_pct`, `drive_energy_saved_pct`, `time_saved_pct`, `extra_distance_pct`;
  - reducción de pendiente máxima y lateral;
  - km de rugoso, blando y dunas evitados;
  - `on_<objetivo>_km_gained`.
- `why`: qué términos de coste evita la ruta frente al A* clásico, medidos con los pesos de esta misión (p. ej. energía 39 %, tiempo 20 %, suelo blando 14 %), y los km ganados sobre cada objetivo científico.
- `warnings` (código, gravedad y mensaje en inglés) y `suggestions`.

### Avisos de luz y batería
- **Luz:** ventana de 06:00 a 18:00 LTST con 30 min de margen. Sin estaciones ni sombras por ahora (llegará con el mapa de sombras).
  - `NO_DAYLIGHT_AT_DEPARTURE`: la salida cae fuera de la ventana de luz.
  - `ARRIVAL_AFTER_DAYLIGHT`: la llegada pasa del límite. Es **crítico con tripulación** y un aviso sin ella.
- **Batería:** se necesita la energía de la ruta, más las paradas, más una reserva (20 % de la capacidad).
  - `BATTERY_BELOW_RESERVE`: se llega con menos de la reserva.
  - `SWITCH_TO_POWER_SAVING` (sugerencia): si no alcanza y `power` estaba desactivado, se calcula la ruta de ahorro y se dice si basta.
  - `CHARGING_STOP_REQUIRED`: si sigue sin alcanzar, se busca un sitio soleado, llano, firme y sin dunas a menos de 1 km de la parte de la ruta alcanzable con la batería actual. Se replanifica pasando por él y se calcula cuánto hay que parar. La carga se estima con un panel desplegado de 3 kW pico × `insolation_rel` × curva solar del día, menos el consumo parado (y el soporte vital si hay tripulación).
  - `BATTERY_INSUFFICIENT`: no se llega ni a la parada de carga.
  - `CHARGING_DOES_NOT_FIT_DAYLIGHT`: no da tiempo a cargar con luz.

## Herramienta en vivo (`live.py`)
- **Controles:** parámetros de misión, `science_targets` con prioridad, `science_detour`, ida y vuelta, y estado del sistema (hora y batería). Origen y destino por lista o con clic en el mapa.
- **Mapa:** ruta con contexto, A* clásico, paradas científicas y parada de carga.
- **Panel:** avisos, tabla comparativa y botón "Ver JSON" con el informe completo.
- **Tiempos:** 0,5 s con un perfil ya en caché, 3–8 s con uno nuevo y 10–17 s con ciencia.

No es el frontend del producto.

## Pendiente / mejoras
- **Mapa de sombras** (capa del equipo, aún no está aquí): una serie de imágenes de sombra por franja de tiempo.
  - Diseño: en cada arista se usa la franja de la hora estimada de paso (`start_hour` + tiempo acumulado), en 2–3 pasadas (ruta → horas → costes → ruta) en lugar de un A* dependiente del tiempo.
  - Sustituye a `insolation_rel` en la carga solar de `power` y en la elección y duración de la parada de carga.
  - Añade frío y calefacción en sombra, y fija el límite de luz real en lugar de la ventana 06–18.
- **Rendimiento:** construir la rejilla de costes (2,5 s) en Numba en paralelo. La ciencia (11 Dijkstras a 20 m) podría seleccionar paradas a 40 m y trazar a 20 m.
- **Explicación más fina:** el `why` mide términos de coste; podría añadir *dónde* (tramos concretos que se evitan).
- **HiRISE 1 m** en el centro: refinar la ruta dentro de un corredor de unos 200 m.
- **Suavizado** de la ruta, al estilo Theta*.
- El valor de cada mancha científica sigue favoreciendo las grandes, y fuera de CRISM el interés vale 0 (no "desconocido").
