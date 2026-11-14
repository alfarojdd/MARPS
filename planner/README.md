# Planner

Mission-aware route planner: A* over the 20 m Jezero grid, with a cost that depends on the LLM parameters and the vehicle state. It returns the route and a JSON report for the helmet LLM summary.

```bash
pip install -r planner/requirements.txt fastapi
python planner/live.py                  # test bench at http://127.0.0.1:8766
cd planner && python -m pytest -q       # tests
```

Data: `data/jezero/` (Drive, see [../data/jezero/README.md](../data/jezero/README.md)) or the path in `JEZERO_DATA`.

- Model, shadows and open issues: [../docs/PLANNER.md](../docs/PLANNER.md).
- Contract with the backend and frontend (`POST /plan-route`): [../docs/PLANNER_INTEGRATION.md](../docs/PLANNER_INTEGRATION.md).
- Real examples: [examples/](examples/).

Shadows: uses `../mars_shadows.py` and `../assets/SunAngle.csv`. If they are missing, it works the same without them.
