/** Mission panel: text → POST /parse-mission (local LLM) → POST /plan-route (planner) → map + report → POST /summarize-route. */

const TARGET_LABELS = {aqueous: "water evidence", carbonates: "carbonates", clays: "clays", smectites: "smectites",
  kaolinite: "kaolinite", olivine: "olivine", pyroxene: "pyroxene", delta: "delta sediments", crater_floor: "crater floor"};
const EXAMPLE = "Two astronauts leave the landing site for the top of the delta to look for carbonates. "
  + "We carry fragile sample tubes, so be careful, and we must be back before dark.";

const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"})[c]);
const num = (value, digits = 1) => (value === null || value === undefined || Number.isNaN(+value)) ? "—" : (+value).toFixed(digits);

async function postJSON(url, body) {
  const response = await fetch(url, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray(data.detail) ? data.detail.map(d => `${d.loc?.at(-1)}: ${d.msg}`).join("; ") : data.detail;
    throw new Error(detail || `HTTP ${response.status}`);
  }
  return data;
}

/** Fills the mission request from the LLM output, letting the panel's origin/destination choices win. */
export function mergeMission(parsed, {origin, destination}) {
  const mission = {...parsed};
  if (origin) mission.origin = origin;
  if (destination) mission.destination = destination;
  const missing = ["origin", "destination"].filter(key => !mission[key]);
  return {mission, missing};
}

export function reportHTML(report) {
  const r = report.route || {}, c = report.comparison || {}, sun = report.sun || {};
  const warnings = [...(report.warnings || [])].sort((a, b) => (b.severity === "critical") - (a.severity === "critical"));
  const gained = Object.entries(c).filter(([k, v]) => k.startsWith("on_") && v > 0)
    .map(([k, v]) => `<li><b>+${num(v, 2)} km</b> over ${esc(TARGET_LABELS[k.slice(3, -10)] || k.slice(3, -10))}</li>`);
  const saved = [
    c.energy_saved_pct > 0 && `<li><b>${num(c.energy_saved_pct, 0)} %</b> less energy</li>`,
    c.time_saved_pct > 0 && `<li><b>${num(c.time_saved_pct, 0)} %</b> less time</li>`,
    c.max_pitch_reduction_deg > 0 && `<li><b>${num(c.max_pitch_reduction_deg)}°</b> gentler max slope</li>`,
    c.max_cross_slope_reduction_deg > 0 && `<li><b>${num(c.max_cross_slope_reduction_deg)}°</b> less cross slope</li>`,
    c.dunes_km_avoided > 0 && `<li><b>${num(c.dunes_km_avoided, 2)} km</b> of dunes avoided</li>`,
    c.soft_km_avoided > 0 && `<li><b>${num(c.soft_km_avoided, 2)} km</b> of soft ground avoided</li>`,
    c.shadow_km_avoided > 0 && `<li><b>${num(c.shadow_km_avoided, 2)} km</b> of shadow avoided</li>`,
  ].filter(Boolean).concat(gained);
  const charging = r.charging_stop;
  return `
    <div class="verdict ${report.feasible ? "ok" : "bad"}">${report.feasible ? "Feasible route" : "Not feasible as planned"}</div>
    ${warnings.length ? `<ul class="warnings">${warnings.map(w => `<li class="${esc(w.severity)}">${esc(w.message)}</li>`).join("")}</ul>` : ""}
    <dl class="figures">
      <div><dt>Distance</dt><dd>${num(r.distance_km)} km</dd></div>
      <div><dt>Duration</dt><dd>${num(r.duration_h ?? r.time_h)} h</dd></div>
      <div><dt>Departure → arrival</dt><dd>${esc(r.departure)} → ${esc(r.arrival)}</dd></div>
      <div><dt>Daylight limit</dt><dd>${esc(sun.daylight_limit || "—")}</dd></div>
      <div><dt>Battery on arrival</dt><dd>${num(r.battery_end_pct, 0)} %</dd></div>
      <div><dt>Ascent / max slope</dt><dd>${num(r.ascent_m, 0)} m · ${num(r.max_pitch_deg)}°</dd></div>
    </dl>
    ${saved.length ? `<h3>Versus a shortest-path A*</h3><ul class="gains">${saved.join("")}</ul>` : ""}
    ${(r.science_stops || []).length ? `<p class="muted">${r.science_stops.length} science stop(s) on the way.</p>` : ""}
    ${charging ? `<p class="muted">Charging stop at ${esc(charging.arrive)} for ${num(charging.charge_hours)} h.</p>` : ""}`;
}

function missionChips(mission) {
  const chips = [
    mission.human ? "crewed" : "uncrewed",
    `safety ${mission.safety}`,
    mission.power && "save power",
    mission.route_preference,
    ...(mission.science_targets || []).map(t => `${TARGET_LABELS[t.target] || t.target}${t.priority < 1 ? ` (${t.priority})` : ""}`),
    mission.science_targets?.length && `detour ${mission.science_detour}`,
    mission.return_to_origin && "round trip",
  ].filter(Boolean);
  return `<div class="route-ends"><span>${esc(mission.origin || "?")}</span> → <span>${esc(mission.destination || "?")}</span></div>
    <div class="chips">${chips.map(c => `<span class="chip">${esc(c)}</span>`).join("")}</div>`;
}

export async function initMission({map, cfg, panel, routeView}) {
  panel.innerHTML = `
    <h2>Plan an excursion</h2>
    <label for="missionText" class="muted">Describe the mission. The local LLM turns it into planner parameters.</label>
    <textarea id="missionText" rows="5">${esc(EXAMPLE)}</textarea>
    <div class="ends">
      ${["origin", "destination"].map(key => `
        <label class="end"><span>${key === "origin" ? "Origin" : "Destination"}</span>
          <select id="${key}Select"><option value="">From the text</option></select>
          <button type="button" id="${key}Pick" title="Pick ${key} on the map" aria-label="Pick ${key} on the map">⌖</button>
        </label>`).join("")}
    </div>
    <details class="system"><summary>Vehicle state</summary>
      <label>Departure (local solar time, h)<input id="startHour" type="number" min="0" max="23.9" step="0.5" value="9"></label>
      <label>Battery (kWh)<input id="batteryKwh" type="number" min="0" step="1" value="30"></label>
      <label>Capacity (kWh)<input id="batteryCap" type="number" min="1" step="1" value="40"></label>
      <label>Reserve on arrival (%)<input id="reservePct" type="number" min="0" max="100" step="5" value="20"></label>
    </details>
    <button id="planBtn" class="primary">Plan route</button>
    <div id="missionStatus" role="status" aria-live="polite"></div>
    <div id="missionParams"></div>
    <div id="missionSummary" aria-live="polite"></div>
    <div id="missionReport"></div>`;
  const $ = selector => panel.querySelector(selector);
  const k = Math.PI * cfg.radius / 180;
  const toLatLng = ([lon, lat]) => L.latLng(lat * k, lon * k);
  const state = {picking: null, markers: {}};

  try {
    const {places} = await fetch("/api/places").then(r => r.json());
    for (const key of ["origin", "destination"]) {
      $(`#${key}Select`).append(...Object.keys(places).map(name => new Option(name.replaceAll("_", " "), name)));
    }
  } catch (error) {
    $("#missionStatus").textContent = `Place list unavailable: ${error.message}`;
  }

  function setPoint(key, value, lonlat) {
    state.markers[key]?.remove();
    delete state.markers[key];
    const select = $(`#${key}Select`);
    if (lonlat) {
      select.querySelector("option[data-map]")?.remove();
      const option = new Option(`map ${lonlat[1].toFixed(4)}N ${lonlat[0].toFixed(4)}E`, value);
      option.dataset.map = "1";
      select.append(option);
      state.markers[key] = L.circleMarker(toLatLng(lonlat), {radius: 7, weight: 2, color: "#fff", fillOpacity: 1,
        fillColor: key === "origin" ? "#5fd38a" : "#ff5a5a", pane: "vectorPane"}).addTo(map);
    }
    select.value = value;
  }
  for (const key of ["origin", "destination"]) {
    $(`#${key}Pick`).onclick = () => {
      state.picking = state.picking === key ? null : key;
      panel.querySelectorAll(".end button").forEach(b => b.classList.toggle("active", b.id === `${state.picking}Pick`));
      map.getContainer().style.cursor = state.picking ? "crosshair" : "";
      $("#missionStatus").textContent = state.picking ? `Click the map to set the ${key}.` : "";
    };
    $(`#${key}Select`).onchange = e => { if (!e.target.selectedOptions[0]?.dataset.map) setPoint(key, e.target.value); };
  }
  map.on("click", e => {
    if (!state.picking) return;
    const lonlat = [e.latlng.lng / k, e.latlng.lat / k];
    setPoint(state.picking, `${lonlat[0].toFixed(5)},${lonlat[1].toFixed(5)}`, lonlat);
    $(`#${state.picking}Pick`).click();
  });

  const system = () => ({start_hour: +$("#startHour").value, battery_kwh: +$("#batteryKwh").value,
    battery_capacity_kwh: +$("#batteryCap").value, reserve_pct: +$("#reservePct").value});

  async function plan() {
    const status = $("#missionStatus"), button = $("#planBtn");
    button.disabled = true;
    for (const id of ["#missionParams", "#missionSummary", "#missionReport"]) $(id).replaceChildren();
    panel.classList.remove("error");
    try {
      status.textContent = "Reading the mission with the local LLM…";
      const parsed = await postJSON("/api/parse-mission", {prompt: $("#missionText").value});
      const {mission, missing} = mergeMission(parsed, {origin: $("#originSelect").value, destination: $("#destinationSelect").value});
      $("#missionParams").innerHTML = missionChips(mission);
      if (missing.length) throw new Error(`The text does not name the ${missing.join(" or ")}. Choose it above or pick it on the map.`);
      status.textContent = mission.science_targets.length ? "Planning the route (science stops take 10–20 s)…" : "Planning the route…";
      const result = await postJSON("/api/plan-route", {mission, system: system()});
      if (result.geojson.features.length) { routeView.setRoute(result); routeView.fitRoute(); }
      $("#missionReport").innerHTML = reportHTML(result.report);
      status.textContent = "Writing the briefing…";
      try {
        const {summary} = await postJSON("/api/summarize-route", {report: result.report});
        $("#missionSummary").innerHTML = `<blockquote>${esc(summary)}</blockquote>`;
        status.textContent = "";
      } catch (error) {
        status.textContent = `Route ready; the briefing failed: ${error.message}`;
      }
    } catch (error) {
      panel.classList.add("error");
      status.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  }
  $("#planBtn").onclick = plan;
  return {isPicking: () => Boolean(state.picking), plan};
}
