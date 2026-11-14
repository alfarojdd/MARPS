# platform/: plataforma web e interfaz

**Rama de área:** `area/llm-platform`

## Qué va aquí
- Visor de mapa con **selector de capas**.
- Selección de **origen y destino** con clic.
- **Cuadro de contexto de misión** y botón de calcular.
- Panel de resultados: ruta sobre el mapa, métricas y explicación.
- API que une las piezas (llama al LLM y al planificador).

## Contratos
Consume las capas **[A]** y la ruta **[C]**, y llama al LLM para obtener **[B]**. Ver [../docs/ARQUITECTURA.md](../docs/ARQUITECTURA.md).

## Guía de diseño de la organización (resumen)
- El propósito se entiende a primera vista: título claro, una frase y un botón principal.
- Flujo principal sin callejones sin salida: origen y destino → misión → ruta.
- Texto principal de 16 px o más; contraste 4,5:1 (3:1 para texto grande e iconos); no usar el color como única señal, importante para las capas.
- Objetivos de pulsación de 44×44 px.
- Cada acción responde: estado de carga mientras el LLM y el planificador trabajan, y mensajes de error que dicen qué hacer.
- Se proyectará en una sala: nada de texto pequeño o técnico.

## Pendiente
- [ ] Elegir framework de mapa y de frontend
- [ ] Maqueta con datos de ejemplo, sin esperar al planificador
- [ ] Interfaz **en inglés**, porque es lo que ve el jurado de NASA
