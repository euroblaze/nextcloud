"""V18 JSON-RPC endpoints for the Nextcloud chatter integration.

All endpoints `auth='user'` (no public access) and `type='json'`
(automatic CSRF + JSON serialisation).
"""
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class NextcloudController(http.Controller):

    @http.route('/nextcloud/folder/tree', type='json', auth='user')
    def folder_tree(self, only_folders=False):
        """Return the cached `nextcloud.folder` tree for the current user's
        company. Used by the Browse-NC dialog.
        """
        company = request.env.company.sudo()
        username = company.nextcloud_username
        domain = [('username', '=', username)]
        if only_folders:
            domain.append(('folder', '=', True))
        rows = request.env['nextcloud.folder'].sudo().search_read(
            domain,
            fields=['id', 'name', 'folder_name', 'parent_id', 'folder', 'file_type'],
            order='folder desc, name asc',
        )
        return {
            'rows': rows,
            'default_folder_id': company.nextcloud_folder_id.id or False,
            'username': username,
        }

    @http.route('/nextcloud/folder/sync', type='json', auth='user')
    def folder_sync(self):
        """Trigger a fresh PROPFIND-based sync."""
        request.env.company.sudo().sync_nextcloud_folder()
        return {'ok': True}

    @http.route('/nextcloud/attachment/upload_to_nc', type='json', auth='user')
    def upload_attachment_to_nc(self, attachment_id, folder_id=False, clear_local=False):
        """Push an existing ir.attachment up to NC."""
        attachment = request.env['ir.attachment'].browse(int(attachment_id))
        if not attachment.exists():
            return {'error': "Unknown attachment."}
        attachment.check('write')
        return attachment.action_upload_to_nextcloud(
            folder_id=folder_id, clear_local=clear_local,
        )

    @http.route('/nextcloud/attachment/from_nc', type='json', auth='user')
    def attachment_from_nc(self, nc_path, res_model, res_id):
        """Create an ir.attachment from a Nextcloud file path,
        bound to (res_model, res_id).
        """
        if not (nc_path and res_model):
            return {'error': "nc_path and res_model are required."}
        attachment = request.env['ir.attachment'].create_from_nextcloud_path(
            nc_path, res_model, res_id,
        )
        return {
            'attachment_id': attachment.id,
            'name': attachment.name,
            'mimetype': attachment.mimetype,
            'share_link': attachment.nextcloud_share_link,
        }

    @http.route('/nextcloud/folder/public_share', type='json', auth='user')
    def folder_public_share(self, folder_id):
        """Generate a public share link for a `nextcloud.folder` row."""
        folder = request.env['nextcloud.folder'].browse(int(folder_id))
        if not folder.exists():
            return {'error': "Unknown folder."}
        url = folder.get_public_link(folder.name, 0, 'nextcloud.folder')
        return {'public_link': url or False}
