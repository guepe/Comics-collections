{
    "name": "Comic Shop",
    "version": "19.0.5.1.0",
    "category": "Website/eCommerce",
    "summary": "Sell comics online and at the POS: albums synced with products, series / author / "
    "publisher shop pages, customer library on the portal, series follow-up and release e-mails",
    "description": """
Comic Shop — the commercial layer of Comic Collection.

Albums linked to products (name, cover, description, ISBN barcode kept in sync),
bulk product creation per series, webshop pages for series, authors and publishers,
a personal comic library for every customer on the portal (collection, wishlist,
ratings, dashboard, ISBN camera scan, shareable wishlist), purchases added
automatically, series follow-up with "now available" e-mails, and moderation of
the albums customers propose.
""",
    "author": "Belspace",
    "maintainers": ["guepe"],
    "website": "https://github.com/guepe/Comics-collections",
    "support": "ph.delaval@gmail.com",
    "license": "OPL-1",
    "price": 200.00,
    "currency": "EUR",
    "development_status": "Beta",
    "images": ["static/description/banner.png"],
    "depends": [
        "comics_collections",
        "comic_datasource",
        "sale",
        "website",
        "website_sale",
        "point_of_sale",
        "portal",
    ],
    "data": [
        "security/comic_shop_security.xml",
        "security/ir.model.access.csv",
        "data/comic_shop_data.xml",
        "data/comic_shop_server_actions.xml",
        "data/comic_release_mail_template.xml",
        "views/comic_portal_refuse_wizard_views.xml",
        "views/comic_release_notify_wizard_views.xml",
        "views/comic_serie_views.xml",
        "views/comic_edition_views.xml",
        "views/comic_work_views.xml",
        "views/comic_customer_album_views.xml",
        "views/product_template_views.xml",
        "views/website_sale_templates.xml",
        "views/website_sale_shop_templates.xml",
        "views/portal_library_templates.xml",
        "views/portal_series_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "comic_shop/static/src/css/comic_shop.css",
            "comics_collections/static/src/isbn_scan/isbn_scan_dialog.js",
            "comics_collections/static/src/isbn_scan/isbn_scan_dialog.xml",
            "comic_shop/static/src/js/portal_isbn_scan.js",
            "comic_shop/static/src/js/portal_wishlist_copy.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
}
