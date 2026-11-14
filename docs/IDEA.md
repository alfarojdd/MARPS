# Nuestra idea: planificador de rutas consciente de la misión

## Resumen en una frase
Un mapa multicapa de una zona de Marte sobre el que un planificador de rutas calcula el camino entre dos puntos teniendo en cuenta **el terreno y también los objetivos de la misión**. Un **LLM local pequeño** traduce la descripción de la misión, escrita en lenguaje natural, a un **JSON de pesos** que modifica el coste del camino.

## El problema que resolvemos
Los planificadores clásicos (A*, Dijkstra, D*...) optimizan sobre una función de coste casi siempre geométrica: distancia, pendiente, obstáculos. En una salida real a Marte el "mejor" camino depende de **para qué** se sale:

- Si la misión es geológica, interesa pasar cerca de afloramientos con ciertos minerales aunque el camino sea más largo.
- Si hay una tormenta solar prevista, interesa minimizar el tiempo expuesto y quedarse cerca de refugio.
- Si el astronauta va cargado con instrumental pesado, las pendientes penalizan mucho más.
- Si se va en rover, cambian los límites de pendiente y de rugosidad.

Nuestra herramienta hace que **la función de coste dependa del contexto de la misión**.

## Cómo funciona (flujo del usuario)
1. El usuario abre la plataforma y ve el mapa de la zona elegida.
2. Activa o desactiva **capas** (relieve, pendiente, rugosidad, mineralogía, inercia térmica, geología, radiación...).
3. Marca un **origen** y un **destino** en el mapa.
4. Escribe el **contexto de la misión** en un cuadro de texto. Ejemplo:
   > "Salida de 4 horas para tomar muestras de arcillas. Vamos dos astronautas a pie con taladro (15 kg). Hay riesgo de evento de partículas solares por la tarde. Evitar pendientes de más de 15°."
5. Un **LLM local** convierte ese texto en un **JSON de parámetros** validado contra un esquema.
6. El planificador combina las capas con esos pesos en un **mapa de coste** y calcula la ruta.
7. Se muestra la ruta sobre el mapa con sus métricas (distancia, desnivel, tiempo estimado, exposición, puntos de interés por los que pasa) y, a ser posible, una explicación de por qué se eligió.

## Pieza clave: del texto al JSON de pesos
El LLM **no planifica la ruta**: solo traduce intención a parámetros. Así el resultado es reproducible, explicable y seguro (el algoritmo de rutas es determinista y los límites de seguridad se aplican siempre).

Esquema orientativo (por definir en detalle):

```json
{
  "modo_desplazamiento": "a_pie",          // a_pie | rover
  "carga_kg": 15,
  "duracion_max_min": 240,
  "restricciones_duras": {
    "pendiente_max_grados": 15,
    "evitar_rugosidad_alta": true
  },
  "pesos": {
    "distancia": 1.0,
    "pendiente": 2.0,
    "rugosidad": 1.5,
    "exposicion_radiacion": 3.0,
    "interes_cientifico": 2.5
  },
  "objetivos_cientificos": ["arcillas", "filosilicatos"],
  "waypoints_deseados": []
}
```

Coste de cada celda del mapa (idea inicial):

```
coste(celda) = Σ peso_i · capa_normalizada_i(celda)  − peso_interés · afinidad(celda, objetivos)
```

Las restricciones duras (pendiente máxima, zonas prohibidas) marcan celdas como intransitables. El "interés científico" actúa como bonificación (menos coste) cerca de lo que la misión busca. El coste se mantiene siempre positivo para que A* siga siendo válido.

## Capas de datos candidatas
| Capa | Origen probable | Uso en el coste |
|---|---|---|
| Elevación (DEM) | HiRISE DTM / CTX / MOLA vía Mars Trek | Base para pendiente y desnivel |
| Pendiente | Derivada del DEM | Penalización y restricción dura |
| Rugosidad / rocas | Derivada del DEM, mapas de rocas HiRISE | Penalización |
| Inercia térmica | THEMIS | Indicador de terreno suelto o roca firme |
| Mineralogía | CRISM | Interés científico |
| Geología | Mapas USGS | Interés científico y tipo de terreno |
| Radiación y clima | RAD (Curiosity), MEDA (Perseverance), modelos | Exposición y ventanas temporales |
| Imágenes de superficie | Raw images de rovers | Vista en primera persona en la ruta |

Para cumplir el requisito del reto basta con **al menos tres tipos de datos**.

## Arquitectura tentativa (sin decidir)
- **Datos:** preprocesado offline de la zona elegida a una rejilla común (mismo CRS y resolución) → GeoTIFF / arrays NumPy.
- **Backend:** Python (FastAPI) con el planificador (A* sobre rejilla) y el endpoint que llama al LLM.
- **LLM local:** modelo pequeño (por ejemplo vía Ollama o llama.cpp) con salida JSON estructurada y validación (Pydantic/JSON Schema). Si falla la validación, se reintenta o se usan pesos por defecto.
- **Frontend:** mapa web (Leaflet / OpenLayers / deck.gl) con selector de capas, clic para origen y destino, cuadro de contexto y panel de resultados.

## Zona candidata
Pendiente de decidir. Opciones con muchos datos: **Gale / Mount Sharp** (Curiosity, boxwork, el propio ejemplo del enunciado) o **cráter Jezero** (Perseverance, delta, HiRISE DTM disponibles).

## Valor diferencial frente a otras soluciones
- Mapas como Mars Trek muestran capas; nosotros **razonamos sobre ellas** para planificar.
- Mismo origen y destino → **rutas distintas según la misión**, una demo muy visual.
- Pesos explícitos en JSON → la decisión es **transparente y editable** por el astronauta o el control de misión.
- LLM **local**: funciona sin conexión con la Tierra (con 4 a 24 minutos de retardo de comunicación, esto importa).
