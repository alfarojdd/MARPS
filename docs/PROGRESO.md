# Registro de progreso

Una entrada por sesión de trabajo, la más reciente arriba. Formato: fecha, área, qué se hizo, decisiones tomadas, bloqueos.

## 2026-11-14: capas de Jezero (data)
- Subido `data/jezero/`: stack de 14 capas a 20 m con la misma rejilla (elevación CTX/HRSC, pendiente, rugosidad, TPI, orientación, sombreado, inercia térmica, THEMIS día/noche, insolación, proxy de columna atmosférica, distancia a la traza), vectores y el pipeline con pruebas. Detalle en [CAPAS_JEZERO.md](CAPAS_JEZERO.md).
- Subido el visor de capas en `platform/viewer/` (las teselas se generan con el pipeline).
- Regla: la base solo incluye capas que cubren el 100 % del recuadro; única excepción, la inercia térmica de Jezero (96,1 %).
- Sin pendiente a escala de metro ni mineralogía en la base: HiRISE y CRISM solo cubren el centro (32-41 %). Quedan documentadas como descartadas.
- El stack pesa 90 MB: no regenerarlo ni resubirlo por cambios pequeños (cada versión se queda en el historial).
- Decidida la zona: Jezero.

## 2026-11-14: organización del repositorio
- Estructura por áreas (`platform/`, `llm/`, `planner/`, `data/`, `docs/`) y ramas de área.
- Borrador de los tres contratos entre áreas en [ARQUITECTURA.md](ARQUITECTURA.md).

## Decisiones pendientes
- [x] Zona de Marte: Jezero
- [x] Capas concretas y fuentes: ver [CAPAS_JEZERO.md](CAPAS_JEZERO.md) (falta que el planificador elija cuáles usa)
- [ ] Formato final de las capas, del JSON de pesos y de la ruta
- [ ] Modelo y runtime del LLM local
- [ ] Framework de mapa web
- [ ] Licencia del repositorio
- [ ] Responsables de cada área (rellenar en [CONTRIBUTING.md](../CONTRIBUTING.md))
