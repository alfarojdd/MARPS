const $ = selector => document.querySelector(selector);
const labels = {landscape: "Escena de superficie", detail: "Detalle de roca", aerial: "Vista aérea"};
const textNode = (tag, value, className) => {
  const element = document.createElement(tag);
  element.textContent = value;
  if (className) element.className = className;
  return element;
};

/** Compact catalogue for the existing floating-card route map. The main viewer already has a sidebar. */
export function mountReconstructionPanel(container) {
  container.insertAdjacentHTML("beforeend", `<details class="route-card reconstruction-panel">
    <summary>Reconstrucciones 3D</summary>
    <section id="reconstructions" aria-label="Reconstrucciones 3D">
      <p class="muted">Selecciona un punto 3D para explorar la superficie.</p>
      <div id="sceneStatus" role="status">Cargando catálogo…</div>
      <div class="scene-actions"><button id="sceneFit">Ver puntos 3D</button><button id="sceneFeatured" disabled>Entrar en Cheyava Falls</button></div>
      <label class="row"><input id="sceneMarkers" type="checkbox" checked>Mostrar puntos 3D</label>
      <label class="row"><input id="sceneRoute" type="checkbox">Recorrido de Perseverance</label>
      <input id="sceneSearch" type="search" placeholder="Buscar lugar, autor o sol…" aria-label="Buscar reconstrucciones">
      <select id="sceneFilter" aria-label="Filtrar reconstrucciones">
        <option value="placed">Con ubicación en el mapa</option><option value="local">Archivos 3D locales</option>
        <option value="landscape">Escenas y afloramientos</option><option value="detail">Detalles de roca</option>
        <option value="unplaced">Sin ubicación verificada</option><option value="all">Todo el catálogo</option>
      </select>
      <div id="sceneList" aria-label="Catálogo de reconstrucciones"></div>
      <p class="muted scene-note">Anclas aproximadas; no delimitan la cobertura 3D. La ruta planificada se conserva al entrar y salir.</p>
    </section>
  </details>`);
}

export async function initReconstructions({map, cfg, terrain = null, container = map.getContainer().parentElement, fitOnLoad = true}) {
  const response = await fetch("/api/reconstructions");
  if (!response.ok) throw new Error("No se pudo cargar el catálogo 3D. Inicia el visor con python3 backend/viewer.py.");
  const catalog = await response.json(), scenes = catalog.scenes;
  const k = Math.PI * cfg.radius / 180;
  const project = coords => L.latLng(coords[1] * k, coords[0] * k);
  const markers = L.layerGroup().addTo(map), pins = new Map();
  if (!$("#surfaceDialog")) document.body.insertAdjacentHTML("beforeend", `<dialog id="surfaceDialog" aria-labelledby="surfaceTitle">
    <header><div><strong id="surfaceTitle"></strong><div id="surfaceByline" class="muted"></div></div><button id="surfaceClose">Volver al mapa ×</button></header>
    <div id="surfaceViewport"></div>
    <footer><span id="surfaceNote"></span><a id="surfaceSource" target="_blank" rel="noopener noreferrer">Fuente original ↗</a></footer>
  </dialog>`);
  const dialog = $("#surfaceDialog");
  let previousFocus, route, routeRequested = false;

  function close() {
    dialog.close();
  }
  dialog.addEventListener("close", () => {
    $("#surfaceViewport").replaceChildren(); // tears down the iframe's WebGL, workers and downloads
    terrain?.setPaused(false);
    previousFocus?.focus();
    map.invalidateSize();
  });
  $("#surfaceClose").onclick = close;

  function open(scene) {
    if (!scene?.available || dialog.open) return;
    map.stop();
    previousFocus = document.activeElement;
    $("#surfaceTitle").textContent = scene.title;
    $("#surfaceByline").textContent = `${scene.author} · ${labels[scene.kind]} · ${scene.license}`;
    $("#surfaceNote").textContent = scene.renderer === "sketchfab"
      ? `${scene.anchor} · Visor externo: usa el modo de primera persona de Sketchfab. La escala depende del modelo; los detalles y vistas aéreas se abren en órbita.`
      : scene.description;
    $("#surfaceSource").href = scene.source;
    const frame = document.createElement("iframe");
    frame.title = `Reconstrucción 3D: ${scene.title}`;
    frame.allow = "autoplay; fullscreen; xr-spatial-tracking";
    frame.allowFullscreen = true;
    if (scene.renderer === "sketchfab") {
      const nav = scene.kind === "landscape" ? "fps" : "orbit";
      frame.src = `https://sketchfab.com/models/${encodeURIComponent(scene.id)}/embed?autostart=1&preload=1&navigation=${nav}`;
    } else {
      const url = new URL("./surface.html", import.meta.url);
      url.searchParams.set("id", scene.id);
      frame.src = url.href;
    }
    $("#surfaceViewport").replaceChildren(frame);
    dialog.showModal();
    terrain?.setPaused(true);
    $("#surfaceClose").focus();
  }
  // Escape also works when focus is inside our WebGL iframe.
  window.addEventListener("message", event => {
    if (event.origin === location.origin && event.source === $("#surfaceViewport iframe")?.contentWindow && event.data === "marps:close-surface") close();
  });

  function card(scene, popup = false) {
    const element = document.createElement("article");
    element.className = "scene-card";
    element.dataset.id = scene.id;
    element.append(textNode("strong", scene.title));
    element.append(textNode("div", `${scene.renderer === "sketchfab" ? "Sketchfab" : "Archivo local"} · ${scene.sol == null ? "Sol no indicado" : `Sol ${scene.sol}${scene.solEnd ? `–${scene.solEnd}` : ""}`} · ${labels[scene.kind]}`, "scene-meta"));
    if (!scene.coordinates) element.append(textNode("div", "Sin ubicación verificada: disponible en el catálogo.", "scene-meta"));
    const enter = textNode("button", scene.kind === "landscape" ? "Entrar en la reconstrucción" : "Ver modelo 3D", "scene-enter");
    enter.disabled = !scene.available;
    if (!scene.available) enter.textContent = "Falta el archivo local";
    enter.onclick = () => open(scene);
    element.append(enter);
    if (scene.coordinates && !popup) {
      const locate = textNode("button", "Situar en mapa");
      locate.onclick = () => {
        setVisible(true);
        if (terrain?.active) {
          const at = project(scene.coordinates);
          terrain.focusAtXY(at.lng, at.lat);
        } else {
          map.setView(project(scene.coordinates), 6, {animate: false});
          pins.get(scene.id)?.openPopup();
        }
      };
      element.append(locate);
    }
    if (popup) element.append(textNode("p", `${scene.author} · ${scene.anchor}`, "scene-meta"));
    return element;
  }

  for (const scene of scenes.filter(s => s.coordinates)) {
    const pin = L.marker(project(scene.coordinates), {
      title: scene.title, alt: scene.title,
      icon: L.divIcon({className: `scene-pin ${scene.renderer !== "sketchfab" ? "local" : scene.kind === "detail" ? "detail" : ""}`, html: "3D", iconSize: [28, 28], iconAnchor: [14, 14]}),
      zIndexOffset: scene.renderer === "sketchfab" ? 0 : 1000,
    }).bindPopup(() => card(scene, true), {maxWidth: 320});
    pin.addTo(markers);
    pins.set(scene.id, pin);
  }

  function fit() {
    const points = scenes.filter(s => s.coordinates).map(s => project(s.coordinates));
    if (!points.length) return;
    const bounds = L.latLngBounds(points).pad(.12);
    if (terrain?.active) terrain.focusAtXY(bounds.getCenter().lng, bounds.getCenter().lat,
      Math.max(bounds.getNorth() - bounds.getSouth(), (bounds.getEast() - bounds.getWest()) / (container.clientWidth / container.clientHeight)));
    else map.fitBounds(bounds, {maxZoom: 4});
  }
  $("#sceneFit").onclick = fit;
  const terrainLayer = document.createElement("div");
  terrainLayer.className = "scene-terrain-layer";
  terrainLayer.hidden = true;
  terrainLayer.setAttribute("aria-label", "Reconstrucciones sobre el relieve");
  container.append(terrainLayer);
  const terrainPins = scenes.filter(s => s.coordinates).map(scene => {
    const button = textNode("button", "3D", `scene-pin scene-terrain-pin ${scene.renderer !== "sketchfab" ? "local" : scene.kind === "detail" ? "detail" : ""}`);
    button.dataset.id = scene.id;
    button.title = `${scene.title} · ${scene.anchor}`;
    button.setAttribute("aria-label", `Abrir reconstrucción: ${scene.title}`);
    button.onclick = () => open(scene);
    button.hidden = true;
    button.disabled = !scene.available;
    terrainLayer.append(button);
    return {scene, button};
  });
  function setVisible(on) {
    $("#sceneMarkers").checked = on;
    if (on) markers.addTo(map); else map.removeLayer(markers);
    updateTerrainPins();
  }
  function updateTerrainPins() {
    map.getContainer().inert = !!terrain?.active;
    terrainLayer.hidden = !terrain?.active || !$("#sceneMarkers").checked;
    if (terrainLayer.hidden) return;
    for (const {scene, button} of terrainPins) {
      const point = terrain.projectPoint(scene.coordinates);
      button.hidden = !point;
      if (point) button.style.transform = `translate(${point.x}px,${point.y}px) translate(-50%,-50%)`;
    }
  }
  terrain?.on(type => { if (["frame", "exit", "entered"].includes(type)) updateTerrainPins(); });
  $("#sceneMarkers").onchange = event => setVisible(event.target.checked);
  $("#sceneRoute").onchange = async event => {
    routeRequested = event.target.checked;
    if (routeRequested && !route) {
      try {
        const response = await fetch("/api/traverse");
        if (!response.ok) throw new Error("No se pudo cargar el recorrido.");
        const data = await response.json();
        route = L.polyline(data.geometry.coordinates.map(project), {color: "#e8bc75", weight: 2, opacity: .75, interactive: false});
      } catch (error) { $("#sceneStatus").textContent = error.message; event.target.checked = false; return; }
    }
    if (route) routeRequested ? route.addTo(map) : map.removeLayer(route);
  };
  const featured = scenes.find(s => s.id === "cheyava-falls" && s.available);
  $("#sceneFeatured").disabled = !featured;
  $("#sceneFeatured").onclick = () => open(featured);

  function render() {
    const query = $("#sceneSearch").value.trim().toLocaleLowerCase("es"), filter = $("#sceneFilter").value;
    const visible = scenes.filter(s => {
      const matches = `${s.title} ${s.author} ${s.sol ?? ""}`.toLocaleLowerCase("es").includes(query);
      return matches && (filter === "all" || filter === "placed" && s.coordinates || filter === "unplaced" && !s.coordinates
        || filter === "local" && s.renderer !== "sketchfab" || filter === s.kind);
    });
    $("#sceneList").replaceChildren(...visible.map(s => card(s)));
    if (!visible.length) $("#sceneList").append(textNode("p", "No hay reconstrucciones para esta búsqueda.", "muted"));
    $("#sceneStatus").textContent = catalog.warnings.length ? catalog.warnings.join(" ")
      : `${catalog.counts.placed} puntos en el mapa · ${catalog.counts.local} modelos locales · ${visible.length} de ${scenes.length} en el catálogo`;
  }
  $("#sceneSearch").oninput = render;
  $("#sceneFilter").onchange = render;
  render();
  if (fitOnLoad) fit();
  return {catalog, open, fit, setVisible};
}
