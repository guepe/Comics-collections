{
    "name": "Comic AI",
    "version": "19.0.1.0.0",
    "category": "Leisure",
    "summary": "AI assistance for comic records: synopsis, translation, discovery (Claude / OpenAI)",
    "author": "Belspace, OCA",
    "maintainers": ["guepe"],
    "website": "https://github.com/Belspace/Comics-collections",
    "license": "LGPL-3",
    "development_status": "Beta",
    "depends": ["comics_collections", "comic_datasource"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "wizards/comic_ai_wizard_views.xml",
        "views/comic_ai_buttons_views.xml",
    ],
    # Bibliothèques importées à la demande (message clair si absentes) : le module
    # s'installe sans elles. Voir comic.ai.service._import_sdk().
    "installable": True,
    "application": False,
    "auto_install": False,
}
