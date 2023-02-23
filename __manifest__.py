# -*- coding: utf-8 -*-
{
    'name': "BF NextCloud Integration",
    'summary': """BF NextCloud Integration Module""",
    'description': """BF NextCloud Integration add the buttons to upload and link Nextcloud files""",
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
            'bf_nextcloud/static/src/**/*.xml',
        ],
        'mail.assets_discuss_public': [
            'bf_nextcloud/static/src/models/*/*.js',
            ('include', 'web._assets_helpers'),
            'mail/static/src/components/*/*',
        ],
        'web.assets_backend': [
            'bf_nextcloud/static/src/**/*.js'
        ],
    }
}