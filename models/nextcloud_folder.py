import base64
import requests
import logging
import xml.etree.ElementTree as ET
from urllib.parse import unquote
from odoo import _, fields, models, api
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)


class NextCloudFolder(models.Model):
    _name = 'nextcloud.folder'
    _description = 'NextCloud Folder'

    name = fields.Char(string='Full Path', required=True)
    folder_name = fields.Char(string='Folder/File Name',
                              compute='_compute_parent_id', store=True)
    etag = fields.Char(string='ETag', required=False)
    company_id = fields.Many2one('res.company', required=True,
                                 default=lambda self: self.env.company)
    parent_id = fields.Many2one('nextcloud.folder', 'Parent Folder',
                                compute='_compute_parent_id', store=True)
    child_ids = fields.One2many('nextcloud.folder', 'parent_id', 'Childs')
    sequence = fields.Integer(default=10)
    folder = fields.Boolean()
    file_type = fields.Char()
    username = fields.Char()
    active = fields.Boolean(default=True)

    @api.depends('name')
    def _compute_parent_id(self):
        company = self.env.user.company_id.sudo()
        username = company.nextcloud_username
        for rec in self:
            parent_id, folder_name = False, False
            if rec.name == '/':
                folder_name = rec.name
            elif rec.name:
                split_arr = rec.name.split('/')
                if len(split_arr) > 1:
                    parent = self.search([
                        ('name', '=', '/'.join(split_arr[:-1])),
                        ('username', '=', username)], limit=1)
                    if parent:
                        parent_id = parent.id
                    folder_name = split_arr[-1]
                else:
                    folder_name = rec.name
                    parent_id = self.search([('name', '=', '/'),
                                             ('username', '=', username)],limit=1).id
            rec.parent_id = parent_id
            rec.folder_name = folder_name

    # @api.model_create_multi
    # def create(self, vals_list):
    #     files = super(NextCloudFolder, self).create(vals_list)
    #     if not self._context.get('sync_nextcloud', False):
    #         files.send_request_create_folder_nextcloud()
    #     return files

    # def write(self, vals):
    #     result = super(NextCloudFolder, self).write(vals)
    #     if 'name' in vals and not self._context.get('sync_nextcloud', False):
    #         self.send_request_create_folder_nextcloud()
    #     return result

    @api.model
    def get_master_data(self, domain, **kwargs):
        values = {}
        res_model = kwargs.get('res_model', False)
        res_id = kwargs.get('res_id', False)
        company = self.env.user.company_id.sudo()
        domain += [('username', '=', company.nextcloud_username)]
        data = self.search_read(domain, fields=[], order="folder, id, parent_id, folder_name")
        folder_data = self.search_read(domain + [('folder', '=', True)], fields=[], order="id asc, parent_id, folder_name")
        nextcloud_params = company.get_nextcloud_information(
            res_model=res_model, res_id=res_id)
        nextcloud_folder_id = nextcloud_params.get('nextcloud_folder_id')
        if nextcloud_folder_id:
            default_folder = nextcloud_folder_id.read()[0]
        else:
            default_folder = folder_data[0] if len(folder_data) > 1 else []
        values.update({
            'data': data,
            'folder_data': folder_data,
            'default_folder': default_folder
        })

        return values

    @api.model
    def download_file_from_nextcloud(self, files, res_model, res_id, **kwargs):
        for file in files:
            company_id = file.get('company_id')[0]
            filename = file['name']
            nextcloud_params = self.env['res.company'].sudo().browse(company_id).get_nextcloud_information()
            url = nextcloud_params.get('nextcloud_url')
            username = nextcloud_params.get('nextcloud_username')
            password = nextcloud_params.get('nextcloud_password')
            _logger.info("======" + str(file))
            download_url = url + f"/remote.php/dav/files/{username}/{filename}"
            auth = (username, password)

            response = requests.get(download_url, auth=auth)
            if response.status_code == 200:
                # File content is in response.text
                values = {
                    'name': filename,
                    'nextcloud_attachment': True,
                    'res_id': res_id,
                    'res_model': res_model,
                    'company_id': company_id,
                    'nextcloud_share_link': download_url,
                    'nextcloud_folder_id': file['id'],
                    'datas': base64.b64encode(response.content)
                }
                attachment = self.env['ir.attachment'].create(values)
                _logger.info(f"File {attachment.name} downloaded successfully.")
            else:
                _logger.error(f"Failed to download file. Status code: {response.status_code}")
                print(response.text)
