import { Terrain3D, leafletView } from "./terrain3d/terrain3d.mjs";

const COLORS = {route: "#ffb347", classic_astar: "#9fd3ff", origin: "#5fd38a", destination: "#ff5a5a"};

/** Shared route/relief controls for the main map and the existing styled route demo. */
export async function initRouteView({map, cfg, container, routeUrl = "/terrain3d/demo_route.json"}) {
  container.classList.add("route-map");
  container.insertAdjacentHTML("beforeend", `
    <section id="tools" class="route-card" aria-label="Route and relief">
      <button id="btn3d" aria-pressed="false" disabled>3D</button>
      <button id="routeFit">Frame route</button>
      <div class="route-legend"><span id="routeKind">Example route</span><br>
        <span class="key" style="background:#ffb347"></span>planned ·
        <span class="key" style="background:#9fd3ff"></span>A*</div>
      <label class="only3d">Vertical exaggeration <span id="exv">×3</span>
        <input id="ex" type="range" min="1" max="8" step=".5" value="3"></label>
      <label class="only3d">Relief source<select id="src"></select></label>
      <button id="replay" class="only3d">Replay route</button>
      <div id="status" role="status"></div>
    </section>
    <section id="profile" class="route-card" aria-label="Route elevation profile">
      <div class="h"><span>Elevation along the route</span><span id="pinfo"></span></div>
      <svg id="psvg" preserveAspectRatio="none"></svg>
    </section>`);
  const $ = selector => container.querySelector(selector);
  const t3d = new Terrain3D(container, {exaggeration: 3});
  const project = c => L.latLng(cfg.radius * c[1] * Math.PI / 180, cfg.radius * c[0] * Math.PI / 180);
  let routeLayer, busy = false, prof = [], sourceLoaded = "";

  function setRoute(plan, {example = false} = {}) {
    if (routeLayer) map.removeLayer(routeLayer);
    routeLayer = L.geoJSON(plan.geojson || plan, {
      coordsToLatLng: project,
      style: f => ({color: COLORS[f.properties.kind] || "#ffe066", weight: f.properties.kind === "route" ? 4 : 2,
        dashArray: f.properties.kind === "classic_astar" ? "6 5" : null}),
      pointToLayer: (f, p) => L.circleMarker(p, {radius: 6, weight: 2, color: "#fff", fillOpacity: 1, fillColor: COLORS[f.properties.kind] || "#ffe066"}),
    }).addTo(map);
    t3d.setRoute(plan);
    $("#routeKind").textContent = example ? "Example route" : "Planned route";
    if (t3d.active) drawProfile();
    container.dataset.routeReady = "true";
  }
  function fitRoute() {
    if (!routeLayer?.getBounds().isValid()) return;
    const b = routeLayer.getBounds();
    if (t3d.active) t3d.focusAtXY(b.getCenter().lng, b.getCenter().lat, Math.max(b.getNorth() - b.getSouth(), (b.getEast() - b.getWest()) / (container.clientWidth / container.clientHeight)) * 1.35);
    else map.fitBounds(b, {padding: [60, 60], maxZoom: 6, animate: false});
  }
  $("#routeFit").onclick = fitRoute;

  async function loadRelief(url) {
    $("#status").textContent = "Loading relief…";
    const meta = await t3d.load(url);
    if (!meta) return null;
    sourceLoaded = url;
    drawProfile();
    $("#status").textContent = meta.fit ? `STL: r = ${meta.fit.corr.toFixed(3)}, RMSE ${meta.fit.rmse_m.toFixed(0)} m` : "CTX DTM";
    return meta;
  }
  const btn = $("#btn3d");
  btn.onclick = async () => {
    if (busy) return;
    busy = true; btn.disabled = true; $("#src").disabled = true;
    try {
      if (!t3d.active) {
        if (sourceLoaded !== $("#src").value && !await loadRelief($("#src").value)) return;
        container.classList.add("is3d");
        btn.setAttribute("aria-pressed", "true"); btn.textContent = "2D";
        drawProfile();
        await t3d.enter(leafletView(map, p => [p.lng, p.lat]));
      } else {
        const view = await t3d.exit();
        if (view) map.fitBounds(L.latLngBounds(
          [view.y - view.height / 2, view.x - view.height * (container.clientWidth / container.clientHeight) / 2],
          [view.y + view.height / 2, view.x + view.height * (container.clientWidth / container.clientHeight) / 2]), {animate: false});
        container.classList.remove("is3d");
        btn.setAttribute("aria-pressed", "false"); btn.textContent = "3D";
      }
    } catch (error) {
      $("#status").textContent = `Relief unavailable: ${error.message}`;
      if (t3d.active) await t3d.exit();
      container.classList.remove("is3d"); btn.setAttribute("aria-pressed", "false"); btn.textContent = "3D";
    } finally { busy = false; btn.disabled = false; $("#src").disabled = false; }
  };
  $("#ex").oninput = e => { $("#exv").textContent = `×${e.target.value}`; t3d.setExaggeration(+e.target.value); };
  $("#replay").onclick = () => t3d.replayRoute();
  $("#src").onchange = async e => {
    // Serialize relief changes with mode transitions and preserve the existing route/camera.
    if (busy) return;
    busy = true; btn.disabled = true; $("#src").disabled = true;
    try { if (await loadRelief(e.target.value)) await t3d.replayRoute(); }
    catch (error) { $("#status").textContent = error.message; $("#src").value = sourceLoaded; }
    finally { busy = false; btn.disabled = false; $("#src").disabled = false; }
  };
  function drawProfile() {
    prof = t3d.routeProfile();
    const svg = $("#psvg");
    if (!prof.length) { svg.replaceChildren(); return; }
    const W = 1000, H = 88, total = prof.at(-1).d;
    const hs = prof.map(p => p.h), lo = Math.min(...hs), hi = Math.max(...hs), span = Math.max(hi - lo, 1);
    const pts = prof.map(p => `${(p.d / Math.max(total, 1) * W).toFixed(1)},${(H - 6 - (p.h - lo) / span * (H - 14)).toFixed(1)}`).join(" ");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.innerHTML = `<polygon points="0,${H} ${pts} ${W},${H}" fill="rgba(255,179,71,.14)"/><polyline points="${pts}" fill="none" stroke="#ffb347" stroke-width="2" vector-effect="non-scaling-stroke"/><line id="pcur" x1="0" x2="0" y1="0" y2="${H}" stroke="#fff"/>`;
    $("#pinfo").textContent = `${(total / 1000).toFixed(1)} km · ${lo.toFixed(0)}–${hi.toFixed(0)} m`;
  }
  t3d.on((type, fraction) => {
    if (type !== "route") return;
    const cursor = $("#pcur");
    if (cursor) for (const attr of ["x1", "x2"]) cursor.setAttribute(attr, fraction * 1000);
  });
  try {
    const response = await fetch(routeUrl);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    setRoute(await response.json(), {example: true}); fitRoute();
  } catch (error) { $("#status").textContent = `Route unavailable: ${error.message}`; }
  try {
    const response = await fetch("/api/terrain-sources");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const {sources} = await response.json();
    $("#src").replaceChildren(...sources.map(source => new Option(source.title, source.url)));
    btn.disabled = !sources.length;
    if (!sources.length) {
      btn.textContent = "3D relief not prepared";
      $("#status").textContent = "The 2D map and surface reconstructions are available.";
    }
  } catch (error) { $("#status").textContent = error.message; }
  window.addEventListener("pagehide", () => t3d.dispose(), {once: true});
  container.addEventListener("marps:plan-route", event => setRoute(event.detail));
  return {terrain: t3d, setRoute, fitRoute, getRouteLayer: () => routeLayer};
}
