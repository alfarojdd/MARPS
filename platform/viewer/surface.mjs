import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { OBJLoader } from "three/addons/loaders/OBJLoader.js";

const $ = selector => document.querySelector(selector);
const EYE_HEIGHT = 1.65;
const MOVE_KEYS = {KeyW: "forward", ArrowUp: "forward", KeyS: "back", ArrowDown: "back", KeyA: "left", ArrowLeft: "left", KeyD: "right", ArrowRight: "right"};

// Approximate visual ground from the observed geometry. Never fills gaps without data.
class SurfaceGrid {
  constructor(cell = .5) { this.cell = cell; this.samples = new Map(); }
  key(x, z) { return `${Math.floor(x / this.cell)},${Math.floor(z / this.cell)}`; }
  add(x, y, z) {
    const key = this.key(x, z), bucket = this.samples.get(key) || [];
    bucket.push(y);
    this.samples.set(key, bucket);
  }
  finish() {
    this.heights = new Map();
    for (const [key, values] of this.samples) {
      if (values.length < 3) continue;
      values.sort((a, b) => a - b);
      this.heights.set(key, values[Math.floor(values.length * .6)]);
    }
    this.samples.clear();
  }
  at(x, z) { return this.heights.get(this.key(x, z)); }
  nearest(x, z, radius = 3) {
    for (let r = 0; r <= radius; r += this.cell) {
      for (let a = 0; a < Math.PI * 2; a += Math.PI / 8) {
        const px = x + r * Math.cos(a), pz = z + r * Math.sin(a), y = this.at(px, pz);
        if (y != null) return new THREE.Vector3(px, y + EYE_HEIGHT, pz);
      }
    }
    let nearest = null, distance = Infinity;
    for (const [key, y] of this.heights) {
      const [col, row] = key.split(",").map(Number);
      const px = (col + .5) * this.cell, pz = (row + .5) * this.cell;
      const candidate = Math.hypot(px - x, pz - z);
      if (candidate < distance) {
        distance = candidate;
        nearest = new THREE.Vector3(px, y + EYE_HEIGHT, pz);
      }
    }
    return nearest;
  }
}

export async function start() {
  const id = new URLSearchParams(location.search).get("id");
  const response = await fetch("/api/reconstructions");
  if (!response.ok) throw new Error("The server did not return the 3D catalogue");
  const catalog = await response.json(), entry = catalog.scenes.find(s => s.id === id);
  if (!entry?.available || !["spz", "obj"].includes(entry.renderer)) throw new Error("Local model unavailable");

  const view = $("#view"), renderer = new THREE.WebGLRenderer({antialias: false});
  if (!renderer.capabilities.isWebGL2) throw new Error("This view requires WebGL2");
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  const quality = new URLSearchParams(location.search).get("quality") || "auto";
  $("#quality").value = ["auto", "full", "light"].includes(quality) ? quality : "auto";
  $("#quality").onchange = event => {
    const url = new URL(location.href);
    url.searchParams.set("quality", event.target.value);
    location.replace(url);
  };
  const gl = renderer.getContext(), debug = gl.getExtension("WEBGL_debug_renderer_info");
  const gpuName = debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : "";
  const lightweight = quality === "light" || quality === "auto" && /swiftshader|llvmpipe|software/i.test(gpuName);
  view.append(renderer.domElement);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color("#211c19");
  const camera = new THREE.PerspectiveCamera(68, 1, .05, 1000);
  camera.rotation.order = "YXZ";
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enabled = false;
  controls.enableDamping = true;
  controls.maxDistance = entry.radius * 3;
  controls.minDistance = .3;
  const ground = new SurfaceGrid();
  let mesh, spark, texture, modelRoot, meshEye, meshTarget;
  const bounds = new THREE.Box3();
  function progress(event) {
    $("#loadingTitle").textContent = event.lengthComputable ? `Loading model · ${Math.round(event.loaded / event.total * 100)} %` : "Downloading and decoding the model…";
    $("#loadingDetail").textContent = entry.renderer === "spz" ? "Cheyava Falls · 16.3 MB · 972,047 Gaussians" : "Textured Navcam mesh · 52 MB";
  }

  // Register disposal before starting downloads to cover exits during loading.
  window.addEventListener("pagehide", () => {
    renderer.setAnimationLoop(null);
    controls.dispose();
    mesh?.dispose?.();
    modelRoot?.traverse(object => {
      object.geometry?.dispose();
      const materials = Array.isArray(object.material) ? object.material : [object.material];
      materials.forEach(material => material?.dispose());
    });
    texture?.dispose();
    spark?.dispose?.();
    renderer.dispose();
    renderer.forceContextLoss();
  }, {once: true});

  if (entry.renderer === "spz") {
    const {SparkRenderer, SplatMesh} = await import("@sparkjsdev/spark");
    spark = new SparkRenderer({renderer});
    scene.add(spark);
    mesh = new SplatMesh({url: entry.asset, onProgress: progress});
    await mesh.initialized;
    mesh.forEachSplat((index, center, scales, quaternion, opacity) => {
      if (index % 3 === 0 && opacity > .35 && Math.hypot(center.x, center.y) < entry.radius) ground.add(center.x, center.z, -center.y);
    });
    bounds.copy(mesh.getBoundingBox()).applyMatrix4(new THREE.Matrix4().makeRotationX(-Math.PI / 2));
    if (lightweight) {
      const original = mesh;
      mesh = new SplatMesh({constructSplats: packed => {
        original.forEachSplat((index, center, scales, quaternion, opacity, color) => {
          if (index % 20 === 0) packed.pushSplat(center, scales, quaternion, opacity, color);
        });
      }});
      await mesh.initialized;
      original.dispose();
    }
    // Published frame: site +X east, +Y north, +Z up → Three +Y up.
    mesh.rotation.x = -Math.PI / 2;
    scene.add(mesh);
  } else {
    [modelRoot, texture] = await Promise.all([
      new OBJLoader().loadAsync(entry.asset, progress),
      new THREE.TextureLoader().loadAsync(entry.texture),
    ]);
    texture.colorSpace = THREE.SRGBColorSpace;
    // NASA SITE_FRAME NED → Three: east, up, south. Not the SPZ site frame.
    const rotation = new THREE.Matrix4().set(0,1,0,0, 0,0,-1,0, -1,0,0,0, 0,0,0,1);
    modelRoot.applyMatrix4(rotation);
    modelRoot.updateMatrixWorld(true);
    bounds.setFromObject(modelRoot);
    const center = bounds.getCenter(new THREE.Vector3());
    modelRoot.position.sub(center);
    modelRoot.updateMatrixWorld(true);
    const p = new THREE.Vector3();
    let eyeScore = Infinity, targetScore = Infinity;
    modelRoot.traverse(object => {
      if (!object.isMesh) return;
      object.material.dispose();
      object.material = new THREE.MeshBasicMaterial({map: texture, side: THREE.DoubleSide});
      const vertices = object.geometry.getAttribute("position");
      const uv = object.geometry.getAttribute("uv");
      for (let i = 0; i < vertices.count; i += 3) {
        p.fromBufferAttribute(vertices, i).applyMatrix4(object.matrixWorld);
        ground.add(p.x, p.y, p.z);
        // Start over the observed foreground and look toward the central terrain
        // of the photo. This mesh's bounding-box center falls in a gap.
        if (uv) {
          const u = uv.getX(i), v = uv.getY(i);
          const near = (u - .5) ** 2 + (v - .15) ** 2;
          const ahead = (u - .5) ** 2 + (v - .55) ** 2;
          if (near < eyeScore) { eyeScore = near; meshEye = p.clone().add(new THREE.Vector3(0, EYE_HEIGHT, 0)); }
          if (ahead < targetScore) { targetScore = ahead; meshTarget = p.clone(); }
        }
      }
    });
    scene.add(modelRoot);
    bounds.setFromObject(modelRoot);
  }
  ground.finish();

  const target = entry.target ? new THREE.Vector3(...entry.target) : meshTarget || bounds.getCenter(new THREE.Vector3());
  const desiredEye = entry.eye ? new THREE.Vector3(...entry.eye) : meshEye || target.clone().add(new THREE.Vector3(0, EYE_HEIGHT, 3));
  const home = ground.nearest(desiredEye.x, desiredEye.z, 10);
  if (!home) throw new Error("No observed surface found for the initial camera");
  let mode = "walk", dragging = null;
  const keys = new Set(), touchMoves = new Set();
  const origin = home.clone(), next = new THREE.Vector3();
  const walkRadius = entry.radius * .85;
  function reset() {
    keys.clear(); touchMoves.clear();
    camera.position.copy(home);
    camera.lookAt(target);
    controls.target.copy(target);
    controls.update();
  }
  function setMode(value) {
    mode = value;
    controls.enabled = mode === "orbit";
    $("#walk").setAttribute("aria-pressed", String(mode === "walk"));
    $("#orbit").setAttribute("aria-pressed", String(mode === "orbit"));
    $("#touchControls").hidden = mode !== "walk";
    keys.clear(); touchMoves.clear();
    if (mode === "walk") reset();
    else controls.target.copy(target);
  }
  $("#walk").onclick = () => setMode("walk");
  $("#orbit").onclick = () => setMode("orbit");
  $("#reset").onclick = () => { setMode("walk"); view.focus(); };
  $("#fullscreen").onclick = async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    } catch { $("#position").textContent = "Fullscreen is not available in this browser."; }
  };
  document.addEventListener("keydown", event => {
    if (MOVE_KEYS[event.code] && !["INPUT", "SELECT", "TEXTAREA"].includes(event.target.tagName)) {
      keys.add(event.code); event.preventDefault();
    }
  });
  document.addEventListener("keyup", event => keys.delete(event.code));
  window.addEventListener("blur", () => { keys.clear(); touchMoves.clear(); dragging = null; });
  document.addEventListener("visibilitychange", () => { keys.clear(); touchMoves.clear(); });
  view.addEventListener("pointerdown", event => {
    if (mode !== "walk" || dragging || event.button !== 0) return;
    dragging = {id: event.pointerId, x: event.clientX, y: event.clientY};
    view.setPointerCapture(event.pointerId); view.focus();
  });
  view.addEventListener("pointermove", event => {
    if (mode !== "walk" || dragging?.id !== event.pointerId) return;
    camera.rotation.y -= (event.clientX - dragging.x) * .004;
    camera.rotation.x = THREE.MathUtils.clamp(camera.rotation.x - (event.clientY - dragging.y) * .004, -1.45, 1.45);
    dragging.x = event.clientX; dragging.y = event.clientY;
  });
  for (const type of ["pointerup", "pointercancel", "lostpointercapture"]) view.addEventListener(type, () => { dragging = null; });
  for (const button of document.querySelectorAll("[data-move]")) {
    button.addEventListener("pointerdown", event => { event.preventDefault(); button.setPointerCapture(event.pointerId); touchMoves.add(button.dataset.move); });
    for (const type of ["pointerup", "pointercancel", "lostpointercapture"]) button.addEventListener(type, () => touchMoves.delete(button.dataset.move));
  }
  function resize() {
    const width = view.clientWidth, height = view.clientHeight;
    renderer.setSize(width, height);
    camera.aspect = width / Math.max(height, 1);
    camera.updateProjectionMatrix();
  }
  window.addEventListener("resize", resize);
  resize(); reset();
  $("#loading").hidden = true;
  $("#position").textContent = lightweight && entry.renderer === "spz" ? "Light quality · reduced detail for smoother performance" : "Eye height: 1.65 m above estimated ground";
  view.dataset.ready = "true";
  const clock = new THREE.Clock();
  renderer.setAnimationLoop(() => {
    const dt = Math.min(clock.getDelta(), .05);
    if (mode === "walk") {
      const held = new Set([...touchMoves, ...[...keys].map(key => MOVE_KEYS[key])]);
      let forward = Number(held.has("forward")) - Number(held.has("back"));
      let right = Number(held.has("right")) - Number(held.has("left"));
      const len = Math.hypot(forward, right);
      if (len) {
        forward /= len; right /= len;
        const yaw = camera.rotation.y, step = 1.2 * dt;
        next.copy(camera.position);
        next.x += (-Math.sin(yaw) * forward + Math.cos(yaw) * right) * step;
        next.z += (-Math.cos(yaw) * forward - Math.sin(yaw) * right) * step;
        const height = ground.at(next.x, next.z);
        const inside = Math.hypot(next.x - origin.x, next.z - origin.z) <= walkRadius;
        if (height != null && inside && Math.abs(height + EYE_HEIGHT - camera.position.y) < .6) {
          next.y = THREE.MathUtils.lerp(camera.position.y, height + EYE_HEIGHT, Math.min(1, dt * 8));
          camera.position.copy(next);
          $("#position").textContent = "Eye height: 1.65 m above estimated ground · no physical collisions";
        } else $("#position").textContent = "Edge of the observed surface. Turn around or step back.";
      }
    } else controls.update();
    renderer.render(scene, camera);
    view.dataset.position = camera.position.toArray().map(v => v.toFixed(3)).join(",");
    view.dataset.direction = camera.getWorldDirection(new THREE.Vector3()).toArray().map(v => v.toFixed(3)).join(",");
  });
}
