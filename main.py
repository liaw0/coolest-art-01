#!/usr/bin/env python3
"""Coolest art: "The Night the Jellyfish Came to the City".

A giant luminous jellyfish drifts over a tiny neon city skyline at night.
One clear focal point (the glowing bell), high-contrast teal/magenta palette,
clean vector-poster style, no text. Pure stdlib, fully deterministic:
same bytes on every run.

Run:  MAKEFUN_OUTPUT_DIR=out python3 main.py   -> writes out/entry.png
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024
OUT_NAME = "entry.png"


# --------------------------------------------------------------------------
# Deterministic RNG (LCG) -- no random module state, no time, no hash seed.
# --------------------------------------------------------------------------
class Rng:
    def __init__(self, seed):
        self.s = seed & 0x7FFFFFFF

    def next(self):
        self.s = (self.s * 1103515245 + 12345) & 0x7FFFFFFF
        return self.s

    def rand(self):
        return self.next() / 0x80000000

    def randint(self, lo, hi):
        return lo + int(self.rand() * (hi - lo + 1))


# --------------------------------------------------------------------------
# Colour helpers
# --------------------------------------------------------------------------
def lerp(a, b, t):
    return a + (b - a) * t


def lerp_rgb(c1, c2, t):
    return (
        int(round(lerp(c1[0], c2[0], t))),
        int(round(lerp(c1[1], c2[1], t))),
        int(round(lerp(c1[2], c2[2], t))),
    )


def blend(fg, bg, alpha):
    """fg over bg, alpha 0..1."""
    return (
        int(round(fg[0] * alpha + bg[0] * (1 - alpha))),
        int(round(fg[1] * alpha + bg[1] * (1 - alpha))),
        int(round(fg[2] * alpha + bg[2] * (1 - alpha))),
    )


def gradient_row(y, stops):
    """stops: list of (y_frac, rgb). Returns rgb at row y."""
    t = y / (H - 1)
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t0 <= t <= t1:
            f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            return lerp_rgb(c0, c1, f)
    return stops[-1][1]


# --------------------------------------------------------------------------
# Canvas: RGB bytearray, span fills (fast, no per-pixel Python loops).
# --------------------------------------------------------------------------
class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.buf = bytearray(w * h * 3)

    def _row_off(self, y):
        return y * self.w * 3

    def get(self, x, y):
        x = max(0, min(self.w - 1, x))
        y = max(0, min(self.h - 1, y))
        o = self._row_off(y) + x * 3
        return (self.buf[o], self.buf[o + 1], self.buf[o + 2])

    def set_px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            o = self._row_off(y) + x * 3
            self.buf[o], self.buf[o + 1], self.buf[o + 2] = c

    def fill_row_span(self, y, x0, x1, c):
        if y < 0 or y >= self.h:
            return
        x0 = max(0, x0)
        x1 = min(self.w - 1, x1)
        if x1 < x0:
            return
        o = self._row_off(y) + x0 * 3
        n = x1 - x0 + 1
        self.buf[o:o + n * 3] = bytes(c) * n

    def fill_rect(self, x0, y0, x1, y1, c):
        for y in range(max(0, y0), min(self.h, y1 + 1)):
            self.fill_row_span(y, x0, x1, c)

    def fill_ellipse(self, cx, cy, rx, ry, c):
        """Solid ellipse via row spans."""
        if rx <= 0 or ry <= 0:
            return
        for y in range(max(0, int(cy - ry)), min(self.h, int(cy + ry) + 1)):
            dy = (y - cy) / ry
            if abs(dy) >= 1.0:
                continue
            dx = rx * math.sqrt(1.0 - dy * dy)
            self.fill_row_span(y, int(cx - dx), int(cx + dx), c)

    def fill_ellipse_rows(self, cx, cy, rx, ry, row_color):
        """Ellipse whose colour is a function of row y."""
        if rx <= 0 or ry <= 0:
            return
        for y in range(max(0, int(cy - ry)), min(self.h, int(cy + ry) + 1)):
            dy = (y - cy) / ry
            if abs(dy) >= 1.0:
                continue
            dx = rx * math.sqrt(1.0 - dy * dy)
            self.fill_row_span(y, int(cx - dx), int(cx + dx), row_color(y))

    def draw_disc(self, cx, cy, r, c):
        self.fill_ellipse(cx, cy, r, r, c)

    def draw_line(self, x0, y0, x1, y1, c, width=1):
        """Bresenham-ish thick line via short spans (fine for small widths)."""
        steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        hw = width // 2
        for i in range(steps + 1):
            t = i / steps
            x = int(round(lerp(x0, x1, t)))
            y = int(round(lerp(y0, y1, t)))
            self.fill_row_span(y, x - hw, x + hw, c)


# --------------------------------------------------------------------------
# Scene
# --------------------------------------------------------------------------
def draw_sky(cv):
    stops = [
        (0.00, (6, 9, 34)),      # deep indigo
        (0.35, (24, 18, 66)),    # violet
        (0.62, (74, 28, 92)),    # purple
        (0.78, (168, 52, 96)),   # magenta horizon
        (1.00, (255, 122, 69)),  # orange glow at the bottom
    ]
    for y in range(H):
        cv.fill_row_span(y, 0, W - 1, gradient_row(y, stops))


def draw_stars(cv, rng):
    # 260 stars, brighter ones get a tiny cross sparkle.
    for _ in range(260):
        x = rng.randint(0, W - 1)
        y = rng.randint(0, int(H * 0.62))
        b = rng.randint(120, 255)
        c = (b, b, min(255, b + 20))
        cv.set_px(x, y, c)
        if rng.rand() < 0.22:
            cv.set_px(x - 1, y, c)
            cv.set_px(x + 1, y, c)
            cv.set_px(x, y - 1, c)
            cv.set_px(x, y + 1, c)
        elif rng.rand() < 0.10:
            cv.set_px(x - 2, y, c)
            cv.set_px(x + 2, y, c)


def draw_small_jellyfish(cv, cx, cy, r, tint, alpha):
    """A distant, dim jellyfish: dome + a few short tentacles."""
    sky = cv.get(cx, cy)
    glow = blend(tint, sky, alpha)
    cv.fill_ellipse(cx, cy, r * 1.35, r * 1.1, blend(tint, sky, alpha * 0.35))
    cv.fill_ellipse_rows(
        cx, cy, r, r * 0.78,
        lambda y: blend(lerp_rgb((240, 250, 255), tint, (y - (cy - r * 0.78)) / (r * 1.56)), sky, alpha),
    )
    rng = Rng(cx * 7919 + cy)
    for i in range(5):
        x0 = cx + int((i - 2) * r * 0.32)
        length = int(r * (1.4 + rng.rand() * 0.7))
        cv.draw_line(x0, cy + int(r * 0.5), x0 + int((rng.rand() - 0.5) * 14),
                     cy + int(r * 0.5) + length, glow, width=2)


def draw_city(cv, rng):
    """Dark skyline silhouette with lit windows, bottom of the frame."""
    base_y = H
    # Ground glow band behind the buildings.
    for y in range(800, H):
        t = (y - 800) / (H - 800)
        c = lerp_rgb((255, 122, 69), (16, 10, 30), t)
        cv.fill_row_span(y, 0, W - 1, c)
    x = -10
    while x < W + 10:
        bw = rng.randint(46, 110)
        bh = rng.randint(70, 210)
        top = base_y - bh
        # A few towers get a small antenna.
        cv.fill_rect(x, top, x + bw, base_y, (13, 10, 26))
        if rng.rand() < 0.3:
            cv.fill_rect(x + bw // 2 - 2, top - 22, x + bw // 2 + 2, top, (13, 10, 26))
            cv.set_px(x + bw // 2, top - 24, (255, 90, 120))
        # Lit windows: deterministic grid, some lit.
        win_cols = [(255, 210, 122), (123, 231, 255), (255, 120, 200)]
        for wy in range(top + 12, base_y - 8, 16):
            for wx in range(x + 8, x + bw - 8, 14):
                if rng.rand() < 0.34:
                    cv.fill_rect(wx, wy, wx + 5, wy + 7,
                                 win_cols[rng.randint(0, 2)])
        x += bw + rng.randint(2, 14)
    # Street glow line.
    cv.fill_row_span(H - 6, 0, W - 1, (255, 150, 90))


def draw_tentacle(cv, x_top, y_top, length, sway, phase, width, core, halo):
    """One wavy tentacle: wide faint halo pass, then bright core pass."""
    steps = length
    for wdt, col in ((width * 3, halo), (width, core)):
        hw = max(1, wdt // 2)
        for i in range(steps):
            t = i / steps
            y = y_top + i
            if y >= H:
                break
            x = x_top + int(sway * math.sin(phase + t * 4.2) * (0.4 + t))
            taper = 1.0 - 0.75 * t
            w = max(1, int(hw * taper))
            cv.fill_row_span(y, x - w, x + w, col)


def draw_jellyfish(cv, rng):
    cx, cy = 512, 330
    rx, ry = 252, 196
    sky = cv.get(cx, cy)

    # Halo: many thin translucent layers, smoothly stepping from magenta
    # (outer) to cyan (inner) so no hard rings show.
    for i in range(12):
        t = i / 11.0
        col = lerp_rgb((255, 79, 216), (53, 224, 255), t)
        f = 1.48 - t * 0.46
        cv.fill_ellipse(cx, cy, rx * f, ry * f, blend(col, sky, 0.07))

    # Rim: bright cyan edge.
    cv.fill_ellipse(cx, cy, rx + 7, ry + 7, (150, 246, 255))

    # Bell body: vertical gradient, bright core top -> deep violet bottom.
    top_c = (234, 252, 255)
    mid_c = (110, 214, 255)
    bot_c = (128, 84, 255)

    def bell_row(y):
        t = (y - (cy - ry)) / (2 * ry)
        if t < 0.55:
            return lerp_rgb(top_c, mid_c, t / 0.55)
        return lerp_rgb(mid_c, bot_c, (t - 0.55) / 0.45)

    cv.fill_ellipse_rows(cx, cy, rx, ry, bell_row)

    # Warm inner glow low in the bell: layered translucent magenta over the
    # bell's own gradient, so the bell reads luminous at its base and ties
    # visually into the magenta tentacles below.
    gy = cy + int(ry * 0.42)
    for fr, al in ((1.00, 0.05), (0.75, 0.06), (0.50, 0.07)):
        cv.fill_ellipse_rows(
            cx, gy, int(150 * fr), int(64 * fr),
            lambda y, a=al: blend((255, 110, 210), bell_row(y), a),
        )

    # Inner glow: soft highlight near the top centre of the bell.
    cv.fill_ellipse(cx - 20, cy - 58, 96, 50, (212, 242, 255))
    cv.fill_ellipse(cx - 20, cy - 54, 58, 30, (238, 250, 255))

    # Ribs: thin curved lines fanning from the bell's top centre.
    for k in range(-3, 4):
        ang = k * 0.16
        x0 = cx + int(30 * math.sin(ang))
        y0 = cy - ry + 26
        x1 = cx + int((rx - 14) * math.sin(ang * 1.9))
        y1 = cy + int(ry * 0.55)
        cv.draw_line(x0, y0, x1, y1, (190, 235, 255), width=1)

    # Oral arms: 4 thick wavy tentacles from under the bell.
    arms = [
        (cx - 128, 0.9, 470, 26, 0.0, (255, 120, 220)),
        (cx - 44, 0.7, 540, 34, 1.4, (120, 235, 255)),
        (cx + 52, 1.1, 500, 30, 2.6, (190, 140, 255)),
        (cx + 138, 0.8, 430, 22, 3.9, (255, 170, 120)),
    ]
    for x0, ph, ln, sw, pha, col in arms:
        sky2 = cv.get(x0, cy + ry - 10)
        draw_tentacle(cv, x0, cy + int(ry * 0.62), ln, sw, pha, 7,
                      col, blend(col, sky2, 0.18))

    # Trailing thin tentacles.
    for i in range(9):
        x0 = cx - 190 + i * 48
        ln = 300 + rng.randint(0, 180)
        col = [(53, 224, 255), (255, 79, 216), (178, 120, 255)][i % 3]
        sky2 = cv.get(x0, cy + ry - 10)
        draw_tentacle(cv, x0, cy + int(ry * 0.55), ln, 16, i * 0.9, 3,
                      col, blend(col, sky2, 0.30))

    # Floating glowing orbs drifting off the tentacles.
    for i in range(14):
        ox = cx - 260 + rng.randint(0, 520)
        oy = cy + 200 + rng.randint(0, 420)
        r = rng.randint(3, 9)
        col = [(53, 224, 255), (255, 79, 216), (255, 210, 122)][i % 3]
        s = cv.get(ox, oy)
        cv.draw_disc(ox, oy, r + 4, blend(col, s, 0.25))
        cv.draw_disc(ox, oy, r, col)


def vignette(cv):
    """Mild vertical falloff: darken top and bottom edges via per-row tables."""
    for y in range(H):
        d = min(y, H - 1 - y) / (H / 2)
        f = 0.72 + 0.28 * d  # 0.72 at edges, 1.0 at centre
        if f >= 0.999:
            continue
        table = bytes(int(round(v * f)) for v in range(256))
        o = y * W * 3
        row = cv.buf[o:o + W * 3]
        cv.buf[o:o + W * 3] = row.translate(table)


# --------------------------------------------------------------------------
# PNG encoder (deterministic: fixed zlib level, no ancillary chunks).
# --------------------------------------------------------------------------
def png_bytes(cv):
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: none
        o = y * W * 3
        raw += cv.buf[o:o + W * 3]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
            chunk(b"IDAT", comp) + chunk(b"IEND", b""))


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    rng = Rng(20261113)
    cv = Canvas(W, H)
    draw_sky(cv)
    draw_stars(cv, rng)
    # Two small distant jellyfish for depth, left and right. Alpha is high
    # so they read as glowing companions, not grey smudges, at small size.
    draw_small_jellyfish(cv, 168, 210, 52, (53, 224, 255), 0.85)
    draw_small_jellyfish(cv, 872, 168, 40, (255, 79, 216), 0.80)
    draw_jellyfish(cv, rng)
    draw_city(cv, rng)
    vignette(cv)
    data = png_bytes(cv)
    path = os.path.join(out_dir, OUT_NAME)
    with open(path, "wb") as f:
        f.write(data)
    print(f"wrote {path} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
