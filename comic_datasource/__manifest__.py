{
    "name": "Comic Datasource",
    "version": "19.0.1.0.0",
    "category": "Leisure",
    "summary": "Connecteur multi-sources pour enrichir les fiches BD",
    "description": """
        Agrège plusieurs sources de données pour les bandes dessinées :
        - Google Books API (clé API gratuite)
        - Open Library API (sans clé)
        - BnF SRU API (sans clé, dépôt légal)
    """,
    "author": "Belspace, OCA",
    "maintainers": ["guepe"],
    "website": "https://github.com/Belspace/Comics-collections",
    "license": "LGPL-3",
    "development_status": "Beta",
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
        "python": ["requests", "beautifulsoup4", "lxml", "xmltodict"],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
