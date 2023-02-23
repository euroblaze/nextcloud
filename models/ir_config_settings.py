from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = ['res.config.settings']

    nextcloud_url = fields.Char(string="Nextcloud URL", config_parameter="bf_nextcloud.nextcloud_url")

    nextcloud_username = fields.Char(string="Nextcloud Username", config_parameter="bf_nextcloud.nextcloud_username")
    nextcloud_password = fields.Char(string="Nextcloud Password", config_parameter="bf_nextcloud.nextcloud_password",
                                     password="True")
    nextcloud_token = fields.Char(string="Nextcloud Token", config_parameter="bf_nextcloud.nextcloud_token")
