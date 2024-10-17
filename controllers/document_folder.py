# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import io
import base64
import logging
from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.tools.translate import _
import re

_logger = logging.getLogger(__name__)


class DocumentFolderController(http.Controller):

    @http.route('/document/folder/upload', methods=['POST'], type='http', auth='public')
    def document_folder_upload(self, folder, thread_id, thread_model, is_pending=False, **kwargs):
        channel_partner = request.env['mail.channel.partner']
        if thread_model == 'mail.channel':
            channel_partner = request.env['mail.channel.partner']._get_as_sudo_from_request_or_raise(request=request,
                                                                                                     channel_id=int(
                                                                                                         thread_id))
        folder = json.loads(folder)
        folder_vals = {
            'name': folder.get('parentFName'),
            'res_id': int(thread_id),
            'res_model': thread_model,
            'x_is_folder': True,
            'mimetype': 'document/folder',
            'type': 'folder'
        }
        if is_pending and is_pending != 'false':
            # Add this point, the message related to the uploaded file does
            # not exist yet, so we use those placeholder values instead.
            folder_vals.update({
                'res_id': 0,
                'res_model': 'mail.compose.message',
            })
        if channel_partner.env.user.share:
            # Only generate the access token if absolutely necessary (= not for internal user).
            folder_vals['access_token'] = channel_partner.env['ir.attachment']._generate_access_token()
        try:
            folder_id = channel_partner.env['ir.attachment'].create(folder_vals)
            folder_id._post_add_create()
            folderData = {
                'name': folder_id.name,
                'id': folder_id.id,
                'size': folder.get('totalFiles'),
                'mimetype': folder_id.mimetype
            }
            folder_document_id = channel_partner.env['document.folder'].create({
                'x_name': folderData['name'],
                'x_parent_folder_id': False,
                'x_linked_attachment': folder_id.id,
                'x_document_folder_path': folderData['name']
            })
            folder_id['x_link_document_folder_id'] = folder_document_id.id
            ufiles_folder = {key: value for key, value in request.params.items() if key.startswith('ufiles_')}
            request.env['document.folder'].sudo().generate_folder_hierarchy(folder_document_id, ufiles_folder,
                                                                            int(thread_id), thread_model)
            request.env['document.folder'].sudo().document_folder_zip(folder_id)
        except AccessError:
            folderData = {'error': _("You are not allowed to upload an attachment here.")}
        return request.make_response(
            data=json.dumps(folderData),
            headers=[('Content-Type', 'application/json')]
        )

    @http.route('/document/folder/download', methods=['POST'], type='http', auth='public')
    def get_download_folder(self, attachment_id, **kwargs):
        zip_attachment_id = request.env['ir.attachment'].browse(int(attachment_id))
        zip_data = {}
        if zip_attachment_id.x_link_document_folder_id:
            if zip_attachment_id.x_link_document_folder_id.x_downloaded_folder_id:
                zip_data['folder_download_id'] = zip_attachment_id.x_link_document_folder_id.x_downloaded_folder_id.id

        return request.make_response(
            data=json.dumps(zip_data),
            headers=[('Content-Type', 'application/json')]
        )

    def extract_path(self, origin_url, url):
        match = re.search(rf'{origin_url}(.*)', url)
        if match:
            path = match.group(1)
            # Normalize the path to remove redundant slashes
            normalized_path = re.sub(r'/+', '/', path)
            return normalized_path
        return '/'

    @http.route('/document/folder/uploadFileExistFolder', methods=['POST'], type='http', auth='public')
    def document_folder_exist_upload_file(self, parent_attachment_folder_id, current_folder_id=False, res_id=False,
                                          res_model=False, **kwargs):

        if not (parent_attachment_folder_id and current_folder_id):
            attachmentData = {'error': _("Missing attachment ID.")}
        else:
            parent_attachment_folder = request.env['ir.attachment'].browse(int(parent_attachment_folder_id))
            upload_document_folder = request.env['document.folder'].browse(int(current_folder_id))
            ufiles_upload = {key: value for key, value in request.params.items() if key.startswith('ufiles_')}
            if ufiles_upload:
                for ufile_k, ufile_v in ufiles_upload.items():
                    parent_folder = upload_document_folder
                    file_name = ufile_v.filename
                    parent_folder_id = parent_attachment_folder.x_link_document_folder_id
                    try:
                        # Check if the file is a BytesIO object
                        if isinstance(ufile_v.stream, io.BytesIO):
                            file_content = ufile_v.stream.read()  # Read the file content from the stream
                        else:
                            file_content = ufile_v.read()  # Read the file content

                        # Convert the file content to base64 for storage
                        file_base64 = base64.b64encode(file_content)

                        vals = {
                            'name': file_name,
                            'datas': file_base64,  # Store the base64-encoded content
                            'x_document_folder_id': parent_folder.id,
                            'x_original_folder_id': parent_folder_id.id,
                            'x_document_folder_path': f'{parent_folder.x_document_folder_path}/{file_name}',
                        }
                        file = request.env['ir.attachment'].create(vals)
                        if parent_attachment_folder.nextcloud_attachment:
                            company = request.env.company.sudo()
                            nextcloud_params = company.get_nextcloud_information(res_model=res_model, res_id=res_id)
                            username = nextcloud_params.get('nextcloud_username')
                            password = nextcloud_params.get('nextcloud_password')
                            folder_mapping = nextcloud_params.get('folder_mapping')
                            url = nextcloud_params.get('nextcloud_url')
                            origin_url = f"{url}/remote.php/dav/files/{username}/"
                            parent_nc_path = self.extract_path(origin_url,
                                                               parent_attachment_folder.nextcloud_share_link)
                            if not parent_nc_path:
                                parent_nc_path = origin_url + '/'
                            # Check if `b` is the last part of `a`
                            if parent_nc_path.endswith(upload_document_folder.x_document_folder_path):
                                current_nc_path = parent_nc_path
                            else:
                                # Merge the two paths if necessary
                                current_nc_path = f'{parent_nc_path}/{upload_document_folder.x_document_folder_path.split("/", 1)[-1]}'
                            nc_current_folder_id = request.env['nextcloud.folder'].search(
                                [('name', '=', current_nc_path)], limit=1)
                            if nc_current_folder_id:
                                file_nc = file.with_context(res_id=res_id,
                                                            res_model=res_model).request_upload_file_nextcloud(
                                    nc_current_folder_id.id)
                    except Exception as e:
                        _logger.error(f"Error creating file: {file_name}, Error: {e}")
                        return False

            attachmentData = {
                'parent_attachment_folder': parent_attachment_folder.id
            }

        return request.make_response(
            data=json.dumps(attachmentData),
            headers=[('Content-Type', 'application/json')]
        )

    @http.route('/document/folder/uploadFolderExistFolder', methods=['POST'], type='http', auth='public')
    def document_folder_exist_upload_folder(self, parent_attachment_folder_id, current_folder_id=False, **kwargs):

        if not (parent_attachment_folder_id and current_folder_id):
            attachmentData = {'error': _("Missing attachment ID.")}
        else:
            parent_attachment_folder = request.env['ir.attachment'].browse(int(parent_attachment_folder_id))
            parent_folder_id = parent_attachment_folder.x_link_document_folder_id
            upload_document_folder = request.env['document.folder'].browse(int(current_folder_id))
            ufiles_upload = {key: value for key, value in request.params.items() if key.startswith('ufiles_')}
            if ufiles_upload:
                folder_name = ufiles_upload['ufiles_0'].filename.split('/')[0]
                request.env['document.folder'].sudo().generate_folder_hierarchy_exist(upload_document_folder,
                                                                                      ufiles_upload, parent_folder_id)
                if parent_attachment_folder.nextcloud_attachment:
                    folder_vals = {
                        'name': folder_name,
                        'x_is_folder': True,
                        'mimetype': 'document/folder',
                        'type': 'folder'
                    }
                    folder_id = request.env['ir.attachment'].create(folder_vals)
                    upload_folder = \
                    upload_document_folder.x_child_folder_ids.filtered(lambda a: a.x_name == folder_name)[0]
                    if upload_folder:
                        folder_id['x_link_document_folder_id'] = upload_folder.id
                    company = request.env.company.sudo()
                    nextcloud_params = company.get_nextcloud_information(res_model=False, res_id=False)
                    username = nextcloud_params.get('nextcloud_username')
                    password = nextcloud_params.get('nextcloud_password')
                    folder_mapping = nextcloud_params.get('folder_mapping')
                    url = nextcloud_params.get('nextcloud_url')
                    origin_url = f"{url}/remote.php/dav/files/{username}/"
                    parent_nc_path = self.extract_path(origin_url, parent_attachment_folder.nextcloud_share_link)
                    if not parent_nc_path:
                        parent_nc_path = origin_url + '/'
                    # Check if `b` is the last part of `a`
                    if parent_nc_path.endswith(upload_document_folder.x_document_folder_path):
                        current_nc_path = parent_nc_path
                    else:
                        # Merge the two paths if necessary
                        current_nc_path = f'{parent_nc_path}/{upload_document_folder.x_document_folder_path.split("/", 1)[-1]}'
                    nc_current_folder_id = request.env['nextcloud.folder'].search(
                        [('name', '=', current_nc_path)], limit=1)
                    if nc_current_folder_id:
                        folder_nc = folder_id.send_request_create_folder_nextcloud(nc_current_folder_id.id)

            attachmentData = {
                'parent_attachment_folder': parent_attachment_folder.id
            }

        return request.make_response(
            data=json.dumps(attachmentData),
            headers=[('Content-Type', 'application/json')]
        )
