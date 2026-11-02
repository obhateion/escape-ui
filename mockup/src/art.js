// ---------- theme/tool/art.py + the drawing half of gen.py, on canvases ----------
const VOID = [0, 0, 0], INK = [242, 242, 238], DIM = [110, 110, 107];
const W = 1024, H = 768, HERO = [430, 96, 560, 470], FIG_LW = 2.2;
const PALETTE = [["white", "White", [242, 242, 238]], ["red", "Red", [255, 42, 31]], ["orange", "Orange", [255, 106, 19]],
  ["yellow", "Yellow", [255, 214, 10]], ["acid", "Acid", [216, 255, 60]], ["green", "Green", [40, 230, 120]],
  ["ice", "Ice", [143, 220, 255]], ["blue", "Blue", [52, 120, 255]], ["violet", "Violet", [185, 140, 255]], ["pink", "Pink", [255, 70, 170]]];
const ACCENT_RGB = Object.fromEntries(PALETTE.map(([s, , c]) => [s, c]));
const KATA = { ALL: "エスケープ", GAMES: "ゲーム", SOUND: "サウンド", APPS: "アプリ" };
const KANJI = { ALL: "脱出", GAMES: "遊", SOUND: "音", APPS: "道具" };
const MORE_KATA = ["プレイ", "セーブ", "スタート", "ロード", "ハイスコア", "データ", "コンティニュー", "ステージ", "ボーナス", "サウンド", "ゲーム"];
const MORE_KANJI = ["遊", "音", "夢", "光", "道", "星", "波", "脱出", "注意", "危険", "再生"];
const STAMPS = [["EXPLICIT", "ESCAPE", "CONTENT"], ["HANDLE", "WITH", "CARE"], ["HIGH", "VOLTAGE", "SOUND"], ["NO", "SIGNAL", "FOUND"],
  ["SYSTEM", "OVER", "RIDE"], ["PLAY", "AT OWN", "RISK"], ["LOW", "BATT", "MODE"], ["DO NOT", "PRESS", "START"],
  ["FREE", "TO", "LEAVE"], ["LOUD", "AND", "CLEAR"], ["ZERO", "LAG", "ZONE"], ["NIGHT", "SHIFT", "ONLY"], ["NOT A", "TOY", "ACTUALLY"]];
const PILLS = ["online", "hi-fi", "stereo", "local", "beta", "rom ok", "8-bit", "v2.0", "no save", "loop", "live", "x-001", "dual",
  "rgb", "mono", "4:3", "no.01", "tilt", "lo-fi", "jp", "save ok", "turbo", "cpu 1", "zero", "new"];
const CHEVS = [">>>", "<<<", "///", "+++", ">>|", "<>", "::", "=>>", "///>"];
const BLURB = { ALL: "Everything on the card in one list.", APPS: "Tools, launchers and ports that are not games.",
  GAMES: "Games only, from every console and port.", SOUND: "Trackers, synths and sequencers." };
const DEFAULT_FIG = { ALL: "globe", APPS: "cube", GAMES: "checker", SOUND: "waves", "custom-collections": "orbits" };

const css = (c, a = 1) => `rgba(${c[0]},${c[1]},${c[2]},${c.length > 3 ? c[3] / 255 : a})`;
const pad2 = n => String(n).padStart(2, "0");
function mk(w, h) { const c = document.createElement("canvas"); c.width = Math.max(1, Math.ceil(w)); c.height = Math.max(1, Math.ceil(h)); return c; }
const ctx = cv => cv.getContext("2d");

// fonts: the same families the theme ships (PIL sizes are em sizes in px, as in CSS)
const FAMILY = { dot: '"Doto"', px: '"Silkscreen"', pxb: '"Silkscreen"', grot: '"Archivo"', jp: '"Noto Sans JP"' };
function font(kind, size, wght) { const w = kind === "pxb" ? 700 : (wght || (kind === "dot" ? 400 : 400)); return { s: `${w} ${size}px ${FAMILY[kind]}`, size }; }
function textLen(f, s) { const c = MEASURE; c.font = f.s; return c.measureText(s).width; }
const MEASURE = ctx(mk(4, 4));
// Pillow anchors: horizontal l/m/r, vertical a(ascender)/t/m(middle of ascender..descender)/s(baseline)/d
function text(c, x, y, s, f, fill, anchor = "la") {
  c.font = f.s; c.fillStyle = Array.isArray(fill) ? css(fill) : fill;
  c.textAlign = { l: "left", m: "center", r: "right" }[anchor[0]];
  c.textBaseline = "alphabetic";
  const m = c.measureText(s), asc = m.fontBoundingBoxAscent, desc = m.fontBoundingBoxDescent, v = anchor[1];
  const by = v === "a" || v === "t" ? y + asc : v === "m" ? y + (asc - desc) / 2 : v === "d" ? y - desc : y;
  c.fillText(s, x, by);
}
function textSpaced(c, x, y, s, f, fill, anchor, spacing) { for (const ch of s) { text(c, x, y, ch, f, fill, anchor); x += textLen(f, ch) + spacing; } }
function textW(f, s, spacing = 0) { return spacing ? [...s].reduce((a, ch) => a + textLen(f, ch) + spacing, 0) - spacing : textLen(f, s); }

function poly(c, pts, fill, stroke, lw = 1) { c.beginPath(); c.moveTo(pts[0][0], pts[0][1]); for (const p of pts.slice(1)) c.lineTo(p[0], p[1]); c.closePath(); if (fill) { c.fillStyle = css(fill); c.fill(); } if (stroke) { c.strokeStyle = css(stroke); c.lineWidth = lw; c.stroke(); } }
function rect(c, x0, y0, x1, y1, fill, outline, w = 1) {   // Pillow's inclusive [x0, y0, x1, y1]
  if (fill) { c.fillStyle = css(fill); c.fillRect(x0, y0, x1 - x0 + 1, y1 - y0 + 1); }
  if (outline) { c.strokeStyle = css(outline); c.lineWidth = w; c.strokeRect(x0 + w / 2, y0 + w / 2, x1 - x0 + 1 - w, y1 - y0 + 1 - w); }
}
function ellipse(c, x0, y0, x1, y1, fill, outline, w = 1) {
  c.beginPath(); c.ellipse((x0 + x1 + 1) / 2, (y0 + y1 + 1) / 2, Math.max(0.1, (x1 - x0 + 1 - w) / 2), Math.max(0.1, (y1 - y0 + 1 - w) / 2), 0, 0, TAU);
  if (fill) { c.fillStyle = css(fill); c.fill(); } if (outline) { c.strokeStyle = css(outline); c.lineWidth = w; c.stroke(); }
}
function rrect(c, x0, y0, x1, y1, r, fill, outline) {
  c.beginPath(); c.roundRect(x0 + 0.5, y0 + 0.5, x1 - x0, y1 - y0, r);
  if (fill) { c.fillStyle = css(fill); c.fill(); } if (outline) { c.strokeStyle = css(outline); c.lineWidth = 1; c.stroke(); }
}
function line(c, pts, col, w = 1) { c.beginPath(); c.moveTo(pts[0][0] + 0.5, pts[0][1] + 0.5); for (const p of pts.slice(1)) c.lineTo(p[0] + 0.5, p[1] + 0.5); c.strokeStyle = css(col); c.lineWidth = w; c.stroke(); }
// Image.rotate(deg, expand=True): counter-clockwise, new box = the rotated corners' bounds
function rotated(src, deg) {
  if (!deg) return src;
  const a = deg * Math.PI / 180, w = src.width, h = src.height, cs = Math.cos(a), sn = Math.sin(a);
  const xs = [], ys = [];
  for (const [x, y] of [[0, 0], [w, 0], [w, h], [0, h]]) { const dx = x - w / 2, dy = y - h / 2; xs.push(dx * cs + dy * sn); ys.push(-dx * sn + dy * cs); }
  const nw = Math.ceil(Math.max(...xs)) - Math.floor(Math.min(...xs)), nh = Math.ceil(Math.max(...ys)) - Math.floor(Math.min(...ys));
  const out = mk(nw, nh), c = ctx(out); c.translate(nw / 2, nh / 2); c.rotate(-a); c.drawImage(src, -w / 2, -h / 2); return out;
}
function bbox(cv) {   // Image.getbbox() on the alpha
  const d = ctx(cv).getImageData(0, 0, cv.width, cv.height).data; let x0 = cv.width, y0 = cv.height, x1 = -1, y1 = -1;
  for (let y = 0; y < cv.height; y++) for (let x = 0; x < cv.width; x++) if (d[(y * cv.width + x) * 4 + 3]) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
  return x1 < 0 ? [0, 0, 1, 1] : [x0, y0, x1 + 1, y1 + 1];
}
function crop(cv, b) { const out = mk(b[2] - b[0], b[3] - b[1]); ctx(out).drawImage(cv, -b[0], -b[1]); return out; }

// ---------- sticker parts ----------
function pill(c, x, y, s, filled = false, col = INK) {
  const f = font("px", 9), w = textW(f, s.toUpperCase()) + 16;
  rrect(c, x, y, x + w, y + 18, 9, filled ? col : null, col);
  text(c, x + 8, y + 9, s.toUpperCase(), f, filled ? VOID : col, "lm");
  return w;
}
function sparkle(c, cx, cy, r, col = INK) { const pts = []; for (let k = 0; k < 8; k++) { const an = k * Math.PI / 4 - Math.PI / 2, rr = k % 2 === 0 ? r : r * 0.22; pts.push([cx + Math.cos(an) * rr, cy + Math.sin(an) * rr]); } poly(c, pts, col); }
function warnTri(c, x, y, w = 22, h = 20, col = INK, mark = VOID) { poly(c, [[x + w / 2, y], [x + w, y + h], [x, y + h]], col); text(c, x + w / 2, y + h * 0.66, "!", font("pxb", 9), mark, "mm"); }
function stripes(c, x, y, w = 46, h = 9, col = INK) { for (let k = -h; k < w; k += 6) poly(c, [[x + k, y + h], [x + k + 3, y + h], [x + k + 3 + h, y], [x + k + h, y]], col); }
function stripesLayer(w, h, col) { const cv = mk(w, h); stripes(ctx(cv), 0, 0, w, h, col); return cv; }
function bars(c, x, y, w = 64, h = 14, col = INK, seed = 0) {
  const r = new PyRandom(seed); let xx = x;
  while (xx < x + w) { const bw = r.choice([1, 1, 2, 3]); rect(c, xx, y, xx + bw - 1, y + h, col); xx += bw + r.choice([1, 2, 3]); }
}
function vtext(c, x, y, s, f, fill, gap = 4) { for (const ch of s) { text(c, x, y, ch, f, fill, "mt"); y += f.size + gap; } }
function stamp(kind, words, accent) {
  const [a, b, cc] = words; let cv, c;
  if (kind === 0) {
    const fb = font("dot", 26, 900), fs = font("px", 10), w = Math.floor(Math.max(textW(fb, a), textW(fb, cc), textW(fs, b)) + 28), h = 104;
    cv = mk(w, h); c = ctx(cv);
    rect(c, 0, 0, w - 1, h - 1, VOID, INK, 2); text(c, w / 2, 22, a, fb, INK, "mm");
    rect(c, 2, 38, w - 3, 62, INK); text(c, w / 2, 50, b, fs, VOID, "mm"); text(c, w / 2, 82, cc, fb, INK, "mm");
  } else if (kind === 1) {
    cv = mk(112, 112); c = ctx(cv);
    ellipse(c, 0, 0, 111, 111, VOID, INK, 2); ellipse(c, 7, 7, 104, 104, null, INK, 1);
    text(c, 56, 30, a, font("px", 8), INK, "mm"); text(c, 56, 56, b, font("dot", 22, 900), accent, "mm"); text(c, 56, 82, cc, font("px", 8), INK, "mm");
  } else {
    const fb = font("dot", 24, 900), w = Math.floor(textW(fb, b) + 54), h = 58; cv = mk(w, h); c = ctx(cv);
    poly(c, [[0, h / 2], [18, 0], [w - 1, 0], [w - 1, h - 1], [18, h - 1]], INK); ellipse(c, 10, h / 2 - 5, 20, h / 2 + 5, VOID);
    text(c, 30, 20, b, fb, VOID, "lm"); text(c, 30, 44, a + " " + cc, font("px", 8), VOID, "lm");
  }
  return cv;
}
function hazardBand(w, h, col = INK) { const cv = mk(w, h), c = ctx(cv); for (let k = -h; k < w; k += 18) poly(c, [[k, h], [k + 9, h], [k + 9 + h, 0], [k + h, 0]], col); return cv; }
function badge(num, col = INK) { const cv = mk(74, 74), c = ctx(cv); ellipse(c, 0, 0, 73, 73, VOID, col); ellipse(c, 5, 5, 68, 68, null, col); text(c, 37, 24, "NO.", font("px", 8), col, "mm"); text(c, 37, 46, num, font("dot", 26, 900), col, "mm"); return cv; }
function disc(label, accent) {
  const cv = mk(96, 96), c = ctx(cv); ellipse(c, 0, 0, 95, 95, VOID, INK);
  for (const r of [40, 34, 28]) ellipse(c, 48 - r, 48 - r, 48 + r, 48 + r, null, [80, 80, 78]);
  ellipse(c, 38, 38, 58, 58, null, accent, 2); text(c, 48, 72, label[0], font("px", 7), INK, "mm"); text(c, 48, 81, label[1], font("px", 7), INK, "mm"); return cv;
}
function jpLabel(kanji, word) {
  const fj = font("jp", 26), w = Math.floor(Math.max(textW(fj, kanji), textW(font("px", 8), word.toUpperCase())) + 22), h = 70, cv = mk(w, h), c = ctx(cv);
  rect(c, 0, 0, w - 1, h - 1, VOID, INK, 2); text(c, w / 2, 26, kanji, fj, INK, "mm");
  rect(c, 2, h - 22, w - 3, h - 3, INK); text(c, w / 2, h - 12, word.toUpperCase(), font("px", 8), VOID, "mm"); return cv;
}
function checkerStrip(w = 120, h = 16, col = INK) { const cv = mk(w, h), c = ctx(cv), s = h / 2 | 0; for (let i = 0; i < w; i += s) for (let j = 0; j < 2; j++) if (((i / s | 0) + j) % 2 === 0) rect(c, i, j * s, i + s - 1, j * s + s - 1, col); rect(c, 0, 0, w - 1, h - 1, null, col); return cv; }
function arrowStk(word, arrow) {
  const f = font("px", 10), w = Math.floor(textW(f, word.toUpperCase()) + 44), h = 30, cv = mk(w, h), c = ctx(cv);
  rect(c, 0, 0, w - 1, h - 1, VOID, INK); rect(c, w - 30, 0, w - 1, h - 1, INK);
  text(c, 8, h / 2, word.toUpperCase(), f, INK, "lm"); text(c, w - 15, h / 2, arrow, font("jp", 18), VOID, "mm"); return cv;
}
function barStk(num) { const cv = mk(130, 34), c = ctx(cv); rect(c, 0, 0, 129, 33, VOID, INK); bars(c, 6, 4, 118, 16, INK, num); text(c, 65, 27, num, font("px", 8), INK, "mm"); return cv; }
function miniFigure(shape, t, accent, size = 120) {
  const cv = mk(size, size), c = ctx(cv);
  ellipse(c, 0, 0, size - 1, size - 1, VOID);
  c.save(); c.beginPath(); c.ellipse(size / 2, size / 2, size / 2 - 2, size / 2 - 2, 0, 0, TAU); c.clip();
  c.scale(0.5, 0.5); renderShape(c, shape, t, accent, size * 2, size * 2, 2, size * 0.8); c.restore();   // Pillow: width round(1.6) = 2 at 2x, then halved
  ellipse(c, 0, 0, size - 1, size - 1, null, INK); return cv;
}
function vinyl(content, round, padd = 6, rot = 0) {
  const w = content.width, h = content.height, Wd = w + padd * 2, Hd = h + padd * 2;
  let base = mk(Wd, Hd); const b = ctx(base);
  if (round) ellipse(b, 0, 0, Wd - 1, Hd - 1, [8, 8, 8]); else rrect(b, 0, 0, Wd - 1, Hd - 1, 7, [8, 8, 8]);
  b.drawImage(content, padd, padd);
  base = rotated(base, rot);
  const sh = mk(base.width + 24, base.height + 24), s = ctx(sh);
  const blk = mk(base.width, base.height), k = ctx(blk); k.drawImage(base, 0, 0); k.globalCompositeOperation = "source-in"; k.fillStyle = "rgba(0,0,0,.65)"; k.fillRect(0, 0, blk.width, blk.height);
  s.filter = "blur(5px)"; s.drawImage(blk, 14, 16); s.filter = "none"; s.drawImage(base, 12, 12);
  return sh;
}

// ---------- the 16 cover patterns ----------
const grey = (v, a = 255) => { v = Math.max(0, Math.min(255, v | 0)); return [v, v, v, a]; };
function tile(Wd, Hd, s, bg, draw, rot = 0) {
  const t = mk(s, s), tc = ctx(t); rect(tc, 0, 0, s - 1, s - 1, grey(bg)); draw(tc, s);
  const big = mk(Wd * 2, Hd * 2), bc = ctx(big);
  for (let y = 0; y < Hd * 2; y += s) for (let x = 0; x < Wd * 2; x += s) bc.drawImage(t, x, y);
  let src = big;
  if (rot) { const r = mk(Wd * 2, Hd * 2), rc = ctx(r); rect(rc, 0, 0, Wd * 2 - 1, Hd * 2 - 1, VOID); rc.translate(Wd, Hd); rc.rotate(-rot); rc.drawImage(big, -Wd, -Hd); src = r; }
  return crop(src, [Wd / 2 | 0, Hd / 2 | 0, (Wd / 2 | 0) + Wd, (Hd / 2 | 0) + Hd]);
}
const PATTERNS = {
  perforated(Wd, Hd) {
    const cv = mk(Wd, Hd), c = ctx(cv); rect(c, 0, 0, Wd - 1, Hd - 1, grey(66)); const s = 22; let row = 0, y = s / 2;
    while (y < Hd) { let x = row % 2 ? s : s / 2; while (x < Wd) { ellipse(c, x - 6, y - 6, x + 6, y + 6, grey(10)); c.beginPath(); c.ellipse(x + 0.5, y + 1.5, 6, 6, 0, 18 * Math.PI / 180, 162 * Math.PI / 180); c.closePath(); c.fillStyle = css(grey(110, 150)); c.fill(); x += s; } y += s; row++; }
    return cv;
  },
  carbon(Wd, Hd) {
    const cv = mk(Wd, Hd), c = ctx(cv); rect(c, 0, 0, Wd - 1, Hd - 1, grey(20)); const s = 16;
    for (let y = 0; y < Hd; y += s) for (let x = 0; x < Wd; x += s) {
      const horiz = ((x + y) / s | 0) % 2;
      for (let i = 0; i < s - 2; i++) { const v = 28 + 42 * (1 - Math.abs((i / (s - 3)) * 2 - 1)); if (horiz) line(c, [[x + 1 + i, y + 1], [x + 1 + i, y + s - 2]], grey(v)); else line(c, [[x + 1, y + 1 + i], [x + s - 2, y + 1 + i]], grey(v)); }
    }
    return cv;
  },
  stripes: (Wd, Hd) => tile(Wd, Hd, 28, 46, (k, s) => rect(k, 0, 0, s / 2, s, grey(66)), Math.PI / 4),
  hazard: (Wd, Hd) => tile(Wd, Hd, 64, 36, (k, s) => rect(k, 0, 0, s / 2, s, grey(78)), -Math.PI / 4),
  pinstripe: (Wd, Hd) => tile(Wd, Hd, 12, 40, (k, s) => rect(k, 0, 0, 1, s, grey(72))),
  crosses: (Wd, Hd) => tile(Wd, Hd, 36, 42, (k, s) => { rect(k, s / 2 - 1.5, s / 2 - 9, s / 2 + 1.5, s / 2 + 9, grey(96)); rect(k, s / 2 - 9, s / 2 - 1.5, s / 2 + 9, s / 2 + 1.5, grey(96)); }),
  xmarks: (Wd, Hd) => tile(Wd, Hd, 56, 50, (k, s) => { for (const [x, y] of [[s / 4, s / 4], [s * 3 / 4, s * 3 / 4]]) { line(k, [[x - 7, y - 7], [x + 7, y + 7]], grey(90), 3); line(k, [[x + 7, y - 7], [x - 7, y + 7]], grey(90), 3); } }),
  grid: (Wd, Hd) => tile(Wd, Hd, 40, 30, (k, s) => { rect(k, 0, 0, s, 1, grey(56)); rect(k, 0, 0, 1, s, grey(56)); rect(k, 0, 0, 2, 2, grey(120)); }),
  checker: (Wd, Hd) => tile(Wd, Hd, 48, 38, (k, s) => { rect(k, 0, 0, s / 2 - 1, s / 2 - 1, grey(60)); rect(k, s / 2, s / 2, s - 1, s - 1, grey(60)); }),
  dots: (Wd, Hd) => tile(Wd, Hd, 20, 34, (k, s) => { for (const [x, y] of [[s / 4, s / 4], [s * 3 / 4, s * 3 / 4]]) ellipse(k, x - 2.6, y - 2.6, x + 2.6, y + 2.6, grey(86)); }),
  chevrons: (Wd, Hd) => tile(Wd, Hd, 40, 44, (k, s) => { for (const y of [s * 0.25, s * 0.75]) line(k, [[-2, y + 10], [s / 2, y - 6], [s + 2, y + 10]], grey(78), 5); }),
  zigzag: (Wd, Hd) => tile(Wd, Hd, 32, 52, (k, s) => line(k, [[0, s * 0.7], [s / 2, s * 0.3], [s, s * 0.7]], grey(30), 3)),
  diamonds: (Wd, Hd) => tile(Wd, Hd, 36, 40, (k, s) => { poly(k, [[s / 2, 4], [s - 4, s / 2], [s / 2, s - 4], [4, s / 2]], null, grey(80)); rect(k, s / 2 - 2, s / 2 - 2, s / 2 + 2, s / 2 + 2, grey(80)); }),
  waves: (Wd, Hd) => tile(Wd, Hd, 48, 40, (k, s) => { for (const y0 of [s * 0.25, s * 0.75]) { const pts = []; for (let x = 0; x <= s; x += 2) pts.push([x, y0 + Math.sin(x / s * Math.PI * 2) * 5]); line(k, pts, grey(76), 3); } }),
  rings: (Wd, Hd) => tile(Wd, Hd, 44, 34, (k, s) => { for (const R of [8, 15]) ellipse(k, s / 2 - R, s / 2 - R, s / 2 + R, s / 2 + R, null, grey(74), 2); }),
  triangles: (Wd, Hd) => tile(Wd, Hd, 40, 36, (k, s) => { poly(k, [[s / 4, s / 2 - 8], [s / 4 + 9, s / 2 + 7], [s / 4 - 9, s / 2 + 7]], grey(64)); poly(k, [[s * 3 / 4, s / 2 + 8], [s * 3 / 4 + 9, s / 2 - 7], [s * 3 / 4 - 9, s / 2 - 7]], null, grey(64)); }),
};
const PATTERN_LIST = Object.keys(PATTERNS);
const pattern = (name, Wd, Hd) => (PATTERNS[name] || PATTERNS.carbon)(Wd, Hd);

// ---------- gen.py: the pictures of the theme ----------
function figureFor(cfg, coll) { let f = cfg.figures[coll] || DEFAULT_FIG[coll]; if (!SHAPES[f]) f = SHAPE_LIST[rng(coll + "fig").randrange(SHAPE_LIST.length)]; return f; }
function patternFor(cfg, game) { let p = cfg.patterns[game]; if (!PATTERNS[p]) p = PATTERN_LIST[rng(game + "surface").randrange(PATTERN_LIST.length)]; return p; }

function sysBase() {
  const cv = mk(W, H), c = ctx(cv); rect(c, 0, 0, W - 1, H - 1, VOID);
  for (const [x, y, dx, dy] of [[24, 24, 1, 1], [W - 24, 24, -1, 1], [24, H - 24, 1, -1], [W - 24, H - 24, -1, -1]]) line(c, [[x, y + 10 * dy], [x, y], [x + 10 * dx, y]], [255, 255, 255, 64]);
  text(c, 44, 46, "ESCAPE/UI", font("px", 16), DIM, "lm");
  return cv;
}
// the figure as the card shows it: lines dimmed to 62 % (the still is the video's first frame, t = 0)
function figFrame(c, fig, t, accent) { renderShape(c, fig, t, accent, HERO[2], HERO[3], FIG_LW, null, 0.62); }

function sysOver(coll, games, level, accent, idx, total, fig = "globe") {
  const cv = mk(W, H); let c = ctx(cv);
  const generic = !coll, r = rng((coll || "new") + "stk"), pick = a => r.choice(a), acc = accent;
  const x0 = 44, y0 = 120;
  if (!generic) { text(c, x0, y0, pad2(idx), font("px", 12), INK, "lm"); text(c, x0 + 26, y0, "/ " + pad2(total), font("px", 12), DIM, "lm"); }
  if (level >= 2) stripes(c, x0 + 78, y0 - 5, 30, 10, INK);
  const n = coll.toUpperCase(), size = n.length <= 5 ? 76 : n.length <= 8 ? 54 : 38;
  if (!generic) text(c, x0 - 4, y0 + 30, n, font("dot", size, 900), INK, "lt");
  const yk = y0 + 30 + Math.floor(size * 0.95) + 18;
  const w0 = pill(c, x0, yk, "collection", true);
  if (!generic) pill(c, x0 + w0 + 8, yk, games.length + " items");
  const blurb = BLURB[n] || "Your own collection. Add games from a game's options.";
  const fb = font("grot", 15, 300); let yb = yk + 40, ln = "";
  for (const word of blurb.split(/\s+/)) {
    if (textLen(fb, ln + " " + word) > 330 && ln) { text(c, x0, yb, ln, fb, [189, 189, 185]); yb += 22; ln = word; } else ln = (ln + " " + word).trim();
  }
  text(c, x0, yb, ln, fb, [189, 189, 185]);
  const ys = yb + 46;
  text(c, x0, ys, "FOLDER", font("px", 12), DIM, "lm"); text(c, x0 + 96, ys, "/collections/" + (coll || "new"), font("grot", 16, 400), INK, "lm");
  const hx = HERO[0] + HERO[2] / 2, hy = HERO[1] + HERO[3] / 2;
  const lab = generic ? "" : coll.toLowerCase(), ls = lab ? (lab.length <= 5 ? 128 : Math.max(44, Math.floor(128 * 5 / lab.length))) : 128, fl = font("dot", ls, 900);
  if (lab) {
    const sh = mk(W, H), s = ctx(sh); text(s, hx, hy, lab, fl, VOID, "mm");
    for (const b of [12, 4]) { c.filter = `blur(${b}px)`; c.drawImage(sh, 0, 0); } c.filter = "none";
    text(c, hx, hy, lab, fl, INK, "mm");
    const lw = textLen(fl, lab); text(c, hx + lw / 2 + 2, hy, ".", fl, acc, "lm");
  }
  if (level >= 1) {
    text(c, HERO[0] + HERO[2] - 4, HERO[1] + 8, "ESC." + pad2(idx), font("px", 12), DIM, "rt");
    text(c, HERO[0] + HERO[2] - 4, HERO[1] + 28, (SHAPE_NAMES[fig] || "figure").toUpperCase(), font("px", 12), DIM, "rt");
  }
  const right = r.random() < 0.5, pct = (a, b, span) => a / 100 * span + r.random() * (b - a) / 100 * span;
  if (level >= 2) {
    const px = HERO[0] + (right ? 20 : HERO[2] - 220), py = HERO[1] + pct(30, 44, HERO[3]);
    let w = pill(c, px, py, pick(PILLS));
    if (r.random() < 0.6) w += 6 + pill(c, px + w + 6, py, pick(PILLS), true);
    text(c, px + w + 10, py + 9, pick(CHEVS), font("px", 12), acc, "lm");
  }
  if (level >= 3) {
    const cnt = 3 + Math.floor(r.random() * 3);
    for (let i = 0; i < cnt; i++) {
      const sx = HERO[0] + (r.random() < .5 ? pct(8, 30, HERO[2]) : pct(70, 92, HERO[2])), sy = HERO[1] + pct(10, 88, HERO[3]);
      if (i < 3 || level >= 5) sparkle(c, sx, sy, 6 + r.random() * 5);
    }
    const kx = HERO[0] + (right ? HERO[2] - 4 : 4), ky = HERO[1] + pct(14, 30, HERO[3]), more = pick(MORE_KATA);
    vtext(c, kx, ky, KATA[n] || more, font("jp", 13), [255, 255, 255, 90]);
  }
  if (level >= 4) {
    const by = HERO[1] + HERO[3] - 30;
    warnTri(c, HERO[0] + 6, by - 4); const xa = r.randrange(999), ya = r.randrange(999);
    text(c, HERO[0] + 36, by + 6, `X ${String(xa).padStart(3, "0")} Y ${String(ya).padStart(3, "0")}`, font("px", 12), DIM, "lm");
    bars(c, HERO[0] + HERO[2] - 150, by, 64, 14, INK, r.randrange(1 << 30)); text(c, HERO[0] + HERO[2] - 78, by + 7, "® " + coll.toLowerCase(), font("px", 12), DIM, "lm");
    for (const cx of [HERO[0] + HERO[2] * 0.06, HERO[0] + HERO[2] * 0.94]) { const cy = HERO[1] + pct(40, 60, HERO[3]); line(c, [[cx - 6, cy], [cx + 6, cy]], INK); line(c, [[cx, cy - 6], [cx, cy + 6]], INK); }
    const extra = r.randrange(4), ex = Math.floor(HERO[0] + pct(28, 56, HERO[2])), ey = Math.floor(HERO[1] + pct(2, 8, HERO[3]));
    const all = [badge(pad2(r.randrange(99)))]; all.push(arrowStk(pick(["enter", "go", "next", "open"]), pick(["→", "»", "↗"]))); all.push(checkerStrip()); all.push(barStk(String(r.randrange(1e8)).padStart(8, "0")));
    c.drawImage(rotated(all[extra], r.random() * 10 - 5), ex, ey);
  }
  if (level >= 5) {
    const kind = r.randrange(3), stp = rotated(stamp(kind, pick(STAMPS), acc), r.random() * 12 - 6);
    const sx = HERO[0] + (right ? HERO[2] - stp.width - 22 : 22), sy = Math.floor(HERO[1] + pct(66, 76, HERO[3]));
    c.drawImage(stp, Math.floor(sx), sy);
    const kx = HERO[0] + (right ? 8 : HERO[2] - 40), ky = HERO[1] + pct(10, 24, HERO[3]), more = pick(MORE_KANJI);
    vtext(c, kx + 16, ky, KANJI[n] || more, font("jp", 30), [255, 255, 255, 60], 2);
    if (r.random() < 0.6) { const hb = hazardBand(HERO[2], 12, acc); c.drawImage(hb, HERO[0], HERO[1] + (r.random() < .5 ? HERO[3] - 40 : 30)); }
    let e5 = r.random() < .5 ? disc(["DIGITAL", coll.toUpperCase()], acc) : jpLabel(pick(["注意", "危険", "再生", "停止", "高速"]), pick(["handle", "keep dry", "live", "do not bend"]));
    e5 = rotated(e5, r.random() * 12 - 6);
    c.drawImage(e5, Math.floor(HERO[0] + (right ? 30 : HERO[2] - e5.width - 30)), Math.floor(HERO[1] + pct(64, 74, HERO[3])) - 60);
  }
  return cv;
}
function sysKey(coll, fig, accent) {
  const f = font("px", 24); let name = coll.toUpperCase();
  while (textLen(f, name) > 180 && name.length > 4) name = name.slice(0, -2) + "…";
  const cv = mk(260, 72), c = ctx(cv), x0 = Math.floor((260 - (64 + 10 + textLen(f, name))) / 2);
  const em = mk(144, 144); renderShape(ctx(em), fig, 0.6, accent, 144, 144, 1.6, 52);
  c.drawImage(em, x0, 4, 64, 64); text(c, x0 + 74, 36, name, f, INK, "lm");
  return cv;
}
function listHead(coll, n) {
  const cv = mk(460, 64), c = ctx(cv), f = font("dot", 44, 900);
  text(c, 0, 6, coll.toUpperCase(), f, INK, "lt");
  text(c, textLen(f, coll.toUpperCase()) + 16, 36, `${n} ITEMS · FAV, A–Z`, font("px", 12), DIM, "lm");
  return cv;
}
// the game's own picture as a Polaroid stuck on the sheet: white paper, the photo cropped to fit,
// a caption in the bottom margin and a strip of tape; paper has no black backing, only a shadow
function polaroid(photo, caption) {
  const pw = 116, ar = photo.height / photo.width, ph = Math.max(88, Math.min(140, Math.round(pw * ar))), fw = pw + 16, fh = ph + 8 + 30;
  const cv = mk(fw, fh + 8), c = ctx(cv), top = 8;
  rect(c, 0, top, fw - 1, top + fh - 1, [242, 242, 238]);
  const s = Math.max(pw / photo.width, ph / photo.height), sw = pw / s, sh = ph / s;   // cover-crop, centred
  c.imageSmoothingQuality = "high"; c.drawImage(photo, (photo.width - sw) / 2, (photo.height - sh) / 2, sw, sh, 8, top + 8, pw, ph);
  rect(c, 8, top + 8, 8 + pw - 1, top + 8 + ph - 1, null, [0, 0, 0, 40]);
  let cap = caption; const f = font("grot", 11, 500); while (textLen(f, cap) > pw && cap.length > 3) cap = cap.slice(0, -2) + "…";
  text(c, fw / 2, top + 8 + ph + 15, cap, f, [44, 44, 42], "mm");
  c.save(); c.translate(fw / 2, top + 1); c.rotate(-0.12); c.fillStyle = "rgba(235,235,225,.55)"; c.fillRect(-24, -7, 48, 14); c.restore();   // tape
  return cv;
}
// no picture: the name as a die-cut logo sticker, with an accent bar under it
function logoSticker(name, accent) {
  let size = 30; const n = name.toUpperCase(); let f = font("dot", size, 900);
  while (textLen(f, n) > 210 && size > 14) { size -= 2; f = font("dot", size, 900); }
  const w = Math.ceil(textLen(f, n)) + 20, h = size + 30, cv = mk(w, h), c = ctx(cv);
  text(c, 10, 8, n, f, INK, "lt"); rect(c, 10, h - 14, Math.min(w - 11, 10 + 46), h - 11, accent);
  text(c, w - 10, h - 12, "NO COVER", font("px", 7), DIM, "rm");
  return cv;
}
function paper(content, rot) {   // a sticker without the black film: just the shadow
  const base = rotated(content, rot), sh = mk(base.width + 24, base.height + 24), s = ctx(sh);
  const blk = mk(base.width, base.height), k = ctx(blk); k.drawImage(base, 0, 0); k.globalCompositeOperation = "source-in"; k.fillStyle = "rgba(0,0,0,.6)"; k.fillRect(0, 0, blk.width, blk.height);
  s.filter = "blur(5px)"; s.drawImage(blk, 14, 16); s.filter = "none"; s.drawImage(base, 12, 12);
  return sh;
}
// what goes on the sheet as the game's own sticker: covers[game] = auto | original | custom | logo | none
function frontSticker(game, accent, cfg, photos) {
  const mode = (cfg.covers || {})[game] || "auto", own = photos.custom[game], orig = photos.original[game];
  if (mode === "none") return null;
  if (mode === "custom" && own) return ["paper", polaroid(own, game)];
  if ((mode === "auto" || mode === "original") && orig) return ["paper", polaroid(orig, game)];
  if (mode === "auto" && own) return ["paper", polaroid(own, game)];
  return ["vinyl", logoSticker(game, accent)];
}
function cover(game, level, accent, cfg, idx = 0, photos = null) {
  const CW = 440, CH = 264, surf = patternFor(cfg, game);
  const cv = mk(CW, CH), c = ctx(cv); c.imageSmoothingQuality = "high"; c.drawImage(pattern(surf, CW * 2, CH * 2), 0, 0, CW, CH);
  const r = rng(game + "sheet"), pick = a => r.choice(a), acc = accent, pool = [], add = (lvl, img, round = false) => pool.push([lvl, img, round]);
  add(1, miniFigure(pick(SHAPE_LIST), r.random() * 6, acc, 110), true);
  { const num = mk(150, 70); text(ctx(num), 75, 35, pad2(idx + 1), font("dot", 64, 900), INK, "mm"); add(1, num); }
  { const pl = mk(200, 22), dp = ctx(pl), w = pill(dp, 1, 2, pick(PILLS)); pill(dp, w + 7, 2, pick(PILLS), true); add(2, crop(pl, bbox(pl))); }
  { const word = pick(["play", "go", "next", "run", "load"]), arr = pick(["→", "↗", "»", "↘"]); add(2, arrowStk(word, arr)); }
  { const ch = mk(70, 22); text(ctx(ch), 35, 11, pick(CHEVS), font("px", 14), acc, "mm"); add(2, ch); }
  { const kt = mk(34, 130); vtext(ctx(kt), 17, 4, pick(MORE_KATA), font("jp", 16), INK, 2); add(3, crop(kt, bbox(kt))); }
  { const sp = mk(60, 40), ds = ctx(sp); sparkle(ds, 18, 20, 14); sparkle(ds, 44, 14, 7); add(3, sp); }
  add(3, badge(pad2(r.randrange(99))), true);
  add(4, barStk(String(r.randrange(1e8)).padStart(8, "0")));
  { const wt = mk(130, 24), dw = ctx(wt); warnTri(dw, 0, 2); text(dw, 30, 12, pick(["caution", "hot", "loud", "fragile", "beta"]).toUpperCase(), font("px", 9), INK, "lm"); add(4, crop(wt, bbox(wt))); }
  add(4, checkerStrip()); add(4, stripesLayer(46, 18, INK));
  { const kind = r.randrange(3), words = pick(STAMPS), st = stamp(kind, words, acc); add(5, st, r.random() < 0); }
  add(5, disc(["DIGITAL", "ESCAPE"], acc), true);
  { const k = pick(MORE_KANJI), wd = pick(["handle", "keep dry", "do not bend", "live"]); add(5, jpLabel(k, wd)); }
  const pool2 = pool.filter(p => p[0] <= Math.max(1, level)); r.shuffle(pool2);
  let want = [0, 2, 4, 6, 9, 14][level];
  // the game's own picture (or its logo) goes on first, so it always finds room; level 0 = pattern only
  const front = level >= 1 && photos ? frontSticker(game, acc, cfg, photos) : null;
  if (front) { pool2.unshift([0, front[1], false, front[0]]); want += 1; }
  const placed = []; let n = 0;
  for (const [, img, rnd, kind] of pool2) {
    if (n >= want) break;
    const st = kind === "paper" ? paper(img, r.random() * 16 - 8) : vinyl(img, rnd, 6, r.random() * 14 - 7);
    if (st.width >= CW - 8 || st.height >= CH - 8) continue;
    for (let k = 0; k < 40; k++) {
      const x = 4 + r.random() * (CW - st.width - 8), y = 4 + r.random() * (CH - st.height - 8);
      if (placed.some(([px, py, pw, ph]) => x < px + pw - 4 && x + st.width - 4 > px && y < py + ph - 4 && y + st.height - 4 > py)) continue;
      placed.push([x, y, st.width, st.height]); c.drawImage(st, Math.floor(x), Math.floor(y)); n++; break;
    }
  }
  const tag = "PATTERN · " + surf.toUpperCase(), fw = font("px", 8), tw = textLen(fw, tag);
  rect(c, CW - tw - 16, CH - 20, CW - 6, CH - 6, VOID); text(c, CW - 11, CH - 13, tag, fw, DIM, "rm");
  return cv;
}
function bootScreen(logo, accent) {
  const cv = mk(W, H), c = ctx(cv); rect(c, 0, 0, W - 1, H - 1, VOID);
  renderShape(c, logo, 0.6, accent, 400, 400, 0.7, null, 1, W / 2 - 200, 130);
  const f = font("dot", 36, 900); textSpaced(c, W / 2 - textW(f, "ESCAPE/UI", 10) / 2, 560, "ESCAPE/UI", f, INK, "lm", 10);
  text(c, W / 2, 604, "エスケープ", font("jp", 14), DIM, "mm");
  return cv;
}
// the glitch the videos open with (gen.glitch_frame), applied to the live canvas
function glitchFrame(src, k, rnd, N = 15) {
  const s = 1 - k / N, w = src.width, h = src.height, out = mk(w, h), o = ctx(out);
  if (k === 0 || k === 3 || k === 7 || (k < 10 && rnd.random() < 0.15)) return out;
  let cur = src;
  if (rnd.random() < 0.8 * s) { const f = 2 + Math.floor(rnd.random() * 10 * s), sm = mk(Math.max(1, w / f | 0), Math.max(1, h / f | 0)), sc = ctx(sm); sc.imageSmoothingEnabled = false; sc.drawImage(src, 0, 0, sm.width, sm.height); const bl = mk(w, h), bc = ctx(bl); bc.imageSmoothingEnabled = false; bc.drawImage(sm, 0, 0, w, h); cur = bl; }
  const bands = mk(w, h), b = ctx(bands); let y = 0;
  while (y < h) { const bh = Math.floor(4 + rnd.random() * 46), dx = rnd.random() < 0.7 ? Math.floor((rnd.random() * 2 - 1) * 90 * s) : 0; b.drawImage(cur, 0, y, w, Math.min(bh, h - y), dx, y, w, Math.min(bh, h - y)); y += bh; }
  const sh = Math.floor(3 + 10 * s), dim = 0.45 + 0.55 * (1 - s) + rnd.random() * 0.2;
  o.globalCompositeOperation = "lighter";
  for (const [dx, col] of [[sh, "#f00"], [0, "#0f0"], [-sh, "#00f"]]) { const ch = mk(w, h), cc = ctx(ch); cc.drawImage(bands, dx, 0); cc.globalCompositeOperation = "multiply"; cc.fillStyle = col; cc.fillRect(0, 0, w, h); cc.globalCompositeOperation = "destination-in"; cc.drawImage(bands, dx, 0); o.drawImage(ch, 0, 0); }
  o.globalCompositeOperation = "source-over"; o.fillStyle = `rgba(0,0,0,${Math.max(0, 1 - Math.min(1, dim))})`; o.fillRect(0, 0, w, h);
  return out;
}
