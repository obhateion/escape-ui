"""Drawing kit shared by the generator and the settings app: fonts, colours, stickers, patterns."""
import math
import os
import random
import zlib

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import shapes

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(os.path.dirname(HERE), "fonts")
JP_FONTS = [os.environ.get("ESCAPE_JPFONT", ""), "/usr/share/fonts/truetype/noto/NotoSansJP-VF.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf"]

VOID = (0, 0, 0)
INK = (242, 242, 238)
DIM = (110, 110, 107)
LINE = (233, 233, 230)

# the accent palette: every colour is drawn ahead of time, so picking one is instant (slug, name, rgb)
PALETTE = [("white", "White", (242, 242, 238)), ("red", "Red", (255, 42, 31)), ("orange", "Orange", (255, 106, 19)),
           ("yellow", "Yellow", (255, 214, 10)), ("acid", "Acid", (216, 255, 60)), ("green", "Green", (40, 230, 120)),
           ("ice", "Ice", (143, 220, 255)), ("blue", "Blue", (52, 120, 255)), ("violet", "Violet", (185, 140, 255)),
           ("pink", "Pink", (255, 70, 170))]
ACCENT_RGB = {s: c for s, _, c in PALETTE}
ACCENTS = [(n, c) for _, n, c in PALETTE]

KATA = {"ALL": "エスケープ", "GAMES": "ゲーム", "SOUND": "サウンド", "APPS": "アプリ"}
KANJI = {"ALL": "脱出", "GAMES": "遊", "SOUND": "音", "APPS": "道具"}
MORE_KATA = ["プレイ", "セーブ", "スタート", "ロード", "ハイスコア", "データ", "コンティニュー", "ステージ", "ボーナス", "サウンド", "ゲーム"]
MORE_KANJI = ["遊", "音", "夢", "光", "道", "星", "波", "脱出", "注意", "危険", "再生"]
STAMPS = [("EXPLICIT", "ESCAPE", "CONTENT"), ("HANDLE", "WITH", "CARE"), ("HIGH", "VOLTAGE", "SOUND"), ("NO", "SIGNAL", "FOUND"),
          ("SYSTEM", "OVER", "RIDE"), ("PLAY", "AT OWN", "RISK"), ("LOW", "BATT", "MODE"), ("DO NOT", "PRESS", "START"),
          ("FREE", "TO", "LEAVE"), ("LOUD", "AND", "CLEAR"), ("ZERO", "LAG", "ZONE"), ("NIGHT", "SHIFT", "ONLY"), ("NOT A", "TOY", "ACTUALLY")]
PILLS = ["online", "hi-fi", "stereo", "local", "beta", "rom ok", "8-bit", "v2.0", "no save", "loop", "live", "x-001", "dual",
         "rgb", "mono", "4:3", "no.01", "tilt", "lo-fi", "jp", "save ok", "turbo", "cpu 1", "zero", "new"]
CHEVS = [">>>", "<<<", "///", "+++", ">>|", "<>", "::", "=>>", "///>"]


def rng(seed):
    return random.Random(zlib.crc32(seed.encode("utf-8")))


_fcache = {}


def font(kind, size, wght=None):
    """kind: dot (Doto), px (Silkscreen), grot (Archivo), mono (Martian Mono), jp."""
    key = (kind, size, wght)
    if key in _fcache:
        return _fcache[key]
    files = {"dot": "Doto[ROND,wght].ttf", "px": "Silkscreen-Regular.ttf", "pxb": "Silkscreen-Bold.ttf",
             "grot": "Archivo[wdth,wght].ttf", "mono": "MartianMono[wdth,wght].ttf"}
    f = None
    if kind == "jp":
        for p in JP_FONTS:
            if os.path.exists(p):
                f = ImageFont.truetype(p, size); break
    else:
        f = ImageFont.truetype(os.path.join(FONTS, files[kind]), size)
    if wght is not None:
        try:
            axes = f.get_variation_axes()
            vals = []
            for ax in axes:
                n = ax.get("name", b"")
                n = n.decode() if isinstance(n, bytes) else str(n)
                if "eight" in n or n.lower().startswith("wght"):
                    vals.append(max(ax["minimum"], min(ax["maximum"], wght)))
                else:
                    vals.append(ax.get("default", ax["minimum"]))
            f.set_variation_by_axes(vals)
        except Exception:
            pass
    _fcache[key] = f
    return f


# ---------- names in any script ----------
# Doto, Silkscreen and Archivo are Latin only. A collection or game name in Cyrillic, Japanese, Korean...
# draws its missing letters from a system font (the Brick has Noto Sans JP: Latin, Cyrillic, Greek, kana,
# kanji; Nanum: Hangul; Droid fallback: the rest of CJK; DejaVu: symbols). For the dot-matrix font the
# borrowed letters are redrawn as dots, so a name keeps the card's look. What no font has (emoji) is left out.
FALLBACK_FONTS = [os.environ.get("ESCAPE_JPFONT", ""), "/usr/share/fonts/truetype/noto/NotoSansJP-VF.ttf",
                  "/usr/share/fonts/truetype/nanum/NanumGothic.ttf", "/usr/share/fonts/truetype/droid/DroidSansFallback.ttf",
                  "/usr/share/fonts/dejavu/DejaVuSans.ttf", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts/malgun.ttf")]
_has = {}
_fb_fonts = {}


def _glyph_print(f, ch):
    """What f draws for ch, as bytes: a letter drawn exactly like the 'missing' box is missing."""
    im = Image.new("L", (f.size * 2 + 8, f.size * 2 + 8)); ImageDraw.Draw(im).text((4, 4), ch, font=f, fill=255)
    return im.tobytes(), f.getbbox(ch)


def _missing_mask(f):
    return _glyph_print(f, "\U0010FFFD")   # a plane-16 private code point: none of these fonts draws it


def has_glyph(f, ch):
    """Does font f really draw ch (not its 'missing' box)?"""
    if ch.isspace():
        return True
    key = (getattr(f, "path", id(f)), f.size, ch)
    if key not in _has:
        miss = _has.get((getattr(f, "path", id(f)), f.size, None))
        if miss is None:
            miss = _has[(getattr(f, "path", id(f)), f.size, None)] = _missing_mask(f)
        _has[key] = _glyph_print(f, ch) != miss
    return _has[key]


def fallback_font(ch, size):
    """The first system font that has ch, at `size` (None: nobody has it)."""
    for p in FALLBACK_FONTS:
        if not p or not os.path.exists(p):
            continue
        k = (p, size)
        if k not in _fb_fonts:
            _fb_fonts[k] = ImageFont.truetype(p, size)
            try:   # variable fallback fonts (Noto Sans JP): bold, so dotted letters keep their strokes
                _fb_fonts[(p, size, "bold")] = ImageFont.truetype(p, size)
                _fb_fonts[(p, size, "bold")].set_variation_by_axes([700])
            except Exception:
                _fb_fonts[(p, size, "bold")] = _fb_fonts[k]
        if has_glyph(_fb_fonts[k], ch):
            return _fb_fonts[k]
    return None


def drawable(f, s):
    """s without what no font can draw (emoji...), trimmed — what a name really shows."""
    return "".join(ch for ch in s if has_glyph(f, ch) or fallback_font(ch, f.size)).strip()


def covered(f, s):
    return all(has_glyph(f, ch) for ch in s)


def _runs(f, s):
    """Split s into (font, text, borrowed) runs; letters nobody has are dropped."""
    out = []
    for ch in s:
        if has_glyph(f, ch):
            g, b = f, False
        else:
            g = fallback_font(ch, max(6, int(round(f.size * (0.86 if _is_dot(f) else 0.92)))))
            b = True
            if g is None:
                continue
            if _is_dot(f):   # dotted letters are drawn (and measured) bold
                g = _fb_fonts.get((g.path, g.size, "bold"), g)
        if out and out[-1][0] is g:
            out[-1][1] += ch
        else:
            out.append([g, ch, b])
    return out


def _is_dot(f):
    return "Doto" in str(getattr(f, "path", ""))


def _wide(s):
    return any(ord(c) >= 0x2E80 for c in s)   # CJK, kana, Hangul: they need a finer dot grid


def _dotted(f, s, size, fill):
    """Borrowed letters as a dot matrix like Doto's: rendered bold, sampled on a grid, one square dot per cell."""
    cells = 13 if _wide(s) else 10
    asc, desc = f.getmetrics()
    w = int(math.ceil(f.getlength(s))) + 2; h = asc + desc
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).text((1, asc), s, font=f, fill=255, anchor="ls")
    p = max(2.0, size * 0.72 / cells)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    gw, gh = int(w / p), int(h / p)
    if gw < 1 or gh < 1:
        return im
    small = m.resize((gw, gh), Image.BOX)
    px = small.load(); r = p * 0.37
    for y in range(gh):
        for x in range(gw):
            if px[x, y] > 80:
                cx, cy = (x + 0.5) * p, (y + 0.5) * p
                d.rounded_rectangle([cx - r, cy - r, cx + r, cy + r], radius=r * 0.35, fill=fill)
    return im


def text_any(d, xy, s, f, fill, anchor="la", im=None):
    """d.text for names: the same when f has every letter, else the missing ones from a system font
    (dotted for Doto). Anchors as Pillow's: l/m/r + a/t/m/s/d. Returns the width drawn."""
    if covered(f, s):
        d.text(xy, s, font=f, fill=fill, anchor=anchor)
        return f.getlength(s)
    runs = _runs(f, s)
    width = sum(g.getlength(t) for g, t, _ in runs)
    asc, desc = f.getmetrics()
    x, y = xy
    x -= {"l": 0, "m": width / 2, "r": width}[anchor[0]]
    v = anchor[1] if len(anchor) > 1 else "a"
    base = y + {"a": asc, "t": asc, "m": (asc - desc) / 2, "s": 0, "d": -desc}[v]
    for g, t, borrowed in runs:
        if borrowed and _is_dot(f):
            dots = _dotted(g, t, f.size, fill if len(fill) == 4 else tuple(fill) + (255,))
            ga = g.getmetrics()[0]
            target = im if im is not None else getattr(d, "_image", None)
            if target is not None and target.mode == "RGBA":
                target.alpha_composite(dots, (int(x), int(base - ga)))
            elif target is not None:
                target.paste(dots, (int(x), int(base - ga)), dots)
        else:
            d.text((x, base), t, font=g, fill=fill, anchor="ls")
        x += g.getlength(t)
    return width


def length_any(f, s):
    if covered(f, s):
        return f.getlength(s)
    return sum(g.getlength(t) for g, t, _ in _runs(f, s))


def text_size(f, s):
    b = f.getbbox(s)
    return b[2] - b[0], b[3] - b[1], b


def draw_text(d, xy, s, f, fill, anchor="la", spacing=0):
    if not spacing:
        d.text(xy, s, font=f, fill=fill, anchor=anchor); return
    x, y = xy   # letter spacing by hand (Pillow has none)
    for ch in s:
        d.text((x, y), ch, font=f, fill=fill, anchor=anchor)
        x += f.getlength(ch) + spacing


def text_w(f, s, spacing=0):
    return sum(f.getlength(ch) + spacing for ch in s) - spacing if spacing else f.getlength(s)


# ---------- small sticker parts (on RGBA layers) ----------

def pill(d, x, y, s, filled=False, col=INK):
    f = font("px", 9)
    w = text_w(f, s.upper()) + 16
    d.rounded_rectangle([x, y, x + w, y + 18], radius=9, outline=col, width=1, fill=col if filled else None)
    d.text((x + 8, y + 9), s.upper(), font=f, fill=VOID if filled else col, anchor="lm")
    return w


def sparkle(d, cx, cy, r, col=INK):
    pts = []
    for k in range(8):
        an = k * math.pi / 4 - math.pi / 2
        rr = r if k % 2 == 0 else r * 0.22
        pts.append((cx + math.cos(an) * rr, cy + math.sin(an) * rr))
    d.polygon(pts, fill=col)


def warn_tri(d, x, y, w=22, h=20, col=INK, mark=VOID):
    d.polygon([(x + w / 2, y), (x + w, y + h), (x, y + h)], fill=col)
    d.text((x + w / 2, y + h * 0.66), "!", font=font("pxb", 9), fill=mark, anchor="mm")


def stripes(d, x, y, w=46, h=9, col=INK):
    for k in range(-h, w, 6):
        d.polygon([(x + k, y + h), (x + k + 3, y + h), (x + k + 3 + h, y), (x + k + h, y)], fill=col)


def stripes_layer(w, h, col):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); stripes(ImageDraw.Draw(im), 0, 0, w, h, col)
    return im


def bars(d, x, y, w=64, h=14, col=INK, seed=0):
    r = random.Random(seed); xx = x
    while xx < x + w:
        bw = r.choice([1, 1, 2, 3]); d.rectangle([xx, y, xx + bw - 1, y + h], fill=col); xx += bw + r.choice([1, 2, 3])


def vtext(d, x, y, s, f, fill, gap=4):
    """Vertical text (writing-mode: vertical-rl) one glyph under the other."""
    for ch in s:
        d.text((x, y), ch, font=f, fill=fill, anchor="mt"); y += f.size + gap


def stamp(kind, words, accent):
    """The big level-5 stamps: advisory box, round seal or hanging tag. Returns an RGBA image."""
    a, b, c = words
    if kind == 0:
        fb, fs = font("dot", 26, 900), font("px", 10)
        w = int(max(text_w(fb, a), text_w(fb, c), text_w(fs, b)) + 28); h = 104
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rectangle([0, 0, w - 1, h - 1], fill=VOID, outline=INK, width=2)
        d.text((w / 2, 22), a, font=fb, fill=INK, anchor="mm")
        d.rectangle([2, 38, w - 3, 62], fill=INK); d.text((w / 2, 50), b, font=fs, fill=VOID, anchor="mm")
        d.text((w / 2, 82), c, font=fb, fill=INK, anchor="mm")
    elif kind == 1:
        w = h = 112; im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.ellipse([0, 0, w - 1, h - 1], fill=VOID, outline=INK, width=2); d.ellipse([7, 7, w - 8, h - 8], outline=INK, width=1)
        d.text((w / 2, 30), a, font=font("px", 8), fill=INK, anchor="mm")
        d.text((w / 2, 56), b, font=font("dot", 22, 900), fill=accent, anchor="mm")
        d.text((w / 2, 82), c, font=font("px", 8), fill=INK, anchor="mm")
    else:
        fb = font("dot", 24, 900); w = int(text_w(fb, b) + 54); h = 58
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.polygon([(0, h / 2), (18, 0), (w - 1, 0), (w - 1, h - 1), (18, h - 1)], fill=INK)
        d.ellipse([10, h / 2 - 5, 20, h / 2 + 5], fill=VOID)
        d.text((30, 20), b, font=fb, fill=VOID, anchor="lm")
        d.text((30, 44), a + " " + c, font=font("px", 8), fill=VOID, anchor="lm")
    return im


def hazard_band(w, h, col=INK):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for k in range(-h, w, 18):
        d.polygon([(k, h), (k + 9, h), (k + 9 + h, 0), (k + h, 0)], fill=col)
    return im


def badge(num, col=INK):
    im = Image.new("RGBA", (74, 74), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([0, 0, 73, 73], fill=VOID, outline=col, width=1); d.ellipse([5, 5, 68, 68], outline=col, width=1)
    d.text((37, 24), "NO.", font=font("px", 8), fill=col, anchor="mm")
    d.text((37, 46), num, font=font("dot", 26, 900), fill=col, anchor="mm")
    return im


def disc(label, accent):
    im = Image.new("RGBA", (96, 96), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([0, 0, 95, 95], fill=VOID, outline=INK, width=1)
    for r in (40, 34, 28): d.ellipse([48 - r, 48 - r, 48 + r, 48 + r], outline=(80, 80, 78), width=1)
    d.ellipse([38, 38, 58, 58], outline=accent, width=2)
    for k, (yy, t) in enumerate(((72, label[0]), (81, label[1]))):
        f = font("px", 7)
        while length_any(f, t) > 56 and len(t) > 2:
            t = t[:-2].rstrip() + "…"
        text_any(d, (48, yy), t, f, INK, "mm", im)
    return im


def jp_label(kanji, word):
    fj = font("jp", 26); w = int(max(text_w(fj, kanji), text_w(font("px", 8), word.upper())) + 22); h = 70
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w - 1, h - 1], fill=VOID, outline=INK, width=2)
    d.text((w / 2, 26), kanji, font=fj, fill=INK, anchor="mm")
    d.rectangle([2, h - 22, w - 3, h - 3], fill=INK); d.text((w / 2, h - 12), word.upper(), font=font("px", 8), fill=VOID, anchor="mm")
    return im


def checker_strip(w=120, h=16, col=INK):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im); s = h // 2
    for i in range(0, w, s):
        for j in range(2):
            if (i // s + j) % 2 == 0: d.rectangle([i, j * s, i + s - 1, j * s + s - 1], fill=col)
    d.rectangle([0, 0, w - 1, h - 1], outline=col)
    return im


def arrow_stk(word, arrow):
    f = font("px", 10); w = int(text_w(f, word.upper()) + 44); h = 30
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w - 1, h - 1], fill=VOID, outline=INK); d.rectangle([w - 30, 0, w - 1, h - 1], fill=INK)
    d.text((8, h / 2), word.upper(), font=f, fill=INK, anchor="lm"); d.text((w - 15, h / 2), arrow, font=font("jp", 18), fill=VOID, anchor="mm")
    return im


def bar_stk(num):
    im = Image.new("RGBA", (130, 34), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 129, 33], fill=VOID, outline=INK); bars(d, 6, 4, 118, 16, INK, num)
    d.text((65, 27), num, font=font("px", 8), fill=INK, anchor="mm")
    return im


def mini_figure(shape, t, accent, size=120):
    fig = shapes.render(shape, t, accent, size * 2, size * 2, lw=1.6, R=size * 0.8, ss=1).resize((size, size), Image.LANCZOS)
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([0, 0, size - 1, size - 1], fill=VOID + (255,))
    mask = Image.new("L", (size, size), 0); ImageDraw.Draw(mask).ellipse([2, 2, size - 3, size - 3], fill=255)
    im.paste(fig, (0, 0), mask)
    ImageDraw.Draw(im).ellipse([0, 0, size - 1, size - 1], outline=INK, width=1)
    return im


def lum_alpha(rgb):
    """A black-background RGB render turned into RGBA where black is transparent."""
    r, g, b = rgb.split()
    a = Image.eval(Image.merge("RGB", (r, g, b)).convert("L"), lambda v: min(255, v * 2))
    from PIL import ImageChops
    a = ImageChops.lighter(a, ImageChops.lighter(r, ImageChops.lighter(g, b)))
    out = rgb.convert("RGBA"); out.putalpha(a)
    return out


def vinyl(content, round_=False, pad=6, rot=0.0):
    """A sticker die-cut from black film: the content on a black backing with a margin, a soft shadow,
    stuck on by hand at a small angle. Returns RGBA."""
    w, h = content.size; W, H = w + pad * 2, h + pad * 2
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(base)
    if round_:
        d.ellipse([0, 0, W - 1, H - 1], fill=(8, 8, 8, 255))
    else:
        d.rounded_rectangle([0, 0, W - 1, H - 1], radius=7, fill=(8, 8, 8, 255))
    base.alpha_composite(content, (pad, pad))
    base = base.rotate(rot, resample=Image.BICUBIC, expand=True)
    sh = Image.new("RGBA", (base.width + 24, base.height + 24), (0, 0, 0, 0))
    a = base.split()[3].point(lambda v: int(v * 0.65))
    blk = Image.new("RGBA", base.size, (0, 0, 0, 255)); blk.putalpha(a)
    sh.alpha_composite(blk, (14, 16)); sh = sh.filter(ImageFilter.GaussianBlur(5))
    sh.alpha_composite(base, (12, 12))
    return sh


# ---------- surface patterns for the game covers (the mock-up's 16 tiles) ----------

def grey(v, a=255):
    v = max(0, min(255, int(v))); return (v, v, v, a)


def _tile(W, H, s, bg, draw, rot=0.0):
    t = Image.new("RGB", (s, s), grey(bg)[:3]); draw(ImageDraw.Draw(t, "RGBA"), s)
    big = Image.new("RGB", (W * 2, H * 2))
    for y in range(0, H * 2, s):
        for x in range(0, W * 2, s):
            big.paste(t, (x, y))
    if rot:
        big = big.rotate(math.degrees(rot), resample=Image.BICUBIC)
    return big.crop((W // 2, H // 2, W // 2 + W, H // 2 + H))


def pat_perforated(W, H):
    im = Image.new("RGB", (W, H), grey(66)[:3]); d = ImageDraw.Draw(im, "RGBA"); s = 22; row = 0; y = s / 2
    while y < H:
        x = s if row % 2 else s / 2
        while x < W:
            d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=grey(10)); d.chord([x - 6, y - 5, x + 6, y + 7], 18, 162, fill=grey(110, 150)); x += s
        y += s; row += 1
    return im


def pat_carbon(W, H):
    im = Image.new("RGB", (W, H), grey(20)[:3]); d = ImageDraw.Draw(im); s = 16
    for y in range(0, H, s):
        for x in range(0, W, s):
            horiz = ((x + y) // s) % 2
            for i in range(s - 2):
                v = 28 + 42 * (1 - abs((i / (s - 3)) * 2 - 1))
                if horiz: d.line([(x + 1 + i, y + 1), (x + 1 + i, y + s - 2)], fill=grey(v)[:3])
                else: d.line([(x + 1, y + 1 + i), (x + s - 2, y + 1 + i)], fill=grey(v)[:3])
    return im


PATTERNS = {
    "perforated": pat_perforated, "carbon": pat_carbon,
    "stripes": lambda W, H: _tile(W, H, 28, 46, lambda k, s: k.rectangle([0, 0, s / 2, s], fill=grey(66)), math.pi / 4),
    "hazard": lambda W, H: _tile(W, H, 64, 36, lambda k, s: k.rectangle([0, 0, s / 2, s], fill=grey(78)), -math.pi / 4),
    "pinstripe": lambda W, H: _tile(W, H, 12, 40, lambda k, s: k.rectangle([0, 0, 1, s], fill=grey(72))),
    "crosses": lambda W, H: _tile(W, H, 36, 42, lambda k, s: (k.rectangle([s / 2 - 1.5, s / 2 - 9, s / 2 + 1.5, s / 2 + 9], fill=grey(96)), k.rectangle([s / 2 - 9, s / 2 - 1.5, s / 2 + 9, s / 2 + 1.5], fill=grey(96)))),
    "xmarks": lambda W, H: _tile(W, H, 56, 50, lambda k, s: [k.line(seg, fill=grey(90), width=3) for x, y in ((s / 4, s / 4), (s * 3 / 4, s * 3 / 4)) for seg in ([(x - 7, y - 7), (x + 7, y + 7)], [(x + 7, y - 7), (x - 7, y + 7)])]),
    "grid": lambda W, H: _tile(W, H, 40, 30, lambda k, s: (k.rectangle([0, 0, s, 1], fill=grey(56)), k.rectangle([0, 0, 1, s], fill=grey(56)), k.rectangle([0, 0, 2, 2], fill=grey(120)))),
    "checker": lambda W, H: _tile(W, H, 48, 38, lambda k, s: (k.rectangle([0, 0, s / 2 - 1, s / 2 - 1], fill=grey(60)), k.rectangle([s / 2, s / 2, s - 1, s - 1], fill=grey(60)))),
    "dots": lambda W, H: _tile(W, H, 20, 34, lambda k, s: [k.ellipse([x - 2.6, y - 2.6, x + 2.6, y + 2.6], fill=grey(86)) for x, y in ((s / 4, s / 4), (s * 3 / 4, s * 3 / 4))]),
    "chevrons": lambda W, H: _tile(W, H, 40, 44, lambda k, s: [k.line([(-2, y + 10), (s / 2, y - 6), (s + 2, y + 10)], fill=grey(78), width=5) for y in (s * 0.25, s * 0.75)]),
    "zigzag": lambda W, H: _tile(W, H, 32, 52, lambda k, s: k.line([(0, s * 0.7), (s / 2, s * 0.3), (s, s * 0.7)], fill=grey(30), width=3)),
    "diamonds": lambda W, H: _tile(W, H, 36, 40, lambda k, s: (k.polygon([(s / 2, 4), (s - 4, s / 2), (s / 2, s - 4), (4, s / 2)], outline=grey(80)), k.rectangle([s / 2 - 2, s / 2 - 2, s / 2 + 2, s / 2 + 2], fill=grey(80)))),
    "waves": lambda W, H: _tile(W, H, 48, 40, lambda k, s: [k.line([(x, y0 + math.sin(x / s * math.pi * 2) * 5) for x in range(0, s + 1, 2)], fill=grey(76), width=3) for y0 in (s * 0.25, s * 0.75)]),
    "rings": lambda W, H: _tile(W, H, 44, 34, lambda k, s: [k.ellipse([s / 2 - R, s / 2 - R, s / 2 + R, s / 2 + R], outline=grey(74), width=2) for R in (8, 15)]),
    "triangles": lambda W, H: _tile(W, H, 40, 36, lambda k, s: (k.polygon([(s / 4, s / 2 - 8), (s / 4 + 9, s / 2 + 7), (s / 4 - 9, s / 2 + 7)], fill=grey(64)), k.polygon([(s * 3 / 4, s / 2 + 8), (s * 3 / 4 + 9, s / 2 - 7), (s * 3 / 4 - 9, s / 2 - 7)], outline=grey(64)))),
}
PATTERN_LIST = list(PATTERNS)


def pattern(name, W, H):
    return PATTERNS.get(name, pat_carbon)(W, H)


# ---------- the game's own picture on its sheet ----------

def polaroid(photo, caption):
    """The game's picture as a Polaroid: white paper, the photo cropped to fit, a caption in the bottom
    margin and a strip of tape (the mock-up's polaroid(), line for line)."""
    pw = 116; ar = photo.height / photo.width; ph = max(88, min(140, round(pw * ar))); fw, fh = pw + 16, ph + 8 + 30
    top = 8
    im = Image.new("RGBA", (fw, fh + 8), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([0, top, fw - 1, top + fh - 1], fill=(242, 242, 238, 255))
    s = max(pw / photo.width, ph / photo.height); sw, sh = pw / s, ph / s
    x0, y0 = max(0.0, (photo.width - sw) / 2), max(0.0, (photo.height - sh) / 2)
    sw, sh = min(sw, photo.width - x0), min(sh, photo.height - y0)   # float rounding
    crop = photo.convert("RGB").resize((pw, ph), Image.LANCZOS, box=(x0, y0, x0 + sw, y0 + sh))
    im.paste(crop, (8, top + 8))
    d.rectangle([8, top + 8, 8 + pw - 1, top + 8 + ph - 1], outline=(0, 0, 0, 40))
    f = font("grot", 11, 500); cap = caption
    while length_any(f, cap) > pw and len(cap) > 3:
        cap = cap[:-2] + "…"
    text_any(d, (fw / 2, top + 8 + ph + 15), cap, f, (44, 44, 42), "mm", im)
    tape = Image.new("RGBA", (48, 14), (235, 235, 225, 140)).rotate(math.degrees(0.12), resample=Image.BICUBIC, expand=True)
    im.alpha_composite(tape, (max(0, int(fw / 2 - tape.width / 2)), max(0, int(top + 1 - tape.height / 2))))
    return im


def logo_sticker(name, accent):
    """No picture: the name as a die-cut logo with an accent bar under it."""
    size = 30; n = name.upper().strip() or "?"; f = font("dot", size, 900)
    while length_any(f, n) > 210 and size > 14:
        size -= 2; f = font("dot", size, 900)
    while length_any(f, n) > 210 and len(n) > 2:
        n = n[:-2].rstrip() + "…"
    w = max(int(math.ceil(length_any(f, n))) + 20, 128); h = size + 30   # room for the bar and NO COVER
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    text_any(d, (10, 8), n, f, INK, "lt", im)
    d.rectangle([10, h - 14, min(w - 11, 10 + 46), h - 11], fill=tuple(accent))
    d.text((w - 10, h - 12), "NO COVER", font=font("px", 7), fill=DIM, anchor="rm")
    return im


def paper(content, rot):
    """A sticker without the black film: just the shadow under it."""
    base = content.rotate(rot, resample=Image.BICUBIC, expand=True)
    sh = Image.new("RGBA", (base.width + 24, base.height + 24), (0, 0, 0, 0))
    a = base.split()[3].point(lambda v: int(v * 0.6))
    blk = Image.new("RGBA", base.size, (0, 0, 0, 255)); blk.putalpha(a)
    sh.alpha_composite(blk, (14, 16)); sh = sh.filter(ImageFilter.GaussianBlur(5))
    sh.alpha_composite(base, (12, 12))
    return sh
