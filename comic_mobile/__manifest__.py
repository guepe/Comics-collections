{
    "name": "Comic Collection — Mobile App",
    "version": "19.0.1.0.0",
    "category": "Leisure",
    "summary": "Manage your comic collection from your phone: ISBN scanner, covers, series, wishlist",
    "description": """
Installable mobile app (PWA) served by Odoo for comic collectors: scan an ISBN in a bookshop
to know at once whether you own it or which volume you are missing, browse your collection
as a cover grid, follow your series and check your wishlist. Add it to the home screen of an
iPhone or Android phone; it uses your Odoo account and only shows your own collection.
""",
    "author": "Belspace, Odoo Community Association (OCA)",
    "website": "https://odoo.belspace.net",
    "support": "ph.delaval@gmail.com",
    "license": "LGPL-3",
    "depends": ["comics_collections", "web"],
    "data": [
        "views/comic_mobile_templates.xml",
        "views/comic_mobile_menu.xml",
    ],
    "assets": {
        "comic_mobile.assets_app": [
            ("include", "web._assets_helpers"),
            ("include", "web._assets_backend_helpers"),
            "web/static/src/scss/pre_variables.scss",
            "web/static/lib/bootstrap/scss/_variables.scss",
            "web/static/lib/bootstrap/scss/_variables-dark.scss",
            "web/static/lib/bootstrap/scss/_maps.scss",
            ("include", "web._assets_bootstrap_backend"),
            ("include", "web._assets_core"),
            ("remove", "web/static/src/core/browser/router.js"),
            ("remove", "web/static/src/core/debug/**/*"),
            "web/static/src/libs/fontawesome/css/font-awesome.css",
            "comics_collections/static/src/isbn_scan/isbn_scan_dialog.js",
            "comics_collections/static/src/isbn_scan/isbn_scan_dialog.xml",
            "comic_mobile/static/src/app/**/*",
        ],
    },
    "images": ["static/description/icon.png"],
    "installable": True,
    "application": False,
}
