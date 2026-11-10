{
    "name": "Comic Datasource",
    "version": "19.0.1.5.1",
    "category": "Productivity",
    "summary": "Covers and metadata for your comics from Google Books, Open Library and the BnF: "
    "one-click completion, search & import, missing volumes detection",
    "description": """
Comic Datasource — fills in your comic catalogue automatically.

Covers, synopses, page counts, publication dates, publishers and authors from Google
Books, Open Library and the BnF (French legal deposit), merged field by field. Only
empty fields are filled — your own data is never overwritten. One-click *Compléter les
infos* on an album, search and import wizard, series update, detection of the missing
volumes of followed series, optional nightly jobs.
""",
    "author": "Belspace",
    "maintainers": ["guepe"],
    "website": "https://odoo.belspace.net",
    "support": "ph.delaval@gmail.com",
    "license": "LGPL-3",
    "development_status": "Beta",
    "images": ["static/description/banner.png"],
    "depends": ["comics_collections"],
    "data": [
        "security/ir.model.access.csv",
        "views/comic_datasource_config_views.xml",
        "views/comic_datasource_wizard_views.xml",
        "views/comic_edition_inherit_views.xml",
        "views/comic_datasource_serie_inherit_views.xml",
        "views/comic_serie_missing_wizard_views.xml",
        "views/comic_datasource_menu.xml",
        "data/comic_datasource_config.xml",
        "data/comic_serie_cron.xml",
    ],
    "external_dependencies": {
        "python": ["requests", "lxml", "xmltodict"],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
