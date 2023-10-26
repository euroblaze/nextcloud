import requests
import logging

from odoo import _, fields, models, api
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)


class NextCloudFolderMapping(models.Model):
    _name = 'nextcloud.folder.mapping'
    _description = 'NextCloud Folder Mapping'
    _order = 'sequence'

    name = fields.Char(string='Folder name', required=True)
    company_id = fields.Many2one('res.company', required=True)
    domain = fields.Text(default='[]', required=True)
    model_name = fields.Selection(selection='_list_all_models', string='Model', required=True)
    sequence = fields.Integer(default=10)

    @api.model
    def _list_all_models(self):
        self._cr.execute('SELECT model, name FROM ir_model ORDER BY name')
        return self._cr.fetchall()

    # @api.constrains('name')
    # def _constrains_folder_name(self):
    #     special_characters = "!@#$%^&*()-+?_=,<>/"
    #     for rec in self:
    #         if rec.name and rec.name[0] in special_characters:
    #             raise ValidationError(_('The first character must be alphanumberic!'))

    @api.model_create_multi
    def create(self, vals_list):
        mappings = super(NextCloudFolderMapping, self).create(vals_list)
        mappings.send_request_create_folder_nextcloud()
        return mappings

    def write(self, vals):
        result = super(NextCloudFolderMapping, self).write(vals)
        if 'name' in vals:
            self.send_request_create_folder_nextcloud()
        return result

    def send_request_create_folder_nextcloud(self):
        for mapping in self:
            try:
                nextcloud_params = mapping.company_id.get_nextcloud_information()
                url = nextcloud_params.get('nextcloud_url')
                username = nextcloud_params.get('nextcloud_username')
                password = nextcloud_params.get('nextcloud_password')
                head = {'OCS-APIRequest': 'true'}
                mkcol_url = url + f'/remote.php/dav/files/{username}/{mapping.name}'
                response = requests.request('MKCOL', mkcol_url, headers=head, auth=(username, password))
                if response.status_code == 201:
                    _logger.info('Create folder on NextCloud success!')
                else:
                    _logger.error('Create folder on NextCloud failed! Err: %s' % response.text)
            except Exception as err:
                _logger.error('Create folder on NextCloud failed! Err: %s' % err)