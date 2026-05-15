{
    'name': 'Comic Collection',
    'version': '19.0.1.0.0',
    'category': 'Leisure',
    'summary': 'Gérez votre collection de bandes dessinées',
    'description': """
        Module de gestion de collection de bandes dessinées.
        Gérez vos séries, albums, auteurs, éditeurs et prêts.
    """,
    'author': 'Belspace',
    'maintainer': 'Belspace',
    'support': 'sales@belspace.net',
    'website': 'https://guepe.github.io',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'contacts'],
    'data': [
        'security/comic_security.xml',
        'security/ir.model.access.csv',
        'data/comic_genre_data.xml',
        'views/comic_genre_views.xml',
        'views/comic_editeur_views.xml',
        'views/comic_serie_views.xml',
        'views/comic_album_views.xml',
        'views/comic_import_wizard_views.xml',
        'views/comic_menu.xml',
    ],
    'demo': [
        'demo/comic_demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
