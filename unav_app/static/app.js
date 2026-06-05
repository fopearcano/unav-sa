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
let navState = null; // last known full backend NavigatorState (source of truth)
let currentRoute = null; // the active route being edited (voyage planning)

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
    $("bookmark-btn").disabled = false;
    $("add-to-route-btn").disabled = currentRoute === null;
    status("selected " + uid);
  } catch (err) { status("inspect failed: " + err.message); }
}

function renderSelected(o) {
  const fields = [
    ["uid", o.uid], ["name", o.name], ["type", o.object_type], ["source", o.source],
    ["ra/dec", fmtPair(o.ra_deg, o.dec_deg)], ["distance (pc)", o.distance_pc],
    ["parallax (mas)", o.parallax_mas], ["redshift", o.redshift],
    ["app. mag", o.apparent_magnitude], ["color index", o.color_index],
    ["pm ra (mas/yr)", o.proper_motion_ra_masyr], ["pm dec (mas/yr)", o.proper_motion_dec_masyr],
    ["radial vel (km/s)", o.radial_velocity_kms], ["x/y/z", fmtTriple(o.x, o.y, o.z)],
  ];
  const el = $("selected");
  el.className = "kv";
  el.innerHTML = fields
    .filter(([, v]) => v !== null && v !== undefined && v !== "")
    .map(([k, v]) => `<div class="k">${k}</div><div>${escapeHtml(String(v))}</div>`)
    .join("") + provenanceHtml(o.provenance) + metadataHtml(o.metadata);
}

// Provenance shown inline in the inspector (origin/audit of the selected object).
function provenanceHtml(p) {
  if (!p) return "";
  const rows = [
    ["source", p.source], ["catalog", p.catalog], ["version", p.version],
    ["frame", p.reference_frame], ["epoch", p.epoch], ["endpoint", p.endpoint],
    ["retrieved", p.retrieved_at], ["notes", p.notes],
  ].filter(([, v]) => v !== null && v !== undefined && v !== "");
  if (!rows.length) return "";
  return `<div class="k section">provenance</div><div></div>` +
    rows.map(([k, v]) => `<div class="k sub">${k}</div><div>${escapeHtml(String(v))}</div>`).join("");
}

function metadataHtml(meta) {
  if (!meta || !Object.keys(meta).length) return "";
  return `<div class="k section">metadata</div><div></div>` +
    Object.entries(meta)
      .map(([k, v]) => `<div class="k sub">${escapeHtml(k)}</div><div>${escapeHtml(String(v))}</div>`)
      .join("");
}

async function focusSelected() {
  if (!selectedObject) return;
  try {
    const state = await api(`/navigator/focus/${encodeURIComponent(selectedObject.uid)}`, { method: "POST" });
    applyStateToForm(state);
    if (window.UNAV3D) window.UNAV3D.focusUid(selectedObject.uid);
    status(`focused on ${selectedObject.uid} — click “Query visible sector” to refresh`);
  } catch (err) { status("focus failed: " + err.message); }
}

// --- navigator state ---

// The form edits the commonly-tweaked fields; the rest of the state (e.g. `up`,
// active datasets) is preserved from the last known backend state (navState).
function readStateFromForm() {
  const base = navState || {};
  return {
    position: { x: num("pos-x"), y: num("pos-y"), z: num("pos-z") },
    direction: { x: num("dir-x"), y: num("dir-y"), z: num("dir-z") },
    up: base.up || { x: 0, y: 1, z: 0 },
    fov_degrees: num("fov", 60),
    near_distance: num("near", 0),
    far_distance: num("far", 1000),
    cone_angle_degrees: num("cone", 45),
    epoch: strOrNull("epoch"),
    max_visible_objects: Math.max(1, Math.round(num("maxv", 1000))),
    active_dataset_ids: base.active_dataset_ids || [],
  };
}

function applyStateToForm(state) {
  navState = state; // remember the full backend state (incl. up, datasets)
  $("pos-x").value = state.position.x; $("pos-y").value = state.position.y; $("pos-z").value = state.position.z;
  $("dir-x").value = state.direction.x; $("dir-y").value = state.direction.y; $("dir-z").value = state.direction.z;
  $("near").value = state.near_distance;
  $("far").value = state.far_distance;
  $("fov").value = state.fov_degrees;
  $("cone").value = state.cone_angle_degrees;
  $("maxv").value = state.max_visible_objects;
  $("epoch").value = state.epoch || "";
  renderStateReadout(state);
}

function renderStateReadout(s) {
  const v = (p) => `${round(p.x)}, ${round(p.y)}, ${round(p.z)}`;
  $("state-readout").textContent =
    `pos [${v(s.position)}] · dir [${v(s.direction)}] · up [${v(s.up)}] · ` +
    `fov ${s.fov_degrees}° · near ${s.near_distance} · far ${s.far_distance} pc · ` +
    `cone ${s.cone_angle_degrees}° · epoch ${s.epoch || "—"} · max ${s.max_visible_objects}`;
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

// Camera-relative movement — persists the new state; does NOT auto-refresh the
// visible sector (manual refresh keeps the query loop under user control).
async function moveNavigator(direction) {
  const distance = Math.abs(num("step", 10)) || 10;
  try {
    const state = await api("/navigator/move", {
      method: "POST",
      body: JSON.stringify({ direction, distance }),
    });
    applyStateToForm(state);
    status(`moved ${direction} ${distance} pc — click “Query visible sector” to refresh`);
  } catch (err) { status("move failed: " + err.message); }
}

async function resetNavigator() {
  const def = {
    position: { x: 0, y: 0, z: 0 }, direction: { x: 0, y: 0, z: -1 }, up: { x: 0, y: 1, z: 0 },
    fov_degrees: 60, near_distance: 0, far_distance: 1000, cone_angle_degrees: 45,
    epoch: null, max_visible_objects: 1000, active_dataset_ids: [],
  };
  try {
    const state = await api("/navigator/state", { method: "POST", body: JSON.stringify(def) });
    applyStateToForm(state);
    if (window.UNAV3D) window.UNAV3D.resetView();
    status("navigator reset — click “Query visible sector” to refresh");
  } catch (err) { status("reset failed: " + err.message); }
}

// The manual refresh of the state loop: persist the form so the backend state is
// authoritative, then query the visible sector FROM that current state. Updates
// the 3D points, the results list, the 2D sky, the object count and cap warning.
async function queryVisibleSector() {
  try {
    const state = await api("/navigator/state", {
      method: "POST",
      body: JSON.stringify(readStateFromForm()),
    });
    applyStateToForm(state);
    const body = await api("/visible-sector/query-current", { method: "POST" });
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
  // No auto-query on load — the user refreshes the sector manually.
  $("viewport3d-note").textContent =
    "drag orbit · right-drag pan · wheel zoom · click a point — “Query visible sector” to load";
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
    status("navigator synced to 3D view — click “Query visible sector” to refresh");
  } catch (err) { status("sync failed: " + err.message); }
}

// --- voyage planning: bookmarks ---

async function loadBookmarks() {
  try {
    const list = await api("/bookmarks");
    const el = $("bookmarks");
    if (!list.length) { el.className = "list muted"; el.innerHTML = "<li>none yet</li>"; return; }
    el.className = "list";
    el.innerHTML = "";
    for (const b of list) {
      const li = document.createElement("li");
      li.innerHTML = `<span>${escapeHtml(b.label)}</span>`;
      const del = document.createElement("button");
      del.className = "chip"; del.textContent = "×"; del.title = "delete bookmark";
      del.addEventListener("click", () => deleteBookmark(b.bookmark_id));
      if (b.object_uid) li.querySelector("span").addEventListener("click", () => selectObject(b.object_uid));
      li.appendChild(del);
      el.appendChild(li);
    }
  } catch (err) { status("bookmarks: " + err.message); }
}

async function bookmarkSelected() {
  if (!selectedObject) return;
  const body = { label: selectedObject.name || selectedObject.uid, object_uid: selectedObject.uid };
  if (hasCartesian(selectedObject)) body.position = { x: selectedObject.x, y: selectedObject.y, z: selectedObject.z };
  try {
    await api("/bookmarks", { method: "POST", body: JSON.stringify(body) });
    await loadBookmarks();
    status("bookmarked " + body.label);
  } catch (err) { status("bookmark failed: " + err.message); }
}

async function deleteBookmark(id) {
  try { await api("/bookmarks/" + encodeURIComponent(id), { method: "DELETE" }); await loadBookmarks(); }
  catch (err) { status("delete bookmark failed: " + err.message); }
}

// --- voyage planning: routes ---

async function loadRoutes() {
  try {
    const list = await api("/routes");
    const el = $("routes");
    if (!list.length) { el.className = "list muted"; el.innerHTML = "<li>none yet</li>"; return; }
    el.className = "list";
    el.innerHTML = "";
    for (const r of list) {
      const li = document.createElement("li");
      li.innerHTML = `<span>${escapeHtml(r.name)}</span><span class="tag">${r.waypoints.length} wp</span>`;
      li.querySelector("span").addEventListener("click", () => selectRoute(r.route_id));
      const del = document.createElement("button");
      del.className = "chip"; del.textContent = "×"; del.title = "delete route";
      del.addEventListener("click", (e) => { e.stopPropagation(); deleteRoute(r.route_id); });
      li.appendChild(del);
      el.appendChild(li);
    }
  } catch (err) { status("routes: " + err.message); }
}

async function newRoute() {
  const name = $("route-name").value.trim() || "Route";
  try {
    currentRoute = await api("/routes", { method: "POST", body: JSON.stringify({ name }) });
    $("route-name").value = "";
    renderRoute();
    await loadRoutes();
    status("created route " + name);
  } catch (err) { status("new route failed: " + err.message); }
}

async function selectRoute(id) {
  try { currentRoute = await api("/routes/" + encodeURIComponent(id)); renderRoute(); }
  catch (err) { status("load route failed: " + err.message); }
}

async function deleteRoute(id) {
  try {
    await api("/routes/" + encodeURIComponent(id), { method: "DELETE" });
    if (currentRoute && currentRoute.route_id === id) { currentRoute = null; renderRoute(); }
    await loadRoutes();
  } catch (err) { status("delete route failed: " + err.message); }
}

async function addSelectedToRoute() {
  if (!selectedObject || !currentRoute) return;
  try {
    currentRoute = await api(
      `/routes/${encodeURIComponent(currentRoute.route_id)}/add-object/${encodeURIComponent(selectedObject.uid)}`,
      { method: "POST" },
    );
    renderRoute();
    await loadRoutes();
    status(`added ${selectedObject.uid} to route`);
  } catch (err) { status("add to route failed: " + err.message); }
}

async function saveActiveRoute() {
  // Persist client-side edits (reorder/remove) to the active route.
  currentRoute = await api(
    "/routes/" + encodeURIComponent(currentRoute.route_id),
    { method: "PUT", body: JSON.stringify(currentRoute) },
  );
}

async function moveWaypoint(index, delta) {
  const wps = currentRoute.waypoints;
  const j = index + delta;
  if (j < 0 || j >= wps.length) return;
  [wps[index], wps[j]] = [wps[j], wps[index]];
  try { await saveActiveRoute(); renderRoute(); await loadRoutes(); }
  catch (err) { status("reorder failed: " + err.message); }
}

async function removeWaypoint(wid) {
  currentRoute.waypoints = currentRoute.waypoints.filter((w) => w.wid !== wid);
  try { await saveActiveRoute(); renderRoute(); await loadRoutes(); }
  catch (err) { status("remove waypoint failed: " + err.message); }
}

function renderRoute() {
  const el = $("route-waypoints");
  $("add-to-route-btn").disabled = currentRoute === null || selectedObject === null;
  $("create-mission-btn").disabled = !(currentRoute && currentRoute.waypoints.length);
  if (!currentRoute) {
    $("active-route-label").textContent = "no active route";
    el.className = "list muted"; el.innerHTML = "<li>create or select a route</li>";
    $("route-summary").textContent = "";
    drawRouteInViewports();
    return;
  }
  $("active-route-label").textContent = `active: ${currentRoute.name}`;
  const wps = currentRoute.waypoints;
  if (!wps.length) { el.className = "list muted"; el.innerHTML = "<li>no waypoints — add the selected object</li>"; }
  else {
    el.className = "list";
    el.innerHTML = "";
    wps.forEach((w, i) => {
      const li = document.createElement("li");
      li.innerHTML = `<span>${i + 1}. ${escapeHtml(w.label || w.object_uid || w.kind)}</span>`;
      const ctrl = document.createElement("span"); ctrl.className = "wp-ctrl";
      ctrl.innerHTML =
        `<button class="chip" title="up">↑</button><button class="chip" title="down">↓</button>` +
        `<button class="chip" title="remove">×</button>`;
      const [up, down, rm] = ctrl.querySelectorAll("button");
      up.addEventListener("click", () => moveWaypoint(i, -1));
      down.addEventListener("click", () => moveWaypoint(i, 1));
      rm.addEventListener("click", () => removeWaypoint(w.wid));
      if (w.object_uid) li.querySelector("span").addEventListener("click", () => selectObject(w.object_uid));
      li.appendChild(ctrl);
      el.appendChild(li);
    });
  }
  updateRouteSummary();
  drawRouteInViewports();
}

async function updateRouteSummary() {
  if (!currentRoute) { $("route-summary").textContent = ""; return; }
  try {
    const s = await api("/routes/" + encodeURIComponent(currentRoute.route_id) + "/summary");
    $("route-summary").textContent =
      `legs: ${s.leg_count} · positioned: ${s.positioned_waypoints} · total: ${round(s.total_distance_pc)} pc`;
  } catch (_) { /* non-fatal */ }
}

function drawRouteInViewports() {
  const wps = currentRoute ? currentRoute.waypoints : [];
  if (window.UNAV3D && window.UNAV3D.setRoute) window.UNAV3D.setRoute(wps);
  if (sky && sky.setRoute) sky.setRoute(wps);
}

// --- voyage planning: missions ---

async function loadMissions() {
  try {
    const list = await api("/missions");
    const el = $("missions");
    if (!list.length) { el.className = "list muted"; el.innerHTML = "<li>none yet</li>"; return; }
    el.className = "list";
    el.innerHTML = "";
    for (const m of list) {
      const li = document.createElement("li");
      const n = m.route ? m.route.waypoints.length : 0;
      li.innerHTML = `<span>${escapeHtml(m.title)}</span><span class="tag">${n} wp</span>`;
      if (m.route) li.querySelector("span").addEventListener("click", () => { currentRoute = m.route; renderRoute(); });
      const del = document.createElement("button");
      del.className = "chip"; del.textContent = "×"; del.title = "delete mission";
      del.addEventListener("click", () => deleteMission(m.mission_id));
      li.appendChild(del);
      el.appendChild(li);
    }
  } catch (err) { status("missions: " + err.message); }
}

async function createMissionFromRoute() {
  if (!currentRoute || !currentRoute.waypoints.length) return;
  const title = $("mission-title").value.trim() || `${currentRoute.name} mission`;
  const segments = currentRoute.waypoints.map((w, i) => ({
    waypoint_id: w.wid, transition_seconds: i === 0 ? 0 : 10, hold_seconds: 0,
  }));
  try {
    await api("/missions", { method: "POST", body: JSON.stringify({ title, route: currentRoute, segments }) });
    $("mission-title").value = "";
    await loadMissions();
    status("created mission " + title);
  } catch (err) { status("create mission failed: " + err.message); }
}

async function deleteMission(id) {
  try { await api("/missions/" + encodeURIComponent(id), { method: "DELETE" }); await loadMissions(); }
  catch (err) { status("delete mission failed: " + err.message); }
}

// --- helpers ---

function num(id, dflt = 0) { const v = parseFloat($(id).value); return Number.isFinite(v) ? v : dflt; }
function strOrNull(id) { const v = $(id).value.trim(); return v === "" ? null : v; }
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
  $("reset-nav-btn").addEventListener("click", resetNavigator);
  $("visible-btn").addEventListener("click", queryVisibleSector);
  for (const dir of ["forward", "back", "left", "right", "up", "down"]) {
    $(`move-${dir}`).addEventListener("click", () => moveNavigator(dir));
  }
  $("full-sky-btn").addEventListener("click", loadFullSky);
  $("load-region-btn").addEventListener("click", loadRegionInView);
  $("fit-btn").addEventListener("click", () => sky.fit());

  // voyage planning: bookmarks, routes, missions
  $("bookmark-btn").addEventListener("click", bookmarkSelected);
  $("new-route-btn").addEventListener("click", newRoute);
  $("add-to-route-btn").addEventListener("click", addSelectedToRoute);
  $("create-mission-btn").addEventListener("click", createMissionFromRoute);

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
  loadBookmarks();
  loadRoutes();
  loadMissions();
}

document.addEventListener("DOMContentLoaded", init);
