# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.tools.translate import _


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
        if zip_attachment_id.x_downloaded_attachment_id:
            zip_data['folder_download_id'] = zip_attachment_id.x_downloaded_attachment_id

        return request.make_response(
            data=json.dumps(zip_data),
            headers=[('Content-Type', 'application/json')]
        )
