# Visor de capas de Jezero

Mapa Leaflet con cambio de capas (←/→), cortinilla de comparación, vectores e inspector de valores. Las teselas no se versionan:

```bash
pip install -r data/jezero/pipeline/requirements.txt
cd data/jezero/pipeline && python unpack_stack.py && python make_viewer_data.py
cd ../../.. && python3 -m http.server 8765 --directory platform/viewer
```
Abrir http://localhost:8765. Usa Leaflet 1.9.4 desde cdnjs (necesita conexión).
