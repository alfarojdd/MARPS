# MARPS

Mars Aerial Route Pairing System: planificador de rutas para una salida a la superficie de Marte que tiene en cuenta el terreno **y** lo que la misión quiere hacer.

Reto: *Interplanetary Survival Guide: Martian Map* (NASA Space Apps Challenge 2026, Málaga).

## Idea

- Un mapa por capas de una zona de Marte, con datos de misiones NASA (relieve, pendiente, rugosidad, térmica, mineralogía, radiación...).
- Origen y destino sobre el mapa.
- Un cuadro donde se describe la misión en lenguaje natural.
- Un LLM local convierte esa descripción en pesos y restricciones (JSON).
- El planificador calcula la ruta con esos pesos. El LLM solo traduce, nunca planifica.

Detalle en [docs/IDEA.md](docs/IDEA.md) y [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md).

## Carpetas

- `platform/`: interfaz y API
- `llm/`: traducción de la misión a JSON
- `planner/`: algoritmo de rutas
- `data/`: descarga y preprocesado de mapas
- `docs/`: reto, idea, fuentes y progreso

Cómo trabajamos: [CONTRIBUTING.md](CONTRIBUTING.md).

## Licencia

Por decidir.
