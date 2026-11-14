# Registro de progreso

Una entrada por sesión de trabajo, la más reciente arriba. Formato: fecha, área, qué se hizo, decisiones tomadas, bloqueos.

## 2026-11-14: sombras y API del planificador (planner)
- Integrado `mars_shadows.py` (Pablo) con `assets/SunAngle.csv` en `planner/shadows.py`. La efeméride se pasa a hora solar local (amanecer 05:48, atardecer 18:12) y se calcula la luz directa con sombra proyectada y autosombra para 26 instantes (en caché).
- La luz entra en la carga solar en marcha, en un término de riesgo por sombra (más con `power` o con tripulación) y en la **parada de carga**: se elige el sitio que termina antes de cargar con la luz real, evitando la sombra. La ventana de luz de los avisos sale del CSV.
- Métricas nuevas: `shadow_km`, `night_km` y `shadow_km_avoided`. Hallazgo: de día casi no hay sombras en el suelo del cráter; importan al amanecer y al atardecer y junto al borde y el delta.
- `planner/api.py`: `POST /plan-route` (FastAPI) con `{mission, system}` → `{report, geojson, ctx_px}`, más `GET /places`. Acepta los nombres del LLM ("Octavia E. Butler Landing", "Belva crater") y coordenadas ("18.44N, 77.45E").
- Contrato con backend y frontend en [PLANNER_INTEGRATION.md](PLANNER_INTEGRATION.md); actualizados [B] y [C] en `ARCHITECTURE.md`.
- Pendiente para integrar: ampliar el esquema del LLM (`backend/llm/api.py` y `Modelfile`) con `safety`, `science_targets`, `science_detour` y `return_to_origin`, y unificar los nombres de lugares.

## 2026-11-14: planificador A* consciente de la misión (planner)
- Subido `planner/`: A* sobre la rejilla de 20 m con 16 vecinos y coste por arista dependiente de la dirección (subida, bajada, pendiente lateral), energía, riesgo (rugosidad, suelo blando por inercia térmica, dunas de SIM 3464, dato desconocido, exposición) y restricciones duras que el JSON no puede relajar. Heurística admisible con cota de subida. Detalle en [PLANNER.md](PLANNER.md).
- Parámetros de misión: los 5 del LLM (`human`, `origin`, `destination`, `power`, `route_preference`) más `safety`, `science_targets`, `science_detour` y `return_to_origin`. El estado del vehículo (hora y batería) llega aparte en `system`.
- `report.py` genera el JSON para el resumen del LLM del casco: comparación frente a un A* clásico de distancia pura, `why`, avisos de luz y batería, y parada de carga solar.
- `live.py`: banco de pruebas interactivo (no es el frontend).
- Hecho como spike (prueba rápida), con 10 pruebas.

## 2026-11-14: capas de Jezero (data)
- Subido `data/jezero/`: stack de 14 capas a 20 m con la misma rejilla (elevación CTX/HRSC, pendiente, rugosidad, TPI, orientación, sombreado, inercia térmica, THEMIS día/noche, insolación, proxy de columna atmosférica, distancia a la traza), vectores y el pipeline con pruebas. Detalle en [JEZERO_LAYERS.md](JEZERO_LAYERS.md).
- Subido el visor de capas en `platform/viewer/` (las teselas se generan con el pipeline).
- Regla: la base solo incluye capas que cubren el 100 % del recuadro; única excepción, la inercia térmica de Jezero (96,1 %).
- Sin pendiente a escala de metro ni mineralogía en la base: HiRISE y CRISM solo cubren el centro (32-41 %). Quedan documentadas como descartadas.
- El stack pesa 90 MB: no regenerarlo ni resubirlo por cambios pequeños (cada versión se queda en el historial).
- Decidida la zona: Jezero.

## 2026-11-14: organización del repositorio
- Estructura por áreas (`platform/`, `llm/`, `planner/`, `data/`, `docs/`) y ramas de área.
- Borrador de los tres contratos entre áreas en [ARCHITECTURE.md](ARCHITECTURE.md).

## 2026-11-14 (tarde): mapas sin trayectoria
- Se retira la trayectoria de Perseverance: capa `dist_traverse`, vectores de traza y waypoints, y la elipse de aterrizaje. Stack base de 13 bandas.
- Pendiente de decisión: reescribir el historial de `main` para borrar la trayectoria de commits anteriores (328d796). No se ha hecho.

## Decisiones pendientes
- [x] Zona de Marte: Jezero
- [x] Capas concretas y fuentes: ver [JEZERO_LAYERS.md](JEZERO_LAYERS.md) (falta que el planificador elija cuáles usa)
- [ ] Formato final de las capas, del JSON de pesos y de la ruta
- [ ] Modelo y runtime del LLM local
- [ ] Framework de mapa web
- [ ] Licencia del repositorio
- [ ] Responsables de cada área (rellenar en [CONTRIBUTING.md](../CONTRIBUTING.md))
