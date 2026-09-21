{
    "name": "Comic Datasource",
    "version": "19.0.1.0.0",
    "category": "Leisure",
    "summary": "Multi-source connector to enrich comic book records",
    "description": """
        Aggregates multiple data sources for comic books:
        - Google Books API (free API key)
        - Open Library API (no key required)
        - BnF SRU API (no key required, French legal deposit)
    """,
    "author": "Belspace, OCA",
    "maintainers": ["guepe"],
    "website": "https://github.com/Belspace/Comics-collections",
    "license": "LGPL-3",
    "development_status": "Beta",
    "images": ["static/description/overview.png"],
    "depends": ["comics_collections"],
    "price":40.00,
    "currency": "EUR",
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
        "python": ["requests", "beautifulsoup4", "lxml", "xmltodict"],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
