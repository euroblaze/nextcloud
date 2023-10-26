import requests

from odoo import _, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    nextcloud_url = fields.Char(string="Nextcloud URL", groups="base.group_system")
    nextcloud_folder = fields.Char(string="Nextcloud Folder", groups="base.group_system")
    nextcloud_username = fields.Char(string="Nextcloud Username", groups="base.group_system")
    nextcloud_password = fields.Char(string="Nextcloud Password", groups="base.group_system",
                                     password="True")
    nextcloud_folder_mapping_ids = fields.One2many('nextcloud.folder.mapping', 'company_id',
                                                   'NextCloud Folder Mapping')

    def get_nextcloud_information(self, res_model=False, res_id=False):
        self.ensure_one()
        values = {
            'nextcloud_url': self.nextcloud_url,
            'nextcloud_folder': self.nextcloud_folder,
            'nextcloud_username': self.nextcloud_username,
            'nextcloud_password': self.nextcloud_password
        }
        if res_model:
            folder_mapping = self.nextcloud_folder_mapping_ids.filtered(
                lambda x: x.model_name == res_model)
            values.update({'folder_mapping': folder_mapping})
            if res_id and folder_mapping:
                for f_mapping in folder_mapping:
                    mapping_domain = eval(f_mapping.domain)
                    filter_domain = [('id', '=', res_id)] + mapping_domain
                    if self.env[res_model].search(filter_domain):
                        values.update({
                            'nextcloud_folder': f_mapping.name
                        })
                        break
        return values

    def nextcloud_test_connection(self):
        self.ensure_one()
        head = {'OCS-APIRequest': 'true'}
        url = self.sudo().nextcloud_url
        username = self.sudo().nextcloud_username
        password = self.sudo().nextcloud_password
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
