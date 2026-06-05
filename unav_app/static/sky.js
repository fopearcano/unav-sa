/*
 * UNAV-SA — interactive 2D sky map (plate-carrée / equirectangular).
 *
 * Pure client-side rendering of RA/Dec points on a <canvas>: pan (drag), zoom
 * (wheel, toward the cursor), click-to-select, hover labels, colour by type and
 * size by magnitude. It holds no astronomy logic — it only projects RA/Dec that
 * the API provides. The projection is a simple plate carrée (x ∝ RA, y ∝ Dec)
 * with NO cos(dec) correction; distortion grows toward the poles. See
 * docs/2D_SKY_NAVIGATOR.md.
 */
"use strict";

const SKY_TYPE_COLORS = {
  star: "#cfe8ff", galaxy: "#ffd28a", quasar: "#ff9bd1", planet: "#9affc4",
  moon: "#cccccc", asteroid: "#bda27a", comet: "#9ad0ff", nebula: "#c9a8ff",
  spacecraft: "#ff8c69", custom: "#b0b0ff", unknown: "#888888",
};

const _NICE_STEPS = [0.5, 1, 2, 5, 10, 15, 30, 45, 90];
const _MIN_SCALE = 0.2; // px per degree (zoomed all the way out)
const _MAX_SCALE = 60; // px per degree (zoomed all the way in)
const _HIT_PX = 8;

function _wrapDeg(d) { return ((d + 180) % 360 + 360) % 360 - 180; }
function _normRa(ra) { return (ra % 360 + 360) % 360; }
function _clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
function _niceStep(target) {
  for (const s of _NICE_STEPS) if (s >= target) return s;
  return 90;
}

class SkyMap {
  constructor(canvas, { onSelect } = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.onSelect = onSelect || (() => {});
    this.objects = [];
    this.route = []; // [{ra, dec, uid, label}] — active route overlay
    this.raCenter = 180;
    this.decCenter = 0;
    this.scale = 1.5;
    this.selectedUid = null;
    this.hoverUid = null;
    this._drag = null;
    this.resize();
    this._bindEvents();
  }

  resize() {
    const dpr = window.devicePixelRatio || 1;
    this.W = this.canvas.clientWidth || 560;
    this.H = this.canvas.clientHeight || 340;
    this.canvas.width = Math.round(this.W * dpr);
    this.canvas.height = Math.round(this.H * dpr);
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.render();
  }

  setObjects(objects, { fit = true } = {}) {
    this.objects = (objects || []).filter((o) => o.ra_deg !== null && o.dec_deg !== null);
    this._allCount = (objects || []).length;
    if (fit) this.fit(); else this.render();
  }

  setSelected(uid) { this.selectedUid = uid; this.render(); }

  // Route overlay: match each waypoint's object_uid to a loaded object's RA/Dec.
  setRoute(waypoints) {
    const byUid = new Map(this.objects.map((o) => [o.uid, o]));
    this.route = (waypoints || [])
      .map((w) => {
        const o = w.object_uid ? byUid.get(w.object_uid) : null;
        return o ? { ra: o.ra_deg, dec: o.dec_deg, uid: o.uid, label: w.label } : null;
      })
      .filter(Boolean);
    this.render();
  }

  fit() {
    if (!this.objects.length) {
      this.raCenter = 180; this.decCenter = 0;
      this.scale = Math.min(this.W / 360, this.H / 180);
      this.render();
      return;
    }
    let raMin = 360, raMax = 0, decMin = 90, decMax = -90;
    for (const o of this.objects) {
      raMin = Math.min(raMin, o.ra_deg); raMax = Math.max(raMax, o.ra_deg);
      decMin = Math.min(decMin, o.dec_deg); decMax = Math.max(decMax, o.dec_deg);
    }
    const pad = 24;
    const spanRa = Math.max(raMax - raMin, 1);
    const spanDec = Math.max(decMax - decMin, 1);
    this.raCenter = (raMin + raMax) / 2;
    this.decCenter = (decMin + decMax) / 2;
    this.scale = _clamp(
      Math.min((this.W - 2 * pad) / spanRa, (this.H - 2 * pad) / spanDec),
      _MIN_SCALE, _MAX_SCALE,
    );
    this.render();
  }

  getViewBounds() {
    const halfRa = (this.W / 2) / this.scale;
    const halfDec = (this.H / 2) / this.scale;
    const decMin = _clamp(this.decCenter - halfDec, -90, 90);
    const decMax = _clamp(this.decCenter + halfDec, -90, 90);
    if (halfRa >= 180) return { ra_min: 0, ra_max: 360, dec_min: decMin, dec_max: decMax };
    return {
      ra_min: _normRa(this.raCenter - halfRa),
      ra_max: _normRa(this.raCenter + halfRa),
      dec_min: decMin, dec_max: decMax,
    };
  }

  _project(ra, dec) {
    return {
      x: this.W / 2 + _wrapDeg(ra - this.raCenter) * this.scale,
      y: this.H / 2 - (dec - this.decCenter) * this.scale,
    };
  }

  _nearest(px, py) {
    let best = null, bestDist = _HIT_PX;
    for (const o of this.objects) {
      const p = this._project(o.ra_deg, o.dec_deg);
      const d = Math.hypot(p.x - px, p.y - py);
      if (d <= bestDist) { bestDist = d; best = o; }
    }
    return best;
  }

  // --- rendering ---

  render() {
    const ctx = this.ctx, W = this.W, H = this.H;
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = "#070a12";
    ctx.fillRect(0, 0, W, H);
    this._drawGrid();
    for (const o of this.objects) this._drawObject(o);
    this._drawRoute();
    if (this.selectedUid) this._ring(this.selectedUid, "#ffffff");
    if (this.hoverUid && this.hoverUid !== this.selectedUid) this._ring(this.hoverUid, "#5db0ff");
    this._drawHoverLabel();
  }

  _drawRoute() {
    if (this.route.length < 1) return;
    const ctx = this.ctx;
    const pts = this.route.map((w) => this._project(w.ra, w.dec));
    if (pts.length >= 2) {
      ctx.beginPath();
      ctx.moveTo(pts[0].x, pts[0].y);
      for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
      ctx.strokeStyle = "#ffd166"; ctx.lineWidth = 1.5; ctx.stroke();
    }
    for (const p of pts) {
      ctx.beginPath();
      ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
      ctx.strokeStyle = "#ffd166"; ctx.lineWidth = 1.5; ctx.stroke();
    }
  }

  _drawGrid() {
    const ctx = this.ctx, W = this.W, H = this.H;
    const spanRa = W / this.scale, spanDec = H / this.scale;
    const stepRa = _niceStep(spanRa / 8), stepDec = _niceStep(spanDec / 6);
    ctx.strokeStyle = "#16213a"; ctx.fillStyle = "#46577d"; ctx.font = "10px system-ui";
    ctx.lineWidth = 1;

    const raStart = Math.floor((this.raCenter - spanRa / 2) / stepRa) * stepRa;
    for (let g = raStart; g <= this.raCenter + spanRa / 2; g += stepRa) {
      const x = this._project(g, this.decCenter).x;
      if (x < 0 || x > W) continue;
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
      ctx.fillText(`${_normRa(g).toFixed(stepRa < 1 ? 1 : 0)}°`, x + 2, H - 4);
    }
    const decStart = Math.floor((this.decCenter - spanDec / 2) / stepDec) * stepDec;
    for (let g = decStart; g <= this.decCenter + spanDec / 2; g += stepDec) {
      if (g < -90 || g > 90) continue;
      const y = this._project(this.raCenter, g).y;
      if (y < 0 || y > H) continue;
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
      ctx.fillText(`${g.toFixed(stepDec < 1 ? 1 : 0)}°`, 2, y - 2);
    }
  }

  _drawObject(o) {
    const p = this._project(o.ra_deg, o.dec_deg);
    if (p.x < -10 || p.x > this.W + 10 || p.y < -10 || p.y > this.H + 10) return;
    const ctx = this.ctx;
    ctx.beginPath();
    ctx.arc(p.x, p.y, _pointSize(o), 0, Math.PI * 2);
    ctx.fillStyle = SKY_TYPE_COLORS[o.object_type] || SKY_TYPE_COLORS.unknown;
    ctx.fill();
  }

  _ring(uid, color) {
    const o = this.objects.find((x) => x.uid === uid);
    if (!o) return;
    const p = this._project(o.ra_deg, o.dec_deg);
    const ctx = this.ctx;
    ctx.beginPath();
    ctx.arc(p.x, p.y, _pointSize(o) + 4, 0, Math.PI * 2);
    ctx.strokeStyle = color; ctx.lineWidth = 1.5; ctx.stroke();
  }

  _drawHoverLabel() {
    const o = this.objects.find((x) => x.uid === this.hoverUid);
    if (!o) return;
    const p = this._project(o.ra_deg, o.dec_deg);
    const label = `${o.name || o.uid} (${o.object_type})`;
    const ctx = this.ctx;
    ctx.font = "11px system-ui";
    const w = ctx.measureText(label).width + 8;
    let lx = p.x + 8, ly = p.y - 8;
    if (lx + w > this.W) lx = p.x - w - 8;
    ctx.fillStyle = "rgba(8,12,22,0.9)";
    ctx.fillRect(lx, ly - 12, w, 16);
    ctx.fillStyle = "#e6ebf5";
    ctx.fillText(label, lx + 4, ly);
  }

  // --- interaction ---

  _bindEvents() {
    const c = this.canvas;
    c.addEventListener("pointerdown", (e) => {
      c.setPointerCapture(e.pointerId);
      this._drag = { x: e.offsetX, y: e.offsetY, moved: 0 };
    });
    c.addEventListener("pointermove", (e) => {
      if (this._drag) {
        const dx = e.offsetX - this._drag.x, dy = e.offsetY - this._drag.y;
        this._drag.moved += Math.abs(dx) + Math.abs(dy);
        this.raCenter = _normRa(this.raCenter - dx / this.scale);
        this.decCenter = _clamp(this.decCenter + dy / this.scale, -90, 90);
        this._drag.x = e.offsetX; this._drag.y = e.offsetY;
        this.render();
      } else {
        const hit = this._nearest(e.offsetX, e.offsetY);
        const uid = hit ? hit.uid : null;
        if (uid !== this.hoverUid) { this.hoverUid = uid; this.render(); }
        c.style.cursor = hit ? "pointer" : "grab";
      }
    });
    const endDrag = (e) => {
      if (this._drag && this._drag.moved < 4) {
        const hit = this._nearest(e.offsetX, e.offsetY);
        if (hit) this.onSelect(hit.uid);
      }
      this._drag = null;
    };
    c.addEventListener("pointerup", endDrag);
    c.addEventListener("pointercancel", () => { this._drag = null; });
    c.addEventListener("wheel", (e) => {
      e.preventDefault();
      const cx = e.offsetX, cy = e.offsetY;
      const raUnder = _normRa(this.raCenter + (cx - this.W / 2) / this.scale);
      const decUnder = this.decCenter - (cy - this.H / 2) / this.scale;
      this.scale = _clamp(this.scale * Math.pow(1.0015, -e.deltaY), _MIN_SCALE, _MAX_SCALE);
      this.raCenter = _normRa(raUnder - (cx - this.W / 2) / this.scale);
      this.decCenter = _clamp(decUnder + (cy - this.H / 2) / this.scale, -90, 90);
      this.render();
    }, { passive: false });
  }
}

function _sizeForMag(mag) {
  if (mag === null || mag === undefined) return 2.5;
  return _clamp(6 - mag / 3, 1.5, 7);
}

// Prefer a server-provided display size (visible-sector render objects); else
// derive it from apparent magnitude (full records from search / sky region).
function _pointSize(o) {
  if (o.display_size !== undefined && o.display_size !== null) {
    return _clamp(o.display_size, 1.5, 7);
  }
  return _sizeForMag(o.apparent_magnitude);
}

window.SkyMap = SkyMap;
window.SKY_TYPE_COLORS = SKY_TYPE_COLORS;
