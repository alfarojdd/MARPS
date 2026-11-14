# El reto: "Interplanetary Survival Guide: Martian Map"

- **Evento:** NASA Space Apps Challenge 2026 (hackathon del 14 al 15 de noviembre de 2026).
- **Página oficial:** https://www.spaceappschallenge.org/2026/challenges/interplanetary-survival-guide-martian-map/
- **Dificultad:** Intermedia.
- **Temas:** Human Exploration, Mars, Planets & Moons, Software, Space Exploration.
- **Número:** lo llamamos "reto 11", pero en el listado oficial de Málaga (14 retos) es el **nº 10** ("Guía de supervivencia marciana"). El nº 11 es "Lunar Landing Site Navigator". El que trabajamos es el **Martian Map**.

## Qué pide

Crear un **mapa, herramienta o interfaz** que un astronauta en Marte pueda usar durante una salida a la superficie (un "Marswalk"). Tiene que ser una **vista por capas e integrada** de una zona o ruta concreta, que combine datos de varias misiones científicas de la NASA y ayude a planificar y ejecutar la salida con seguridad mientras se hace ciencia.

### Por qué existe el reto
Hoy hay herramientas como JPL Mars Trek o los mapas geológicos del USGS que permiten superponer capas sobre Marte, pero están pensadas para **escala regional o global**. Para una salida concreta de un astronauta hace falta un mapa **hiperlocal**, centrado en su ruta y sus objetivos.

### Objetivos explícitos
1. Elegir **objetivos científicos** de la misión y una **ubicación** (ejemplo del enunciado: estudiar las formaciones *boxwork* en el Monte Sharp, donde las vio Curiosity en 2025).
2. Se recomienda una zona muy explorada por rovers (más datos e imágenes), aunque se puede elegir una menos estudiada.
3. Integrar **al menos tres tipos de datos**: óptico, térmico, espectral, topográfico, geofísico, atmosférico, radiación, químico...
4. **Seguridad del astronauta, lo primero:** meteorología espacial y radiación, movilidad reducida por el traje y la carga.
5. Si es posible, un **mapa de ruta** que muestre por dónde va el astronauta para cumplir sus objetivos científicos **evitando obstáculos** (rocas grandes, etc.).

### Consideraciones opcionales
- Formato libre: pantalla en el hábitat, app de tablet, HUD en el visor del casco...
- Puede ser estático, interactivo, o **un sistema que genere mapas** de distintos lugares o con distintos datos.
- Inspirarse en mapas de otras misiones (Tierra, Luna, otros planetas).
- Marco temporal libre: datos pasados, condiciones previstas o datos estables (topografía, geología).
- Incluir **imágenes en primera persona** de los rovers para que el astronauta sepa qué se va a encontrar.
- Considerar rovers de apoyo o astronautas trabajando en parejas.

## Recursos oficiales del reto
| Recurso | Para qué sirve | URL |
|---|---|---|
| JPL Mars Trek | Portal web con capas de datos de Marte (DEM, mosaicos, etc.) y servicios WMTS | https://trek.nasa.gov/mars/ |
| USGS-NASA Planetary Geologic Mapping | Mapas geológicos estandarizados de Marte | https://astrogeology-usgs.hub.arcgis.com/pages/interactive-maps-mars |
| Ruta propuesta de Curiosity en Mount Sharp | Ejemplo visual de un mapa de ruta | https://science.nasa.gov/resource/curiositys-proposed-path-up-mount-sharp/ |
| NASA Worldview | Inspiración (es de la Tierra) | https://worldview.earthdata.nasa.gov/ |
| Perseverance Raw Images | Más de 1 millón de imágenes de superficie | https://mars.nasa.gov/mars2020/multimedia/raw-images/ |

Fuentes de datos adicionales probables (por verificar cuando lleguemos a la fase de datos): HiRISE (DTM e imágenes de alta resolución), CTX, THEMIS (inercia térmica), CRISM (mineralogía), MOLA (topografía global), MEDA/REMS (meteorología de superficie), RAD de Curiosity (radiación).
