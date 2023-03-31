# -*- coding: utf-8 -*-
{
    'name': "NextCloud",
    'summary': """NextCloud""",
    'description': """NextCloud""",
    'author': "Simplify-ERP®",
    'website': "https://simplify-erp.com/",
    'category': 'Extra Tools',
    'version': '1.0',
    'license': 'LGPL-3',
    'depends': ['base', 'account', 'mail'],
    'data': [
        'views/settings_view.xml',
        'views/ir_attachments.xml',
    ],
    'assets': {
        'web.assets_qweb': [
            'nextcloud/static/src/**/*.xml',
        ],
        'web.assets_backend': [
            'nextcloud/static/src/**/*.js',
            'nextcloud/static/src/**/*.scss',
        ],
    }
}
