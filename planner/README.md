# planner/: algoritmo de planificación de rutas

**Rama de área:** `area/planner`

## Qué va aquí
- Construcción del **mapa de coste** a partir de las capas y los pesos.
- Búsqueda de ruta (A* sobre rejilla como base; D*, Theta* u otros si compensa).
- Restricciones duras (pendiente máxima, zonas prohibidas) y bonificación por interés científico.
- Cálculo de métricas de la ruta (distancia, desnivel, pendiente máxima, tiempo, exposición).
- **Tests**: es la parte más importante de comprobar. Casos pequeños con respuesta conocida.

## Contratos
- Entrada: rejilla de capas **[A]** y JSON de parámetros **[B]**.
- Salida: ruta y métricas **[C]**.
- Detalle en [../docs/ARQUITECTURA.md](../docs/ARQUITECTURA.md).

## Pendiente
- [ ] Elegir lenguaje y estructura (propuesta: Python + NumPy)
- [ ] Planificador mínimo con capas sintéticas, sin esperar a los datos reales
- [ ] Integrar los pesos del LLM
- [ ] Explicación de por qué se eligió la ruta
