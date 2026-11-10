# flake8: noqa
# Script « odoo shell » : la variable env est fournie par le shell Odoo.
# Retouches de la démo : identité du shop, images produit carrées, wishlist de Camille
import base64, io, json, sys

sys.path.insert(0, "/work")
from PIL import Image, ImageDraw, ImageFont
from covers import F_BLACK, F_MED

IDS = json.load(open("/work/ids.json"))
company = env.company
company.write(
    {
        "phone": "+32 81 12 34 56",
        "email": "contact@bulles-et-cases.example",
        "street": "Rue des Bulles 12",
        "zip": "5000",
        "city": "Namur",
    }
)

# Logo texte sobre
logo = Image.new("RGBA", (720, 180), (0, 0, 0, 0))
d = ImageDraw.Draw(logo)
d.ellipse([10, 30, 130, 150], fill=(113, 75, 103, 255))
d.ellipse([70, 20, 160, 100], fill=(240, 160, 60, 255))
f = ImageFont.truetype(F_BLACK, 74)
d.text((180, 40), "Bulles & Cases", font=f, fill=(45, 45, 60, 255))
logo = logo.crop(logo.getbbox())
buf = io.BytesIO()
logo.save(buf, "PNG")
b64 = base64.b64encode(buf.getvalue())
company.logo = b64
website = env["website"].search([], limit=1)
website.logo = b64

# Images produit : couverture centrée sur fond carré clair (évite le recadrage)
for ed in env["comic.edition"].search([("product_tmpl_id", "!=", False)]):
    img = Image.open(io.BytesIO(base64.b64decode(ed.image_couverture))).convert("RGB")
    side = max(img.size) + 80
    sq = Image.new("RGB", (side, side), (244, 242, 238))
    sq.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
    buf = io.BytesIO()
    sq.save(buf, "JPEG", quality=90)
    ed.product_tmpl_id.image_1920 = base64.b64encode(buf.getvalue())

# Wishlist de Camille plus fournie
cam = env["res.users"].browse(IDS["camille_uid"]).partner_id
CA = env["comic.customer.album"].sudo()
for serie_name, tome in (("Capitaine Ombelline", 3), ("Le Dernier Phare", 2)):
    w = env["comic.work"].search([("serie_id.name", "=", serie_name), ("tome", "=", tome)])
    if not CA.search([("partner_id", "=", cam.id), ("edition_id", "=", w.primary_edition_id.id)]):
        CA.create(
            {
                "partner_id": cam.id,
                "edition_id": w.primary_edition_id.id,
                "dans_collection": False,
                "dans_wishlist": True,
            }
        )

IDS["shop_serie"] = env["comic.serie"].search([("name", "=", "Le Dernier Phare")]).id
IDS["work_ai"] = env["comic.work"].search([("serie_id.name", "=", "Les Chroniques d'Argos"), ("tome", "=", 5)]).id
json.dump(IDS, open("/work/ids.json", "w"))
env.cr.commit()
print("FIX OK", IDS)
