from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    nextcloud_url = fields.Char(
        config_parameter='nextcloud.nextcloud_url',
        string='Nextcloud URL'
    )

    nextcloud_username = fields.Char(
        config_parameter='nextcloud.nextcloud_username',
        string='Nextcloud Username'
    )

    nextcloud_password = fields.Char(
        config_parameter='nextcloud.nextcloud_password',
        string='Nextcloud Password'
    )

    def nextcloud_test_connection(self):
        return self.env.company.sudo().nextcloud_test_connection()
