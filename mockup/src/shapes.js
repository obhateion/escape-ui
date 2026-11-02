// ---------- the 18 figures, line for line from theme/tool/shapes.py ----------
const TAU = Math.PI * 2;
const SH_INK = [233, 233, 230];
const SHAPE_NAMES = { globe: "wire globe", checker: "checker sphere", waves: "wave field", warp: "warp grid", orbits: "orbit rings",
  target: "target", spiral: "spiral", burst: "starburst", torus: "torus", cube: "wire cube", tunnel: "tunnel", dots: "dot sphere",
  helix: "helix", lissajous: "lissajous", rose: "rose", radar: "radar", floor: "y2k floor", stars: "star stack" };
const SHAPE_LIST = Object.keys(SHAPE_NAMES);

class Pen {
  // the Pen of shapes.py on a canvas: colour, width, alpha; `mul` dims every colour (the 62 % of the card)
  constructor(c, lw, mul = 1) { this.c = c; this.lw = lw; this.col = SH_INK; this.alpha = 1; this.mul = mul; c.lineJoin = "round"; c.lineCap = "round"; }
  rgba(col, a) { const k = this.mul, c = col || this.col; return `rgba(${c[0] * k | 0},${c[1] * k | 0},${c[2] * k | 0},${Math.max(0, Math.min(1, a == null ? this.alpha : a))})`; }
  poly(pts, close) {
    const list = pts.slice(); if (close && pts.length && pts[0]) list.push(pts[0]);
    let run = [];
    for (const p of list) { if (!p) { this.run(run); run = []; } else run.push(p); }
    this.run(run);
  }
  run(run) {
    if (run.length < 2) return;
    const c = this.c; c.strokeStyle = this.rgba(); c.lineWidth = Math.max(0.5, this.lw);
    c.beginPath(); c.moveTo(run[0][0], run[0][1]); for (let i = 1; i < run.length; i++) c.lineTo(run[i][0], run[i][1]); c.stroke();
  }
  line(x0, y0, x1, y1) { this.run([[x0, y0], [x1, y1]]); }
  ellipse(cx, cy, rx, ry, rot = 0, a0 = 0, a1 = TAU, n = 96) {
    const pts = [];
    for (let i = 0; i <= n; i++) {
      const a = a0 + (a1 - a0) * i / n, x = Math.cos(a) * rx, y = Math.sin(a) * ry;
      pts.push([cx + x * Math.cos(rot) - y * Math.sin(rot), cy + x * Math.sin(rot) + y * Math.cos(rot)]);
    }
    this.poly(pts);
  }
  circle(cx, cy, r) { this.ellipse(cx, cy, r, r); }
  arc(cx, cy, r, a0, a1) { this.ellipse(cx, cy, r, r, 0, a0, a1, Math.max(8, Math.floor(Math.abs(a1 - a0) * 30))); }
  dot(cx, cy, r, col, a) { const c = this.c; c.fillStyle = this.rgba(col, a); c.beginPath(); c.arc(cx, cy, Math.max(0.5, r), 0, TAU); c.fill(); }
  fillPoly(pts, col, a) { const c = this.c; c.fillStyle = this.rgba(col, a); c.beginPath(); c.moveTo(pts[0][0], pts[0][1]); for (const p of pts.slice(1)) c.lineTo(p[0], p[1]); c.closePath(); c.fill(); }
  rect(x, y, w, h) { this.poly([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], true); }
  dashedCircle(cx, cy, r, dash, gap, offset) {
    const circ = TAU * r, step = dash + gap; let s = -(((offset % step) + step) % step);
    while (s < circ) { const a0 = Math.max(0, s) / r, a1 = Math.min(circ, s + dash) / r; if (a1 > a0) this.arc(cx, cy, r, a0, a1); s += step; }
  }
}
function sphere(cx, cy, R, lat, lon, t) { const l = lon + t, x = Math.cos(lat) * Math.sin(l), z = Math.cos(lat) * Math.cos(l); return z < -0.02 ? null : [cx + R * x, cy - R * Math.sin(lat), z]; }
function rot3(p, ax, ay) { const [x, y, z] = p, c = Math.cos(ax), s = Math.sin(ax), y1 = y * c - z * s, z1 = y * s + z * c, c2 = Math.cos(ay), s2 = Math.sin(ay); return [x * c2 + z1 * s2, y1, -x * s2 + z1 * c2]; }
const SHAPES = {
  globe(p, cx, cy, R, t, a) {
    p.circle(cx, cy, R);
    for (let k = 0; k < 12; k++) { const lon = k * TAU / 12, pts = []; for (let i = 0; i < 41; i++) pts.push(sphere(cx, cy, R, -Math.PI / 2 + i * Math.PI / 40, lon, t)); p.poly(pts); }
    for (let k = 1; k < 8; k++) { const lat = -Math.PI / 2 + k * Math.PI / 8; p.ellipse(cx, cy - R * Math.sin(lat), R * Math.cos(lat), R * Math.cos(lat) * 0.16, 0, 0, Math.PI); }
    p.col = a; p.ellipse(cx, cy, R * 1.32, R * 0.32, -0.32);
  },
  checker(p, cx, cy, R, t, a) {
    const nlat = 10, nlon = 16;
    for (let i = 0; i < nlat; i++) for (let j = 0; j < nlon; j++) {
      if ((i + j) % 2) continue;
      const la0 = -Math.PI / 2 + i * Math.PI / nlat, la1 = la0 + Math.PI / nlat, lo0 = j * TAU / nlon, lo1 = lo0 + TAU / nlon;
      const q = [sphere(cx, cy, R, la0, lo0, t), sphere(cx, cy, R, la0, lo1, t), sphere(cx, cy, R, la1, lo1, t), sphere(cx, cy, R, la1, lo0, t)];
      if (q.some(v => !v)) continue;
      p.fillPoly(q, null, 0.25 + 0.75 * Math.min(1, q[0][2] * 1.4));
    }
    p.circle(cx, cy, R); p.dot(cx + R * 0.92, cy - R * 0.92, 7, a, 1);
  },
  waves(p, cx, cy, R, t, a) {
    for (let k = 0; k < 13; k++) {
      const y0 = cy - R + k * (2 * R / 12), pts = []; let x = -R * 1.3;
      while (x <= R * 1.3) { const env = Math.exp(-(x * x) / (R * R * 0.6)); pts.push([cx + x, y0 + Math.sin(x * 0.03 + t * 3 + k * 0.5) * 34 * env]); x += 6; }
      p.col = k === 6 ? a : SH_INK; p.poly(pts);
    }
    p.col = SH_INK;
  },
  warp(p, cx, cy, R, t, a) {
    const n = 12, s = 2 * R / n;
    const d = (x, y) => { const r = Math.hypot(x, y) / R, k = 1 + 0.35 * Math.sin(r * 4 - t * 2) * Math.max(0, 1 - r); return [cx + x * k, cy + y * k]; };
    for (let i = 0; i <= n; i++) { const pts = [], pts2 = []; for (let j = 0; j < 41; j++) { const u = -R + j * 2 * R / 40, v = -R + i * s; pts.push(d(u, v)); pts2.push(d(v, u)); } p.poly(pts); p.poly(pts2); }
    p.col = a; p.rect(cx - R - 10, cy - R - 10, 2 * R + 20, 2 * R + 20);
  },
  orbits(p, cx, cy, R, t, a) {
    p.circle(cx, cy, R * 0.22);
    [[0, 1], [1.05, -1], [2.1, 2]].forEach(([rot, sp], i) => {
      p.ellipse(cx, cy, R, R * 0.3, rot);
      const ph = t * sp + i * 2, x = Math.cos(ph) * R, y = Math.sin(ph) * R * 0.3;
      p.dot(cx + x * Math.cos(rot) - y * Math.sin(rot), cy + x * Math.sin(rot) + y * Math.cos(rot), 8, i === 0 ? a : SH_INK);
    });
  },
  target(p, cx, cy, R, t, a) {
    for (let k = 1; k < 6; k++) p.circle(cx, cy, R * k / 5);
    p.dashedCircle(cx, cy, R * 1.18, 4, 10, -t * 182 / TAU);
    for (let k = 0; k < 4; k++) { const an = k * Math.PI / 2; p.line(cx + Math.cos(an) * R * 1.05, cy + Math.sin(an) * R * 1.05, cx + Math.cos(an) * R * 1.32, cy + Math.sin(an) * R * 1.32); }
    p.col = a; p.arc(cx, cy, R * 1.18, t, t + 0.8);
  },
  spiral(p, cx, cy, R, t, a) {
    const pts = []; for (let i = 0; i < 601; i++) { const th = i / 600 * TAU * 7, r = R * i / 600; pts.push([cx + Math.cos(th - t * 1.5) * r, cy + Math.sin(th - t * 1.5) * r]); }
    p.poly(pts); p.dot(cx + Math.cos(TAU * 7 - t * 1.5) * R, cy + Math.sin(TAU * 7 - t * 1.5) * R, 8, a);
  },
  burst(p, cx, cy, R, t, a) {
    for (let k = 0; k < 72; k++) { const an = k * TAU / 72 + t / 36, ln = R * (0.45 + 0.55 * Math.abs(Math.sin(k * 1.7 + t * (1.7 + Math.PI) / Math.PI))); p.line(cx + Math.cos(an) * R * 0.3, cy + Math.sin(an) * R * 0.3, cx + Math.cos(an) * ln, cy + Math.sin(an) * ln); }
    p.col = a; p.circle(cx, cy, R * 0.3);
  },
  torus(p, cx, cy, R, t, a) {
    const ring = (u0, isU) => {
      const pts = [];
      for (let k = 0; k < 49; k++) {
        const u = isU ? u0 : k * TAU / 48, v = isU ? k * TAU / 48 : u0, uu = u + t / 24;
        const q = rot3([(1 + 0.42 * Math.cos(v)) * Math.cos(uu), 0.42 * Math.sin(v), (1 + 0.42 * Math.cos(v)) * Math.sin(uu)], 1.0, 0.3);
        pts.push(q[2] < -0.55 ? null : [cx + q[0] * R * 0.72, cy + q[1] * R * 0.72]);
      }
      p.poly(pts);
    };
    for (let i = 0; i < 24; i++) ring(i * TAU / 24, true);
    p.col = a; for (let i = 0; i < 2; i++) ring(i * Math.PI, false);
  },
  cube(p, cx, cy, R, t, a) {
    const box = (s, col) => {
      p.col = col; const c = Math.cos(t / 4), sn = Math.sin(t / 4), v = [];
      for (const x of [-1, 1]) for (const y of [-1, 1]) for (const z of [-1, 1]) v.push(rot3([(x * c - z * sn) * s, y * s, (x * sn + z * c) * s], 0.6, 0.5));
      for (const [i, j] of [[0, 1], [0, 2], [0, 4], [1, 3], [1, 5], [2, 3], [2, 6], [3, 7], [4, 5], [4, 6], [5, 7], [6, 7]]) p.line(cx + v[i][0] * R * 0.6, cy + v[i][1] * R * 0.6, cx + v[j][0] * R * 0.6, cy + v[j][1] * R * 0.6);
    };
    box(1, SH_INK); box(0.5, a);
  },
  tunnel(p, cx, cy, R, t, a) {
    for (let k = 0; k < 14; k++) { const f = (((k / 14 + t * 0.15) % 1) + 1) % 1, s = Math.pow(f, 2.2) * R * 1.3; p.alpha = Math.min(1, f * 1.6); p.rect(cx - s, cy - s * 0.75, 2 * s, 1.5 * s); }
    p.alpha = 1; p.col = a;
    p.line(cx - R * 1.3, cy - R * 0.98, cx + R * 1.3, cy + R * 0.98); p.line(cx + R * 1.3, cy - R * 0.98, cx - R * 1.3, cy + R * 0.98);
  },
  dots(p, cx, cy, R, t, a) {
    const n = 420, ga = Math.PI * (3 - Math.sqrt(5));
    for (let i = 0; i < n; i++) {
      const y = 1 - (i / (n - 1)) * 2, r0 = Math.sqrt(Math.max(0, 1 - y * y)), th = ga * i, q = rot3([Math.cos(th) * r0, y, Math.sin(th) * r0], 0.35, t);
      if (q[2] < -0.1) continue;
      p.dot(cx + q[0] * R, cy + q[1] * R, 2 + 3 * q[2], i % 37 === 0 ? a : SH_INK, 0.3 + 0.7 * q[2]);
    }
  },
  helix(p, cx, cy, R, t, a) {
    for (let s = 0; s < 2; s++) { const pts = []; for (let k = 0; k < 121; k++) { const y = cy - R * 1.2 + k * 2.4 * R / 120, ph = k * 0.16 + t * 2 + s * Math.PI; pts.push([cx + Math.sin(ph) * R * 0.5, y]); } p.poly(pts); }
    for (let k = 0; k < 121; k += 8) { const y = cy - R * 1.2 + k * 2.4 * R / 120, ph = k * 0.16 + t * 2; p.col = k % 24 ? SH_INK : a; p.line(cx + Math.sin(ph) * R * 0.5, y, cx - Math.sin(ph) * R * 0.5, y); }
    p.col = SH_INK;
  },
  lissajous(p, cx, cy, R, t, a) {
    const pts = []; for (let k = 0; k < 801; k++) pts.push([cx + Math.sin(3 * (k / 800 * TAU) + t) * R, cy + Math.sin(4 * (k / 800 * TAU)) * R * 0.8]);
    p.poly(pts); p.col = a; p.rect(cx - R - 14, cy - R * 0.8 - 14, 2 * R + 28, 1.6 * R + 28);
  },
  rose(p, cx, cy, R, t, a) {
    const pts = []; for (let k = 0; k < 901; k++) { const th = k / 900 * TAU * 2, r = R * Math.cos(2.5 * th); pts.push([cx + Math.cos(th + t * 0.4) * r, cy + Math.sin(th + t * 0.4) * r]); }
    p.poly(pts); p.dot(cx, cy, 7, a);
  },
  radar(p, cx, cy, R, t, a) {
    for (let k = 1; k < 5; k++) p.circle(cx, cy, R * k / 4);
    p.line(cx - R, cy, cx + R, cy); p.line(cx, cy - R, cx, cy + R);
    const an = t * 2.2;
    for (let k = 0; k < 24; k++) { p.alpha = (1 - k / 24) * 0.6; p.line(cx, cy, cx + Math.cos(an - k * 0.03) * R, cy + Math.sin(an - k * 0.03) * R); }
    p.alpha = 1;
    for (const [b, d] of [[0.6, 0.8], [2.4, 0.5], [4.1, 0.7]]) p.dot(cx + Math.cos(b) * R * d, cy + Math.sin(b) * R * d, 6, a);
  },
  floor(p, cx, cy, R, t, a) {
    const hz = cy - R * 0.1, bottom = cy + R * 1.2;
    for (let k = -10; k < 11; k++) p.line(cx + k * 8, hz, cx + k * R * 0.32, bottom);
    for (let k = 0; k < 12; k++) { const f = Math.pow((((k / 12 + t * 0.2) % 1) + 1) % 1, 2), y = hz + f * (bottom - hz); p.alpha = f; p.line(cx - R * 3.4 * f - 20, y, cx + R * 3.4 * f + 20, y); }
    p.alpha = 1; p.col = a;
    const r = R * 0.6; p.arc(cx, hz, r, Math.PI, TAU);
    for (let k = 1; k < 9; k++) { const y = hz - k * k * 1.6 - 4; if (hz - y < r) { const half = Math.sqrt(r * r - (hz - y) ** 2); p.line(cx - half, y, cx + half, y); } }
  },
  stars(p, cx, cy, R, t, a) {
    const star = (r, n, rot) => { const pts = []; for (let k = 0; k < n * 2 + 1; k++) { const rr = k % 2 ? r * 0.45 : r, an = rot + k * Math.PI / n; pts.push([cx + Math.cos(an) * rr, cy + Math.sin(an) * rr]); } p.poly(pts); };
    for (let k = 0; k < 6; k++) { const n = 5 + (k % 3); star(R * (1 - k * 0.15), n, t * 4 / n * (k % 2 ? -1 : 1) + k); }
    p.col = a; star(R * 0.18, 4, t);
  },
};
// shapes.render(): a frame at (w, h) on black; ss=2 there means line widths are round(lw*2)/2 here
function renderShape(c, shape, t, accent, w, h, lw = 2, R = null, mul = 1, x0 = 0, y0 = 0) {
  c.save(); c.translate(x0, y0);
  const p = new Pen(c, Math.round(lw * 2) / 2, mul);
  (SHAPES[shape] || SHAPES.globe)(p, w / 2, h / 2, R || Math.min(w, h) * 0.36, t, accent);
  c.restore();
}
// LOOP of gen.py: the shortest seamless span of t and how long it takes (seconds)
const LOOP = { globe: [TAU / 12, 2.5], checker: [Math.PI / 4, 4], waves: [TAU / 3, 3], warp: [Math.PI, 3.5], orbits: [TAU, 12], target: [TAU, 12],
  spiral: [4 * Math.PI / 3, 8], burst: [Math.PI, 6], torus: [TAU, 3], cube: [TAU, 3.5], tunnel: [1 / 14 / 0.15, 3], dots: [TAU, 14],
  helix: [Math.PI, 3], lissajous: [Math.PI / 2, 3], rose: [Math.PI, 6], radar: [TAU / 2.2, 6], floor: [1 / 12 / 0.2, 2.5], stars: [Math.PI / 2, 6] };
