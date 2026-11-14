const $ = selector => document.querySelector(selector);
const labels = {landscape: "Escena de superficie", detail: "Detalle de roca", aerial: "Vista aérea"};
const textNode = (tag, value, className) => {
  const element = document.createElement(tag);
  element.textContent = value;
  if (className) element.className = className;
  return element;
};

export async function initReconstructions({map, cfg}) {
  const response = await fetch("/api/reconstructions");
  if (!response.ok) throw new Error("No se pudo cargar el catálogo 3D. Inicia el visor con python3 backend/viewer.py.");
  const catalog = await response.json(), scenes = catalog.scenes;
  const k = Math.PI * cfg.radius / 180;
  const project = coords => L.latLng(coords[1] * k, coords[0] * k);
  const markers = L.layerGroup().addTo(map), pins = new Map();
  const dialog = $("#surfaceDialog");
  let previousFocus, route, routeRequested = false;

  function close() {
    dialog.close();
  }
  dialog.addEventListener("close", () => {
    $("#surfaceViewport").replaceChildren(); // destruye WebGL, workers y descargas del iframe
    previousFocus?.focus();
    map.invalidateSize();
  });
  $("#surfaceClose").onclick = close;

  function open(scene) {
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
    } else frame.src = `surface.html?id=${encodeURIComponent(scene.id)}`;
    $("#surfaceViewport").replaceChildren(frame);
    dialog.showModal();
    $("#surfaceClose").focus();
  }
  // Escape funciona también cuando el foco está en nuestro iframe WebGL.
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
        $("#sceneMarkers").checked = true;
        markers.addTo(map);
        map.setView(project(scene.coordinates), 6);
        pins.get(scene.id)?.openPopup();
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
    if (points.length) map.fitBounds(L.latLngBounds(points).pad(.12), {maxZoom: 4});
  }
  $("#sceneFit").onclick = fit;
  $("#sceneMarkers").onchange = event => event.target.checked ? markers.addTo(map) : map.removeLayer(markers);
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
  fit();
}
