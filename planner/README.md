# planner

Planificador de rutas consciente de la misión: A* sobre la rejilla de 20 m de Jezero, con coste que depende de los parámetros del LLM y del estado del vehículo. Devuelve la ruta y un informe JSON para el resumen del LLM del casco.

```bash
pip install -r planner/requirements.txt fastapi
python planner/live.py                  # banco de pruebas en http://127.0.0.1:8766
cd planner && python -m pytest -q       # pruebas
```

Datos: `data/jezero/` (Drive, ver [../data/jezero/README.md](../data/jezero/README.md)) o la ruta de `JEZERO_DATA`.

- Modelo, sombras y pendientes: [../docs/PLANNER.md](../docs/PLANNER.md).
- Contrato con backend y frontend (`POST /plan-route`): [../docs/PLANNER_INTEGRATION.md](../docs/PLANNER_INTEGRATION.md).
- Ejemplos reales: [examples/](examples/).

Sombras: usa `../mars_shadows.py` y `../assets/SunAngle.csv`. Si faltan, funciona igual sin ellas.
