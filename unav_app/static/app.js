/*
 * UNAV-SA standalone shell — minimal vanilla JS.
 *
 * Talks to the local API (same origin). It only renders responses and posts
 * user input; all astronomy/query logic lives server-side in unav_core.
 */
"use strict";

// Same-origin by default; override with window.UNAV_API_BASE if served elsewhere.
const API_BASE = window.UNAV_API_BASE || "";

let selectedObject = null;
let sky = null; // the SkyMap instance
let wired3D = false;
let currentView = "3d"; // "3d" | "2d" — which viewport is shown

const $ = (id) => document.getElementById(id);
const status = (msg) => { $("status").textContent = msg; };

async function api(path, options = {}) {
  const res = await fetch(API_BASE + path, {
    headers: { "content-type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch (_) {}
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.status === 204 ? null : res.json();
}

// --- health & datasets ---

async function loadHealth() {
  try {
    const h = await api("/health");
    $("health-dot").className = "dot ok";
    $("health-text").textContent = `ok · ${h.object_count} objects`;
  } catch (err) {
    $("health-dot").className = "dot bad";
    $("health-text").textContent = "unavailable";
    status("API unreachable: " + err.message);
  }
}

async function loadDatasets() {
  try {
    const datasets = await api("/datasets");
    const el = $("datasets");
    if (!datasets.length) { el.className = "list muted"; el.innerHTML = "<li>no datasets imported</li>"; return; }
    el.className = "list";
    el.innerHTML = "";
    for (const d of datasets) {
      const li = document.createElement("li");
      li.innerHTML = `<span>${escapeHtml(d.name)}</span><span class="tag">${d.object_count} · ${escapeHtml(d.source)}</span>`;
      el.appendChild(li);
    }
  } catch (err) { status("datasets: " + err.message); }
}

// --- search ---

async function doSearch(event) {
  if (event) event.preventDefault();
  const params = new URLSearchParams();
  const q = $("q").value.trim();
  const source = $("source").value.trim();
  const type = $("object_type").value.trim();
  if (q) params.set("q", q);
  if (source) params.set("source", source);
  if (type) params.set("object_type", type);
  params.set("limit", "1000");
  try {
    const body = await api("/objects/search?" + params.toString());
    renderResults(body.objects);
    status(`search: ${body.count} object(s)`);
  } catch (err) { status("search failed: " + err.message); }
}

function renderResults(objects) {
  const el = $("results");
  if (!objects.length) { el.className = "list muted"; el.innerHTML = "<li>no matches</li>"; sky.setObjects([]); return; }
  el.className = "list";
  el.innerHTML = "";
  for (const o of objects) {
    const li = document.createElement("li");
    li.dataset.uid = o.uid;
    li.innerHTML = `<span>${escapeHtml(o.name || o.uid)}</span><span class="tag">${escapeHtml(o.object_type)}</span>`;
    li.addEventListener("click", () => selectObject(o.uid));
    el.appendChild(li);
  }
  sky.setObjects(objects); // fits the view to the loaded objects
  updatePlotNote(objects);
}

function updatePlotNote(objects) {
  const placeable = objects.filter((o) => o.ra_deg !== null && o.dec_deg !== null).length;
  $("plot-note").textContent = `· ${placeable}/${objects.length} on sky`;
}

async function selectObject(uid) {
  document.querySelectorAll("#results li.active").forEach((x) => x.classList.remove("active"));
  for (const li of document.querySelectorAll("#results li")) {
    if (li.dataset.uid === uid) { li.classList.add("active"); li.scrollIntoView({ block: "nearest" }); }
  }
  try {
    selectedObject = await api("/objects/" + encodeURIComponent(uid));
    renderSelected(selectedObject);
    sky.setSelected(uid);
    if (window.UNAV3D) window.UNAV3D.highlight(uid);
    $("focus-btn").disabled = !hasCartesian(selectedObject);
    status("selected " + uid);
  } catch (err) { status("inspect failed: " + err.message); }
}

function renderSelected(o) {
  const fields = [
    ["uid", o.uid], ["name", o.name], ["type", o.object_type], ["source", o.source],
    ["ra/dec", fmtPair(o.ra_deg, o.dec_deg)], ["distance (pc)", o.distance_pc],
    ["parallax (mas)", o.parallax_mas], ["redshift", o.redshift],
    ["app. mag", o.apparent_magnitude], ["x/y/z", fmtTriple(o.x, o.y, o.z)],
  ];
  const el = $("selected");
  el.className = "kv";
  el.innerHTML = fields
    .filter(([, v]) => v !== null && v !== undefined && v !== "")
    .map(([k, v]) => `<div class="k">${k}</div><div>${escapeHtml(String(v))}</div>`)
    .join("");
}

async function focusSelected() {
  if (!selectedObject) return;
  try {
    const state = await api(`/navigator/focus/${encodeURIComponent(selectedObject.uid)}`, { method: "POST" });
    applyStateToForm(state);
    if (window.UNAV3D) window.UNAV3D.focusUid(selectedObject.uid);
    status("focused on " + selectedObject.uid);
  } catch (err) { status("focus failed: " + err.message); }
}

// --- navigator state ---

function readStateFromForm() {
  return {
    position: { x: num("pos-x"), y: num("pos-y"), z: num("pos-z") },
    direction: { x: num("dir-x"), y: num("dir-y"), z: num("dir-z") },
    up: { x: 0, y: 1, z: 0 },
    far_distance: num("far"),
    cone_angle_degrees: num("cone"),
    max_visible_objects: Math.max(1, Math.round(num("maxv"))),
  };
}

function applyStateToForm(state) {
  $("pos-x").value = state.position.x; $("pos-y").value = state.position.y; $("pos-z").value = state.position.z;
  $("dir-x").value = state.direction.x; $("dir-y").value = state.direction.y; $("dir-z").value = state.direction.z;
  $("far").value = state.far_distance;
  $("cone").value = state.cone_angle_degrees;
  $("maxv").value = state.max_visible_objects;
}

async function loadState() {
  try { applyStateToForm(await api("/navigator/state")); }
  catch (err) { status("state: " + err.message); }
}

async function setState() {
  try {
    const state = await api("/navigator/state", { method: "POST", body: JSON.stringify(readStateFromForm()) });
    applyStateToForm(state);
    status("navigator state updated");
  } catch (err) { status("set state failed: " + err.message); }
}

// One action drives both viewports: query the visible sector (lightweight render
// objects), then update the 3D points, the results list, the 2D sky, the object
// count and the cap warning.
async function queryVisibleSector() {
  try {
    const body = await api("/visible-sector/query", {
      method: "POST",
      body: JSON.stringify({ state: readStateFromForm(), sort: "distance" }),
    });
    if (window.UNAV3D) {
      window.UNAV3D.setPoints(body.objects);
      if (selectedObject) window.UNAV3D.highlight(selectedObject.uid);
      $("viewport3d-note").textContent =
        `${body.count} point(s) · drag orbit · right-drag pan · wheel zoom · click to select`;
    }
    renderResults(body.objects); // results list + 2D sky (objects carry ra/dec)
    updateVisibleStatus(body);
    status(`visible sector: ${body.count} object(s)`);
  } catch (err) { status("visible-sector failed: " + err.message); }
}

function updateVisibleStatus(body) {
  $("visible-summary").textContent = `visible: ${body.count} object(s)`;
  let msg = `visible sector: ${body.count} object(s)`;
  if (body.capped) {
    msg += ` — ⚠ result cap reached (max ${body.max_visible_objects}); increase “max” to see more.`;
    $("visible-status").className = "warn";
  } else {
    $("visible-status").className = "muted";
  }
  $("visible-status").textContent = msg;
}

// --- 2D / 3D view toggle ---

function showView(which) {
  currentView = which;
  const is3d = which === "3d";
  $("view-3d").classList.toggle("hidden", !is3d);
  $("view-2d").classList.toggle("hidden", is3d);
  $("view-3d-btn").classList.toggle("active", is3d);
  $("view-2d-btn").classList.toggle("active", !is3d);
  // The hidden view had zero size while collapsed; refresh the now-visible one.
  if (is3d && window.UNAV3D) window.UNAV3D.resize();
  if (!is3d && sky) sky.resize();
}

// --- sky region loading ---

async function loadFullSky() {
  await queryRegion({ ra_min: 0, ra_max: 360, dec_min: -90, dec_max: 90 }, true);
}

async function loadRegionInView() {
  await queryRegion(sky.getViewBounds(), false);
}

async function queryRegion(bounds, fit) {
  try {
    const body = await api("/sky/query-region", {
      method: "POST",
      body: JSON.stringify({ ...bounds, limit: 5000 }),
    });
    renderResultsList(body.objects);
    sky.setObjects(body.objects, { fit });
    updatePlotNote(body.objects);
    status(`sky region: ${body.count} object(s)`);
  } catch (err) { status("sky region failed: " + err.message); }
}

// like renderResults but never refits the sky (used by region loads)
function renderResultsList(objects) {
  const el = $("results");
  el.className = objects.length ? "list" : "list muted";
  el.innerHTML = "";
  for (const o of objects) {
    const li = document.createElement("li");
    li.dataset.uid = o.uid;
    li.innerHTML = `<span>${escapeHtml(o.name || o.uid)}</span><span class="tag">${escapeHtml(o.object_type)}</span>`;
    li.addEventListener("click", () => selectObject(o.uid));
    el.appendChild(li);
  }
  if (!objects.length) el.innerHTML = "<li>no objects in region</li>";
}

// --- legend ---

function renderLegend() {
  const el = $("legend");
  el.innerHTML = "";
  for (const [type, color] of Object.entries(window.SKY_TYPE_COLORS)) {
    const span = document.createElement("span");
    span.className = "legend-item";
    span.innerHTML = `<span class="swatch" style="background:${color}"></span>${type}`;
    el.appendChild(span);
  }
}

// --- 3D viewport ---

function wire3D() {
  if (wired3D || !window.UNAV3D) return;
  wired3D = true;
  window.UNAV3D.setOnSelect((uid) => selectObject(uid));
  for (const id of ["render3d-btn", "sync3d-btn", "reset3d-btn"]) $(id).disabled = false;
  $("render3d-btn").addEventListener("click", queryVisibleSector);
  $("sync3d-btn").addEventListener("click", syncNavigatorToView);
  $("reset3d-btn").addEventListener("click", () => window.UNAV3D.resetView());
  $("viewport3d-note").textContent =
    "drag to orbit · right-drag to pan · wheel to zoom · click a point";
  queryVisibleSector(); // populate the 3D view on load
}

async function syncNavigatorToView() {
  if (!window.UNAV3D) return;
  const cam = window.UNAV3D.getCameraState();
  const state = readStateFromForm();
  state.position = cam.position;
  state.direction = cam.direction;
  state.up = cam.up;
  try {
    const updated = await api("/navigator/state", { method: "POST", body: JSON.stringify(state) });
    applyStateToForm(updated);
    status("navigator synced to 3D view");
  } catch (err) { status("sync failed: " + err.message); }
}

// --- helpers ---

function num(id) { const v = parseFloat($(id).value); return Number.isFinite(v) ? v : 0; }
function hasCartesian(o) { return o.x !== null && o.y !== null && o.z !== null; }
function fmtPair(a, b) { return a === null || b === null ? "" : `${round(a)}, ${round(b)}`; }
function fmtTriple(a, b, c) { return a === null || b === null || c === null ? "" : `${round(a)}, ${round(b)}, ${round(c)}`; }
function round(v) { return Math.round(v * 1000) / 1000; }
function escapeHtml(s) { return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }

// --- wire up ---

function init() {
  sky = new SkyMap($("sky"), { onSelect: (uid) => selectObject(uid) });
  window.addEventListener("resize", () => sky.resize());
  renderLegend();

  $("search-form").addEventListener("submit", doSearch);
  $("focus-btn").addEventListener("click", focusSelected);
  $("set-state-btn").addEventListener("click", setState);
  $("visible-btn").addEventListener("click", queryVisibleSector);
  $("full-sky-btn").addEventListener("click", loadFullSky);
  $("load-region-btn").addEventListener("click", loadRegionInView);
  $("fit-btn").addEventListener("click", () => sky.fit());

  // 2D / 3D view toggle.
  $("view-3d-btn").addEventListener("click", () => showView("3d"));
  $("view-2d-btn").addEventListener("click", () => showView("2d"));

  // 3D viewport (Three.js module): wire when ready, with a graceful fallback.
  window.addEventListener("unav3d-ready", wire3D);
  if (window.UNAV3D) wire3D();
  else setTimeout(() => {
    if (!window.UNAV3D) $("viewport3d-note").textContent = "3D unavailable (WebGL/Three.js not loaded)";
  }, 2500);

  loadHealth();
  loadDatasets();
  loadState();
  loadFullSky(); // populate the sky map on first load
}

document.addEventListener("DOMContentLoaded", init);
