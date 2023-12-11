# -*- coding: utf-8 -*-
{
    'name': "NextCloud Attachments",
    'summary': """NextCloud Attachments""",
    'description': """NextCloud Attachments""",
    'author': "Simplify-ERP®",
    'website': "https://simplify-erp.com/",
    'category': 'Extra Tools',
    'version': '1.0',
    'license': 'LGPL-3',
    'depends': ['base', 'account', 'mail'],
    'data': [
        'views/res_company_views.xml',
        'views/nextcloud_folder_views.xml',
        'views/ir_attachment_views.xml',
        'wizard/select_nextcloud_folder_wizard_view.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'mail.assets_discuss_public': [
            'nextcloud/static/src/models/js/attachment.js',
        ],
        'web.assets_qweb': [
            'nextcloud/static/src/view/**/*.xml',
            'nextcloud/static/src/**/*.xml',
        ],
        'web.assets_backend': [
            'nextcloud/static/src/**/*.js',
            'nextcloud/static/src/view/**/*.js',
            'nextcloud/static/src/**/*.scss',
            'nextcloud/static/src/**/*.css',
        ],
    }
}
