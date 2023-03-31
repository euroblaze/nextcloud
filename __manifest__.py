# -*- coding: utf-8 -*-
{
    'name': "NextCloud Documents",
    'summary': """NextCloud Documents""",
    'description': """NextCloud Documents""",
    'author': "Simplify-ERP®",
    'website': "https://simplify-erp.com/",
    'category': 'Extra Tools',
    'version': '1.0',
    'license': 'LGPL-3',
    'depends': ['base', 'account', 'mail', 'documents'],
    'data': [
        'views/documents_document.xml',
        'views/settings_view.xml',
        'views/ir_attachments.xml'
    ],
    'assets': {
        'web.assets_qweb': [
            'bf_nextcloud/static/src/**/*.xml',
        ],
        'web.assets_backend': [
            'bf_nextcloud/static/src/**/*.js',
            'bf_nextcloud/static/src/**/*.scss',
        ],
    }
}
