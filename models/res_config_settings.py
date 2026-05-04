"""Nextcloud settings.

V18: store credentials per `res.company` (real multi-company), not
in `ir.config_parameter`.
"""
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    nextcloud_url = fields.Char(
        related='company_id.nextcloud_url',
        readonly=False,
        string='Nextcloud URL',
    )
    nextcloud_username = fields.Char(
        related='company_id.nextcloud_username',
        readonly=False,
        string='Nextcloud Username',
    )
    nextcloud_password = fields.Char(
        related='company_id.nextcloud_password',
        readonly=False,
        string='Nextcloud App-Password',
    )
    nextcloud_folder_id = fields.Many2one(
        related='company_id.nextcloud_folder_id',
        readonly=False,
        string='Nextcloud Default Folder',
    )

    def nextcloud_test_connection(self):
        return self.env.company.sudo().nextcloud_test_connection()
