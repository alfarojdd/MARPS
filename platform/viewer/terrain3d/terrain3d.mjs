// Tilted 3D view of the relief with the route on top. It overlays the 2D map (Leaflet) and animates the
// transition: top-down -> tilted, with the relief "growing" and the route being drawn over it.
//
// Coordinates: Mars equirectangular metres (x = R·lon·π/180, y = R·lat·π/180, R = 3 396 190 m), the same
// as the map viewer and the planner. Three.js scene: X = east, Y = height, Z = south.
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { Line2 } from "three/addons/lines/Line2.js";
import { LineGeometry } from "three/addons/lines/LineGeometry.js";
import { LineMaterial } from "three/addons/lines/LineMaterial.js";

const DEG = Math.PI / 180;
const ease = t => (t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const lerp = (a, b, t) => a + (b - a) * t;

const DEFAULTS = {
  exaggeration: 3,    // vertical exaggeration in the tilted view (the real Jezero relief is gentle)
  pitch: 58,          // final tilt in degrees (0 = top-down)
  bearing: -25,       // final bearing in degrees relative to north
  fov: 35,
  enterMs: 1800,
  exitMs: 1200,
  routeMs: 3000,      // duration of the progressive route drawing
  lift: 12,           // metres above ground where the route floats (before exaggeration)
  colors: { route: 0xffb347, classic: 0x9fd3ff, origin: 0x5fd38a, destination: 0xff5a5a, stop: 0xffe066 },
};

export class Terrain3D {
  constructor(container, options = {}) {
    this.container = container;
    this.opt = { ...DEFAULTS, ...options, colors: { ...DEFAULTS.colors, ...options.colors } };
    this.active = false;
    this._raf = 0;
    this._tweens = [];
    this._listeners = new Set();
    this._gen = 0;
    this._paused = false;
  }

  // ---------- loading
  async load(terrainUrl) {
    const req = this._loadSeq = (this._loadSeq || 0) + 1;
    const meta = await fetchJSON(terrainUrl);
    const base = new URL(terrainUrl, location.href);
    const buf = await fetchBuffer(new URL(meta.heights, base));
    const heights = new Float32Array(buf);
    if (heights.length !== meta.width * meta.height) throw new Error(`${meta.heights}: unexpected size`);
    const texture = meta.texture ? await new THREE.TextureLoader().loadAsync(new URL(meta.texture, base).href) : null;
    if (req !== this._loadSeq) { texture?.dispose(); return null; }  // a newer request arrived
    this._buildScene();
    this._baseTextureUrl = meta.texture ? new URL(meta.texture, base).href : null;
    this.setTerrain(meta, heights, texture);
    return meta;
  }

  setTerrain(meta, heights, texture) {
    const b = meta.bounds;
    this.meta = meta;
    this.heights = heights;
    this.R = meta.radius || 3396190;
    this.cx = (b.left + b.right) / 2;
    this.cy = (b.top + b.bottom) / 2;
    this.sizeX = b.right - b.left;
    this.sizeY = b.top - b.bottom;
    this.h0 = meta.min;

    if (this.terrain) { this.world.remove(this.terrain); disposeTree(this.terrain); }
    const g = new THREE.PlaneGeometry(this.sizeX, this.sizeY, meta.width - 1, meta.height - 1);
    g.rotateX(-Math.PI / 2);  // plane row 0 = north (−Z), same as heightmap row 0
    const pos = g.attributes.position;
    for (let i = 0; i < pos.count; i++) pos.setY(i, heights[i] - this.h0);
    g.computeVertexNormals();
    if (texture) { texture.colorSpace = THREE.SRGBColorSpace; texture.anisotropy = this.renderer.capabilities.getMaxAnisotropy(); }
    const mat = new THREE.MeshStandardMaterial({
      map: texture, color: texture ? 0xffffff : 0xc08a64, roughness: 1, metalness: 0,
      polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1,
    });
    this.terrain = new THREE.Mesh(g, mat);
    this.world.add(this.terrain);
    if (this._routeData) this.setRoute(this._routeData);
  }

  /**
   * Re-textures the relief: a basemap image (default: the terrain's own texture) with an optional data layer
   * composited on top. Both images must cover the same bounds as the relief (north up).
   * options = {baseUrl, overlayUrl, opacity, pixelated}
   */
  async setTextureLayers({ baseUrl = null, overlayUrl = null, opacity = 0.7, pixelated = false } = {}) {
    if (!this.terrain) return;
    const token = this._texSeq = (this._texSeq || 0) + 1;
    const loadImage = url => new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error(`${url}: could not load`));
      img.src = url;
    });
    const baseSrc = baseUrl || this._baseTextureUrl;
    if (!baseSrc) return;
    const [base, overlay] = await Promise.all([loadImage(baseSrc), overlayUrl ? loadImage(overlayUrl) : null]);
    if (token !== this._texSeq || !this.terrain) return;  // a newer request arrived or the relief changed
    const w = Math.min(base.width, 2048), h = Math.round(w * base.height / base.width);
    const canvas = document.createElement("canvas");
    canvas.width = w; canvas.height = h;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(base, 0, 0, w, h);
    if (overlay) {
      ctx.globalAlpha = opacity;
      ctx.imageSmoothingEnabled = !pixelated;
      ctx.drawImage(overlay, 0, 0, w, h);
    }
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.anisotropy = this.renderer.capabilities.getMaxAnisotropy();
    const material = this.terrain.material;
    material.map?.dispose();
    material.map = texture;
    material.color.set(0xffffff);
    material.needsUpdate = true;
  }

  _buildScene() {
    if (this.renderer) return;
    const r = this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    r.setPixelRatio(Math.min(devicePixelRatio, 2));
    r.outputColorSpace = THREE.SRGBColorSpace;
    const el = r.domElement;
    el.className = "terrain3d-canvas";
    Object.assign(el.style, { position: "absolute", inset: "0", width: "100%", height: "100%",
      opacity: "0", pointerEvents: "none", transition: "opacity .35s ease", zIndex: "900" });
    this.container.appendChild(el);

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x14100e);
    this.scene.fog = new THREE.Fog(0x14100e, 1, 1);
    this.world = new THREE.Group();
    this.scene.add(this.world);
    this.scene.add(new THREE.HemisphereLight(0xfff1e0, 0x2a1a12, 1.1));
    const sun = new THREE.DirectionalLight(0xffe2c4, 2.2);
    sun.position.set(-1, .55, -.6);  // low sun from the north-west to bring out the relief
    this.scene.add(sun);

    this.camera = new THREE.PerspectiveCamera(this.opt.fov, 1, 5, 400000);
    this.controls = new OrbitControls(this.camera, el);
    Object.assign(this.controls, { enableDamping: true, dampingFactor: .08, maxPolarAngle: 80 * DEG,
      screenSpacePanning: false, minDistance: 300, enabled: false });
    this._resize = () => {
      const { clientWidth: w, clientHeight: h } = this.container;
      if (!w || !h) return;
      r.setSize(w, h, false);
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
      for (const m of this._lineMaterials()) m.resolution.set(w, h);
    };
    this._ro = new ResizeObserver(this._resize);
    this._ro.observe(this.container);
    this._resize();
  }

  // ---------- coordinate conversion
  lonLatToXY(lon, lat) { return [this.R * lon * DEG, this.R * lat * DEG]; }
  xyToLonLat(x, y) { return [x / (this.R * DEG), y / (this.R * DEG)]; }

  /** Height (m) interpolated at equirectangular coordinates; null outside the relief. */
  heightAtXY(x, y) {
    const { width: w, height: h, bounds: b } = this.meta;
    const fc = (x - b.left) / this.sizeX * (w - 1);
    const fr = (b.top - y) / this.sizeY * (h - 1);
    if (fc < 0 || fr < 0 || fc > w - 1 || fr > h - 1) return null;
    const c0 = Math.min(Math.floor(fc), w - 2), r0 = Math.min(Math.floor(fr), h - 2);
    const tc = fc - c0, tr = fr - r0, H = this.heights, i = r0 * w + c0;
    return lerp(lerp(H[i], H[i + 1], tc), lerp(H[i + w], H[i + w + 1], tc), tr);
  }
  heightAt(lon, lat) { return this.heightAtXY(...this.lonLatToXY(lon, lat)); }

  _toScene(x, y, h, out = new THREE.Vector3()) { return out.set(x - this.cx, h - this.h0, this.cy - y); }

  /** Screen anchor for a surface reconstruction; null outside the relief/frustum or behind terrain. */
  projectPoint([lon, lat]) {
    if (!this.active || !this.meta || !this.camera) return null;
    const [x, y] = this.lonLatToXY(lon, lat), height = this.heightAtXY(x, y);
    if (height === null) return null;
    const point = this._toScene(x, y, height);
    point.y = point.y * this.world.scale.y + 60;
    const projected = point.clone().project(this.camera);
    if (projected.z < -1 || projected.z > 1 || Math.abs(projected.x) > 1 || Math.abs(projected.y) > 1) return null;
    // Approximate terrain visibility without raycasting the entire high-resolution mesh each frame.
    for (let i = 1; i < 16; i++) {
      const p = point.clone().lerp(this.camera.position, i / 16);
      const ground = this.heightAtXY(p.x + this.cx, this.cy - p.z);
      if (ground !== null && (ground - this.h0) * this.world.scale.y > p.y + 20) return null;
    }
    return {x: (projected.x + 1) / 2 * this.container.clientWidth,
      y: (1 - projected.y) / 2 * this.container.clientHeight};
  }

  /** Centre a catalogue location or route while keeping the tilted map active. */
  focusAtXY(x, y, visibleHeight = 1500) {
    if (!this.active || !this.meta) return;
    const height = this.heightAtXY(x, y);
    if (height === null) return;
    const target = this._toScene(x, y, height);
    target.y *= this.world.scale.y;
    const spherical = new THREE.Spherical().setFromVector3(this.camera.position.clone().sub(this.controls.target));
    this.controls.target.copy(target);
    this._placeCamera(target, Math.max(300, visibleHeight / 2 / Math.tan(this.opt.fov * DEG / 2)), spherical.phi, spherical.theta);
    this.controls.update();
    this.camera.updateMatrixWorld(true);
    this._emit("frame");
  }

  /** Suspend GPU work and animation time while an immersive reconstruction covers this map. */
  setPaused(paused) {
    if (this._paused === paused) return;
    this._paused = paused;
    if (paused) {
      this._pausedAt = performance.now();
      cancelAnimationFrame(this._raf);
    } else {
      const elapsed = performance.now() - this._pausedAt;
      for (const tween of this._tweens) if (tween.startedAt !== null) tween.startedAt += elapsed;
      if (this.active) this._loop();
    }
  }

  // ---------- route
  /**
   * Accepts the POST /plan-route response ({geojson}), its FeatureCollection, or an array of [[lon, lat], …].
   * Uses features with kind = route | classic_astar | origin | destination | science_stop | charging_stop.
   */
  setRoute(input) {
    if (!this.world) { this._routeData = input; return; }
    this._routeData = input;
    if (this.routeGroup) { this.world.remove(this.routeGroup); disposeTree(this.routeGroup); }
    this.routeGroup = new THREE.Group();
    this.world.add(this.routeGroup);
    this.route = null;
    if (!input) return;
    const fc = Array.isArray(input) ? { features: [{ properties: { kind: "route" }, geometry: { type: "LineString", coordinates: input } }] }
      : input.geojson || input;
    const C = this.opt.colors;
    for (const f of fc.features || []) {
      const kind = f.properties?.kind, coords = f.geometry?.coordinates;
      if (!coords) continue;
      if (kind === "route") this.route = this._addLine(coords, C.route, 5, false);
      else if (kind === "classic_astar") this._addLine(coords, C.classic, 2, true);
      else if (f.geometry.type === "Point") {
        const color = { origin: C.origin, destination: C.destination, charging_stop: C.stop }[kind] ?? C.stop;
        this._addPin(coords, color, kind === "origin" || kind === "destination" ? 1 : .7);
      }
    }
    if (this.route) {
      const head = new THREE.Mesh(new THREE.SphereGeometry(1, 20, 12), new THREE.MeshBasicMaterial({ color: 0xffffff }));
      head.visible = false;
      this.routeGroup.add(head);
      this.route.head = head;
      this._showRouteFraction(this.active ? 1 : 0);
    }
    this._setExaggeration(this.world.scale.y);  // sizes the pins and the route head
  }

  _densify(coords, step) {
    const pts = [];
    for (let i = 0; i < coords.length; i++) {
      const [x, y] = this.lonLatToXY(coords[i][0], coords[i][1]);
      if (i) {
        const [px, py] = pts[pts.length - 1], n = Math.ceil(Math.hypot(x - px, y - py) / step);
        for (let k = 1; k < n; k++) pts.push([lerp(px, x, k / n), lerp(py, y, k / n)]);
      }
      pts.push([x, y]);
    }
    return pts;
  }

  _addLine(coords, color, width, dashed) {
    const cell = this.sizeX / (this.meta.width - 1);
    const pts = this._densify(coords, cell / 2), flat = [], dist = [0], v = new THREE.Vector3();
    for (let i = 0; i < pts.length; i++) {
      const [x, y] = pts[i], h = this.heightAtXY(x, y) ?? this.h0;
      this._toScene(x, y, h + this.opt.lift, v);
      flat.push(v.x, v.y, v.z);
      if (i) dist.push(dist[i - 1] + Math.hypot(x - pts[i - 1][0], y - pts[i - 1][1]));
    }
    const geo = new LineGeometry();
    geo.setPositions(flat);
    const mat = new LineMaterial({ color, linewidth: width, dashed, dashSize: 120, gapSize: 90,
      resolution: new THREE.Vector2(this.container.clientWidth, this.container.clientHeight) });
    const line = new Line2(geo, mat);
    line.computeLineDistances();
    line.renderOrder = 2;
    this.routeGroup.add(line);
    if (!dashed) {
      // Dark halo under the line so it reads over any texture. It does not write depth:
      // being wider, its depth differs slightly from the line and would hide it.
      const halo = new Line2(geo, new LineMaterial({ color: 0x1a0d05, linewidth: width + 3, depthWrite: false,
        resolution: mat.resolution }));
      halo.renderOrder = 1;
      this.routeGroup.add(halo);
    }
    return { line, geo, flat, dist, total: dist[dist.length - 1] };
  }

  _addPin([lon, lat], color, scale) {
    const [x, y] = this.lonLatToXY(lon, lat), h = this.heightAtXY(x, y) ?? this.h0;
    const pin = new THREE.Group();
    const stem = new THREE.Mesh(new THREE.CylinderGeometry(.06, .06, 1, 8), new THREE.MeshBasicMaterial({ color: 0xffffff }));
    stem.position.y = .5;
    const ball = new THREE.Mesh(new THREE.SphereGeometry(.22, 20, 12), new THREE.MeshBasicMaterial({ color }));
    ball.position.y = 1;
    pin.add(stem, ball);
    this._toScene(x, y, h, pin.position);
    pin.userData.size = 260 * scale;  // height in metres; _setExaggeration compensates the exaggeration
    this.routeGroup.add(pin);
  }

  /** Route profile: [{d (metres travelled), h (m)}], useful for an elevation chart. */
  routeProfile() {
    if (!this.route) return [];
    const { flat, dist } = this.route;
    return dist.map((d, i) => ({ d, h: flat[i * 3 + 1] + this.h0 - this.opt.lift }));
  }

  _showRouteFraction(f) {
    const r = this.route;
    if (!r) return;
    const segs = r.flat.length / 3 - 1, n = Math.max(0, Math.min(segs, Math.round(segs * f)));
    r.geo.instanceCount = n;
    r.head.visible = f > 0 && f < 1;
    if (r.head.visible) {
      const i = Math.min(n, segs) * 3;
      r.head.position.set(r.flat[i], r.flat[i + 1], r.flat[i + 2]);
    }
    this._emit("route", f);
  }

  // ---------- animations
  /**
   * Enters 3D. view = {x, y, height}: centre and visible height (m) of the 2D map, so the animation starts from the same framing.
   * Returns a promise that resolves once the route has been drawn.
   */
  async enter(view = {}) {
    if (!this.terrain) throw new Error("Terrain3D: llama a load() antes de enter()");
    const o = this.opt;
    const x = clamp(view.x ?? this.cx, this.cx - this.sizeX / 2, this.cx + this.sizeX / 2);
    const y = clamp(view.y ?? this.cy, this.cy - this.sizeY / 2, this.cy + this.sizeY / 2);
    const visH = view.height ?? this.sizeY;
    const groundH = this.heightAtXY(x, y) ?? this.h0;
    const target = this._toScene(x, y, groundH);
    const dist0 = (visH / 2) / Math.tan(o.fov * DEG / 2);

    const gen = ++this._gen;
    this._stopTweens();
    this.active = true;
    this.controls.enabled = false;
    this._setExaggeration(1);
    this._showRouteFraction(0);
    this.controls.target.copy(target);  // _setExaggeration keeps target.y on the exaggerated ground
    this._placeCamera(this.controls.target, dist0, 0.0001, 0);
    this._loop();
    this.renderer.domElement.style.pointerEvents = "auto";
    this.renderer.domElement.style.opacity = "1";
    this._emit("enter");

    await this._tween(o.enterMs, t => {
      const e = ease(t);
      this._setExaggeration(lerp(1, o.exaggeration, e));
      this._placeCamera(this.controls.target, lerp(dist0, dist0 * .8, e), lerp(0.0001, o.pitch * DEG, e), lerp(0, o.bearing * DEG, e));
    });
    if (gen !== this._gen) return;  // exit() or another enter() interrupted the animation
    this.controls.enabled = true;
    this._emit("entered");
    await this.replayRoute();
  }

  replayRoute() {
    if (!this.route) return Promise.resolve();
    if (!this.active) { this._showRouteFraction(1); return Promise.resolve(); }
    for (const tw of this._tweens.filter(tw => tw.tag === "route")) { this._tweens.splice(this._tweens.indexOf(tw), 1); tw.resolve(); }
    return this._tween(this.opt.routeMs, t => this._showRouteFraction(t), "route");
  }

  /** Returns to top-down and hides the view. Returns {x, y, height} to reposition the 2D map. */
  async exit() {
    if (!this.active) return null;
    const o = this.opt, gen = ++this._gen;
    this._stopTweens();
    this.controls.enabled = false;
    const target = this.controls.target.clone();
    const off = this.camera.position.clone().sub(target);
    const sph = new THREE.Spherical().setFromVector3(off);
    const ex0 = this.world.scale.y, b0 = sph.theta, p0 = sph.phi, d0 = sph.radius;
    const b1 = Math.round(b0 / (2 * Math.PI)) * 2 * Math.PI;  // back to north-up by the shortest path
    await this._tween(o.exitMs, t => {
      const e = ease(t);
      this._setExaggeration(lerp(ex0, 1, e));
      target.y = this.controls.target.y;  // follows the exaggeration
      this._placeCamera(target, d0, lerp(p0, 0.0001, e), lerp(b0, b1, e));
    });
    if (gen !== this._gen) return null;
    this._showRouteFraction(1);
    const el = this.renderer.domElement;
    el.style.opacity = "0";
    el.style.pointerEvents = "none";
    await new Promise(res => setTimeout(res, 350));
    if (gen !== this._gen) return null;  // enter() was called again during the fade
    this.active = false;
    cancelAnimationFrame(this._raf);
    const view = { x: target.x + this.cx, y: this.cy - target.z, height: 2 * d0 * Math.tan(o.fov * DEG / 2) };
    this._emit("exit", view);
    return view;
  }

  setExaggeration(v) { this.opt.exaggeration = v; if (this.active) this._setExaggeration(v); }

  _setExaggeration(v) {
    const old = this.world.scale.y;
    this.world.scale.y = v;
    if (this.controls && old > 0 && old !== v) {
      // The pivot and camera follow the ground when the exaggeration changes (target is in scene coordinates).
      const dy = this.controls.target.y * (v / old - 1);
      this.controls.target.y += dy;
      if (this.controls.enabled) this.camera.position.y += dy;
    }
    for (const c of this.routeGroup?.children || []) {
      if (c.userData.size) c.scale.set(c.userData.size, c.userData.size / v, c.userData.size);
    }
    if (this.route?.head) {
      const s = Math.max(this.sizeX, this.sizeY) / 900;
      this.route.head.scale.set(s, s / v, s);
    }
  }

  _placeCamera(target, dist, phi, theta) {
    const off = new THREE.Vector3().setFromSphericalCoords(dist, phi, theta);
    this.camera.position.copy(target).add(off);
    this.camera.up.set(0, 1, 0);
    // In pure top-down the orientation depends on "up": it is set to north so it matches the 2D map.
    if (phi < 1e-3) this.camera.up.set(-Math.sin(theta), 0, -Math.cos(theta));
    this.camera.lookAt(target);
  }

  _loop() {
    cancelAnimationFrame(this._raf);
    const tick = now => {
      if (!this.active || this._paused) return;
      this._raf = requestAnimationFrame(tick);
      for (const tw of [...this._tweens]) tw.step(now);
      if (this.controls.enabled) this.controls.update();
      const d = this.camera.position.distanceTo(this.controls.target);
      this.scene.fog.near = d * 1.2;
      this.scene.fog.far = d * 4;
      this.renderer.render(this.scene, this.camera);
      this._emit("frame");
    };
    this._raf = requestAnimationFrame(tick);
  }

  _tween(ms, fn, tag) {
    return new Promise(resolve => {
      const tw = {
        tag, resolve, startedAt: null,
        step: now => {
          tw.startedAt ??= now;
          const t = Math.min(1, (now - tw.startedAt) / ms);
          fn(t);
          if (t >= 1) { this._tweens.splice(this._tweens.indexOf(tw), 1); resolve(); }
        },
      };
      this._tweens.push(tw);
    });
  }

  _stopTweens() {
    for (const tw of this._tweens.splice(0)) tw.resolve();
  }

  _lineMaterials() {
    const out = [];
    this.routeGroup?.traverse(o => { if (o.material?.isLineMaterial) out.push(o.material); });
    return out;
  }

  // ---------- events and cleanup
  on(fn) { this._listeners.add(fn); return () => this._listeners.delete(fn); }
  _emit(type, data) { for (const fn of this._listeners) fn(type, data); }

  dispose() {
    this.active = false;
    this._loadSeq = (this._loadSeq || 0) + 1;
    this._stopTweens();
    cancelAnimationFrame(this._raf);
    this._ro?.disconnect();
    this.controls?.dispose();
    if (this.scene) disposeTree(this.scene);
    this.renderer?.dispose();
    this.renderer?.domElement.remove();
  }
}

/** Current framing of a Leaflet map in equirectangular metres. toXY(latlng) → [x, y]. */
export function leafletView(map, toXY) {
  const b = map.getBounds(), c = map.getCenter();
  const [x, y] = toXY(c), [, yN] = toXY(b.getNorthEast()), [, yS] = toXY(b.getSouthWest());
  return { x, y, height: Math.abs(yN - yS) };
}

function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

async function fetchJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  return r.json();
}

async function fetchBuffer(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  return r.arrayBuffer();
}

function disposeTree(root) {
  root.traverse(o => {
    o.geometry?.dispose();
    const ms = Array.isArray(o.material) ? o.material : o.material ? [o.material] : [];
    for (const m of ms) { m.map?.dispose(); m.dispose(); }
  });
}
