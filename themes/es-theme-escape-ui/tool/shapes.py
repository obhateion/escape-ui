"""The 18 background figures of escape/UI, ported line for line from the mock-up's canvas code.

Every figure draws thin white lines with one accent detail around (cx, cy) with radius R at
phase t. Drawing goes through a tiny canvas-like wrapper over PIL so the port stays readable.
"""
import math

from PIL import Image, ImageDraw

TAU = math.pi * 2
INK = (233, 233, 230)

NAMES = {
    "globe": "wire globe", "checker": "checker sphere", "waves": "wave field", "warp": "warp grid",
    "orbits": "orbit rings", "target": "target", "spiral": "spiral", "burst": "starburst",
    "torus": "torus", "cube": "wire cube", "tunnel": "tunnel", "dots": "dot sphere", "helix": "helix",
    "lissajous": "lissajous", "rose": "rose", "radar": "radar", "floor": "y2k floor", "stars": "star stack",
}
LIST = list(NAMES)


class Pen:
    """Just enough of the canvas API: stroke colour, width, alpha; lines, arcs, fills.
    Draws on an RGB black image with alpha blending, so overlapping strokes add up as on canvas."""

    def __init__(self, im, lw=2.0):
        self.im, self.d = im, ImageDraw.Draw(im, "RGBA")
        self.lw, self.col, self.alpha = lw, INK, 1.0

    def _c(self, col=None, a=None):
        c = col or self.col
        return (c[0], c[1], c[2], int(255 * max(0.0, min(1.0, self.alpha if a is None else a))))

    def poly(self, pts, close=False):
        run = []
        for p in list(pts) + ([pts[0]] if close and pts and pts[0] else []):
            if p is None:
                self._run(run); run = []
            else:
                run.append((p[0], p[1]))
        self._run(run)

    def _run(self, run):
        if len(run) >= 2:
            self.d.line(run, fill=self._c(), width=max(1, round(self.lw)), joint="curve")

    def line(self, x0, y0, x1, y1):
        self.d.line([(x0, y0), (x1, y1)], fill=self._c(), width=max(1, round(self.lw)))

    def ellipse(self, cx, cy, rx, ry, rot=0.0, a0=0.0, a1=TAU, n=96):
        pts = []
        for i in range(n + 1):
            a = a0 + (a1 - a0) * i / n
            x, y = math.cos(a) * rx, math.sin(a) * ry
            pts.append((cx + x * math.cos(rot) - y * math.sin(rot), cy + x * math.sin(rot) + y * math.cos(rot)))
        self.poly(pts)

    def circle(self, cx, cy, r):
        self.ellipse(cx, cy, r, r)

    def arc(self, cx, cy, r, a0, a1):
        self.ellipse(cx, cy, r, r, 0, a0, a1, max(8, int(abs(a1 - a0) * 30)))

    def dot(self, cx, cy, r, col=None, a=None):
        self.d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=self._c(col, a))

    def fill_poly(self, pts, col=None, a=None):
        self.d.polygon([(p[0], p[1]) for p in pts], fill=self._c(col, a))

    def rect(self, x, y, w, h):
        self.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], close=True)

    def dashed_circle(self, cx, cy, r, dash, gap, offset):
        circ = TAU * r; step = dash + gap; s = -(offset % step)
        while s < circ:
            a0, a1 = max(0.0, s) / r, min(circ, s + dash) / r
            if a1 > a0:
                self.arc(cx, cy, r, a0, a1)
            s += step


def sphere(cx, cy, R, lat, lon, t):
    l = lon + t
    x, z = math.cos(lat) * math.sin(l), math.cos(lat) * math.cos(l)
    return None if z < -0.02 else (cx + R * x, cy - R * math.sin(lat), z)


def rot3(p, ax, ay):
    x, y, z = p
    c, s = math.cos(ax), math.sin(ax)
    y1, z1 = y * c - z * s, y * s + z * c
    c2, s2 = math.cos(ay), math.sin(ay)
    return (x * c2 + z1 * s2, y1, -x * s2 + z1 * c2)


def globe(p, cx, cy, R, t, a):
    p.circle(cx, cy, R)
    for k in range(12):
        lon = k * TAU / 12
        p.poly([sphere(cx, cy, R, -math.pi / 2 + i * math.pi / 40, lon, t) for i in range(41)])
    for k in range(1, 8):
        lat = -math.pi / 2 + k * math.pi / 8
        p.ellipse(cx, cy - R * math.sin(lat), R * math.cos(lat), R * math.cos(lat) * 0.16, 0, 0, math.pi)
    p.col = a; p.ellipse(cx, cy, R * 1.32, R * 0.32, -0.32)


def checker(p, cx, cy, R, t, a):
    nlat, nlon = 10, 16
    for i in range(nlat):
        for j in range(nlon):
            if (i + j) % 2:
                continue
            la0 = -math.pi / 2 + i * math.pi / nlat; la1 = la0 + math.pi / nlat
            lo0 = j * TAU / nlon; lo1 = lo0 + TAU / nlon
            q = [sphere(cx, cy, R, la0, lo0, t), sphere(cx, cy, R, la0, lo1, t), sphere(cx, cy, R, la1, lo1, t), sphere(cx, cy, R, la1, lo0, t)]
            if any(v is None for v in q):
                continue
            p.fill_poly(q, a=0.25 + 0.75 * min(1, q[0][2] * 1.4))
    p.circle(cx, cy, R)
    p.dot(cx + R * 0.92, cy - R * 0.92, 7, col=a, a=1)


def waves(p, cx, cy, R, t, a):
    for k in range(13):
        y0 = cy - R + k * (2 * R / 12); pts = []; x = -R * 1.3
        while x <= R * 1.3:
            env = math.exp(-(x * x) / (R * R * 0.6))
            pts.append((cx + x, y0 + math.sin(x * 0.03 + t * 3 + k * 0.5) * 34 * env)); x += 6
        p.col = a if k == 6 else INK; p.poly(pts)
    p.col = INK


def warp(p, cx, cy, R, t, a):
    n = 12; s = 2 * R / n

    def d(x, y):
        r = math.hypot(x, y) / R; k = 1 + 0.35 * math.sin(r * 4 - t * 2) * max(0, 1 - r)
        return (cx + x * k, cy + y * k)
    for i in range(n + 1):
        pts, pts2 = [], []
        for j in range(41):
            u, v = -R + j * 2 * R / 40, -R + i * s
            pts.append(d(u, v)); pts2.append(d(v, u))
        p.poly(pts); p.poly(pts2)
    p.col = a; p.rect(cx - R - 10, cy - R - 10, 2 * R + 20, 2 * R + 20)


def orbits(p, cx, cy, R, t, a):
    p.circle(cx, cy, R * 0.22)
    for i, (rot, sp) in enumerate([(0, 1), (1.05, -1), (2.1, 2)]):   # whole turns in 2π: the loop is seamless
        p.ellipse(cx, cy, R, R * 0.3, rot)
        ph = t * sp + i * 2; x, y = math.cos(ph) * R, math.sin(ph) * R * 0.3
        p.dot(cx + x * math.cos(rot) - y * math.sin(rot), cy + x * math.sin(rot) + y * math.cos(rot), 8, col=a if i == 0 else INK)


def target(p, cx, cy, R, t, a):
    for k in range(1, 6):
        p.circle(cx, cy, R * k / 5)
    p.dashed_circle(cx, cy, R * 1.18, 4, 10, -t * 182 / TAU)   # 13 whole dash steps (4 + 10) per 2π of t: seamless
    for k in range(4):
        an = k * math.pi / 2
        p.line(cx + math.cos(an) * R * 1.05, cy + math.sin(an) * R * 1.05, cx + math.cos(an) * R * 1.32, cy + math.sin(an) * R * 1.32)
    p.col = a; p.arc(cx, cy, R * 1.18, t, t + 0.8)


def spiral(p, cx, cy, R, t, a):
    pts = []
    for i in range(601):
        th = i / 600 * TAU * 7; r = R * i / 600
        pts.append((cx + math.cos(th - t * 1.5) * r, cy + math.sin(th - t * 1.5) * r))
    p.poly(pts)
    p.dot(cx + math.cos(TAU * 7 - t * 1.5) * R, cy + math.sin(TAU * 7 - t * 1.5) * R, 8, col=a)


def burst(p, cx, cy, R, t, a):
    for k in range(72):
        an = k * TAU / 72 + t / 36; ln = R * (0.45 + 0.55 * abs(math.sin(k * 1.7 + t * (1.7 + math.pi) / math.pi)))   # after π every ray stands where the next was, as long: seamless
        p.line(cx + math.cos(an) * R * 0.3, cy + math.sin(an) * R * 0.3, cx + math.cos(an) * ln, cy + math.sin(an) * ln)
    p.col = a; p.circle(cx, cy, R * 0.3)


def torus(p, cx, cy, R, t, a):
    def ring(u0, is_u):
        pts = []
        for k in range(49):
            u = u0 if is_u else k * TAU / 48; v = k * TAU / 48 if is_u else u0
            uu = u + t / 24   # spins about its own axis: one ring step per 2π of t (seamless)
            q = rot3(((1 + 0.42 * math.cos(v)) * math.cos(uu), 0.42 * math.sin(v), (1 + 0.42 * math.cos(v)) * math.sin(uu)), 1.0, 0.3)
            pts.append(None if q[2] < -0.55 else (cx + q[0] * R * 0.72, cy + q[1] * R * 0.72))
        p.poly(pts)
    for i in range(24):
        ring(i * TAU / 24, True)
    p.col = a
    for i in range(2):
        ring(i * math.pi, False)


def cube(p, cx, cy, R, t, a):
    def box(s, col):
        p.col = col
        c, sn = math.cos(t / 4), math.sin(t / 4)   # spins about its own vertical axis: a quarter turn per 2π of t
        v = [rot3(((x * c - z * sn) * s, y * s, (x * sn + z * c) * s), 0.6, 0.5) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
        for i, j in [(0, 1), (0, 2), (0, 4), (1, 3), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 6), (5, 7), (6, 7)]:
            p.line(cx + v[i][0] * R * 0.6, cy + v[i][1] * R * 0.6, cx + v[j][0] * R * 0.6, cy + v[j][1] * R * 0.6)
    box(1, INK); box(0.5, a)


def tunnel(p, cx, cy, R, t, a):
    for k in range(14):
        f = (k / 14 + t * 0.15) % 1; s = f ** 2.2 * R * 1.3
        p.alpha = min(1, f * 1.6); p.rect(cx - s, cy - s * 0.75, 2 * s, 1.5 * s)
    p.alpha = 1; p.col = a
    p.line(cx - R * 1.3, cy - R * 0.98, cx + R * 1.3, cy + R * 0.98)
    p.line(cx + R * 1.3, cy - R * 0.98, cx - R * 1.3, cy + R * 0.98)


def dots(p, cx, cy, R, t, a):
    n = 420; ga = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        y = 1 - (i / (n - 1)) * 2; r0 = math.sqrt(max(0, 1 - y * y)); th = ga * i
        q = rot3((math.cos(th) * r0, y, math.sin(th) * r0), 0.35, t)
        if q[2] < -0.1:
            continue
        p.dot(cx + q[0] * R, cy + q[1] * R, 2 + 3 * q[2], col=a if i % 37 == 0 else INK, a=0.3 + 0.7 * q[2])


def helix(p, cx, cy, R, t, a):
    for s in range(2):
        pts = []
        for k in range(121):
            y = cy - R * 1.2 + k * 2.4 * R / 120; ph = k * 0.16 + t * 2 + s * math.pi
            pts.append((cx + math.sin(ph) * R * 0.5, y))
        p.poly(pts)
    for k in range(0, 121, 8):
        y = cy - R * 1.2 + k * 2.4 * R / 120; ph = k * 0.16 + t * 2
        p.col = INK if k % 24 else a
        p.line(cx + math.sin(ph) * R * 0.5, y, cx - math.sin(ph) * R * 0.5, y)
    p.col = INK


def lissajous(p, cx, cy, R, t, a):
    p.poly([(cx + math.sin(3 * (k / 800 * TAU) + t) * R, cy + math.sin(4 * (k / 800 * TAU)) * R * 0.8) for k in range(801)])
    p.col = a; p.rect(cx - R - 14, cy - R * 0.8 - 14, 2 * R + 28, 1.6 * R + 28)


def rose(p, cx, cy, R, t, a):
    pts = []
    for k in range(901):
        th = k / 900 * TAU * 2; r = R * math.cos(2.5 * th)
        pts.append((cx + math.cos(th + t * 0.4) * r, cy + math.sin(th + t * 0.4) * r))
    p.poly(pts); p.dot(cx, cy, 7, col=a)


def radar(p, cx, cy, R, t, a):
    for k in range(1, 5):
        p.circle(cx, cy, R * k / 4)
    p.line(cx - R, cy, cx + R, cy); p.line(cx, cy - R, cx, cy + R)
    an = t * 2.2
    for k in range(24):
        p.alpha = (1 - k / 24) * 0.6
        p.line(cx, cy, cx + math.cos(an - k * 0.03) * R, cy + math.sin(an - k * 0.03) * R)
    p.alpha = 1
    for b, d in [(0.6, 0.8), (2.4, 0.5), (4.1, 0.7)]:
        p.dot(cx + math.cos(b) * R * d, cy + math.sin(b) * R * d, 6, col=a)


def floor(p, cx, cy, R, t, a):
    hz, bottom = cy - R * 0.1, cy + R * 1.2
    for k in range(-10, 11):
        p.line(cx + k * 8, hz, cx + k * R * 0.32, bottom)
    for k in range(12):
        f = (((k / 12) + t * 0.2) % 1) ** 2; y = hz + f * (bottom - hz)
        p.alpha = f; p.line(cx - R * 3.4 * f - 20, y, cx + R * 3.4 * f + 20, y)
    p.alpha = 1; p.col = a
    r = R * 0.6
    p.arc(cx, hz, r, math.pi, TAU)
    for k in range(1, 9):   # the sliced sun: chords inside the half disc
        y = hz - k * k * 1.6 - 4
        if hz - y < r:
            half = math.sqrt(r * r - (hz - y) ** 2); p.line(cx - half, y, cx + half, y)


def stars(p, cx, cy, R, t, a):
    def star(r, n, rot):
        pts = []
        for k in range(n * 2 + 1):
            rr = r * 0.45 if k % 2 else r; an = rot + k * math.pi / n
            pts.append((cx + math.cos(an) * rr, cy + math.sin(an) * rr))
        p.poly(pts)
    for k in range(6):
        n = 5 + (k % 3); star(R * (1 - k * 0.15), n, t * 4 / n * (-1 if k % 2 else 1) + k)   # one point per π/2 of t: seamless
    p.col = a; star(R * 0.18, 4, t)


SHAPES = {n: globals()[n] for n in LIST}


def render(shape, t, accent, w, h, lw=2.0, R=None, ss=2):
    """One frame of a figure on black, supersampled ss× and scaled back down for smooth lines."""
    W, H = w * ss, h * ss
    im = Image.new("RGB", (W, H), (0, 0, 0))
    p = Pen(im, lw * ss)
    shape = shape if shape in SHAPES else "globe"
    SHAPES[shape](p, W / 2, H / 2, (R * ss) if R else min(W, H) * 0.36, t, tuple(accent))
    return im.resize((w, h), Image.LANCZOS) if ss != 1 else im
