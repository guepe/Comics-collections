{
    "name": "Comic Collection",
    "version": "19.0.2.0.0",
    "category": "Leisure",
    "summary": "Gérez votre collection de bandes dessinées",
    "description": """
        Module de gestion de collection de bandes dessinées.
        Gérez vos séries, albums, auteurs, éditeurs et prêts.
    """,
    "author": "Belspace",
    "maintainer": "Belspace",
    "support": "sales@belspace.net",
    "website": "https://guepe.github.io",
    "license": "LGPL-3",
    "depends": ["base", "mail", "contacts"],
    "data": [
        "security/comic_security.xml",
        "security/ir.model.access.csv",
        "data/comic_genre_data.xml",
        "data/comic_cron_data.xml",
        "data/comic_server_actions.xml",
        "views/comic_genre_views.xml",
        "views/comic_editeur_views.xml",
        "views/comic_auteur_views.xml",
        "views/comic_serie_views.xml",
        "views/comic_work_views.xml",
        "views/comic_edition_views.xml",
        "views/comic_pret_views.xml",
        "views/comic_import_wizard_views.xml",
        "views/comic_dedup_views.xml",
        "views/comic_menu.xml",
        "views/comic_fonts_template.xml",
    ],
    "demo": [
        "demo/comic_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "comics_collections/static/src/scss/comics_theme.scss",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}
