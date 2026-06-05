/*
 * UNAV-SA — 3D point-space viewport (Three.js, vendored locally).
 *
 * Renders the visible-sector render payload (Cartesian x/y/z parsecs) as GPU
 * points: colour and size come from the server payload (display_color /
 * display_size). Orbit camera (drag = orbit, right-drag or shift-drag = pan,
 * wheel = zoom), CPU click-picking for selection, and a selection marker. It is a
 * *navigator aid*, not a render engine — no lighting, materials, or scene
 * authoring. See docs/THREE_D_VIEW.md.
 */
import * as THREE from "three";

const _VERT = `
  attribute float size;
  attribute vec3 pColor;
  varying vec3 vColor;
  void main() {
    vColor = pColor;
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = max(2.0, size * (220.0 / max(1.0, -mv.z)));
    gl_Position = projectionMatrix * mv;
  }
`;
const _FRAG = `
  varying vec3 vColor;
  void main() {
    vec2 d = gl_PointCoord - vec2(0.5);
    if (dot(d, d) > 0.25) discard;
    gl_FragColor = vec4(vColor, 1.0);
  }
`;

function hexToRgb(hex) {
  const n = parseInt((hex || "#888888").slice(1), 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
}

function createViewport(container) {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio || 1);
  renderer.setSize(container.clientWidth, container.clientHeight);
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x05080f);
  const camera = new THREE.PerspectiveCamera(
    60, container.clientWidth / container.clientHeight, 0.001, 1e7,
  );

  // simple axes for orientation (x=red, y=green, z=blue)
  scene.add(new THREE.AxesHelper(5));

  // selection marker
  const marker = new THREE.Mesh(
    new THREE.SphereGeometry(1, 12, 8),
    new THREE.MeshBasicMaterial({ color: 0xffffff, wireframe: true }),
  );
  marker.visible = false;
  scene.add(marker);

  let pointsObject = null;
  let pointData = []; // parallel array: {uid, x, y, z}
  let onSelect = () => {};

  // --- orbit state (spherical around target) ---
  const target = new THREE.Vector3(0, 0, 0);
  let radius = 80, theta = 0.6, phi = 1.1;
  function updateCamera() {
    phi = Math.max(0.01, Math.min(Math.PI - 0.01, phi));
    camera.position.set(
      target.x + radius * Math.sin(phi) * Math.sin(theta),
      target.y + radius * Math.cos(phi),
      target.z + radius * Math.sin(phi) * Math.cos(theta),
    );
    camera.lookAt(target);
  }
  updateCamera();

  function setPoints(points) {
    if (pointsObject) { scene.remove(pointsObject); pointsObject.geometry.dispose(); }
    pointData = points || [];
    const n = pointData.length;
    const pos = new Float32Array(n * 3);
    const col = new Float32Array(n * 3);
    const siz = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const p = pointData[i];
      pos[i * 3] = p.x; pos[i * 3 + 1] = p.y; pos[i * 3 + 2] = p.z;
      const [r, g, b] = hexToRgb(p.display_color || p.color);
      col[i * 3] = r; col[i * 3 + 1] = g; col[i * 3 + 2] = b;
      siz[i] = (p.display_size || p.size || 2.5) * 1.6;
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    geo.setAttribute("pColor", new THREE.BufferAttribute(col, 3));
    geo.setAttribute("size", new THREE.BufferAttribute(siz, 1));
    const mat = new THREE.ShaderMaterial({ vertexShader: _VERT, fragmentShader: _FRAG });
    pointsObject = new THREE.Points(geo, mat);
    scene.add(pointsObject);
    marker.visible = false;
    frame();
  }

  function frame() {
    if (!pointData.length) { target.set(0, 0, 0); radius = 80; updateCamera(); return; }
    const c = new THREE.Vector3();
    let maxR = 1;
    for (const p of pointData) c.add(new THREE.Vector3(p.x, p.y, p.z));
    c.multiplyScalar(1 / pointData.length);
    for (const p of pointData) maxR = Math.max(maxR, c.distanceTo(new THREE.Vector3(p.x, p.y, p.z)));
    target.copy(c);
    radius = maxR * 2.4;
    updateCamera();
  }

  function highlight(uid) {
    const p = pointData.find((d) => d.uid === uid);
    if (!p) { marker.visible = false; return; }
    marker.position.set(p.x, p.y, p.z);
    marker.scale.setScalar(Math.max(0.5, radius * 0.02));
    marker.visible = true;
  }

  function focusUid(uid) {
    const p = pointData.find((d) => d.uid === uid);
    if (!p) return;
    target.set(p.x, p.y, p.z);
    radius = Math.max(2, radius * 0.5);
    updateCamera();
    highlight(uid);
  }

  // Pan: translate the orbit target (and camera) across the view plane.
  function panBy(dxPx, dyPx) {
    camera.updateMatrixWorld();
    const right = new THREE.Vector3(), up = new THREE.Vector3(), fwd = new THREE.Vector3();
    camera.matrixWorld.extractBasis(right, up, fwd);
    const k = radius / Math.max(1, container.clientHeight); // ~world units per pixel
    target.addScaledVector(right, -dxPx * k);
    target.addScaledVector(up, dyPx * k);
    updateCamera();
  }

  function getCameraState() {
    const dir = target.clone().sub(camera.position);
    if (dir.lengthSq() === 0) camera.getWorldDirection(dir);
    dir.normalize();
    const up = camera.up.clone().normalize();
    return {
      position: { x: camera.position.x, y: camera.position.y, z: camera.position.z },
      direction: { x: dir.x, y: dir.y, z: dir.z },
      up: { x: up.x, y: up.y, z: up.z },
    };
  }

  function pick(clientX, clientY) {
    const rect = renderer.domElement.getBoundingClientRect();
    const px = clientX - rect.left, py = clientY - rect.top;
    let best = null, bestDist = 14;
    const v = new THREE.Vector3();
    for (const p of pointData) {
      v.set(p.x, p.y, p.z).project(camera);
      if (v.z > 1) continue; // behind camera
      const sx = (v.x * 0.5 + 0.5) * rect.width;
      const sy = (-v.y * 0.5 + 0.5) * rect.height;
      const d = Math.hypot(sx - px, sy - py);
      if (d <= bestDist) { bestDist = d; best = p; }
    }
    return best;
  }

  // --- interaction ---
  const el = renderer.domElement;
  let drag = null;
  el.style.cursor = "grab";
  el.addEventListener("contextmenu", (e) => e.preventDefault()); // right-drag = pan
  el.addEventListener("pointerdown", (e) => {
    el.setPointerCapture(e.pointerId);
    drag = { x: e.clientX, y: e.clientY, moved: 0, pan: e.button === 2 || e.shiftKey };
  });
  el.addEventListener("pointermove", (e) => {
    if (!drag) return;
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    drag.moved += Math.abs(dx) + Math.abs(dy);
    if (drag.pan) {
      panBy(dx, dy);
    } else {
      theta -= dx * 0.005;
      phi -= dy * 0.005;
      updateCamera();
    }
    drag.x = e.clientX; drag.y = e.clientY;
  });
  el.addEventListener("pointerup", (e) => {
    if (drag && drag.moved < 5 && !drag.pan) {
      const hit = pick(e.clientX, e.clientY);
      if (hit) { highlight(hit.uid); onSelect(hit.uid); }
    }
    drag = null;
  });
  el.addEventListener("pointercancel", () => { drag = null; });
  el.addEventListener("wheel", (e) => {
    e.preventDefault();
    radius = Math.max(0.05, Math.min(1e6, radius * Math.pow(1.0015, e.deltaY)));
    updateCamera();
  }, { passive: false });

  function resize() {
    const w = container.clientWidth, h = container.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  window.addEventListener("resize", resize);

  function resetView() { frame(); }

  (function animate() {
    requestAnimationFrame(animate);
    renderer.render(scene, camera);
  })();

  return {
    setPoints, getCameraState, focusUid, highlight, resetView, resize,
    setOnSelect(fn) { onSelect = fn || (() => {}); },
  };
}

// Self-initialise against the page container; expose a small global API.
try {
  const container = document.getElementById("viewport3d");
  if (container) {
    window.UNAV3D = createViewport(container);
    window.dispatchEvent(new Event("unav3d-ready"));
  }
} catch (err) {
  console.error("3D viewport unavailable:", err);
}
