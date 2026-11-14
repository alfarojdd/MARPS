# llm/: traducción de la misión a parámetros

**Rama de área:** `area/llm-platform`

## Qué va aquí
- Prompt del sistema y ejemplos (few-shot) para convertir el texto de misión en JSON.
- **Esquema JSON** de salida y validación (Pydantic o JSON Schema).
- Configuración del modelo local (Ollama, llama.cpp u otro) y cómo instalarlo.
- Valores por defecto y reintentos si el JSON no valida.
- Pruebas con misiones de ejemplo (texto → JSON esperado).

## Principio
**El LLM solo traduce, no planifica.** Sus salidas se validan siempre, y los límites de seguridad los aplica el planificador aunque el modelo no los mencione.

## Contrato
Salida **[B]** definida en [../docs/ARQUITECTURA.md](../docs/ARQUITECTURA.md).

## Pendiente
- [ ] Elegir modelo y runtime (tamaño pequeño, JSON estructurado, funciona sin conexión)
- [ ] Esquema JSON definitivo, acordado con `planner/`
- [ ] Conjunto de misiones de ejemplo para probar
- [ ] Los modelos descargados **no** se suben al repo (están en `.gitignore`)
