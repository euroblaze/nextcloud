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
    'depends': ['account', 'documents', 'mail'],
    'data': [
        'views/settings_view.xml',
        'views/ir_attachments.xml',
        'views/documents_document.xml'
    ],
    'assets': {
        'web.assets_qweb': [
            'nextcloud/static/src/**/*.xml',
        ],
        'mail.assets_discuss_public': [
            'nextcloud/static/src/models/*/*.js',
            ('include', 'web._assets_helpers'),
            'mail/static/src/components/*/*',
        ],
        'web.assets_backend': [
            'nextcloud/static/src/**/*.js'
        ],
    }
}