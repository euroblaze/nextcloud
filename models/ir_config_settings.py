import requests

from odoo import _, fields, models
from odoo.http import request


class ResConfigSettings(models.TransientModel):
    _inherit = ['res.config.settings']

    nextcloud_url = fields.Char(string="Nextcloud URL", config_parameter="nextcloud.nextcloud_url")
    nextcloud_username = fields.Char(string="Nextcloud Username", config_parameter="nextcloud.nextcloud_username")
    nextcloud_password = fields.Char(string="Nextcloud Password", config_parameter="nextcloud.nextcloud_password",
                                     password="True")

    def nextcloud_test_connection(self):
        head = {'OCS-APIRequest': 'true'}
        url = request.env['ir.config_parameter'].sudo().get_param('nextcloud.nextcloud_url')
        username = request.env['ir.config_parameter'].sudo().get_param('nextcloud.nextcloud_username')
        password = request.env['ir.config_parameter'].sudo().get_param('nextcloud.nextcloud_password')
        get_url = url + '/remote.php/dav/files/%s' % username
        get_call = requests.get(get_url, headers=head, auth=(username, password))
        status_code = get_call.status_code
        if status_code == 200:
            message = _("Connection Test Successful!")
            type_toast = 'success'
        else:
            message = _("Connection Test Unsuccessful!")
            type_toast = 'danger'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': type_toast,
                'sticky': False,
            }
        }
