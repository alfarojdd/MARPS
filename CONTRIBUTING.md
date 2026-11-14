# Cómo trabajamos

Documentación interna en español. El README y todo lo que se entregue a NASA va **en inglés**.

## Áreas y responsables

Cada área tiene su carpeta, para no pisarnos los ficheros.

| Área | Carpeta | Rama de área | Responsable |
|---|---|---|---|
| LLM + plataforma e interfaz | `llm/`, `platform/` | `area/llm-platform` | _por rellenar_ |
| Algoritmo de planificación | `planner/` | `area/planner` | _por rellenar_ |
| Búsqueda y preparación de mapas | `data/` | `area/data` | _por rellenar_ |
| Documentación y entrega | `docs/`, `README.md` | `main` (cambios pequeños) | _por rellenar_ |

Rellenad la columna de responsables con vuestros usuarios de GitHub.

## Ramas

- **`main`**: siempre presentable. Es lo que se entrega a NASA. Solo entra por Pull Request.
- **`area/*`**: una rama de integración por área. Cada persona del área sube aquí su trabajo del día a día.
- **`feat/<area>-<tema>`** (opcional): rama corta para algo concreto, por ejemplo `feat/planner-astar`. Se funde en la rama de área.

Flujo:

```bash
git clone https://github.com/alfarojdd/MARPS.git
cd MARPS
git checkout area/planner          # tu rama de área
git pull
# ...trabajas dentro de tu carpeta...
git add planner/
git commit -m "planner: A* sobre rejilla con coste ponderado"
git push
```

Cuando algo funciona de forma estable, abrid un **Pull Request de `area/...` a `main`**. Que lo mire otra persona antes de fundirlo. Hacedlo **a menudo**, no solo al final: dos días no dan para un merge gigante.

Antes de empezar cada sesión: `git pull`. Antes de abrir el PR: traed `main` a vuestra rama (`git merge origin/main`) y resolved los conflictos allí.

## Reglas para no pisarnos

1. **Trabaja dentro de tu carpeta.** Si necesitas tocar la de otro área, avísale primero.
2. **Los acuerdos entre áreas están en [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md).** Si cambias un formato (JSON de pesos, formato de capas, formato de ruta), cámbialo ahí **en el mismo PR** y avisa al equipo.
3. **Datos pesados no se suben** (mapas GeoTIFF, DTM...). Se ignoran en `.gitignore`. Sube el script que los descarga y apunta el origen, versión y licencia en [docs/FUENTES.md](docs/FUENTES.md). Sí se pueden subir muestras pequeñas (unos pocos MB) para tests y demo.
4. **Nada de secretos** (claves, tokens, `.env`) ni datos personales. Nunca nombres ni imágenes de menores.
5. **Mensajes de commit claros**, con prefijo de área: `planner:`, `llm:`, `platform:`, `data:`, `docs:`.
6. **Cada pieza lleva su README** con cómo instalarla y ejecutarla, y tests mínimos de lo importante (sobre todo el planificador).

## Plazos que importan

- El desarrollo empieza el **sábado 14 a las 09:00** y el cierre oficial de NASA es el **domingo 15 antes de las 23:59** (ver [docs/ENTREGA.md](docs/ENTREGA.md)).
- Congelad `main` con margen: lo que no esté en `main` a media tarde del domingo no se entrega.

## Licencia

Pendiente de decidir. Hay que elegir una antes de la entrega, porque el repositorio es público. Si no hay preferencia, una permisiva como MIT o Apache-2.0 suele ser lo más sencillo.
