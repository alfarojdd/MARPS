const $ = selector => document.querySelector(selector);
const labels = {landscape: "Surface scene", detail: "Rock detail", aerial: "Aerial view"};
const textNode = (tag, value, className) => {
  const element = document.createElement(tag);
  element.textContent = value;
  if (className) element.className = className;
  return element;
};

/** Compact catalogue for the existing floating-card route map. The main viewer already has a sidebar. */
export function mountReconstructionPanel(container) {
  container.insertAdjacentHTML("beforeend", `<details class="route-card reconstruction-panel">
    <summary>3D reconstructions</summary>
    <section id="reconstructions" aria-label="3D reconstructions">
      <p class="muted">Select a 3D point to explore the surface.</p>
      <div id="sceneStatus" role="status">Loading catalogue…</div>
      <div class="scene-actions"><button id="sceneFit">Show 3D points</button><button id="sceneFeatured" disabled>Enter Cheyava Falls</button></div>
      <label class="row"><input id="sceneMarkers" type="checkbox" checked>Show 3D points</label>
      <label class="row"><input id="sceneRoute" type="checkbox">Perseverance traverse</label>
      <input id="sceneSearch" type="search" placeholder="Search by place, author or sol…" aria-label="Search reconstructions">
      <select id="sceneFilter" aria-label="Filter reconstructions">
        <option value="placed">Placed on the map</option><option value="local">Local 3D files</option>
        <option value="landscape">Scenes and outcrops</option><option value="detail">Rock details</option>
        <option value="unplaced">No verified location</option><option value="all">Entire catalogue</option>
      </select>
      <div id="sceneList" aria-label="Reconstruction catalogue"></div>
      <p class="muted scene-note">Approximate anchors; they do not delimit the 3D coverage. The planned route is preserved when entering and leaving a scene.</p>
    </section>
  </details>`);
}

export async function initReconstructions({map, cfg, terrain = null, container = map.getContainer().parentElement, fitOnLoad = true}) {
  const response = await fetch("/api/reconstructions");
  if (!response.ok) throw new Error("Could not load the 3D catalogue. Start the server with python3 backend/app.py.");
  const catalog = await response.json(), scenes = catalog.scenes;
  const k = Math.PI * cfg.radius / 180;
  const project = coords => L.latLng(coords[1] * k, coords[0] * k);
  const markers = L.layerGroup().addTo(map), pins = new Map();
  if (!$("#surfaceDialog")) document.body.insertAdjacentHTML("beforeend", `<dialog id="surfaceDialog" aria-labelledby="surfaceTitle">
    <header><div><strong id="surfaceTitle"></strong><div id="surfaceByline" class="muted"></div></div><button id="surfaceClose">Back to map ×</button></header>
    <div id="surfaceViewport"></div>
    <footer><span id="surfaceNote"></span><a id="surfaceSource" target="_blank" rel="noopener noreferrer">Original source ↗</a></footer>
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
      ? `${scene.anchor} · External viewer: use Sketchfab first-person mode. Scale depends on the model; details and aerial views open in orbit mode.`
      : scene.description;
    $("#surfaceSource").href = scene.source;
    const frame = document.createElement("iframe");
    frame.title = `3D reconstruction: ${scene.title}`;
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
    element.append(textNode("div", `${scene.renderer === "sketchfab" ? "Sketchfab" : "Local file"} · ${scene.sol == null ? "Sol not specified" : `Sol ${scene.sol}${scene.solEnd ? `–${scene.solEnd}` : ""}`} · ${labels[scene.kind]}`, "scene-meta"));
    if (!scene.coordinates) element.append(textNode("div", "No verified location: available in the catalogue only.", "scene-meta"));
    const enter = textNode("button", scene.kind === "landscape" ? "Enter the reconstruction" : "View 3D model", "scene-enter");
    enter.disabled = !scene.available;
    if (!scene.available) enter.textContent = "Local file missing";
    enter.onclick = () => open(scene);
    element.append(enter);
    if (scene.coordinates && !popup) {
      const locate = textNode("button", "Show on map");
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
  terrainLayer.setAttribute("aria-label", "Reconstructions over the relief");
  container.append(terrainLayer);
  const terrainPins = scenes.filter(s => s.coordinates).map(scene => {
    const button = textNode("button", "3D", `scene-pin scene-terrain-pin ${scene.renderer !== "sketchfab" ? "local" : scene.kind === "detail" ? "detail" : ""}`);
    button.dataset.id = scene.id;
    button.title = `${scene.title} · ${scene.anchor}`;
    button.setAttribute("aria-label", `Open reconstruction: ${scene.title}`);
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
        if (!response.ok) throw new Error("Could not load the traverse.");
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
    const query = $("#sceneSearch").value.trim().toLocaleLowerCase("en"), filter = $("#sceneFilter").value;
    const visible = scenes.filter(s => {
      const matches = `${s.title} ${s.author} ${s.sol ?? ""}`.toLocaleLowerCase("en").includes(query);
      return matches && (filter === "all" || filter === "placed" && s.coordinates || filter === "unplaced" && !s.coordinates
        || filter === "local" && s.renderer !== "sketchfab" || filter === s.kind);
    });
    $("#sceneList").replaceChildren(...visible.map(s => card(s)));
    if (!visible.length) $("#sceneList").append(textNode("p", "No reconstructions match this search.", "muted"));
    $("#sceneStatus").textContent = catalog.warnings.length ? catalog.warnings.join(" ")
      : `${catalog.counts.placed} points on the map · ${catalog.counts.local} local models · ${visible.length} of ${scenes.length} in the catalogue`;
  }
  $("#sceneSearch").oninput = render;
  $("#sceneFilter").onchange = render;
  render();
  if (fitOnLoad) fit();
  return {catalog, open, fit, setVisible};
}
