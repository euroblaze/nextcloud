# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

import requests

from odoo import fields, models
from odoo.http import request


class IrAttachments(models.Model):
    _inherit = ['ir.attachment']

    nextcloud_attachment = fields.Boolean(string="Nextcloud Attachment", readonly="True")
    nextcloud_view_link = fields.Char(string="Nextcloud View Link")
    nextcloud_share_link = fields.Char(string="Nextcloud Share Link")

    def unlink(self):
        nextcloud_attachments = self.filtered(lambda l: l.nextcloud_attachment)
        if nextcloud_attachments:
            url = request.env['ir.config_parameter'].sudo().get_param('nextcloud.nextcloud_url')
            username = request.env['ir.config_parameter'].sudo().get_param('nextcloud.nextcloud_username')
            password = request.env['ir.config_parameter'].sudo().get_param('nextcloud.nextcloud_password')
            head = {'OCS-APIRequest': 'true'}
            for record in nextcloud_attachments:
                filename = record.name
                url = url + '/remote.php/dav/files/' + username + '/' + filename
                delete_file = requests.delete(
                    url,
                    headers=head,
                    auth=(username, password)
                )
                logging.info(delete_file)
        return super().unlink()


