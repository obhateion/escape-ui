// ---------- the Brick, screen by screen (layout numbers come from theme.xml, × 1024 / × 768) ----------
const $ = id => document.getElementById(id);
const store = (k, v) => { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } };
const load = (k, d) => { try { const v = JSON.parse(localStorage.getItem(k)); return v == null ? d : v; } catch (e) { return d; } };
const save = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* private window */ } };

// state = what es_settings.cfg and config.json hold on the Brick
const S = Object.assign({ accent: DEVICE.accent || "white", detail: "3", covers: "3", motion: "video", ca: "off", lowbatt: "on", charge: "on" }, load("escui31-subsets", {}));
const CFG = Object.assign({ boot_logo: "globe", figures: {}, patterns: {}, covers: {} }, DEVICE.cfg, load("escui31-cfg", {}));
CFG.covers = CFG.covers || {};
CFG.figures = Object.assign({}, DEVICE.cfg.figures, CFG.figures); CFG.patterns = Object.assign({}, DEVICE.cfg.patterns, CFG.patterns);
const persist = () => { save("escui31-subsets", S); save("escui31-cfg", { boot_logo: CFG.boot_logo, figures: CFG.figures, patterns: CFG.patterns, covers: CFG.covers }); };
// the games' own pictures: what the Brick has scraped (ORIGINAL) and the ones you add (kept in this browser)
const PHOTOS = { original: {}, custom: {} };
const CUSTOM = load("escui31-custom", {});
const loadImg = src => new Promise(res => { const i = new Image(); i.onload = () => res(i); i.onerror = () => res(null); i.src = src; });
// EscapeUI has no box art: its picture is the theme's own boot figure
function escapeUiPhoto() { const cv = mk(220, 220), c = ctx(cv); rect(c, 0, 0, 219, 219, VOID); renderShape(c, CFG.boot_logo, 0.6, acc(), 220, 220, 1.4, 80); return cv; }
const photosReady = Promise.all([
  ...Object.entries(ORIGINAL).map(([g, u]) => loadImg(u).then(i => { if (i) PHOTOS.original[g] = i; })),
  ...Object.entries(CUSTOM).map(([g, u]) => loadImg(u).then(i => { if (i) PHOTOS.custom[g] = i; }))]);
const acc = () => ACCENT_RGB[S.accent];
const batt = { lvl: 87, chg: false };

// collections as the Brick has them: favourites first, then a–z; ES adds [system] in collections
const INFO = DEVICE.info;
const COLLS = Object.keys(DEVICE.colls).sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()));
const gamesOf = c => [...new Set(DEVICE.colls[c])].sort((a, b) => ((INFO[b] || {}).fav ? 1 : 0) - ((INFO[a] || {}).fav ? 1 : 0) || a.toLowerCase().localeCompare(b.toLowerCase()));
const ALL_GAMES = [...new Set(COLLS.flatMap(c => DEVICE.colls[c]))].sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()));

// ---------- picture cache: the theme's generated images, drawn on demand like gen.py would ----------
const cache = new Map();
const pic = (key, make) => { if (!cache.has(key)) cache.set(key, make()); return cache.get(key); };
const overKey = (c, L) => `over|${c}|${L}|${S.accent}|${figureFor(CFG, c)}`;
const overOf = (c, L) => pic(overKey(c, L), () => sysOver(c, DEVICE.colls[c], L, acc(), COLLS.indexOf(c) + 1, COLLS.length, figureFor(CFG, c)));
const keyOf = c => pic(`key|${c}|${S.accent}|${figureFor(CFG, c)}`, () => sysKey(c, figureFor(CFG, c), acc()));
const headOf = c => pic(`head|${c}`, () => listHead(c, DEVICE.colls[c].length));
const coverOf = (g, L) => pic(`cov|${g}|${L}|${S.accent}|${patternFor(CFG, g)}|${CFG.covers[g] || "auto"}|${PHOTOS.custom[g] ? 1 : 0}`, () => cover(g, L, acc(), CFG, ALL_GAMES.indexOf(g), PHOTOS));
const baseOf = () => pic("base", sysBase);

// ---------- screens ----------
let screen = "sys", ci = 0, gi = 0, gtop = 0;
const SCREENS = ["s-boot", "s-sys", "s-list", "s-menu", "s-app", "s-charge"];
function show(s) {
  screen = s;
  for (const id of SCREENS) $(id).hidden = !(id === "s-" + s || (s === "menu" && id === "s-" + under) || (s === "app" && false));
  document.querySelectorAll("[data-go]").forEach(b => b.setAttribute("aria-pressed", b.dataset.go === s || (s === "menu" && b.dataset.go === "menu")));
  render();
}
let under = "sys";   // the view under ES's menu

function render() {
  $("stage").classList.toggle("ca", S.ca === "always");
  if (screen === "boot") { const b = $("boot"); ctx(b).drawImage(pic(`boot|${CFG.boot_logo}|${S.accent}`, () => bootScreen(CFG.boot_logo, acc())), 0, 0); }
  if (screen === "sys" || (screen === "menu" && under === "sys")) renderSys();
  if (screen === "list" || (screen === "menu" && under === "list")) renderList();
  if (screen === "menu") renderMenu();
  if (screen === "app") renderApp();
  renderHelp(); renderFx();
}

// system view: base, the figure (video / light / still), the over image of the detail level, ES's carousel
let figStart = performance.now(), glitchRnd = null;
function renderSys() {
  const c = COLLS[ci];
  ctx($("base")).drawImage(baseOf(), 0, 0);
  const o = $("over"), oc = ctx(o); oc.clearRect(0, 0, W, H); oc.drawImage(overOf(c, lvl(S.detail)), 0, 0);
  const still = $("fig"), sc = ctx(still); sc.clearRect(0, 0, HERO[2], HERO[3]);
  if (lvl(S.detail) !== 0) figFrame(sc, figureFor(CFG, c), 0, acc());
  $("fig").classList.toggle("light", S.motion === "light");
  $("fig").hidden = lvl(S.detail) === 0 || S.motion === "video";
  $("loop").hidden = lvl(S.detail) === 0 || S.motion !== "video";
  // the carousel: three keys, the picked one in the middle, 1.08×; the others at ES's half opacity
  const strip = $("strip"); strip.innerHTML = "";
  [-1, 0, 1].forEach(d => {
    const k = COLLS[(ci + d + COLLS.length) % COLLS.length], img = keyOf(k), el = document.createElement("canvas");
    el.width = 260; el.height = 72; ctx(el).drawImage(img, 0, 0); el.className = "key" + (d === 0 ? " on" : "");
    el.style.left = (44 + 312 * (d + 1) + 26) + "px"; strip.appendChild(el);
  });
}
function startFigure() { figStart = performance.now(); glitchRnd = new PyRandom(figureFor(CFG, COLLS[ci]) + "glitch"); }
const loopCanvas = mk(HERO[2], HERO[3]);
function tick() {
  requestAnimationFrame(tick);
  if (!(screen === "sys" || (screen === "menu" && under === "sys")) || S.motion !== "video" || lvl(S.detail) === 0) return;
  const fig = figureFor(CFG, COLLS[ci]), [span, sec] = LOOP[fig] || [TAU, 12];
  const el = (performance.now() - figStart) / 1000, frame = Math.floor(el * 24);   // the videos are 24 fps
  if (frame === tick.last && fig === tick.fig) return; tick.last = frame; tick.fig = fig;
  const n = Math.max(2, Math.round(sec * 24)), t = span * (frame % n) / n, lc = ctx(loopCanvas);
  lc.fillStyle = "#000"; lc.fillRect(0, 0, HERO[2], HERO[3]); figFrame(lc, fig, t, acc());
  const out = $("loop"), c = ctx(out);
  if (frame < 15 && glitchRnd) { c.clearRect(0, 0, HERO[2], HERO[3]); c.drawImage(glitchFrame(loopCanvas, frame, glitchRnd), 0, 0); }
  else { c.clearRect(0, 0, HERO[2], HERO[3]); c.drawImage(loopCanvas, 0, 0); }
}

// game lists (the detailed view)
function renderList() {
  const c = COLLS[ci], games = gamesOf(c);
  ctx($("base2")).drawImage(baseOf(), 0, 0);
  const h = $("head"), hc = ctx(h); hc.clearRect(0, 0, 460, 64); hc.drawImage(headOf(c), 0, 0);
  gi = Math.max(0, Math.min(gi, games.length - 1));
  const vis = 14; if (gi < gtop) gtop = gi; if (gi >= gtop + vis) gtop = gi - vis + 1;
  $("rows").innerHTML = games.slice(gtop, gtop + vis).map((g, i) => {
    const inf = INFO[g] || {}, label = g + (inf.s ? ` [${inf.s}]` : "");
    return `<div class="tl${gtop + i === gi ? " on" : ""}">${esc(label)}</div>`;
  }).join("");
  const g = games[gi], inf = INFO[g] || {};
  const cv = ctx($("cover")); cv.drawImage(pic("blank", () => { const b = mk(440, 264), bc = ctx(b); bc.drawImage(pattern("carbon", 880, 528), 0, 0, 440, 264); rect(bc, 12, 230, 190, 252, VOID); text(bc, 20, 241, "NO SHEET YET · RUN ESCAPE-UI", font("px", 8), DIM, "lm"); return b; }), 0, 0);
  cv.drawImage(coverOf(g, lvl(S.covers)), 0, 0);
  $("md-name").textContent = g;
  $("md-plays").textContent = inf.p > 0 ? inf.p : "—";
  $("md-time").textContent = inf.h > 0 ? expandSeconds(inf.h) : "—";
  $("md-last").textContent = inf.l ? inf.l.slice(6, 8) + "." + inf.l.slice(4, 6) : "";
  $("md-desc").textContent = inf.d || "";
}
const esc = s => s.replace(/[&<>]/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[ch]);
function expandSeconds(s) { const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60); return h ? `${h} H ${m} MN` : m ? `${m} MN` : `${s} S`; }

// ---------- ES's menu (main menu > user interface settings > theme configuration), as the Brick draws it ----------
const lvl = v => (v === "default" || v === undefined || v === "") ? 3 : +v;   // "default" = the theme's 3, as on the Brick
const OPTS = {
  detail: { lb: "ESCAPE/UI · DETAIL LEVEL", ch: ["default", "0", "1", "2", "3", "4", "5"],
            names: { default: "DEFAULT (3)", 0: "0 · TEXT ONLY", 1: "1 · FIGURE + HUD", 2: "2 · PILLS, CHEVRONS", 3: "3 · SPARKLES, KATAKANA", 4: "4 · WARNINGS, BARCODES", 5: "5 · EVERYTHING" } },
  covers: { lb: "ESCAPE/UI · COVER STICKERS", ch: ["default", "0", "1", "2", "3", "4", "5"],
            names: { default: "DEFAULT (3)", 0: "0 · PATTERN ONLY", 5: "5 · AS MANY AS FIT" } },
  motion: { lb: "ESCAPE/UI · FIGURE MOTION", ch: ["video", "light", "still"] },
  ca: { lb: "ESCAPE/UI · CHROMATIC ABERRATION", ch: ["off", "always"] },
  lowbatt: { lb: "ESCAPE/UI · LOW BATTERY PULSE", ch: ["on", "off"] },
  charge: { lb: "ESCAPE/UI · CHARGING SCREEN", ch: ["on", "off"] },
  accent: { lb: "ESCAPE/UI · ACCENT COLOUR", ch: PALETTE.map(p => p[0]) },
};
const MENUS = {
  main: { title: "MAIN MENU", foot: "KNULLI GLADIATOR-II 2025/08/12 23:34 [0]", rows: [
    { lb: "GAME SETTINGS", arrow: 1 }, { lb: "CONTROLLER & BLUETOOTH SETTINGS", arrow: 1 }, { lb: "USER INTERFACE SETTINGS", open: "ui" },
    { lb: "GAME COLLECTION SETTINGS", arrow: 1 }, { lb: "SOUND SETTINGS", arrow: 1 }, { lb: "NETWORK SETTINGS", arrow: 1 }, { lb: "SCRAPER", arrow: 1 },
    { lb: "UPDATES & DOWNLOADS", arrow: 1 }, { lb: "DEVICE SETTINGS", arrow: 1 }, { lb: "SYSTEM SETTINGS", arrow: 1 }, { lb: "QUIT", arrow: 1 }] },
  ui: { title: "USER INTERFACE SETTINGS", back: true, rows: [
    { grp: "APPEARANCE" }, { lb: "THEME SET", val: () => "ES-THEME-ESCAPE-UI", lr: 1 }, { lb: "THEME CONFIGURATION", open: "theme" },
    { grp: "DISPLAY OPTIONS" }, { lb: "SCREENSAVER SETTINGS", arrow: 1 }, { lb: "LIST TRANSITION", val: () => "AUTO", lr: 1 },
    { lb: "GAME LAUNCH TRANSITION", val: () => "AUTO", lr: 1 }, { lb: "SHOW CLOCK", sw: true }, { lb: "ON-SCREEN HELP", sw: true },
    { lb: "SHOW BATTERY STATUS", val: () => "ICON AND TEXT", lr: 1 }] },
  theme: { title: "THEME CONFIGURATION", back: true, rows: [
    { grp: "GAMELIST STYLE" }, { lb: "GAMELIST VIEW STYLE", val: () => "AUTOMATIC", lr: 1 }, { grp: "THEME OPTIONS" },
    ...Object.keys(OPTS).map(k => ({ lb: OPTS[k].lb, opt: k })), { grp: "TOOLS" }, { lb: "RESET CUSTOMIZATIONS", act: () => { for (const k of Object.keys(OPTS)) S[k] = OPTS[k].ch[0]; S.accent = DEVICE.accent; persist(); } }] },
};
let mstack = [], mcur = 0;
function openMenu(page) { if (screen !== "menu") under = screen; mstack.push(page); mcur = MENUS[page].rows.findIndex(r => !r.grp); show("menu"); }
function renderMenu() {
  const m = MENUS[mstack[mstack.length - 1]], el = $("menu"), rows = [];
  m.rows.forEach((r, i) => {
    if (r.grp) { rows.push(`<div class="mg">${r.grp}</div>`); return; }
    let right = "";
    if (r.opt) { const v = S[r.opt]; right = `<span class="mv"><i>◂</i>${((OPTS[r.opt].names || {})[v] || String(v).toUpperCase())}<i>▸</i></span>`; }
    else if (r.val) right = `<span class="mv">${r.lr ? "<i>◂</i>" : ""}${r.val()}${r.lr ? "<i>▸</i>" : ""}</span>`;
    else if (r.sw) right = `<span class="msw"></span>`;
    else if (r.open || r.arrow) right = `<span class="ma">›</span>`;
    rows.push(`<div class="mi${i === mcur ? " on" : ""}"><span>${r.lb}</span>${right}</div>`);
  });
  el.innerHTML = `<div class="mt">${m.title}</div><div class="mrows">${rows.join("")}</div>` +
    (m.foot ? `<div class="mf">${m.foot}</div>` : "") + (m.back ? `<div class="mb"><span class="${mcur === m.rows.length ? "on" : ""}">BACK</span></div>` : "");
}
function menuKey(k) {
  const m = MENUS[mstack[mstack.length - 1]], rows = m.rows, selectable = i => i === rows.length ? !!m.back : !rows[i].grp;
  const step = d => { let i = mcur; do { i = (i + d + rows.length + 1) % (rows.length + 1); } while (!selectable(i)); mcur = i; };
  if (k === "up") step(-1); else if (k === "down") step(1);
  else if (k === "left" || k === "right") { const r = rows[mcur]; if (r && r.opt) { const o = OPTS[r.opt], i = o.ch.indexOf(S[r.opt]); S[r.opt] = o.ch[(i + (k === "left" ? -1 : 1) + o.ch.length) % o.ch.length]; persist(); applySettings(); } }
  else if (k === "a") { const r = rows[mcur]; if (mcur === rows.length) return menuKey("b"); if (r.open) { mstack.push(r.open); mcur = MENUS[r.open].rows.findIndex(x => !x.grp); } else if (r.act) { r.act(); applySettings(); } }
  else if (k === "b") { mstack.pop(); if (!mstack.length) { show(under); return; } mcur = 0; }
  else if (k === "start") { mstack = []; show(under); return; }
  render();
}
function applySettings() { syncHeader(); startFigure(); }

// ---------- the escape-UI app (a port, full screen, pygame): tool/app.py ----------
const APP = { page: "main", cur: 0, top: 0, armed: false };
const MOTION_NAMES = { video: "animated", light: "light", still: "still" };
function appRows() {
  if (APP.page === "main") return [
    ["Accent colour", ["chip", S.accent], d => cyc("accent", d), true],
    ["Detail level", ["txt", lvl(S.detail) + " / 5"], d => cycNum("detail", d), false],
    ["Cover stickers", ["txt", lvl(S.covers) + " / 5"], d => cycNum("covers", d), false],
    ["Figure motion", ["txt", MOTION_NAMES[S.motion]], d => cyc("motion", d), true],
    ["Boot logo", ["fig", CFG.boot_logo], d => { CFG.boot_logo = SHAPE_LIST[(SHAPE_LIST.indexOf(CFG.boot_logo) + d + SHAPE_LIST.length) % SHAPE_LIST.length]; }, false],
    ["Chromatic aberration", ["txt", S.ca], d => cyc("ca", d), false],
    ["Low battery pulse · ≤10%", ["txt", S.lowbatt], d => cyc("lowbatt", d), false],
    ["Charging screen", ["txt", S.charge], d => cyc("charge", d), true],
    ["Figures of collections", ["open", ""], () => { APP.page = "figs"; APP.cur = 0; APP.top = 0; }, false],
    ["Patterns of covers", ["open", ""], () => { APP.page = "pats"; APP.cur = 0; APP.top = 0; }, false],
    ["Covers of games", ["open", ""], () => { APP.page = "covs"; APP.cur = 0; APP.top = 0; }, false],
    [APP.armed ? "A again: ~0 min, keep charging" : "Draw all colours · all 10 ready", ["open", ""], () => { APP.armed = false; }, false],
    ["Save & exit", ["open", ""], () => leaveApp(), true],
    ["Reset figures & patterns", ["danger", ""], d => { if (!d) { CFG.figures = {}; CFG.patterns = {}; } }, false]];
  if (APP.page === "figs") return COLLS.map(c => [c, ["fig", figureFor(CFG, c)], d => { const L = SHAPE_LIST; CFG.figures[c] = L[(L.indexOf(figureFor(CFG, c)) + d + L.length) % L.length]; }, false])
    .concat([["Reset figures", ["danger", ""], d => { if (!d) CFG.figures = {}; }, false]]);
  if (APP.page === "covs") return ALL_GAMES.map(g => [g, ["cov", coverMode(g)], d => {
      const L = coverModes(g); CFG.covers[g] = L[(L.indexOf(coverMode(g)) + d + L.length) % L.length]; }, false])
    .concat([["Reset covers", ["danger", ""], d => { if (!d) CFG.covers = {}; }, false]]);
  return ALL_GAMES.map(g => [g, ["pat", CFG.patterns[g] || "auto"], d => { const L = ["auto", ...PATTERN_LIST], cur = CFG.patterns[g] || "auto", nx = L[(L.indexOf(cur) + d + L.length) % L.length]; if (nx === "auto") delete CFG.patterns[g]; else CFG.patterns[g] = nx; }, false])
    .concat([["Reset patterns", ["danger", ""], d => { if (!d) CFG.patterns = {}; }, false]]);
}
// a game's cover choices: its own picture, yours, its name as a logo sticker, or nothing
const coverModes = g => [...(PHOTOS.original[g] ? ["original"] : []), ...(PHOTOS.custom[g] ? ["custom"] : []), "logo", "none"];
const coverMode = g => { const m = CFG.covers[g] || "auto"; return m === "auto" ? (PHOTOS.original[g] ? "original" : PHOTOS.custom[g] ? "custom" : "logo") : m; };
const COVER_NAMES = { original: "original", custom: "your own", logo: "logo", none: "none" };
function addOwnCover(g) {   // on the Brick: a picture dropped into SHARE/escape-ui/covers/<game>.png
  const inp = document.createElement("input"); inp.type = "file"; inp.accept = "image/*";
  inp.onchange = () => { const f = inp.files[0]; if (!f) return; const rd = new FileReader();
    rd.onload = async () => { const im = await loadImg(rd.result); if (!im) return; const s = Math.min(1, 260 / Math.max(im.width, im.height)), cv = mk(im.width * s, im.height * s);
      ctx(cv).drawImage(im, 0, 0, cv.width, cv.height); const url = cv.toDataURL("image/jpeg", 0.85); CUSTOM[g] = url; save("escui31-custom", CUSTOM);
      PHOTOS.custom[g] = await loadImg(url); CFG.covers[g] = "custom"; persist(); render(); };
    rd.readAsDataURL(f); };
  inp.click();
}
const cyc = (k, d) => { const ch = OPTS[k].ch.slice().sort((a, b) => k === "accent" ? PALETTE.findIndex(p => p[0] === a) - PALETTE.findIndex(p => p[0] === b) : 0); S[k] = ch[(ch.indexOf(S[k]) + d + ch.length) % ch.length]; };
const cycNum = (k, d) => { S[k] = String((lvl(S[k]) + d + 6) % 6); };
const thumbCache = new Map();
function thumb(kind, val) {
  const key = kind + val + S.accent; if (thumbCache.has(key)) return thumbCache.get(key);
  const t = mk(48, 30), c = ctx(t); rect(c, 0, 0, 47, 29, VOID);
  if (kind === "fig") { const f = mk(96, 60); renderShape(ctx(f), val, 0.6, acc(), 96, 60, 1.0, 22); c.drawImage(f, 0, 0, 48, 30); }
  else c.drawImage(pattern(val, 96, 60), 0, 0, 48, 30);
  rect(c, 0, 0, 47, 29, null, [255, 255, 255, 40]); thumbCache.set(key, t); return t;
}
function renderApp() {
  const cv = $("app"), c = ctx(cv), RED = [255, 42, 31];
  // the card behind, darkened (make_bg): base + figure + over3 of the first collection
  c.drawImage(baseOf(), 0, 0); const fc = mk(HERO[2], HERO[3]); figFrame(ctx(fc), figureFor(CFG, COLLS[0]), 0, acc()); c.drawImage(fc, HERO[0], HERO[1]);
  c.drawImage(overOf(COLLS[0], 3), 0, 0); c.fillStyle = "rgba(0,0,0,.816)"; c.fillRect(0, 0, W, H);
  const rows = appRows(), vis = 15, rh = 36;
  APP.cur = Math.max(0, Math.min(APP.cur, rows.length - 1)); if (APP.cur < APP.top) APP.top = APP.cur; if (APP.cur >= APP.top + vis) APP.top = APP.cur - vis + 1;
  const shown = rows.slice(APP.top, APP.top + vis), pw = 560, ph = 86 + shown.length * rh + 40, px = (W - pw) >> 1, py = (H - ph) >> 1;
  rect(c, px, py, px + pw, py + ph, [11, 11, 11, 246], [255, 255, 255, 26]);
  const ic = mk(120, 120); renderShape(ctx(ic), CFG.boot_logo, 0.6, acc(), 120, 120, 1.2, 48); c.drawImage(ic, px + 22, py + 22, 34, 34);
  text(c, px + 66, py + 39, { main: "ESCAPE/UI", figs: "FIGURES", pats: "PATTERNS", covs: "COVERS" }[APP.page], font("dot", 30, 900), INK, "lm");
  text(c, px + pw - 22, py + 39, { main: "THEME SETTINGS", figs: "PER COLLECTION", pats: "PER GAME", covs: "PER GAME" }[APP.page], font("px", 12), DIM, "rm");
  let y = py + 76;
  shown.forEach(([lb, [kind, val], , sep], i) => {
    const n = APP.top + i, on = n === APP.cur;
    if (kind === "danger") {
      c.save(); c.beginPath(); c.rect(px + 1, y + 2, pw - 2, rh - 4); c.clip();
      for (let k = -rh; k < pw; k += 18) poly(c, [[px + 1 + k, y + rh - 2], [px + 1 + k + 9, y + rh - 2], [px + 1 + k + 9 + rh - 4, y + 2], [px + 1 + k + rh - 4, y + 2]], RED.concat([on ? 255 : 85]));
      c.restore();
      const fl = font("px", 12), t = lb.toUpperCase(), tw = textLen(fl, t);
      rect(c, W / 2 - tw / 2 - 12, y + 8, W / 2 + tw / 2 + 12, y + rh - 8, VOID, on ? RED : null);
      text(c, W / 2, y + rh / 2, t, fl, on ? [255, 255, 255] : RED, "mm");
      for (const tx of [px + 16, px + pw - 36]) warnTri(c, tx, y + 9, 20, 18, on ? [255, 255, 255] : RED, on ? RED : VOID);
    } else {
      if (on) rect(c, px + 1, y, px + pw - 1, y + rh - 1, [255, 255, 255, 18]);
      text(c, px + 24, y + rh / 2, pad2(n + 1), font("px", 12), on ? acc() : [255, 255, 255, 48], "lm");
      text(c, px + 56, y + rh / 2, lb.length < 34 ? lb : lb.slice(0, 32) + "…", font("grot", 16, 400), on ? [255, 255, 255] : [169, 169, 165], "lm");
      let rx = px + pw - 24;
      if (kind === "open") text(c, rx, y + rh / 2, ">>>", font("px", 12), on ? acc() : [60, 60, 60], "rm");
      else {
        const vt = kind === "fig" ? (SHAPE_NAMES[val] || val).toUpperCase() : kind === "cov" ? COVER_NAMES[val].toUpperCase() : val.toUpperCase(), fv = font("px", 12);
        if (on) { text(c, rx, y + rh / 2, ">", fv, acc(), "rm"); rx -= 18; }
        text(c, rx, y + rh / 2, vt, fv, on ? INK : DIM, "rm"); rx -= textLen(fv, vt) + 10;
        if (kind === "chip") { rect(c, rx - 14, y + rh / 2 - 7, rx, y + rh / 2 + 7, acc(), [255, 255, 255, 70]); rx -= 24; }
        else if (kind === "cov") {
          const ph = val === "original" ? PHOTOS.original[lb] : val === "custom" ? PHOTOS.custom[lb] : null, t = mk(48, 30), tc = ctx(t);
          rect(tc, 0, 0, 47, 29, VOID); if (ph) { const s = Math.max(48 / ph.width, 30 / ph.height); tc.drawImage(ph, (48 - ph.width * s) / 2, (30 - ph.height * s) / 2, ph.width * s, ph.height * s); }
          else if (val === "logo") text(tc, 24, 15, "ABC", font("dot", 14, 900), INK, "mm");
          rect(tc, 0, 0, 47, 29, null, [255, 255, 255, 40]); c.drawImage(t, Math.floor(rx - 48), Math.floor(y + rh / 2 - 15));
          if (on) rect(c, rx - 48, y + rh / 2 - 15, rx - 1, y + rh / 2 + 14, null, acc()); rx -= 58;
        }
        else if (kind === "fig" || kind === "pat") {
          const th = kind === "pat" ? thumb("pat", val === "auto" ? patternFor({ patterns: {} }, lb) : val) : thumb("fig", val);
          c.drawImage(th, Math.floor(rx - 48), Math.floor(y + rh / 2 - 15)); if (on) rect(c, rx - 48, y + rh / 2 - 15, rx - 1, y + rh / 2 + 14, null, acc()); rx -= 58;
        }
        if (on) text(c, rx, y + rh / 2, "<", fv, acc(), "rm");
      }
      if (sep) line(c, [[px + 1, y + rh - 1], [px + pw - 1, y + rh - 1]], [29, 29, 28]);
    }
    y += rh;
  });
  text(c, px + 22, py + ph - 20, "ESCAPE/UI", font("px", 12), DIM, "lm");
  text(c, px + pw - 22, py + ph - 20, "◀▶ CHANGE · A " + (APP.page === "covs" ? "YOUR OWN" : "OPEN") + " · B " + (APP.page === "main" ? "SAVE & EXIT" : "BACK"), font("px", 12), DIM, "rm");
}
function appKey(k) {
  const rows = appRows(); if (k !== "a") APP.armed = false;
  if (k === "up") APP.cur = (APP.cur - 1 + rows.length) % rows.length;
  else if (k === "down") APP.cur = (APP.cur + 1) % rows.length;
  else if (k === "left" || k === "right") { const r = rows[APP.cur]; if (!["open", "danger"].includes(r[1][0])) r[2](k === "left" ? -1 : 1); }
  else if (k === "a") { const r = rows[APP.cur]; if (r[0].startsWith("Draw all")) APP.armed = true; else if (r[1][0] === "cov") addOwnCover(r[0]); else r[2](["open", "danger"].includes(r[1][0]) ? 0 : 1); }
  else if (k === "b") { if (APP.page !== "main") { APP.cur = { figs: 8, pats: 9, covs: 10 }[APP.page]; APP.page = "main"; APP.top = 0; } else return leaveApp(); }
  else if (k === "start") return leaveApp();
  persist(); thumbCache.clear(); render();
}
function leaveApp() { persist(); syncHeader(); show("list"); startFigure(); }

// ---------- ES's help bar and status line ----------
const HELP = {
  sys: [["start", "MENU"], ["B", "NAVIGATION BAR"], ["Y", "SEARCH"], ["X", "RANDOM"], ["A", "SELECT"], ["dpad", "CHOOSE"]],
  list: [["select", "OPTIONS"], ["start", "MENU"], ["B", "BACK"], ["Y", "SEARCH"], ["X", "FAVORITE"], ["A", "LAUNCH"]],
  menu: [["start", "CLOSE"], ["B", "BACK"], ["A", "SELECT"], ["dpad", "CHANGE"], ["dpad", "CHOOSE"]],
};
function renderHelp() {
  const h = screen === "menu" ? HELP.menu : screen === "list" ? HELP.list : screen === "sys" ? HELP.sys : null;
  $("help").hidden = !h; $("status").hidden = screen === "boot" || screen === "app" || screen === "charge";
  if (!h) return;
  $("help").innerHTML = h.map(([b, t]) => `<span><i class="hb hb-${b}">${b.length === 1 ? b : ""}</i>${t}</span>`).join("");
}
function clock() { const d = new Date(); $("clock").textContent = pad2(d.getHours()) + ":" + pad2(d.getMinutes()); $("batt").textContent = batt.lvl + "%"; }

// ---------- battery effects (ES's battery icon over the whole screen) ----------
function renderFx() {
  const st = $("stage"), onSys = screen === "sys" || (screen === "menu" && under === "sys");
  st.classList.toggle("low", S.lowbatt === "on" && !batt.chg && batt.lvl <= 10 && screen !== "boot" && screen !== "app");
  fxCharge.on = false;   // the in-menu effect is gone: charged.py shows a charging screen instead
  fxCharge.card = onSys ? COLLS[ci] : null;
}
// charge_frames(): fringes in torn zones over the card + flickering dead pixels; game lists get thin torn lines
const PAL = [[0, 0, 0], [2, 2, 2], [255, 0, 64], [0, 220, 255], [0, 255, 106], [42, 107, 255], [255, 255, 255], [255, 0, 255], [0, 240, 255]];
const fxCharge = { on: false, card: null, frames: new Map(), f: 0 };
function chargeFrames(card) {
  const key = (card || "") + S.accent + (card ? figureFor(CFG, card) : ""); if (fxCharge.frames.has(key)) return fxCharge.frames.get(key);
  let lum = null;
  if (card) {
    const cc = mk(W, H), c = ctx(cc); c.drawImage(baseOf(), 0, 0); const fc = mk(HERO[2], HERO[3]); figFrame(ctx(fc), figureFor(CFG, card), 0, acc()); c.drawImage(fc, HERO[0], HERO[1]); c.drawImage(overOf(card, 3), 0, 0);
    const d = c.getImageData(0, 0, W, H).data; lum = new Int16Array(W * H); for (let i = 0; i < W * H; i++) lum[i] = (d[i * 4] * 299 + d[i * 4 + 1] * 587 + d[i * 4 + 2] * 114) / 1000 | 0;
  }
  const r = new PyRandom(card || 7), frames = []; let dead = [];
  for (let f = 0; f < 14; f++) {
    const idx = new Uint8Array(W * H);
    for (let z = 0, nz = 2 + r.randrange(3); z < nz; z++) {
      const zw = Math.floor(90 + r.random() * 420), zh = r.random() < .5 ? Math.floor(10 + r.random() * 40) : Math.floor(60 + r.random() * 160);
      const zx = Math.floor(r.random() * (W - zw)), zy = Math.floor(r.random() * (H - zh)), s = 4 + r.randrange(6);
      if (lum) for (let y = zy; y < zy + zh; y++) for (let x = zx; x < zx + zw; x++) {
        const v = lum[y * W + x], rv = x - s >= zx ? lum[y * W + x - s] : 0, lv = x + s < zx + zw ? lum[y * W + x + s] : 0;
        if (rv - v > 60) idx[y * W + x] = 2; if (lv - v > 60) idx[y * W + x] = 3;
      } else { const yy = zy + (zh >> 1); for (let x = zx; x < zx + zw; x++) idx[yy * W + x] = 2; for (let x = Math.min(W - 1, zx + 6); x < Math.min(W, zx + zw + 6); x++) idx[Math.min(H - 1, yy + 2) * W + x] = 3; }
    }
    if (r.random() < 0.9) { const ln = r.random() < .12, sz = 2 + r.randrange(4); for (let k = 0, m = ln ? 1 : 1 + r.randrange(3); k < m; k++) dead.push([r.randrange(W), r.randrange(H), ln ? Math.floor(30 + r.random() * 160) : sz, ln ? 1 : sz, 2 + r.randrange(PAL.length - 2), f + 1 + r.randrange(8)]); }
    dead = dead.filter(p => p[5] > f);
    for (const [x, y, w, h, c] of dead) if (r.random() < .85) for (let yy = y; yy < Math.min(H, y + h); yy++) for (let xx = x; xx < Math.min(W, x + w); xx++) idx[yy * W + xx] = c;
    const cv = mk(W, H), c = ctx(cv), im = c.createImageData(W, H);
    for (let i = 0; i < W * H; i++) if (idx[i] >= 2) { const p = PAL[idx[i]]; im.data[i * 4] = p[0]; im.data[i * 4 + 1] = p[1]; im.data[i * 4 + 2] = p[2]; im.data[i * 4 + 3] = 255; }
    c.putImageData(im, 0, 0); frames.push(cv);
  }
  fxCharge.frames.set(key, frames); return frames;
}
setInterval(() => {
  const c = ctx($("fx-charge")); c.clearRect(0, 0, W, H);
  if (!fxCharge.on) return;
  const fr = chargeFrames(fxCharge.card); fxCharge.f = (fxCharge.f + 1) % fr.length; c.drawImage(fr[fxCharge.f], 0, 0);
}, 110);
// vignette_frames(): red dots on a 2-px Bayer grid, breathing (12 frames × 110 ms)
const vig = (() => {
  const B = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], frames = [];
  for (let k = 0; k < 12; k++) {
    const f = 0.15 + 0.85 * (0.5 - 0.5 * Math.cos(TAU * k / 12)), cv = mk(W, H), c = ctx(cv), im = c.createImageData(W, H);
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const dx = (x - W / 2) / (W / 2), dy = (y - H / 2) / (H / 2), r = Math.sqrt(dx * dx * 0.9 + dy * dy * 1.1), a = Math.pow(Math.max(0, Math.min(1, (r - 0.72) / 0.5)), 1.8);
      if (a * f * 0.6 > B[(y >> 1) & 3][(x >> 1) & 3] / 16) { const i = (y * W + x) * 4; im.data[i] = 255; im.data[i + 1] = 24; im.data[i + 2] = 16; im.data[i + 3] = 255; }
    }
    c.putImageData(im, 0, 0); frames.push(cv);
  }
  return { frames, f: 0 };
})();
setInterval(() => { const c = ctx($("fx-vig")); c.clearRect(0, 0, W, H); if (!$("stage").classList.contains("low")) return; vig.f = (vig.f + 1) % 12; c.drawImage(vig.frames[vig.f], 0, 0); }, 110);

// ---------- input: the Brick's buttons (keyboard: arrows, Enter = A, Backspace/Esc = B, M = START) ----------
// ---------- the charging screen (tool/charge_screen.py): plugged in + 15 s untouched, once per plug-in ----------
const CHG = { timer: null, fig: "globe", k: 0, burst: -1, next: 0, rnd: null, back: null, prev: "sys" };
function armCharging() {
  clearTimeout(CHG.timer);
  if (batt.chg && S.charge === "on") CHG.timer = setTimeout(() => { if (screen !== "app" && screen !== "boot" && screen !== "charge") openCharging(); }, 15000);
}
function openCharging() {
  CHG.prev = screen === "menu" ? under : screen; CHG.fig = SHAPE_LIST[Math.floor(Math.random() * SHAPE_LIST.length)];
  CHG.k = 0; CHG.burst = -1; CHG.next = performance.now() + 1000 + Math.random() * 2000; CHG.rnd = new PyRandom(Math.floor(Math.random() * 1e9));
  const b = mk(W, H), c = ctx(b); rect(c, 0, 0, W - 1, H - 1, VOID);
  const f = font("dot", 36, 900); textSpaced(c, W / 2 - textW(f, "ESCAPE/UI", 10) / 2, 560, "ESCAPE/UI", f, INK, "lm", 10);
  text(c, W / 2, 604, "エスケープ", font("jp", 14), DIM, "mm"); text(c, W / 2, 660, `CHARGING · ${batt.lvl}%`, font("px", 16), INK, "mm");
  rect(c, W / 2 - 110, 684, W / 2 + 110, 688, null, [60, 60, 58]); rect(c, W / 2 - 109, 685, W / 2 - 109 + 218 * batt.lvl / 100, 687, acc());
  CHG.back = b; show("charge");
}
function chargeTick() {
  if (screen !== "charge") return;
  const [span, sec] = LOOP[CHG.fig] || [TAU, 12], n = Math.max(2, Math.round(sec * 24));
  const cv = $("chg-screen"), c = ctx(cv); c.drawImage(CHG.back, 0, 0);
  renderShape(c, CHG.fig, span * (CHG.k % n) / n, acc(), 400, 400, 0.8, null, 1, W / 2 - 200, 130); CHG.k++;
  const now = performance.now();
  if (CHG.burst < 0 && now >= CHG.next) { CHG.burst = 0; CHG.blen = 6 + CHG.rnd.randrange(8); }
  if (CHG.burst >= 0) {
    const g = glitchFrame(cv, Math.min(14, Math.floor(CHG.burst * 15 / CHG.blen)), CHG.rnd); c.fillStyle = "#000"; c.fillRect(0, 0, W, H); c.drawImage(g, 0, 0);
    if (++CHG.burst >= CHG.blen) { CHG.burst = -1; CHG.next = now + 2000 + Math.random() * 4000; }
  }
}
setInterval(chargeTick, 1000 / 24);

function key(k) {
  armCharging();
  if (screen === "charge") { show(CHG.prev); startFigure(); return; }   // the button is eaten, as on the Brick
  if (screen === "boot") { show("sys"); startFigure(); return; }
  if (screen === "menu") return menuKey(k);
  if (screen === "app") return appKey(k);
  if (k === "start") return openMenu("main");
  if (screen === "sys") {
    if (k === "left" || k === "right") { ci = (ci + (k === "left" ? -1 : 1) + COLLS.length) % COLLS.length; startFigure(); }
    else if (k === "a") { gi = 0; gtop = 0; show("list"); return; }
  } else if (screen === "list") {
    const n = gamesOf(COLLS[ci]).length;
    if (k === "up") gi = (gi - 1 + n) % n; else if (k === "down") gi = (gi + 1) % n;
    else if (k === "left") gi = Math.max(0, gi - 10); else if (k === "right") gi = Math.min(n - 1, gi + 10);
    else if (k === "b") { show("sys"); startFigure(); return; }
    else if (k === "a" && gamesOf(COLLS[ci])[gi] === "EscapeUI") { APP.page = "main"; APP.cur = 0; show("app"); return; }
  }
  render();
}
const KEYMAP = { ArrowUp: "up", ArrowDown: "down", ArrowLeft: "left", ArrowRight: "right", Enter: "a", " ": "a", Backspace: "b", Escape: "b", m: "start", M: "start" };
addEventListener("keydown", e => { const k = KEYMAP[e.key]; if (k) { e.preventDefault(); key(k); } });
document.querySelectorAll("[data-k]").forEach(b => b.addEventListener("click", () => key(b.dataset.k)));

// ---------- the page around the screen ----------
function syncHeader() {
  document.querySelectorAll(".sw").forEach(b => b.setAttribute("aria-pressed", b.dataset.a === S.accent));
  document.querySelectorAll("[data-mo]").forEach(b => b.setAttribute("aria-pressed", b.dataset.mo === S.motion));
  $("chg").setAttribute("aria-pressed", batt.chg); $("batt-val").textContent = batt.lvl + "%"; clock();
}
PALETTE.forEach(([slug, name, c]) => {
  const b = document.createElement("button"); b.className = "sw"; b.dataset.a = slug; b.title = name; b.setAttribute("aria-label", name);
  b.style.background = css(c); b.onclick = () => { S.accent = slug; persist(); syncHeader(); startFigure(); render(); }; $("swatches").appendChild(b);
});
document.querySelectorAll("[data-mo]").forEach(b => b.onclick = () => { S.motion = b.dataset.mo; persist(); syncHeader(); startFigure(); render(); });
document.querySelectorAll("[data-go]").forEach(b => b.onclick = () => {
  const g = b.dataset.go; mstack = [];
  if (g === "menu") { under = "sys"; screen = "sys"; openMenu("main"); return; }
  if (g === "app") { APP.page = "main"; APP.cur = 0; show("app"); return; }
  show(g); startFigure();
});
$("batt-in").oninput = e => { batt.lvl = +e.target.value; syncHeader(); render(); };
$("chg").onclick = () => { batt.chg = !batt.chg; syncHeader(); if (!batt.chg && screen === "charge") show(CHG.prev); armCharging(); render(); };
function fit() {
  const f = $("frame").getBoundingClientRect(), padd = innerWidth < 640 ? 16 : 36;
  const s = Math.min((f.width - padd) / 1024, (Math.max(f.height, 260) - padd) / 768, 1.25);
  $("viewport").style.width = 1024 * s + "px"; $("viewport").style.height = 768 * s + "px"; $("stage").style.transform = `scale(${s})`;
}
addEventListener("resize", fit);
setInterval(clock, 10000);
const FONTS = ['900 76px "Doto"', '400 16px "Silkscreen"', '700 16px "Silkscreen"', '300 15px "Archivo"', '400 16px "Archivo"', '400 16px "Noto Sans JP"'];
Promise.all(FONTS.map(f => document.fonts.load(f, "AZaz09エスケープ脱出→")).concat([photosReady])).catch(() => {}).then(() => {
  if (!PHOTOS.original.EscapeUI) PHOTOS.original.EscapeUI = escapeUiPhoto();
  fit(); syncHeader(); show("boot"); requestAnimationFrame(tick);
  setTimeout(() => { if (screen === "boot") { show("sys"); startFigure(); } }, 1600);
});
