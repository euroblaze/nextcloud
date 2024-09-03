import base64
import logging
import requests

from odoo import fields, models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class IrAttachments(models.Model):
    _inherit = 'ir.attachment'

    nextcloud_attachment = fields.Boolean(string="Nextcloud Attachment", readonly="True")
    nextcloud_view_link = fields.Char(string="Nextcloud View Link")
    nextcloud_share_link = fields.Char(string="Nextcloud Share Link")
    nextcloud_folder_id = fields.Many2one("nextcloud.folder", string="Nextcloud Folder")

    # Non NC Document Folder
    x_document_folder_id = fields.Many2one("document.folder", string="Parent Folder", ondelete="cascade")
    x_link_document_folder_id = fields.Many2one("document.folder", string="Document Folder Link", ondelete="cascade")
    x_is_folder = fields.Boolean(string="Is Folder", default=False)
    x_original_folder_id = fields.Integer(string="Original Folder Id", store=True)
    x_document_folder_path = fields.Char(string="Path", store=True)
    type = fields.Selection(selection_add=[("folder", "Folder")], ondelete={'folder': 'cascade'})

    # NOTE: not delete nextcloud file when delete ir.attachment
    # def unlink(self):
    #     nextcloud_attachments = self.filtered(lambda l: l.nextcloud_attachment)
    #     if nextcloud_attachments:
    #         head = {'OCS-APIRequest': 'true'}
    #         for record in nextcloud_attachments:
    #             nextcloud_params = record.company_id.sudo().get_nextcloud_information()
    #             username = nextcloud_params.get('nextcloud_username')
    #             password = nextcloud_params.get('nextcloud_password')
    #             url = record.nextcloud_share_link
    #             delete_file = requests.delete(
    #                 url,
    #                 headers=head,
    #                 auth=(username, password)
    #             )
    #             logging.info("Delete NextCloud: %s Status %s " % (url, delete_file))
    #     return super().unlink()

    def request_upload_file_nextcloud(self, folder_id=False):
        self.ensure_one()
        NextcloudEnv = self.env['nextcloud.folder']
        company = self.company_id.sudo()
        nextcloud_params = company.get_nextcloud_information(
            res_model=self.res_model, res_id=self.res_id)
        if 'folder_mapping' not in nextcloud_params.keys():
            res_model = self._context.get('res_model', False)
            res_id = int(self._context.get('res_id', 0))
            if res_id and res_model:
                nextcloud_params = company.get_nextcloud_information(
                    res_model=res_model, res_id=res_id)
        url = nextcloud_params.get('nextcloud_url')
        username = nextcloud_params.get('nextcloud_username')
        password = nextcloud_params.get('nextcloud_password')
        folder_mapping = nextcloud_params.get('folder_mapping')
        origin_url = url + f'/remote.php/dav/files/{username}/'
        path_arr = [self.name]
        if not folder_id:
            folder = nextcloud_params.get('nextcloud_folder_id')
            folder_id = folder.id
        else:
            folder_id = int(folder_id)
            folder = NextcloudEnv.browse(folder_id).name
        if folder:
            path_arr.insert(0, folder)
        file_path = '/'.join(path_arr)
        head = {'OCS-APIRequest': 'true'}
        exist, index = False, 1

        while not exist:
            get_url = origin_url + file_path
            get_call = requests.get(get_url, headers=head, auth=(username, password))
            if get_call.status_code == 200:
                file_path = '(%s).'.join(file_path.rsplit('.', 1)) % str(index)
                index += 1
            else:
                exist = True
        share_url = origin_url + file_path
        file_data = base64.b64decode(self.datas)
        response = requests.put(share_url, headers=head, auth=(username, password), data=file_data)
        if response.status_code == 201:
            attachmentData = {
                'nextcloud_attachment': True,
                'nextcloud_share_link': share_url,
                'nextcloud_folder_id': folder_id
            }
            self.write(attachmentData)
            del attachmentData['nextcloud_folder_id']
            company.send_request_get_folder(origin_url, file_path, username, password)
            if folder_mapping:
                folder_mapping.write({'nextcloud_folder_id': folder_id})
        else:
            attachmentData = {'error': _("Cannot upload file to NextCloud.")}
        return attachmentData

    @api.model
    def send_request_create_folder_nextcloud(self, folder_id=False):
        self.ensure_one()
        NextcloudEnv = self.env['nextcloud.folder']
        company = self.company_id.sudo()

        nextcloud_params = company.get_nextcloud_information(res_model=self.res_model, res_id=self.res_id)
        username = nextcloud_params.get('nextcloud_username')
        password = nextcloud_params.get('nextcloud_password')
        folder_mapping = nextcloud_params.get('folder_mapping')
        url = nextcloud_params.get('nextcloud_url')
        head = {'OCS-APIRequest': 'true'}

        origin_url = f"{url}/remote.php/dav/files/{username}"
        uploaded_folder = self.x_link_document_folder_id
        path_arr = [uploaded_folder.x_document_folder_path]

        if not folder_id:
            folder = nextcloud_params.get('nextcloud_folder_id')
            folder_id = folder.id
        else:
            folder_id = int(folder_id)
            folder = NextcloudEnv.browse(folder_id).name

        if folder:
            path_arr.insert(0, folder)

            if path_arr[0].split('/')[-1] == path_arr[1].split('/')[0]:
                path_arr[1] = uploaded_folder.x_name

        folder_path = self._get_unique_folder_path(origin_url, path_arr, head, username, password)

        share_mkcol_url = f"{origin_url}/{folder_path}"
        response = requests.request('MKCOL', share_mkcol_url, headers=head, auth=(username, password))

        if response.status_code == 201:
            attachmentData = {
                'nextcloud_attachment': True,
                'nextcloud_share_link': share_mkcol_url,
                'nextcloud_folder_id': folder_id
            }
            self.write(attachmentData)
            if folder != '/':
                origin_url += '/'
            company.send_request_get_folder(origin_url, folder_path, username, password)
            if folder_mapping:
                folder_mapping.write({'nextcloud_folder_id': folder_id})
            parent_nc_folder = NextcloudEnv.search(
                [('name', '=', folder_path if folder != '/' else uploaded_folder.x_document_folder_path)], limit=1)
            if uploaded_folder.x_child_file_ids:
                self._create_nc_files(parent_nc_folder.id, uploaded_folder)
            if uploaded_folder.x_child_folder_ids:
                self._create_nested_folders(folder, folder_id, origin_url, uploaded_folder.x_child_folder_ids, {
                    'username': username,
                    'password': password,
                    'header': head
                }, folder_mapping)
        else:
            attachmentData = {'error': _("Cannot upload file to NextCloud.")}

        return attachmentData

    def _get_unique_folder_path(self, origin_url, path_arr, head, username, password):
        """Generates a unique folder path in NextCloud."""
        folder_path = '/'.join(path_arr)
        index = 1
        while True:
            get_url = f"{origin_url}/{folder_path}"
            get_call = requests.get(get_url, headers=head, auth=(username, password))
            if get_call.status_code != 200:
                break
            folder_path = f"({index}).".join(folder_path.rsplit('.', 1))
            index += 1
        return folder_path

    def _create_nested_folders(self, nc_folder, nc_folder_id, origin_url, child_folders, authen_params, folder_mapping):
        """Creates nested folders recursively in NextCloud."""
        for folder in child_folders:
            path_arr = [nc_folder, folder.x_document_folder_path]
            folder_path = self._get_unique_folder_path(origin_url, path_arr, authen_params['header'],
                                                       authen_params['username'], authen_params['password'])

            share_mkcol_url = f"{origin_url}/{folder_path}"
            response = requests.request('MKCOL', share_mkcol_url, headers=authen_params['header'],
                                        auth=(authen_params['username'], authen_params['password']))

            if response.status_code == 201:
                self.company_id.sudo().send_request_get_folder(origin_url, folder_path, authen_params['username'],
                                                               authen_params['password'])
                if folder_mapping:
                    folder_mapping.write({'nextcloud_folder_id': nc_folder_id})
                nc_current_folder = self.env['nextcloud.folder'].search(
                    [('name', '=', folder_path if nc_folder != '/' else folder.x_document_folder_path)],
                    limit=1)
                if folder.x_child_file_ids:
                    self._create_nc_files(nc_current_folder.id, folder)
                if folder.x_child_folder_ids:
                    self._create_nested_folders(nc_folder, nc_folder_id, origin_url, folder.x_child_folder_ids,
                                                authen_params, folder_mapping)
                else:
                    pass
            else:
                _logger.error(_("Cannot upload folder to NextCloud."))

    def _create_nc_files(self, parent_nc_folder, document_folder):
        if parent_nc_folder and document_folder.x_child_file_ids:
            for file in document_folder.x_child_file_ids:
                file.with_context(res_id=document_folder.x_res_id,
                                  res_model=document_folder.x_res_model).request_upload_file_nextcloud(parent_nc_folder)
