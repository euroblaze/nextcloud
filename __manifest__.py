# -*- coding: utf-8 -*-
{
    'name': "NextCloud based DMS for PowerOn",
    'summary': """This module enables the decoupled (from Odoo) storage of file attachments on a separate NextCloud Server""",
    'description': """You will need a working NextCloud server to actually perform file-storage functions.""",
    'author': "Vy Vo, Ashant Chalasani, Quy Ho, Bojan Ancev",
    'website': "https://poweron.software/dms",
    'category': 'Extra Tools',
    'version': '15.0.0.5',
    'license': 'LGPL-3',
    'depends': ['base', 'account', 'mail'],
    'data': [
        'views/res_company_views.xml',
        'views/nextcloud_folder_views.xml',
        'views/ir_attachment_views.xml',
        'views/document_folder_view.xml',
        'wizard/select_nextcloud_folder_wizard_view.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'mail.assets_discuss_public': [
            'nextcloud/static/src/models/js/attachment.js',
        ],
        'web.assets_qweb': [
            'nextcloud/static/src/views/**/*.xml',
            'nextcloud/static/src/**/*.xml',
        ],
        'web.assets_backend': [
            'nextcloud/static/src/**/*.js',
            'nextcloud/static/src/views/**/*.js',
            'nextcloud/static/src/**/*.scss',
            'nextcloud/static/src/**/*.css',
        ],
    }
}
