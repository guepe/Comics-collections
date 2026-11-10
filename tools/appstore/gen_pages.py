# flake8: noqa
# Gabarits HTML : lignes longues assumées.
"""Génère les pages Odoo Apps Store (static/description/index.html) de comics_collections et comic_shop.

Styles en ligne uniquement (l'App Store retire <style> et <script>), grille Bootstrap,
icônes Font Awesome (chargées par apps.odoo.com), images relatives à static/description/.
"""

import sys
from pathlib import Path

INK = "#022E51"
INK2 = "#2a4a6a"
INK3 = "#6f88a4"
CREAM = "#f3eee4"
ACCENT = "#B74803"
FONT = "font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;"


def hero(title, tagline, intro, badges, banner):
    badge_html = "".join(
        f'<span style="display:inline-block;margin:4px;padding:5px 12px;border-radius:14px;'
        f'background:#ffffff;color:{INK};font-size:13px;font-weight:600;border:1px solid rgba(2,46,81,.15);">'
        f"{b}</span>"
        for b in badges
    )
    return f"""
<section style="background:{CREAM};padding:48px 16px 40px;{FONT}">
  <div class="container" style="max-width:1100px;margin:auto;text-align:center;">
    <h1 style="color:{INK};font-size:44px;font-weight:800;margin:0 0 8px;letter-spacing:-.5px;">{title}</h1>
    <p style="color:{ACCENT};font-size:21px;font-weight:600;margin:0 0 18px;">{tagline}</p>
    <p style="color:{INK2};font-size:17px;line-height:1.6;max-width:780px;margin:0 auto 18px;">{intro}</p>
    <div style="margin-bottom:28px;">{badge_html}</div>
    <img src="{banner}" alt="{title}" style="max-width:100%;border-radius:10px;box-shadow:0 12px 40px rgba(2,46,81,.18);"/>
  </div>
</section>"""


def grid(title, cards):
    cols = "".join(
        f"""
    <div class="col-md-4 col-sm-6" style="padding:12px;">
      <div style="height:100%;background:#ffffff;border:1px solid rgba(2,46,81,.10);border-radius:10px;padding:22px;">
        <div style="width:44px;height:44px;border-radius:10px;background:{CREAM};color:{ACCENT};
                    display:flex;align-items:center;justify-content:center;font-size:20px;margin-bottom:12px;">
          <i class="fa {icon}"></i>
        </div>
        <h4 style="color:{INK};font-size:17px;font-weight:700;margin:0 0 6px;">{name}</h4>
        <p style="color:{INK2};font-size:14px;line-height:1.55;margin:0;">{text}</p>
      </div>
    </div>"""
        for icon, name, text in cards
    )
    return f"""
<section style="padding:48px 16px;{FONT}">
  <div class="container" style="max-width:1100px;margin:auto;">
    <h2 style="color:{INK};text-align:center;font-size:30px;font-weight:800;margin:0 0 26px;">{title}</h2>
    <div class="row">{cols}
    </div>
  </div>
</section>"""


def feature(kicker, title, paragraphs, bullets, image, reverse=False, dark=False):
    bg = CREAM if dark else "#ffffff"
    text = "".join(
        f'<p style="color:{INK2};font-size:15px;line-height:1.65;margin:0 0 12px;">{p}</p>' for p in paragraphs
    )
    items = "".join(
        f'<li style="margin:0 0 7px;"><i class="fa fa-check" style="color:{ACCENT};margin-right:8px;"></i>{b}</li>'
        for b in bullets
    )
    text_col = f"""
      <div class="col-md-5" style="padding:16px;">
        <div style="color:{ACCENT};font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">{kicker}</div>
        <h3 style="color:{INK};font-size:26px;font-weight:800;margin:0 0 14px;">{title}</h3>
        {text}
        <ul style="list-style:none;padding:0;margin:8px 0 0;color:{INK2};font-size:14px;">{items}</ul>
      </div>"""
    img_col = f"""
      <div class="col-md-7" style="padding:16px;">
        <img src="{image}" alt="{title}" style="width:100%;border-radius:8px;border:1px solid rgba(2,46,81,.12);box-shadow:0 8px 28px rgba(2,46,81,.12);"/>
      </div>"""
    cols = img_col + text_col if reverse else text_col + img_col
    return f"""
<section style="background:{bg};padding:44px 16px;{FONT}">
  <div class="container" style="max-width:1100px;margin:auto;">
    <div class="row" style="align-items:center;display:flex;flex-wrap:wrap;">{cols}
    </div>
  </div>
</section>"""


def addons(title, items):
    cards = "".join(
        f"""
    <div class="col-md-4" style="padding:12px;">
      <div style="height:100%;border-radius:10px;padding:22px;background:#ffffff;border:1px solid rgba(2,46,81,.10);">
        <h4 style="color:{INK};font-size:18px;font-weight:800;margin:0 0 4px;"><i class="fa {icon}" style="color:{ACCENT};margin-right:8px;"></i>{name}</h4>
        <div style="color:{INK3};font-size:12px;font-family:monospace;margin-bottom:10px;">{tech}</div>
        <p style="color:{INK2};font-size:14px;line-height:1.55;margin:0;">{text}</p>
      </div>
    </div>"""
        for icon, name, tech, text in items
    )
    return f"""
<section style="background:{CREAM};padding:48px 16px;{FONT}">
  <div class="container" style="max-width:1100px;margin:auto;">
    <h2 style="color:{INK};text-align:center;font-size:30px;font-weight:800;margin:0 0 26px;">{title}</h2>
    <div class="row">{cards}
    </div>
  </div>
</section>"""


def tech(title, rows, support):
    trs = "".join(
        f'<tr><td style="padding:9px 14px;color:{INK3};font-weight:600;width:34%;border-bottom:1px solid rgba(2,46,81,.08);">{k}</td>'
        f'<td style="padding:9px 14px;color:{INK2};border-bottom:1px solid rgba(2,46,81,.08);">{v}</td></tr>'
        for k, v in rows
    )
    return f"""
<section style="padding:48px 16px;{FONT}">
  <div class="container" style="max-width:860px;margin:auto;">
    <h2 style="color:{INK};text-align:center;font-size:28px;font-weight:800;margin:0 0 22px;">{title}</h2>
    <table style="width:100%;border-collapse:collapse;font-size:14px;background:#ffffff;border:1px solid rgba(2,46,81,.10);border-radius:8px;">{trs}</table>
    <p style="text-align:center;color:{INK2};font-size:15px;margin:26px 0 0;">{support}</p>
  </div>
</section>"""


def page(sections):
    return '<div style="background:#ffffff;">' + "".join(sections) + "\n</div>\n"


SUPPORT = (
    '<i class="fa fa-life-ring" style="color:#B74803;margin-right:6px;"></i>Questions, bugs or feature requests: '
    '<a href="mailto:ph.delaval@gmail.com" style="color:#B74803;">ph.delaval@gmail.com</a> · '
    '<a href="https://github.com/guepe/Comics-collections/issues" style="color:#B74803;">GitHub issues</a>'
)


def collection_page():
    return page(
        [
            hero(
                "Comic Collection",
                "Your comic books, manga and graphic novels — finally organised in Odoo",
                "Series, albums, covers, authors and publishers; a private library for every user with "
                "wishlist, reading status and ratings; the missing volumes of the series you follow; "
                "loans, value and a printable inventory. Built for passionate collectors at home, ready "
                "to grow into a full comic shop.",
                ["Odoo 19", "Community &amp; Enterprise", "LGPL-3", "Free", "Interface in French"],
                "banner.png",
            ),
            grid(
                "Everything a collector needs",
                [
                    (
                        "fa-th-large",
                        "Series &amp; albums",
                        "Cover galleries of your series and volumes, one-shots and "
                        "hors-séries, editions, ISBN, publishers and authors with their roles.",
                    ),
                    (
                        "fa-heart",
                        "Smart wishlist",
                        "Series you start are followed automatically: their missing volumes "
                        "show up in your wishlist next to your own wishes.",
                    ),
                    (
                        "fa-star",
                        "Personal library",
                        "Owned or wished, read or in progress, star ratings, comments, "
                        "purchase price and estimated value — per user.",
                    ),
                    (
                        "fa-bar-chart",
                        "Dashboard",
                        "Collection size and value, complete series, genres, reading "
                        "progress, best-rated series and overdue loans at a glance.",
                    ),
                    (
                        "fa-exchange",
                        "Loans",
                        "Know who borrowed which album, with due dates, overdue highlighting "
                        "and automatic reminders.",
                    ),
                    (
                        "fa-upload",
                        "Import &amp; clean-up",
                        "CSV / Excel import with column mapping and a duplicate " "detector to merge records safely.",
                    ),
                ],
            ),
            feature(
                "Dashboard",
                "Your collection at a glance",
                [
                    "A dedicated dashboard sums up what you own and what you are looking for: number of albums and "
                    "series, complete and ongoing series, wishlist, reading status and genres.",
                    "Add a purchase price and an estimated value to your albums to know what your collection is "
                    "worth — then export it to CSV or print a PDF inventory, e.g. for your insurer.",
                ],
                [
                    "Collection value and totals",
                    "Best-rated series and recent additions",
                    "Overdue loans",
                    "CSV export and PDF inventory",
                ],
                "screenshot_dashboard.png",
                dark=True,
            ),
            feature(
                "Series &amp; albums",
                "Beautiful cover galleries",
                [
                    "<b>My series</b> and <b>My albums</b> open as cover galleries, grouped and sorted by series "
                    "and volume. Each user only sees their own comics; the shared catalogue stays behind the scenes.",
                    "The series form gathers every author of its albums with their roles, and its volumes.",
                ],
                [
                    "Unnumbered volumes and one-shots",
                    "Several editions and ISBN per album",
                    "Authors are regular Odoo contacts",
                    "Chatter and activities everywhere",
                ],
                "screenshot_series.png",
                reverse=True,
            ),
            feature(
                "Album form",
                "All the details, one form",
                [
                    "Create an album with its series, volume, title, publisher, authors and ISBN in a single form. "
                    "ISBN-10 and EAN-13 are validated and converted; on a phone, scan the barcode with the camera.",
                    "Mark albums as read or in progress, add them to your wishlist in one click.",
                ],
                [
                    "ISBN validation, conversion and uniqueness",
                    "Camera barcode scan on mobile",
                    "Purchase links (Club, Amazon, FNAC)",
                    "New-release notifications for followed series",
                ],
                "screenshot_album_form.png",
                dark=True,
            ),
            feature(
                "Wishlist",
                "Never miss a volume again",
                [
                    "Start a series and it is followed automatically (unfollowing is remembered). <b>My wishlist</b> "
                    "lists, series by series, the volumes you are missing plus the albums you wished for.",
                    "One click to say <i>I have it</i>, to ignore a volume you will not buy, or to stop following "
                    "the series.",
                ],
                [
                    "Missing volumes computed per user",
                    "Manual wishes",
                    "Upcoming releases filter",
                    "Shareable wishlist with Comic Shop",
                ],
                "screenshot_wishlist.png",
                reverse=True,
            ),
            feature(
                "Library",
                "Your personal library",
                [
                    "Every album you own or wish for, with your star rating, reading status, comments, purchase "
                    "price and estimated value — private to you, even when several people share the same Odoo.",
                ],
                [
                    "Read / in progress / unread",
                    "1 to 5 stars",
                    "Group by series, genre or source",
                    "Multi-user: shared catalogue, private collections",
                ],
                "screenshot_library.png",
                dark=True,
            ),
            feature(
                "Authors",
                "Who worked with whom",
                [
                    "Authors are Odoo contacts with a comics tab: every series and album they worked on, their roles, "
                    "and the artists they most often worked with — click through to their series.",
                ],
                [
                    "Bibliography per author",
                    "Frequent collaborators",
                    "Publisher catalogues",
                    "Biography tab with the AI add-on",
                ],
                "screenshot_author.png",
                reverse=True,
            ),
            feature(
                "Import",
                "Bring your existing list",
                [
                    "Import a CSV, TSV, XLS or XLSX file: map the columns, choose whether existing albums are updated "
                    "or skipped, download covers from a URL column and get a report with the real line numbers.",
                    "A duplicate detector (normalised titles and similarity score) proposes pairs to merge or ignore.",
                ],
                [
                    "Column mapping step",
                    "Update or skip policy",
                    "Series matched on normalised names",
                    "Scored duplicate pairs, merge in either direction",
                ],
                "screenshot_import.png",
                dark=True,
            ),
            addons(
                "Make it even more powerful",
                [
                    (
                        "fa-cloud-download",
                        "Data sources (free)",
                        "comic_datasource",
                        "Fill in covers, synopses, page counts, dates and authors from Google Books, Open Library and the "
                        "BnF — one button per album, or a nightly job. Detects the missing volumes of followed series.",
                    ),
                    (
                        "fa-magic",
                        "AI assistant (paid add-on)",
                        "comic_ai",
                        "Generate or translate synopses, author biographies and publisher histories with Claude or "
                        "OpenAI, fill empty texts in the background, and discover new series from your 4★ favourites.",
                    ),
                    (
                        "fa-shopping-cart",
                        "Comic Shop (paid add-on)",
                        "comic_shop",
                        "Sell your comics online and at the POS, and give every customer their own library on the "
                        "portal, with series follow-up and release e-mails.",
                    ),
                ],
            ),
            feature(
                "AI add-on",
                "Synopses in seconds",
                [
                    "With <b>comic_ai</b>, a manager generates a synopsis from what the catalogue knows (series, "
                    "volume, authors, publisher), previews and edits it before applying — an existing text is never "
                    "replaced without confirmation, and every change is logged.",
                ],
                [
                    "Claude (Anthropic) or OpenAI, your own API key",
                    "French, Dutch, English, German",
                    "Background filling of empty texts, marked for review",
                    "Discovery of new series",
                ],
                "screenshot_ai_wizard.png",
                reverse=True,
            ),
            tech(
                "Technical information",
                [
                    ("Odoo version", "19.0 — Community and Enterprise"),
                    ("Dependencies", "base, mail, contacts"),
                    ("License", "LGPL-3"),
                    ("Users", "Shared catalogue, private collection per user; manager role for the full catalogue"),
                    ("Interface language", "French (vocabulary: album / tome / série)"),
                    ("Quality", "Automated test suite (≈ 500 tests across the modules), pre-commit, OCA guidelines"),
                ],
                SUPPORT,
            ),
        ]
    )


def shop_page():
    return page(
        [
            hero(
                "Comic Shop",
                "Sell comic books online and at the counter — and keep your customers coming back",
                "Your albums become products in one click, with covers, descriptions and ISBN barcodes kept in sync. "
                "Customers browse series, authors and publishers on your webshop, keep their own comic library on "
                "the portal, follow their series and get an e-mail when the next volume is on sale.",
                ["Odoo 19", "eCommerce", "Point of Sale", "Customer portal", "OPL-1"],
                "banner.png",
            ),
            grid(
                "A comic shop, not just a shop",
                [
                    (
                        "fa-refresh",
                        "Album ↔ product sync",
                        "Name, cover, description and ISBN barcode follow the album. "
                        "Bulk-create the products of a whole series.",
                    ),
                    (
                        "fa-globe",
                        "Webshop pages",
                        "Browse by series, author and publisher; album pages with volume, " "authors and synopsis.",
                    ),
                    (
                        "fa-book",
                        "Customer library",
                        "Collection, wishlist, reading status, ratings and a dashboard for "
                        "every customer on the portal.",
                    ),
                    (
                        "fa-bell",
                        "Release e-mails",
                        "Customers follow series; when a volume goes on sale, you preview "
                        "and send the « now available » e-mail.",
                    ),
                    (
                        "fa-barcode",
                        "Scan &amp; POS",
                        "Scan an ISBN at the counter; paid orders land in the buyer's " "library automatically.",
                    ),
                    (
                        "fa-share-alt",
                        "Shareable wishlist",
                        "A secret, revocable link to show a wishlist to friends and " "family — perfect for gifts.",
                    ),
                ],
            ),
            feature(
                "Webshop",
                "Album pages that sell",
                [
                    "Every album on sale gets a rich product page: series and volume, authors with their roles, "
                    "publisher, synopsis and cover — all coming from your catalogue, always up to date.",
                ],
                [
                    "Series, author and publisher pages",
                    "Filters by series type",
                    "Only published products are shown",
                    "Author biographies with the AI add-on",
                ],
                "shop_product.png",
                dark=True,
            ),
            feature(
                "Series",
                "Follow a series, never miss a volume",
                [
                    "Customers follow a series from the webshop or their library. When you put a new volume on sale, "
                    "Odoo tells you how many customers are waiting for it.",
                ],
                ["Follow / unfollow from the portal", "List of followed series", "One e-mail per album and customer"],
                "shop_series.png",
                reverse=True,
            ),
            feature(
                "Release e-mails",
                "« Good news — it's available! »",
                [
                    "Publish the albums of a series and the assistant shows the customers to notify — followers of "
                    "the series and customers who have the album in their wishlist — with a preview of the e-mail.",
                ],
                ["Preview before sending", "Never twice for the same album", "Logged in the album chatter"],
                "shop_release_notify.png",
                dark=True,
            ),
            feature(
                "Customer portal",
                "A comic library for every customer",
                [
                    "On <b>My library</b>, customers keep their collection and wishlist, reading status, star ratings "
                    "and comments. Albums bought in your shop are added automatically; others are added by ISBN, "
                    "title search or camera scan.",
                ],
                [
                    "Collection and wishlist",
                    "Purchases added automatically (opt-out)",
                    "Search in your catalogue and online sources",
                    "Albums proposed by customers are moderated",
                ],
                "shop_portal_library.png",
                reverse=True,
            ),
            feature(
                "Customer dashboard",
                "Their collection, in numbers",
                [
                    "Customers see how many albums and series they own, their complete series, reading progress, "
                    "favourite genres and their best-rated series.",
                ],
                ["Personal statistics", "Best-rated series", "Recent additions"],
                "shop_portal_dashboard.png",
                dark=True,
            ),
            feature(
                "Add a comic",
                "Scan the barcode with the phone",
                [
                    "To add an album bought elsewhere, customers scan its ISBN with their phone camera, or type it. "
                    "Odoo searches your catalogue first, then Google Books, Open Library and the BnF.",
                ],
                ["Camera scan (HTTPS)", "Manual entry fallback", "Covers from trusted sources only"],
                "shop_portal_add.png",
                reverse=True,
            ),
            feature(
                "Wishlist",
                "Gift ideas, shared in one link",
                [
                    "A customer creates a secret link to their wishlist and sends it to friends and family: a read-only "
                    "page with the covers and a link to each album on sale in your shop. The link can be revoked at "
                    "any time.",
                ],
                ["Read-only, no account needed", "Links to your products", "Revocable"],
                "shop_wishlist_public.png",
                dark=True,
            ),
            addons(
                "Works hand in hand with",
                [
                    (
                        "fa-th-large",
                        "Comic Collection",
                        "comics_collections",
                        "The free core (LGPL-3): series, albums, authors, personal libraries, wishlist, loans and import. Required.",
                    ),
                    (
                        "fa-cloud-download",
                        "Data sources",
                        "comic_datasource",
                        "Free (LGPL-3): covers and metadata from Google Books, Open Library and the BnF. Required.",
                    ),
                    (
                        "fa-magic",
                        "AI discovery (paid add-on)",
                        "comic_ai + comic_ai_shop",
                        "Customers discover new series from the ones they rated 4★ — with a daily limit to control costs.",
                    ),
                ],
            ),
            feature(
                "AI add-on",
                "Recommendations your customers will love",
                [
                    "With <b>comic_ai</b>, customers get 10 to 15 series suggestions based on their favourites, can "
                    "check each one against the data sources, and add them to their wishlist.",
                ],
                ["Taste profile from 4★ albums", "Excludes what they already have", "Daily limit per customer"],
                "shop_portal_discover.png",
                reverse=True,
            ),
            tech(
                "Technical information",
                [
                    ("Odoo version", "19.0 — Community and Enterprise"),
                    (
                        "Dependencies",
                        "comics_collections, comic_datasource, sale, website, website_sale, point_of_sale, portal",
                    ),
                    ("License", "OPL-1 (Odoo Proprietary License) — the free core modules are LGPL-3"),
                    (
                        "Reinstall-safe",
                        "Album ↔ product links are restored automatically when the module is reinstalled",
                    ),
                    ("Interface language", "French"),
                    ("Quality", "Automated test suite, pre-commit, OCA guidelines"),
                ],
                SUPPORT,
            ),
        ]
    )


if __name__ == "__main__":
    root = Path(sys.argv[1])
    (root / "comics_collections/static/description/index.html").write_text(collection_page(), encoding="utf-8")
    (root / "comic_shop/static/description/index.html").write_text(shop_page(), encoding="utf-8")
    print("ok")
