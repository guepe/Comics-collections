"""Génération de couvertures BD fictives (Pillow) pour la démo App Store."""

import base64
import colorsys
import io
import math
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_DIR = "/usr/share/fonts/truetype/roboto/unhinted/"
F_BLACK = FONT_DIR + "RobotoTTF/Roboto-Black.ttf"
F_BOLD = FONT_DIR + "RobotoTTF/Roboto-Bold.ttf"
F_MED = FONT_DIR + "RobotoTTF/Roboto-Medium.ttf"
F_COND = FONT_DIR + "RobotoCondensed-Bold.ttf"
F_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"

W, H = 600, 800


def font(path, size):
    return ImageFont.truetype(path, size)


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def shift(rgb, dh=0.0, dl=0.0, ds=0.0):
    r, g, b = (c / 255 for c in rgb)
    h, lum, s = colorsys.rgb_to_hls(r, g, b)
    h = (h + dh) % 1
    lum = max(0, min(1, lum + dl))
    s = max(0, min(1, s + ds))
    return tuple(int(c * 255) for c in colorsys.hls_to_rgb(h, lum, s))


def gradient(c1, c2, w=W, h=H):
    img = Image.new("RGB", (w, h), c1)
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / (h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(c1, c2)))
    return img


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=fnt) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_font(draw, text, path, max_w, start, min_size=20, max_lines=2):
    size = start
    while size > min_size:
        f = font(path, size)
        lines = wrap(draw, text, f, max_w)
        if len(lines) <= max_lines and all(draw.textlength(line, font=f) <= max_w for line in lines):
            return f, lines
        size -= 2
    f = font(path, min_size)
    return f, wrap(draw, text, f, max_w)


# ── Motifs ────────────────────────────────────────────────────────────────


def motif_mountains(img, rnd, accent):
    d = ImageDraw.Draw(img, "RGBA")
    cx, cy = rnd.randint(150, 450), rnd.randint(250, 340)
    d.ellipse([cx - 90, cy - 90, cx + 90, cy + 90], fill=accent + (230,))
    for layer, alpha in ((0, 120), (1, 190), (2, 255)):
        base = 560 + layer * 60
        pts = [(0, H)]
        x = -40
        while x < W + 80:
            pts.append((x, base - rnd.randint(80, 220) + layer * 30))
            x += rnd.randint(90, 160)
            pts.append((x, base + rnd.randint(-10, 30)))
        pts.append((W, H))
        shade = 20 + layer * 15
        d.polygon(pts, fill=(shade, shade, shade + 20, alpha))


def motif_space(img, rnd, accent):
    d = ImageDraw.Draw(img, "RGBA")
    for _ in range(160):
        x, y = rnd.randint(0, W), rnd.randint(0, H)
        r = rnd.choice((1, 1, 1, 2, 2, 3))
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, rnd.randint(120, 255)))
    cx, cy, r = rnd.randint(180, 420), rnd.randint(380, 480), rnd.randint(110, 150)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=accent + (255,))
    d.ellipse([cx - r + 25, cy - r + 10, cx + r - 5, cy + r - 30], fill=shift(accent, dl=0.12) + (120,))
    d.arc([cx - r - 70, cy - 30, cx + r + 70, cy + 40], 200, 520, fill=(255, 255, 255, 200), width=6)
    # station
    sx, sy = rnd.randint(60, 200), rnd.randint(560, 640)
    d.rectangle([sx, sy, sx + 120, sy + 14], fill=(230, 230, 240, 230))
    d.rectangle([sx + 50, sy - 30, sx + 70, sy + 44], fill=(230, 230, 240, 230))


def motif_fog(img, rnd, accent):
    d = ImageDraw.Draw(img, "RGBA")
    # remparts / ville
    x = 0
    while x < W:
        w = rnd.randint(40, 90)
        h = rnd.randint(120, 300)
        d.rectangle([x, 640 - h, x + w, H], fill=(15, 20, 35, 255))
        if rnd.random() < 0.5:
            d.polygon([(x, 640 - h), (x + w / 2, 600 - h), (x + w, 640 - h)], fill=(15, 20, 35, 255))
        for wy in range(640 - h + 20, 640, 34):
            if rnd.random() < 0.35:
                d.rectangle([x + 10, wy, x + 20, wy + 14], fill=accent + (255,))
        x += w + rnd.randint(0, 10)
    for _i in range(6):
        y = rnd.randint(420, 760)
        d.rectangle([0, y, W, y + rnd.randint(18, 40)], fill=(220, 225, 235, 60))
    fog = img.filter(ImageFilter.GaussianBlur(2))
    img.paste(fog)


def motif_waves(img, rnd, accent):
    d = ImageDraw.Draw(img, "RGBA")
    # voilier
    bx = rnd.randint(200, 380)
    d.polygon([(bx, 300), (bx, 520), (bx + 130, 520)], fill=(250, 245, 230, 255))
    d.polygon([(bx - 10, 330), (bx - 10, 520), (bx - 100, 520)], fill=accent + (255,))
    d.polygon([(bx - 130, 530), (bx + 160, 530), (bx + 120, 570), (bx - 100, 570)], fill=(60, 30, 20, 255))
    for k in range(5):
        y0 = 560 + k * 50
        pts = [(0, H)]
        for x in range(0, W + 10, 10):
            pts.append((x, y0 + 14 * math.sin(x / 45 + k * 1.3 + rnd.random())))
        pts.append((W, H))
        d.polygon(pts, fill=(20, 60 + k * 10, 110 + k * 12, 200))


def motif_lighthouse(img, rnd, accent):
    d = ImageDraw.Draw(img, "RGBA")
    lx = rnd.randint(300, 420)
    d.polygon([(lx, 250), (lx - 300 - rnd.randint(0, 80), 120), (lx - 300, 380)], fill=accent + (90,))
    d.polygon([(lx, 250), (lx + 280, 150), (lx + 260, 330)], fill=accent + (60,))
    d.polygon([(lx - 28, 280), (lx + 28, 280), (lx + 45, 640), (lx - 45, 640)], fill=(240, 235, 225, 255))
    for y in (360, 460, 560):
        d.rectangle([lx - 50, y, lx + 50, y + 30], fill=(180, 40, 40, 255))
    d.rectangle([lx - 32, 230, lx + 32, 282], fill=(30, 30, 40, 255))
    d.ellipse([lx - 18, 240, lx + 18, 272], fill=accent + (255,))
    d.polygon([(0, 680), (lx - 120, 620), (lx + 140, 630), (W, 700), (W, H), (0, H)], fill=(25, 25, 35, 255))


def motif_manga(img, rnd, accent):
    d = ImageDraw.Draw(img, "RGBA")
    cx, cy = rnd.randint(250, 350), rnd.randint(380, 450)
    for i in range(90):
        a = i * 2 * math.pi / 90
        d.line([(cx, cy), (cx + 900 * math.cos(a), cy + 900 * math.sin(a))], fill=(0, 0, 0, 40), width=3)
    d.ellipse([cx - 150, cy - 150, cx + 150, cy + 150], fill=accent + (255,))
    # renard stylisé
    d.polygon([(cx - 70, cy + 40), (cx, cy - 60), (cx + 70, cy + 40), (cx, cy + 90)], fill=(250, 250, 250, 255))
    d.polygon([(cx - 70, cy + 40), (cx - 60, cy - 80), (cx - 25, cy - 20)], fill=(250, 250, 250, 255))
    d.polygon([(cx + 70, cy + 40), (cx + 60, cy - 80), (cx + 25, cy - 20)], fill=(250, 250, 250, 255))
    d.ellipse([cx - 30, cy + 5, cx - 14, cy + 21], fill=(20, 20, 20, 255))
    d.ellipse([cx + 14, cy + 5, cx + 30, cy + 21], fill=(20, 20, 20, 255))


def motif_arches(img, rnd, accent):
    d = ImageDraw.Draw(img, "RGBA")
    n = rnd.choice((3, 4))
    w = W // n
    for i in range(n):
        x0 = i * w + 18
        x1 = (i + 1) * w - 18
        d.rectangle([x0, 420, x1, 700], fill=(250, 240, 220, 60))
        d.pieslice([x0, 330, x1, 510], 180, 360, fill=(250, 240, 220, 60))
        d.rectangle([x0 + 12, 430, x1 - 12, 700], fill=accent + (90,))
        d.pieslice([x0 + 12, 342, x1 - 12, 498], 180, 360, fill=accent + (90,))
    for _i in range(14):
        x = rnd.randint(0, W)
        d.ellipse([x - 22, 650 + rnd.randint(-20, 20), x + 22, 694], fill=(40, 90, 50, 220))
    d.rectangle([0, 700, W, H], fill=(60, 45, 35, 255))


def motif_target(img, rnd, accent):
    d = ImageDraw.Draw(img, "RGBA")
    cx, cy = rnd.randint(220, 380), rnd.randint(380, 460)
    for r in range(260, 0, -40):
        d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], outline=accent + (200,), width=5)
    d.line([(cx - 300, cy), (cx + 300, cy)], fill=accent + (160,), width=2)
    d.line([(cx, cy - 300), (cx, cy + 300)], fill=accent + (160,), width=2)
    # silhouette
    d.ellipse([cx - 28, cy - 120, cx + 28, cy - 64], fill=(10, 10, 15, 255))
    d.polygon([(cx - 60, cy + 80), (cx - 40, cy - 60), (cx + 40, cy - 60), (cx + 60, cy + 80)], fill=(10, 10, 15, 255))


MOTIFS = {
    "mountains": motif_mountains,
    "space": motif_space,
    "fog": motif_fog,
    "waves": motif_waves,
    "lighthouse": motif_lighthouse,
    "manga": motif_manga,
    "arches": motif_arches,
    "target": motif_target,
}


def make_cover(
    serie,
    title=None,
    tome=None,
    authors="",
    publisher="",
    palette=("#1d3557", "#e63946"),
    motif="mountains",
    accent="#f4a261",
    seed=0,
    title_font=F_BLACK,
):
    rnd = random.Random(seed)
    c1, c2 = hex2rgb(palette[0]), hex2rgb(palette[1])
    dh = ((tome or 0) * 0.035) % 0.25 - 0.06
    c1, c2 = shift(c1, dh=dh), shift(c2, dh=dh * 0.6)
    img = gradient(c1, c2)
    MOTIFS[motif](img, rnd, shift(hex2rgb(accent), dh=dh * 0.4))
    d = ImageDraw.Draw(img, "RGBA")

    # Bandeau titre de série
    f, lines = fit_font(d, serie.upper(), title_font, W - 70, 64, max_lines=2)
    band = 40 + len(lines) * (f.size + 8) + 14
    d.rectangle([0, 0, W, band], fill=(0, 0, 0, 120))
    y = 34
    for line in lines:
        tw = d.textlength(line, font=f)
        d.text(((W - tw) / 2 + 3, y + 3), line, font=f, fill=(0, 0, 0, 160))
        d.text(((W - tw) / 2, y), line, font=f, fill=(255, 255, 255))
        y += f.size + 8
    d.line([(60, band - 4), (W - 60, band - 4)], fill=hex2rgb(accent) + (255,), width=3)

    if tome:
        fb = font(F_BLACK, 40)
        label = f"T{tome}"
        tw = d.textlength(label, font=fb)
        bx, by = W - 60, band + 58
        r = max(40, tw / 2 + 16)
        d.ellipse([bx - r, by - r, bx + r, by + r], fill=(255, 255, 255, 245), outline=hex2rgb(accent), width=4)
        d.text((bx - tw / 2, by - 25), label, font=fb, fill=(20, 20, 30))

    # Titre de l'album
    if title:
        d.rectangle([0, H - 190, W, H], fill=(0, 0, 0, 150))
        ft, tl = fit_font(d, title, F_BOLD, W - 80, 44, min_size=26, max_lines=2)
        y = H - 175 if len(tl) == 2 else H - 160
        for line in tl:
            tw = d.textlength(line, font=ft)
            d.text(((W - tw) / 2, y), line, font=ft, fill=(255, 255, 255))
            y += ft.size + 6
    else:
        d.rectangle([0, H - 120, W, H], fill=(0, 0, 0, 150))
    fa = font(F_MED, 22)
    if authors:
        tw = d.textlength(authors, font=fa)
        d.text(((W - tw) / 2, H - 62), authors, font=fa, fill=(230, 230, 230))
    if publisher:
        fp = font(F_COND, 16)
        tw = d.textlength(publisher.upper(), font=fp)
        d.text(((W - tw) / 2, H - 30), publisher.upper(), font=fp, fill=hex2rgb(accent))
    return img


def to_b64(img, fmt="JPEG"):
    buf = io.BytesIO()
    img.save(buf, fmt, quality=88)
    return base64.b64encode(buf.getvalue())
