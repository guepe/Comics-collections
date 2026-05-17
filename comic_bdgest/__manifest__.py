{
    'name': 'Comic Collection — BDGest Connector',
    'version': '19.0.1.0.0',
    'category': 'Leisure',
    'summary': 'Scraping et import depuis BDGest / Bedetheque',
    'author': 'Belspace',
    'maintainer': 'Belspace',
    'license': 'LGPL-3',
    'depends': ['comics_collections'],
    'external_dependencies': {
        'python': ['requests', 'beautifulsoup4', 'lxml'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/comic_bdgest_enrich_wizard_views.xml',
        'views/comic_album_inherit_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
