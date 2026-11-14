# Fuentes de datos y referencias

Registro de **todo lo que usamos**: datos, código, imágenes y herramientas. Es obligatorio para la entrega (campos "NASA Data" y "Otros datos y referencias"), y el jurado preguntará **dónde interviene cada recurso NASA y qué cambiaría si se retirara**.

Quien añada una fuente rellena una fila. Las URLs de la sección 2 son candidatas **por verificar**.

## 1. Recursos oficiales del reto

| Recurso | Para qué sirve | URL |
|---|---|---|
| JPL Mars Trek | Portal con capas de Marte (relieve, mosaicos...); candidato a fuente de capas | https://trek.nasa.gov/mars/ |
| USGS-NASA Planetary Geologic Mapping | Mapas geológicos estandarizados de Marte | https://astrogeology-usgs.hub.arcgis.com/pages/interactive-maps-mars |
| Ruta propuesta de Curiosity en Mount Sharp | Ejemplo visual de mapa de ruta | https://science.nasa.gov/resource/curiositys-proposed-path-up-mount-sharp/ |
| Perseverance Raw Images | Imágenes en primera persona | https://mars.nasa.gov/mars2020/multimedia/raw-images/ |
| NASA Worldview | Solo inspiración (es de la Tierra) | https://worldview.earthdata.nasa.gov/ |
| Enunciado del reto | Texto oficial | https://www.spaceappschallenge.org/2026/challenges/interplanetary-survival-guide-martian-map/ |

## 2. Candidatas a capas (por verificar)

| Dato | Instrumento / misión | Tipo | Uso previsto | Dónde buscar |
|---|---|---|---|---|
| Topografía global | MOLA (Mars Global Surveyor) | Topográfico | Relieve base | Mars Trek, USGS Astrogeology |
| Modelos de elevación de alta resolución | HiRISE DTM (MRO) | Topográfico | Pendiente y rugosidad en la zona elegida | https://www.uahirise.org/dtm/ |
| Imagen de contexto | CTX (MRO) | Óptico | Capa visual de fondo | PDS / Mars Trek |
| Inercia térmica | THEMIS (Mars Odyssey) | Térmico | Terreno suelto o roca firme | Mars Trek, PDS |
| Mineralogía | CRISM (MRO) | Espectral | Interés científico (arcillas, sulfatos...) | PDS Geosciences |
| Radiación | RAD (Curiosity) | Radiación | Exposición, ventanas de riesgo | PDS |
| Meteorología de superficie | MEDA (Perseverance), REMS (Curiosity) | Atmosférico | Temperatura y polvo | PDS |
| Geología | Mapas USGS | Geológico | Tipo de terreno e interés | Enlace del punto 1 |

Portales de datos útiles: https://ode.rsl.wustl.edu/mars/ (Mars Orbital Data Explorer) y https://pds-geosciences.wustl.edu/ (PDS Geosciences Node).

## 3. Registro de datos realmente usados

Rellenar al incorporar cada capa.

| Capa | Fuente y enlace | Versión o fecha de consulta | Licencia / condiciones | Resolución y cobertura | Procesado aplicado | Quién |
|---|---|---|---|---|---|---|
| _ejemplo: elevation_ | _HiRISE DTM XXXX_ | | | | _reproyectado, remuestreado a N m_ | |

Para cada capa responder: ¿qué mide y en qué unidades?, ¿hay valores ausentes?, ¿qué NO permite concluir?, ¿qué es observación y qué es transformación o inferencia nuestra?

## 4. Código, librerías y herramientas

| Recurso | Uso | Licencia |
|---|---|---|
| _por rellenar_ | | |

## 5. Uso de IA

Declarar aquí qué herramientas de IA se usan en el desarrollo y cómo (la entrega exige declararlo y marcar el contenido generado):

- Asistente de código: _por rellenar_
- LLM local del producto: _modelo y runtime por rellenar_
