{
    "name": "Comic Collection",
    "version": "19.0.4.4.0",
    "category": "Productivity",
    "summary": "Your comic, manga & graphic-novel collection in Odoo: series, missing volumes, "
    "wishlist, loans, ISBN scan, dashboard and collection value",
    "description": """
Comic Collection — manage a comic book (BD), manga and comics collection in Odoo.

Series and albums with covers, authors and publishers; a private library per user
(collection, wishlist, reading status, star ratings, purchase price and estimated
value); automatically followed series with their missing volumes; loans with
overdue reminders; CSV / Excel import with duplicate detection; ISBN camera scan;
dashboard, CSV export and PDF inventory.
""",
    "author": "Belspace",
    "maintainers": ["guepe"],
    "website": "https://odoo.belspace.net",
    "support": "ph.delaval@gmail.com",
    "license": "LGPL-3",
    "development_status": "Beta",
    "images": ["static/description/banner.png"],
    "depends": ["base", "mail", "contacts"],
    "data": [
        "security/comic_security.xml",
        "security/ir.model.access.csv",
        "data/comic_genre_data.xml",
        "data/comic_cron_data.xml",
        "data/comic_config_data.xml",
        "data/comic_server_actions.xml",
        "views/comic_genre_views.xml",
        "views/comic_editeur_views.xml",
        "views/comic_auteur_views.xml",
        "views/comic_serie_views.xml",
        "views/comic_work_views.xml",
        "views/comic_edition_views.xml",
        "views/comic_pret_views.xml",
        "views/comic_customer_album_views.xml",
        "views/comic_import_wizard_views.xml",
        "views/comic_dedup_views.xml",
        "views/comic_dashboard_views.xml",
        "views/comic_wishlist_views.xml",
        "views/comic_menu.xml",
        "views/comic_wishlist_menu.xml",
        "report/report_comic_collection_inventory.xml",
        "views/comic_fonts_template.xml",
    ],
    "demo": [
        "demo/comic_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "comics_collections/static/src/scss/comics_theme.scss",
            "comics_collections/static/src/dashboard/collection_dashboard.js",
            "comics_collections/static/src/dashboard/collection_dashboard.xml",
            "comics_collections/static/src/dashboard/collection_dashboard.scss",
            "comics_collections/static/src/isbn_scan/isbn_scan_dialog.js",
            "comics_collections/static/src/isbn_scan/isbn_scan_dialog.xml",
            "comics_collections/static/src/isbn_scan/isbn_scan_field.js",
            "comics_collections/static/src/isbn_scan/isbn_scan_field.xml",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}
