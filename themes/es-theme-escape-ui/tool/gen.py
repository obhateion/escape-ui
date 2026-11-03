#!/usr/bin/env python3
"""escape/UI artwork generator for EmulationStation on Knulli/Batocera handhelds.

Draws everything the theme shows into <theme>/gen/: one card per custom collection (figure,
stickers at detail levels 0-5, video loop, charging overlay), a sticker cover per game at cover
levels 0-5, the boot screen and the battery effects. Settings live in
/userdata/system/configs/escape-ui/config.json so a theme update keeps them.

  gen.py            draw what is missing (new collections, new games, changed settings)
  gen.py --all      redraw everything
  gen.py --list     print collections and games it found
"""
import glob
import hashlib
import json
import math
import os
import random
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from PIL import Image, ImageChops, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art  # noqa: E402
import shapes  # noqa: E402
from art import DIM, INK, VOID, font  # noqa: E402

THEME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# ESCAPE_PC=<snapshot.json>: draw on a PC from a snapshot of the Brick (gen.py --snapshot there), into
# ESCAPE_GEN; then the folders are copied over. Everything else stays as on the Brick.
PC = os.environ.get("ESCAPE_PC")
GEN = os.environ.get("ESCAPE_GEN") or os.path.join(THEME, "gen")
FFMPEG = os.environ.get("ESCAPE_FFMPEG", "ffmpeg")
USERDATA = "/userdata"
ES_DIR = os.path.join(USERDATA, "system/configs/emulationstation")
CFG_DIR = os.path.join(USERDATA, "system/configs/escape-ui")
CFG = os.path.join(CFG_DIR, "config.json")

DEFAULTS = {
    "accent": [242, 242, 238],   # unused since the palette: the accent is the theme option escape-accent
    "boot_logo": "globe",
    "figures": {},          # collection name -> figure
    "patterns": {},         # game name -> pattern
    "covers": {},           # game name -> auto | original | custom | logo | none
    "draw_on_device": True,  # False: this Brick never draws, all its art comes ready from a PC (pc/sync.sh)
}
DISPLAY = {"custom-collections": "collections"}   # theme name -> what the card says
DEFAULT_FIG = {"ALL": "globe", "APPS": "cube", "GAMES": "checker", "SOUND": "waves", "custom-collections": "orbits", "ports": "orbits",
               "gba": "target", "gb": "dots", "nds": "burst", "easyrpg": "torus", "nes": "radar", "prboom": "tunnel", "dreamcast": "floor"}
BLURB = {"ALL": "Everything on the card in one list.", "APPS": "Tools, launchers and ports that are not games.",
         "GAMES": "Games only, from every console and port.", "SOUND": "Trackers, synths and sequencers."}
AUTO_BLURB = {"favorites": "The games you starred.", "last played": "What you played last.", "all games": "Every game on the card.",
              "never played": "Games you have not started yet."}


def display(c):
    """What a card is called on screen (the folder keeps ES's theme name)."""
    i = SYSINFO.get(c) or {}
    return DISPLAY.get(c) or (i.get("full") if i.get("kind") == "auto" else None) or c


def card_text(c, coll):
    """(pill, blurb, folder) for the card's left panel."""
    i = SYSINFO.get(c) or {}
    if i.get("kind") == "system":
        return "system", "%s. Every game in its rom folder." % i.get("full", c), i.get("folder", "/roms/" + c)
    if i.get("kind") == "auto":
        return "auto", AUTO_BLURB.get(i.get("full"), "One of the collections ES makes on its own."), "/auto/" + (i.get("full") or c)
    return "collection", BLURB.get(coll.upper(), "Your own collection. Add games from a game's options."), "/collections/" + (coll or "new")


def cover_level():
    """The cover-sticker level in use (the theme option; the app passes a new one before ES has it)."""
    v = os.environ.get("ESCAPE_COVER_LEVEL") or (str(snapshot().get("cover_level", 3)) if PC else es_setting("subset.escape-covers"))
    return int(v) if v in ("0", "1", "2", "3", "4", "5") else 3


W, H = 1024, 768
HERO = (430, 96, 560, 470)   # x, y, w, h of the figure box, as in the mock-up
FIG_LW = 2.2   # line width of the big figure (still and animated alike)


def fit(kind, s, maxw, size, smallest, wght=None):
    """(font, text) for a name in at most maxw px: the size steps down to `smallest`, then the end is cut
    with an ellipsis. Measures letters borrowed from system fonts too (art.length_any)."""
    s = art.drawable(font(kind, size, wght), s) or "?"
    while size > smallest and art.length_any(font(kind, size, wght), s) > maxw:
        size -= 2
    f = font(kind, size, wght)
    if art.length_any(f, s) > maxw:
        while len(s) > 1 and art.length_any(f, s + "…") > maxw:
            s = s[:-1].rstrip()
        s += "…"
    return f, s


HOOK = None   # the settings app shows progress through this: HOOK(text, fraction done 0..1)
_P = {"done": 0.0, "total": 1.0, "text": "", "at": 0.0}


def log(*a):
    print("[escape-ui]", *a, flush=True)
    _P["text"] = " ".join(str(x) for x in a)
    tick(0, force=True)


def tick(work=1, force=False):
    """Count finished work; tells the app at most ~8 times a second."""
    _P["done"] += work
    if HOOK and (force or time.time() - _P["at"] > 0.12):
        _P["at"] = time.time()
        HOOK(_P["text"], min(1.0, _P["done"] / max(1.0, _P["total"])))


# ---------- settings ----------

_SNAP = None


def snapshot():
    """PC mode: what the Brick sent (collections with their games, the settings, the colour)."""
    global _SNAP
    if _SNAP is None:
        with open(PC, encoding="utf-8") as f:
            _SNAP = json.load(f)
    return _SNAP


def load_cfg():
    if PC:
        c = json.loads(json.dumps(DEFAULTS)); c.update(snapshot()["cfg"]); return c
    c = json.loads(json.dumps(DEFAULTS))
    try:
        with open(CFG) as f:
            c.update(json.load(f))
    except Exception:
        pass
    c["accent"] = [max(0, min(255, int(v))) for v in c.get("accent", DEFAULTS["accent"])][:3]
    return c


def save_cfg(c):
    os.makedirs(CFG_DIR, exist_ok=True)
    tmp = CFG + ".tmp"
    with open(tmp, "w") as f:
        json.dump(c, f, indent=1, ensure_ascii=False)
    os.replace(tmp, CFG)


def figure_for(cfg, coll):
    f = cfg["figures"].get(coll) or DEFAULT_FIG.get(coll)
    if f not in shapes.SHAPES:
        f = shapes.LIST[art.rng(coll + "fig").randrange(len(shapes.LIST))]
    return f


def pattern_for(cfg, game):
    p = cfg["patterns"].get(game)
    if p not in art.PATTERNS:
        p = art.PATTERN_LIST[art.rng(game + "surface").randrange(len(art.PATTERN_LIST))]
    return p


# ---------- what is on the card ----------

_ES_SETTINGS = {"key": None, "vals": {}, "at": 0.0}


def es_setting(name):
    """One of ES's settings. The file is parsed again only when its time or size changed: charged.py
    asks every couple of seconds, and every read of /userdata goes through the exFAT FUSE daemon."""
    p = os.path.join(ES_DIR, "es_settings.cfg")
    try:
        st = os.stat(p)
        key = (st.st_mtime_ns, st.st_size)
        now = time.time()   # exFAT keeps coarse times: also look again after 30 s whatever they say
        if key != _ES_SETTINGS["key"] or now - _ES_SETTINGS["at"] > 30:
            vals = {}
            for e in ET.parse(p).getroot():
                if e.get("name") is not None and e.get("name") not in vals:
                    vals[e.get("name")] = e.get("value")
            _ES_SETTINGS.update(key=key, vals=vals, at=now)
        return _ES_SETTINGS["vals"].get(name)
    except Exception:   # missing, or caught half-written: read it again next time
        _ES_SETTINGS["key"] = None
        return None


def grouped():
    """Does ES put the custom collections under one card? It saves this as UseCustomCollectionsSystemEx
    and rewrites its settings file on its own (dropping the older UseCustomCollectionsSystem)."""
    ex = es_setting("UseCustomCollectionsSystemEx")
    if ex is not None:
        return ex != "false"
    return es_setting("UseCustomCollectionsSystem") != "false"


HIDDEN = set()   # rom files a gamelist hides
FAVS, PLAYED = set(), {}   # rom files marked favourite; rom file -> last played (for ES's auto collections)


def gamelists():
    """path (absolute) -> displayed name, from every system's gamelist.xml."""
    names = {}
    for gl in glob.glob(os.path.join(USERDATA, "roms/*/gamelist.xml")):
        base = os.path.dirname(gl)
        try:
            root = ET.parse(gl).getroot()
        except Exception:
            continue
        for g in root.iter("game"):
            p, n = g.findtext("path"), g.findtext("name")
            if p and (g.findtext("hidden") or "").lower() == "true":
                HIDDEN.add(os.path.normpath(os.path.join(base, p)))
            if not p or (g.findtext("hidden") or "").lower() == "true":
                continue
            if (g.findtext("favorite") or "").lower() == "true":
                FAVS.add(os.path.normpath(os.path.join(base, p)))
            if g.findtext("lastplayed"):
                PLAYED[os.path.normpath(os.path.join(base, p))] = g.findtext("lastplayed")
            ap = os.path.normpath(os.path.join(base, p))
            if not os.path.exists(ap):
                continue
            names[ap] = (n or os.path.splitext(os.path.basename(p))[0]).strip()
            PATHS.setdefault(names[ap], set()).add(ap)
            img = g.findtext("image")
            if img:
                ip = os.path.normpath(os.path.join(base, img))
                if os.path.exists(ip):
                    IMAGES.setdefault(names[ap], ip)
    return names


IMAGES = {}   # game name -> the picture the scraper (or the port) left in its gamelist


# ---------- the game's own picture ----------
# yours in SHARE/system/configs/escape-ui/covers/<game>.png|jpg, then what was found online
# (covers-found/), then the gamelist's own image; EscapeUI's picture is the theme's boot figure
COVERS_DIR = os.path.join(CFG_DIR, "covers")
FOUND_DIR = os.path.join(CFG_DIR, "covers-found")


def _in(folder, game):
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        f = os.path.join(folder, safe_name(game) + ext)
        if os.path.exists(f):
            return f
    return None


def photo_files(game):
    """{"original": path or None, "custom": path or None} for a game."""
    if PC:   # pulled next to the snapshot: photos/custom/<game>.*, photos/original/<game>.*
        root = os.path.join(os.path.dirname(PC), "photos")
        return {"original": _in(os.path.join(root, "original"), game), "custom": _in(os.path.join(root, "custom"), game)}
    if not IMAGES:
        gamelists()
    return {"original": _in(FOUND_DIR, game) if not IMAGES.get(game) else IMAGES.get(game), "custom": _in(COVERS_DIR, game)}


def cover_mode(cfg, game, files):
    m = (cfg.get("covers") or {}).get(game, "auto")
    if m == "auto":
        return "original" if files["original"] or game == "EscapeUI" else "custom" if files["custom"] else "logo"
    return m


def front_sticker(game, accent, cfg):
    """What goes on the sheet as the game's own sticker: ("paper", polaroid) or ("vinyl", logo) or None."""
    files = photo_files(game); mode = cover_mode(cfg, game, files)
    if mode == "none":
        return None
    path = files["custom"] if mode == "custom" else files["original"] if mode == "original" else None
    if path:
        try:
            return "paper", art.polaroid(Image.open(path), game)
        except Exception:
            pass
    if mode == "original" and game == "EscapeUI":   # no box art: the theme's own boot figure
        fig = shapes.render(cfg["boot_logo"], 0.6, accent, 220, 220, lw=1.4, R=80)
        return "paper", art.polaroid(fig, game)
    return "vinyl", art.logo_sticker(game, accent)


_MD5 = {}


def front_stamp(cfg, game):
    """Changes when the sticker would: the mode and the picture's content (a hash, so the Brick and a
    PC drawing from copies agree)."""
    files = photo_files(game); mode = cover_mode(cfg, game, files)
    f = files.get(mode) if mode in ("original", "custom") else None
    if f and f not in _MD5:
        with open(f, "rb") as fh:
            _MD5[f] = hashlib.md5(fh.read()).hexdigest()[:12]
    return [mode, _MD5.get(f, "") if f else "", cfg["boot_logo"] if game == "EscapeUI" else ""]


SYSINFO = {}   # card (ES theme name) -> {"kind": collection | system | auto, "full": ..., "folder": ...}
AUTO = {"all": ("auto-allgames", "all games"), "favorites": ("auto-favorites", "favorites"), "recent": ("auto-lastplayed", "last played"),
        "2players": ("auto-at2players", "2 players"), "4players": ("auto-at4players", "4 players"), "neverplayed": ("auto-neverplayed", "never played"),
        "retroachievements": ("auto-retroachievements", "achievements"), "lightgun": ("auto-lightgun", "lightgun"), "wheel": ("auto-wheel", "wheel"),
        "trackball": ("auto-trackball", "trackball"), "spinner": ("auto-spinner", "spinner"), "vertical": ("auto-verticalarcade", "vertical")}
SKIP_DIRS = {"images", "videos", "media", "manuals", "downloaded_images", "downloaded_videos", "thumbnails", "marquees", "wheels", "boxart", "snap", "titles"}


def es_systems():
    """The systems ES knows: [{name, full, path, exts, theme}] from its es_systems*.cfg."""
    out, seen = [], set()
    files = glob.glob(os.path.join(ES_DIR, "es_systems_*.cfg")) + ["/usr/share/emulationstation/es_systems.cfg"]
    for f in files:
        try:
            root = ET.parse(f).getroot()
        except Exception:
            continue
        for e in root.iter("system"):
            n = e.findtext("name")
            if not n or n in seen:
                continue
            seen.add(n)
            exts = {x.lower() for x in (e.findtext("extension") or "").split()}
            out.append({"name": n, "full": (e.findtext("fullname") or n).strip(), "path": (e.findtext("path") or "").strip(),
                        "exts": exts, "theme": (e.findtext("theme") or n).strip()})
    return out


def rom_files(path, exts, depth=2):
    """The games ES would list in a rom folder: files with the system's extensions (and folders named like
    one, e.g. "game.m3u"); scraper folders skipped."""
    out = []
    try:
        entries = list(os.scandir(path))
    except OSError:
        return out
    for e in entries:
        if e.name.startswith("."):
            continue
        ext = os.path.splitext(e.name)[1].lower()
        try:
            is_dir = e.is_dir(follow_symlinks=False)
        except OSError:
            continue
        if is_dir:
            if ext and ext in exts:
                out.append(os.path.normpath(e.path))
            elif depth > 1 and e.name.lower() not in SKIP_DIRS:
                out.extend(rom_files(e.path, exts, depth - 1))
        elif ext and ext in exts:
            out.append(os.path.normpath(e.path))
    return out


def collections():
    """{card name: [game names]} for every card ES shows on its home screen: custom collections, the
    consoles with games, ES's own auto collections. Card names are what ES calls the card's theme."""
    if PC:
        SYSINFO.update(snapshot().get("info", {}))
        return snapshot()["colls"]
    names = gamelists()
    # every rom on the card, scraped or not (ES lists a game without a gamelist entry by its file name)
    hidden_sys = set((es_setting("HiddenSystems") or "").split(";"))
    consoles = {}
    for sy in es_systems():
        if not sy["path"] or not os.path.isdir(sy["path"]):
            continue
        games = []
        for ap in rom_files(sy["path"], sy["exts"]):
            if ap in HIDDEN:
                continue
            g = names.get(ap) or os.path.splitext(os.path.basename(ap))[0]
            names[ap] = g; PATHS.setdefault(g, set()).add(ap); games.append(g)
        if games and sy["name"] not in hidden_sys:
            consoles[sy["theme"]] = games
            SYSINFO[sy["theme"]] = {"kind": "system", "full": sy["full"], "folder": "/roms/" + os.path.basename(sy["path"].rstrip("/"))}
    on = [s for s in (es_setting("CollectionSystemsCustom") or "").split(",") if s]
    cdir = os.path.join(ES_DIR, "collections")
    found = {}
    for f in glob.glob(os.path.join(cdir, "custom-*.cfg")):
        n = os.path.basename(f)[7:-4]
        games = []
        for line in open(f, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if not line:
                continue
            ap = os.path.normpath(os.path.join(USERDATA, line[2:] if line.startswith("./") else line))
            g = names.get(ap) or os.path.splitext(os.path.basename(ap))[0]
            games.append(g); PATHS.setdefault(g, set()).add(ap)
        found[n] = games
    in_cfgs = {g for v in found.values() for g in v} | {g for v in consoles.values() for g in v}
    for f in glob.glob(os.path.join(cdir, "*.xcc")):   # dynamic collections: ALL.xcc etc. take everything
        found[os.path.basename(f)[:-4]] = sorted(set(names.values()) | in_cfgs, key=str.lower)
    if on:
        found = {k: v for k, v in found.items() if k in on}
    if found and grouped():   # ES groups them under one card
        found = {"custom-collections": sorted({g for v in found.values() for g in v}, key=str.lower)}
    for k in found:
        SYSINFO[k] = {"kind": "collection"}
    # ES's own collections (favourites, last played, all games...), each its own card
    for a in [x for x in (es_setting("CollectionSystemsAuto") or "").split(",") if x]:
        theme, label = AUTO.get(a, ("auto-" + a, a))
        if any(theme.lower() == k.lower() for k in found):
            continue
        g = {"all": sorted(set(names.values()), key=str.lower), "favorites": sorted({names[p] for p in FAVS if p in names}, key=str.lower),
             "recent": [names[p] for p, _ in sorted(PLAYED.items(), key=lambda kv: kv[1], reverse=True) if p in names][:50],
             "neverplayed": sorted({n for p, n in names.items() if p not in PLAYED}, key=str.lower)}.get(a)
        found[theme] = g if g is not None else []
        SYSINFO[theme] = {"kind": "auto", "full": label, "known": g is not None}
    for k, v in consoles.items():   # the consoles: a rom folder with games that is not hidden
        if not any(k.lower() == c.lower() for c in found):   # (SHARE ignores case: one folder per name)
            found[k] = v
    return found


BAD_CHARS = '\\/:*?"<>|'   # what exFAT (the Brick's SHARE) and Windows refuse in a file name


def safe_name(n):
    """n as a file name the SHARE partition accepts."""
    s = "".join("_" if c in BAD_CHARS or ord(c) < 32 else c for c in n).rstrip(" .")
    return s or "_"


def by_name(n):
    """Can ES find a game's sheet by its name ({game:name})? Not when the name can't be a file name
    ("Zelda: Link's Awakening") — those are drawn per rom file instead ({game:path}, always a valid name)."""
    return safe_name(n) == n and len(n.encode("utf-8")) <= 240


PATHS = {}   # game name -> the rom files that carry it (for the sheets drawn per file)


def game_paths(g):
    if PC:
        return snapshot().get("paths", {}).get(g, [])
    return sorted(PATHS.get(g, ()))


def cover_files(G, L, g):
    """Where game g's sheet at level L goes: per rom file (covers/L/<absolute rom path>.png), which the
    theme finds with {game:path}. ES keeps the LAST {game:...} <path> of an image whether that file
    exists or not, so the theme can't fall back from a by-name file to a per-file one: every game goes
    per rom file. Only a game with no rom path known keeps a by-name file."""
    per_file = [os.path.join(G, "covers", str(L)) + p + ".png" for p in sorted(game_paths(g)) if p.startswith("/")]
    if per_file:
        return per_file
    return [os.path.join(G, "covers", str(L), safe_name(g) + ".png")]


# ---------- drawing ----------

def fig_still(fig, accent):
    """The figure as ES shows it behind the label: the first frame of its video (t=0), so the still
    card and the moment the video starts are the same picture."""
    return art.lum_alpha(figure_frame(fig, 0.0, accent))


def sys_base():
    """Shared background: black with the HUD corner ticks and the status-bar mark."""
    im = Image.new("RGB", (W, H), VOID); d = ImageDraw.Draw(im, "RGBA")
    for (x, y, dx, dy) in [(24, 24, 1, 1), (W - 24, 24, -1, 1), (24, H - 24, 1, -1), (W - 24, H - 24, -1, -1)]:
        d.line([(x, y + 10 * dy), (x, y), (x + 10 * dx, y)], fill=(255, 255, 255, 64), width=1)
    d.text((44, 46), "ESCAPE/UI", font=font("px", 16), fill=DIM, anchor="lm")
    return im


def sys_over(coll, games, level, accent, idx, total, fig="globe", key=None):
    """Everything in front of the figure: the left panel, the big label and the stickers up to `level`.
    key: the card's ES name (for system/auto cards: their pill, blurb and folder); games None = count unknown."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pill_word, blurb, folder = card_text(key if key is not None else coll, coll)
    generic = not coll   # the stand-in card for a collection that has no art yet: ES writes the name
    r = art.rng((coll or "new") + "stk"); pick = r.choice
    acc = tuple(accent)
    # left panel
    x0, y0 = 44, 120
    if not generic:
        d.text((x0, y0), "%02d" % idx, font=font("px", 12), fill=INK, anchor="lm")
        d.text((x0 + 26, y0), "/ %02d" % total, font=font("px", 12), fill=DIM, anchor="lm")
    if level >= 2:
        art.stripes(d, x0 + 78, y0 - 5, 30, 10, INK)
    n = coll.upper(); size = 76 if len(n) <= 5 else 54 if len(n) <= 8 else 38
    ft, nt = fit("dot", n, 360, size, 26, 900); size = ft.size
    if not generic:
        art.text_any(d, (x0 - 4, y0 + 30), nt, ft, INK, "lt", im)
    yk = y0 + 30 + int(size * 0.95) + 18
    w = art.pill(d, x0, yk, pill_word, filled=True)
    if not generic and games is not None:
        art.pill(d, x0 + w + 8, yk, "%d items" % len(games))
    fb = font("grot", 15, 300); yb = yk + 40; line = ""
    for word in blurb.split():
        if fb.getlength(line + " " + word) > 330 and line:
            d.text((x0, yb), line, font=fb, fill=(189, 189, 185)); yb += 22; line = word
        else:
            line = (line + " " + word).strip()
    d.text((x0, yb), line, font=fb, fill=(189, 189, 185))
    ys = yb + 46
    d.text((x0, ys), "FOLDER", font=font("px", 12), fill=DIM, anchor="lm")
    ff, ft_ = fit("grot", folder, 270, 16, 12, 400)
    art.text_any(d, (x0 + 96, ys), ft_, ff, INK, "lm", im)
    # the big label on the figure, centred on the word; the dot hangs outside in the accent
    hx, hy = HERO[0] + HERO[2] / 2, HERO[1] + HERO[3] / 2
    lab = coll.lower() if not generic else ""; ls = 128 if len(lab) <= 5 else max(44, int(128 * 5 / len(lab)))
    ls = ls if lab else 128
    fl, lab = fit("dot", lab, HERO[2] - 60, ls, 30, 900) if lab else (font("dot", ls, 900), lab)
    if generic:
        lab = None
    if lab:
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow); art.text_any(sd, (hx, hy), lab, fl, (0, 0, 0, 255), "mm", shadow)
        im.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(12)))
        im.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(4)))
        d = ImageDraw.Draw(im)
        art.text_any(d, (hx, hy), lab, fl, INK, "mm", im)
        lw = art.length_any(fl, lab); d.text((hx + lw / 2 + 2, hy), ".", font=fl, fill=acc, anchor="lm")
    if level >= 1:
        d.text((HERO[0] + HERO[2] - 4, HERO[1] + 8), "ESC.%02d" % idx, font=font("px", 12), fill=DIM, anchor="rt")
        d.text((HERO[0] + HERO[2] - 4, HERO[1] + 28), "%s" % shapes.NAMES.get(fig, "figure").upper(), font=font("px", 12), fill=DIM, anchor="rt")
    right = r.random() < 0.5
    pct = lambda a, b, span: a / 100 * span + r.random() * (b - a) / 100 * span
    # 2: a pill or two and a chevron run
    if level >= 2:
        px = HERO[0] + (20 if right else HERO[2] - 220); py = HERO[1] + pct(30, 44, HERO[3])
        w = art.pill(d, px, py, pick(art.PILLS))
        if r.random() < 0.6:
            w += 6 + art.pill(d, px + w + 6, py, pick(art.PILLS), filled=True)
        d.text((px + w + 10, py + 9), pick(art.CHEVS), font=font("px", 12), fill=acc, anchor="lm")
    # 3: sparkles and the collection's katakana down one edge
    if level >= 3:
        for i in range(3 + int(r.random() * 3)):
            sx = HERO[0] + (pct(8, 30, HERO[2]) if r.random() < .5 else pct(70, 92, HERO[2])); sy = HERO[1] + pct(10, 88, HERO[3])
            if i < 3 or level >= 5:
                art.sparkle(d, sx, sy, 6 + r.random() * 5)
        kx = HERO[0] + (HERO[2] - 4 if right else 4); ky = HERO[1] + pct(14, 30, HERO[3])
        art.vtext(d, kx, ky, art.KATA.get(n, pick(art.MORE_KATA)), font("jp", 13), (255, 255, 255, 90))
    # 4: technical bits in the bottom corners of the hero, crosses on the axis, one extra badge
    if level >= 4:
        by = HERO[1] + HERO[3] - 30
        art.warn_tri(d, HERO[0] + 6, by - 4); d.text((HERO[0] + 36, by + 6), "X %03d Y %03d" % (r.randrange(999), r.randrange(999)), font=font("px", 12), fill=DIM, anchor="lm")
        art.bars(d, HERO[0] + HERO[2] - 150, by, 64, 14, INK, r.randrange(1 << 30)); fr, rt = fit("px", "® " + coll.lower(), 72, 12, 12); art.text_any(d, (HERO[0] + HERO[2] - 78, by + 7), rt, fr, DIM, "lm", im)
        for cx in (HERO[0] + HERO[2] * 0.06, HERO[0] + HERO[2] * 0.94):
            cy = HERO[1] + pct(40, 60, HERO[3]); d.line([(cx - 6, cy), (cx + 6, cy)], fill=INK); d.line([(cx, cy - 6), (cx, cy + 6)], fill=INK)
        extra = r.randrange(4)
        ex = int(HERO[0] + pct(28, 56, HERO[2])); ey = int(HERO[1] + pct(2, 8, HERO[3]))
        st = [art.badge("%02d" % r.randrange(99)), art.arrow_stk(pick(["enter", "go", "next", "open"]), pick(["→", "»", "↗"])),
              art.checker_strip(), art.bar_stk("%08d" % r.randrange(10 ** 8))][extra]
        im.alpha_composite(st.rotate(r.random() * 10 - 5, resample=Image.BICUBIC, expand=True), (ex, ey))
        d = ImageDraw.Draw(im)
    # 5: one big stamp, the kanji, maybe a hazard band and a disc / jp label
    if level >= 5:
        stp = art.stamp(r.randrange(3), pick(art.STAMPS), acc).rotate(r.random() * 12 - 6, resample=Image.BICUBIC, expand=True)
        sx = HERO[0] + (HERO[2] - stp.width - 22 if right else 22); sy = int(HERO[1] + pct(66, 76, HERO[3]))
        im.alpha_composite(stp, (int(sx), sy))
        d = ImageDraw.Draw(im)
        kx = HERO[0] + (8 if right else HERO[2] - 40)
        art.vtext(d, kx + 16, HERO[1] + pct(10, 24, HERO[3]), art.KANJI.get(n, pick(art.MORE_KANJI)), font("jp", 30), (255, 255, 255, 60), 2)
        if r.random() < 0.6:
            hb = art.hazard_band(HERO[2], 12, acc); im.alpha_composite(hb, (HERO[0], HERO[1] + (HERO[3] - 40 if r.random() < .5 else 30)))
        e5 = art.disc(("DIGITAL", coll.upper()), acc) if r.random() < .5 else art.jp_label(pick(["注意", "危険", "再生", "停止", "高速"]), pick(["handle", "keep dry", "live", "do not bend"]))
        e5 = e5.rotate(r.random() * 12 - 6, resample=Image.BICUBIC, expand=True)
        im.alpha_composite(e5, (int(HERO[0] + (30 if right else HERO[2] - e5.width - 30)), int(HERO[1] + pct(64, 74, HERO[3])) - 60))
    return im


def sys_key(coll, fig, accent):
    """The key for the carousel strip at the bottom: mini emblem + name (24 px: on Silkscreen's 8 px grid)."""
    f, name = fit("px", coll.upper(), 180, 24, 24)
    im = Image.new("RGBA", (260, 72), (0, 0, 0, 0))
    em = art.lum_alpha(shapes.render(fig, 0.6, accent, 144, 144, lw=1.6, R=52, ss=2)).resize((64, 64), Image.LANCZOS)
    x0 = int((260 - (64 + 10 + art.length_any(f, name))) / 2)   # emblem + name centred in the key
    im.alpha_composite(em, (x0, 4))
    art.text_any(ImageDraw.Draw(im), (x0 + 74, 36), name, f, INK, "lm", im)
    return im


def menu_art(accent):
    """Our own frames for ES's menu (its stock ones are drawn for other corner sizes and
    leave the rows sticking out of the panel and a stripe through a focused button).
    9-patches, 48 px with 16 px corners."""
    bg = Image.new("RGBA", (48, 48), (11, 11, 11, 250)); d = ImageDraw.Draw(bg)
    d.rectangle([0, 0, 47, 47], outline=(255, 255, 255, 34))
    btn = Image.new("RGBA", (48, 48), (0, 0, 0, 0)); d = ImageDraw.Draw(btn)
    d.rectangle([0, 0, 47, 47], outline=(255, 255, 255, 90))
    btf = Image.new("RGBA", (48, 48), (36, 36, 36, 255)); d = ImageDraw.Draw(btf)
    d.rectangle([0, 0, 47, 47], outline=tuple(accent) + (255,))
    return bg, btn, btf


def list_head(coll, n, accent):
    im = Image.new("RGBA", (460, 64), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    tail = ("%d ITEMS · " % n if n is not None else "") + "FAV, A–Z"; tw = font("px", 12).getlength(tail)
    f, name = fit("dot", coll.upper(), 460 - tw - 18, 44, 24, 900)
    art.text_any(d, (0, 6 + (44 - f.size) * 0.7), name, f, INK, "lt", im)
    d.text((art.length_any(f, name) + 16, 36), tail, font=font("px", 12), fill=DIM, anchor="lm")
    return im


def cover(game, level, accent, cfg, idx=0):
    """A game's sticker sheet: stickers stuck on a patterned surface, more of them at higher levels."""
    CW, CH = 440, 264
    surf = pattern_for(cfg, game)
    im = art.pattern(surf, CW * 2, CH * 2).resize((CW, CH), Image.LANCZOS).convert("RGBA")
    r = art.rng(game + "sheet"); pick = r.choice; acc = tuple(accent)
    pool = []

    def add(lvl, img, round_=False):
        pool.append((lvl, img, round_))
    add(1, art.mini_figure(pick(shapes.LIST), r.random() * 6, acc, 110), True)
    num = Image.new("RGBA", (150, 70), (0, 0, 0, 0)); ImageDraw.Draw(num).text((75, 35), "%02d" % (idx + 1), font=font("dot", 64, 900), fill=INK, anchor="mm"); add(1, num)
    pl = Image.new("RGBA", (200, 22), (0, 0, 0, 0)); dp = ImageDraw.Draw(pl); w = art.pill(dp, 1, 2, pick(art.PILLS)); art.pill(dp, w + 7, 2, pick(art.PILLS), filled=True); add(2, pl.crop(pl.getbbox() or (0, 0, 1, 1)))
    add(2, art.arrow_stk(pick(["play", "go", "next", "run", "load"]), pick(["→", "↗", "»", "↘"])))
    ch = Image.new("RGBA", (70, 22), (0, 0, 0, 0)); ImageDraw.Draw(ch).text((35, 11), pick(art.CHEVS), font=font("px", 14), fill=acc, anchor="mm"); add(2, ch)
    kt = Image.new("RGBA", (34, 130), (0, 0, 0, 0)); art.vtext(ImageDraw.Draw(kt), 17, 4, pick(art.MORE_KATA), font("jp", 16), INK, 2); add(3, kt.crop(kt.getbbox() or (0, 0, 1, 1)))
    sp = Image.new("RGBA", (60, 40), (0, 0, 0, 0)); ds = ImageDraw.Draw(sp); art.sparkle(ds, 18, 20, 14); art.sparkle(ds, 44, 14, 7); add(3, sp)
    add(3, art.badge("%02d" % r.randrange(99)), True)
    add(4, art.bar_stk("%08d" % r.randrange(10 ** 8)))
    wt = Image.new("RGBA", (130, 24), (0, 0, 0, 0)); dw = ImageDraw.Draw(wt); art.warn_tri(dw, 0, 2); dw.text((30, 12), pick(["caution", "hot", "loud", "fragile", "beta"]).upper(), font=font("px", 9), fill=INK, anchor="lm"); add(4, wt.crop(wt.getbbox()))
    add(4, art.checker_strip())
    add(4, art.stripes_layer(46, 18, INK))
    add(5, art.stamp(r.randrange(3), pick(art.STAMPS), acc), r.random() < 0)
    add(5, art.disc(("DIGITAL", "ESCAPE"), acc), True)
    add(5, art.jp_label(pick(art.MORE_KANJI), pick(["handle", "keep dry", "do not bend", "live"])))
    pool = [p + ("vinyl",) for p in pool if p[0] <= max(1, level)]
    r.shuffle(pool)
    want = [0, 2, 4, 6, 9, 14][level]
    # the game's own picture (or its logo) goes on first, so it always finds room; level 0 = pattern only
    front = front_sticker(game, acc, cfg) if level >= 1 else None
    if front:
        pool.insert(0, (0, front[1], False, front[0])); want += 1
    placed = []; n = 0
    for lvl, img, rnd, kind in pool:
        if n >= want:
            break
        st = art.paper(img, r.random() * 16 - 8) if kind == "paper" else art.vinyl(img, rnd, 6, r.random() * 14 - 7)
        if st.width >= CW - 8 or st.height >= CH - 8:
            continue
        for _ in range(40):
            x = 4 + r.random() * (CW - st.width - 8); y = 4 + r.random() * (CH - st.height - 8)
            if any(x < px + pw - 4 and x + st.width - 4 > px and y < py + ph - 4 and y + st.height - 4 > py for px, py, pw, ph in placed):
                continue
            placed.append((x, y, st.width, st.height)); im.alpha_composite(st, (int(x), int(y))); n += 1
            break
    d = ImageDraw.Draw(im)
    tag = "PATTERN · " + surf.upper(); fw = font("px", 8); tw = fw.getlength(tag)
    d.rectangle([CW - tw - 16, CH - 20, CW - 6, CH - 6], fill=VOID); d.text((CW - 11, CH - 13), tag, font=fw, fill=DIM, anchor="rm")
    return im.convert("RGB")


def boot_screen(logo, accent):
    im = Image.new("RGB", (W, H), VOID)
    fig = art.lum_alpha(shapes.render(logo, 0.6, accent, 400, 400, lw=0.7))
    im.paste(fig, (W // 2 - 200, 130), fig)
    d = ImageDraw.Draw(im)
    art.draw_text(d, (W / 2 - art.text_w(font("dot", 36, 900), "ESCAPE/UI", 10) / 2, 560), "ESCAPE/UI", font("dot", 36, 900), INK, "lm", 10)
    d.text((W / 2, 604), "エスケープ", font=font("jp", 14), fill=DIM, anchor="mm")
    return im


def vignette_frames(n=12):
    """Low battery: red at the edges, breathing. GIF has no soft alpha, so the fade is an ordered
    dither of red dots on a 2-px grid (ES shows only the first frame of APNG and can't animate a
    battery icon's opacity) — which suits the theme anyway."""
    import numpy as np
    yy, xx = np.mgrid[0:H, 0:W]
    dx, dy = (xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2)
    r = np.sqrt(dx * dx * 0.9 + dy * dy * 1.1)
    a = np.clip((r - 0.72) / 0.5, 0, 1) ** 1.8
    bayer = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0
    thr = np.kron(bayer, np.ones((2, 2)))   # 2-px dots
    thr = np.tile(thr, (H // 8 + 1, W // 8 + 1))[:H, :W]
    frames = []
    for k in range(n):
        f = 0.15 + 0.85 * (0.5 - 0.5 * math.cos(2 * math.pi * k / n))
        idx = np.where(a * f * 0.6 > thr, 2, 0).astype(np.uint8)
        idx[0, 0] = idx[0, W - 1] = idx[H - 1, 0] = idx[H - 1, W - 1] = 1 if k % 2 else 0
        im = Image.fromarray(idx, "P"); im.putpalette([0, 0, 0, 2, 2, 2, 255, 24, 16] + [0] * 759)
        frames.append(im)
    return frames


def chroma(src, shift):
    """Split the channels sideways: red one way, blue the other."""
    r, g, b = src.convert("RGB").split()
    return Image.merge("RGB", (ImageChops.offset(r, shift, 0), g, ImageChops.offset(b, -shift, 0)))


# charging overlay as a palette GIF: index 0 transparent, a few fixed colours; every frame is full
# size (corner pixels alternate) and disposed before the next, so nothing piles up in ES's decoder
PAL = [(0, 0, 0), (2, 2, 2), (255, 0, 64), (0, 220, 255), (0, 255, 106), (42, 107, 255), (255, 255, 255), (255, 0, 255), (0, 240, 255)]
RED, CYAN = 2, 3


def charge_frames(card, seed, n=14):
    """Charging: in a few torn zones that jump every frame the edges split into red and cyan
    fringes (drawn over the real screen, not covering it), plus flickering dead pixels.
    card=None (game lists): thin torn red/cyan lines instead of fringes."""
    import numpy as np
    r = random.Random(seed); frames = []; dead = []
    lum = np.asarray(card.convert("L"), dtype=np.int16) if card is not None else None
    for f in range(n):
        idx = np.zeros((H, W), dtype=np.uint8)
        for _ in range(2 + r.randrange(3)):
            zw = int(90 + r.random() * 420); zh = int(10 + r.random() * 40) if r.random() < .5 else int(60 + r.random() * 160)
            zx = int(r.random() * (W - zw)); zy = int(r.random() * (H - zh)); s = 4 + r.randrange(6)
            if lum is not None:
                z = lum[zy:zy + zh, zx:zx + zw]
                right = np.zeros_like(z); right[:, s:] = z[:, :-s]    # the image moved right: red ghost
                left = np.zeros_like(z); left[:, :-s] = z[:, s:]      # moved left: cyan ghost
                sub = idx[zy:zy + zh, zx:zx + zw]
                sub[(right - z) > 60] = RED; sub[(left - z) > 60] = CYAN
            else:
                yy = zy + zh // 2
                idx[yy, zx:zx + zw] = RED; idx[min(H - 1, yy + 2), min(W - 1, zx + 6):min(W, zx + zw + 6)] = CYAN
        if r.random() < 0.9:
            line = r.random() < .12; sz = 2 + r.randrange(4)
            for _ in range(1 if line else 1 + r.randrange(3)):
                dead.append([r.randrange(W), r.randrange(H), int(30 + r.random() * 160) if line else sz, 1 if line else sz, 2 + r.randrange(len(PAL) - 2), f + 1 + r.randrange(8)])
        dead = [p for p in dead if p[5] > f]
        for x, y, w, h, c, _ in dead:
            if r.random() < .85:
                idx[y:y + h, x:x + w] = c
        k = 1 if f % 2 else 0   # corners toggle between transparent and near-black: whole-frame updates
        idx[0, 0] = idx[0, W - 1] = idx[H - 1, 0] = idx[H - 1, W - 1] = k
        im = Image.fromarray(idx, "P"); im.putpalette([v for c in PAL for v in c] + [0] * (768 - 3 * len(PAL)))
        frames.append(im)
    return frames


def save_anim(frames, path, ms=110):
    tmp = path + ".tmp.gif"
    frames[0].save(tmp, save_all=True, append_images=frames[1:], duration=ms, loop=0, disposal=2, transparency=0, optimize=False)
    os.replace(tmp, path)


# figure loops: (span of t, seconds). The span is the shortest stretch after which the figure looks the
# same again (a meridian step, a ring step, one star point...), so the loop has no seam; the seconds set
# how fast it turns. Played as a video: ES decodes h264 cheaply enough, while its GIF decoder thrashes
# past ~10 frames (1.1-2.2 cores). The loop is repeated inside one ~60 s file, because ES stalls for a
# moment each time it restarts a video.
LOOP = {"globe": (2 * math.pi / 12, 2.5), "checker": (math.pi / 4, 4), "waves": (2 * math.pi / 3, 3), "warp": (math.pi, 3.5),
        "orbits": (2 * math.pi, 12), "target": (2 * math.pi, 12), "spiral": (4 * math.pi / 3, 8), "burst": (math.pi, 6),
        "torus": (2 * math.pi, 3), "cube": (2 * math.pi, 3.5), "tunnel": (1 / 14 / 0.15, 3), "dots": (2 * math.pi, 14),
        "helix": (math.pi, 3), "lissajous": (math.pi / 2, 3), "rose": (math.pi, 6), "radar": (2 * math.pi / 2.2, 6),
        "floor": (1 / 12 / 0.2, 2.5), "stars": (math.pi / 2, 6)}
LOOP_VERSION = {"target": 10, "burst": 10}   # their loops had a seam before: redraw only these
VIDEO_FPS = 24      # looks the same as 30 here and costs ES less
VIDEO_LEN = 90.0    # seconds per file (the glitch entrance plays again when ES restarts it)


def loop_plan(fig):
    span, sec = LOOP.get(fig, (2 * math.pi, 12))
    n = max(2, int(round(sec * VIDEO_FPS)))
    reps = max(1, int(round(VIDEO_LEN / sec)))
    return span, n, reps


def figure_frame(fig, t, accent):
    """One frame of the figure as the card shows it: lines dimmed to 62 % on black."""
    return Image.eval(shapes.render(fig, t, accent, HERO[2], HERO[3], lw=FIG_LW), lambda v: v * 62 // 100)


GLITCH_FRAMES = 15   # 0.6 s at 24 fps


def glitch_frame(im, k, rnd):
    """Frame k of the entrance: blinks, torn horizontal bands, blocky pixels and a red/cyan split,
    all fading out as k reaches GLITCH_FRAMES (cyberpunk-style). The motion underneath keeps going,
    so the entrance runs straight into the loop."""
    s = 1.0 - k / GLITCH_FRAMES   # strength
    w, h = im.size
    if k in (0, 3, 7) or (k < 10 and rnd.random() < 0.15):
        return Image.new("RGB", (w, h))   # a dead frame
    out = im.convert("RGB")
    if rnd.random() < 0.8 * s:   # blocky
        f = 2 + int(rnd.random() * 10 * s)
        out = out.resize((max(1, w // f), max(1, h // f)), Image.NEAREST).resize((w, h), Image.NEAREST)
    bands = Image.new("RGB", (w, h))
    y = 0
    while y < h:   # torn: each band slides sideways
        bh = int(4 + rnd.random() * 46)
        dx = int((rnd.random() * 2 - 1) * 90 * s) if rnd.random() < 0.7 else 0
        bands.paste(out.crop((0, y, w, min(h, y + bh))), (dx, y))
        y += bh
    out = bands
    sh = int(3 + 10 * s)   # the channels drift apart
    r, g, b = out.split()
    out = Image.merge("RGB", (ImageChops.offset(r, sh, 0), g, ImageChops.offset(b, -sh, 0)))
    dim = 0.45 + 0.55 * (1 - s) + rnd.random() * 0.2
    return Image.eval(out, lambda v: min(255, int(v * dim)))


def figure_video(fig, accent, path):
    """The figure turning, as an h264 file: the loop's frames are drawn once (kept PNG-packed, they are
    mostly black) and fed to the encoder again and again, so every repeat joins frame-exact."""
    import io
    span, n, reps = loop_plan(fig)
    packed = []
    for k in range(n):
        b = io.BytesIO(); figure_frame(fig, span * k / n, accent).save(b, "PNG", compress_level=1)
        packed.append(b.getvalue()); tick(1)
    tmp = path + ".tmp.mp4"
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (HERO[2], HERO[3]),
           "-r", str(VIDEO_FPS), "-i", "-", "-c:v", "libx264", "-profile:v", "baseline", "-preset", "veryfast", "-crf", "22",
           "-g", "6", "-pix_fmt", "yuv420p", "-movflags", "+faststart", tmp]   # a key frame every 6: ES resuming
           # after the charging screen jumps into the stream, and long GOPs showed grey mush until the next one
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    rnd = random.Random(fig + "glitch")
    try:
        for r in range(reps):
            for k, b in enumerate(packed):
                im = Image.open(io.BytesIO(b))
                if r == 0 and k < GLITCH_FRAMES:   # the entrance: the figure arrives through pixel glitches
                    im = glitch_frame(im, k, rnd)
                p.stdin.write(im.convert("RGB").tobytes())
            tick(n // 2)
        p.stdin.close()
    except BrokenPipeError:
        pass
    p.wait()
    if p.returncode == 0:
        os.replace(tmp, path)
    elif os.path.exists(tmp):
        os.remove(tmp)
    return p.returncode == 0


CHG_FPS, CHG_SIZE = 24, 400   # the charging screen's figure (tool/charge_screen.py)
# drawn on a PC and in background runs; the app's own (foreground) run leaves them to the background,
# so the first setup on the Brick stays a few minutes
DRAW_CHARGE = bool(PC) or any(a in sys.argv for a in ("--event", "--all-colours", "--worker", "--library"))
# With "draw_on_device": false the Brick draws nothing itself: all art is drawn on a PC (pc/sync.sh:
# the Brick's snapshot -> library -> upload) and the Brick only puts the right drawn files in place.
# What the library lacks is listed in gen/<colour>/missing.txt and the log ("draw on the PC") and the
# old picture stays. --draw (or ESCAPE_DRAW=1) lets one run on the Brick draw anyway.
DRAW_FORCED = bool(PC) or "--draw" in sys.argv or os.environ.get("ESCAPE_DRAW") == "1"
_DRAW = {}


def drawing():
    """May this run draw art itself? Always on a PC; on the Brick unless config.json says
    "draw_on_device": false (then everything comes ready from the PC and the library)."""
    if DRAW_FORCED:
        return True
    if "v" not in _DRAW:
        _DRAW["v"] = bool(load_cfg().get("draw_on_device", True))
    return _DRAW["v"]
MISSING = {"G": None, "keys": []}   # what the colour being done could not take from the library


def cannot_draw(key):
    """Not drawing(): note the piece of art as missing (to draw on the PC) instead of drawing it."""
    if drawing():
        return False
    if key not in MISSING["keys"]:
        MISSING["keys"].append(key)
        log("missing in the library, draw on the PC:", key)
    return True


def write_missing(G):
    """gen/<colour>/missing.txt: what the Brick could not take from the library (none: no file)."""
    p = os.path.join(G, "missing.txt")
    try:
        if MISSING["keys"]:
            open(p + ".tmp", "w", encoding="utf-8").write(chr(10).join(MISSING["keys"]) + chr(10)); os.replace(p + ".tmp", p)
        elif os.path.exists(p):
            os.remove(p)
    except OSError:
        pass


def charge_plan(fig):
    """The charging screen's loop of a figure: (span of t, frames), at most 7 s."""
    span, sec = LOOP.get(fig, (2 * math.pi, 12))
    return span, max(2, min(CHG_FPS * 7, int(round(sec * CHG_FPS))))


def charge_frame(fig, t, accent):
    """One frame of the charging screen's figure, as PNG bytes (supersampled: smooth lines)."""
    import io
    b = io.BytesIO(); shapes.render(fig, t, accent, CHG_SIZE, CHG_SIZE, lw=1.6, ss=2).save(b, "PNG", compress_level=6)
    return b.getvalue()


def loop_frames(fig):
    """How much work a figure's video is, for the progress bar."""
    span, n, reps = loop_plan(fig)
    return n + reps * (n // 2)


# ---------- the run ----------

def stamp_of(*parts):
    return hashlib.md5(json.dumps(parts, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]


def write(path, im, **kw):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ext = os.path.splitext(path)[1]
    tmp = path + ".tmp" + ext
    im.save(tmp, **kw); os.replace(tmp, path)


def lock(wait):
    """One generator at a time (the app and the background event can overlap)."""
    import fcntl
    os.makedirs(GEN, exist_ok=True)
    f = open(os.path.join(GEN, ".lock"), "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | (0 if wait else fcntl.LOCK_NB))
    except OSError:
        return None
    return f


def theme_default_accent():
    """The colour theme.xml falls back to (<acc> in its variables). ES treats the FIRST colour of the
    option list as the default and, when you pick it, removes the setting: so the first one listed and
    <acc> must always be the same colour (update_accent_list keeps them together)."""
    try:
        m = re.search(r"<acc>(\w+)</acc>", open(os.path.join(THEME, "theme.xml"), encoding="utf-8").read())
        if m and m.group(1) in art.ACCENT_RGB:
            return m.group(1)
    except OSError:
        pass
    return "white"


def current_accent():
    """The accent ES uses now (an option of the theme); an empty one means the theme's default."""
    if PC:
        return snapshot()["accent"]
    s = es_setting("subset.escape-accent")
    return s if s in art.ACCENT_RGB else theme_default_accent()


def sys_stamp(cfg, colls, names, i, c, acc, fig=None):
    fig = fig or figure_for(cfg, c)
    info = SYSINFO.get(c) or {}
    return stamp_of(fig, acc, len(colls[c]), i, len(names), FIG_LW, 13, *([info] if info.get("kind", "collection") != "collection" else []))


def loop_stamp(fig, acc):
    return stamp_of(fig, acc, LOOP.get(fig), FIG_LW, VIDEO_FPS, VIDEO_LEN, GLITCH_FRAMES, LOOP_VERSION.get(fig, 9))


def cover_stamp(cfg, g, acc, pattern=None):
    return stamp_of(pattern or pattern_for(cfg, g), acc, front_stamp(cfg, g), 4)


def boot_stamp(logo, acc):
    return stamp_of(logo, acc, 2)


def want_for(cfg, colls, names, all_games, acc, videos=True):
    """The stamp every piece of art should have now (a changed stamp = draw it again)."""
    want = {"common": stamp_of(10, acc), "boot": boot_stamp(cfg["boot_logo"], acc)}
    for i, c in enumerate(names):
        want["sys:" + c] = sys_stamp(cfg, colls, names, i, c, acc)
        if videos:
            want["loop:" + c] = loop_stamp(figure_for(cfg, c), acc)
    if videos and DRAW_CHARGE:   # the charging screen's loops, every figure: the Brick never draws one when plugged in
        for fig in shapes.LIST:
            want["chg:" + fig] = stamp_of(fig, acc, charge_plan(fig), CHG_SIZE, 1)
    for g in all_games:
        want["cov:" + g] = cover_stamp(cfg, g, acc)
    return want


# ---------- the library: every variant drawn ahead (on a PC: gen.py --library) ----------
# gen/<colour>/lib/<kind>-<stamp>/ holds the files of one variant. Before drawing anything the generator
# looks there and copies, so picking another figure, pattern or boot logo costs the Brick a file copy.

def lib_dir(G, key):
    return os.path.join(G, "lib", key)


def lib_take(G, key, pairs):
    """Copy a variant from the library: pairs = [(file in the library, destination)]. False if missing."""
    import shutil
    d = lib_dir(G, key)
    if not pairs or not all(os.path.exists(os.path.join(d, n)) for n, _ in pairs):
        return False
    for n, dest in pairs:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(os.path.join(d, n), dest + ".tmp"); os.replace(dest + ".tmp", dest)
    return True


SYS_FILES = ["fig.png"] + ["over%d.png" % L for L in range(6)] + ["key.png", "head.png"]


def draw_sys(d, c, games, i, total, fig, acc):
    """A card's pictures into folder d."""
    known = (SYSINFO.get(c) or {}).get("known", True)
    write(os.path.join(d, "fig.png"), fig_still(fig, acc))
    for L in range(6):
        write(os.path.join(d, "over%d.png" % L), sys_over(display(c), games if known else None, L, acc, i + 1, total, fig, c)); tick(1)
    write(os.path.join(d, "key.png"), sys_key(display(c), fig, acc))
    write(os.path.join(d, "head.png"), list_head(display(c), len(games) if known else None, acc))


def draw_boot(d, logo, acc):
    write(os.path.join(d, "boot.png"), boot_screen(logo, acc))
    write(os.path.join(d, "menu-icon.png"), art.lum_alpha(shapes.render(logo, 0.6, acc, 120, 120, lw=1.2, R=48)))


def build_library(slug, cfg, colls, names, all_games):
    """Every variant the settings can ask for, for one colour: each collection with each of the 18
    figures (card + video), each game on each of the 16 patterns (all six levels), each boot logo."""
    G = os.path.join(GEN, slug); acc = art.ACCENT_RGB[slug]
    have = set(os.listdir(os.path.join(G, "lib"))) if os.path.isdir(os.path.join(G, "lib")) else set()
    jobs = []
    for logo in shapes.LIST:
        jobs.append(("boot-" + boot_stamp(logo, acc), lambda d, logo=logo: draw_boot(d, logo, acc)))
    for i, c in enumerate(names):
        for fig in shapes.LIST:
            jobs.append(("sys-" + sys_stamp(cfg, colls, names, i, c, acc, fig),
                         lambda d, c=c, i=i, fig=fig: draw_sys(d, c, colls[c], i, len(names), fig, acc)))
    for fig in shapes.LIST:
        jobs.append(("loop-" + loop_stamp(fig, acc), lambda d, fig=fig: figure_video(fig, acc, os.path.join(d, "fig.mp4"))))
    order = {g: k for k, g in enumerate(all_games)}
    for g in all_games:
        for pat in art.PATTERN_LIST:
            c2 = dict(cfg); c2["patterns"] = dict(cfg.get("patterns") or {}); c2["patterns"][g] = pat
            jobs.append(("cov-%s-%d" % (cover_stamp(cfg, g, acc, pat), order[g]),
                         lambda d, g=g, c2=c2: [write(os.path.join(d, "%d.png" % L), cover(g, L, acc, c2, order[g]), optimize=False) for L in range(6)]))
    todo = [(k, f) for k, f in jobs if k not in have]
    log("library %s: %d of %d variants to draw" % (slug, len(todo), len(jobs)))
    for n, (k, f) in enumerate(todo):
        if n % 50 == 0:
            log("library %s %d / %d" % (slug, n, len(todo)))
        tmp = lib_dir(G, k + ".tmp")
        import shutil
        shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
        f(tmp)
        os.replace(tmp, lib_dir(G, k))


def plan_accent(slug, cfg, colls, names, all_games, videos=True, force=False):
    """What is missing or out of date for one accent: (folder, rgb, stamps, want, todo)."""
    G = os.path.join(GEN, slug); acc = art.ACCENT_RGB[slug]
    try:
        stamps = json.load(open(os.path.join(G, "stamps.json")))
    except Exception:
        stamps = {}
    want = want_for(cfg, colls, names, all_games, acc, videos)
    todo = {k for k, s in want.items() if force or stamps.get(k) != s}
    want_lv = range(6) if all_levels(all_games) else [cover_level()]   # every level, or (big libraries) the one in use
    for g in all_games:
        if not set(want_lv) <= set(cover_levels_drawn(stamps, g)):
            todo.add("cov:" + g)
        elif not all(os.path.exists(f) for L in want_lv for f in cover_files(G, L, g)):
            todo.add("cov:" + g)   # drawn, but not where the theme looks now (or a rom file was added)
    if not os.path.exists(os.path.join(G, "base.png")):
        todo.add("common")
    for c in names:
        if videos and not os.path.exists(os.path.join(G, "sys", safe_name(c), "fig.mp4")):
            todo.add("loop:" + c)
    return G, acc, stamps, want, todo


def cover_levels_drawn(stamps, g):
    if "covlv:" + g in stamps:
        return stamps["covlv:" + g]
    return [0, 1, 2, 3, 4, 5] if "cov:" + g in stamps else []   # drawn before levels were tracked: all six


def ready_accents():
    """The colours whose art is complete and up to date (they are the ones offered in ES's menu)."""
    cfg = load_cfg(); colls = collections()
    names = sorted(colls, key=str.lower); all_games = sorted({g for v in colls.values() for g in v}, key=str.lower)
    return [s for s, _, _ in art.PALETTE if not plan_accent(s, cfg, colls, names, all_games)[4]]


def accent_ready(slug):
    return slug in ready_accents()


ACC_BEGIN, ACC_END = "<!-- accents: begin (written by tool/gen.py) -->", "<!-- accents: end -->"


def update_accent_list(ready=None):
    """Offer in ES's theme options only the colours that are drawn (a colour that is not would show
    an empty theme). The list lives between two markers in theme.xml; ES reads it on its next start.
    The default colour (<acc>) stays put while it is drawn and is always listed first (see
    theme_default_accent) — moving it would silently change the colour of anyone whose setting is empty."""
    ready = ready_accents() if ready is None else ready
    cur = current_accent()
    shown = [s for s, _, _ in art.PALETTE if s in ready or s == cur]
    if not shown:
        return
    default = theme_default_accent()
    if default not in shown:
        default = cur if cur in shown else shown[0]
    order = [default] + [s for s in shown if s != default]
    names = {s: n for s, n, _ in art.PALETTE}
    rows = ['    <include name="%s" displayName="%s">./accents/%s.xml</include>' % (s, names[s].lower(), s) for s in order]
    p = os.path.join(THEME, "theme.xml")
    try:
        txt = open(p, encoding="utf-8").read()
    except OSError:
        return
    a, b = txt.find(ACC_BEGIN), txt.find(ACC_END)
    if a < 0 or b < 0:
        return
    new = txt[:a + len(ACC_BEGIN)] + "\n" + "\n".join(rows) + "\n    " + txt[b:]
    new = re.sub(r"<acc>\w+</acc>", "<acc>%s</acc>" % default, new, count=1)
    if new != txt:
        with open(p + ".tmp", "w", encoding="utf-8") as f:
            f.write(new)
        os.replace(p + ".tmp", p)


def run(force=False, videos=True, accents=None, jobs=1, worker=False):
    """Draw the art for each accent in `accents` (default: the current one). Every accent has its own
    folder gen/<slug>, so switching between drawn colours is instant; "all" draws the whole palette."""
    t0 = time.time()
    cfg = load_cfg()
    colls = collections()
    cur = current_accent()
    if accents is None:
        accents = [cur]
    elif accents == "all":
        accents = [cur] + [s for s, _, _ in art.PALETTE if s != cur]
    names = sorted(colls, key=str.lower)
    all_games = sorted({g for v in colls.values() for g in v}, key=str.lower)

    # plan every accent first, so the app can show how far along it is
    plans = []
    total = 0.0
    for slug in accents:
        G, acc, stamps, want, todo = plan_accent(slug, cfg, colls, names, all_games, videos, force)
        total += sum({"common": 30, "boot": 3}.get(k, 14 if k.startswith("sys:") else 6 if k.startswith("cov:")
                     else loop_frames(figure_for(cfg, k[5:])) if k.startswith("loop:") else charge_plan(k[4:])[1] / 2 if k.startswith("chg:") else 1) for k in todo)
        plans.append((slug, G, acc, stamps, want, todo))
    _P.update(done=0.0, total=max(1.0, total))

    busy = [p for p in plans if p[5]]
    if jobs > 1 and len(busy) > 2:
        # the colour on screen here, the others split between `jobs` worker processes (one core each)
        first = busy[0]; log("accent", first[0]); _draw_accent(cfg, colls, names, all_games, *first[1:])
        _parallel(busy[1:], jobs, force, videos, cfg)
    else:
        for slug, G, acc, stamps, want, todo in plans:
            if todo:
                log("accent", slug)
            _draw_accent(cfg, colls, names, all_games, G, acc, stamps, want, todo)
    if not PC and not worker:   # on a PC only the art is made; the Brick keeps its own theme.xml
        _drop_old_layout()
        update_accent_list()
        publish_boot()
    log("done in %.0fs: %d accents, %d collections, %d games" % (time.time() - t0, len(accents), len(names), len(all_games)))
    return [p[0] for p in plans if p[5]]


def _parallel(busy, jobs, force, videos, cfg):
    """Draw the accents in `busy` with `jobs` gen.py workers; their progress is read from their log."""
    weight = {p[0]: sum({"common": 30, "boot": 3}.get(k, 14 if k.startswith("sys:") else 6 if k.startswith("cov:")
                         else loop_frames(figure_for(cfg, k[5:])) if k.startswith("loop:") else charge_plan(k[4:])[1] / 2 if k.startswith("chg:") else 1) for k in p[5]) for p in busy}
    groups = [busy[i::jobs] for i in range(jobs)]
    procs = []
    for g in groups:
        if not g:
            continue
        cmd = [sys.executable, os.path.abspath(__file__), "--worker"] + ["--accent=" + p[0] for p in g]
        cmd += ["--all"] if force else []
        cmd += [] if videos else ["--no-video"]
        cmd += ["--all-levels"] if ALL_LEVELS else []
        procs.append([subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1), None])
    try:
        import select as _sel
        while any(p.poll() is None for p, _ in procs) or any(p.stdout and not p.stdout.closed for p, _ in procs):
            live = [p.stdout for p, _ in procs if p.stdout and not p.stdout.closed]
            if not live:
                break
            for out in _sel.select(live, [], [], 0.5)[0]:
                line = out.readline()
                if not line:
                    out.close(); continue
                line = line.strip()
                for pr in procs:
                    if pr[0].stdout is out and line.startswith("[escape-ui] accent "):
                        if pr[1]:
                            tick(weight.get(pr[1], 0))   # that worker finished its previous colour
                        pr[1] = line.split()[-1]
                if line.startswith("[escape-ui] accent "):
                    log(line[len("[escape-ui] "):])
                else:
                    tick(0)
        for pr in procs:
            if pr[1]:
                tick(weight.get(pr[1], 0))
    finally:
        for p, _ in procs:
            if p.poll() is None:
                p.terminate()


def _draw_accent(cfg, colls, names, all_games, G, acc, stamps, want, todo):
    MISSING.update(G=G, keys=[])
    try:
        _draw_accent_in(cfg, colls, names, all_games, G, acc, stamps, want, todo)
    finally:
        if not drawing():
            write_missing(G)


def _draw_accent_in(cfg, colls, names, all_games, G, acc, stamps, want, todo):
    stamps_path = os.path.join(G, "stamps.json")
    os.makedirs(G, exist_ok=True)

    def done(key):
        stamps[key] = want[key]
        json.dump(stamps, open(stamps_path + ".tmp", "w")); os.replace(stamps_path + ".tmp", stamps_path)

    if "common" in todo and not cannot_draw("common"):
        log("base, menu, battery effects")
        write(os.path.join(G, "base.png"), sys_base())
        blank = art.pattern("carbon", 880, 528).resize((440, 264), Image.LANCZOS); db = ImageDraw.Draw(blank)
        db.rectangle([12, 230, 190, 252], fill=VOID); db.text((20, 241), "NO SHEET YET · RUN ESCAPE-UI", font=font("px", 8), fill=DIM, anchor="lm")
        write(os.path.join(G, "cover-blank.png"), blank)
        nd = os.path.join(G, "sys", "_new")   # stand-in for a collection that has no art yet
        write(os.path.join(nd, "fig.png"), fig_still("globe", acc))
        for L in range(6):
            write(os.path.join(nd, "over%d.png" % L), sys_over("", [], L, acc, 0, 0)); tick(2)
        write(os.path.join(nd, "head.png"), Image.new("RGBA", (4, 4), (0, 0, 0, 0)))   # ES writes the name itself
        write(os.path.join(G, "fx/clear.png"), Image.new("RGBA", (4, 4), (0, 0, 0, 0)))
        for f, im in zip(("menu-bg.png", "menu-button.png", "menu-button-on.png"), menu_art(acc)):
            write(os.path.join(G, "fx", f), im)
        save_anim(vignette_frames(), os.path.join(G, "fx/vignette.gif"), ms=110); tick(9)
        tick(9)
        done("common")
    if "boot" in todo:
        if lib_take(G, "boot-" + want["boot"], [(n, os.path.join(G, n)) for n in ("boot.png", "menu-icon.png")]):
            done("boot")
        elif not cannot_draw("boot-" + want["boot"]):
            draw_boot(G, cfg["boot_logo"], acc); done("boot")
        tick(3)
    for i, c in enumerate(names):
        fig = figure_for(cfg, c); games = colls[c]
        d = os.path.join(G, "sys", safe_name(c))
        if "sys:" + c in todo:
            log("collection", c, fig)
            if lib_take(G, "sys-" + want["sys:" + c], [(n, os.path.join(d, n)) for n in SYS_FILES]):
                done("sys:" + c)
            elif not cannot_draw("sys-" + want["sys:" + c] + " (" + c + ")"):
                draw_sys(d, c, games, i, len(names), fig, acc); done("sys:" + c)
            tick(8)
        if "loop:" + c in todo:
            log("animation", c, fig)
            if lib_take(G, "loop-" + want["loop:" + c], [("fig.mp4", os.path.join(d, "fig.mp4"))]):
                done("loop:" + c)
            elif not cannot_draw("loop-" + want["loop:" + c] + " (" + c + ")") and figure_video(fig, acc, os.path.join(d, "fig.mp4")):
                done("loop:" + c)
    for fig in shapes.LIST:   # the charging screen's loops
        if "chg:" + fig in todo:
            span, n = charge_plan(fig)
            d = os.path.join(G, "charge", fig); os.makedirs(d, exist_ok=True)
            try:   # already there (an art pack): meta.json carries the stamp it was drawn for
                m = json.load(open(os.path.join(d, "meta.json")))
                if m.get("stamp") == want["chg:" + fig] and all(os.path.exists(os.path.join(d, "%03d.png" % k)) for k in range(n)):
                    done("chg:" + fig)
                    continue
            except Exception:
                pass
            if cannot_draw("chg:" + fig):
                continue
            log("charging loop", fig)
            for k in range(n):
                p = os.path.join(d, "%03d.png" % k)
                open(p + ".tmp", "wb").write(charge_frame(fig, span * k / n, acc)); os.replace(p + ".tmp", p)
                tick(0.5)
            json.dump({"fig": fig, "n": n, "stamp": want["chg:" + fig]}, open(os.path.join(d, "meta.json"), "w"))
            done("chg:" + fig)
    covers = [g for g in all_games if "cov:" + g in todo]
    order = {g: k for k, g in enumerate(all_games)}
    lv = cover_level()
    for n, g in enumerate(covers):
        if n % 5 == 0:
            log("covers %d / %d" % (n + 1, len(covers)))
        fresh = stamps.get("cov:" + g) == want["cov:" + g]
        drawn = set(cover_levels_drawn(stamps, g)) if fresh else set()
        levels = range(6) if all_levels(all_games) else [lv]
        if not fresh:   # the sheet changed: the other levels' old files would show it outdated
            for L in set(range(6)) - set(levels):
                for f in cover_files(G, L, g):
                    if os.path.exists(f):
                        os.remove(f)
        key = "cov-%s-%d" % (want["cov:" + g], order[g])
        got = set()
        for L in levels:
            files = cover_files(G, L, g)
            if files and lib_take(G, key, [("%d.png" % L, f) for f in files]):
                got.add(L); tick(6 / len(levels)); continue
            if files and cannot_draw(key + " (" + g + ")"):
                tick(6 / len(levels)); continue
            im = cover(g, L, acc, cfg, order[g]) if files else None
            for f in files:
                write(f, im, optimize=False)
            got.add(L); tick(6 / len(levels))
        if got != set(levels):   # some level could not be taken from the library: keep it to do
            continue
        stamps["covlv:" + g] = sorted(drawn | set(levels))
        done("cov:" + g)


ALL_LEVELS = "--all-levels" in sys.argv   # every cover level now, not only the one in use
BIG_LIBRARY = 300   # games: up to this many, every cover level is drawn ahead (switching is instant)


def all_levels(all_games):
    return ALL_LEVELS or len(all_games) <= BIG_LIBRARY


def publish_boot():
    """ES shows the boot screen before it knows the accent, so splash.xml points at gen/boot.png:
    keep that a copy of the current colour's one."""
    import shutil
    src = os.path.join(GEN, current_accent(), "boot.png")
    if os.path.exists(src):
        shutil.copyfile(src, os.path.join(GEN, "boot.png.tmp")); os.replace(os.path.join(GEN, "boot.png.tmp"), os.path.join(GEN, "boot.png"))


def _drop_old_layout():
    """Before the palette everything lived straight in gen/: remove that once the accents are drawn."""
    import shutil
    for n in ("sys", "covers", "fx"):
        p = os.path.join(GEN, n)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
    for n in ("base.png", "cover-blank.png", "menu-icon.png", "stamps.json"):
        p = os.path.join(GEN, n)
        if os.path.exists(p):
            os.remove(p)


def stop_background():
    """Stop a background run (it may be drawing the other colours for the next half hour) so the app
    can draw what is on screen right away."""
    me = str(os.getpid())
    for pid in os.listdir("/proc"):
        if not pid.isdigit() or pid == me:
            continue
        try:
            cmd = open("/proc/%s/cmdline" % pid, "rb").read().split(b"\0")
        except OSError:
            continue
        if any(a.endswith(b"gen.py") for a in cmd) and (b"--event" in cmd or b"--all-colours" in cmd or b"--worker" in cmd):
            try:
                os.kill(int(pid), 15)
            except OSError:
                pass
    for pid in os.listdir("/proc"):   # its ffmpeg would keep the CPU busy for a while
        try:
            cmd = open("/proc/%s/cmdline" % pid, "rb").read()
        except OSError:
            continue
        if cmd.startswith(b"ffmpeg") and os.path.join(GEN, "").encode() in cmd:
            try:
                os.kill(int(pid), 15)
            except OSError:
                pass


if __name__ == "__main__":
    if "--snapshot" in sys.argv:   # for drawing on a PC: everything the drawing depends on
        cl = collections(); games = sorted({g for v in cl.values() for g in v})
        json.dump({"colls": cl, "cfg": load_cfg(), "accent": current_accent(), "paths": {g: game_paths(g) for g in games},
                   "info": SYSINFO, "cover_level": cover_level(),
                   "photos": {g: photo_files(g) for g in games}}, sys.stdout, ensure_ascii=False)
        sys.exit(0)
    if "--list" in sys.argv:
        print("grouped:", grouped(), "accent:", current_accent())
        for k, v in collections().items():
            print(k, len(v), v[:8])
        sys.exit(0)
    if "--event" in sys.argv:
        # from an ES event script: quietly, once at a time, the current colour only. It never
        # pokes ES (a reload while ES applied a setting hung it); new art shows on the next ES start.
        held = lock(wait=False)   # kept in a name: a lock file nobody holds is closed and lets go at once
        if not held:
            sys.exit(0)
        os.nice(19)
        run()
        sys.exit(0)
    if "--library" in sys.argv:   # on a PC: every variant for the colours given (--accent=...), into gen/<colour>/lib
        cfg = load_cfg(); colls = collections()
        names = sorted(colls, key=str.lower); all_games = sorted({g for v in colls.values() for g in v}, key=str.lower)
        for slug in [a.split("=", 1)[1] for a in sys.argv if a.startswith("--accent=")] or [s for s, _, _ in art.PALETTE]:
            build_library(slug, cfg, colls, names, all_games)
        sys.exit(0)
    worker = "--worker" in sys.argv   # one of _parallel()'s helpers: the parent holds the lock
    held = None if PC or worker else lock(wait=True)
    only = [a.split("=", 1)[1] for a in sys.argv if a.startswith("--accent=")]
    jobs = int(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--jobs=")), "1"))
    run(force="--all" in sys.argv, videos="--no-video" not in sys.argv,
        accents="all" if "--all-colours" in sys.argv else (only or None), jobs=jobs, worker=worker)
