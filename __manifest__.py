# -*- coding: utf-8 -*-
{
    'name': "NextCloud Integration",
    'summary': """NextCloud Integration Module""",
    'description': """NextCloud Integration add the buttons to upload and link Nextcloud files""",
    'author': "Simplify-ERP®",
    'website': "https://simplify-erp.com/",
    'category': 'Extra Tools',
    'version': '1.0',
    'license': 'LGPL-3',
    'depends': ['nextcloud', 'documents'],
    'data': [
        'views/documents_document.xml'
    ],
    'assets': {
        'web.assets_qweb': [
            'bf_nextcloud/static/src/**/*.xml',
        ],
        'web.assets_backend': [
            'bf_nextcloud/static/src/**/*.js'
        ],
    }
}
