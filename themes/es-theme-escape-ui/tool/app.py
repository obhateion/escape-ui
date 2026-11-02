#!/usr/bin/env python3
"""escape-UI: the settings app of the escape/UI theme (runs as a port, 1024x768, pad or keyboard).

Everything the theme can change: accent colour (presets or R/G/B), detail level, cover stickers,
figure motion, boot logo, battery effects, the figure of each collection, the pattern of each game.
B / START saves and leaves: the art is redrawn here, then ES restarts with the new settings.
"""
import os
import sys
import time

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art  # noqa: E402
import esctl  # noqa: E402
import gen  # noqa: E402
import shapes  # noqa: E402
from art import DIM, INK, VOID, font  # noqa: E402

W, H = 1024, 768
PAD_BUTTONS = {5: "A", 4: "B", 7: "X", 6: "Y", 13: "START", 14: "SELECT", 12: "MENU", 8: "L1", 9: "R1"}   # TrimUI Brick, Knulli
KEYS = {pygame.K_UP: "UP", pygame.K_DOWN: "DOWN", pygame.K_LEFT: "LEFT", pygame.K_RIGHT: "RIGHT", pygame.K_RETURN: "A",
        pygame.K_SPACE: "A", pygame.K_BACKSPACE: "B", pygame.K_ESCAPE: "B", pygame.K_m: "START", pygame.K_x: "X"}
RED = (255, 42, 31)
SUBSETS = {   # es_settings key -> (choices, default)
    "subset.escape-detail": (["0", "1", "2", "3", "4", "5"], "3"),
    "subset.escape-covers": (["0", "1", "2", "3", "4", "5"], "3"),
    "subset.escape-motion": (["video", "light", "still"], "video"),
    "subset.escape-ca": (["off", "always"], "off"),
    "subset.escape-lowbatt": (["on", "off"], "on"),
    "subset.escape-charge": (["on", "off"], "on"),
    "subset.escape-perf": (["on", "off"], "on"),
    "subset.escape-accent": ([s for s, _, _ in art.PALETTE], "white"),
}
THEME_NAME = "es-theme-escape-ui"
EVENTS = ["settings-changed", "config-changed", "game-end", "theme-changed"]
MOTION_NAMES = {"video": "animated", "light": "light", "still": "still"}
COVER_NAMES = {"original": "original", "custom": "your own", "logo": "logo", "none": "none"}


CUSTOM_SH = "/userdata/system/custom.sh"
HOOK_MARK = "# escape/UI: draw the missing accent colours while charging"


def boot_hook():
    """Start tool/charged.py at every boot from Batocera's custom.sh (added once, kept if it exists)."""
    try:
        txt = open(CUSTOM_SH).read() if os.path.exists(CUSTOM_SH) else "#!/bin/bash" + chr(10)
        if HOOK_MARK in txt:
            return
        start = 'case "$1" in start) nohup python3 %s/charged.py >/dev/null 2>&1 & ;; esac' % os.path.dirname(os.path.abspath(__file__))
        lines = txt.rstrip(chr(10)).split(chr(10))
        at = len(lines)   # before a closing top-level "exit", or the hook would never run
        while at > 1 and not lines[at - 1].strip():
            at -= 1
        if at > 1 and (lines[at - 1] == "exit" or lines[at - 1].startswith("exit ")):
            at -= 1
        lines[at:at] = ["", HOOK_MARK, start, ""]
        tmp = CUSTOM_SH + ".escape-ui.tmp"   # written whole, then swapped in: a cut-off custom.sh breaks the boot
        with open(tmp, "w") as f:
            f.write(chr(10).join(lines) + chr(10))
        os.chmod(tmp, 0o755)
        os.replace(tmp, CUSTOM_SH)
        os.sync()
        import subprocess
        subprocess.Popen(["python3", os.path.join(os.path.dirname(os.path.abspath(__file__)), "charged.py")],
                         start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


class Cancelled(Exception):
    """B pressed while drawing."""


class App:
    def __init__(self):
        pygame.init()
        self.scr = pygame.display.set_mode((W, H), pygame.FULLSCREEN)
        pygame.mouse.set_visible(False)
        self.joys = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]   # kept, or they close
        for j in self.joys:
            j.init()
        self.cfg = gen.load_cfg(); self.cfg0 = repr(self.cfg)
        self.sub = {k: (esctl.get(k) if esctl.get(k) in ch else d) for k, (ch, d) in SUBSETS.items()}
        self.sub["subset.escape-accent"] = gen.current_accent()   # an empty setting = the theme's default colour
        self.sub0 = dict(self.sub)
        self.colls = gen.collections()
        self.names = sorted(self.colls, key=str.lower)
        self.games = sorted({g for v in self.colls.values() for g in v}, key=str.lower)
        self.page, self.cur, self.top = "main", 0, 0
        if esctl.get("ThemeSet") != THEME_NAME or os.environ.get("ESCAPE_SETUP"):   # first run on this device: the setup screen
            self.page = "setup"
        self.thumbs = {}; self.bg = None; self.held = {}; self.dirty = True
        self.armed = False   # "Draw all colours" waits for a second A
        self.ready = gen.ready_accents(); self.drew = False   # colours already drawn (switching to them is instant)
        self.make_bg()

    # ---------- state ----------
    def acc(self):
        return art.ACCENT_RGB[self.sub["subset.escape-accent"]]

    def make_bg(self):
        """The current card behind the menu, darkened, like the mock-up."""
        try:
            c = self.names[0] if self.names else "ALL"
            g = gen.GEN
            im = Image.open(os.path.join(g, "base.png")).convert("RGBA")
            im.alpha_composite(Image.open(os.path.join(g, "sys", c, "fig.png")), (gen.HERO[0], gen.HERO[1]))
            im.alpha_composite(Image.open(os.path.join(g, "sys", c, "over3.png")))
        except Exception:
            im = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        dark = Image.new("RGBA", (W, H), (0, 0, 0, 208)); im.alpha_composite(dark)
        self.bg = im.convert("RGB")   # draw on RGB: Pillow only blends translucent fills into RGB images

    def thumb(self, kind, val):
        k = (kind, val, self.acc())
        if k not in self.thumbs:
            if kind == "fig":
                im = art.lum_alpha(shapes.render(val, 0.6, self.acc(), 96, 60, lw=1.0, R=22, ss=2))
            else:
                im = art.pattern(val, 96, 60).convert("RGBA")
            t = Image.new("RGBA", (48, 30), (0, 0, 0, 255)); t.alpha_composite(im.resize((48, 30), Image.LANCZOS))
            ImageDraw.Draw(t).rectangle([0, 0, 47, 29], outline=(255, 255, 255, 40))
            self.thumbs[k] = t
        return self.thumbs[k]

    def items(self):
        if self.page == "main":
            return [
                ("Accent colour", ("chip", self.sub["subset.escape-accent"] + ("" if self.sub["subset.escape-accent"] in self.ready else " · draws on save")), lambda d: self.ch_sub("subset.escape-accent", d), True),
                ("Detail level", ("txt", self.sub["subset.escape-detail"] + " / 5"), lambda d: self.ch_sub("subset.escape-detail", d), False),
                ("Cover stickers", ("txt", self.sub["subset.escape-covers"] + " / 5"), lambda d: self.ch_sub("subset.escape-covers", d), False),
                ("Figure motion", ("txt", MOTION_NAMES[self.sub["subset.escape-motion"]]), lambda d: self.ch_sub("subset.escape-motion", d), True),
                ("Boot logo", ("fig", self.cfg["boot_logo"]), self.ch_boot, False),
                ("Chromatic aberration", ("txt", self.sub["subset.escape-ca"]), lambda d: self.ch_sub("subset.escape-ca", d), False),
                ("Low battery pulse · ≤10%", ("txt", self.sub["subset.escape-lowbatt"]), lambda d: self.ch_sub("subset.escape-lowbatt", d), False),
                ("Charging screen", ("txt", self.sub["subset.escape-charge"]), lambda d: self.ch_sub("subset.escape-charge", d), False),
                ("Smooth mode (more power)", ("txt", self.sub["subset.escape-perf"]), lambda d: self.ch_sub("subset.escape-perf", d), True),
                ("Figures of collections", ("open", ""), lambda d: self.open("figs"), False),
                ("Patterns of covers", ("open", ""), lambda d: self.open("pats"), False),
                ("Covers of games", ("open", ""), lambda d: self.open("covs"), False),
                (self.draw_all_label(), ("open", ""), lambda d: self.draw_all(), False),
                ("Save & exit", ("open", ""), lambda d: self.leave(True), True),
                ("Reset figures & patterns", ("danger", ""), self.reset, False),
            ]
        if self.page == "figs":
            rows = [(n, ("fig", gen.figure_for(self.cfg, n)), (lambda n: lambda d: self.ch_fig(n, d))(n), False) for n in self.names]
            return rows + [("Reset figures", ("danger", ""), lambda d: self.reset(d, figs=True, pats=False), False)]
        if self.page == "covs":
            rows = [(g, ("cov", self.cover_mode(g)), (lambda g: lambda d: self.ch_cov(g, d))(g), False) for g in self.games]
            return rows + [("Reset covers", ("danger", ""), lambda d: self.reset_covers(d), False)]
        rows = [(g, ("pat", self.cfg["patterns"].get(g) or "auto"), (lambda g: lambda d: self.ch_pat(g, d))(g), False) for g in self.games]
        return rows + [("Reset patterns", ("danger", ""), lambda d: self.reset(d, figs=False, pats=True), False)]

    # ---------- changes ----------
    def ch_sub(self, key, d):
        ch = SUBSETS[key][0]; self.sub[key] = ch[(ch.index(self.sub[key]) + d) % len(ch)]

    def ch_boot(self, d):
        L = shapes.LIST; self.cfg["boot_logo"] = L[(L.index(self.cfg["boot_logo"]) + d) % len(L)] if self.cfg["boot_logo"] in L else L[0]

    def ch_fig(self, n, d):
        L = shapes.LIST; cur = gen.figure_for(self.cfg, n); self.cfg["figures"][n] = L[(L.index(cur) + d) % len(L)]

    # ---------- covers: the game's own sticker ----------
    def cover_mode(self, g):
        return gen.cover_mode(self.cfg, g, gen.photo_files(g))

    def cover_modes(self, g):
        f = gen.photo_files(g)
        return (["original"] if f["original"] or g == "EscapeUI" else []) + (["custom"] if f["custom"] else []) + ["logo", "none"]

    def ch_cov(self, g, d):
        L = self.cover_modes(g); cur = self.cover_mode(g)
        self.cfg.setdefault("covers", {})[g] = L[(L.index(cur) + d) % len(L)] if cur in L else L[0]

    def reset_covers(self, d):
        if d == 0:
            self.cfg["covers"] = {}

    def cover_thumb(self, g, mode):
        k = ("cov", g, mode)
        if k not in self.thumbs:
            t = Image.new("RGB", (48, 30), (0, 0, 0)); dt = ImageDraw.Draw(t)
            f = gen.photo_files(g).get(mode) if mode in ("original", "custom") else None
            try:
                if f:
                    ph = Image.open(f).convert("RGB"); s = max(48 / ph.width, 30 / ph.height)
                    ph = ph.resize((max(1, int(ph.width * s)), max(1, int(ph.height * s))), Image.LANCZOS)
                    t.paste(ph, ((48 - ph.width) // 2, (30 - ph.height) // 2))
                elif mode == "original" and g == "EscapeUI":
                    fig = art.lum_alpha(shapes.render(self.cfg["boot_logo"], 0.6, self.acc(), 60, 60, lw=1.0, R=22)); t.paste(fig.resize((30, 30)), (9, 0), fig.resize((30, 30)))
                elif mode == "logo":
                    dt.text((24, 15), "ABC", font=font("dot", 14, 900), fill=INK, anchor="mm")
            except Exception:
                pass
            dt.rectangle([0, 0, 47, 29], outline=(60, 60, 60))
            self.thumbs[k] = t
        return self.thumbs[k]

    def own_cover(self, g):
        """Your own picture: a file in SHARE; A shows where and looks again."""
        name = gen.safe_name(g)
        self.message("YOUR OWN COVER", "SHARE/SYSTEM/CONFIGS/ESCAPE-UI/COVERS/")
        time.sleep(2.2)
        self.message("FILE NAME", (name + ".PNG OR .JPG")[:40])
        time.sleep(2.2)
        os.makedirs(gen.COVERS_DIR, exist_ok=True)
        self.thumbs = {k: v for k, v in self.thumbs.items() if k[0] != "cov"}
        if gen.photo_files(g)["custom"]:
            self.cfg.setdefault("covers", {})[g] = "custom"

    def ch_pat(self, g, d):
        L = ["auto"] + art.PATTERN_LIST; cur = self.cfg["patterns"].get(g) or "auto"
        nxt = L[(L.index(cur) + d) % len(L)]
        if nxt == "auto":
            self.cfg["patterns"].pop(g, None)
        else:
            self.cfg["patterns"][g] = nxt

    def reset(self, d=0, figs=True, pats=True):
        if d != 0:   # only A resets, arrows do nothing on the danger row
            return
        if figs:
            self.cfg["figures"] = {}
        if pats:
            self.cfg["patterns"] = {}

    def open(self, page):
        self.page, self.cur, self.top = page, 0, 0

    # ---------- first run ----------
    def draw_setup(self):
        im = self.bg.copy(); d = ImageDraw.Draw(im, "RGBA")
        d.rectangle([212, 170, 812, 598], fill=(11, 11, 11, 246), outline=(255, 255, 255, 26))
        d.text((W / 2, 222), "ESCAPE/UI", font=font("dot", 44, 900), fill=INK, anchor="mm")
        d.text((W / 2, 262), "エスケープ · THEME SETUP", font=font("jp", 13), fill=DIM, anchor="mm")
        lines = [("A", "turn the theme on and draw its art"), ("X", "the same + custom collections straight on the home screen"),
                 ("B", "leave, change nothing")]
        y = 320
        for k, t in lines:
            d.rectangle([252, y - 12, 276, y + 12], outline=INK); d.text((264, y), k, font=font("px", 11), fill=INK, anchor="mm")
            d.text((292, y), t, font=font("grot", 16, 400), fill=(200, 200, 196), anchor="lm"); y += 46
        d.text((W / 2, 488), "drawing takes a few minutes the first time", font=font("px", 12), fill=DIM, anchor="mm")
        d.text((W / 2, 508), "settings: this app or UI settings > theme configuration", font=font("px", 12), fill=DIM, anchor="mm")
        art.stripes(d, W / 2 - 23, 548, 46, 9, self.acc())
        self.blit(im)

    def install(self, top):
        import shutil
        src = os.path.join(gen.THEME, "events", "escape-ui.sh")
        for ev in EVENTS:
            dd = os.path.join(gen.ES_DIR, "scripts", ev); os.makedirs(dd, exist_ok=True)
            shutil.copy(src, os.path.join(dd, "escape-ui.sh")); os.chmod(os.path.join(dd, "escape-ui.sh"), 0o755)
        boot_hook()
        pairs = [("ThemeSet", THEME_NAME)] + [(k, d) for k, (ch, d) in SUBSETS.items() if esctl.get(k) not in ch]
        if top:   # ES reads the old key and saves the new one; write both so it holds either way
            grp = [("UseCustomCollectionsSystem", "false"), ("UseCustomCollectionsSystemEx", "false")]
            pairs += grp
            esctl.set_many(grp)   # now, so the generator draws the collections, not one group card
        gen.save_cfg(self.cfg)
        self.draw_art("first time: a few minutes", [self.sub["subset.escape-accent"]])
        self.message("STARTING", "the theme comes up in a few seconds")
        esctl.apply_detached(pairs, "tool/app.py"); time.sleep(0.8)
        pygame.quit(); sys.exit(0)

    # ---------- drawing ----------
    def draw(self):
        if self.page == "setup":
            return self.draw_setup()
        im = self.bg.copy(); d = ImageDraw.Draw(im, "RGBA")
        rows = self.items(); vis = 15; rh = 36
        self.cur = max(0, min(self.cur, len(rows) - 1))
        if self.cur < self.top:
            self.top = self.cur
        if self.cur >= self.top + vis:
            self.top = self.cur - vis + 1
        shown = rows[self.top:self.top + vis]
        pw = 560; ph = 86 + len(shown) * rh + 40; px = (W - pw) // 2; py = (H - ph) // 2
        d.rectangle([px, py, px + pw, py + ph], fill=(11, 11, 11, 246), outline=(255, 255, 255, 26))
        icon = art.lum_alpha(shapes.render(self.cfg["boot_logo"], 0.6, self.acc(), 120, 120, lw=1.2, R=48)).resize((34, 34), Image.LANCZOS)
        im.paste(icon, (px + 22, py + 22), icon)
        title = {"main": "ESCAPE/UI", "figs": "FIGURES", "pats": "PATTERNS", "covs": "COVERS"}[self.page]
        d.text((px + 66, py + 39), title, font=font("dot", 30, 900), fill=INK, anchor="lm")
        d.text((px + pw - 22, py + 39), {"main": "THEME SETTINGS", "figs": "PER COLLECTION", "pats": "PER GAME", "covs": "PER GAME"}[self.page], font=font("px", 12), fill=DIM, anchor="rm")
        y = py + 76
        for i, (lb, (kind, val), _, sep) in enumerate(shown):
            n = self.top + i; on = n == self.cur; danger = kind == "danger"
            if danger:
                band = Image.new("RGBA", (pw - 2, rh - 4), (0, 0, 0, 0)); bd = ImageDraw.Draw(band)
                for k in range(-rh, pw, 18):
                    bd.polygon([(k, rh - 4), (k + 9, rh - 4), (k + 9 + rh - 4, 0), (k + rh - 4, 0)], fill=RED + ((255,) if on else (85,)))
                im.paste(band, (px + 1, y + 2), band); d = ImageDraw.Draw(im, "RGBA")
                fl = font("px", 12); t = lb.upper(); tw = fl.getlength(t)
                d.rectangle([W / 2 - tw / 2 - 12, y + 8, W / 2 + tw / 2 + 12, y + rh - 8], fill=VOID, outline=RED if on else None)
                d.text((W / 2, y + rh / 2), t, font=fl, fill=(255, 255, 255) if on else RED, anchor="mm")
                for tx in (px + 16, px + pw - 36):
                    art.warn_tri(d, tx, y + 9, 20, 18, (255, 255, 255) if on else RED, RED if on else VOID)
            else:
                if on:
                    d.rectangle([px + 1, y, px + pw - 1, y + rh - 1], fill=(255, 255, 255, 18))
                d.text((px + 24, y + rh / 2), "%02d" % (n + 1), font=font("px", 12), fill=self.acc() if on else (255, 255, 255, 48), anchor="lm")
                d.text((px + 56, y + rh / 2), lb if len(lb) < 34 else lb[:32] + "…", font=font("grot", 16, 400), fill=(255, 255, 255) if on else (169, 169, 165), anchor="lm")
                rx = px + pw - 24
                if kind == "open":
                    d.text((rx, y + rh / 2), ">>>", font=font("px", 12), fill=self.acc() if on else (60, 60, 60), anchor="rm")
                else:
                    vt = val.upper() if kind in ("txt", "chip") else (shapes.NAMES.get(val, val).upper() if kind == "fig" else COVER_NAMES.get(val, val).upper() if kind == "cov" else val.upper())
                    fv = font("px", 12)
                    if on:
                        d.text((rx, y + rh / 2), ">", font=fv, fill=self.acc(), anchor="rm"); rx -= 18
                    d.text((rx, y + rh / 2), vt, font=fv, fill=INK if on else DIM, anchor="rm"); rx -= fv.getlength(vt) + 10
                    if kind == "chip":
                        d.rectangle([rx - 14, y + rh / 2 - 7, rx, y + rh / 2 + 7], fill=self.acc(), outline=(255, 255, 255, 70)); rx -= 24
                    elif kind == "cov":
                        th = self.cover_thumb(lb, val)
                        im.paste(th, (int(rx - 48), int(y + rh / 2 - 15))); d = ImageDraw.Draw(im, "RGBA")
                        if on:
                            d.rectangle([rx - 48, y + rh / 2 - 15, rx - 1, y + rh / 2 + 14], outline=self.acc())
                        rx -= 58
                    elif kind in ("fig", "pat"):
                        th = self.thumb(kind, val if val != "auto" else art.PATTERN_LIST[0]) if not (kind == "pat" and val == "auto") else None
                        if kind == "pat" and val == "auto":
                            th = self.thumb("pat", gen.pattern_for({"patterns": {}}, lb))
                        im.paste(th, (int(rx - 48), int(y + rh / 2 - 15)), th); d = ImageDraw.Draw(im, "RGBA")
                        if on:
                            d.rectangle([rx - 48, y + rh / 2 - 15, rx - 1, y + rh / 2 + 14], outline=self.acc())
                        rx -= 58
                    if on:
                        d.text((rx, y + rh / 2), "<", font=fv, fill=self.acc(), anchor="rm")
            if sep and not danger:
                d.line([(px + 1, y + rh - 1), (px + pw - 1, y + rh - 1)], fill=(29, 29, 28, 255))
            y += rh
        d.text((px + 22, py + ph - 20), "ESCAPE/UI", font=font("px", 12), fill=DIM, anchor="lm")
        d.text((px + pw - 22, py + ph - 20), "◀▶ CHANGE · A " + ("YOUR OWN" if self.page == "covs" else "OPEN") + " · B " + ("SAVE & EXIT" if self.page == "main" else "BACK"), font=font("px", 12), fill=DIM, anchor="rm")
        self.blit(im)

    def blit(self, im):
        im = im.convert("RGB")
        self.scr.blit(pygame.image.frombuffer(im.tobytes(), im.size, "RGB"), (0, 0)); pygame.display.flip()

    def message(self, title, line, frac=None, hint=None):
        im = self.bg.copy(); d = ImageDraw.Draw(im, "RGBA")
        d.rectangle([232, 290, 792, 478], fill=(11, 11, 11, 246), outline=(255, 255, 255, 26))
        d.text((W / 2, 336), title, font=font("dot", 30, 900), fill=INK, anchor="mm")
        d.text((W / 2, 382), line.upper()[:40], font=font("px", 16), fill=DIM, anchor="mm")
        if frac is None:
            art.stripes(d, W / 2 - 23, 428, 46, 9, self.acc())
        else:   # a real bar: the generator counts its work up front
            x0, x1, y = 272, 752, 416
            d.rectangle([x0, y, x1, y + 12], outline=(255, 255, 255, 60))
            d.rectangle([x0 + 2, y + 2, x0 + 2 + int((x1 - x0 - 4) * frac), y + 10], fill=self.acc())
            d.text((W / 2, y + 36), "%d %%" % round(frac * 100), font=font("px", 16), fill=INK, anchor="mm")
        if hint:
            d.text((W / 2, 500), hint, font=font("px", 16), fill=DIM, anchor="mm")
        self.blit(im); pygame.event.pump()

    def draw_art(self, line, accents):
        """Redraw the art here with a progress bar (a still screen for minutes looked hung). A background
        run of the other colours is stopped first and started again afterwards."""
        self.message("DRAWING…", line, 0.0)
        gen.stop_background()
        held = gen.lock(wait=True)
        gen.HOOK = lambda s, f: (self.message("DRAWING…", s, f, "B — STOP"), self.check_cancel())
        try:
            gen.run(videos=True, accents=accents, jobs=2 if accents == "all" else 1)   # two cores for the whole palette
        except Cancelled:
            self.message("STOPPED", "what was drawn is kept")
            time.sleep(1.2)
        finally:
            gen.HOOK = None
            if held:
                held.close()
    # ---------- input ----------
    def press(self, k):
        if self.page == "setup":
            if k in ("A", "X"):
                self.install(k == "X")
            elif k == "B":
                pygame.quit(); sys.exit(0)
            return
        rows = self.items()
        if k != "A":
            self.armed = False
        if k == "UP":
            self.cur = (self.cur - 1) % len(rows)
        elif k == "DOWN":
            self.cur = (self.cur + 1) % len(rows)
        elif k in ("LEFT", "RIGHT"):
            if rows[self.cur][1][0] not in ("open", "danger"):
                rows[self.cur][2](-1 if k == "LEFT" else 1)
        elif k == "A":
            kind = rows[self.cur][1][0]
            if kind == "cov":
                self.own_cover(rows[self.cur][0])
            else:
                rows[self.cur][2](0 if kind in ("danger", "open") else 1)
        elif k == "B":
            if self.page != "main":
                self.cur = {"figs": 9, "pats": 10, "covs": 11}[self.page]; self.page = "main"; self.top = 0
            else:
                self.leave(True)
        elif k == "START":
            self.leave(True)
        elif k == "L1":
            self.cur = max(0, self.cur - 10)
        elif k == "R1":
            self.cur = min(len(rows) - 1, self.cur + 10)
        self.dirty = True

    def check_cancel(self):
        """While drawing: B (or START) stops it; the work already done stays."""
        for e in pygame.event.get():
            k = PAD_BUTTONS.get(e.button) if e.type == pygame.JOYBUTTONDOWN else KEYS.get(e.key) if e.type == pygame.KEYDOWN else None
            if k in ("B", "START"):
                raise Cancelled()

    def draw_all_label(self):
        left = len(art.PALETTE) - len(self.ready)
        if not left:
            return "Draw all colours · all %d ready" % len(art.PALETTE)
        mins = left * 6
        if self.armed:
            return "A again: ~%d min, keep charging" % mins
        return "Draw all colours · %d/%d · ~%d min" % (len(self.ready), len(art.PALETTE), mins)

    def draw_all(self):
        """Draw every colour of the palette now (about 6 minutes each on the Brick): only on a second
        A, after the row has said how long it takes. B stops it."""
        if len(self.ready) == len(art.PALETTE) and repr(self.cfg) == self.cfg0:
            return
        if not self.armed:
            self.armed = True; self.dirty = True
            return
        self.armed = False
        gen.save_cfg(self.cfg); self.cfg0 = repr(self.cfg)
        self.draw_art("every colour: leave it on the charger", "all")
        self.ready = gen.ready_accents(); self.drew = True; self.dirty = True

    def leave(self, save):
        art_changed = repr(self.cfg) != self.cfg0
        subs = [(k, v) for k, v in self.sub.items() if v != self.sub0.get(k)]
        acc = self.sub["subset.escape-accent"]
        if save and (art_changed or subs or self.drew):
            lv = self.sub["subset.escape-covers"]
            os.environ["ESCAPE_COVER_LEVEL"] = lv   # ES gets the new level only after the restart below
            new_level = lv != self.sub0.get("subset.escape-covers")
            if art_changed or acc not in self.ready or new_level:
                gen.save_cfg(self.cfg)
                # only the colour in use: the others are drawn by "Draw all colours" (they would
                # otherwise keep the CPU busy for half an hour while you play); covers only at the
                # level in use (a new level is drawn here, before ES shows it)
                self.draw_art("figures, stickers and covers" if art_changed else "covers at level " + lv if new_level and acc in self.ready
                              else "this colour for the first time", [acc])
            self.message("RESTARTING", "the menu comes back in a few seconds")
            esctl.apply_detached(subs, "tool/app.py")
            time.sleep(0.8)
        pygame.quit(); sys.exit(0)

    def run(self):
        clock = pygame.time.Clock(); rep_at = {}
        while True:
            for e in pygame.event.get():
                k = None
                if e.type == pygame.KEYDOWN:
                    k = KEYS.get(e.key)
                elif e.type == pygame.JOYBUTTONDOWN:
                    k = PAD_BUTTONS.get(e.button); print("button", e.button, k, flush=True)
                elif e.type == pygame.JOYHATMOTION:
                    x, y = e.value
                    k = "LEFT" if x < 0 else "RIGHT" if x > 0 else "UP" if y > 0 else "DOWN" if y < 0 else None
                    for n in ("LEFT", "RIGHT", "UP", "DOWN"):
                        if n != k:
                            rep_at.pop(n, None)
                    if k:
                        rep_at[k] = time.time() + 0.4
                elif e.type == pygame.KEYUP:
                    rep_at.pop(KEYS.get(e.key), None)
                elif e.type == pygame.QUIT:
                    self.leave(False)
                if e.type == pygame.KEYDOWN and KEYS.get(e.key) in ("LEFT", "RIGHT", "UP", "DOWN"):
                    rep_at[KEYS[e.key]] = time.time() + 0.4
                if k:
                    self.press(k)
            now = time.time()
            for n, t in list(rep_at.items()):   # held direction repeats
                if now >= t:
                    rep_at[n] = now + 0.08; self.press(n)
            if self.dirty:
                self.draw(); self.dirty = False
            clock.tick(30)


if __name__ == "__main__":
    App().run()
