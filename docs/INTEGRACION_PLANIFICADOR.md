# Integración del planificador con el backend y el frontend

Contrato entre `planner/` (rutas), `backend/` (LLM + API) y el frontend (React + Leaflet). Si cambia, actualizad este fichero y `ARQUITECTURA.md` en el mismo PR.

## Flujo

```
Astronauta (texto)
   │
   ▼
POST /parse-mission  (backend/llm, Ollama)         → mission  (JSON del LLM)
   │
   ▼  + system (hora y batería, los sabe el vehículo)
POST /plan-route     (planner/api.py, mismo FastAPI) → report + geojson + ctx_px
   │                                   │
   ▼                                   ▼
LLM: resumen en lenguaje natural    Frontend: dibuja la ruta, las paradas y los avisos
("has ahorrado un 14 % de batería…")
a partir de `report`
```

El LLM **no planifica**: solo rellena `mission` y después redacta el resumen a partir de `report`. Todo lo numérico (ahorro, avisos, horas) lo calcula el planificador.

## Requisitos

| Qué | Detalle |
|---|---|
| Python | 3.10+; `pip install -r planner/requirements.txt` (numpy, scipy, numba, rasterio, matplotlib, pillow) + `fastapi` del backend |
| Datos | `data/jezero/stack/jezero_stack_20m.tif`, `data/jezero/extra/geo_unit.tif`, `data/jezero/extra/crism_class.tif` (Drive). Otra ruta: `JEZERO_DATA` |
| Sombras | `mars_shadows.py` (raíz del repo) y `assets/SunAngle.csv`. Otras rutas: `MARS_SHADOWS_DIR`, `SUN_CSV_DIR`. Sin ellos funciona igual con la insolación media y una ventana de luz fija 06–18 h |
| Memoria | ~2 GB (rejilla 1512 × 1596 con 16 vecinos; caché de 4 perfiles de ~150 MB) |
| Arranque | El primer `POST /plan-route` tarda ~10 s (capas + 26 mapas de sombra; luego en caché `data/jezero/planner_*.npz`) |
| Tiempo por petición | 1–6 s; con `science_targets` 10–17 s. Mostrar un indicador de "calculando" |
| Concurrencia | Un cálculo a la vez (lock). Para la demo basta |

Montaje en el FastAPI del backend:
```python
import sys; sys.path.insert(0, "planner")
from api import router as planner_router
app.include_router(planner_router)
```

## Entrada: `POST /plan-route`

```json
{
  "mission": { "human": true, "origin": "Octavia E. Butler Landing", "destination": "delta_top",
               "power": true, "route_preference": null, "safety": "normal",
               "science_targets": [{"target": "carbonates", "priority": 1.0}],
               "science_detour": "medium", "return_to_origin": false },
  "system":  { "start_hour": 9.0, "battery_kwh": 24, "battery_capacity_kwh": 40, "reserve_pct": 20 }
}
```
Ejemplo completo: [../planner/examples/plan_route_request.json](../planner/examples/plan_route_request.json).

### `mission` (lo rellena el LLM)
| Campo | Tipo | Defecto | Significado |
|---|---|---|---|
| `human` | bool | `true` | Hay tripulación a bordo. Sube la seguridad a `normal` como mínimo, añade soporte vital (+1,5 kW), penaliza exposición y sombra, y llegar de noche pasa a ser crítico |
| `origin`, `destination` | str | obligatorio | Nombre de lugar o coordenadas (ver abajo) |
| `power` | bool | `false` | Ahorrar energía y aprovechar el sol: más peso a la energía, evita la sombra y, si la batería no llega, busca dónde cargar al sol |
| `route_preference` | `"shortest"` \| `"fastest"` \| `null` | `null` | Distancia, tiempo o equilibrio |
| `safety` | `"low"` \| `"normal"` \| `"high"` | `"normal"` | Personas o carga frágil → `high` (pendiente máx. 15°, lateral 8°, margen de 100 m, evita dunas, arena y celdas sin dato) |
| `science_targets` | lista de `{target, priority}` | `[]` | Qué se quiere investigar (tabla siguiente). `priority` de 0,1 a 1 |
| `science_detour` | `"low"` \| `"medium"` \| `"high"` | `"medium"` | Rodeo aceptado por la ciencia: +20 / +50 / +100 % de coste |
| `return_to_origin` | bool | `false` | Ida y vuelta |

**Lugares** (`GET /places` los lista):
- Nombres: `landing_site` ("Octavia E. Butler Landing"), `belva_crater` ("Belva", "Belva crater rim"), `neretva_vallis`, `jezero_centre`, `delta_top`, `delta_carbonates`, `north_carbonates`, `crater_floor_south`, `western_rim` y `north_plains`. No distingue mayúsculas, espacios ni paréntesis.
- Coordenadas: `"77.45,18.44"` o `"18.44N, 77.45E"`.
- Un lugar desconocido o fuera del mapa devuelve **400** con la lista de lugares válidos. El backend puede pedir al LLM que corrija. "Three Forks" aún no está, porque faltan coordenadas verificadas.

**`science_targets`: posibilidades para la demo**
| `target` | Qué es | Datos | Dónde hay en el mapa |
|---|---|---|---|
| `aqueous` | Atajo: indicios de agua antigua = `carbonates` + `clays` + `delta` | CRISM + SIM 3464 | Delta y margen del lago |
| `carbonates` | Carbonatos de Mg (se forman en agua) | CRISM clases 2 y 6 | ~48 km², sobre todo delta occidental y margen (núcleo en 77,364 °E, 18,546 °N) |
| `clays` | Arcillas / filosilicatos (esmectitas, caolinita) | CRISM 3, 4, 5, 9 y 10 | ~91 km², repartidas por el centro |
| `smectites` | Solo esmectitas Fe/Mg | CRISM 3, 4, 5 y 10 | Subconjunto de `clays` |
| `kaolinite` | Caolinita (alteración intensa por agua) | CRISM 9 | ~15 km² |
| `olivine` | Olivino (roca ígnea; con esmectita indica alteración) | CRISM 1, 4 y 5 | Suelo del cráter |
| `pyroxene` | Piroxeno (roca ígnea) | CRISM 7 y 8 | ~23 km² |
| `delta` | Sedimentos del abanico deltaico | SIM 3464 (Jezero fan 1 y 2) | Delta occidental |
| `crater_floor` | Unidad del suelo del cráter | SIM 3464 (Jezero floor) | Centro y sur |

CRISM solo cubre el **41 % central**. Para la demo, A y B deben estar cerca de esa zona (por ejemplo, de `landing_site` o `crater_floor_south` a `delta_top`). Guía de frases para el prompt del LLM: [PLANIFICADOR.md](PLANIFICADOR.md) (sección "Esquema de `mission`").

### `system` (lo pone el vehículo, no el LLM)
| Campo | Defecto | Significado |
|---|---|---|
| `start_hour` | 9.0 | Hora solar local de Jezero (LTST, 0–24) a la que se sale |
| `battery_kwh` | 30 | Carga actual |
| `battery_capacity_kwh` | 40 | Capacidad |
| `reserve_pct` | 20 | Reserva mínima a la llegada |

## Salida: `200 OK`

```json
{ "report": { … }, "geojson": { "type": "FeatureCollection", "features": [ … ] }, "ctx_px": { "route": [[c, r], …], "classic_astar": [[c, r], …] } }
```
Ejemplo completo: [../planner/examples/plan_route_response.json](../planner/examples/plan_route_response.json).

### `report`: para el resumen del LLM y el panel del frontend
| Bloque | Contenido |
|---|---|
| `feasible` | `false` si hay algún aviso crítico |
| `mission`, `system` | Lo recibido, ya validado |
| `sun` | `source`, `sunrise`, `sunset` y `daylight_limit` (LTST, de `SunAngle.csv`) |
| `route` | Ver detalle debajo de la tabla |
| `classic_astar` | Las mismas métricas para un A* de distancia pura, con el mismo vehículo |
| `comparison` | Ver detalle debajo de la tabla |
| `why` | Lista `{factor, share_pct}`: qué parte del coste evitado frente al A* clásico se debe a cada factor (`energy`, `time`, `soft`, `rough`, `cross`, `dune`, `shadow`…), más `{factor: "on_<target>", km_gained}` |
| `warnings` | `{code, severity: "warning" \| "critical", message}` en inglés (ver tabla de avisos) |
| `suggestions` | Por ejemplo `SWITCH_TO_POWER_SAVING` con la energía y la batería que quedarían |

Detalle de `route`:
- **Distancia y tiempo:** `distance_km` y `time_h` / `duration_h` (horas terrestres; `duration_h` incluye paradas y carga).
- **Horario:** `departure` y `arrival` (LTST, "HH:MM"), `daylight_margin_h`.
- **Energía:** `energy_kwh`, `drive_kwh`, `battery_start_kwh`, `battery_end_kwh` y `battery_end_pct`.
- **Relieve:** `ascent_m`, `descent_m`, `max_pitch_deg` y `max_cross_deg`.
- **Terreno:** `rough_km`, `soft_km`, `dunes_km` y `unknown_km`.
- **Luz:** `shadow_km`, `shadow_pct` y `night_km`.
- **Ciencia:** `on_<target>_km` y `science_stops` (`[{lon, lat, targets, dwell_min}]`).
- **Carga:** `charging_stop` (`{lon, lat, arrive, charge_hours, energy_needed_kwh, battery_on_arrival_kwh, mean_direct_light}` o `null`).
- **Trazado:** `waypoints_lonlat` (~60 puntos).

Detalle de `comparison` (positivo = mejor que el A* clásico):
- **Porcentajes:** `energy_saved_pct`, `drive_energy_saved_pct`, `time_saved_pct` y `extra_distance_pct`.
- **Pendientes:** `max_pitch_reduction_deg` y `max_cross_slope_reduction_deg`.
- **Terreno evitado:** `rough_km_avoided`, `soft_km_avoided`, `dunes_km_avoided` y `shadow_km_avoided`.
- **Ciencia:** `on_<target>_km_gained`.

**Avisos**
| `code` | Gravedad | Cuándo |
|---|---|---|
| `NO_ROUTE` | crítico | Ninguna ruta cumple las restricciones |
| `NO_DAYLIGHT_AT_DEPARTURE` | crítico | Se sale de noche |
| `ARRIVAL_AFTER_DAYLIGHT` | crítico con tripulación / aviso sin ella | Se llega después de `daylight_limit` (atardecer − 30 min) |
| `BATTERY_BELOW_RESERVE` | aviso | Se llega por debajo de la reserva |
| `CHARGING_STOP_REQUIRED` | aviso | No llega la batería: parar X h a cargar en un punto soleado (ya incluido en la ruta) |
| `CHARGING_DOES_NOT_FIT_DAYLIGHT` | crítico | Ni cargando da tiempo con luz |
| `BATTERY_INSUFFICIENT` | crítico | No se llega ni al punto de carga |
| `ROUTE_IN_SHADOW` | aviso | Con tripulación, más del 15 % de la ruta en sombra del terreno |

Ejemplo de prompt para el resumen (backend): *"You are the helmet assistant. Using only the numbers in this JSON, tell the astronaut in 3 short sentences: the route, what it saves versus a classic shortest path (comparison/why), and any warnings first if feasible is false."* + `report`.

### `geojson`: para dibujar en el mapa
Coordenadas **lon/lat planetocéntricas, este positivo**, en el sistema Mars 2000 (el mismo que `meta.json` del mapa base). Cada feature tiene `properties.kind`:
- `route`: LineString de la ruta (cada celda de 20 m).
- `classic_astar`: LineString de referencia (dibujar discontinua).
- `origin`, `destination`: Point con `name`.
- `science_stop`: Point con `order`, `targets` y `dwell_min`.
- `charging_stop`: Point con `charge_hours` y `arrive`.

### `ctx_px`: atajo para Leaflet `CRS.Simple`
Las mismas líneas en píxeles del mosaico CTX de 6 m (`[col, row]`). El mosaico comparte la esquina noroeste con la rejilla de 20 m, así que la conversión es exacta.

## Qué hace el frontend (React + Leaflet)

1. Envía el texto a `/parse-mission` y muestra el `mission` resultante para que el astronauta lo pueda corregir (opcional, pero da confianza).
2. Llama a `/plan-route` con `mission` y `system`, y muestra "calculando" (1–17 s).
3. Dibuja con `ctx_px` sobre el mapa base CTX (`L.CRS.Simple`, `lat = -row`, `lng = col`):
   ```tsx
   const toLatLng = ([c, r]: number[]) => [-r, c] as [number, number];
   <Polyline positions={data.ctx_px.classic_astar.map(toLatLng)} pathOptions={{ dashArray: "8 6", color: "#fff" }} />
   <Polyline positions={data.ctx_px.route.map(toLatLng)} pathOptions={{ color: "#ff8a3d", weight: 4 }} />
   ```
   Para los puntos (paradas, carga) se usan sus lon/lat del `geojson`, pasados a píxel del mapa base con `meta.json` (`col = (R·lon·π/180 − x0)/6`, `row = (y0 − R·lat·π/180)/6`), o con el helper `ctxTiles.ts` del equipo.
4. Panel con:
   - `feasible` y `warnings` (los críticos primero, en rojo);
   - tres o cuatro cifras de `comparison` (energía ahorrada, pendiente lateral reducida, km de arena o dunas evitados, km sobre el objetivo científico);
   - salida, llegada y luz (`route.departure`, `route.arrival`, `sun`);
   - batería al llegar;
   - la parada de carga, si existe.
5. Muestra el resumen del LLM generado a partir de `report`.

## Pendiente para la integración
- Llevar el esquema `Mission` a `backend/llm/api.py` (`JezeroMissionRequirements`), con `safety`, `science_targets`, `science_detour` y `return_to_origin`, y añadir ejemplos al `Modelfile`. Hoy el LLM solo saca 5 campos; el resto toma los valores por defecto.
- Unificar nombres de lugares: `places.json` del frontend, `PLACES` del planificador y los ejemplos del `Modelfile` ("Three Forks" no tiene coordenadas en ninguno).
- `SunAngle.csv` es de un solo día (2026-318). Para otro día hay que generar otro CSV con la misma forma.
