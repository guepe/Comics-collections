{
    "name": "Comic Shop",
    "version": "19.0.2.0.0",
    "category": "Leisure",
    "summary": "Sell your comics online and manage customer libraries",
    "description": """
        Commercial extension of Comic Collection.
        Album ↔ product link, comic webshop, POS integration and customer portal library.
    """,
    "author": "Belspace, OCA",
    "maintainers": ["guepe"],
    "website": "https://github.com/Belspace/Comics-collections",
    "license": "LGPL-3",
    "development_status": "Beta",
    "images": ["static/description/overview.png"],
    "price":200.00,
    "currency": "EUR",
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
        "views/comic_serie_views.xml",
        "views/comic_edition_views.xml",
        "views/comic_customer_album_views.xml",
        "views/product_template_views.xml",
        "views/website_sale_templates.xml",
        "views/website_sale_shop_templates.xml",
        "views/portal_library_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "comic_shop/static/src/css/comic_shop.css",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "uninstall_hook": "uninstall_hook",
}
