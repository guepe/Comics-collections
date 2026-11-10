"""Recadrage, réduction à 1440 px, optimisation PNG et bannières (Pillow, dans le conteneur)."""

import os
import sys

sys.path.insert(0, "/work")
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402
from covers import F_BLACK, F_MED, F_BOLD  # noqa: E402

RAW = "/work/out/raw"
FIN = "/work/out/final"
os.makedirs(FIN + "/comics_collections", exist_ok=True)
os.makedirs(FIN + "/comic_shop", exist_ok=True)

# nom -> (module, hauteur CSS max)
SHOTS = {
    "screenshot_dashboard": ("comics_collections", 900),
    "screenshot_series": ("comics_collections", 820),
    "screenshot_albums": ("comics_collections", 900),
    "screenshot_album_form": ("comics_collections", 700),
    "screenshot_serie_form": ("comics_collections", 900),
    "screenshot_wishlist": ("comics_collections", 900),
    "screenshot_library": ("comics_collections", 900),
    "screenshot_author": ("comics_collections", 1040),
    "screenshot_import": ("comics_collections", 900),
    "screenshot_ai_wizard": ("comics_collections", 900),
    "shop_product": ("comic_shop", 1100),
    "shop_series": ("comic_shop", 1300),
    "shop_portal_library": ("comic_shop", 1400),
    "shop_portal_dashboard": ("comic_shop", 1400),
    "shop_portal_add": ("comic_shop", 1100),
    "shop_wishlist_public": ("comic_shop", 1300),
    "shop_release_notify": ("comic_shop", 900),
    "shop_portal_discover": ("comic_shop", 1500),
}


def save_png(img, path, colors=256):
    q = img.convert("RGB").quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    q.save(path, optimize=True)
    return os.path.getsize(path)


final = {}
for name, (module, max_h) in SHOTS.items():
    src = os.path.join(RAW, name + ".png")
    img = Image.open(src).convert("RGB")
    scale = 1440 / img.width
    img = img.resize((1440, round(img.height * scale)), Image.LANCZOS)
    img = img.crop((0, 0, 1440, min(img.height, max_h)))
    out = os.path.join(FIN, module, name + ".png")
    size = save_png(img, out)
    if size > 400_000:
        size = save_png(img, out, colors=128)
    final[name] = img
    print(f"{module}/{name}.png {img.width}x{img.height} {size // 1024} Ko")


def banner(path, title, subtitle, shot, crop_box, bg, accent):
    W, H = 1200, 600
    b = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(b)
    # Capture à droite, en débord
    sc = shot.crop(crop_box)
    target_w = 700
    sc = sc.resize((target_w, round(sc.height * target_w / sc.width)), Image.LANCZOS)
    x0, y0 = 540, 110
    shadow = Image.new("RGBA", (sc.width + 60, sc.height + 60), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([30, 30, sc.width + 30, sc.height + 30], 14, fill=(0, 0, 0, 110))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    b.paste(shadow, (x0 - 30 + 6, y0 - 30 + 10), shadow)
    mask = Image.new("L", sc.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, sc.width, sc.height + 40], 14, fill=255)
    b.paste(sc, (x0, y0), mask)
    # Texte
    d.rectangle([60, 170, 120, 176], fill=accent)
    ft = ImageFont.truetype(F_BLACK, 58)
    y = 200
    for line in title.split("\n"):
        d.text((60, y), line, font=ft, fill=(255, 255, 255))
        y += 68
    fs = ImageFont.truetype(F_MED, 27)
    y += 14
    for line in subtitle.split("\n"):
        d.text((60, y), line, font=fs, fill=(225, 222, 235))
        y += 38
    fo = ImageFont.truetype(F_BOLD, 18)
    d.text((60, H - 60), "POUR ODOO 19", font=fo, fill=accent)
    size = save_png(b, path)
    print(f"{path} {W}x{H} {size // 1024} Ko")


banner(
    FIN + "/comics_collections/banner.png",
    "Comic\nCollection",
    "Votre collection de BD\ndans Odoo",
    final["screenshot_library"],
    (40, 62, 1010, 700),
    (52, 40, 72),
    (246, 196, 83),
)
banner(
    FIN + "/comic_shop/banner.png",
    "Comic Shop",
    "Vendez vos BD en ligne\net en caisse",
    final["shop_series"],
    (60, 50, 1440, 900),
    (30, 52, 64),
    (240, 160, 60),
)
