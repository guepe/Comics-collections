{
    'name': 'Comic Shop',
    'version': '19.0.2.0.0',
    'category': 'Leisure',
    'summary': 'Vendez vos BD en ligne et gérez la bibliothèque de vos clients',
    'description': """
        Extension commerciale de Comic Collection.
        Lien album ↔ produit, webshop BD, caisse (POS) et bibliothèque client sur le portail.
    """,
    'author': 'Belspace',
    'maintainer': 'Belspace',
    'support': 'sales@belspace.net',
    'website': 'https://guepe.github.io',
    'license': 'LGPL-3',
    'depends': [
        'comics_collections',
        'comic_datasource',
        'sale',
        'website',
        'website_sale',
        'point_of_sale',
        'portal',
    ],
    'data': [
        'security/comic_shop_security.xml',
        'security/ir.model.access.csv',
        'data/comic_shop_data.xml',
        'data/comic_shop_server_actions.xml',
        'views/comic_serie_views.xml',
        'views/comic_edition_views.xml',
        'views/comic_customer_album_views.xml',
        'views/product_template_views.xml',
        'views/website_sale_templates.xml',
        'views/website_sale_shop_templates.xml',
        'views/portal_library_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'comic_shop/static/src/css/comic_shop.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'uninstall_hook': 'uninstall_hook',
}
