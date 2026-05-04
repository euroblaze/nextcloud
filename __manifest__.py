# -*- coding: utf-8 -*-
{
    'name': "Nextcloud Attachments",
    'summary': "Store Odoo attachments on Nextcloud via WebDAV",
    'description': """
Nextcloud Attachments
=====================
Offload Odoo attachments to a Nextcloud instance over WebDAV.

* Per-company configuration with app-password authentication.
* Public API ``env['nextcloud.client']`` (mkdir / upload / download /
  ls / delete / create_public_share).
* Folder mapping per model (`nextcloud.folder.mapping`).
* Folder picker wizard (`select.nextcloud.folder.wizard`).
* **Chatter integration**: "Attach from Nextcloud" button next to the
  paperclip on every record's chatter, modal browser of the synced
  NC tree, one-click attach.
* **Upload to Nextcloud** button on the attachment form.
* Retry-aware client (exp-backoff on 5xx), `queue_job`-friendly
  (`with_delay()` available on uploads).
    """,
    'author': "Simplify-ERP®",
    'website': "https://simplify-erp.com/",
    'category': 'Extra Tools',
    'version': '18.0.1.1.0',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'web', 'base_setup'],
    'external_dependencies': {
        'python': ['webdav4'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/nextcloud_folder_views.xml',
        'views/ir_attachment_views.xml',
        'views/nextcloud_config_setting.xml',
        'views/res_company_views.xml',
        'wizard/select_nextcloud_folder_wizard_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'nextcloud/static/src/**/*.js',
            'nextcloud/static/src/**/*.xml',
            'nextcloud/static/src/**/*.scss',
        ],
    },
    'installable': True,
    'application': False,
}
