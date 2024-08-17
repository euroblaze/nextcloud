import base64
import requests
import logging
import xml.etree.ElementTree as ET
from urllib.parse import unquote

from odoo import _, fields, models, api
from odoo.exceptions import ValidationError, AccessError

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
                                             ('username', '=', username)], limit=1).id
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
        folder_data = self.search_read(domain + [('folder', '=', True)], fields=[],
                                       order="id asc, parent_id, folder_name")
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

    @api.model
    def download_folder_from_nextcloud(self, folder, res_model, res_id, **kwargs):
        folder = self.env['nextcloud.folder'].search([('id', '=', folder)])
        company_id = self.env.user.company_id.sudo()
        folder_name = folder['name']
        path_parts = folder_name.split('/')
        nextcloud_params = company_id.get_nextcloud_information()
        url = nextcloud_params.get('nextcloud_url')
        username = nextcloud_params.get('nextcloud_username')
        password = nextcloud_params.get('nextcloud_password')
        _logger.info("====== Folder" + str(folder))
        download_url = url + f"/remote.php/dav/files/{username}/{folder_name}"
        payload = '''<?xml version="1.0" encoding="UTF-8"?>
        <d:propfind xmlns:d="DAV:">
        <d:prop xmlns:oc="http://owncloud.org/ns">
            <d:resourcetype/>
            <d:getcontenttype/>
            <oc:fileid/>
        </d:prop>
        </d:propfind>'''
        request_header = {
            'OCS-APIRequest': 'true',
            'Depth': '10000'
        }
        get_folder_response = requests.request("PROPFIND", download_url, headers=request_header,
                                               data=payload, auth=(username, password))
        xml_data = get_folder_response.content.decode("utf-8")
        root = ET.fromstring(xml_data)
        root_response = root.findall('.//{DAV:}response')
        parent_root_response = root_response[0]
        parent_folder_name = path_parts[-1]
        parent_folder_vals = {
            'name': parent_folder_name,
            'res_id': int(res_id),
            'res_model': res_model,
            'x_is_folder': True,
            'mimetype': 'document/folder',
            'type': 'folder',
            'nextcloud_attachment': True
        }
        channel_partner = self.env['mail.channel.partner']
        try:
            if channel_partner.env.user.share:
                # Only generate the access token if absolutely necessary (= not for internal user).
                parent_folder_vals['access_token'] = channel_partner.env['ir.attachment']._generate_access_token()
            folder_id = self.env['ir.attachment'].create(parent_folder_vals)
            folder_id._post_add_create()
            folderData = {
                'name': folder_id.name,
                'id': folder_id.id,
                'size': 0,
                'mimetype': folder_id.mimetype
            }
            folder_document_id = channel_partner.env['document.folder'].create({
                'x_name': folderData['name'],
                'x_parent_folder_id': False,
                'x_linked_attachment': folder_id.id,
                'x_document_folder_path': folderData['name']
            })
            folder_id['x_link_document_folder_id'] = folder_document_id.id
            ufiles_folder = {}
            for response in root_response[1:]:
                href = unquote(response.find('{DAV:}href').text)
                if href[-1] != '/':
                    file_download_url = url + href
                    file_response = requests.get(file_download_url, auth=(username, password))
                    if file_response.status_code != 200:
                        ufiles_folder = {}
                        break
                    # file_href = href.get
                    ufiles_folder[href.replace(
                        f'/remote.php/dav/files/{username}/{folder_name[0:folder_name.index(path_parts[-1])]}',
                        '')] = file_response
                else:
                    pass
            self.generate_folder_hierarchy_nc(folder_document_id, ufiles_folder, int(res_id), res_model)
            if not folder_id.datas:
                self.env['document.folder'].sudo().document_folder_zip(folder_id.id)
        except AccessError:
            folderData = {'error': _("You are not allowed to upload an attachment here.")}

    def create_file(self, parent_folder, ufile, file_path, file_name, original_folder_id, res_id, res_model):
        try:
            # Check if the file is a BytesIO object
            # if isinstance(ufile.stream, io.BytesIO):
            #     file_content = ufile.stream.read()  # Read the file content from the stream
            # else:
            file_content = ufile.content  # Read the file content

            # Convert the file content to base64 for storage
            file_base64 = base64.b64encode(file_content)

            vals = {
                'name': file_name,
                'datas': file_base64,  # Store the base64-encoded content
                'x_document_folder_id': parent_folder.id,
                'x_original_folder_id': original_folder_id,
                'x_document_folder_path': file_path,
            }
            return self.env['ir.attachment'].create(vals)
        except Exception as e:
            _logger.error(f"Error creating file: {file_name}, Error: {e}")
            return False

    def generate_folder_hierarchy_nc(self, parent_folder_id, files_list, res_id, res_model):
        if not (parent_folder_id and files_list):
            return False

        try:
            parent_folder_id['x_sequence_folder'] = 0
            parent_folder_id['x_original_folder_id'] = parent_folder_id.id
            parent_folder_id['x_res_id'] = res_id
            parent_folder_id['x_res_model'] = res_model
            for ufile_k, ufile_v in files_list.items():
                f_path = ufile_k
                path_items = f_path.split('/')
                file_name = path_items.pop()  # Extract the file name
                parent_folder = parent_folder_id

                for sequence, item in enumerate(path_items[1:]):
                    # Check if the folder already exists
                    exist_folder = self.env['document.folder'].search([
                        ('x_name', '=', item),
                        ('x_sequence_folder', '=', sequence + 1),
                        ('x_parent_folder_id', '=', parent_folder.id)
                    ], limit=1)

                    if not exist_folder:
                        # Create a new folder if it doesn't exist
                        document_subfolder = self.env['document.folder'].create({
                            'x_name': item,
                            'x_sequence_folder': sequence + 1,
                            'x_parent_folder_id': parent_folder.id,
                            'x_original_folder_id': parent_folder_id.id,
                            'x_document_folder_path': parent_folder.x_document_folder_path + f'/{item}',
                            'x_res_id': res_id,
                            'x_res_model': res_model
                        })
                    else:
                        document_subfolder = exist_folder

                    # Update the parent folder reference for the next iteration
                    parent_folder = document_subfolder

                # Create the file in the final folder
                self.create_file(parent_folder, ufile_v, ufile_k, file_name, parent_folder_id.id, res_id, res_model)
        except Exception as e:
            _logger.error(f"Error generating folder hierarchy: {e}")
            return False
