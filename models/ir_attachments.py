import logging

import requests

from odoo import fields, models
from odoo.http import request


class IrAttachments(models.Model):
    _inherit = 'ir.attachment'

    nextcloud_attachment = fields.Boolean(string="Nextcloud Attachment", readonly="True")
    nextcloud_view_link = fields.Char(string="Nextcloud View Link")
    nextcloud_share_link = fields.Char(string="Nextcloud Share Link")
    # Handle choose folder later
    # nextcloud_folder = fields.Char(string="Nextcloud Folder")

    def unlink(self):
        nextcloud_attachments = self.filtered(lambda l: l.nextcloud_attachment)
        if nextcloud_attachments:
            head = {'OCS-APIRequest': 'true'}
            for record in nextcloud_attachments:
                nextcloud_params = record.company_id.sudo().get_nextcloud_information()
                username = nextcloud_params.get('nextcloud_username')
                password = nextcloud_params.get('nextcloud_password')
                url = record.nextcloud_share_link
                delete_file = requests.delete(
                    url,
                    headers=head,
                    auth=(username, password)
                )
                logging.info("Delete NextCloud: %s Status %s " % (url, delete_file))
        return super().unlink()
