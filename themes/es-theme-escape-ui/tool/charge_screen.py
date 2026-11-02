#!/usr/bin/env python3
"""escape/UI charging screen: the boot screen with a random figure turning, glitch bursts and the charge.

Started by charged.py while ES is paused. Any button or unplugging the charger ends it. The buttons are
grabbed (EVIOCGRAB), so the press that wakes the Brick never reaches ES.
"""
import fcntl
import io
import glob
import math
import os
import random
import select
import sys
import time
T_START = time.time()

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import numpy as np  # noqa: E402
import pygame  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art  # noqa: E402
import gen  # noqa: E402
import shapes  # noqa: E402
from art import DIM, INK, font  # noqa: E402

W, H = 1024, 768
CACHE = "/tmp/escape-charge"    # the loop, drawn ahead by --prepare while the 15 s run
EVIOCGRAB = 0x40044590
FPS = 24
FIG = 400
TEST_UNTIL = time.time() + float(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[1] == "--test" else 0   # --test SECONDS


def battery():
    try:
        return int(open(glob.glob("/sys/class/power_supply/*battery*/capacity")[0]).read().strip())
    except Exception:
        return None


def plugged():
    for p in glob.glob("/sys/class/power_supply/*usb*/online") + glob.glob("/sys/class/power_supply/*ac*/online"):
        try:
            if open(p).read().strip() == "1":
                return True
        except OSError:
            pass
    return False


def grab_inputs():
    fds = []
    for p in glob.glob("/dev/input/event*"):
        try:
            fd = os.open(p, os.O_RDONLY | os.O_NONBLOCK)
            try:
                fcntl.ioctl(fd, EVIOCGRAB, 1)
            except OSError:
                pass
            fds.append(fd)
        except OSError:
            pass
    return fds


def backdrop(accent, level):
    """Everything but the figure: the boot screen's words and the charge."""
    im = Image.new("RGB", (W, H), (0, 0, 0)); d = ImageDraw.Draw(im)
    f = font("dot", 36, 900)
    art.draw_text(d, (W / 2 - art.text_w(f, "ESCAPE/UI", 10) / 2, 560), "ESCAPE/UI", f, INK, "lm", 10)
    d.text((W / 2, 604), "エスケープ", font=font("jp", 14), fill=DIM, anchor="mm")
    lv = "CHARGING" + (" · %d%%" % level if level is not None else "")
    d.text((W / 2, 660), lv, font=font("px", 16), fill=INK, anchor="mm")
    x0, x1, y = W / 2 - 110, W / 2 + 110, 684
    d.rectangle([x0, y, x1, y + 4], outline=(60, 60, 58))
    if level is not None:
        d.rectangle([x0 + 1, y + 1, x0 + 1 + (x1 - x0 - 2) * level / 100, y + 3], fill=tuple(accent))
    return np.asarray(im).copy()


GX0, GY0, GX1, GY1 = W // 2 - 250, 110, W // 2 + 250, 700   # where it glitches: the figure and the words
ES_BOX = (430, 96, 990, 566)   # the figure on ES's home screen (theme.xml escape-loop: 0.41992 0.125, 0.546875 0.61198)
HEAD_AT = (44, 84)             # a game list's collection title (theme.xml escape-head: 0.043 0.11, 460x64)
COVER_BOX = (546, 96, 986, 360)   # a game's sticker sheet in the detailed list (escape-cover: 0.5332 0.125, 0.4297 0.34375)
SHOT = "/tmp/escape-es.ppm"    # ES's screen as it was paused (charged.py dumps it), for the way back


def es_shot():
    """ES's last frame (fbdump by charged.py after the pause), if it is fresh."""
    try:
        if time.time() - os.path.getmtime(SHOT) > 12 * 3600 + 60:
            return None
        im = np.asarray(Image.open(SHOT).convert("RGB"))
        return im if im.shape[:2] == (H, W) else None
    except Exception:
        return None


def _match(shot, img, at):
    """How far ES's screen is from one of our images where that image is solid (0 = the same)."""
    a = np.asarray(img)
    x, y = at; h, w = a.shape[:2]
    solid = a[:, :, 3] > 250
    if solid.sum() < 200:
        return 999.0
    d = np.abs(shot[y:y + h, x:x + w].astype(np.int16) - a[:, :, :3].astype(np.int16))
    return float(d[solid].mean())


def es_view(shot):
    """Which of our screens ES was paused on, from its pixels and the theme's own art:
    ("system", overlay RGBA of that card) | ("list", has_cover) | None (a menu, something else)."""
    try:
        acc = gen.current_accent()
        level = gen.es_setting("subset.escape-detail")
        level = level if level in ("0", "1", "2", "3", "4", "5") else "3"   # empty / "default" = the theme's 3
        root = os.path.join(gen.GEN, acc, "sys")
        names = [n for n in os.listdir(root) if os.path.isdir(os.path.join(root, n))]
        best, card = 999.0, None
        for n in names:   # the card's left panel (title, pills, blurb) is unique per collection
            p = os.path.join(root, n, "over%s.png" % level)
            if os.path.exists(p):
                o = Image.open(p).convert("RGBA")
                s = _match(shot, o.crop((0, 0, 420, H)), (0, 0))   # the panel only: nothing moves there
                if s < best:
                    best, card = s, o
        if best < 12:
            return "system", np.asarray(card)
        for n in names:
            p = os.path.join(root, n, "head.png")
            if os.path.exists(p) and _match(shot, Image.open(p).convert("RGBA"), HEAD_AT) < 12:
                x0, y0, x1, y1 = COVER_BOX
                return "list", bool(shot[y0:y1, x0:x1].max(axis=2).mean() > 6)
    except Exception as e:
        print("es_view:", e, file=sys.stderr)
    return None


def way_back(shot, rnd, n=15):
    """The frames from black back to ES's screen: only the figure glitches in (the videos' entrance).
    Home screen: the figure's own pixels (in its box, not under the card's label and stickers) are lifted
    off, glitched on their own and put back under the overlay. Game list: the game's sticker sheet,
    inside its own frame. Anywhere else: ES simply comes back. Ends on the exact frame ES was paused on."""
    view = es_view(shot)
    print("way back:", view[0] if view else "plain", file=sys.stderr)
    x0, y0, x1, y1 = ES_BOX
    if view and view[0] == "system":
        o = view[1][y0:y1, x0:x1].astype(np.float32)
        a = o[:, :, 3:4] / 255.0
        reg = shot[y0:y1, x0:x1]
        fig = (reg * ((a[:, :, 0] < 0.05) & (reg.max(axis=2) > 16))[:, :, None]).astype(np.uint8)
        top = o[:, :, :3] * a
        h, w = fig.shape[:2]
        for j in range(n):
            g = glitch(fig, j, n, rnd, (0, 0, w, h)).astype(np.float32)
            f = shot.copy(); f[y0:y1, x0:x1] = (top + g * (1 - a)).astype(np.uint8)
            yield f
    elif view and view[0] == "list" and view[1]:
        for j in range(n):
            yield glitch(shot, j, n, rnd, COVER_BOX)
    yield shot


def glitch(frame, k, n, rnd, box=None):
    """One frame of a burst: the glitch the figure videos open with (gen.glitch_frame / the mock-up's):
    dead frames, blocky pixels, torn bands, a red/cyan split, dimming — fading out as k reaches n.
    In numpy over the middle of the screen (the rest is black), so the figure keeps its pace."""
    GX0, GY0, GX1, GY1 = box or (globals()["GX0"], globals()["GY0"], globals()["GX1"], globals()["GY1"])
    s = 1.0 - k / n
    kk = int(k * 15 / max(1, n))
    out = frame.copy()
    if kk in (0, 3, 7) or (kk < 10 and rnd.random() < 0.15):
        out[GY0:GY1, GX0:GX1] = 0
        return out
    reg = frame[GY0:GY1, GX0:GX1]
    h, w = reg.shape[:2]
    if rnd.random() < 0.8 * s:   # blocky
        f = 2 + int(rnd.random() * 10 * s)
        reg = np.repeat(np.repeat(reg[::f, ::f], f, axis=0), f, axis=1)[:h, :w]
    reg = reg.copy()
    y = 0
    while y < h:   # torn: each band slides sideways
        bh = int(4 + rnd.random() * 46)
        if rnd.random() < 0.7:
            dx = int((rnd.random() * 2 - 1) * 90 * s)
            if dx:
                reg[y:y + bh] = np.roll(reg[y:y + bh], dx, axis=1)
        y += bh
    sh = int(3 + 10 * s)   # the channels drift apart
    reg[:, :, 0] = np.roll(reg[:, :, 0], sh, axis=1); reg[:, :, 2] = np.roll(reg[:, :, 2], -sh, axis=1)
    dim = min(1.0, 0.45 + 0.55 * (1 - s) + rnd.random() * 0.2)
    out[GY0:GY1, GX0:GX1] = (np.arange(256) * dim).astype(np.uint8)[reg]   # dimming by a lookup table
    return out


def _frame(job):
    fig, t, accent = job
    rgb = shapes.render(fig, t, accent, FIG, FIG, lw=1.6, ss=2)   # supersampled: smooth lines
    b = io.BytesIO(); rgb.save(b, "PNG", compress_level=1)
    return b.getvalue()


def library():
    """The loops drawn ahead by gen.py for the colour in use: gen/<colour>/charge/<figure>/."""
    root = os.path.join(gen.GEN, gen.current_accent(), "charge")
    try:
        return [f for f in os.listdir(root) if os.path.exists(os.path.join(root, f, "meta.json"))], root
    except OSError:
        return [], root


def prepare():
    """Draw the loop of a random figure on two cores into CACHE (charged.py starts this at plug-in).
    Nothing to do when gen.py has drawn the loops ahead (the usual case)."""
    import json
    import multiprocessing
    import shutil
    if library()[0]:
        return
    accent = art.ACCENT_RGB.get(gen.current_accent(), art.INK)
    fig = random.choice(shapes.LIST)
    span, sec = gen.LOOP.get(fig, (2 * math.pi, 12))
    n = max(2, min(FPS * 7, int(round(sec * FPS))))   # ≤ 7 s, so it is ready within the 15 s wait
    tmp = CACHE + ".tmp"
    shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    os.nice(10)
    with multiprocessing.Pool(2) as pool:
        for i, png in enumerate(pool.imap(_frame, [(fig, span * k / n, accent) for k in range(n)], chunksize=4)):
            open(os.path.join(tmp, "%03d.png" % i), "wb").write(png)
    json.dump({"fig": fig, "accent": list(accent), "n": n}, open(os.path.join(tmp, "meta.json"), "w"))
    shutil.rmtree(CACHE, ignore_errors=True); os.replace(tmp, CACHE)


def cached(accent):
    """A loop as PNG bytes: a random figure from the drawn-ahead library, else the one prepared at plug-in."""
    import json
    figs, root = library()
    if figs:
        fig = random.choice(figs)
        try:
            n = json.load(open(os.path.join(root, fig, "meta.json")))["n"]
            return fig, [open(os.path.join(root, fig, "%03d.png" % i), "rb").read() for i in range(n)]
        except Exception:
            pass
    try:
        meta = json.load(open(os.path.join(CACHE, "meta.json")))
        if tuple(meta["accent"]) != tuple(accent):
            return None, None
        return meta["fig"], [open(os.path.join(CACHE, "%03d.png" % i), "rb").read() for i in range(meta["n"])]
    except Exception:
        return None, None


def main():
    t0 = time.time()
    fds = grab_inputs()   # first: from here on no press reaches the paused ES
    pygame.init()
    scr = pygame.display.set_mode((W, H), pygame.FULLSCREEN)
    pygame.mouse.set_visible(False)
    print("screen up %.2fs after start (imports %.2fs)" % (time.time() - t0, t0 - T_START), file=sys.stderr)
    accent = art.ACCENT_RGB.get(gen.current_accent(), art.INK)
    fig, packed = cached(accent)
    if not fig:
        fig = random.choice(shapes.LIST)
    span, sec = gen.LOOP.get(fig, (2 * math.pi, 12))
    n = len(packed) if packed else max(2, int(round(sec * FPS)))
    back_frames = []   # the way back to ES's screen, drawn while the charging screen already runs

    def prepare_back():
        es = es_shot()
        if es is not None:
            back_frames.extend(way_back(es, random.Random()))
        print("way back ready %.2fs after start" % (time.time() - t0), file=sys.stderr)
    import threading
    back_job = threading.Thread(target=prepare_back, daemon=True); back_job.start()
    level = battery(); back = backdrop(accent, level); level_at = time.time()

    def figure(i):
        if packed:
            return np.asarray(Image.open(io.BytesIO(packed[i])).convert("RGB"))
        return np.asarray(shapes.render(fig, span * i / n, accent, FIG, FIG, lw=1.6, ss=1))   # not prepared: live

    frames = []   # the loop, drawn while the first frames already show
    rnd = random.Random()
    burst, next_burst = -1, time.time() + 1.0 + rnd.random() * 2
    k = 0
    clock = pygame.time.Clock()
    last = back

    def show(f):
        scr.blit(pygame.image.frombuffer(np.ascontiguousarray(f).tobytes(), (W, H), "RGB"), (0, 0))
        pygame.display.flip(); clock.tick(FPS)

    def leave():
        """A button or unplugging: the screen breaks up in a short glitch and ends on black; then ES's
        home screen comes back with its figure glitching in (the videos' entrance), settling on the
        exact frame ES was paused on, so ES carries on from there."""
        for j in range(12):   # the burst played backwards: it builds up and ends on black
            show(glitch(last, max(0, 6 - j), 9, rnd) if j < 9 else np.zeros_like(last))   # medium to full, then black
        back_job.join(5)
        if back_frames and not back_job.is_alive():
            for f in back_frames:   # forward burst on ES's figure only: dead frames, blocks, tears, fading out
                show(f)
        raise SystemExit

    while True:
        for fd in fds:   # any button ends it
            try:
                if os.read(fd, 4096):
                    leave()
            except BlockingIOError:
                pass
            except OSError:
                pass
        if TEST_UNTIL:
            if time.time() > TEST_UNTIL:
                leave()   # the test ends the way a button does
        elif not plugged():
            leave()
        if time.time() - level_at > 30:
            level = battery(); back = backdrop(accent, level); level_at = time.time()
        i = k % n
        if packed:
            cur = figure(i)   # PNG-packed loop: decode as we go (a few ms), keeps memory small
        else:
            if i >= len(frames):
                frames.append(figure(i))
            cur = frames[i]
        frame = back.copy()
        fx, fy = W // 2 - FIG // 2, 130
        frame[fy:fy + FIG, fx:fx + FIG] = np.maximum(frame[fy:fy + FIG, fx:fx + FIG], cur)
        if burst < 0 and time.time() >= next_burst:
            burst, blen = 0, 6 + rnd.randrange(8)
        if burst >= 0:
            frame = glitch(frame, burst, blen, rnd); burst += 1
            if burst >= blen:
                burst, next_burst = -1, time.time() + 2.0 + rnd.random() * 4
        last = frame
        scr.blit(pygame.image.frombuffer(np.ascontiguousarray(frame).tobytes(), (W, H), "RGB"), (0, 0))
        pygame.display.flip(); pygame.event.pump()
        k += 1
        clock.tick(FPS)


if __name__ == "__main__":
    if "--prepare" in sys.argv:
        prepare(); sys.exit(0)
    try:
        main()
    except SystemExit:
        pass
    finally:
        pygame.quit()
